"""
Tests for API endpoints
"""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from main import app
from domain.entities import EntityType, Location, NPC, Player, Item, ItemType


@pytest.fixture
async def client():
    """HTTP client for testing API"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_world_service():
    """Mock world service for API tests"""
    mock = AsyncMock()
    mock.is_initialized = True
    return mock


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.mark.api
    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "environment" in data
    
    @pytest.mark.api
    async def test_health_check(self, client):
        """Test health check endpoint"""
        with patch('main.world_service') as mock_service:
            mock_service.is_initialized = True
            
            response = await client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["world_service_initialized"] is True


class TestEntityEndpoints:
    """Test entity CRUD endpoints"""
    
    @pytest.mark.api
    async def test_create_location(self, client, mock_world_service):
        """Test creating a location via API"""
        location_data = {
            "entity_data": {
                "name": "Test Tavern",
                "description": "A test tavern",
                "is_safe": True,
                "exploration_level": 0
            },
            "entity_type": "location",
            "actor_id": str(uuid4()),
            "session_id": str(uuid4())
        }
        
        created_location = Location(**location_data["entity_data"])
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.create_entity.return_value = created_location
            
            response = await client.post("/api/v1/entities", json=location_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["entity"]["name"] == "Test Tavern"
            assert data["entity_type"] == "location"
            
            # Verify world service was called
            mock_world_service.create_entity.assert_called_once()
    
    @pytest.mark.api
    async def test_create_npc(self, client, mock_world_service):
        """Test creating an NPC via API"""
        npc_data = {
            "entity_data": {
                "name": "Test Bartender",
                "description": "A friendly bartender",
                "personality": {
                    "core_traits": ["friendly", "talkative"],
                    "speech_patterns": ["speaks warmly"],
                    "likes": ["good stories"],
                    "dislikes": ["troublemakers"],
                    "fears": ["losing customers"],
                    "goals": ["serve good drinks"],
                    "backstory": "Has been a bartender for 20 years",
                    "example_phrases": ["Welcome to my tavern!"]
                },
                "current_state": {
                    "current_mood": "happy",
                    "current_activity": "cleaning glasses"
                },
                "importance_level": 5
            },
            "entity_type": "npc"
        }
        
        created_npc = NPC(**npc_data["entity_data"])
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.create_entity.return_value = created_npc
            
            response = await client.post("/api/v1/entities", json=npc_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["entity"]["name"] == "Test Bartender"
            assert data["entity_type"] == "npc"
    
    @pytest.mark.api
    async def test_get_entity(self, client, mock_world_service):
        """Test getting an entity by ID"""
        entity_id = uuid4()
        location = Location(
            id=entity_id,
            name="Test Location",
            description="A test location"
        )
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity.return_value = location
            
            response = await client.get(f"/api/v1/entities/{entity_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["entity"]["name"] == "Test Location"
            assert data["entity_type"] == "location"
            
            mock_world_service.get_entity.assert_called_once_with(entity_id, None)
    
    @pytest.mark.api
    async def test_get_entity_not_found(self, client, mock_world_service):
        """Test getting non-existent entity"""
        entity_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity.return_value = None
            
            response = await client.get(f"/api/v1/entities/{entity_id}")
            assert response.status_code == 404
            
            data = response.json()
            assert "not found" in data["detail"].lower()
    
    @pytest.mark.api
    async def test_update_entity(self, client, mock_world_service):
        """Test updating an entity"""
        entity_id = uuid4()
        original_location = Location(
            id=entity_id,
            name="Original Name",
            description="Original description"
        )
        
        updated_location = Location(
            id=entity_id,
            name="Updated Name", 
            description="Updated description"
        )
        
        update_data = {
            "entity_data": {
                "name": "Updated Name",
                "description": "Updated description"
            },
            "actor_id": str(uuid4())
        }
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity.return_value = original_location
            mock_world_service.update_entity.return_value = updated_location
            
            response = await client.put(f"/api/v1/entities/{entity_id}", json=update_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["entity"]["name"] == "Updated Name"
            
            mock_world_service.update_entity.assert_called_once()
    
    @pytest.mark.api
    async def test_delete_entity(self, client, mock_world_service):
        """Test deleting an entity"""
        entity_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.delete_entity.return_value = True
            
            response = await client.delete(
                f"/api/v1/entities/{entity_id}",
                params={"entity_type": "location"}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "deleted successfully" in data["message"]
            
            mock_world_service.delete_entity.assert_called_once()
    
    @pytest.mark.api
    async def test_delete_entity_not_found(self, client, mock_world_service):
        """Test deleting non-existent entity"""
        entity_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.delete_entity.return_value = False
            
            response = await client.delete(
                f"/api/v1/entities/{entity_id}",
                params={"entity_type": "location"}
            )
            assert response.status_code == 404


class TestSearchEndpoints:
    """Test search endpoints"""
    
    @pytest.mark.api
    async def test_search_entities(self, client, mock_world_service):
        """Test entity search"""
        search_data = {
            "query": "tavern ale",
            "limit": 10,
            "entity_types": ["location", "item"],
            "include_context": True
        }
        
        location = Location(name="Tavern", description="A cozy tavern")
        item = Item(name="Ale", description="A mug of ale", item_type=ItemType.CONSUMABLE)
        
        search_results = [
            (location, 0.95),
            (item, 0.87)
        ]
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.search_entities.return_value = search_results
            
            response = await client.post("/api/v1/search", json=search_data)
            assert response.status_code == 200
            
            data = response.json()
            assert len(data) == 2
            assert data[0]["score"] == 0.95
            assert data[0]["entity"]["name"] == "Tavern"
            assert data[1]["score"] == 0.87
            assert data[1]["entity"]["name"] == "Ale"
            
            mock_world_service.search_entities.assert_called_once()
    
    @pytest.mark.api
    async def test_get_entity_context(self, client, mock_world_service):
        """Test getting entity context"""
        entity_id = uuid4()
        
        npc = NPC(name="Bartender", description="Friendly bartender")
        item = Item(name="Mug", description="A wooden mug", item_type=ItemType.CONSUMABLE)
        
        context_entities = [npc, item]
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity_context.return_value = context_entities
            
            response = await client.get(
                f"/api/v1/entities/{entity_id}/context",
                params={"max_depth": 2}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert len(data) == 2
            assert data[0]["entity"]["name"] == "Bartender"
            assert data[1]["entity"]["name"] == "Mug"


class TestRelationshipEndpoints:
    """Test relationship endpoints"""
    
    @pytest.mark.api
    async def test_create_relationship(self, client, mock_world_service):
        """Test creating a relationship"""
        relationship_data = {
            "from_entity_id": str(uuid4()),
            "to_entity_id": str(uuid4()),
            "relationship_type": "LOCATED_IN",
            "properties": {"since": "today"},
            "actor_id": str(uuid4())
        }
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.create_relationship.return_value = True
            
            response = await client.post("/api/v1/relationships", json=relationship_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "created successfully" in data["message"]
            
            mock_world_service.create_relationship.assert_called_once()
    
    @pytest.mark.api
    async def test_create_relationship_failure(self, client, mock_world_service):
        """Test relationship creation failure"""
        relationship_data = {
            "from_entity_id": str(uuid4()),
            "to_entity_id": str(uuid4()),
            "relationship_type": "INVALID",
        }
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.create_relationship.return_value = False
            
            response = await client.post("/api/v1/relationships", json=relationship_data)
            assert response.status_code == 400


class TestSnapshotEndpoints:
    """Test snapshot endpoints"""
    
    @pytest.mark.api
    async def test_create_snapshot(self, client, mock_world_service):
        """Test creating a world snapshot"""
        snapshot_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.create_world_snapshot.return_value = snapshot_id
            
            response = await client.post("/api/v1/snapshots", params={"created_by": "test_user"})
            assert response.status_code == 200
            
            data = response.json()
            assert data["snapshot_id"] == str(snapshot_id)
            assert "created successfully" in data["message"]
    
    @pytest.mark.api
    async def test_rollback_to_snapshot(self, client, mock_world_service):
        """Test rolling back to a snapshot"""
        snapshot_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.rollback_to_snapshot.return_value = True
            
            response = await client.post(f"/api/v1/snapshots/{snapshot_id}/rollback")
            assert response.status_code == 200
            
            data = response.json()
            assert "initiated successfully" in data["message"]
    
    @pytest.mark.api
    async def test_rollback_failure(self, client, mock_world_service):
        """Test rollback failure"""
        snapshot_id = uuid4()
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.rollback_to_snapshot.return_value = False
            
            response = await client.post(f"/api/v1/snapshots/{snapshot_id}/rollback")
            assert response.status_code == 400


class TestHistoryEndpoints:
    """Test history endpoints"""
    
    @pytest.mark.api
    async def test_get_entity_history(self, client, mock_world_service):
        """Test getting entity history"""
        entity_id = uuid4()
        history = []  # Mock empty history
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity_history.return_value = history
            
            response = await client.get(f"/api/v1/entities/{entity_id}/history")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.api
    async def test_get_session_changes(self, client, mock_world_service):
        """Test getting session changes"""
        session_id = uuid4()
        changes = []  # Mock empty changes
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_session_changes.return_value = changes
            
            response = await client.get(f"/api/v1/sessions/{session_id}/changes")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.api
    async def test_get_recent_changes(self, client, mock_world_service):
        """Test getting recent changes"""
        changes = []  # Mock empty changes
        
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_recent_changes.return_value = changes
            
            response = await client.get("/api/v1/changes/recent", params={"limit": 50})
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)


class TestErrorHandling:
    """Test API error handling"""
    
    @pytest.mark.api
    async def test_invalid_entity_type(self, client):
        """Test invalid entity type handling"""
        invalid_data = {
            "entity_data": {"name": "Test"},
            "entity_type": "invalid_type"
        }
        
        response = await client.post("/api/v1/entities", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.api
    async def test_missing_required_fields(self, client):
        """Test missing required fields"""
        incomplete_data = {
            "entity_type": "location"
            # Missing entity_data
        }
        
        response = await client.post("/api/v1/entities", json=incomplete_data)
        assert response.status_code == 422
    
    @pytest.mark.api
    async def test_invalid_uuid(self, client):
        """Test invalid UUID handling"""
        response = await client.get("/api/v1/entities/not-a-uuid")
        assert response.status_code == 422
    
    @pytest.mark.api
    async def test_internal_server_error(self, client, mock_world_service):
        """Test internal server error handling"""
        with patch('api.routes.world_service', mock_world_service):
            mock_world_service.get_entity.side_effect = Exception("Database error")
            
            response = await client.get(f"/api/v1/entities/{uuid4()}")
            assert response.status_code == 500


@pytest.mark.api
@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests with real services"""
    
    async def test_full_entity_lifecycle(self, client):
        """Test complete entity lifecycle via API"""
        # This test requires real services to be running
        pytest.skip("Requires running services")
        
        # Create entity
        location_data = {
            "entity_data": {
                "name": "Integration Test Location",
                "description": "A location for integration testing"
            },
            "entity_type": "location"
        }
        
        create_response = await client.post("/api/v1/entities", json=location_data)
        assert create_response.status_code == 200
        
        entity_id = create_response.json()["entity"]["id"]
        
        # Get entity
        get_response = await client.get(f"/api/v1/entities/{entity_id}")
        assert get_response.status_code == 200
        
        # Update entity  
        update_data = {
            "entity_data": {"description": "Updated description"}
        }
        update_response = await client.put(f"/api/v1/entities/{entity_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Delete entity
        delete_response = await client.delete(
            f"/api/v1/entities/{entity_id}",
            params={"entity_type": "location"}
        )
        assert delete_response.status_code == 200