"""
Movement Handler

Moves the player between locations and describes what they arrive to.
"""

import logging
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID


from core import narration
from core.world_service import world_service
from domain.entities import BaseEntity, EntityType, Location, Player

if TYPE_CHECKING:
    # Imported for type annotations only (runtime import would be circular).
    from core.semantic_parser import ParsedCommand

from core.actions.command import GameCommand

logger = logging.getLogger(__name__)


async def _resolve_destination(
    parsed: "ParsedCommand", command: str
) -> Optional[BaseEntity]:
    """Find the location the player is heading for.

    The parser resolves obvious mentions; anything vaguer ("to the smithy
    across the square") falls back to semantic search over locations.
    """
    if parsed.target_location_id:
        location = await world_service.get_location(parsed.target_location_id)
        if location:
            return location

    query = (parsed.intent_details or {}).get("destination") or command
    try:
        results = await world_service.search_entities(
            query=query,
            limit=1,
            entity_types=[EntityType.LOCATION],
        )
        if results:
            return results[0][0]
    except Exception as e:
        logger.warning(f"Semantic fallback for destination failed: {e}")

    return None


async def handle_movement(
    command: GameCommand, parsed: "ParsedCommand"
) -> dict[str, Any]:
    """Handle movement to location"""

    warnings: list[str] = []

    player = await world_service.get_player(command.player_id, world_id=command.world_id)
    if not isinstance(player, Player):
        return {
            "success": False,
            "action_type": "movement",
            "content": "You cannot move — your character is missing from the world.",
            "original_command": command.text,
            "warnings": ["Player not found"],
        }

    origin_id: Optional[UUID] = getattr(player, "current_location_id", None)
    destination = await _resolve_destination(parsed, command.text)

    if not destination:
        return {
            "success": False,
            "action_type": "movement",
            "content": "You look around, but nothing here matches where you meant to go.",
            "original_command": command.text,
            "resolved_entities": {"from_location": str(origin_id) if origin_id else None},
            "parsing_confidence": parsed.confidence,
            "warnings": ["No destination resolved from command"],
        }

    if origin_id and destination.id == origin_id:
        warnings.append("Already at destination")
    else:
        # The world graph is sparser than the fiction: a location with no
        # recorded exits should not trap the player, so an unconnected move
        # is reported rather than refused.
        found_origin = (
            await world_service.get_location(origin_id)
            if origin_id
            else None
        )
        origin = found_origin if isinstance(found_origin, Location) else None
        connections = origin.connected_locations if origin else []
        if origin is not None and connections and destination.id not in connections:
            warnings.append(
                f"No recorded route from {origin.name} to {destination.name}"
            )

        # Persist the move through WorldService so it lands in the event log
        # and can be rolled back like any other change.
        player.current_location_id = destination.id
        await world_service.update_entity(
            entity=player,
            actor_id=command.player_id,
            session_id=command.session_id,
        )
        logger.info(
            f"🚶 {player.name} moved {origin.name if origin else 'nowhere'} -> {destination.name}"
        )

    # Describe what the player arrives to, not the journey.
    ai_response = await narration.describe_world(
        player_id=command.player_id,
        request=f"I have just arrived at {destination.name}. {command.text}",
        session_id=command.session_id,
        arriving=True,
    )

    return {
        "success": True,
        "action_type": "movement",
        "content": ai_response.content,
        "confidence": ai_response.confidence,
        "tokens_used": ai_response.tokens_used,
        "response_time": ai_response.response_time,
        "resolved_entities": {
            "from_location": str(origin_id) if origin_id else None,
            "to_location": str(destination.id),
            "to_location_name": destination.name,
            "moved": destination.id != origin_id,
        },
        "parsing_confidence": parsed.confidence,
        "original_command": command.text,
        "warnings": warnings + list(ai_response.warnings or []),
        "event_id": ai_response.event_id,
    }
