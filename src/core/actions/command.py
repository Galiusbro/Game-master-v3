"""
The unit of play: one utterance at a table.

Independent of how it arrived — an HTTP request, a message in a group
chat or a test all build the same object.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class GameCommand:
    """Something an actor said or did at a table."""

    world_id: UUID
    # The table this was said at. Every change it causes is tagged with it.
    session_id: UUID
    # Who is acting. Once accounts exist this comes from the caller's
    # identity rather than from whatever the client claims.
    player_id: UUID
    # What they actually said, in their own words.
    text: str
    # Set by a client that is continuing a conversation it started.
    dialogue_context: Optional[Dict[str, Any]] = None
