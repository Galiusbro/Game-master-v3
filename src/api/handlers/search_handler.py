"""
Search Handler

Rolls an Investigation check and reveals what is actually in the room,
rather than describing a search that never finds anything.
"""

import logging
from typing import Any, List, TYPE_CHECKING

from core.dice_engine import dice_engine
from core.world_service import world_service
from domain.entities import BaseEntity, EntityType, SkillType
from infrastructure.ai_service import ai_service

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from api.game_routes import GameCommandRequest
    from core.semantic_parser import ParsedCommand

logger = logging.getLogger(__name__)


async def _items_in_room(location_id: Any) -> List[BaseEntity]:
    """Items the graph says are in this location."""
    try:
        return await world_service.get_entity_context(
            location_id, max_depth=1, entity_types=[EntityType.ITEM]
        )
    except Exception as e:
        logger.warning(f"Failed to list items in {location_id}: {e}")
        return []


async def handle_search(
    request: "GameCommandRequest", parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle search/investigation actions"""

    target = (parsed.intent_details or {}).get("target", "something")
    warnings: List[str] = []

    player = await world_service.get_player(request.player_id)
    if not player:
        return {
            "success": False,
            "action_type": "search",
            "content": "You cannot search — your character is missing from the world.",
            "original_command": request.command,
            "warnings": ["Player not found"],
        }

    # The dice decide before anything is described.
    dc = dice_engine.determine_difficulty_class(request.command)
    roll = dice_engine.make_skill_check(
        character=player,
        skill=SkillType.INVESTIGATION,
        dc=dc,
        description=f"Searching for {target}",
    )
    player.add_roll_to_history(roll)

    discovered: List[BaseEntity] = []
    already_known: List[BaseEntity] = []

    if roll.is_success and player.current_location_id:
        for item in await _items_in_room(player.current_location_id):
            if item.id in player.known_items:
                already_known.append(item)
            else:
                discovered.append(item)
                player.known_items.append(item.id)

    # Persist the roll history and anything newly noticed. This goes
    # through WorldService, so a discovery lands in the event log and is
    # undone by a rollback like any other change.
    await world_service.update_entity(
        entity=player,
        actor_id=request.player_id,
        session_id=request.session_id,
    )

    if discovered:
        found_text = ", ".join(f"{i.name} ({i.description})" for i in discovered)
        outcome = f"- Found: {found_text}"
    elif roll.is_success and already_known:
        outcome = (
            "- Nothing new: the room holds only what this character has "
            f"already noticed ({', '.join(i.name for i in already_known)})"
        )
    elif roll.is_success:
        outcome = "- The search was thorough, but there is nothing here to find"
    else:
        outcome = "- The search turned up nothing; the character missed whatever is here"

    dice_context = "\n".join([
        "SEARCH RESULT:",
        f"- Action: {request.command}",
        f"- Investigation check: {roll.dice_notation} = {roll.total} vs DC {dc}",
        f"- Result: {'SUCCESS' if roll.is_success else 'FAILURE'}",
        outcome,
    ])

    ai_response = None
    content = dice_context
    try:
        if ai_service.is_initialized:
            ai_response = await ai_service.generate_dice_outcome_narration(
                dice_results=dice_context,
                action_description=request.command,
                player=player,
                context_entities=(parsed.context_entities or []) + discovered,
            )
            content = ai_response.content
        elif discovered:
            content = (
                f"🔍 You search and find: "
                f"{', '.join(i.name for i in discovered)}."
            )
        else:
            content = (
                f"🔍 {roll.total} vs DC {dc} — you find nothing of interest."
            )
    except Exception as e:
        logger.warning(f"AI search narration failed: {e}")
        warnings.append(f"Narration unavailable: {e}")

    return {
        "success": roll.is_success,
        "action_type": "search",
        "content": content,
        "confidence": ai_response.confidence if ai_response else 1.0,
        "tokens_used": ai_response.tokens_used if ai_response else 0,
        "response_time": ai_response.response_time if ai_response else 0.0,
        "resolved_entities": {
            "search_target": target,
            "dc": dc,
            "found": [
                {"id": str(i.id), "name": i.name} for i in discovered
            ],
            "already_known": [i.name for i in already_known],
        },
        "dice_rolls": [{
            "type": roll.description,
            "dice_notation": roll.dice_notation,
            "result": roll.total,
            "dc": dc,
            "success": roll.is_success,
            "is_critical": roll.is_critical,
            "is_fumble": roll.is_fumble,
            "modifiers": roll.modifiers,
            "raw_results": roll.raw_results,
        }],
        "parsing_confidence": parsed.confidence,
        "original_command": request.command,
        "warnings": warnings,
    }
