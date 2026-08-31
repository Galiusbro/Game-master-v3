"""
Combat Handler

Resolves one round of combat: the player swings, the target strikes back,
and hit points on both sides decide who falls. The dice settle the outcome
before any narration is requested.
"""

import logging
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

from fastapi import HTTPException

from core.dice_engine import dice_engine
from core.world_service import world_service
from domain.entities import NPC, AbilityScore, Player
from infrastructure.ai_service import ai_service

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from core.semantic_parser import ParsedCommand

from core.actions.command import GameCommand

logger = logging.getLogger(__name__)

# Used when the player swings at something the world does not model as an
# entity ("the bandit"), so a fight against fiction still behaves sanely.
UNKNOWN_TARGET_AC = 13
UNKNOWN_TARGET_ATTACK_BONUS = 2
UNKNOWN_TARGET_DAMAGE = "1d4"


def _player_damage_notation(player: Player) -> str:
    """Weapon damage for the player, scaled by Strength."""
    modifier = player.stats.get_ability_modifier(AbilityScore.STRENGTH)
    if modifier > 0:
        return f"1d8+{modifier}"
    if modifier < 0:
        return f"1d8-{abs(modifier)}"
    return "1d8"


async def handle_combat(
    command: GameCommand, parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle combat actions with dice rolling and state mutations"""
    warnings: list[str] = []
    dice_rolls_data: list[dict[str, Any]] = []

    try:
        player = await world_service.get_player(command.player_id, world_id=command.world_id)
        if not isinstance(player, Player):
            raise HTTPException(status_code=404, detail="Player not found")

        # ---------------------------------------------------------------- #
        # Resolve the target
        # ---------------------------------------------------------------- #
        target_npc: Optional[NPC] = None
        if parsed.target_npc_id:
            found = await world_service.get_npc(parsed.target_npc_id, world_id=command.world_id)
            target_npc = found if isinstance(found, NPC) else None

        if target_npc is not None and not target_npc.is_alive:
            return {
                "success": False,
                "action_type": "combat",
                "content": (
                    f"{target_npc.name} is already dead. Your blade finds nothing "
                    "but a body that has stopped answering."
                ),
                "resolved_entities": {"target_npc": target_npc.name},
                "parsing_confidence": parsed.confidence,
                "original_command": command.text,
                "warnings": ["Target already deceased"],
            }

        if target_npc is not None:
            target_ac = target_npc.effective_armor_class
            target_name = target_npc.name
        else:
            target_ac = UNKNOWN_TARGET_AC
            target_name = "your opponent"
            warnings.append("Target is not a known entity — using default statistics")

        # ---------------------------------------------------------------- #
        # The player's swing
        # ---------------------------------------------------------------- #
        attack_roll = dice_engine.make_attack_roll(
            attacker=player,
            target_ac=target_ac,
            description=f"Attack on {target_name}",
        )
        player.add_roll_to_history(attack_roll)

        dice_rolls_data.append({
            "type": attack_roll.description,
            "dice_notation": attack_roll.dice_notation,
            "result": attack_roll.total,
            "dc": target_ac,
            "success": attack_roll.is_success,
            "is_critical": attack_roll.is_critical,
            "is_fumble": attack_roll.is_fumble,
            "modifiers": attack_roll.modifiers,
            "raw_results": attack_roll.raw_results,
        })

        damage_dealt = 0
        target_died = False
        if attack_roll.is_success:
            damage_roll = dice_engine.make_damage_roll(
                attacker=player,
                damage_dice=_player_damage_notation(player),
                critical=attack_roll.is_critical,
                description=f"Damage to {target_name}",
            )
            player.add_roll_to_history(damage_roll)
            damage_dealt = max(0, damage_roll.total)

            dice_rolls_data.append({
                "type": damage_roll.description,
                "dice_notation": damage_roll.dice_notation,
                "result": damage_roll.total,
                "is_critical": damage_roll.is_critical,
                "modifiers": damage_roll.modifiers,
                "raw_results": damage_roll.raw_results,
            })

            if target_npc is not None:
                before_hp = target_npc.current_hit_points
                target_npc.current_hit_points = max(0, before_hp - damage_dealt)
                target_died = target_npc.current_hit_points <= 0
                logger.info(
                    f"⚔️ {player.name} hit {target_npc.name} for {damage_dealt}: "
                    f"{before_hp} → {target_npc.current_hit_points} HP"
                )

                if target_died:
                    target_npc.is_alive = False
                    target_npc.current_state.current_mood = "dead"
                    target_npc.current_state.current_activity = "deceased"
                    warnings.append(f"{target_npc.name} has been slain")

                await world_service.update_entity(
                    entity=target_npc,
                    actor_id=command.player_id,
                    session_id=command.session_id,
                )

                if target_died:
                    await _record_death_event(command, player, target_npc, warnings)

        # ---------------------------------------------------------------- #
        # The counter-attack. Damage reaches the player from an opponent's
        # roll against their armour class — never from their own miss.
        # ---------------------------------------------------------------- #
        damage_taken = 0
        if not target_died:
            if target_npc is not None:
                enemy_bonus = target_npc.attack_bonus
                enemy_damage = target_npc.damage_dice
            else:
                enemy_bonus = UNKNOWN_TARGET_ATTACK_BONUS
                enemy_damage = UNKNOWN_TARGET_DAMAGE

            enemy_die = dice_engine.roll_dice("1d20")[0]
            enemy_total = enemy_die + enemy_bonus
            player_ac = player.stats.armor_class
            enemy_hits = enemy_total >= player_ac

            dice_rolls_data.append({
                "type": f"{target_name} attacks back",
                "dice_notation": f"1d20+{enemy_bonus}",
                "result": enemy_total,
                "dc": player_ac,
                "success": enemy_hits,
                "is_critical": enemy_die == 20,
                "is_fumble": enemy_die == 1,
                "modifiers": enemy_bonus,
                "raw_results": [enemy_die],
            })

            if enemy_hits:
                rolled = dice_engine.roll_dice(enemy_damage)
                damage_taken = sum(rolled)
                if enemy_die == 20:
                    damage_taken += sum(dice_engine.roll_dice(enemy_damage))

                old_hp = player.effective_hit_points
                player.stats.current_hit_points = max(
                    0, player.stats.current_hit_points - damage_taken
                )
                logger.info(
                    f"💥 {target_name} hit {player.name} for {damage_taken}: "
                    f"{old_hp} → {player.effective_hit_points} HP"
                )
                if player.effective_hit_points <= 0:
                    warnings.append(
                        f"Player has fallen in battle! HP: {player.effective_hit_points}"
                    )

        # Persist the player once, after both sides have acted.
        await world_service.update_entity(
            entity=player,
            actor_id=command.player_id,
            session_id=command.session_id,
        )

        # ---------------------------------------------------------------- #
        # Narration — the dice have already decided everything above
        # ---------------------------------------------------------------- #
        outcome_lines = [
            f"- Action: {command.text}",
            f"- Attack roll: {attack_roll.dice_notation} = {attack_roll.total} vs AC {target_ac}",
            f"- Result: {'HIT' if attack_roll.is_success else 'MISS'}",
        ]
        if attack_roll.is_critical:
            outcome_lines.append("- CRITICAL HIT! (Natural 20)")
        elif attack_roll.is_fumble:
            outcome_lines.append("- CRITICAL MISS! (Natural 1)")
        if damage_dealt:
            outcome_lines.append(f"- {target_name} takes {damage_dealt} damage")
            if target_npc is not None:
                outcome_lines.append(
                    f"- {target_name} now at {target_npc.current_hit_points}/"
                    f"{target_npc.max_hit_points} HP"
                )
        if target_died:
            outcome_lines.append(f"- {target_name} is slain and falls")
        if damage_taken:
            outcome_lines.append(
                f"- {target_name} strikes back for {damage_taken} damage; "
                f"{player.name} now at {player.effective_hit_points}/"
                f"{player.effective_max_hit_points} HP"
            )
        if player.effective_hit_points <= 0:
            outcome_lines.append(f"- {player.name} falls unconscious and is dying")

        dice_context = "COMBAT ROUND RESULT:\n" + "\n".join(outcome_lines)

        ai_response = None
        response_content = dice_context
        try:
            if ai_service.is_initialized:
                ai_response = await ai_service.generate_dice_outcome_narration(
                    dice_results=dice_context,
                    action_description=command.text,
                    player=player,
                    context_entities=parsed.context_entities or [],
                )
                response_content = ai_response.content
            else:
                parts = [
                    f"⚔️ {attack_roll.total} vs AC {target_ac} = "
                    f"{'HIT' if attack_roll.is_success else 'MISS'}"
                ]
                if damage_dealt:
                    parts.append(f"{target_name} takes {damage_dealt}")
                if target_died:
                    parts.append(f"{target_name} falls")
                if damage_taken:
                    parts.append(f"you take {damage_taken}")
                response_content = " · ".join(parts)
        except Exception as e:
            logger.warning(f"AI combat narration failed: {e}")
            response_content = (
                f"⚔️ {attack_roll.total} vs AC {target_ac} = "
                f"{'HIT' if attack_roll.is_success else 'MISS'}"
            )

        return {
            "success": attack_roll.is_success,
            "action_type": "combat",
            "content": response_content,
            "confidence": ai_response.confidence if ai_response else 1.0,
            "tokens_used": ai_response.tokens_used if ai_response else 0,
            "response_time": ai_response.response_time if ai_response else 0.0,
            "resolved_entities": {
                "target_npc": str(parsed.target_npc_id) if parsed.target_npc_id else None,
                "target_name": target_name,
                "target_ac": target_ac,
                "target_hp": target_npc.current_hit_points if target_npc else None,
                "target_max_hp": target_npc.max_hit_points if target_npc else None,
                "target_dead": target_died,
                "combat_result": "HIT" if attack_roll.is_success else "MISS",
                "attack_roll": attack_roll.total,
                "damage_dealt": damage_dealt,
                "damage_taken": damage_taken,
                "player_hp": player.effective_hit_points,
                "player_max_hp": player.effective_max_hit_points,
                "player_dead": player.effective_hit_points <= 0,
            },
            "dice_rolls": dice_rolls_data,
            "parsing_confidence": parsed.confidence,
            "original_command": command.text,
            "warnings": warnings,
            "event_id": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling combat: {e}")
        return {
            "success": False,
            "action_type": "combat",
            "content": f"You attempt: {command.text}, but the combat system encounters an error.",
            "original_command": command.text,
            "warnings": [f"Combat failed: {str(e)}"],
        }


async def _record_death_event(
    command: GameCommand, player: Player, npc: NPC, warnings: list[str]
) -> None:
    """Persist the death as an Event so later scenes can remember it."""
    try:
        from domain.entities import ActionType, ActorType, Event

        death_event = Event(
            id=uuid4(),
            name=f"Death of {npc.name}",
            description=(
                f"{npc.name} was slain in combat by {player.name}."
            ),
            action_type=ActionType.COMBAT,
            actor_id=command.player_id,
            actor_type=ActorType.PLAYER,
            world_id=command.world_id,
            participants=[command.player_id, npc.id],
            location_id=npc.current_state.current_location_id,
            before_state={"npc_alive": True},
            after_state={"npc_alive": False, "death_confirmed": True},
            session_id=command.session_id,
            confidence_score=1.0,
        )

        await world_service.create_entity(
            death_event,
            actor_id=command.player_id,
            session_id=command.session_id,
            world_id=command.world_id,
        )
        logger.info(f"📚 Created death event entity: {death_event.id}")
    except Exception as e:
        logger.error(f"Failed to create death event: {e}")
        warnings.append(f"Warning: death event not recorded — {e}")
