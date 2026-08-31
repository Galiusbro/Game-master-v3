"""
World Service for Game Master V3
Central orchestrator for all world operations and data consistency
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID, uuid4

from config.settings import settings
from core.event_sourcing import event_store
from domain.entities import (
    NPC, ActionType, ActorType, BaseEntity, ChangeLogEntry, EntityType,
    Event, Location, Player, WorldSnapshot
)
from infrastructure.graph_db import graph_db
from infrastructure.vector_db import vector_db
from infrastructure.ai_service import ai_service
from infrastructure.cache_service import cache_service

logger = logging.getLogger(__name__)


class WorldService:
    """Central service for managing world state and operations"""
    
    def __init__(self) -> None:
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize all database connections and AI service"""
        try:
            # Initialize all infrastructure components
            await asyncio.gather(
                graph_db.connect(),
                vector_db.connect(),
                event_store.connect(),
                cache_service.connect(),
            )
            
            # Initialize AI service if API key is provided
            if settings.llm_api_key:
                try:
                    await ai_service.initialize()
                    logger.info("AI Service initialized successfully")
                except Exception as e:
                    logger.warning(f"AI Service initialization failed (will continue without AI): {e}")
            else:
                logger.info("AI Service skipped (no LLM API key provided)")
            
            self.is_initialized = True
            logger.info("World Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize World Service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all connections"""
        if self.is_initialized:
            await asyncio.gather(
                graph_db.disconnect(),
                vector_db.disconnect(),
                event_store.disconnect(),
                cache_service.disconnect(),
                return_exceptions=True,
            )
            logger.info("World Service shutdown complete")
    
    async def create_entity(
        self,
        entity: BaseEntity,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
        session_id: Optional[UUID] = None,
        world_id: Optional[UUID] = None,
    ) -> BaseEntity:
        """Create a new entity with full transaction logging.

        `world_id` stamps which world the entity belongs to when the entity
        does not already say so. Queries scoped to a world will not return
        anything left unstamped, so callers that know the world should pass
        it.
        """

        if world_id and entity.world_id is None:
            entity.world_id = world_id

        # Create event for this action
        event_id = uuid4()
        
        try:
            # Store in graph database
            created_entity = await graph_db.create_entity(entity)
            
            # Store in vector database for semantic search
            await vector_db.store_entity(created_entity)
            
            # Log the change
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity.type,
                entity_id=entity.id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state={},
                after_state=entity.dict(),
                session_id=session_id,
                confidence_score=1.0,
            )
            
            logger.info(f"Created {entity.type} entity: {entity.id}")
            return created_entity
            
        except Exception as e:
            logger.error(f"Failed to create entity {entity.id}: {e}")
            
            # Log failed attempt
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity.type,
                entity_id=entity.id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state={},
                after_state={"error": str(e)},
                session_id=session_id,
                confidence_score=0.0,
            )
            raise
    
    async def update_entity(
        self,
        entity: BaseEntity,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
        session_id: Optional[UUID] = None,
    ) -> BaseEntity:
        """Update an existing entity with full transaction logging"""
        
        event_id = uuid4()
        
        # Get current state for before_state
        current_entity = await graph_db.get_entity(entity.id, entity.type)
        before_state = current_entity.dict() if current_entity else {}
        
        try:
            # Update in graph database
            updated_entity = await graph_db.update_entity(entity)
            
            # Update in vector database
            await vector_db.update_entity(updated_entity)
            
            # Invalidate related caches
            await cache_service.invalidate_entity(entity.id, entity.type)
            
            # Log the change
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity.type,
                entity_id=entity.id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state=before_state,
                after_state=entity.dict(),
                session_id=session_id,
                confidence_score=1.0,
                rollback_data=before_state,  # For potential rollback
            )
            
            logger.info(f"Updated {entity.type} entity: {entity.id}")
            return updated_entity
            
        except Exception as e:
            logger.error(f"Failed to update entity {entity.id}: {e}")
            
            # Log failed attempt
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity.type,
                entity_id=entity.id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state=before_state,
                after_state={"error": str(e)},
                session_id=session_id,
                confidence_score=0.0,
            )
            raise
    
    async def delete_entity(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
        session_id: Optional[UUID] = None,
    ) -> bool:
        """Delete an entity with full transaction logging"""
        
        event_id = uuid4()
        
        # Get current state for logging
        current_entity = await graph_db.get_entity(entity_id, entity_type)
        before_state = current_entity.dict() if current_entity else {}
        
        try:
            # Delete from graph database
            deleted_from_graph: bool = await graph_db.delete_entity(entity_id)
            
            # Delete from vector database
            await vector_db.delete_entity(entity_id)
            
            # Log the change
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state=before_state,
                after_state={"deleted": True},
                session_id=session_id,
                confidence_score=1.0,
                rollback_data=before_state,  # For potential rollback
            )
            
            logger.info(f"Deleted {entity_type} entity: {entity_id}")
            return deleted_from_graph
            
        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            
            # Log failed attempt
            await event_store.log_change(
                event_id=event_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state=before_state,
                after_state={"error": str(e)},
                session_id=session_id,
                confidence_score=0.0,
            )
            raise
    
    async def get_entity(
        self,
        entity_id: UUID,
        entity_type: Optional[EntityType] = None,
        world_id: Optional[UUID] = None,
    ) -> Optional[BaseEntity]:
        """Get entity by ID with caching, optionally confined to one world"""

        # Try cache first
        cached_entity = await cache_service.get_entity(entity_id, entity_type)
        if cached_entity:
            # The cache is keyed by id alone, so a hit still has to answer
            # for the world it came from.
            if world_id and cached_entity.world_id != world_id:
                return None
            return cached_entity

        # Cache miss - get from database
        entity = await graph_db.get_entity(entity_id, entity_type, world_id=world_id)
        
        # Cache the result if found
        if entity:
            await cache_service.set_entity(entity)
        
        return entity
    
    async def get_player(
        self,
        player_id: UUID,
        world_id: Optional[UUID] = None,
    ) -> Optional[Player]:
        """Get a player by id, or None if missing or not a player.

        get_entity has to return the base type because it serves every
        kind of entity; callers that know what they asked for should use
        these instead of narrowing by hand.
        """
        entity = await self.get_entity(player_id, EntityType.PLAYER, world_id=world_id)
        return entity if isinstance(entity, Player) else None

    async def get_npc(
        self,
        npc_id: UUID,
        world_id: Optional[UUID] = None,
    ) -> Optional[NPC]:
        """Get an NPC by id, or None if missing or not an NPC."""
        entity = await self.get_entity(npc_id, EntityType.NPC, world_id=world_id)
        return entity if isinstance(entity, NPC) else None

    async def get_location(
        self,
        location_id: UUID,
        world_id: Optional[UUID] = None,
    ) -> Optional[Location]:
        """Get a location by id, or None if missing or not a location."""
        entity = await self.get_entity(location_id, EntityType.LOCATION, world_id=world_id)
        return entity if isinstance(entity, Location) else None

    async def get_dialogue_history(
        self,
        player_id: UUID,
        npc_id: UUID,
        limit: int = 6,
        world_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        """Recent exchanges between a player and an NPC.

        Redis holds this for speed, but it is a cache and not the record:
        every exchange is also written to the graph as a dialogue Event.
        On a miss — a restart, a flush, or simply a long enough break —
        the conversation is rebuilt from those events, so an NPC does not
        forget someone it has actually met.
        """
        cached = await cache_service.get_dialogue_history(player_id, npc_id)
        if cached:
            return cached

        history = await self._dialogue_history_from_events(
            player_id, npc_id, limit, world_id
        )
        if history:
            await cache_service.set_dialogue_history(player_id, npc_id, history)
            logger.info(
                f"Rebuilt {len(history)} dialogue turns for {player_id} "
                f"and {npc_id} from the event log"
            )
        return history

    async def _dialogue_history_from_events(
        self,
        player_id: UUID,
        npc_id: UUID,
        limit: int,
        world_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        """Reconstruct a conversation from the durable event log.

        The graph narrows by action type and confidence; participants are
        matched here, on the typed entities, because they are stored as a
        JSON string rather than an array.
        """
        try:
            events = await graph_db.get_recent_events(
                action_type=ActionType.DIALOGUE,
                min_confidence=0.0,
                limit=max(limit * 10, 50),
                world_id=world_id,
            )
        except Exception as e:
            logger.warning(f"Could not read dialogue events: {e}")
            return []

        turns: List[Tuple[datetime, Dict[str, str]]] = []
        for event in events:
            if not isinstance(event, Event):
                continue
            participants = set(event.participants)
            if player_id not in participants or npc_id not in participants:
                continue

            said = (event.before_state or {}).get("player_message")
            replied = (event.after_state or {}).get("npc_response")
            if not said or not replied:
                continue

            turns.append((event.created_at, {"player": said, "npc": replied}))

        turns.sort(key=lambda item: item[0])
        return [turn for _, turn in turns[-limit:]]

    async def record_dialogue_turn(
        self, player_id: UUID, npc_id: UUID, player_message: str, npc_response: str
    ) -> None:
        """Add one exchange to the cached conversation."""
        await cache_service.append_dialogue_turn(
            player_id=player_id,
            npc_id=npc_id,
            player_message=player_message,
            npc_response=npc_response,
        )

    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_types: Optional[List[EntityType]] = None,
        include_graph_context: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        world_id: Optional[UUID] = None,
    ) -> List[Tuple[BaseEntity, float]]:
        """Search entities with optional graph context expansion.

        `world_id` rides the existing payload filter: every entity stores
        it, so confining a search to one world costs nothing extra.
        """
        if world_id:
            filters = {**(filters or {}), "world_id": str(world_id)}
        
        # Try cache first (for simple searches without graph context)
        if not include_graph_context:
            cached_results: Optional[List[Tuple[BaseEntity, float]]] = await cache_service.get_vector_search(query, entity_types, limit, filters)
            if cached_results:
                return cached_results

        # Cache miss - perform search
        vector_results: List[Tuple[BaseEntity, float]] = await vector_db.search_entities(
            query=query,
            limit=limit,
            entity_types=entity_types,
            filters=filters,
        )
        
        # Cache simple search results
        if not include_graph_context:
            await cache_service.set_vector_search(query, entity_types, limit, vector_results, filters)
        
        if not include_graph_context:
            return vector_results
        
        # Expand results with graph context
        enriched_results = []
        for entity, score in vector_results:
            # Get full entity from graph DB, staying inside the same world
            full_entity = await graph_db.get_entity(
                entity.id, entity.type, world_id=world_id
            )
            if full_entity:
                enriched_results.append((full_entity, score))
        
        return enriched_results

    async def index_docs(self, docs: List[Tuple[str, str, str, List[str]]]) -> int:
        """Index RAG documents into the docs collection.

        docs: list of (doc_id, title, text, tags)
        returns number of indexed docs
        """
        count = 0
        for doc_id, title, text, tags in docs:
            try:
                await vector_db.store_doc(doc_id=doc_id, title=title, text=text, tags=tags)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to index doc {doc_id}: {e}")
        return count

    async def search_docs(self, query: str, limit: int = 5, tags: Optional[List[str]] = None) -> Any:
        return await vector_db.search_docs(query=query, limit=limit, tags=tags)
    
    async def get_entity_context(
        self,
        entity_id: UUID,
        max_depth: int = 2,
        entity_types: Optional[List[EntityType]] = None,
        world_id: Optional[UUID] = None,
    ) -> List[BaseEntity]:
        """Get contextual entities related to the given entity with caching"""
        
        # Try cache first
        cached_context: Optional[List[BaseEntity]] = await cache_service.get_entity_context(entity_id, max_depth, entity_types)
        if cached_context:
            return cached_context

        # Cache miss - get from graph DB
        context_entities: List[BaseEntity] = await graph_db.traverse_graph(
            start_entity_id=entity_id,
            max_depth=max_depth,
            entity_types=entity_types,
            world_id=world_id,
        )
        
        # Cache the results
        await cache_service.set_entity_context(entity_id, max_depth, entity_types, context_entities)
        
        return context_entities
    
    async def get_entities_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100,
        world_id: Optional[UUID] = None,
    ) -> List[BaseEntity]:
        """Get all entities of a specific type"""
        try:
            entities: List[BaseEntity] = await graph_db.get_entities_by_type(
                entity_type, limit, world_id=world_id
            )
            logger.debug(f"Retrieved {len(entities)} {entity_type.value} entities")
            return entities
        except Exception as e:
            logger.error(f"Failed to get entities by type {entity_type}: {e}")
            raise
    
    async def get_all_entities(
        self,
        entity_types: Optional[List[EntityType]] = None,
        limit_per_type: int = 50
    ) -> Dict[EntityType, List[BaseEntity]]:
        """Get all entities, optionally filtered by type"""
        try:
            if entity_types is None:
                entity_types = list(EntityType)
            
            all_entities = {}
            for entity_type in entity_types:
                entities = await self.get_entities_by_type(entity_type, limit_per_type)
                all_entities[entity_type] = entities
            
            logger.debug(f"Retrieved entities: {sum(len(entities) for entities in all_entities.values())} total")
            return all_entities
            
        except Exception as e:
            logger.error(f"Failed to get all entities: {e}")
            raise
    
    async def create_relationship(
        self,
        from_entity_id: UUID,
        to_entity_id: UUID,
        relationship_type: str,
        actor_id: UUID,
        properties: Optional[Dict[str, Any]] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        session_id: Optional[UUID] = None,
    ) -> bool:
        """Create relationship between entities with logging"""
        
        event_id = uuid4()
        
        try:
            success: bool = await graph_db.create_relationship(
                from_id=from_entity_id,
                to_id=to_entity_id,
                relationship_type=relationship_type,
                properties=properties,
            )
            
            # Log the relationship creation
            await event_store.log_change(
                event_id=event_id,
                entity_type=EntityType.EVENT,  # Special type for relationships
                entity_id=event_id,  # Use event ID as entity ID
                action_type=ActionType.WORLD_CHANGE,
                actor_type=actor_type,
                actor_id=actor_id,
                before_state={},
                after_state={
                    "relationship_type": relationship_type,
                    "from_entity": str(from_entity_id),
                    "to_entity": str(to_entity_id),
                    "properties": properties or {},
                },
                session_id=session_id,
                confidence_score=1.0,
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            raise
    
    async def create_world_snapshot(
        self,
        created_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Create a complete snapshot of world state"""
        
        try:
            # Get all entities from graph DB
            all_entities = {}
            
            for entity_type in EntityType:
                entities = await graph_db.get_entities_by_type(entity_type, limit=10000)
                # Convert entities to dicts and serialize UUIDs
                serialized_entities = []
                for entity in entities:
                    entity_dict = entity.dict()
                    # Convert UUID objects to strings for JSON serialization
                    entity_dict = self._serialize_uuids_for_json(entity_dict)
                    serialized_entities.append(entity_dict)
                all_entities[entity_type.value] = serialized_entities
            
            # Create snapshot data
            snapshot_data = {
                "entities": all_entities,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            
            # Store snapshot
            snapshot_id: UUID = await event_store.create_world_snapshot(
                snapshot_data=snapshot_data,
                created_by=created_by,
                metadata=metadata,
            )
            
            logger.info(f"Created world snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to create world snapshot: {e}")
            raise
    
    def _serialize_uuids_for_json(self, data: Any) -> Any:
        """Recursively convert UUID and datetime objects to strings for JSON serialization"""
        from uuid import UUID
        from datetime import datetime
        from enum import Enum

        if isinstance(data, UUID):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            # Keys need converting too: NPC state maps player UUIDs to
            # dispositions and cooldowns, and JSONB rejects non-string keys.
            return {
                str(key.value) if isinstance(key, Enum) else str(key):
                    self._serialize_uuids_for_json(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._serialize_uuids_for_json(item) for item in data]
        elif hasattr(data, '__dict__'):
            # Handle objects with dict representation (like enums)
            if hasattr(data, 'value'):
                return data.value
            return str(data)
        else:
            return data
    
    async def rollback_to_snapshot(self, snapshot_id: UUID) -> Dict[str, Any]:
        """Rollback the world to a previous snapshot by reverse event replay.

        Every mutation goes through this service and is logged with
        before/after state (updates and deletes also carry rollback_data),
        so rolling back means walking the event log since the snapshot in
        reverse and applying the inverse of each change to the graph and
        vector stores:

        - CREATE  -> delete the entity
        - UPDATE  -> restore the pre-update state
        - DELETE  -> re-create the entity from rollback_data

        The replay is best-effort per event: a failure to revert one event
        is recorded and the replay continues, so a single corrupt entry
        cannot brick the whole rollback. Returns a report with counts and
        any per-event errors.
        """

        snapshot = await event_store.get_world_snapshot(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")

        # Mark the rollback in the event log before mutating anything.
        await event_store.rollback_to_snapshot(snapshot_id)

        changes = await event_store.get_changes_since_snapshot(snapshot["timestamp"])

        report: Dict[str, Any] = {
            "snapshot_id": str(snapshot_id),
            "events_seen": len(changes),
            "reverted_creates": 0,
            "reverted_updates": 0,
            "restored_deletes": 0,
            "skipped": 0,
            "errors": [],
        }

        for change in reversed(changes):
            try:
                # System/bookkeeping events and failed attempts are not
                # world mutations — nothing to revert.
                if change.entity_type == EntityType.EVENT or change.confidence_score == 0.0:
                    report["skipped"] += 1
                    continue

                before = change.before_state or {}
                after = change.after_state or {}

                if "error" in after:
                    report["skipped"] += 1
                    continue

                is_delete = after.get("deleted") is True
                is_create = not before and not is_delete
                is_update = bool(before) and not is_delete

                if is_create:
                    await graph_db.delete_entity(change.entity_id)
                    await vector_db.delete_entity(change.entity_id)
                    await cache_service.invalidate_entity(change.entity_id, change.entity_type)
                    report["reverted_creates"] += 1

                elif is_delete:
                    restored = self._entity_from_state(
                        change.rollback_data or before, change.entity_type
                    )
                    if restored is None:
                        raise ValueError("cannot reconstruct entity from rollback_data")
                    await graph_db.create_entity(restored)
                    await vector_db.store_entity(restored)
                    report["restored_deletes"] += 1

                elif is_update:
                    restored = self._entity_from_state(
                        change.rollback_data or before, change.entity_type
                    )
                    if restored is None:
                        raise ValueError("cannot reconstruct entity from rollback_data")
                    await graph_db.update_entity(restored)
                    await vector_db.update_entity(restored)
                    await cache_service.invalidate_entity(change.entity_id, change.entity_type)
                    report["reverted_updates"] += 1

                else:
                    report["skipped"] += 1

            except Exception as e:  # best-effort: record and continue
                logger.error(f"Rollback: failed to revert event {change.id}: {e}")
                report["errors"].append({"event": str(change.id), "error": str(e)})

        # Record the completed rollback with its report.
        await event_store.log_change(
            event_id=uuid4(),
            entity_type=EntityType.EVENT,
            entity_id=snapshot_id,
            action_type=ActionType.WORLD_CHANGE,
            actor_type=ActorType.SYSTEM,
            actor_id=snapshot_id,
            before_state={"action": "rollback_completed"},
            after_state={
                k: v for k, v in report.items() if k != "errors"
            } | {"error_count": len(report["errors"])},
            confidence_score=1.0,
        )

        logger.info(
            "Rollback to %s complete: %d creates reverted, %d updates reverted, "
            "%d deletes restored, %d skipped, %d errors",
            snapshot_id,
            report["reverted_creates"],
            report["reverted_updates"],
            report["restored_deletes"],
            report["skipped"],
            len(report["errors"]),
        )
        return report

    def _entity_from_state(
        self, state: Dict[str, Any], entity_type: EntityType
    ) -> Optional[BaseEntity]:
        """Reconstruct a typed domain entity from an event-log state dict."""
        if not state:
            return None

        from domain.entities import NPC, Event, Item, Location, Player, Quest

        entity_classes: Dict[EntityType, Type[BaseEntity]] = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.EVENT: Event,
            EntityType.QUEST: Quest,
        }
        entity_class = entity_classes.get(entity_type, BaseEntity)

        try:
            return entity_class(**state)
        except Exception as e:
            logger.error(f"Failed to reconstruct {entity_type} from state: {e}")
            return None
    
    async def get_entity_history(self, entity_id: UUID, limit: int = 100) -> List[ChangeLogEntry]:
        """Get change history for an entity"""
        history: List[ChangeLogEntry] = await event_store.get_entity_history(entity_id, limit)
        return history

    async def get_session_changes(self, session_id: UUID) -> List[ChangeLogEntry]:
        """Get all changes for a session"""
        changes: List[ChangeLogEntry] = await event_store.get_session_changes(session_id)
        return changes

    async def get_recent_changes(
        self,
        limit: int = 100,
        entity_types: Optional[List[EntityType]] = None,
        actor_types: Optional[List[ActorType]] = None,
    ) -> List[ChangeLogEntry]:
        """Get recent changes with filters"""
        recent: List[ChangeLogEntry] = await event_store.get_recent_changes(
            limit=limit,
            entity_types=entity_types,
            actor_types=actor_types,
        )
        return recent


# Global world service instance
world_service = WorldService()