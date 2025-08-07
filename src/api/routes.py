"""
API routes for Game Master V3
"""
import logging
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.ai_routes import router as ai_router
from api.game_routes import router as game_router
from api.streaming_routes import router as streaming_router
from core.world_service import world_service
from infrastructure.cache_service import cache_service
from domain.entities import (
    ActorType, BaseEntity, EntityType, Player, NPC, Location, Item, Event, Quest
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Include AI routes  
router.include_router(ai_router)

# Include Natural Language Game routes
router.include_router(game_router)

# Include Streaming routes for real-time responses
router.include_router(streaming_router)


# Request/Response models
class CreateEntityRequest(BaseModel):
    entity_data: dict
    entity_type: EntityType
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class UpdateEntityRequest(BaseModel):
    entity_data: dict
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    entity_types: Optional[List[EntityType]] = None
    include_context: bool = False


class CreateRelationshipRequest(BaseModel):
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    properties: Optional[dict] = None
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class EntityResponse(BaseModel):
    entity: dict
    entity_type: str


class SearchResultResponse(BaseModel):
    entity: dict
    score: float


class SnapshotResponse(BaseModel):
    snapshot_id: UUID
    message: str


# Entity CRUD endpoints
@router.post("/entities", response_model=EntityResponse)
async def create_entity(request: CreateEntityRequest):
    """Create a new entity in the world"""
    try:
        # Map entity type to class
        entity_classes = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.EVENT: Event,
            EntityType.QUEST: Quest,
        }
        
        entity_class = entity_classes.get(request.entity_type, BaseEntity)
        entity = entity_class(**request.entity_data)
        
        # Use provided actor_id or generate system actor
        actor_id = request.actor_id or uuid4()
        
        created_entity = await world_service.create_entity(
            entity=entity,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=request.session_id,
        )
        
        return EntityResponse(
            entity=created_entity.dict(),
            entity_type=created_entity.type.value,
        )
        
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}", response_model=Optional[EntityResponse])
async def get_entity(entity_id: UUID, entity_type: Optional[EntityType] = None):
    """Get entity by ID"""
    try:
        entity = await world_service.get_entity(entity_id, entity_type)
        
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return EntityResponse(
            entity=entity.dict(),
            entity_type=entity.type.value,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(entity_id: UUID, request: UpdateEntityRequest):
    """Update an existing entity"""
    try:
        # Get current entity to determine type
        current_entity = await world_service.get_entity(entity_id)
        if not current_entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        # Update entity data
        entity_data = current_entity.dict()
        entity_data.update(request.entity_data)
        
        # Create updated entity instance
        entity_classes = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.EVENT: Event,
            EntityType.QUEST: Quest,
        }
        
        entity_class = entity_classes.get(current_entity.type, BaseEntity)
        updated_entity = entity_class(**entity_data)
        
        # Use provided actor_id or generate system actor
        actor_id = request.actor_id or uuid4()
        
        result = await world_service.update_entity(
            entity=updated_entity,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=request.session_id,
        )
        
        return EntityResponse(
            entity=result.dict(),
            entity_type=result.type.value,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: UUID,
    entity_type: EntityType,
    actor_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
):
    """Delete an entity"""
    try:
        actor_id = actor_id or uuid4()
        
        success = await world_service.delete_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=session_id,
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return {"message": "Entity deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoints
@router.post("/search", response_model=List[SearchResultResponse])
async def search_entities(request: SearchRequest):
    """Search entities by semantic similarity"""
    try:
        results = await world_service.search_entities(
            query=request.query,
            limit=request.limit,
            entity_types=request.entity_types,
            include_graph_context=request.include_context,
        )
        
        return [
            SearchResultResponse(
                entity=entity.dict(),
                score=score,
            )
            for entity, score in results
        ]
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/context", response_model=List[EntityResponse])
async def get_entity_context(
    entity_id: UUID,
    max_depth: int = Query(default=2, ge=1, le=5),
    entity_types: Optional[List[EntityType]] = Query(default=None),
):
    """Get contextual entities related to the given entity"""
    try:
        context_entities = await world_service.get_entity_context(
            entity_id=entity_id,
            max_depth=max_depth,
            entity_types=entity_types,
        )
        
        return [
            EntityResponse(
                entity=entity.dict(),
                entity_type=entity.type.value,
            )
            for entity in context_entities
        ]
        
    except Exception as e:
        logger.error(f"Failed to get context for entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Relationship endpoints
@router.post("/relationships")
async def create_relationship(request: CreateRelationshipRequest):
    """Create a relationship between entities"""
    try:
        actor_id = request.actor_id or uuid4()
        
        success = await world_service.create_relationship(
            from_entity_id=request.from_entity_id,
            to_entity_id=request.to_entity_id,
            relationship_type=request.relationship_type,
            properties=request.properties,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            session_id=request.session_id,
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create relationship")
        
        return {"message": "Relationship created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Snapshot and history endpoints
@router.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshot(created_by: str = "api_user"):
    """Create a world snapshot"""
    try:
        snapshot_id = await world_service.create_world_snapshot(created_by=created_by)
        
        return SnapshotResponse(
            snapshot_id=snapshot_id,
            message="World snapshot created successfully",
        )
        
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshots/{snapshot_id}/rollback")
async def rollback_to_snapshot(snapshot_id: UUID):
    """Rollback world to a previous snapshot"""
    try:
        success = await world_service.rollback_to_snapshot(snapshot_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed")
        
        return {"message": "Rollback initiated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback to snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/history")
async def get_entity_history(entity_id: UUID, limit: int = Query(default=100, ge=1, le=1000)):
    """Get change history for an entity"""
    try:
        history = await world_service.get_entity_history(entity_id, limit)
        
        return [
            {
                "id": str(entry.id),
                "timestamp": entry.timestamp.isoformat(),
                "action_type": entry.action_type.value,
                "actor_type": entry.actor_type.value,
                "actor_id": str(entry.actor_id),
                "before_state": entry.before_state,
                "after_state": entry.after_state,
                "confidence_score": entry.confidence_score,
            }
            for entry in history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get history for entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/changes")
async def get_session_changes(session_id: UUID):
    """Get all changes for a session"""
    try:
        changes = await world_service.get_session_changes(session_id)
        
        return [
            {
                "id": str(entry.id),
                "timestamp": entry.timestamp.isoformat(),
                "entity_type": entry.entity_type.value,
                "entity_id": str(entry.entity_id),
                "action_type": entry.action_type.value,
                "actor_type": entry.actor_type.value,
                "before_state": entry.before_state,
                "after_state": entry.after_state,
                "confidence_score": entry.confidence_score,
            }
            for entry in changes
        ]
        
    except Exception as e:
        logger.error(f"Failed to get changes for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes/recent")
async def get_recent_changes(
    limit: int = Query(default=100, ge=1, le=1000),
    entity_types: Optional[List[EntityType]] = Query(default=None),
):
    """Get recent changes with optional filters"""
    try:
        changes = await world_service.get_recent_changes(
            limit=limit,
            entity_types=entity_types,
        )
        
        return [
            {
                "id": str(entry.id),
                "timestamp": entry.timestamp.isoformat(),
                "entity_type": entry.entity_type.value,
                "entity_id": str(entry.entity_id),
                "action_type": entry.action_type.value,
                "actor_type": entry.actor_type.value,
                "confidence_score": entry.confidence_score,
            }
            for entry in changes
        ]
        
    except Exception as e:
        logger.error(f"Failed to get recent changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache performance statistics"""
    try:
        stats = await cache_service.get_stats()
        return {
            "cache_enabled": stats.get("enabled", False),
            "hit_rate_percent": round(stats.get("hit_rate", 0), 2),
            "memory_usage": stats.get("used_memory_human", "0B"),
            "total_commands": stats.get("total_commands_processed", 0),
            "connected_clients": stats.get("connected_clients", 0),
            "cache_hits": stats.get("keyspace_hits", 0),
            "cache_misses": stats.get("keyspace_misses", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"cache_enabled": False, "error": str(e)}