"""
Combat Handler

Handles combat actions with dice rolling and state mutations
"""

import logging
from typing import Any, List, Optional, TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException

from core.dice_engine import dice_engine
from core.world_service import world_service
from domain.entities import EntityType
from infrastructure.ai_service import ai_service
from infrastructure.command_classification_service import command_classifier

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from api.game_routes import GameCommandRequest
    from core.semantic_parser import ParsedCommand

logger = logging.getLogger(__name__)


async def handle_combat(
    request: "GameCommandRequest", parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle combat actions with dice rolling and state mutations"""
    warnings = []  # Initialize warnings list at the beginning
    try:
        # Get player entity for combat calculations
        player = await world_service.get_entity(request.player_id, EntityType.PLAYER)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Build combat context
        context = {
            'time_of_day': 'day',
            'target_attitude': 'hostile',  # Combat is always hostile
            'combat_mode': True
        }
        
        # Get target info for combat calculations
        target_ac = 15  # Default AC
        if parsed.target_npc_id:
            target_npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
            if target_npc and target_npc.metadata:
                # Extract AC from boss metadata
                target_ac = target_npc.metadata.get('armor_class', 15)
                logger.info(f"⚔️ Combat vs {target_npc.name}: AC={target_ac}")
                context['target_ac'] = target_ac
        
        # 🎲 RESOLVE COMBAT ACTION WITH DICE ROLLS!
        sequence = dice_engine.resolve_complex_action(
            actor=player,
            action_description=request.command,
            target_id=parsed.target_npc_id,
            context=context
        )
        
        # 💀 HANDLE PLAYER DAMAGE IN COMBAT
        damage_taken = 0
        if sequence and sequence.primary_roll:
            # If player failed the roll, they take damage
            if not sequence.success:
                # Calculate damage based on difficulty
                base_damage = 5  # Base damage for failed rolls
                if sequence.primary_roll.is_fumble:
                    damage_taken = base_damage * 2  # Critical failure = double damage
                else:
                    damage_taken = base_damage
                
                # Apply damage to player
                old_hp = player.effective_hit_points
                player.stats.current_hit_points = max(0, player.stats.current_hit_points - damage_taken)
                new_hp = player.effective_hit_points
                
                logger.info(f"💀 Player {player.name} took {damage_taken} damage: {old_hp} → {new_hp} HP")
                
                # Check if player died
                if player.effective_hit_points <= 0:
                    logger.info(f"💀💀💀 PLAYER {player.name} HAS DIED! HP: {player.effective_hit_points}")
                    warnings.append(f"Player has fallen in battle! HP: {player.effective_hit_points}")
        
        # Update player with combat results (including damage)
        await world_service.update_entity(
            entity=player,
            actor_id=request.player_id,
            session_id=request.session_id
        )
        
        # Generate AI response based on combat dice results
        ai_response = None
        if sequence.primary_roll:
            dice_context = f"""
                COMBAT ROLL RESULT:
                - Action: {sequence.action_description}
                - Attack Roll: {sequence.primary_roll.dice_notation} = {sequence.primary_roll.total}
                - Target AC: {target_ac}
                - Result: {'HIT' if sequence.success else 'MISS'}
            """
            if sequence.primary_roll.is_critical:
                dice_context += "- CRITICAL HIT! (Natural 20)\n"
            elif sequence.primary_roll.is_fumble:
                dice_context += "- CRITICAL MISS! (Natural 1)\n"
            
            # Generate AI narration for combat
            try:
                if ai_service.is_initialized:
                    ai_response = await ai_service.generate_dice_outcome_narration(
                        dice_results=dice_context,
                        action_description=request.command,
                        player=player,
                        context_entities=parsed.context_entities or []
                    )
                    response_content = ai_response.content
                else:
                    # Fallback combat narration
                    result_word = "HIT" if sequence.success else "MISS"
                    critical_text = ""
                    if sequence.primary_roll.is_critical:
                        critical_text = " - DEVASTATING BLOW!"
                    elif sequence.primary_roll.is_fumble:
                        critical_text = " - COMPLETE FAILURE!"
                    
                    response_content = f"⚔️ {sequence.primary_roll.description}: {sequence.primary_roll.total} vs AC {target_ac} = {result_word}{critical_text}"
            except Exception as e:
                logger.warning(f"AI combat narration failed: {e}")
                result_word = "HIT" if sequence.success else "MISS"
                response_content = f"⚔️ Combat roll: {sequence.primary_roll.total} vs AC {target_ac} = {result_word}"
        else:
            response_content = f"You attempt: {request.command}. Combat outcome unclear."
            ai_response = None
    
        # Check if combat resulted in NPC death and update state
    
        if parsed.target_npc_id:
            # Check if player command or AI response mentions death/killing using modern classification
            command_death_event, command_death_conf = command_classifier.detect_special_event(request.command)
            ai_death_event, ai_death_conf = command_classifier.detect_special_event(ai_response.content if ai_response else "")
            
            command_mentions_death = command_death_event == "death_event" and command_death_conf > 0.5
            ai_mentions_death = ai_death_event == "death_event" and ai_death_conf > 0.5
            
            if command_mentions_death or ai_mentions_death:
                try:
                    logger.info(f"🗡️ Death event detected! Command: {command_death_conf:.2f}, AI: {ai_death_conf:.2f}, NPC: {parsed.target_npc_id}")
                    
                    # Get the NPC entity
                    npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
                    logger.info(f"📋 Retrieved NPC: {npc.name if npc else 'None'}, is_alive: {npc.is_alive if npc else 'N/A'}")
                    
                    if npc and npc.is_alive:
                        logger.info(f"💀 Killing NPC {npc.name}...")
                        
                        # Update NPC state to dead
                        npc.is_alive = False
                        npc.current_state.current_mood = "dead"
                        npc.current_state.current_activity = "deceased"
                        
                        logger.info(f"💾 Saving updated NPC state for {npc.name}...")
                        
                        # Save the updated NPC state
                        updated_npc = await world_service.update_entity(
                            entity=npc,
                            actor_id=request.player_id,
                            session_id=request.session_id
                        )
                        
                        logger.info(f"✅ SUCCESS! NPC {npc.name} updated. New state: alive={updated_npc.is_alive}")
                        
                        # CREATE EVENT ENTITY FOR AI MEMORY!
                        try:
                            from domain.entities import Event, ActionType, ActorType
                            from uuid import uuid4
                            
                            death_event = Event(
                                id=uuid4(),
                                name=f"Death of {npc.name}",
                                description=f"{npc.name} was slain in combat. The tragic event occurred in the tavern, forever changing the atmosphere of the place.",
                                action_type=ActionType.COMBAT,
                                actor_id=request.player_id,
                                actor_type=ActorType.PLAYER,
                                participants=[request.player_id, npc.id],
                                location_id=npc.current_state.current_location_id,
                                before_state={"npc_alive": True, "combat_initiated": True},
                                after_state={"npc_alive": False, "death_confirmed": True},
                                session_id=request.session_id,
                                confidence_score=1.0
                            )
                            
                            # Store event in Graph DB for AI memory
                            await world_service.create_entity(
                                death_event,
                                actor_id=request.player_id,
                                session_id=request.session_id
                            )
                            
                            logger.info(f"📚 Created death event entity: {death_event.id}")
                            warnings.append(f"Death event recorded for AI memory")
                            
                        except Exception as e:
                            logger.error(f"Failed to create death event: {e}")
                            warnings.append(f"Warning: Death event not recorded - {e}")
                        
                        warnings.append(f"NPC {npc.name} state updated to deceased")
                        
                        # Override AI response if it refused to cooperate (using semantic quality analysis)
                        if ai_response:
                            quality, quality_conf = command_classifier.analyze_content_quality(ai_response.content)
                            if quality == "low_quality" and quality_conf > 0.6:
                                ai_response.content = f"In a tragic turn of events, {npc.name} has fallen. The tavern falls silent as the gravity of what has transpired settles over the room."
                                warnings.append(f"AI response overridden due to low quality ({quality}, conf: {quality_conf:.2f}) - death event processed")
                    else:
                        logger.warning(f"⚠️ Cannot kill NPC: npc={npc}, is_alive={npc.is_alive if npc else 'N/A'}")
                        
                except Exception as e:
                    logger.error(f"💥 CRITICAL ERROR updating NPC state: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(f"💥 Stack trace: {traceback.format_exc()}")
                    warnings.append(f"Failed to update NPC state: {e}")
        
        # Prepare combat dice rolls data for response
        dice_rolls_data = []
        if sequence and sequence.primary_roll:
            dice_rolls_data.append({
                "type": sequence.primary_roll.description,
                "dice_notation": sequence.primary_roll.dice_notation,
                "result": sequence.primary_roll.total,
                "dc": target_ac,  # In combat, DC is the target's AC
                "success": sequence.success,
                "is_critical": sequence.primary_roll.is_critical,
                "is_fumble": sequence.primary_roll.is_fumble,
                "modifiers": sequence.primary_roll.modifiers,
                "raw_results": sequence.primary_roll.raw_results
            })
        
        return {
            "success": sequence.success if sequence and sequence.primary_roll else True,
            "action_type": "combat",
            "content": response_content,
            "confidence": sequence.primary_roll.total / 20.0 if sequence and sequence.primary_roll else (ai_response.confidence if ai_response else 0.5),
            "tokens_used": ai_response.tokens_used if ai_response else 0,
            "response_time": ai_response.response_time if ai_response else 0.0,
            "resolved_entities": {
                'target_npc': str(parsed.target_npc_id) if parsed.target_npc_id else None,
                'target_ac': target_ac,
                'combat_result': 'HIT' if (sequence and sequence.success) else 'MISS',
                'attack_roll': sequence.primary_roll.total if sequence and sequence.primary_roll else None,
                'damage_taken': damage_taken,
                'player_hp': player.effective_hit_points,
                'player_max_hp': player.effective_max_hit_points,
                'player_dead': player.effective_hit_points <= 0
            },
            "dice_rolls": dice_rolls_data,
            "parsing_confidence": parsed.confidence,
            "original_command": request.command,
            "warnings": warnings,
            "event_id": sequence.sequence_id if sequence else (ai_response.event_id if ai_response else None)
        }
        
    except Exception as e:
        logger.error(f"Error handling combat: {e}")
        return {
            "success": False,
            "action_type": "combat",
            "content": f"You attempt: {request.command}, but the combat system encounters an error.",
            "original_command": request.command,
            "warnings": [f"Combat failed: {str(e)}"]
        }