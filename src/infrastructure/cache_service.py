"""
Redis Cache Service for Game Master V3
Provides intelligent caching for database queries and AI responses
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast
from uuid import UUID
import hashlib
from datetime import datetime, timedelta
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel

from config.settings import settings
from domain.entities import BaseEntity, EntityType


logger = logging.getLogger(__name__)


class CacheKey:
    """Cache key patterns for different data types"""
    
    # Entity caching
    ENTITY = "entity:{entity_type}:{entity_id}"
    ENTITY_CONTEXT = "context:{entity_id}:{depth}:{types_hash}"
    
    # Search caching
    VECTOR_SEARCH = "search:vector:{query_hash}:{types}:{limit}"
    GRAPH_TRAVERSAL = "graph:traverse:{start_id}:{depth}:{types_hash}"
    
    # Player data
    PLAYER_STATS = "player:{player_id}:stats"
    PLAYER_RECENT_ROLLS = "player:{player_id}:rolls"
    
    # AI responses (short TTL)
    AI_RESPONSE = "ai:response:{context_hash}"
    DICE_NARRATIVE = "ai:dice:{outcome_hash}"
    
    # Session data
    SESSION = "session:{session_id}"
    SESSION_HISTORY = "session:{session_id}:history"


class CacheService:
    """Redis-based caching service"""
    
    def __init__(self) -> None:
        self.redis: Optional[redis.Redis] = None
        self.enabled = True
        
        # Cache TTL settings (in seconds)
        self.ttl = {
            'entity': 300,           # 5 minutes - entities change infrequently
            'entity_context': 180,   # 3 minutes - context can change
            'player_stats': 300,     # 5 minutes - stats don't change often
            'player_rolls': 600,     # 10 minutes - roll history
            'vector_search': 120,    # 2 minutes - search results
            'graph_traversal': 180,  # 3 minutes - graph results
            'ai_response': 60,       # 1 minute - AI responses (short for freshness)
            'dice_narrative': 300,   # 5 minutes - dice narratives can be reused
            'session': 1800,         # 30 minutes - session data
        }
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle JSON ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            # Test connection
            await self.redis.ping()
            logger.info(f"Connected to Redis at {settings.redis_url}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.enabled = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    def _make_hash(self, data: Union[str, Dict[str, Any], List[Any]]) -> str:
        """Create a stable hash for cache keys"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True, default=str)
        
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _serialize(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        def stringify_keys(obj: Any) -> Any:
            """Recursively convert dict keys to strings and handle special types.
            This prevents JSON errors like 'keys must be str, int, float, bool or None, not UUID'.
            """
            if isinstance(obj, dict):
                new_dict: Dict[str, Any] = {}
                for k, v in obj.items():
                    if isinstance(k, Enum):
                        new_key = str(k.value)
                    else:
                        new_key = str(k)
                    new_dict[new_key] = stringify_keys(v)
                return new_dict
            if isinstance(obj, list):
                return [stringify_keys(v) for v in obj]
            if isinstance(obj, tuple):
                return [stringify_keys(v) for v in obj]
            if isinstance(obj, BaseModel):
                return stringify_keys(obj.dict())
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        payload = stringify_keys(data)
        return json.dumps(payload, ensure_ascii=False).encode()
    
    def _deserialize(self, data: bytes, model_class: Optional[type] = None) -> Any:
        """Deserialize data from Redis"""
        try:
            json_data = json.loads(data.decode())
            if model_class and issubclass(model_class, BaseModel):
                return model_class(**json_data)
            return json_data
        except Exception as e:
            logger.warning(f"Failed to deserialize cache data: {e}")
            return None
    
    async def get(self, key: str, model_class: Optional[type] = None) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                # decode_responses=False guarantees bytes from Redis
                return self._deserialize(cast(bytes, data), model_class)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.enabled or not self.redis:
            return False
        
        try:
            serialized = self._serialize(value)
            result: Any
            if ttl:
                result = await self.redis.setex(key, ttl, serialized)
            else:
                result = await self.redis.set(key, serialized)
            
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self.redis:
            return 0
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                logger.debug(f"Cache DELETE pattern {pattern}: {len(keys)} keys")
                return result
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    # High-level cache methods
    
    async def get_entity(self, entity_id: UUID, entity_type: Optional[EntityType] = None) -> Optional[BaseEntity]:
        """Get cached entity with proper type deserialization"""
        type_str = entity_type.value if entity_type else "*"
        key = CacheKey.ENTITY.format(entity_type=type_str, entity_id=str(entity_id))
        
        # Get raw data
        raw_data = await self.get(key)
        if not raw_data:
            return None
        
        # Determine the correct entity class based on type
        from domain.entities import Player, NPC, Location, Item, Quest
        
        entity_type_from_data = raw_data.get('type')
        if not entity_type_from_data:
            return None
        
        # Map entity types to classes
        type_map: Dict[EntityType, Type[BaseEntity]] = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.QUEST: Quest,
        }
        
        entity_class = type_map.get(EntityType(entity_type_from_data), BaseEntity)
        
        try:
            return entity_class(**raw_data)
        except Exception as e:
            logger.warning(f"Failed to deserialize entity {entity_id} as {entity_class.__name__}: {e}")
            return None
    
    async def set_entity(self, entity: BaseEntity) -> bool:
        """Cache entity"""
        key = CacheKey.ENTITY.format(entity_type=entity.type.value, entity_id=str(entity.id))
        return await self.set(key, entity, self.ttl['entity'])
    
    async def invalidate_entity(self, entity_id: UUID, entity_type: Optional[EntityType] = None) -> None:
        """Invalidate entity cache and related caches"""
        # Delete entity cache
        if entity_type:
            key = CacheKey.ENTITY.format(entity_type=entity_type.value, entity_id=str(entity_id))
            await self.delete(key)
        else:
            # Delete all variants if type unknown
            pattern = CacheKey.ENTITY.format(entity_type="*", entity_id=str(entity_id))
            await self.delete_pattern(pattern)
        
        # Delete related context caches
        context_pattern = CacheKey.ENTITY_CONTEXT.format(entity_id=str(entity_id), depth="*", types_hash="*")
        await self.delete_pattern(context_pattern)
        
        # If it's a player, also invalidate player-specific caches
        if entity_type == EntityType.PLAYER:
            await self.delete_pattern(f"player:{entity_id}:*")
    
    async def get_vector_search(self, query: str, entity_types: Optional[List[EntityType]] = None, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> Optional[List[Tuple[Any, Any]]]:
        """Get cached vector search results"""
        query_hash = self._make_hash({"q": query, "filters": filters or {}})
        types_str = ",".join(sorted([t.value for t in entity_types])) if entity_types else "all"
        
        key = CacheKey.VECTOR_SEARCH.format(
            query_hash=query_hash,
            types=types_str,
            limit=limit
        )
        
        # Get raw data
        raw_results = await self.get(key)
        if not raw_results:
            return None
        
        # Deserialize entities properly
        try:
            from domain.entities import Player, NPC, Location, Item, Quest
            
            type_map: Dict[EntityType, Type[BaseEntity]] = {
                EntityType.PLAYER: Player,
                EntityType.NPC: NPC,
                EntityType.LOCATION: Location,
                EntityType.ITEM: Item,
                EntityType.QUEST: Quest,
            }
            
            deserialized_results: List[Tuple[Any, Any]] = []
            for entity_data, score in raw_results:
                if isinstance(entity_data, dict) and 'type' in entity_data:
                    entity_type = EntityType(entity_data['type'])
                    entity_class = type_map.get(entity_type, BaseEntity)
                    try:
                        entity = entity_class(**entity_data)
                        deserialized_results.append((entity, score))
                    except Exception as e:
                        logger.debug(f"Failed to deserialize search result entity: {e}")
                        continue
                elif hasattr(entity_data, 'id'):
                    # Already an entity object
                    deserialized_results.append((entity_data, score))
            
            return deserialized_results
            
        except Exception as e:
            logger.warning(f"Failed to deserialize vector search cache: {e}")
            return None
    
    async def set_vector_search(self, query: str, entity_types: Optional[List[EntityType]], limit: int, results: List[Any], filters: Optional[Dict[str, Any]] = None) -> bool:
        """Cache vector search results"""
        query_hash = self._make_hash({"q": query, "filters": filters or {}})
        types_str = ",".join(sorted([t.value for t in entity_types])) if entity_types else "all"
        
        key = CacheKey.VECTOR_SEARCH.format(
            query_hash=query_hash,
            types=types_str,
            limit=limit
        )
        return await self.set(key, results, self.ttl['vector_search'])
    
    def _entity_from_cached(self, data: Any) -> Optional[BaseEntity]:
        """Rehydrate one cached record into its typed domain entity.

        Cached payloads are plain JSON, so a cache hit would otherwise hand
        callers dicts where they expect entities.
        """
        if isinstance(data, BaseEntity):
            return data
        if not isinstance(data, dict) or 'type' not in data:
            return None

        from domain.entities import Player, NPC, Location, Item, Quest

        type_map: Dict[EntityType, Type[BaseEntity]] = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC,
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.QUEST: Quest,
        }

        try:
            entity_class = type_map.get(EntityType(data['type']), BaseEntity)
            return entity_class(**data)
        except Exception as e:
            logger.debug(f"Failed to deserialize cached entity: {e}")
            return None

    async def get_entity_context(self, entity_id: UUID, depth: int, entity_types: Optional[List[EntityType]]) -> Optional[List[BaseEntity]]:
        """Get cached entity context"""
        types_hash = self._make_hash(entity_types or [])
        key = CacheKey.ENTITY_CONTEXT.format(
            entity_id=str(entity_id),
            depth=depth,
            types_hash=types_hash
        )
        raw_results = await self.get(key)
        if not raw_results:
            return None

        entities = [e for e in (self._entity_from_cached(d) for d in raw_results) if e is not None]
        return entities or None
    
    async def set_entity_context(self, entity_id: UUID, depth: int, entity_types: Optional[List[EntityType]], results: List[Any]) -> bool:
        """Cache entity context"""
        types_hash = self._make_hash(entity_types or [])
        key = CacheKey.ENTITY_CONTEXT.format(
            entity_id=str(entity_id),
            depth=depth,
            types_hash=types_hash
        )
        return await self.set(key, results, self.ttl['entity_context'])
    
    async def get_ai_response(self, context_hash: str) -> Optional[str]:
        """Get cached AI response"""
        key = CacheKey.AI_RESPONSE.format(context_hash=context_hash)
        return await self.get(key)
    
    async def set_ai_response(self, context_hash: str, response: str) -> bool:
        """Cache AI response"""
        key = CacheKey.AI_RESPONSE.format(context_hash=context_hash)
        return await self.set(key, response, self.ttl['ai_response'])
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled or not self.redis:
            return {"enabled": False}
        
        try:
            info = await self.redis.info()
            return {
                "enabled": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                ) * 100,
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache service instance
cache_service = CacheService()