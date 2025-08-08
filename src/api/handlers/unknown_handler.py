"""
Unknown Handler

Handles unknown/unclear commands using AI interpretation
"""

import logging

from fastapi import BackgroundTasks

from api.ai_routes import WorldDescriptionRequest, describe_world

logger = logging.getLogger(__name__)


async def handle_unknown(request, parsed) -> dict:
    """Handle unknown/unclear commands"""
    
    # Let AI try to interpret the command
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=f"I try to: {request.command}",
        session_id=request.session_id
    )
    
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return {
        "success": True,
        "action_type": "unknown",
        "content": ai_response.content,
        "confidence": ai_response.confidence * 0.5,  # Lower confidence for unknown actions
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "parsing_confidence": parsed.confidence,
        "original_command": request.command,
        "warnings": ["Command action type unclear - using general interpretation"]
    }