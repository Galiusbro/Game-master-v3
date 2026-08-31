"""
Unknown Handler

Handles unknown/unclear commands using AI interpretation
"""

import logging
from typing import Any, TYPE_CHECKING


from core import narration

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from core.semantic_parser import ParsedCommand

from core.actions.command import GameCommand

logger = logging.getLogger(__name__)


async def handle_unknown(
    command: GameCommand, parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle unknown/unclear commands"""
    
    # Let AI try to interpret the command
    ai_response = await narration.describe_world(
        player_id=command.player_id,
        request=f"I try to: {command.text}",
        session_id=command.session_id,
        world_id=command.world_id,
    )
    
    return {
        "success": True,
        "action_type": "unknown",
        "content": ai_response.content,
        "confidence": ai_response.confidence * 0.5,  # Lower confidence for unknown actions
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "parsing_confidence": parsed.confidence,
        "original_command": command.text,
        "warnings": ["Command action type unclear - using general interpretation"]
    }