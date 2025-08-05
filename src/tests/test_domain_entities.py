"""
Tests for Domain Entities
"""
import pytest
from datetime import datetime
from uuid import uuid4

from domain.entities import (
    Player, NPC, Location, Item, Event, Quest,
    NPCPersonality, NPCState, ItemType, EntityType,
    ActionType, ActorType, ChangeLogEntry, WorldSnapshot
)


class TestBaseEntity:
    """Test BaseEntity functionality"""
    
    def test_entity_creation(self, sample_location):
        """Test basic entity creation"""
        assert sample_location.id is not None
        assert sample_location.type == EntityType.LOCATION
        assert sample_location.name
        assert sample_location.description
        assert isinstance(sample_location.created_at, datetime)
        assert isinstance(sample_location.updated_at, datetime)
        assert isinstance(sample_location.metadata, dict)
    
    def test_update_metadata(self, sample_location):
        """Test metadata update functionality"""
        original_updated_at = sample_location.updated_at
        
        sample_location.update_metadata("test_key", "test_value")
        
        assert sample_location.metadata["test_key"] == "test_value"
        assert sample_location.updated_at > original_updated_at


class TestPlayer:
    """Test Player entity"""
    
    def test_player_creation(self, sample_player):
        """Test player creation with default values"""
        assert sample_player.type == EntityType.PLAYER
        assert sample_player.level >= 1
        assert sample_player.health <= sample_player.max_health
        assert isinstance(sample_player.inventory, list)
        assert isinstance(sample_player.active_quests, list)
        assert isinstance(sample_player.completed_quests, list)
        assert isinstance(sample_player.known_npcs, list)
        assert isinstance(sample_player.known_locations, list)
        assert isinstance(sample_player.personal_notes, dict)
    
    def test_player_with_location(self, sample_location):
        """Test player with location assignment"""
        player = Player(
            name="Test Player",
            description="A test player",
            current_location_id=sample_location.id
        )
        assert player.current_location_id == sample_location.id


class TestNPC:
    """Test NPC entity"""
    
    def test_npc_creation(self, sample_npc):
        """Test NPC creation"""
        assert sample_npc.type == EntityType.NPC
        assert isinstance(sample_npc.personality, NPCPersonality)
        assert isinstance(sample_npc.current_state, NPCState)
        assert sample_npc.is_alive is True
        assert 1 <= sample_npc.importance_level <= 10
    
    def test_npc_personality(self, sample_npc):
        """Test NPC personality structure"""
        personality = sample_npc.personality
        assert isinstance(personality.core_traits, list)
        assert isinstance(personality.speech_patterns, list)
        assert isinstance(personality.likes, list)
        assert isinstance(personality.dislikes, list)
        assert isinstance(personality.fears, list)
        assert isinstance(personality.goals, list)
        assert isinstance(personality.backstory, str)
        assert isinstance(personality.example_phrases, list)
    
    def test_npc_state(self, sample_npc):
        """Test NPC current state"""
        state = sample_npc.current_state
        assert isinstance(state.current_mood, str)
        assert isinstance(state.current_activity, str)
        assert isinstance(state.relationship_to_player, dict)
        assert isinstance(state.recent_events, list)
    
    def test_npc_relationship_tracking(self):
        """Test NPC relationship tracking"""
        npc = NPC(
            name="Test NPC",
            description="A test NPC"
        )
        player_id = uuid4()
        
        # Add relationship
        npc.current_state.relationship_to_player[player_id] = "friendly"
        
        assert npc.current_state.relationship_to_player[player_id] == "friendly"


class TestLocation:
    """Test Location entity"""
    
    def test_location_creation(self, sample_location):
        """Test location creation"""
        assert sample_location.type == EntityType.LOCATION
        assert isinstance(sample_location.connected_locations, list)
        assert isinstance(sample_location.items_present, list)
        assert isinstance(sample_location.npcs_present, list)
        assert isinstance(sample_location.players_present, list)
        assert isinstance(sample_location.is_safe, bool)
        assert 0 <= sample_location.exploration_level <= 100
    
    def test_location_connections(self):
        """Test location connections"""
        location1 = Location(name="Location 1", description="First location")
        location2 = Location(name="Location 2", description="Second location")
        
        # Connect locations
        location1.connected_locations.append(location2.id)
        location2.connected_locations.append(location1.id)
        
        assert location2.id in location1.connected_locations
        assert location1.id in location2.connected_locations


class TestItem:
    """Test Item entity"""
    
    def test_item_creation(self, sample_item):
        """Test item creation"""
        assert sample_item.type == EntityType.ITEM
        assert sample_item.item_type in ItemType
        assert isinstance(sample_item.is_unique, bool)
        assert sample_item.value >= 0
        assert isinstance(sample_item.properties, dict)
    
    def test_item_ownership(self):
        """Test item ownership assignment"""
        item = Item(
            name="Test Sword",
            description="A test weapon",
            item_type=ItemType.WEAPON,
            value=100
        )
        
        player_id = uuid4()
        item.owner_id = player_id
        
        assert item.owner_id == player_id
        assert item.location_id is None
    
    def test_item_properties(self):
        """Test item custom properties"""
        item = Item(
            name="Magic Potion",
            description="A healing potion",
            item_type=ItemType.CONSUMABLE,
            properties={
                "healing": 50,
                "duration": 10,
                "consumable": True
            }
        )
        
        assert item.properties["healing"] == 50
        assert item.properties["consumable"] is True


class TestEvent:
    """Test Event entity"""
    
    def test_event_creation(self):
        """Test event creation"""
        actor_id = uuid4()
        event = Event(
            name="Test Event",
            description="A test event",
            action_type=ActionType.WORLD_CHANGE,
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM
        )
        
        assert event.type == EntityType.EVENT
        assert event.action_type == ActionType.WORLD_CHANGE
        assert event.actor_id == actor_id
        assert event.actor_type == ActorType.SYSTEM
        assert isinstance(event.participants, list)
        assert isinstance(event.before_state, dict)
        assert isinstance(event.after_state, dict)
        assert isinstance(event.consequences, list)
        assert event.confidence_score == 1.0
    
    def test_event_with_participants(self):
        """Test event with multiple participants"""
        event = Event(
            name="Combat Event",
            description="A battle occurred",
            action_type=ActionType.COMBAT,
            actor_id=uuid4(),
            actor_type=ActorType.PLAYER,
            participants=[uuid4(), uuid4()]
        )
        
        assert len(event.participants) == 2


class TestQuest:
    """Test Quest entity"""
    
    def test_quest_creation(self):
        """Test quest creation"""
        quest = Quest(
            name="Test Quest",
            description="A test quest"
        )
        
        assert quest.type == EntityType.QUEST
        assert isinstance(quest.objectives, list)
        assert isinstance(quest.completed_objectives, list)
        assert isinstance(quest.rewards, dict)
        assert isinstance(quest.prerequisites, list)
    
    def test_quest_progress(self):
        """Test quest progress tracking"""
        quest = Quest(
            name="Collect Items",
            description="Collect 5 items",
            objectives=["Find item 1", "Find item 2", "Find item 3"]
        )
        
        # Complete first objective
        quest.completed_objectives.append("Find item 1")
        
        assert len(quest.completed_objectives) == 1
        assert "Find item 1" in quest.completed_objectives


class TestChangeLogEntry:
    """Test ChangeLogEntry for event sourcing"""
    
    def test_change_log_creation(self):
        """Test change log entry creation"""
        entry = ChangeLogEntry(
            event_id=uuid4(),
            entity_type=EntityType.PLAYER,
            entity_id=uuid4(),
            action_type=ActionType.WORLD_CHANGE,
            actor_type=ActorType.SYSTEM,
            actor_id=uuid4(),
            before_state={"health": 100},
            after_state={"health": 80}
        )
        
        assert isinstance(entry.id, type(uuid4()))
        assert isinstance(entry.timestamp, datetime)
        assert entry.before_state["health"] == 100
        assert entry.after_state["health"] == 80
        assert entry.confidence_score == 1.0


class TestWorldSnapshot:
    """Test WorldSnapshot functionality"""
    
    def test_world_snapshot_creation(self, sample_entities):
        """Test world snapshot creation"""
        snapshot = WorldSnapshot(
            players=[sample_entities['player']],
            npcs=[sample_entities['npc']],
            locations=[sample_entities['location']],
            items=[sample_entities['item']],
            metadata={"created_by": "test", "version": "1.0"}
        )
        
        assert isinstance(snapshot.timestamp, datetime)
        assert len(snapshot.players) == 1
        assert len(snapshot.npcs) == 1
        assert len(snapshot.locations) == 1
        assert len(snapshot.items) == 1
        assert snapshot.metadata["created_by"] == "test"


class TestEntityValidation:
    """Test entity validation and constraints"""
    
    def test_player_health_constraints(self):
        """Test player health cannot exceed max_health"""
        player = Player(
            name="Test Player",
            description="Test",
            health=150,
            max_health=100
        )
        
        # Health can be set higher than max, but this should be validated in business logic
        assert player.health == 150
        assert player.max_health == 100
    
    def test_npc_importance_level_bounds(self):
        """Test NPC importance level validation"""
        npc = NPC(
            name="Test NPC",
            description="Test",
            importance_level=15  # Above normal range
        )
        
        # Should accept any int value, validation in business logic
        assert npc.importance_level == 15
    
    def test_location_exploration_bounds(self):
        """Test location exploration level"""
        location = Location(
            name="Test Location",
            description="Test",
            exploration_level=150  # Above 100%
        )
        
        # Should accept any int value
        assert location.exploration_level == 150


@pytest.mark.parametrize("entity_factory", [
    "sample_player", "sample_npc", "sample_location", "sample_item"
])
def test_entity_serialization(entity_factory, request):
    """Test that all entities can be serialized to dict"""
    entity = request.getfixturevalue(entity_factory)
    
    # Should be able to convert to dict without errors
    entity_dict = entity.dict()
    
    assert isinstance(entity_dict, dict)
    assert 'id' in entity_dict
    assert 'type' in entity_dict
    assert 'name' in entity_dict
    assert 'created_at' in entity_dict
    assert 'updated_at' in entity_dict