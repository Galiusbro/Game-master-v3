"""
Exploration Handler

Handles general exploration
"""

import logging

from fastapi import BackgroundTasks

from api.ai_routes import WorldDescriptionRequest, describe_world

logger = logging.getLogger(__name__)


async def handle_exploration(request, parsed) -> dict:
    """Handle general exploration"""
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=request.command,
        session_id=request.session_id
    )
    
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return {
        "success": True,
        "action_type": "exploration",
        "content": ai_response.content,
        "confidence": ai_response.confidence,
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "parsing_confidence": parsed.confidence,
        "original_command": request.command
    }