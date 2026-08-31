"""
Search Handler

Handles search/investigation actions
"""

import logging
from typing import Any, TYPE_CHECKING

from fastapi import BackgroundTasks

from api.ai_routes import WorldDescriptionRequest, describe_world

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from api.game_routes import GameCommandRequest
    from core.semantic_parser import ParsedCommand

logger = logging.getLogger(__name__)


async def handle_search(
    request: "GameCommandRequest", parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle search/investigation actions"""
    
    search_request = f"I search for {(parsed.intent_details or {}).get('target', 'something')}. {request.command}"
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=search_request,
        session_id=request.session_id
    )
    
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return {
        "success": True,
        "action_type": "search",
        "content": ai_response.content,
        "confidence": ai_response.confidence,
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "resolved_entities": {
            "search_target": (parsed.intent_details or {}).get('target', 'unknown')
        },
        "parsing_confidence": parsed.confidence,
        "original_command": request.command
    }