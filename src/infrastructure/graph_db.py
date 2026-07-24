"""
Neo4j Graph Database integration for Game Master V3
Handles all graph operations and entity relationships
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, TransientError

from config.settings import settings
from domain.entities import (
    BaseEntity, EntityType, Player, NPC, Location, Item, Event, Quest,
    ChangeLogEntry
)

logger = logging.getLogger(__name__)


class GraphDatabase:
    """Neo4j graph database client"""
    
    def __init__(self) -> None:
        self.driver: Optional[AsyncDriver] = None
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.database = settings.neo4j_database
    
    def _serialize_complex_objects(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Convert complex objects to JSON strings for Neo4j storage"""
        import json
        from uuid import UUID
        from datetime import datetime
        from enum import Enum
        
        class UUIDEncoder(json.JSONEncoder):
            def default(self, o: Any) -> Any:
                if isinstance(o, UUID):
                    return str(o)
                elif isinstance(o, datetime):
                    return o.isoformat()
                return super().default(o)

        def stringify(obj: Any) -> Any:
            """Recursively ensure dict keys are strings and convert special types."""
            if isinstance(obj, dict):
                new_dict = {}
                for k, v in obj.items():
                    if isinstance(k, Enum):
                        key = str(k.value)
                    else:
                        key = str(k)
                    new_dict[key] = stringify(v)
                return new_dict
            if isinstance(obj, list):
                return [stringify(v) for v in obj]
            if isinstance(obj, tuple):
                return [stringify(v) for v in obj]
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        serialized: Dict[str, Any] = {}
        for key, value in props.items():
            if isinstance(value, UUID):
                # Convert standalone UUIDs to strings
                serialized[key] = str(value)
            elif isinstance(value, (dict, list)):
                if value:  # Non-empty dict/list
                    safe_value = stringify(value)
                    serialized[key] = json.dumps(safe_value, cls=UUIDEncoder)
                else:  # Empty dict/list - store as null to avoid noisy empty payloads
                    serialized[key] = None
            else:
                serialized[key] = value
        return serialized
    
    def _deserialize_complex_objects(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON strings back to complex objects"""
        import json
        from uuid import UUID
        
        # Fields that should be converted back to UUID
        uuid_fields = {
            'id', 'current_location_id', 'owner_id', 'location_id', 'actor_id', 
            'session_id', 'entity_id', 'from_entity_id', 'to_entity_id'
        }
        
        deserialized = {}
        for key, value in props.items():
            if isinstance(value, str) and value.startswith(('{', '[')):
                try:
                    deserialized[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    deserialized[key] = value
            elif key in uuid_fields and isinstance(value, str) and value:
                # Convert UUID string back to UUID object
                try:
                    deserialized[key] = UUID(value)
                except (ValueError, TypeError):
                    deserialized[key] = value
            else:
                deserialized[key] = value
        return deserialized
    
    async def connect(self) -> None:
        """Initialize connection to Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=30 * 60,  # 30 minutes
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
            # Test connection
            await self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            
            # Initialize schema
            await self._initialize_schema()
            
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get Neo4j session"""
        if not self.driver:
            raise RuntimeError("Database not connected")
        
        session = self.driver.session(database=self.database)
        try:
            yield session
        finally:
            await session.close()
    
    async def _initialize_schema(self) -> None:
        """Create indexes and constraints"""
        constraints_and_indexes = [
            # Unique constraints
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:Player) REQUIRE p.id IS UNIQUE", 
            "CREATE CONSTRAINT npc_id IF NOT EXISTS FOR (n:NPC) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT item_id IF NOT EXISTS FOR (i:Item) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT quest_id IF NOT EXISTS FOR (q:Quest) REQUIRE q.id IS UNIQUE",
            
            # Performance indexes
            "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_created_idx IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
            "CREATE INDEX event_timestamp_idx IF NOT EXISTS FOR (e:Event) ON (e.created_at)",
            "CREATE INDEX npc_importance_idx IF NOT EXISTS FOR (n:NPC) ON (n.importance_level)",
            "CREATE INDEX location_safe_idx IF NOT EXISTS FOR (l:Location) ON (l.is_safe)",
        ]
        
        async with self.session() as session:
            for query in constraints_and_indexes:
                try:
                    await session.run(query)
                    logger.debug(f"Executed: {query}")
                except Exception as e:
                    logger.warning(f"Schema query failed (may already exist): {query} - {e}")
    
    async def create_entity(self, entity: BaseEntity) -> BaseEntity:
        """Create a new entity in the graph"""
        query = f"""
        CREATE (e:{entity.type.value.title()}:Entity $props)
        RETURN e
        """
        
        props = entity.dict(exclude={'type'})
        props['id'] = str(entity.id)
        props['created_at'] = entity.created_at.isoformat()
        props['updated_at'] = entity.updated_at.isoformat()
        
        # Serialize complex objects for Neo4j
        props = self._serialize_complex_objects(props)
        
        async with self.session() as session:
            result = await session.run(query, props=props)
            record = await result.single()
            if not record:
                raise RuntimeError(f"Failed to create entity {entity.id}")
            
            logger.info(f"Created {entity.type} entity: {entity.id}")
            return entity
    
    async def get_entity(self, entity_id: UUID, entity_type: Optional[EntityType] = None) -> Optional[BaseEntity]:
        """Get entity by ID"""
        type_filter = f":{entity_type.value.title()}" if entity_type else ""
        query = f"""
        MATCH (e:Entity{type_filter} {{id: $entity_id}})
        RETURN e, labels(e) as labels
        """
        
        async with self.session() as session:
            result = await session.run(query, entity_id=str(entity_id))
            record = await result.single()
            
            if not record:
                return None
            
            return self._record_to_entity(record)
    
    async def update_entity(self, entity: BaseEntity) -> BaseEntity:
        """Update existing entity"""
        props = entity.dict(exclude={'type', 'id'})
        props['updated_at'] = entity.updated_at.isoformat()
        
        # Serialize complex objects for Neo4j
        props = self._serialize_complex_objects(props)
        
        query = f"""
        MATCH (e:Entity {{id: $entity_id}})
        SET e += $props
        RETURN e
        """
        
        async with self.session() as session:
            result = await session.run(query, entity_id=str(entity.id), props=props)
            record = await result.single()
            
            if not record:
                raise RuntimeError(f"Entity {entity.id} not found for update")
            
            logger.info(f"Updated entity: {entity.id}")
            return entity
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete entity and all its relationships"""
        query = """
        MATCH (e:Entity {id: $entity_id})
        DETACH DELETE e
        RETURN count(e) as deleted_count
        """
        
        async with self.session() as session:
            result = await session.run(query, entity_id=str(entity_id))
            record = await result.single()
            if not record:
                # RETURN count(e) always yields exactly one row
                raise RuntimeError(f"Failed to delete entity {entity_id}")
            deleted: bool = record["deleted_count"] > 0

            if deleted:
                logger.info(f"Deleted entity: {entity_id}")
            return deleted
    
    async def create_relationship(
        self, 
        from_id: UUID, 
        to_id: UUID, 
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create relationship between entities"""
        props = properties or {}
        
        query = f"""
        MATCH (from:Entity {{id: $from_id}})
        MATCH (to:Entity {{id: $to_id}})
        CREATE (from)-[r:{relationship_type} $props]->(to)
        RETURN r
        """
        
        async with self.session() as session:
            result = await session.run(query, from_id=str(from_id), to_id=str(to_id), props=props)
            record = await result.single()
            
            if record:
                logger.debug(f"Created relationship: {from_id} -{relationship_type}-> {to_id}")
                return True
            return False
    
    async def traverse_graph(
        self,
        start_entity_id: UUID,
        max_depth: int = settings.graph_traversal_max_depth,
        relationship_types: Optional[List[str]] = None,
        entity_types: Optional[List[EntityType]] = None
    ) -> List[BaseEntity]:
        """Traverse graph from starting entity"""
        
        # Build the relationship pattern correctly for Neo4j
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_pattern = f"[r:{rel_types}*1..{max_depth}]"
        else:
            rel_pattern = f"[r*1..{max_depth}]"
        
        # Build query - Neo4j doesn't support complex label patterns in MATCH easily
        # So we'll filter after matching all Entity nodes
        query = f"""
        MATCH path = (start:Entity {{id: $start_id}})-{rel_pattern}-(connected:Entity)
        WITH DISTINCT connected, labels(connected) as labels, length(path) as path_length
        RETURN connected AS e, labels AS labels, path_length
        ORDER BY path_length, connected.importance_level DESC, connected.created_at DESC
        LIMIT {settings.graph_traversal_max_width}
        """
        
        entities = []
        async with self.session() as session:
            result = await session.run(query, start_id=str(start_entity_id))
            async for record in result:
                entity = self._record_to_entity(record)
                if entity:
                    # Filter by entity types if specified
                    if entity_types:
                        if entity.type in entity_types:
                            entities.append(entity)
                    else:
                        entities.append(entity)
        
        logger.debug(f"Traversed graph from {start_entity_id}, found {len(entities)} entities")
        return entities
    
    async def get_entities_by_type(self, entity_type: EntityType, limit: int = 100) -> List[BaseEntity]:
        """Get all entities of a specific type"""
        query = f"""
        MATCH (e:{entity_type.value.title()}:Entity)
        RETURN e, labels(e) as labels
        ORDER BY e.created_at DESC
        LIMIT {limit}
        """
        
        entities = []
        async with self.session() as session:
            result = await session.run(query)
            async for record in result:
                entity = self._record_to_entity(record)
                if entity:
                    entities.append(entity)
        
        return entities
    
    def _record_to_entity(self, record: Any) -> Optional[BaseEntity]:
        """Convert Neo4j record to domain entity"""
        node = record["e"]
        labels = record["labels"]
        
        # Determine entity type from labels
        entity_type = None
        for label in labels:
            if label.lower() in [t.value for t in EntityType]:
                entity_type = EntityType(label.lower())
                break
        
        if not entity_type:
            logger.warning(f"Unknown entity type for labels: {labels}")
            return None
        
        # Convert properties
        props = dict(node)
        props['type'] = entity_type
        
        # Fix Neo4j datetime objects - convert to ISO strings for Pydantic
        import neo4j.time
        from datetime import datetime
        
        for key, value in props.items():
            if isinstance(value, neo4j.time.DateTime):
                # Convert Neo4j DateTime to Python datetime, then to ISO string
                dt = datetime(
                    year=value.year,
                    month=value.month, 
                    day=value.day,
                    hour=value.hour,
                    minute=value.minute,
                    second=value.second,
                    microsecond=value.nanosecond // 1000  # Convert nanoseconds to microseconds
                )
                props[key] = dt.isoformat()
        
        # Deserialize complex objects from JSON
        props = self._deserialize_complex_objects(props)
        
        # Map to appropriate entity class
        entity_classes = {
            EntityType.PLAYER: Player,
            EntityType.NPC: NPC, 
            EntityType.LOCATION: Location,
            EntityType.ITEM: Item,
            EntityType.EVENT: Event,
            EntityType.QUEST: Quest,
        }
        
        entity_class = entity_classes.get(entity_type, BaseEntity)
        
        try:
            return entity_class(**props)
        except Exception as e:
            logger.error(f"Failed to create entity from record: {e}")
            logger.error(f"Props were: {props}")
            return None


# Global graph database instance
graph_db = GraphDatabase()