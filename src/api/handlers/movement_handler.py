"""
Movement Handler

Handles movement to location
"""

import logging

from fastapi import BackgroundTasks

from api.ai_routes import WorldDescriptionRequest, describe_world

logger = logging.getLogger(__name__)


async def handle_movement(request, parsed) -> dict:
    """Handle movement to location"""
    
    # Create world description request for movement
    movement_request = f"I want to go to {parsed.intent_details.get('destination', 'somewhere')}. {request.command}"
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=movement_request,
        session_id=request.session_id
    )
    
    # Call AI world description endpoint
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return {
        "success": True,
        "action_type": "movement",
        "content": ai_response.content,
        "confidence": ai_response.confidence,
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "resolved_entities": {
            "target_location": parsed.intent_details.get('destination', 'unknown'),
            "location_id": str(parsed.target_location_id) if parsed.target_location_id else None
        },
        "parsing_confidence": parsed.confidence,
        "original_command": request.command
    }