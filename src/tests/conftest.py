"""
Test fixtures for Game Master V3
Provides common test utilities and fixtures
"""
import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator, List
from uuid import uuid4
import tempfile
from unittest.mock import AsyncMock, MagicMock

from faker import Faker
import factory

# Allow the suite to run without torch/sentence-transformers installed
# (CI and local runs without the ML stack): stub the module before any
# project import pulls it in. The classification service degrades to
# keyword mode by design when embeddings are unavailable.
import sys
try:  # pragma: no cover
    import sentence_transformers  # noqa: F401
except ImportError:  # pragma: no cover
    _st_stub = MagicMock()
    _st_stub.SentenceTransformer = MagicMock
    sys.modules["sentence_transformers"] = _st_stub

# Test imports
from config.settings import Settings
from core.world_service import WorldService
from domain.entities import (
    Player, NPC, Location, Item, Event, Quest,
    NPCPersonality, NPCState, ItemType, EntityType
)

fake = Faker()


# Test Settings Configuration
@pytest.fixture(scope="session")
def test_settings():
    """Test settings with minimal dependencies"""
    return Settings(
        app_debug=True,
        environment="test",
        openai_api_key="test_key",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j", 
        neo4j_password="gamemaster123",
        qdrant_host="localhost",
        qdrant_port=6333,
        redis_host="localhost",
        redis_port=6379,
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="gamemaster_test",
        postgres_user="gm_user",
        postgres_password="gm_password",
        log_level="DEBUG",
        enable_hallucination_detection=False,  # Disable for testing
        enable_auto_rollback=False,
    )


# Event Loop Configuration
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Mock Services
@pytest.fixture
def mock_graph_db():
    """Mock Neo4j Graph Database"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.create_entity = AsyncMock()
    mock.get_entity = AsyncMock()
    mock.update_entity = AsyncMock()
    mock.delete_entity = AsyncMock()
    mock.create_relationship = AsyncMock()
    mock.traverse_graph = AsyncMock(return_value=[])
    mock.get_entities_by_type = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_vector_db():
    """Mock Qdrant Vector Database"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.store_entity = AsyncMock()
    mock.search_entities = AsyncMock(return_value=[])
    mock.get_similar_entities = AsyncMock(return_value=[])
    mock.delete_entity = AsyncMock()
    mock.update_entity = AsyncMock()
    return mock


@pytest.fixture
def mock_event_store():
    """Mock Event Store"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.log_change = AsyncMock()
    mock.get_entity_history = AsyncMock(return_value=[])
    mock.get_session_changes = AsyncMock(return_value=[])
    mock.get_recent_changes = AsyncMock(return_value=[])
    mock.create_world_snapshot = AsyncMock(return_value=uuid4())
    mock.get_world_snapshot = AsyncMock()
    mock.rollback_to_snapshot = AsyncMock(return_value=True)
    # Reverse event replay walks this list — it must be a real list, not an
    # auto-created child mock (len()/reversed() would silently see nothing).
    mock.get_changes_since_snapshot = AsyncMock(return_value=[])
    return mock


@pytest.fixture
async def world_service(mock_graph_db, mock_vector_db, mock_event_store, monkeypatch):
    """World Service with mocked dependencies.

    WorldService talks to module-level singletons, so the mocks must be
    patched into the module namespace — assigning instance attributes
    (the previous approach) left the real clients in place and the mocks
    were never exercised.
    """
    import core.world_service as ws_module

    service = WorldService()
    monkeypatch.setattr(ws_module, "graph_db", mock_graph_db)
    monkeypatch.setattr(ws_module, "vector_db", mock_vector_db)
    monkeypatch.setattr(ws_module, "event_store", mock_event_store)
    mock_cache = AsyncMock()
    # Defaults: every cache lookup is a miss unless a test says otherwise.
    # Every getter the code awaits needs an explicit None — an auto-created
    # child mock is truthy and would be returned as a fake cache hit.
    mock_cache.get.return_value = None
    mock_cache.get_entity.return_value = None
    mock_cache.get_vector_search.return_value = None
    mock_cache.get_ai_response.return_value = None
    mock_cache.get_entity_context.return_value = None
    monkeypatch.setattr(ws_module, "cache_service", mock_cache)

    # Expose the same mocks as instance attributes so tests can reach them
    # via the service object (module globals stay the interception point).
    service.graph_db = mock_graph_db
    service.vector_db = mock_vector_db
    service.event_store = mock_event_store
    service.cache_service = mock_cache
    service.is_initialized = True

    return service


# Entity Factories using Factory Boy
class PlayerFactory(factory.Factory):
    class Meta:
        model = Player
    
    name = factory.Faker('name')
    description = factory.Faker('text', max_nb_chars=200)
    level = factory.Faker('random_int', min=1, max=20)
    experience = factory.Faker('random_int', min=0, max=10000)
    health = 100
    max_health = 100
    current_location_id = factory.LazyFunction(uuid4)


class NPCPersonalityFactory(factory.Factory):
    class Meta:
        model = NPCPersonality
    
    core_traits = factory.LazyFunction(lambda: fake.words(3))
    speech_patterns = factory.LazyFunction(lambda: fake.sentences(2))
    likes = factory.LazyFunction(lambda: fake.words(3))
    dislikes = factory.LazyFunction(lambda: fake.words(2))
    fears = factory.LazyFunction(lambda: fake.words(2))
    goals = factory.LazyFunction(lambda: fake.sentences(2))
    backstory = factory.Faker('text', max_nb_chars=500)
    example_phrases = factory.LazyFunction(lambda: fake.sentences(3))


class NPCStateFactory(factory.Factory):
    class Meta:
        model = NPCState
    
    current_mood = factory.Faker('random_element', elements=['happy', 'sad', 'angry', 'neutral', 'excited'])
    current_activity = factory.Faker('random_element', elements=['working', 'resting', 'talking', 'thinking'])
    current_location_id = factory.LazyFunction(uuid4)


class NPCFactory(factory.Factory):
    class Meta:
        model = NPC
    
    name = factory.Faker('name')
    description = factory.Faker('text', max_nb_chars=200)
    personality = factory.SubFactory(NPCPersonalityFactory)
    current_state = factory.SubFactory(NPCStateFactory)
    is_alive = True
    importance_level = factory.Faker('random_int', min=1, max=10)


class LocationFactory(factory.Factory):
    class Meta:
        model = Location
    
    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=300)
    is_safe = factory.Faker('boolean', chance_of_getting_true=70)
    exploration_level = factory.Faker('random_int', min=0, max=100)


class ItemFactory(factory.Factory):
    class Meta:
        model = Item
    
    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=200)
    item_type = factory.Faker('random_element', elements=list(ItemType))
    is_unique = factory.Faker('boolean', chance_of_getting_true=20)
    value = factory.Faker('random_int', min=1, max=1000)
    location_id = factory.LazyFunction(uuid4)


# Test Data Fixtures
@pytest.fixture
def sample_player():
    """Sample player for testing"""
    return PlayerFactory()


@pytest.fixture
def sample_npc():
    """Sample NPC for testing"""
    return NPCFactory()


@pytest.fixture
def sample_location():
    """Sample location for testing"""
    return LocationFactory()


@pytest.fixture
def sample_item():
    """Sample item for testing"""
    return ItemFactory()


@pytest.fixture
def sample_entities(sample_player, sample_npc, sample_location, sample_item):
    """Collection of sample entities"""
    return {
        'player': sample_player,
        'npc': sample_npc,
        'location': sample_location,
        'item': sample_item,
    }


# Integration Test Fixtures (with real services)
@pytest.fixture(scope="session")
async def real_world_service():
    """Real World Service for integration tests"""
    service = WorldService()
    await service.initialize()
    yield service
    await service.shutdown()


# Test Database Cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Auto cleanup test data after each test"""
    # Setup
    yield
    # Teardown - could clean test entities if needed
    pass


# Utility Fixtures
@pytest.fixture
def unique_id():
    """Generate unique ID for tests"""
    return uuid4()


@pytest.fixture
def system_actor_id():
    """System actor ID for tests"""
    return uuid4()


@pytest.fixture
def test_session_id():
    """Test session ID"""
    return uuid4()


# Parametrized Fixtures
@pytest.fixture(params=list(EntityType))
def entity_type(request):
    """Parametrized entity type fixture"""
    return request.param


@pytest.fixture(params=[1, 5, 10])
def entity_count(request):
    """Parametrized entity count fixture"""
    return request.param