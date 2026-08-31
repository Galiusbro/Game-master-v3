"""
Trade Handler

Handles trade/commerce actions
"""

import logging
from typing import Any, TYPE_CHECKING


from core import narration

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from core.semantic_parser import ParsedCommand

from core.actions.command import GameCommand

logger = logging.getLogger(__name__)


async def handle_trade(
    command: GameCommand, parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle trade/commerce actions"""
    
    if parsed.target_npc_id:
        # Trade with specific NPC
        trade_message = f"I want to {command.text}"
        
        ai_response = await narration.npc_dialogue(
            player_id=command.player_id,
            npc_id=parsed.target_npc_id,
            player_message=trade_message,
            situation="trade",
            session_id=command.session_id,
            world_id=command.world_id,
        )
        
        return {
            "success": True,
            "action_type": "trade",
            "content": ai_response.content,
            "confidence": ai_response.confidence,
            "tokens_used": ai_response.tokens_used,
            "response_time": ai_response.response_time,
            "resolved_entities": {"npc_id": str(parsed.target_npc_id)},
            "parsing_confidence": parsed.confidence,
            "original_command": command.text,
            "event_id": ai_response.event_id
        }
    else:
        # General trade description - needs exploration handler
        return {
            "success": False,
            "action_type": "trade",
            "content": f"You attempt: {command.text}. The trade details are unclear.",
            "original_command": command.text,
            "warnings": ["No specific NPC found for trade - needs exploration handler"],
            "needs_exploration_handler": True  # Flag to indicate this should go to _handle_exploration
        }