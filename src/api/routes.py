"""
API routes for Game Master V3
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.ai_routes import router as ai_router
from api.game_routes import router as game_router
from api.streaming_routes import router as streaming_router
from core.world_service import world_service
from core.enrichment.demographics import enrich_city_demographics
from pathlib import Path
import json
from core.worldgen import generate_world
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
    entity_data: Dict[str, Any]
    entity_type: EntityType
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class UpdateEntityRequest(BaseModel):
    entity_data: Dict[str, Any]
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    entity_types: Optional[List[EntityType]] = None
    include_context: bool = False


class DocsIndexRequest(BaseModel):
    docs: List[Dict[str, Any]]  # {id, title, text, tags?}


class DocsSearchRequest(BaseModel):
    query: str
    limit: int = 5
    tags: Optional[List[str]] = None


class CreateRelationshipRequest(BaseModel):
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    properties: Optional[Dict[str, Any]] = None
    actor_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class EntityResponse(BaseModel):
    entity: Dict[str, Any]
    entity_type: str


class SearchResultResponse(BaseModel):
    entity: Dict[str, Any]
    score: float
class WorldGenRequest(BaseModel):
    """Parameters for world generation (MVP)."""
    seed: Optional[str] = None
    grid_size: Optional[int] = None
    water_ratio: Optional[float] = None
    mountain_density: Optional[float] = None
    enable_ai_enrichment: Optional[bool] = True


class WorldEnrichRequest(BaseModel):
    """Parameters for AI enrichment of existing world."""
    world_id: str



class SnapshotResponse(BaseModel):
    snapshot_id: UUID
    message: str


# Entity CRUD endpoints
@router.post("/entities", response_model=EntityResponse)
async def create_entity(request: CreateEntityRequest) -> EntityResponse:
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


@router.get("/entities", response_model=List[EntityResponse])
async def get_entities(
    entity_type: Optional[EntityType] = Query(default=None, description="Filter by entity type"),
    limit: int = Query(default=50, ge=1, le=1000, description="Maximum entities per type")
) -> List[EntityResponse]:
    """Get all entities, optionally filtered by type"""
    try:
        if entity_type:
            # Get entities of specific type
            entities = await world_service.get_entities_by_type(entity_type, limit)
            return [
                EntityResponse(
                    entity=entity.dict(),
                    entity_type=entity.type.value,
                )
                for entity in entities
            ]
        else:
            # Get all entities
            all_entities = await world_service.get_all_entities(limit_per_type=limit)
            
            # Flatten the results
            response = []
            for entity_type, entities in all_entities.items():
                for entity in entities:
                    response.append(EntityResponse(
                        entity=entity.dict(),
                        entity_type=entity.type.value,
                    ))
            
            return response
        
    except Exception as e:
        logger.error(f"Failed to get entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}", response_model=Optional[EntityResponse])
async def get_entity(entity_id: UUID, entity_type: Optional[EntityType] = None) -> EntityResponse:
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
async def update_entity(entity_id: UUID, request: UpdateEntityRequest) -> EntityResponse:
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
) -> Dict[str, Any]:
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
async def search_entities(request: SearchRequest) -> List[SearchResultResponse]:
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


# RAG Docs endpoints
@router.post("/rag/docs/index")
async def index_docs(request: DocsIndexRequest) -> Dict[str, Any]:
    try:
        docs_payload = []
        for d in request.docs:
            doc_id = str(d.get("id"))
            title = d.get("title", "")
            text = d.get("text", "")
            tags = d.get("tags", [])
            docs_payload.append((doc_id, title, text, tags))
        count = await world_service.index_docs(docs_payload)
        return {"indexed": count}
    except Exception as e:
        logger.error(f"Docs index failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/docs/search")
async def search_docs(request: DocsSearchRequest) -> List[Dict[str, Any]]:
    try:
        results = await world_service.search_docs(query=request.query, limit=request.limit, tags=request.tags)
        return [
            {
                "payload": payload,
                "score": score,
            }
            for payload, score in results
        ]
    except Exception as e:
        logger.error(f"Docs search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/context", response_model=List[EntityResponse])
async def get_entity_context(
    entity_id: UUID,
    max_depth: int = Query(default=2, ge=1, le=5),
    entity_types: Optional[List[EntityType]] = Query(default=None),
) -> List[EntityResponse]:
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
async def create_relationship(request: CreateRelationshipRequest) -> Dict[str, Any]:
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
async def create_snapshot(created_by: str = "api_user") -> SnapshotResponse:
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
async def rollback_to_snapshot(snapshot_id: UUID) -> Dict[str, Any]:
    """Rollback the world to a previous snapshot via reverse event replay."""
    try:
        report = await world_service.rollback_to_snapshot(snapshot_id)

        return {
            "message": "Rollback completed",
            "report": report,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rollback to snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}/history")
async def get_entity_history(
    entity_id: UUID, limit: int = Query(default=100, ge=1, le=1000)
) -> List[Dict[str, Any]]:
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
async def get_session_changes(session_id: UUID) -> List[Dict[str, Any]]:
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
) -> List[Dict[str, Any]]:
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


# World generation endpoint (MVP)
@router.post("/world/generate")
async def generate_world_endpoint(req: WorldGenRequest) -> Dict[str, Any]:
    """Generate a minimal macro world and return summary."""
    try:
        summary = await generate_world({k: v for k, v in req.dict().items() if v is not None})
        return {"success": True, "summary": summary}
    except Exception as e:
        logger.error(f"World generation failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/world/enrich")
async def enrich_world_endpoint(req: WorldEnrichRequest) -> Dict[str, Any]:
    """Apply AI enrichment to an existing world."""
    try:
        from core.worldgen.ai_enrichment_service import ai_world_enrichment_service
        
        # Verify world exists
        world_entity = await world_service.get_entity(UUID(req.world_id), EntityType.LOCATION)
        if not world_entity:
            raise HTTPException(status_code=404, detail="World not found")
        
        # Check if already enriched
        if world_entity.metadata and world_entity.metadata.get('enriched_by_ai'):
            logger.warning(f"World {req.world_id} already AI enriched, re-enriching...")
        
        # Build summary from existing world data
        summary = await _build_world_summary_from_existing(req.world_id)
        
        # Apply AI enrichment
        logger.info(f"Starting AI enrichment for world {req.world_id}")
        enriched_summary = await ai_world_enrichment_service.enrich_world_batch(summary, req.world_id)
        
        return {
            "success": True, 
            "message": f"World {req.world_id} successfully enriched with AI",
            "summary": enriched_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"World enrichment failed: {e}")
        return {"success": False, "error": str(e)}


async def _build_world_summary_from_existing(world_id: str) -> Dict[str, Any]:
    """Build world summary from existing entities in the database."""
    try:
        # 1) Verify world exists
        world_entity = await world_service.get_entity(UUID(world_id), EntityType.LOCATION)
        if not world_entity:
            raise ValueError(f"World {world_id} not found")

        # 2) Load all locations and build ancestry index
        all_locations = await world_service.get_entities_by_type(EntityType.LOCATION, limit=100000)
        loc_by_id = {str(ent.id): ent for ent in all_locations}

        def belongs_to_world(ent_id: str) -> bool:
            if ent_id == world_id:
                return False  # skip the world node itself in children sets
            seen = 0
            current = ent_id
            while seen < 16:
                ent = loc_by_id.get(current)
                if not ent or not getattr(ent, "metadata", None):
                    return False
                parent = ent.metadata.get("parent_id")
                if not parent:
                    return False
                if str(parent) == str(world_id):
                    return True
                current = str(parent)
                seen += 1
            return False

        # 3) Collect locations strictly under this world
        summary: Dict[str, Any] = {
            "continents": [],
            "seas": [],
            "regions": [],
            "rivers": [],
            "cities": [],
            "towns": [],
            "villages": [],
            "roads": [],
            "districts": [],
            "streets": [],
            "buildings": [],
            "poi": [],
            "countries": [],
            "npcs": [],
            "bosses": [],
            "npc_races": {},
            "world_id": world_id,
        }

        for ent_id, ent in loc_by_id.items():
            if not belongs_to_world(ent_id):
                continue
            kind = (ent.metadata or {}).get("location_kind", "")
            if kind == "continent":
                summary["continents"].append(ent_id)
            elif kind in ("sea", "ocean"):
                summary["seas"].append(ent_id)
            elif kind == "region":
                summary["regions"].append(ent_id)
            elif kind == "river":
                summary["rivers"].append(ent_id)
            elif kind == "city":
                summary["cities"].append(ent_id)
            elif kind == "town":
                summary["towns"].append(ent_id)
            elif kind == "village":
                summary["villages"].append(ent_id)
            elif kind == "road":
                summary["roads"].append(ent_id)
            elif kind == "district":
                summary["districts"].append(ent_id)
            elif kind == "street":
                summary["streets"].append(ent_id)
            elif kind == "building":
                summary["buildings"].append(ent_id)
            elif kind == "poi":
                summary["poi"].append(ent_id)
            elif kind == "country":
                summary["countries"].append(ent_id)

        # 4) Collect NPCs whose location is in this world's locations
        location_keys = [
            "continents","seas","regions","rivers","cities","towns","villages",
            "roads","districts","streets","buildings","poi","countries"
        ]
        location_ids: set[str] = set()
        for key in location_keys:
            ids = summary.get(key, [])
            if isinstance(ids, list):
                location_ids.update(ids)
        if location_ids:
            all_npcs = await world_service.get_entities_by_type(EntityType.NPC, limit=200000)
            for npc in all_npcs:
                loc_id = None
                try:
                    if hasattr(npc, "current_state") and getattr(npc.current_state, "current_location_id", None):
                        loc_id = str(npc.current_state.current_location_id)
                    elif npc.metadata:
                        loc_id = npc.metadata.get("home_building_id") or npc.metadata.get("home_location_id")
                    if loc_id and str(loc_id) in location_ids:
                        if npc.metadata and npc.metadata.get("threat_level", 0) >= 8:
                            summary["bosses"].append(str(npc.id))
                        else:
                            summary["npcs"].append(str(npc.id))
                except Exception:
                    continue

        # 5) De-duplicate while preserving order
        def _uniq(seq: List[Any]) -> List[Any]:
            return list(dict.fromkeys(seq))
        for key in [
            "continents","seas","regions","rivers","cities","towns","villages",
            "roads","districts","streets","buildings","poi","countries","npcs","bosses"
        ]:
            summary[key] = _uniq(summary[key])

        logger.info(
            f"Built summary for world {world_id}: "
            f"{len(summary['continents'])} continents, "
            f"{len(summary['regions'])} regions, "
            f"{len(summary['cities'])} cities, "
            f"{len(summary['npcs'])} NPCs"
        )

        return summary
        
    except Exception as e:
        logger.error(f"Failed to build world summary: {e}")
        raise


@router.post("/world/enrich/demographics")
async def enrich_demographics(
    seed: Optional[str] = None,
    world_id: Optional[str] = None,
    include_towns: bool = False,
    max_npcs_per_settlement: int = 100,
) -> Dict[str, Any]:
    """Enrich world with race distributions and assign NPC races based on biomes.
    Requires the world to be generated first.
    """
    try:
        result = await enrich_city_demographics(
            seed or "gmv3",
            world_id=world_id,
            include_towns=include_towns,
            max_npcs_per_settlement=max_npcs_per_settlement,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Demographics enrichment failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/world/{world_id}/export")
async def export_world(
    world_id: UUID, max_depth: int = 6, include_npcs: bool = True, save: bool = True
) -> Dict[str, Any]:
    """Export all locations (and NPCs optionally) belonging to a world into a JSON file.

    Traverses the graph from the `world_id` down to depth and collects location IDs,
    then filters NPCs whose current_location_id (or home_* id) belongs to that set.
    """
    try:
        # Approach: scan all locations and filter by ancestry up to world_id via parent_id chain
        world_entity = await world_service.get_entity(world_id)
        if not world_entity:
            return {"success": False, "error": "world not found"}

        all_locations = await world_service.get_entities_by_type(EntityType.LOCATION, limit=100000)
        # Build quick index for ancestry traversal
        loc_by_id = {str(e.id): e for e in all_locations}

        def location_belongs_to_world(ent_id: str) -> bool:
            # Walk up via parent_id until root or world_id
            seen = 0
            current_id = ent_id
            while seen < 12:  # safe guard
                ent = loc_by_id.get(current_id)
                if not ent:
                    return False
                pid = (ent.metadata or {}).get("parent_id")
                if not pid:
                    return False
                if str(pid) == str(world_id):
                    return True
                current_id = str(pid)
                seen += 1
            return False

        locations = [e for e in all_locations if location_belongs_to_world(str(e.id))]
        location_ids = {str(e.id) for e in locations}

        # Collect NPCs optionally
        npcs = []
        if include_npcs:
            all_npcs = await world_service.get_entities_by_type(EntityType.NPC, limit=100000)
            for npc in all_npcs:
                try:
                    loc_id = getattr(getattr(npc, "current_state", None), "current_location_id", None)
                    in_world = False
                    if loc_id and str(loc_id) in location_ids:
                        in_world = True
                    else:
                        md = npc.metadata or {}
                        for key in ("home_building_id", "home_district_id", "home_city_id"):
                            hid = md.get(key)
                            if hid and str(hid) in location_ids:
                                in_world = True
                                break
                    if in_world:
                        npcs.append(npc)
                except Exception:
                    continue

        def _jsonify(obj: Any) -> Any:
            if isinstance(obj, (str, int, float, bool)) or obj is None:
                return obj
            try:
                from uuid import UUID
                from datetime import datetime
                if isinstance(obj, UUID):
                    return str(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
            except Exception:
                pass
            if isinstance(obj, dict):
                return {k: _jsonify(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_jsonify(v) for v in obj]
            if hasattr(obj, 'dict'):
                return _jsonify(obj.dict())
            return str(obj)

        export_obj = {
            "world_id": str(world_id),
            "counts": {
                "locations": len(locations),
                "npcs": len(npcs),
            },
            "locations": [_jsonify(loc) for loc in locations],
            "npcs": [_jsonify(e) for e in npcs],
        }

        saved_path = None
        if save:
            export_dir = Path(__file__).resolve().parents[2] / "world_exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            saved_path = export_dir / f"world_{world_id}.json"
            with saved_path.open("w", encoding="utf-8") as f:
                json.dump(_jsonify(export_obj), f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "saved_path": str(saved_path) if saved_path else None,
            "counts": export_obj["counts"],
        }
    except Exception as e:
        logger.error(f"World export failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
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