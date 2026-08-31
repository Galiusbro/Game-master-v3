"""
AI Routes for Game Master V3
API endpoints for AI-powered game interactions
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from config.settings import settings
from core.context_builder import context_builder
from core.world_service import world_service
from domain.entities import ActorType, EntityType, Event, ActionType
from infrastructure.ai_service import ai_service, AIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Interactions"])


# Request/Response models
class NPCDialogueRequest(BaseModel):
    player_id: UUID
    npc_id: UUID
    player_message: str
    situation_context: Optional[str] = ""
    session_id: Optional[UUID] = None


class WorldDescriptionRequest(BaseModel):
    player_id: UUID
    request: str  # What the player wants to see/explore
    session_id: Optional[UUID] = None


class ActionResolutionRequest(BaseModel):
    player_id: UUID
    action_description: str
    target_entity_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class AIInteractionResponse(BaseModel):
    content: str
    confidence: float
    tokens_used: int
    response_time: float
    hallucination_detected: bool
    cited_entities: List[str]
    warnings: List[str]
    context_entities_used: int
    event_id: Optional[UUID] = None  # ID of created event for this interaction


class ContextSummaryResponse(BaseModel):
    total_entities_found: int
    entities_included: int
    tokens_estimated: int
    priority_breakdown: Dict[str, Any]
    assembly_time: float


@router.post("/npc/dialogue", response_model=AIInteractionResponse)
async def npc_dialogue(
    request: NPCDialogueRequest, background_tasks: BackgroundTasks
) -> AIInteractionResponse:
    """Generate NPC dialogue response to player message"""
    try:
        # Get player and NPC entities
        player = await world_service.get_player(request.player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        npc = await world_service.get_npc(request.npc_id)
        if not npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        # Build context for this interaction
        context_entities, context_metrics = await context_builder.build_npc_interaction_context(
            player=player,
            target_npc=npc,
            player_message=request.player_message
        )
        
        # Generate AI response
        ai_response = await ai_service.generate_npc_dialogue(
            npc=npc,
            player_action=request.player_message,
            context_entities=context_entities,
            situation=request.situation_context or ""
        )
        
        # Create event for this interaction
        event_id = uuid4()
        interaction_event = Event(
            id=event_id,
            name=f"Dialogue between {player.name} and {npc.name}",
            description=f"Player said: '{request.player_message}'",
            action_type=ActionType.DIALOGUE,
            actor_id=request.player_id,
            actor_type=ActorType.PLAYER,
            participants=[request.player_id, request.npc_id],
            location_id=getattr(player, 'current_location_id', None),
            before_state={
                "player_message": request.player_message,
                "npc_mood": npc.current_state.current_mood if npc.current_state else "unknown"
            },
            after_state={
                "npc_response": ai_response.content,
                "confidence": ai_response.confidence,
                "hallucination_detected": ai_response.hallucination_detected
            },
            session_id=request.session_id,
            confidence_score=ai_response.confidence
        )
        
        # Log the interaction in background
        background_tasks.add_task(
            log_ai_interaction, 
            interaction_event, 
            request.player_id
        )
        
        return AIInteractionResponse(
            content=ai_response.content,
            confidence=ai_response.confidence,
            tokens_used=ai_response.tokens_used,
            response_time=ai_response.response_time,
            hallucination_detected=ai_response.hallucination_detected,
            cited_entities=ai_response.cited_entities,
            warnings=ai_response.warnings,
            context_entities_used=len(context_entities),
            event_id=event_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NPC dialogue generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dialogue generation failed: {str(e)}")


@router.post("/world/describe", response_model=AIInteractionResponse)
async def describe_world(
    request: WorldDescriptionRequest, background_tasks: BackgroundTasks
) -> AIInteractionResponse:
    """Generate world/location description based on player request"""
    try:
        # Get player entity
        player = await world_service.get_player(request.player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Build context for exploration
        context_entities, context_metrics = await context_builder.build_world_exploration_context(
            player=player,
            exploration_query=request.request
        )
        
        # Generate description
        ai_response = await ai_service.generate_world_description(
            player=player,
            request=request.request,
            context_entities=context_entities
        )
        
        # Create event for this exploration
        event_id = uuid4()
        exploration_event = Event(
            id=event_id,
            name=f"World exploration by {player.name}",
            description=f"Player requested: '{request.request}'",
            action_type=ActionType.WORLD_CHANGE,
            actor_id=request.player_id,
            actor_type=ActorType.PLAYER,
            participants=[request.player_id],
            location_id=getattr(player, 'current_location_id', None),
            before_state={
                "exploration_request": request.request
            },
            after_state={
                "description_generated": ai_response.content,
                "confidence": ai_response.confidence
            },
            session_id=request.session_id,
            confidence_score=ai_response.confidence
        )
        
        # Log the exploration in background
        background_tasks.add_task(
            log_ai_interaction,
            exploration_event,
            request.player_id
        )
        
        return AIInteractionResponse(
            content=ai_response.content,
            confidence=ai_response.confidence,
            tokens_used=ai_response.tokens_used,
            response_time=ai_response.response_time,
            hallucination_detected=ai_response.hallucination_detected,
            cited_entities=ai_response.cited_entities,
            warnings=ai_response.warnings,
            context_entities_used=len(context_entities),
            event_id=event_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"World description generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Description generation failed: {str(e)}")


@router.get("/context/preview/{player_id}")
async def preview_context(
    player_id: UUID,
    interaction_target_id: Optional[UUID] = None,
    search_query: Optional[str] = None
) -> Dict[str, Any]:
    """Preview what context would be built for a player (debugging/testing)"""
    try:
        player = await world_service.get_player(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        interaction_target = None
        if interaction_target_id:
            interaction_target = await world_service.get_entity(interaction_target_id)
        
        context_entities, metrics = await context_builder.build_optimized_context(
            player=player,
            interaction_target=interaction_target,
            search_query=search_query
        )
        
        return {
            "entities": [
                {
                    "id": str(entity.id),
                    "type": entity.type.value,
                    "name": entity.name,
                    "description": entity.description[:100] + "..." if len(entity.description) > 100 else entity.description
                }
                for entity in context_entities
            ],
            "metrics": {
                "total_entities_found": metrics.total_entities_found,
                "entities_included": metrics.entities_included,
                "tokens_estimated": metrics.tokens_estimated,
                "priority_breakdown": metrics.priority_breakdown,
                "assembly_time": metrics.assembly_time
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Context preview failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context preview failed: {str(e)}")


@router.get("/health")
async def ai_health_check() -> Dict[str, Any]:
    """Check AI service health"""
    try:
        is_healthy = ai_service.is_initialized
        
        return {
            "ai_service_initialized": is_healthy,
            "llm_model": settings.llm_model if is_healthy else None,
            "status": "healthy" if is_healthy else "not_initialized"
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "ai_service_initialized": False,
            "status": "error",
            "error": str(e)
        }


# Background task functions
async def log_ai_interaction(event: Event, actor_id: UUID) -> None:
    """Log AI interaction as background task"""
    try:
        await world_service.create_entity(
            entity=event,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=event.session_id
        )
        logger.info(f"Logged AI interaction event: {event.id}")
    except Exception as e:
        logger.error(f"Failed to log AI interaction: {e}")


# Utility endpoints for AI management
@router.post("/admin/reset-context-cache")
async def reset_context_cache() -> Dict[str, str]:
    """Reset any context caching (admin endpoint)"""
    # For future context caching implementation
    return {"message": "Context cache cleared"}


@router.get("/admin/ai-stats")
async def get_ai_stats() -> Dict[str, Any]:
    """Get AI usage statistics (admin endpoint)"""
    try:
        # Get recent AI-generated events
        recent_ai_events = await world_service.get_recent_changes(
            limit=50,
            actor_types=[ActorType.SYSTEM],
            entity_types=[EntityType.EVENT]
        )
        
        ai_events = [event for event in recent_ai_events if 'confidence' in event.after_state]
        
        if not ai_events:
            return {
                "total_ai_interactions": 0,
                "average_confidence": 0,
                "hallucination_rate": 0,
                "recent_interactions": []
            }
        
        # Calculate statistics
        confidences = [event.after_state.get('confidence', 0) for event in ai_events]
        hallucinations = [event for event in ai_events if event.after_state.get('hallucination_detected', False)]
        
        return {
            "total_ai_interactions": len(ai_events),
            "average_confidence": sum(confidences) / len(confidences),
            "hallucination_rate": len(hallucinations) / len(ai_events),
            "recent_interactions": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "action_type": event.action_type.value,
                    "confidence": event.after_state.get('confidence', 0),
                    "hallucination_detected": event.after_state.get('hallucination_detected', False)
                }
                for event in ai_events[:10]
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get AI stats: {e}")
        raise HTTPException(status_code=500, detail=f"AI stats failed: {str(e)}")