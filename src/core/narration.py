"""
Narration

Turns a situation into prose and records that it happened. Free of any
transport: an HTTP route, a chat bot or a test calls the same functions
and renders the result however it likes.
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from core.context_builder import context_builder
from core.world_service import world_service
from domain.entities import ActionType, ActorType, Event
from infrastructure.ai_service import ai_service

logger = logging.getLogger(__name__)


class EntityNotFound(LookupError):
    """A referenced entity is not in the world. Transports map this to 404."""


class NarrationResult(BaseModel):
    """One piece of narration and what it cost to produce."""

    content: str
    confidence: float
    tokens_used: int
    response_time: float
    hallucination_detected: bool = False
    cited_entities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    context_entities_used: int = 0
    event_id: Optional[UUID] = None


async def _record(event: Event, actor_id: UUID) -> None:
    """Persist an interaction so later scenes can remember it."""
    try:
        await world_service.create_entity(
            entity=event,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=event.session_id,
        )
        logger.info(f"Logged AI interaction event: {event.id}")
    except Exception as e:
        logger.error(f"Failed to log AI interaction: {e}")


async def npc_dialogue(
    player_id: UUID,
    npc_id: UUID,
    player_message: str,
    situation: str = "",
    session_id: Optional[UUID] = None,
) -> NarrationResult:
    """Have an NPC answer a player, in character and in context."""
    player = await world_service.get_player(player_id)
    if not player:
        raise EntityNotFound("Player not found")

    npc = await world_service.get_npc(npc_id)
    if not npc:
        raise EntityNotFound("NPC not found")

    context_entities, _ = await context_builder.build_npc_interaction_context(
        player=player,
        target_npc=npc,
        player_message=player_message,
    )

    # What the two of them have said to each other recently, so the NPC
    # can carry the thread instead of restarting it every turn.
    history = await world_service.get_dialogue_history(player_id, npc_id)

    ai_response = await ai_service.generate_npc_dialogue(
        npc=npc,
        player_action=player_message,
        context_entities=context_entities,
        situation=situation,
        history=history,
    )

    await world_service.record_dialogue_turn(
        player_id=player_id,
        npc_id=npc_id,
        player_message=player_message,
        npc_response=ai_response.content,
    )

    event_id = uuid4()
    await _record(
        Event(
            id=event_id,
            name=f"Dialogue between {player.name} and {npc.name}",
            description=f"Player said: '{player_message}'",
            action_type=ActionType.DIALOGUE,
            actor_id=player_id,
            actor_type=ActorType.PLAYER,
            participants=[player_id, npc_id],
            location_id=player.current_location_id,
            before_state={
                "player_message": player_message,
                "npc_mood": npc.current_state.current_mood,
            },
            after_state={
                "npc_response": ai_response.content,
                "confidence": ai_response.confidence,
                "hallucination_detected": ai_response.hallucination_detected,
            },
            session_id=session_id,
            confidence_score=ai_response.confidence,
        ),
        actor_id=player_id,
    )

    return NarrationResult(
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        hallucination_detected=ai_response.hallucination_detected,
        cited_entities=ai_response.cited_entities,
        warnings=ai_response.warnings,
        context_entities_used=len(context_entities),
        event_id=event_id,
    )


async def describe_world(
    player_id: UUID,
    request: str,
    session_id: Optional[UUID] = None,
    arriving: bool = False,
) -> NarrationResult:
    """Describe the scene around a player.

    `arriving` marks the one case where the character has just moved here
    and the narration may describe them turning up.
    """
    player = await world_service.get_player(player_id)
    if not player:
        raise EntityNotFound("Player not found")

    context_entities, _ = await context_builder.build_world_exploration_context(
        player=player,
        exploration_query=request,
    )

    ai_response = await ai_service.generate_world_description(
        player=player,
        request=request,
        context_entities=context_entities,
        arriving=arriving,
    )

    event_id = uuid4()
    await _record(
        Event(
            id=event_id,
            name=f"World exploration by {player.name}",
            description=f"Player requested: '{request}'",
            action_type=ActionType.WORLD_CHANGE,
            actor_id=player_id,
            actor_type=ActorType.PLAYER,
            participants=[player_id],
            location_id=player.current_location_id,
            before_state={"exploration_request": request},
            after_state={
                "description_generated": ai_response.content,
                "confidence": ai_response.confidence,
            },
            session_id=session_id,
            confidence_score=ai_response.confidence,
        ),
        actor_id=player_id,
    )

    return NarrationResult(
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        hallucination_detected=ai_response.hallucination_detected,
        cited_entities=ai_response.cited_entities,
        warnings=ai_response.warnings,
        context_entities_used=len(context_entities),
        event_id=event_id,
    )
