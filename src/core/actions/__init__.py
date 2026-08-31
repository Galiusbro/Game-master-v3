"""
Game actions

What a character can do at a table, and the dispatcher that decides which
of them a given utterance means. Nothing here knows about HTTP: a route,
a chat bot or a test all call `execute_command` with the same object.
"""

from .command import GameCommand
from .dispatch import execute_command
from .combat import handle_combat
from .dialogue import handle_dialogue
from .exploration import handle_exploration
from .magic import handle_magic
from .movement import handle_movement
from .resurrection import handle_resurrection
from .search import handle_search
from .skill_check import handle_skill_check
from .trade import handle_trade
from .unknown import handle_unknown

__all__ = [
    "GameCommand",
    "execute_command",
    "handle_combat",
    "handle_dialogue",
    "handle_exploration",
    "handle_magic",
    "handle_movement",
    "handle_resurrection",
    "handle_search",
    "handle_skill_check",
    "handle_trade",
    "handle_unknown",
]
