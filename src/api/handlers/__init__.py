"""
Game Handlers

This module contains handlers for different types of game actions,
extracted from game_routes.py for better code organization.
"""

from .combat_handler import handle_combat
from .skill_check_handler import handle_skill_check
from .resurrection_handler import handle_resurrection
from .magic_handler import handle_magic
from .unknown_handler import handle_unknown
from .dialogue_handler import handle_dialogue
from .trade_handler import handle_trade
from .movement_handler import handle_movement
from .search_handler import handle_search
from .exploration_handler import handle_exploration

__all__ = [
    "handle_combat",
    "handle_skill_check",
    "handle_resurrection",
    "handle_magic",
    "handle_unknown",
    "handle_dialogue",
    "handle_trade",
    "handle_movement",
    "handle_search",
    "handle_exploration",
]