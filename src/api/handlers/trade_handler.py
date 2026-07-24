"""
Trade Handler

Handles trade/commerce actions
"""

import logging
from typing import Any, TYPE_CHECKING

from fastapi import BackgroundTasks

from api.ai_routes import NPCDialogueRequest, npc_dialogue

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from api.game_routes import GameCommandRequest
    from core.semantic_parser import ParsedCommand

logger = logging.getLogger(__name__)


async def handle_trade(
    request: "GameCommandRequest", parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle trade/commerce actions"""
    
    if parsed.target_npc_id:
        # Trade with specific NPC
        trade_message = f"I want to {request.command}"
        
        dialogue_req = NPCDialogueRequest(
            player_id=request.player_id,
            npc_id=parsed.target_npc_id,
            player_message=trade_message,
            situation_context="trade",
            session_id=request.session_id
        )
        
        bg_tasks = BackgroundTasks()
        ai_response = await npc_dialogue(dialogue_req, bg_tasks)
        
        return {
            "success": True,
            "action_type": "trade",
            "content": ai_response.content,
            "confidence": ai_response.confidence,
            "tokens_used": ai_response.tokens_used,
            "response_time": ai_response.response_time,
            "resolved_entities": {"npc_id": str(parsed.target_npc_id)},
            "parsing_confidence": parsed.confidence,
            "original_command": request.command,
            "event_id": ai_response.event_id
        }
    else:
        # General trade description - needs exploration handler
        return {
            "success": False,
            "action_type": "trade",
            "content": f"You attempt: {request.command}. The trade details are unclear.",
            "original_command": request.command,
            "warnings": ["No specific NPC found for trade - needs exploration handler"],
            "needs_exploration_handler": True  # Flag to indicate this should go to _handle_exploration
        }