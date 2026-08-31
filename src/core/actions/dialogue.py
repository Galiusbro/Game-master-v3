"""
Dialogue Handler

Handles dialogue with NPCs
"""

import logging
from typing import Any, TYPE_CHECKING


from core import narration
from infrastructure.command_classification_service import command_classifier
from core.world_service import world_service
from domain.entities import EntityType
from core.social_checks import (
    BEFRIEND_INTENT_THRESHOLD,
    is_on_social_cooldown,
)
from core.social_engine.engine import social_engine

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from core.semantic_parser import ParsedCommand

from core.actions.command import GameCommand

logger = logging.getLogger(__name__)


async def handle_dialogue(
    command: GameCommand, parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle dialogue with NPC"""
    
    mechanics_info = None

    if not parsed.target_npc_id:
        # Try to resolve NPC via semantic search as a graceful fallback
        try:
            # Prefer NPCs in player's current location when resolving by description
            location_filter = None
            try:
                player = await world_service.get_player(command.player_id)
                if player and getattr(player, 'current_location_id', None):
                    location_filter = {"current_location_id": str(player.current_location_id)}
            except Exception:
                location_filter = None

            search_results = await world_service.search_entities(
                query=command.text,
                limit=1,
                entity_types=[EntityType.NPC],
                include_graph_context=False,
                filters=location_filter,
            )
            if search_results:
                parsed.target_npc_id = search_results[0][0].id
                logger.info(f"Resolved NPC via vector search: {parsed.target_npc_id}")
        except Exception as e:
            logger.warning(f"Vector fallback for NPC resolution failed: {e}")
        
        if not parsed.target_npc_id:
            return {
                "success": False,
                "action_type": "dialogue",
                "content": "I don't see anyone to talk to here. Could you be more specific about who you want to speak with?",
                "original_command": command.text,
                "warnings": ["No NPC resolved from command"]
            }
    
    # CHECK IF NPC IS ALIVE BEFORE DIALOGUE!
    logger.info(f"🔍 Checking NPC status for dialogue: {parsed.target_npc_id}")
    try:
        npc = await world_service.get_npc(parsed.target_npc_id)
        
        if npc:
            logger.info(f"✅ NPC found: {npc.name}, is_alive: {getattr(npc, 'is_alive', 'MISSING')}")
            if hasattr(npc, 'is_alive') and not npc.is_alive:
                logger.info(f"💀 Player tried to talk to dead NPC: {npc.name}")
                return {
                    "success": True,
                    "action_type": "dialogue",
                    "content": f"You approach {npc.name}, but there is no response. The lifeless body lies motionless before you - death has claimed them. No amount of words can reach them now.",
                    "original_command": command.text,
                    "warnings": [f"Cannot dialogue with deceased NPC: {npc.name}"],
                    "resolved_entities": {"target_npc": npc.name}
                }
            else:
                logger.info(f"✅ NPC {npc.name} is alive, proceeding with dialogue")
        else:
            logger.warning(f"❌ NPC {parsed.target_npc_id} not found in database")
            return {
                "success": False,
                "action_type": "dialogue", 
                "content": "I don't see that person here anymore.",
                "original_command": command.text,
                "warnings": ["NPC not found in database"]
            }
            
    except Exception as e:
        logger.error(f"❌ Error checking NPC status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Continue with normal dialogue as fallback
    
    # Detect social intent (e.g., befriend) and run social check if needed
    try:
        intent, intent_conf = command_classifier.classify_social_intent(command.text)
        logger.info(f"Social intent detected: intent={intent}, confidence={intent_conf:.3f} for command='{command.text}'")
        player = await world_service.get_player(command.player_id)
        if intent == "befriend" and intent_conf >= BEFRIEND_INTENT_THRESHOLD and npc and player:

            # Hard blockers: same location and NPC is alive checked above
            if player.current_location_id and npc.current_state.current_location_id:
                if player.current_location_id != npc.current_state.current_location_id:
                    return {
                        "success": False,
                        "action_type": "dialogue",
                        "content": "There is no one like that here. You would have to find them first.",
                        "original_command": command.text,
                        "warnings": ["Different location: cannot befriend out of proximity"],
                    }

            # A cooldown bars another attempt at winning them over — it does
            # not make the NPC mute. Skip the check and let the conversation
            # happen as ordinary dialogue.
            on_cooldown = is_on_social_cooldown(npc, command.player_id)
            if on_cooldown:
                logger.info(
                    f"Social cooldown active for {npc.name}; continuing as plain dialogue"
                )

            # Run social engine (thin wrapper around existing mechanics)
            mechanics_info = None if on_cooldown else await social_engine.run_social_check(
                intent="befriend",
                player=player,
                npc=npc,
                message=command.text,
            )

            if mechanics_info:
                # Sync relationship label based on thresholds using returned disposition
                new_score = mechanics_info.get("new_disposition", 0)
                if new_score >= 50:
                    npc.current_state.relationship_to_player[command.player_id] = "friendly"
                elif new_score <= -50:
                    npc.current_state.relationship_to_player[command.player_id] = "hostile"

                # Persist via world service
                await world_service.update_entity(
                    entity=npc,
                    actor_id=command.player_id,
                    session_id=command.session_id,
                )

                # Log summary
                try:
                    roll = mechanics_info.get("roll", {})
                    logger.info(
                        f"🤝 Social check (Persuasion): DC {mechanics_info.get('dc')}, roll {roll.get('total')} "
                        f"({'success' if roll.get('success') else 'fail'}), disposition delta {mechanics_info.get('disposition_delta')} -> {new_score}"
                    )
                except Exception:
                    pass

                # Prepare mechanics info for response
                try:
                    relationship_label = npc.current_state.compute_relationship_for_player(command.player_id)
                except Exception:
                    relationship_label = npc.current_state.relationship_to_player.get(command.player_id, "neutral")

                mechanics_info["relationship"] = relationship_label
    except Exception as e:
        logger.warning(f"Failed to process social intent: {e}")

    # Create dialogue request
    ai_response = await narration.npc_dialogue(
        player_id=command.player_id,
        npc_id=parsed.target_npc_id,
        # The parser only fills `message` when the player quoted their words
        # or used a colon. Otherwise the command itself is what they said —
        # the old "Hello" default meant the NPC never heard the question.
        player_message=parsed.message or command.text,
        session_id=command.session_id,
    )
    
    return {
        "success": True,
        "action_type": "dialogue",
        "content": ai_response.content,
        "confidence": ai_response.confidence,
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "resolved_entities": {
            "npc_id": str(parsed.target_npc_id),
            "npc_found": True
        },
        "parsing_confidence": parsed.confidence,
        "original_command": command.text,
        "warnings": ai_response.warnings,
        "dice_rolls": ([mechanics_info] if mechanics_info else []),
        "event_id": ai_response.event_id
    }