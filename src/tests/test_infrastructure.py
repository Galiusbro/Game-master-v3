"""
Tests for Infrastructure components
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from infrastructure.graph_db import GraphDatabase
from infrastructure.vector_db import VectorDatabase  
from core.event_sourcing import EventStore
from domain.entities import EntityType, Location, NPC, ActionType, ActorType


class TestGraphDatabase:
    """Test Neo4j Graph Database integration"""
    
    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver"""
        driver = AsyncMock()
        session = AsyncMock()
        driver.session.return_value.__aenter__.return_value = session
        driver.session.return_value.__aexit__.return_value = None
        return driver, session
    
    @pytest.mark.integration
    async def test_connection(self, mock_driver):
        """Test database connection"""
        driver, session = mock_driver
        
        with patch('infrastructure.graph_db.AsyncGraphDatabase') as mock_graph_db:
            mock_graph_db.driver.return_value = driver
            
            graph_db = GraphDatabase()
            await graph_db.connect()
            
            assert graph_db.driver == driver
            driver.verify_connectivity.assert_called_once()
    
    @pytest.mark.integration  
    async def test_create_entity(self, mock_driver, sample_location):
        """Test entity creation in graph database"""
        driver, session = mock_driver
        
        # Mock session context manager
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        driver.session.return_value = session
        
        # Mock query result
        mock_record = MagicMock()
        session.run.return_value.single.return_value = mock_record
        
        graph_db = GraphDatabase()
        graph_db.driver = driver
        
        result = await graph_db.create_entity(sample_location)
        
        assert result == sample_location
        session.run.assert_called_once()
    
    @pytest.mark.integration
    async def test_get_entity(self, mock_driver, sample_location):
        """Test entity retrieval"""
        driver, session = mock_driver
        
        # Mock session and result
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        driver.session.return_value = session
        
        mock_record = {
            "e": {
                "id": str(sample_location.id),
                "name": sample_location.name,
                "description": sample_location.description,
                "type": sample_location.type.value
            },
            "labels": ["Location", "Entity"]
        }
        session.run.return_value.single.return_value = mock_record
        
        graph_db = GraphDatabase()
        graph_db.driver = driver
        graph_db._record_to_entity = MagicMock(return_value=sample_location)
        
        result = await graph_db.get_entity(sample_location.id, EntityType.LOCATION)
        
        assert result == sample_location
        session.run.assert_called_once()
    
    @pytest.mark.integration
    async def test_traverse_graph(self, mock_driver, sample_location):
        """Test graph traversal"""
        driver, session = mock_driver
        
        # Mock session
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        driver.session.return_value = session
        
        # Mock async iteration
        async def mock_iterate():
            yield {"e": {}, "labels": ["Location", "Entity"]}
        
        session.run.return_value.__aiter__ = mock_iterate
        
        graph_db = GraphDatabase()
        graph_db.driver = driver
        graph_db._record_to_entity = MagicMock(return_value=sample_location)
        
        results = await graph_db.traverse_graph(
            start_entity_id=sample_location.id,
            max_depth=2
        )
        
        assert len(results) == 1
        assert results[0] == sample_location


class TestVectorDatabase:
    """Test Qdrant Vector Database integration"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client"""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock sentence transformer"""
        encoder = MagicMock()
        encoder.encode.return_value = [0.1, 0.2, 0.3] * 128  # 384 dimensions
        return encoder
    
    @pytest.mark.integration
    async def test_connection(self, mock_qdrant_client, mock_sentence_transformer):
        """Test vector database connection"""
        with patch('infrastructure.vector_db.AsyncQdrantClient', return_value=mock_qdrant_client), \
             patch('infrastructure.vector_db.SentenceTransformer', return_value=mock_sentence_transformer):
            
            # Mock collections response
            mock_collections = MagicMock()
            mock_collections.collections = [MagicMock(name="existing_collection")]
            mock_qdrant_client.get_collections.return_value = mock_collections
            
            vector_db = VectorDatabase()
            await vector_db.connect()
            
            assert vector_db.client == mock_qdrant_client
            assert vector_db.encoder == mock_sentence_transformer
    
    @pytest.mark.integration
    async def test_store_entity(self, mock_qdrant_client, mock_sentence_transformer, sample_location):
        """Test storing entity in vector database"""
        vector_db = VectorDatabase()
        vector_db.client = mock_qdrant_client
        vector_db.encoder = mock_sentence_transformer
        
        await vector_db.store_entity(sample_location)
        
        # Verify encoding was called
        mock_sentence_transformer.encode.assert_called_once()
        
        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called_once()
    
    @pytest.mark.integration
    async def test_search_entities(self, mock_qdrant_client, mock_sentence_transformer, sample_location):
        """Test searching entities"""
        vector_db = VectorDatabase()
        vector_db.client = mock_qdrant_client
        vector_db.encoder = mock_sentence_transformer
        
        # Mock search result
        mock_point = MagicMock()
        mock_point.score = 0.95
        mock_point.payload = {
            "entity_id": str(sample_location.id),
            "entity_type": sample_location.type.value,
            "name": sample_location.name,
            "description": sample_location.description
        }
        mock_qdrant_client.search.return_value = [mock_point]
        
        results = await vector_db.search_entities(
            query="tavern",
            limit=10,
            entity_types=[EntityType.LOCATION]
        )
        
        assert len(results) == 1
        entity, score = results[0]
        assert score == 0.95
        assert entity.name == sample_location.name
    
    @pytest.mark.integration
    async def test_entity_to_searchable_text(self, sample_npc):
        """Test converting entity to searchable text"""
        vector_db = VectorDatabase()
        
        searchable_text = vector_db._entity_to_searchable_text(sample_npc)
        
        assert sample_npc.name in searchable_text
        assert sample_npc.description in searchable_text
        assert sample_npc.type.value in searchable_text
        # Should include personality traits
        for trait in sample_npc.personality.core_traits:
            assert trait in searchable_text


class TestEventStore:
    """Test PostgreSQL Event Store"""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock SQLAlchemy engine"""
        engine = AsyncMock()
        return engine
    
    @pytest.fixture
    def mock_session(self):
        """Mock SQLAlchemy session"""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session
    
    @pytest.mark.integration
    async def test_connection(self, mock_engine, mock_session):
        """Test event store connection"""
        with patch('core.event_sourcing.create_async_engine', return_value=mock_engine), \
             patch('core.event_sourcing.async_sessionmaker', return_value=mock_session):
            
            event_store = EventStore()
            await event_store.connect()
            
            assert event_store.engine == mock_engine
            assert event_store.async_session == mock_session
    
    @pytest.mark.integration 
    async def test_log_change(self, mock_session):
        """Test logging a change"""
        event_store = EventStore()
        event_store.async_session = lambda: mock_session
        
        entry = await event_store.log_change(
            event_id=uuid4(),
            entity_type=EntityType.LOCATION,
            entity_id=uuid4(),
            action_type=ActionType.WORLD_CHANGE,
            actor_type=ActorType.SYSTEM,
            actor_id=uuid4(),
            before_state={"name": "Old Name"},
            after_state={"name": "New Name"}
        )
        
        assert entry.before_state == {"name": "Old Name"}
        assert entry.after_state == {"name": "New Name"}
        
        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.integration
    async def test_get_entity_history(self, mock_session):
        """Test getting entity history"""
        entity_id = uuid4()
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        event_store = EventStore()
        event_store.async_session = lambda: mock_session
        
        history = await event_store.get_entity_history(entity_id, limit=10)
        
        assert isinstance(history, list)
        mock_session.execute.assert_called_once()
    
    @pytest.mark.integration
    async def test_create_world_snapshot(self, mock_session):
        """Test creating world snapshot"""
        snapshot_data = {"entities": {"location": [], "npc": []}}
        
        mock_snapshot = MagicMock()
        mock_snapshot.id = uuid4()
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        
        # Mock the session call to return the snapshot with ID
        def mock_session_context():
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.__aexit__ = AsyncMock(return_value=None)
            # Simulate the snapshot being created with an ID
            ctx.id = mock_snapshot.id
            return ctx
        
        event_store = EventStore()
        event_store.async_session = mock_session_context
        
        with patch('core.event_sourcing.WorldSnapshotModel') as mock_model:
            mock_model.return_value = mock_snapshot
            
            snapshot_id = await event_store.create_world_snapshot(
                snapshot_data=snapshot_data,
                created_by="test"
            )
            
            assert snapshot_id == mock_snapshot.id


class TestDatabaseIntegration:
    """Integration tests for database components"""
    
    @pytest.mark.integration
    async def test_graph_vector_integration(self, sample_location):
        """Test integration between graph and vector databases"""
        # This test requires real databases
        pytest.skip("Requires running databases")
        
        graph_db = GraphDatabase()
        vector_db = VectorDatabase()
        
        await graph_db.connect()
        await vector_db.connect()
        
        try:
            # Store in graph DB
            created_entity = await graph_db.create_entity(sample_location)
            
            # Store in vector DB
            await vector_db.store_entity(created_entity)
            
            # Search in vector DB
            results = await vector_db.search_entities(
                query=sample_location.name,
                limit=5
            )
            
            # Should find the entity
            assert len(results) > 0
            found_entity, score = results[0]
            assert found_entity.id == sample_location.id
            
        finally:
            await graph_db.disconnect()
            await vector_db.disconnect()
    
    @pytest.mark.integration
    async def test_event_sourcing_integration(self):
        """Test event sourcing integration"""
        pytest.skip("Requires running PostgreSQL")
        
        event_store = EventStore()
        await event_store.connect()
        
        try:
            # Log a change
            entry = await event_store.log_change(
                event_id=uuid4(),
                entity_type=EntityType.LOCATION,
                entity_id=uuid4(),
                action_type=ActionType.WORLD_CHANGE,
                actor_type=ActorType.SYSTEM,
                actor_id=uuid4(),
                before_state={},
                after_state={"created": True}
            )
            
            # Get recent changes
            changes = await event_store.get_recent_changes(limit=1)
            
            # Should include our change
            assert len(changes) >= 1
            assert any(c.id == entry.id for c in changes)
            
        finally:
            await event_store.disconnect()


class TestDatabaseErrorHandling:
    """Test database error handling"""
    
    @pytest.mark.integration
    async def test_graph_db_connection_failure(self):
        """Test graph database connection failure"""
        with patch('infrastructure.graph_db.AsyncGraphDatabase') as mock_graph_db:
            mock_graph_db.driver.side_effect = Exception("Connection failed")
            
            graph_db = GraphDatabase()
            
            with pytest.raises(Exception) as exc_info:
                await graph_db.connect()
            
            assert "Connection failed" in str(exc_info.value)
    
    @pytest.mark.integration
    async def test_vector_db_search_failure(self, mock_qdrant_client, mock_sentence_transformer):
        """Test vector database search failure"""
        vector_db = VectorDatabase()
        vector_db.client = mock_qdrant_client
        vector_db.encoder = mock_sentence_transformer
        
        # Mock search failure
        mock_qdrant_client.search.side_effect = Exception("Search failed")
        
        with pytest.raises(Exception) as exc_info:
            await vector_db.search_entities("test query")
        
        assert "Search failed" in str(exc_info.value)
    
    @pytest.mark.integration
    async def test_event_store_log_failure(self, mock_session):
        """Test event store logging failure"""
        event_store = EventStore()
        event_store.async_session = lambda: mock_session
        
        # Mock commit failure
        mock_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            await event_store.log_change(
                event_id=uuid4(),
                entity_type=EntityType.LOCATION,
                entity_id=uuid4(),
                action_type=ActionType.WORLD_CHANGE,
                actor_type=ActorType.SYSTEM,
                actor_id=uuid4(),
                before_state={},
                after_state={}
            )
        
        assert "Database error" in str(exc_info.value)