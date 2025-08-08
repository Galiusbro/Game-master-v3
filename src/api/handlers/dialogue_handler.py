"""
Dialogue Handler

Handles dialogue with NPCs
"""

import logging

from fastapi import BackgroundTasks

from api.ai_routes import NPCDialogueRequest, npc_dialogue
from infrastructure.command_classification_service import command_classifier
from core.world_service import world_service
from domain.entities import EntityType

logger = logging.getLogger(__name__)


async def handle_dialogue(request, parsed) -> dict:
    """Handle dialogue with NPC"""
    
    if not parsed.target_npc_id:
        # Try to resolve NPC via semantic search as a graceful fallback
        try:
            # Prefer NPCs in player's current location when resolving by description
            location_filter = None
            try:
                player = await world_service.get_entity(request.player_id, EntityType.PLAYER)
                if player and getattr(player, 'current_location_id', None):
                    location_filter = {"current_location_id": str(player.current_location_id)}
            except Exception:
                location_filter = None

            search_results = await world_service.search_entities(
                query=request.command,
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
                "original_command": request.command,
                "warnings": ["No NPC resolved from command"]
            }
    
    # CHECK IF NPC IS ALIVE BEFORE DIALOGUE!
    logger.info(f"🔍 Checking NPC status for dialogue: {parsed.target_npc_id}")
    try:
        npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
        
        if npc:
            logger.info(f"✅ NPC found: {npc.name}, is_alive: {getattr(npc, 'is_alive', 'MISSING')}")
            if hasattr(npc, 'is_alive') and not npc.is_alive:
                logger.info(f"💀 Player tried to talk to dead NPC: {npc.name}")
                return {
                    "success": True,
                    "action_type": "dialogue",
                    "content": f"You approach {npc.name}, but there is no response. The lifeless body lies motionless before you - death has claimed them. No amount of words can reach them now.",
                    "original_command": request.command,
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
                "original_command": request.command,
                "warnings": ["NPC not found in database"]
            }
            
    except Exception as e:
        logger.error(f"❌ Error checking NPC status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Continue with normal dialogue as fallback
    
    # Detect social intent (e.g., befriend) and update relationship if needed
    try:
        intent, intent_conf = command_classifier.classify_social_intent(request.command)
        if intent == "befriend" and intent_conf >= 0.5:
            # Update NPC relationship_to_player -> 'friendly'
            # Note: relationship_to_player expects string UUID keys in JSON persistence
            if npc and hasattr(npc, 'current_state') and npc.current_state:
                # Ensure dict exists
                relationship_map = getattr(npc.current_state, 'relationship_to_player', None)
                if relationship_map is None:
                    npc.current_state.relationship_to_player = {}
                    relationship_map = npc.current_state.relationship_to_player
                # Keep UUID key in-memory (Pydantic-typed); storage layers stringify keys safely
                relationship_map[request.player_id] = "friendly"
                # Persist via world service (no external API)
                await world_service.update_entity(
                    entity=npc,
                    actor_id=request.player_id,
                    session_id=request.session_id
                )
                logger.info(f"🤝 Set relationship_to_player[{request.player_id}] = friendly for NPC {npc.id}")
    except Exception as e:
        logger.warning(f"Failed to process social intent: {e}")

    # Create dialogue request
    dialogue_req = NPCDialogueRequest(
        player_id=request.player_id,
        npc_id=parsed.target_npc_id,
        player_message=parsed.message or "Hello",
        situation_context="",
        session_id=request.session_id
    )
    
    # Call AI dialogue endpoint with BackgroundTasks
    bg_tasks = BackgroundTasks()
    ai_response = await npc_dialogue(dialogue_req, bg_tasks)
    
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
        "original_command": request.command,
        "warnings": ai_response.warnings,
        "event_id": ai_response.event_id
    }