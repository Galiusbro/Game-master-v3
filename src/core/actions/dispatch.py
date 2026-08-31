"""
Dispatch

Takes one utterance at a table and plays it out: checks whether the
character can act at all, works out what they meant, and hands it to the
action that resolves it. Returns a plain result dictionary that any
transport can render.
"""

import logging
from typing import Any, Dict

from core.actions.command import GameCommand
from core.actions.combat import handle_combat
from core.actions.dialogue import handle_dialogue
from core.actions.exploration import handle_exploration
from core.actions.magic import handle_magic
from core.actions.movement import handle_movement
from core.actions.resurrection import handle_resurrection
from core.actions.search import handle_search
from core.actions.skill_check import handle_skill_check
from core.actions.trade import handle_trade
from core.actions.unknown import handle_unknown
from core.narration import EntityNotFound
from core.permissions import NotYours
from core.semantic_parser import semantic_parser
from core.social_checks import BEFRIEND_INTENT_THRESHOLD
from core.world_service import world_service
from infrastructure.ai_service import ai_service
from infrastructure.command_classification_service import GameAction, command_classifier

logger = logging.getLogger(__name__)

# Actions that are really someone talking, however the parser labelled them.
CONVERSATIONAL = {
    GameAction.DIALOGUE,
    GameAction.PERSUASION,
    GameAction.DECEPTION,
}

# Actions resolved by a skill check rather than by their own handler.
SKILL_CHECKS = {
    GameAction.STEALTH,
    GameAction.INVESTIGATION,
    GameAction.SLEIGHT_OF_HAND,
    GameAction.ATHLETICS,
    GameAction.PERCEPTION,
    GameAction.SKILL_CHECK,
}


async def execute_command(command: GameCommand) -> Dict[str, Any]:
    """Play out one command and return what happened."""
    logger.info(
        f"Processing command: '{command.text}' for player {command.player_id}"
    )

    player = await world_service.get_player(command.player_id, world_id=command.world_id)
    if not player:
        # Either there is no such character, or it belongs to another world.
        # Both are the same refusal from here: you cannot act in a world you
        # are not in.
        raise EntityNotFound(
            f"No character {command.player_id} in world {command.world_id}"
        )

    if player.account_id and player.account_id != command.account_id:
        # The character has an owner and the caller is not them. Saying so
        # plainly beats pretending the character does not exist, because
        # the caller can see it in their own world listings.
        raise NotYours(
            f"Character {player.id} belongs to another account"
        )

    if player.effective_hit_points <= 0:
        return await _handle_while_dead(command, player)

    parsed = await semantic_parser.parse_command(
        world_id=command.world_id,
        session_id=command.session_id,
        player_id=command.player_id,
        raw_command=command.text,
        dialogue_context=command.dialogue_context,
    )
    logger.info(f"Parsed action: {parsed.action}, confidence: {parsed.confidence}")

    # A deliberate attempt to win someone over is a conversation, whatever
    # else the parser made of the phrasing.
    try:
        social_intent, social_conf = command_classifier.classify_social_intent(
            command.text
        )
    except Exception:
        social_intent, social_conf = None, 0.0
    if social_intent == "befriend" and social_conf >= BEFRIEND_INTENT_THRESHOLD:
        return await handle_dialogue(command, parsed)

    if parsed.action in CONVERSATIONAL:
        return await handle_dialogue(command, parsed)

    if parsed.action == GameAction.MOVEMENT:
        return await handle_movement(command, parsed)

    if parsed.action == GameAction.SEARCH:
        return await handle_search(command, parsed)

    if parsed.action == GameAction.EXPLORE:
        return await handle_exploration(command, parsed)

    if parsed.action == GameAction.TRADE:
        result = await handle_trade(command, parsed)
        # Trade without a merchant in reach is really just looking around.
        if result.get("needs_exploration_handler"):
            return await handle_exploration(command, parsed)
        return result

    if parsed.action == GameAction.COMBAT:
        return await handle_combat(command, parsed)

    if parsed.action == GameAction.MAGIC:
        result = await handle_magic(command, parsed)
        # Anything but resurrection is left for the model to interpret.
        if result.get("needs_ai_interpretation"):
            return await handle_unknown(command, parsed)
        return result

    if parsed.action in SKILL_CHECKS:
        return await handle_skill_check(command, parsed)

    return await handle_unknown(command, parsed)


async def _handle_while_dead(command: GameCommand, player: Any) -> Dict[str, Any]:
    """A dead character can do one thing: come back."""
    logger.info(
        f"💀 Player {player.name} is dead (HP: {player.effective_hit_points}). "
        "Checking for resurrection attempt."
    )

    event, confidence = command_classifier.detect_special_event(command.text)
    if event == "resurrection_event" and confidence > 0.6:
        logger.info(f"📜 Resurrection attempt detected! Confidence: {confidence:.2f}")
        return await handle_resurrection(command, player)

    content = (
        f"💀 {player.name}, you have fallen. Your spirit lingers between life "
        "and death. To continue, you must use a Scroll of Resurrection."
    )
    tokens_used = 0
    response_time = 0.0
    try:
        if ai_service.is_initialized:
            death = await ai_service.generate_death_response(
                player_name=player.name,
                player_class=(
                    player.stats.character_class.value
                    if player.stats.character_class
                    else "adventurer"
                ),
                command=command.text,
            )
            content = death.content
            tokens_used = death.tokens_used
            response_time = death.response_time
    except Exception as e:
        logger.warning(f"AI death response failed: {e}")

    return {
        "success": False,
        "action_type": "death",
        "content": content,
        "confidence": 1.0,
        "tokens_used": tokens_used,
        "response_time": response_time,
        "resolved_entities": {
            "player_dead": True,
            "player_hp": player.effective_hit_points,
            "player_max_hp": player.effective_max_hit_points,
            "resurrection_required": True,
        },
        "parsing_confidence": 1.0,
        "original_command": command.text,
        "warnings": ["Player is dead - resurrection required"],
        "event_id": None,
    }
