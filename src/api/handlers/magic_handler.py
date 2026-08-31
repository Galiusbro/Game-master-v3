"""
Magic Handler

Handles magic spells and rituals with automatic event creation
"""

import logging
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from core.world_service import world_service
from domain.entities import EntityType
from infrastructure.command_classification_service import command_classifier

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from api.game_routes import GameCommandRequest
    from core.semantic_parser import ParsedCommand

logger = logging.getLogger(__name__)


async def handle_magic(
    request: "GameCommandRequest", parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle magic spells and rituals with automatic event creation"""
    logger.info(f"🔮 Processing magic action: {parsed.raw_command}")
    
    # Detect resurrection magic using modern classification
    resurrection_event, resurrection_conf = command_classifier.detect_special_event(parsed.raw_command)
    is_resurrection = resurrection_event == "resurrection_event" and resurrection_conf > 0.5
    
    if is_resurrection and parsed.target_npc_id:
        logger.info(f"✨ Resurrection spell detected! Confidence: {resurrection_conf:.2f}, NPC: {parsed.target_npc_id}")
        
        try:
            npc = await world_service.get_npc(parsed.target_npc_id)
            
            if npc and hasattr(npc, 'is_alive') and not npc.is_alive:
                logger.info(f"💀➡️😇 Resurrecting {npc.name}!")
                
                # RESURRECT THE NPC!
                npc.is_alive = True
                npc.current_state.current_mood = "confused but grateful"
                npc.current_state.current_activity = "slowly awakening"
                npc.description = f"A stout, cheerful man with graying hair and a welcoming smile. He looks slightly bewildered but very much alive, with a faint glow still lingering around him from recent magical revival."
                
                # Save the resurrection
                updated_npc = await world_service.update_entity(
                    entity=npc, 
                    actor_id=request.player_id, 
                    session_id=request.session_id
                )
                
                # CREATE RESURRECTION EVENT ENTITY FOR AI MEMORY!
                try:
                    from domain.entities import Event, ActionType, ActorType
                    from uuid import uuid4
                    
                    event = Event(
                        id=uuid4(),
                        name=f"Magical Resurrection of {npc.name}",
                        description=f"Through ancient magic and a scroll of resurrection, {npc.name} was brought back from death to life in the tavern. His soul was restored to his body by powerful magic.",
                        action_type=ActionType.MAGIC,
                        actor_id=request.player_id,
                        actor_type=ActorType.PLAYER,
                        participants=[request.player_id, npc.id],
                        location_id=npc.current_state.current_location_id,
                        before_state={"npc_alive": False, "spell_cast": "resurrection"},
                        after_state={"npc_alive": True, "resurrection_successful": True},
                        session_id=request.session_id,
                        confidence_score=1.0
                    )
                    
                    # Store event in Graph DB for AI memory
                    await world_service.create_entity(
                        event,
                        actor_id=request.player_id,
                        session_id=request.session_id
                    )
                    
                    logger.info(f"📚 Created resurrection event entity: {event.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create resurrection event: {e}")
                
                logger.info(f"✅ {npc.name} successfully resurrected!")
                
                return {
                    "success": True,
                    "action_type": "magic",
                    "content": f"The scroll glows with brilliant light as ancient magic courses through {npc.name}'s lifeless form. Suddenly, his eyes flutter open and he draws a sharp, gasping breath! The color returns to his cheeks as life floods back into his body. {npc.name} sits up slowly, looking around in confusion but very much alive. 'What... what happened?' he whispers, his voice hoarse but real.",
                    "original_command": request.command,
                    "resolved_entities": {"resurrected_npc": npc.name},
                    "warnings": [f"Successfully resurrected {npc.name}", "Resurrection event recorded for AI memory"]
                }
                
            elif npc and getattr(npc, 'is_alive', True):
                return {
                    "success": True,
                    "action_type": "magic",
                    "content": f"You attempt to cast resurrection on {npc.name}, but the magic fizzles harmlessly - {npc.name} is already very much alive and well!",
                    "original_command": request.command,
                    "warnings": ["Target is already alive"]
                }
            else:
                return {
                    "success": False,
                    "action_type": "magic",
                    "content": "The scroll glows, but there is no suitable target for resurrection magic here.",
                    "original_command": request.command,
                    "warnings": ["No dead NPC found to resurrect"]
                }
                
        except Exception as e:
            logger.error(f"Error in resurrection magic: {e}")
            return {
                "success": False,
                "action_type": "magic",
                "content": "The magical energies swirl chaotically and then dissipate. Something went wrong with the spell.",
                "original_command": request.command,
                "warnings": [f"Magic failed: {str(e)}"]
            }
    
    # For other magic, return a generic response that can be handled by _handle_unknown
    return {
        "success": False,
        "action_type": "magic",
        "content": f"You attempt: {request.command}. The magical energies are unclear.",
        "original_command": request.command,
        "warnings": ["Non-resurrection magic - needs AI interpretation"],
        "needs_ai_interpretation": True  # Flag to indicate this should go to _handle_unknown
    }