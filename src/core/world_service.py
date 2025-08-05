"""
World Service for Game Master V3
Central orchestrator for all world operations and data consistency
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from core.event_sourcing import event_store
from domain.entities import (
    ActionType, ActorType, BaseEntity, ChangeLogEntry, EntityType,
    Event, WorldSnapshot
)
from infrastructure.graph_db import graph_db
from infrastructure.vector_db import vector_db
from infrastructure.ai_service import ai_service

logger = logging.getLogger(__name__)


class WorldService:
    """Central service for managing world state and operations"""
    
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize all database connections and AI service"""
        try:
            # Initialize all infrastructure components
            await asyncio.gather(
                graph_db.connect(),
                vector_db.connect(),
                event_store.connect(),
            )
            
            # Initialize AI service if API key is provided
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                try:
                    await ai_service.initialize()
                    logger.info("AI Service initialized successfully")
                except Exception as e:
                    logger.warning(f"AI Service initialization failed (will continue without AI): {e}")
            else:
                logger.info("AI Service skipped (no OpenAI API key provided)")
            
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
                return_exceptions=True,
            )
            logger.info("World Service shutdown complete")
    
    async def create_entity(
        self,
        entity: BaseEntity,
        actor_id: UUID,
        actor_type: ActorType = ActorType.SYSTEM,
        session_id: Optional[UUID] = None,
    ) -> BaseEntity:
        """Create a new entity with full transaction logging"""
        
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
            deleted_from_graph = await graph_db.delete_entity(entity_id)
            
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
    
    async def get_entity(self, entity_id: UUID, entity_type: Optional[EntityType] = None) -> Optional[BaseEntity]:
        """Get entity by ID"""
        return await graph_db.get_entity(entity_id, entity_type)
    
    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_types: Optional[List[EntityType]] = None,
        include_graph_context: bool = False,
    ) -> List[Tuple[BaseEntity, float]]:
        """Search entities with optional graph context expansion"""
        
        # First, semantic search via vector DB
        vector_results = await vector_db.search_entities(
            query=query,
            limit=limit,
            entity_types=entity_types,
        )
        
        if not include_graph_context:
            return vector_results
        
        # Expand results with graph context
        enriched_results = []
        for entity, score in vector_results:
            # Get full entity from graph DB
            full_entity = await graph_db.get_entity(entity.id, entity.type)
            if full_entity:
                enriched_results.append((full_entity, score))
        
        return enriched_results
    
    async def get_entity_context(
        self,
        entity_id: UUID,
        max_depth: int = 2,
        entity_types: Optional[List[EntityType]] = None,
    ) -> List[BaseEntity]:
        """Get contextual entities related to the given entity"""
        
        return await graph_db.traverse_graph(
            start_entity_id=entity_id,
            max_depth=max_depth,
            entity_types=entity_types,
        )
    
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
            success = await graph_db.create_relationship(
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
            snapshot_id = await event_store.create_world_snapshot(
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
        
        if isinstance(data, UUID):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._serialize_uuids_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_uuids_for_json(item) for item in data]
        elif hasattr(data, '__dict__'):
            # Handle objects with dict representation (like enums)
            if hasattr(data, 'value'):
                return data.value
            return str(data)
        else:
            return data
    
    async def rollback_to_snapshot(self, snapshot_id: UUID) -> bool:
        """Rollback world to a previous snapshot"""
        
        try:
            # Get snapshot data
            snapshot = await event_store.get_world_snapshot(snapshot_id)
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            # Log rollback initiation
            await event_store.rollback_to_snapshot(snapshot_id)
            
            # TODO: Implement actual rollback logic
            # This would involve:
            # 1. Clear current world state
            # 2. Restore entities from snapshot
            # 3. Rebuild graph relationships
            # 4. Update vector database
            
            logger.warning("Rollback requested but not fully implemented yet")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback to snapshot {snapshot_id}: {e}")
            raise
    
    async def get_entity_history(self, entity_id: UUID, limit: int = 100) -> List[ChangeLogEntry]:
        """Get change history for an entity"""
        return await event_store.get_entity_history(entity_id, limit)
    
    async def get_session_changes(self, session_id: UUID) -> List[ChangeLogEntry]:
        """Get all changes for a session"""
        return await event_store.get_session_changes(session_id)
    
    async def get_recent_changes(
        self,
        limit: int = 100,
        entity_types: Optional[List[EntityType]] = None,
        actor_types: Optional[List[ActorType]] = None,
    ) -> List[ChangeLogEntry]:
        """Get recent changes with filters"""
        return await event_store.get_recent_changes(
            limit=limit,
            entity_types=entity_types,
            actor_types=actor_types,
        )


# Global world service instance
world_service = WorldService()