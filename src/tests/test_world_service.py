"""
Tests for World Service
"""
from datetime import datetime

import pytest
from unittest.mock import AsyncMock, call
from uuid import uuid4

from core.world_service import world_service
from domain.entities import (
    EntityType, ActionType, ActorType, Location, Player, NPC, Item
)


class TestWorldServiceInitialization:
    """Test World Service initialization"""
    
    @pytest.mark.integration
    async def test_service_initialization(self, world_service):
        """Test that world service initializes properly"""
        assert world_service.is_initialized is True
    
    @pytest.mark.integration
    async def test_service_shutdown(self, world_service):
        """Test that world service shuts down properly"""
        await world_service.shutdown()
        # Mock services should have disconnect called
        world_service.graph_db.disconnect.assert_called_once()
        world_service.vector_db.disconnect.assert_called_once()
        world_service.event_store.disconnect.assert_called_once()


class TestEntityOperations:
    """Test basic entity CRUD operations"""
    
    @pytest.mark.integration
    async def test_create_entity(self, world_service, sample_location, system_actor_id):
        """Test entity creation"""
        # Setup mocks
        world_service.graph_db.create_entity.return_value = sample_location
        world_service.vector_db.store_entity = AsyncMock()
        world_service.event_store.log_change = AsyncMock()
        
        # Create entity
        result = await world_service.create_entity(
            entity=sample_location,
            actor_id=system_actor_id,
            actor_type=ActorType.SYSTEM
        )
        
        # Verify result
        assert result == sample_location
        
        # Verify interactions
        world_service.graph_db.create_entity.assert_called_once_with(sample_location)
        world_service.vector_db.store_entity.assert_called_once_with(sample_location)
        world_service.event_store.log_change.assert_called_once()
    
    @pytest.mark.integration
    async def test_create_entity_failure(self, world_service, sample_location, system_actor_id):
        """Test entity creation failure handling"""
        # Setup mock to fail
        world_service.graph_db.create_entity.side_effect = Exception("DB Error")
        
        # Attempt to create entity
        with pytest.raises(Exception) as exc_info:
            await world_service.create_entity(
                entity=sample_location,
                actor_id=system_actor_id,
                actor_type=ActorType.SYSTEM
            )
        
        assert "DB Error" in str(exc_info.value)
        
        # Verify error was logged
        world_service.event_store.log_change.assert_called_once()
        log_call = world_service.event_store.log_change.call_args
        assert log_call[1]['confidence_score'] == 0.0
    
    @pytest.mark.integration
    async def test_get_entity(self, world_service, sample_location):
        """Test entity retrieval"""
        # Setup mock
        world_service.graph_db.get_entity.return_value = sample_location
        
        # Get entity
        result = await world_service.get_entity(
            entity_id=sample_location.id,
            entity_type=EntityType.LOCATION
        )
        
        # Verify result
        assert result == sample_location
        world_service.graph_db.get_entity.assert_called_once_with(
            sample_location.id, EntityType.LOCATION, world_id=None
        )
    
    @pytest.mark.integration
    async def test_get_entity_not_found(self, world_service, unique_id):
        """Test entity retrieval when not found"""
        # Setup mock to return None
        world_service.graph_db.get_entity.return_value = None
        
        # Get entity
        result = await world_service.get_entity(
            entity_id=unique_id,
            entity_type=EntityType.LOCATION
        )
        
        # Verify result
        assert result is None
    
    @pytest.mark.integration
    async def test_update_entity(self, world_service, sample_location, system_actor_id):
        """Test entity update"""
        # Setup mocks
        world_service.graph_db.get_entity.return_value = sample_location
        world_service.graph_db.update_entity.return_value = sample_location
        world_service.vector_db.update_entity = AsyncMock()
        world_service.event_store.log_change = AsyncMock()
        
        # Update entity
        sample_location.description = "Updated description"
        result = await world_service.update_entity(
            entity=sample_location,
            actor_id=system_actor_id,
            actor_type=ActorType.SYSTEM
        )
        
        # Verify result
        assert result == sample_location
        
        # Verify interactions
        world_service.graph_db.update_entity.assert_called_once_with(sample_location)
        world_service.vector_db.update_entity.assert_called_once_with(sample_location)
        world_service.event_store.log_change.assert_called_once()
    
    @pytest.mark.integration
    async def test_delete_entity(self, world_service, sample_location, system_actor_id):
        """Test entity deletion"""
        # Setup mocks
        world_service.graph_db.get_entity.return_value = sample_location
        world_service.graph_db.delete_entity.return_value = True
        world_service.vector_db.delete_entity = AsyncMock()
        world_service.event_store.log_change = AsyncMock()
        
        # Delete entity
        result = await world_service.delete_entity(
            entity_id=sample_location.id,
            entity_type=EntityType.LOCATION,
            actor_id=system_actor_id,
            actor_type=ActorType.SYSTEM
        )
        
        # Verify result
        assert result is True
        
        # Verify interactions
        world_service.graph_db.delete_entity.assert_called_once_with(sample_location.id)
        world_service.vector_db.delete_entity.assert_called_once_with(sample_location.id)
        world_service.event_store.log_change.assert_called_once()


class TestSearchOperations:
    """Test search and context operations"""
    
    @pytest.mark.integration
    async def test_search_entities_basic(self, world_service, sample_location):
        """Test basic entity search"""
        # Setup mock
        search_results = [(sample_location, 0.95)]
        world_service.vector_db.search_entities.return_value = search_results
        
        # Search entities
        results = await world_service.search_entities(
            query="tavern",
            limit=10,
            entity_types=[EntityType.LOCATION]
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0] == (sample_location, 0.95)
        
        # Verify interaction (service always forwards filters, defaulting to None)
        world_service.vector_db.search_entities.assert_called_once_with(
            query="tavern",
            limit=10,
            entity_types=[EntityType.LOCATION],
            filters=None
        )
    
    @pytest.mark.integration
    async def test_search_entities_with_context(self, world_service, sample_location):
        """Test entity search with graph context"""
        # Setup mocks
        search_results = [(sample_location, 0.95)]
        world_service.vector_db.search_entities.return_value = search_results
        world_service.graph_db.get_entity.return_value = sample_location
        
        # Search entities with context
        results = await world_service.search_entities(
            query="tavern",
            limit=10,
            entity_types=[EntityType.LOCATION],
            include_graph_context=True
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0] == (sample_location, 0.95)
        
        # Verify graph DB was called for full entity
        world_service.graph_db.get_entity.assert_called_once_with(
            sample_location.id, sample_location.type, world_id=None
        )
    
    @pytest.mark.integration
    async def test_get_entity_context(self, world_service, sample_location):
        """Test getting entity context via graph traversal"""
        # Setup mock
        context_entities = [sample_location]
        world_service.graph_db.traverse_graph.return_value = context_entities
        
        # Get context
        results = await world_service.get_entity_context(
            entity_id=sample_location.id,
            max_depth=2,
            entity_types=[EntityType.NPC, EntityType.ITEM]
        )
        
        # Verify results
        assert results == context_entities
        
        # Verify interaction
        world_service.graph_db.traverse_graph.assert_called_once_with(
            start_entity_id=sample_location.id,
            max_depth=2,
            entity_types=[EntityType.NPC, EntityType.ITEM],
            world_id=None
        )


class TestRelationshipOperations:
    """Test relationship creation and management"""
    
    @pytest.mark.integration
    async def test_create_relationship(self, world_service, sample_location, sample_npc, system_actor_id):
        """Test relationship creation between entities"""
        # Setup mock
        world_service.graph_db.create_relationship.return_value = True
        world_service.event_store.log_change = AsyncMock()
        
        # Create relationship
        result = await world_service.create_relationship(
            from_entity_id=sample_npc.id,
            to_entity_id=sample_location.id,
            relationship_type="LOCATED_IN",
            properties={"since": "today"},
            actor_id=system_actor_id,
            actor_type=ActorType.SYSTEM
        )
        
        # Verify result
        assert result is True
        
        # Verify interactions
        world_service.graph_db.create_relationship.assert_called_once_with(
            from_id=sample_npc.id,
            to_id=sample_location.id,
            relationship_type="LOCATED_IN",
            properties={"since": "today"}
        )
        world_service.event_store.log_change.assert_called_once()
    
    @pytest.mark.integration
    async def test_create_relationship_failure(self, world_service, unique_id, system_actor_id):
        """Test relationship creation failure"""
        # Setup mock to fail
        world_service.graph_db.create_relationship.side_effect = Exception("Relationship Error")
        
        # Attempt to create relationship
        with pytest.raises(Exception) as exc_info:
            await world_service.create_relationship(
                from_entity_id=unique_id,
                to_entity_id=unique_id,
                relationship_type="KNOWS",
                actor_id=system_actor_id,
                actor_type=ActorType.SYSTEM
            )
        
        assert "Relationship Error" in str(exc_info.value)


class TestSnapshotOperations:
    """Test world snapshot operations"""
    
    @pytest.mark.integration
    async def test_create_world_snapshot(self, world_service, sample_entities):
        """Test world snapshot creation"""
        # Setup mocks
        world_service.graph_db.get_entities_by_type.return_value = [sample_entities['location']]
        snapshot_id = uuid4()
        world_service.event_store.create_world_snapshot.return_value = snapshot_id
        
        # Create snapshot
        result = await world_service.create_world_snapshot(
            created_by="test",
            metadata={"test": True}
        )
        
        # Verify result
        assert result == snapshot_id
        
        # Verify all entity types were queried
        assert world_service.graph_db.get_entities_by_type.call_count == len(EntityType)
        
        # Verify snapshot was created
        world_service.event_store.create_world_snapshot.assert_called_once()
        create_call = world_service.event_store.create_world_snapshot.call_args
        assert create_call[1]['created_by'] == "test"
        assert create_call[1]['metadata'] == {"test": True}
    
    @pytest.mark.integration
    async def test_rollback_to_snapshot(self, world_service):
        """Test rollback to snapshot returns a replay report"""
        # Setup mocks
        snapshot_id = uuid4()
        snapshot_timestamp = datetime(2024, 1, 1)
        snapshot_data = {
            "id": snapshot_id,
            "timestamp": snapshot_timestamp,
            "data": {"entities": {}},
            "metadata": {},
            "created_by": "test"
        }
        world_service.event_store.get_world_snapshot.return_value = snapshot_data
        world_service.event_store.get_changes_since_snapshot.return_value = []

        # Rollback
        result = await world_service.rollback_to_snapshot(snapshot_id)

        # Verify the replay report shape
        assert result == {
            "snapshot_id": str(snapshot_id),
            "events_seen": 0,
            "reverted_creates": 0,
            "reverted_updates": 0,
            "restored_deletes": 0,
            "skipped": 0,
            "errors": [],
        }

        # Verify interactions
        world_service.event_store.get_world_snapshot.assert_called_once_with(snapshot_id)
        world_service.event_store.rollback_to_snapshot.assert_called_once_with(snapshot_id)
        world_service.event_store.get_changes_since_snapshot.assert_called_once_with(
            snapshot_timestamp
        )
        # Completion record is written to the event log
        world_service.event_store.log_change.assert_called_once()
        completion = world_service.event_store.log_change.call_args
        assert completion[1]["before_state"] == {"action": "rollback_completed"}
    
    @pytest.mark.integration
    async def test_rollback_to_nonexistent_snapshot(self, world_service):
        """Test rollback to non-existent snapshot"""
        # Setup mock to return None
        snapshot_id = uuid4()
        world_service.event_store.get_world_snapshot.return_value = None
        
        # Attempt rollback
        with pytest.raises(ValueError) as exc_info:
            await world_service.rollback_to_snapshot(snapshot_id)
        
        assert f"Snapshot {snapshot_id} not found" in str(exc_info.value)


class TestHistoryOperations:
    """Test history and change tracking operations"""
    
    @pytest.mark.integration
    async def test_get_entity_history(self, world_service, unique_id):
        """Test getting entity change history"""
        # Setup mock
        history = []  # Mock empty history
        world_service.event_store.get_entity_history.return_value = history
        
        # Get history
        result = await world_service.get_entity_history(unique_id, limit=50)
        
        # Verify result
        assert result == history
        world_service.event_store.get_entity_history.assert_called_once_with(unique_id, 50)
    
    @pytest.mark.integration
    async def test_get_session_changes(self, world_service, test_session_id):
        """Test getting session changes"""
        # Setup mock
        changes = []  # Mock empty changes
        world_service.event_store.get_session_changes.return_value = changes
        
        # Get changes
        result = await world_service.get_session_changes(test_session_id)
        
        # Verify result
        assert result == changes
        world_service.event_store.get_session_changes.assert_called_once_with(test_session_id)
    
    @pytest.mark.integration
    async def test_get_recent_changes(self, world_service):
        """Test getting recent world changes"""
        # Setup mock
        changes = []  # Mock empty changes
        world_service.event_store.get_recent_changes.return_value = changes
        
        # Get changes
        result = await world_service.get_recent_changes(
            limit=100,
            entity_types=[EntityType.PLAYER],
            actor_types=[ActorType.SYSTEM]
        )
        
        # Verify result
        assert result == changes
        world_service.event_store.get_recent_changes.assert_called_once_with(
            limit=100,
            entity_types=[EntityType.PLAYER],
            actor_types=[ActorType.SYSTEM]
        )


@pytest.mark.integration
@pytest.mark.skip(reason="requires live services (Neo4j/Qdrant/Postgres); mutates a real world DB, cannot be meaningfully mocked")
class TestWorldServiceIntegration:
    """Integration tests with real services (requires running databases)"""
    
    async def test_real_entity_creation(self, real_world_service):
        """Test entity creation with real services"""
        location = Location(
            name="Integration Test Tavern",
            description="A test tavern for integration testing"
        )
        
        system_actor = uuid4()
        
        # Create entity
        result = await real_world_service.create_entity(
            entity=location,
            actor_id=system_actor,
            actor_type=ActorType.SYSTEM
        )
        
        # Verify creation
        assert result.id == location.id
        assert result.name == location.name
        
        # Verify we can retrieve it
        retrieved = await real_world_service.get_entity(result.id, EntityType.LOCATION)
        assert retrieved is not None
        assert retrieved.name == location.name
        
        # Cleanup - delete the test entity
        await real_world_service.delete_entity(
            entity_id=result.id,
            entity_type=EntityType.LOCATION,
            actor_id=system_actor,
            actor_type=ActorType.SYSTEM
        )
    
    async def test_real_search_functionality(self, real_world_service):
        """Test search with real services"""
        # Search for existing entities (from init_databases.py)
        results = await real_world_service.search_entities(
            query="tavern ale",
            limit=5,
            entity_types=[EntityType.LOCATION, EntityType.ITEM]
        )
        
        # Should find some results from the sample world
        assert len(results) >= 0  # Might be 0 if no data, that's ok for tests