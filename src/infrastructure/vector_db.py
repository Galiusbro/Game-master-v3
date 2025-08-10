"""
Qdrant Vector Database integration for Game Master V3
Handles semantic search and embeddings for world content
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException
from sentence_transformers import SentenceTransformer

from config.settings import settings
from domain.entities import BaseEntity, EntityType

logger = logging.getLogger(__name__)


class VectorDatabase:
    """Qdrant vector database client for semantic search"""
    
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.encoder: Optional[SentenceTransformer] = None
        self.collection_name = settings.qdrant_collection_name
        self.docs_collection_name = getattr(settings, 'qdrant_docs_collection_name', 'gamemaster_docs')
        self.host = settings.qdrant_host
        self.port = settings.qdrant_port
        self.vector_size = 384  # all-MiniLM-L6-v2 dimension
        
    async def connect(self) -> None:
        """Initialize connection to Qdrant"""
        try:
            self.client = AsyncQdrantClient(
                host=self.host,
                port=self.port,
                timeout=60,
                grpc_port=6334,
                prefer_grpc=False,
            )
            
            # Initialize sentence transformer for embeddings
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create collection if it doesn't exist
            await self._ensure_collection_exists()
            
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Qdrant connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Qdrant")
    
    async def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't exist"""
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            to_create = []
            if self.collection_name not in collection_names:
                to_create.append(self.collection_name)
            if self.docs_collection_name not in collection_names:
                to_create.append(self.docs_collection_name)

            for cname in to_create:
                await self.client.create_collection(
                    collection_name=cname,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {cname}")

            if self.collection_name in collection_names:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
            if self.docs_collection_name in collection_names:
                logger.info(f"Using existing Qdrant collection: {self.docs_collection_name}")
                
        except ResponseHandlingException as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise
    
    def _encode_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.encoder:
            raise RuntimeError("Encoder not initialized")
        
        # Encode text to vector
        embedding = self.encoder.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _entity_to_searchable_text(self, entity: BaseEntity) -> str:
        """Convert entity to searchable text"""
        text_parts = [
            f"Name: {entity.name}",
            f"Type: {entity.type.value}",
            f"Description: {entity.description}",
        ]
        
        # Add entity-specific fields
        if hasattr(entity, 'personality') and entity.personality:
            personality = entity.personality
            text_parts.extend([
                f"Traits: {', '.join(personality.core_traits)}",
                f"Likes: {', '.join(personality.likes)}",
                f"Dislikes: {', '.join(personality.dislikes)}",
                f"Backstory: {personality.backstory}",
            ])
        
        if hasattr(entity, 'current_state') and entity.current_state:
            state = entity.current_state
            text_parts.extend([
                f"Mood: {state.current_mood}",
                f"Activity: {state.current_activity}",
            ])
        
        if hasattr(entity, 'connected_locations'):
            text_parts.append(f"Connected to {len(entity.connected_locations)} locations")
        
        if hasattr(entity, 'item_type'):
            text_parts.append(f"Item type: {entity.item_type.value}")
        
        # Add metadata (strings and short lists)
        for key, value in entity.metadata.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, list) and value and isinstance(value[0], str):
                sample = ", ".join(value[:8])
                text_parts.append(f"{key}: {sample}")
        
        return " | ".join(text_parts)
    
    def _entity_to_payload(self, entity: BaseEntity) -> Dict[str, Any]:
        """Convert entity to Qdrant payload"""
        from uuid import UUID
        
        payload = {
            "entity_id": str(entity.id),
            "entity_type": entity.type.value,
            "name": entity.name,
            "description": entity.description,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
        }
        
        # Safely handle all UUID fields in entity attributes
        for key, value in entity.__dict__.items():
            if isinstance(value, UUID):
                payload[key] = str(value)
            elif value is not None and not key.startswith('_') and key not in payload:
                # Include other relevant fields that are not already in payload
                if isinstance(value, (str, int, float, bool)):
                    payload[key] = value
        
        # Add type-specific fields for filtering
        if entity.type == EntityType.NPC:
            npc = entity
            payload["importance_level"] = getattr(npc, 'importance_level', 1)
            payload["is_alive"] = getattr(npc, 'is_alive', True)
            if hasattr(npc, 'current_state') and npc.current_state:
                payload["current_mood"] = npc.current_state.current_mood
                payload["current_location_id"] = str(npc.current_state.current_location_id) if npc.current_state.current_location_id else None
            # Useful filters
            if isinstance(entity.metadata, dict):
                roles = entity.metadata.get("roles")
                if isinstance(roles, list):
                    payload["roles"] = roles
                caps = entity.metadata.get("capabilities")
                if isinstance(caps, dict):
                    payload["capability_keys"] = list(caps.keys())
        
        elif entity.type == EntityType.LOCATION:
            location = entity
            payload["is_safe"] = getattr(location, 'is_safe', True)
            payload["exploration_level"] = getattr(location, 'exploration_level', 0)
            if isinstance(entity.metadata, dict):
                lk = entity.metadata.get("location_kind")
                if isinstance(lk, str):
                    payload["location_kind"] = lk
                biome = entity.metadata.get("primary_biome")
                if isinstance(biome, str):
                    payload["biome"] = biome
        
        elif entity.type == EntityType.ITEM:
            item = entity
            payload["item_type"] = getattr(item, 'item_type', {}).value if hasattr(getattr(item, 'item_type', {}), 'value') else None
            payload["is_unique"] = getattr(item, 'is_unique', False)
            
            # Safely convert UUID fields to strings
            owner_id = getattr(item, 'owner_id', None)
            payload["owner_id"] = str(owner_id) if owner_id else None
            
            location_id = getattr(item, 'location_id', None)  
            payload["location_id"] = str(location_id) if location_id else None
        
        elif entity.type == EntityType.EVENT:
            event = entity
            payload["action_type"] = getattr(event, 'action_type', {}).value if hasattr(getattr(event, 'action_type', {}), 'value') else None
            
            # Safely convert UUID fields to strings
            actor_id = getattr(event, 'actor_id', None)
            payload["actor_id"] = str(actor_id) if actor_id else None
            payload["confidence_score"] = getattr(event, 'confidence_score', 1.0)
        
        return payload

    async def store_doc(self, doc_id: str, title: str, text: str, tags: Optional[List[str]] = None) -> None:
        """Store a design/lore document chunk into docs collection."""
        embedding = self._encode_text(text)
        # Qdrant expects numeric or UUID IDs; map doc_id to a UUID5
        from uuid import uuid5, NAMESPACE_URL
        safe_id = str(uuid5(NAMESPACE_URL, doc_id))
        payload = {
            "doc_id": doc_id,
            "title": title,
            "tags": tags or [],
            "collection": "docs",
        }
        point = models.PointStruct(id=safe_id, vector=embedding, payload=payload)
        await self.client.upsert(collection_name=self.docs_collection_name, points=[point])
        logger.debug(f"Stored doc in vector DB: {doc_id}")

    async def search_docs(self, query: str, limit: int = 5, tags: Optional[List[str]] = None) -> List[Tuple[Dict[str, Any], float]]:
        """Search in docs collection and return payloads with scores."""
        query_embedding = self._encode_text(query)

        must_conditions = []
        if tags:
            must_conditions.append(
                models.FieldCondition(key="tags", match=models.MatchAny(any=tags))
            )
        search_filter = models.Filter(must=must_conditions) if must_conditions else None

        search_result = await self.client.search(
            collection_name=self.docs_collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
        )

        results: List[Tuple[Dict[str, Any], float]] = []
        for point in search_result:
            results.append((point.payload or {}, point.score))
        return results
    
    async def store_entity(self, entity: BaseEntity) -> None:
        """Store entity in vector database"""
        searchable_text = self._entity_to_searchable_text(entity)
        embedding = self._encode_text(searchable_text)
        payload = self._entity_to_payload(entity)
        
        point = models.PointStruct(
            id=str(entity.id),
            vector=embedding,
            payload=payload,
        )
        
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        
        logger.debug(f"Stored {entity.type} entity in vector DB: {entity.id}")
    
    async def search_entities(
        self,
        query: str,
        limit: int = 10,
        entity_types: Optional[List[EntityType]] = None,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> List[Tuple[BaseEntity, float]]:
        """Search for entities by semantic similarity"""
        query_embedding = self._encode_text(query)
        
        # Build filter conditions
        must_conditions = []
        
        # Filter by entity types
        if entity_types:
            must_conditions.append(
                models.FieldCondition(
                    key="entity_type",
                    match=models.MatchAny(any=[t.value for t in entity_types])
                )
            )
        
        # Add custom filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value)
                        )
                    )
                else:
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
        
        search_filter = None
        if must_conditions:
            search_filter = models.Filter(must=must_conditions)
        
        # Perform search
        search_result = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        
        results = []
        for point in search_result:
            # Convert payload back to entity
            payload = point.payload
            
            # Create minimal entity from payload (for context assembly)
            entity_data = {
                "id": UUID(payload["entity_id"]),
                "type": EntityType(payload["entity_type"]),
                "name": payload["name"],
                "description": payload["description"],
                "metadata": {},
            }
            
            # This is a minimal entity - full entity should be loaded from graph DB
            entity = BaseEntity(**entity_data)
            results.append((entity, point.score))
        
        logger.debug(f"Vector search for '{query}' returned {len(results)} results")
        return results
    
    async def get_similar_entities(
        self,
        entity: BaseEntity,
        limit: int = 5,
        exclude_self: bool = True,
    ) -> List[Tuple[BaseEntity, float]]:
        """Find entities similar to the given entity"""
        searchable_text = self._entity_to_searchable_text(entity)
        query_embedding = self._encode_text(searchable_text)
        
        # Exclude the entity itself if requested
        must_not_conditions = []
        if exclude_self:
            must_not_conditions.append(
                models.FieldCondition(
                    key="entity_id",
                    match=models.MatchValue(value=str(entity.id))
                )
            )
        
        search_filter = None
        if must_not_conditions:
            search_filter = models.Filter(must_not=must_not_conditions)
        
        search_result = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
        )
        
        results = []
        for point in search_result:
            payload = point.payload
            entity_data = {
                "id": UUID(payload["entity_id"]),
                "type": EntityType(payload["entity_type"]),
                "name": payload["name"],
                "description": payload["description"],
                "metadata": {},
            }
            
            similar_entity = BaseEntity(**entity_data)
            results.append((similar_entity, point.score))
        
        return results
    
    async def delete_entity(self, entity_id: UUID) -> None:
        """Delete entity from vector database"""
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[str(entity_id)]
            ),
        )
        logger.debug(f"Deleted entity from vector DB: {entity_id}")
    
    async def update_entity(self, entity: BaseEntity) -> None:
        """Update entity in vector database"""
        # For updates, we just store again (upsert)
        await self.store_entity(entity)


# Global vector database instance
vector_db = VectorDatabase()