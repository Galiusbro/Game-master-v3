"""
Streaming API Routes for Real-time Game Master Responses
Provides Server-Sent Events (SSE) for live AI response streaming
"""
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.world_service import world_service
from infrastructure.ai_service import ai_service
from domain.entities import BaseEntity, EntityType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["streaming"])


class StreamCommandRequest(BaseModel):
    """Request model for streaming game commands"""
    world_id: str = Field(..., description="World identifier")
    session_id: str = Field(..., description="Session identifier")
    player_id: str = Field(..., description="Player identifier")
    command: str = Field(..., description="Player command to execute")


class StreamNPCDialogueRequest(BaseModel):
    """Request model for streaming NPC dialogue"""
    world_id: str = Field(..., description="World identifier")
    npc_id: str = Field(..., description="NPC identifier")
    player_action: str = Field(..., description="Player's action or statement")
    situation: str = Field(default="ongoing conversation", description="Current situation context")


def format_sse_data(data: str, event: str = "message") -> str:
    """Format data for Server-Sent Events"""
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/command")
async def stream_game_command(request: StreamCommandRequest):
    """
    Stream game command response in real-time using Server-Sent Events
    
    This endpoint provides live streaming of AI responses as they are generated,
    giving players immediate feedback without waiting for the complete response.
    """
    try:
        logger.info(f"Streaming command: {request.command[:50]}...")
        
        async def generate_stream():
            try:
                # Send initial status
                yield format_sse_data("Starting command processing...", "status")
                
                # Get relevant entities using semantic search
                yield format_sse_data("Finding relevant entities...", "status")
                search_results = await world_service.search_entities(
                    query=request.command,
                    limit=20,
                    include_graph_context=True
                )
                entities = [entity for entity, score in search_results]
                
                # Build simple context from entities
                yield format_sse_data("Building world context...", "status")
                context = "\n".join([
                    f"- {entity.name}: {entity.description}"
                    for entity in entities[:10]  # Limit context
                ])
                
                # Start streaming response
                yield format_sse_data("Generating response...", "status")
                yield format_sse_data("", "content_start")
                
                # Stream the actual AI response
                async for chunk in ai_service.stream_world_description(
                    request=request.command,
                    context=context,
                    entities=entities
                ):
                    yield format_sse_data(chunk, "content")
                
                # Signal completion
                yield format_sse_data("", "content_end")
                yield format_sse_data("Command processing complete!", "status")
                
            except Exception as e:
                logger.error(f"Streaming command error: {e}")
                yield format_sse_data(f"Error: {str(e)}", "error")
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream command setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to setup streaming: {str(e)}")


@router.post("/npc-dialogue")
async def stream_npc_dialogue(request: StreamNPCDialogueRequest):
    """
    Stream NPC dialogue response in real-time
    
    Provides live streaming of NPC responses as they are generated,
    creating a more natural conversation experience.
    """
    try:
        logger.info(f"Streaming NPC dialogue for NPC: {request.npc_id}")
        
        async def generate_dialogue_stream():
            try:
                # Send initial status
                yield format_sse_data("Initiating dialogue...", "status")
                
                # Get NPC entity
                yield format_sse_data("Loading NPC information...", "status")
                try:
                    from uuid import UUID
                    npc_uuid = UUID(request.npc_id) if isinstance(request.npc_id, str) else request.npc_id
                    npc = await world_service.get_entity(npc_uuid, EntityType.NPC)
                    if not npc:
                        yield format_sse_data("NPC not found", "error")
                        return
                except Exception as e:
                    yield format_sse_data(f"Error loading NPC: {str(e)}", "error")
                    return
                
                # Build conversation context
                yield format_sse_data("Building conversation context...", "status")
                search_results = await world_service.search_entities(
                    query=request.player_action,
                    limit=10,
                    include_graph_context=True
                )
                context_entities = [entity for entity, score in search_results]
                context = "\n".join([
                    f"- {entity.name}: {entity.description}"
                    for entity in context_entities[:5]
                ])
                
                # Start streaming dialogue
                yield format_sse_data(f"{npc.name} responds...", "status")
                yield format_sse_data("", "dialogue_start")
                
                # Stream the NPC dialogue
                async for chunk in ai_service.stream_npc_dialogue(
                    npc=npc,
                    player_action=request.player_action,
                    context=context,
                    situation=request.situation
                ):
                    yield format_sse_data(chunk, "dialogue")
                
                # Signal completion
                yield format_sse_data("", "dialogue_end")
                yield format_sse_data("Dialogue complete!", "status")
                
            except Exception as e:
                logger.error(f"Streaming dialogue error: {e}")
                yield format_sse_data(f"Error: {str(e)}", "error")
        
        return StreamingResponse(
            generate_dialogue_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream dialogue setup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to setup dialogue streaming: {str(e)}")


@router.get("/health")
async def streaming_health():
    """Health check for streaming endpoints"""
    return {"status": "healthy", "streaming": "available"}


# Additional streaming endpoints for future features
@router.post("/world-exploration")
async def stream_world_exploration(
    world_id: str = Query(..., description="World identifier"),
    location: str = Query(..., description="Location to explore"),
    detail_level: str = Query(default="normal", description="Detail level: brief, normal, detailed")
):
    """
    Stream world exploration descriptions
    Future endpoint for detailed area exploration
    """
    async def generate_exploration_stream():
        yield format_sse_data("Exploration streaming not yet implemented", "info")
        yield format_sse_data("This endpoint will provide detailed area descriptions", "info")
    
    return StreamingResponse(
        generate_exploration_stream(),
        media_type="text/event-stream"
    )