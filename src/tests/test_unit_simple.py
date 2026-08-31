"""
Simple unit tests for core business logic without external dependencies
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from domain.entities import (
    EntityType, Location, NPC, Player, Item, ItemType,
    ActionType, ActorType, NPCPersonality, NPCState
)


class TestBusinessLogic:
    """Test business logic without external dependencies"""
    
    @pytest.mark.unit
    def test_entity_type_validation(self):
        """Test entity type enumeration"""
        assert EntityType.PLAYER == "player"
        assert EntityType.NPC == "npc"
        assert EntityType.LOCATION == "location"
        assert EntityType.ITEM == "item"
        assert EntityType.EVENT == "event"
        assert EntityType.QUEST == "quest"
    
    @pytest.mark.unit
    def test_location_business_logic(self):
        """Test location entity business logic"""
        location = Location(
            name="Test Tavern",
            description="A cozy tavern",
            is_safe=True,
            exploration_level=50
        )
        
        # Test metadata updates
        location.update_metadata("visitors", 10)
        assert location.metadata["visitors"] == 10
        
        # Test connections
        other_location_id = uuid4()
        location.connected_locations.append(other_location_id)
        assert other_location_id in location.connected_locations
    
    @pytest.mark.unit
    def test_npc_personality_logic(self):
        """Test NPC personality system"""
        personality = NPCPersonality(
            core_traits=["friendly", "talkative"],
            speech_patterns=["speaks warmly", "uses local dialect"],
            likes=["good stories", "ale"],
            dislikes=["rudeness", "silence"],
            fears=["losing customers"],
            goals=["serve the best ale in town"],
            backstory="Been a bartender for 20 years",
            example_phrases=["Welcome, friend!", "What brings you here?"]
        )
        
        npc = NPC(
            name="Barliman",
            description="Friendly tavern keeper",
            personality=personality,
            importance_level=7
        )
        
        # Test personality access
        assert "friendly" in npc.personality.core_traits
        assert "good stories" in npc.personality.likes
        assert npc.importance_level == 7
    
    @pytest.mark.unit
    def test_npc_state_management(self):
        """Test NPC state tracking"""
        state = NPCState(
            current_mood="happy",
            current_activity="cleaning glasses"
        )
        
        # Test relationship tracking
        player_id = uuid4()
        state.relationship_to_player[player_id] = "friendly"
        
        # Test recent events
        state.recent_events.append("Player ordered ale")
        
        assert state.relationship_to_player[player_id] == "friendly"
        assert "Player ordered ale" in state.recent_events
    
    @pytest.mark.unit
    def test_item_logic(self):
        """Test item business logic"""
        # Test consumable item
        ale = Item(
            name="Mug of Ale",
            description="A frothy mug of ale",
            item_type=ItemType.CONSUMABLE,
            value=5,
            properties={
                "healing": 10,
                "duration": 5,
                "alcoholic": True
            }
        )
        
        assert ale.item_type == ItemType.CONSUMABLE
        assert ale.properties["healing"] == 10
        assert ale.properties["alcoholic"] is True
        
        # Test weapon item
        sword = Item(
            name="Iron Sword",
            description="A sturdy iron sword",
            item_type=ItemType.WEAPON,
            value=50,
            properties={
                "damage": 15,
                "durability": 100,
                "weight": 3
            }
        )
        
        assert sword.item_type == ItemType.WEAPON
        assert sword.properties["damage"] == 15
    
    @pytest.mark.unit
    def test_player_inventory_logic(self):
        """Test player inventory management"""
        player = Player(
            name="Test Adventurer",
            description="A brave adventurer",
            level=5,
            health=80,
            max_health=100
        )
        
        # Test inventory
        sword_id = uuid4()
        ale_id = uuid4()
        
        player.inventory.extend([sword_id, ale_id])
        
        assert len(player.inventory) == 2
        assert sword_id in player.inventory
        assert ale_id in player.inventory
        
        # Test known NPCs
        npc_id = uuid4()
        player.known_npcs.append(npc_id)
        assert npc_id in player.known_npcs
    
    @pytest.mark.unit
    def test_entity_metadata_system(self):
        """Test entity metadata system"""
        location = Location(
            name="Test Location",
            description="A test location"
        )
        
        # Test initial metadata
        assert isinstance(location.metadata, dict)
        
        # Test metadata updates
        location.update_metadata("temperature", "warm")
        location.update_metadata("mood", "cozy")
        location.update_metadata("visitors_today", 15)
        
        assert location.metadata["temperature"] == "warm"
        assert location.metadata["mood"] == "cozy"
        assert location.metadata["visitors_today"] == 15
        
        # Test overwriting metadata
        location.update_metadata("temperature", "hot")
        assert location.metadata["temperature"] == "hot"
    
    @pytest.mark.unit
    def test_entity_id_uniqueness(self):
        """Test that entities get unique IDs"""
        location1 = Location(name="Location 1", description="First")
        location2 = Location(name="Location 2", description="Second")
        
        assert location1.id != location2.id
        assert location1.type == location2.type == EntityType.LOCATION
    
    @pytest.mark.unit
    def test_entity_timestamps(self):
        """Test entity timestamp behavior"""
        location = Location(
            name="Timestamp Test",
            description="Testing timestamps"
        )
        
        original_created = location.created_at
        original_updated = location.updated_at
        
        # Should be approximately the same
        assert abs((original_created - original_updated).total_seconds()) < 1
        
        # Update metadata to trigger updated_at change
        import time
        time.sleep(0.01)  # Small delay
        location.update_metadata("test", "value")
        
        # updated_at should change, created_at should not
        assert location.created_at == original_created
        assert location.updated_at > original_updated


class TestEnumValidation:
    """Test enum validation and values"""
    
    @pytest.mark.unit
    def test_entity_types(self):
        """Test EntityType enum"""
        types = [e.value for e in EntityType]
        expected = ["player", "npc", "location", "item", "event", "quest"]
        assert set(types) == set(expected)
    
    @pytest.mark.unit
    def test_item_types(self):
        """Test ItemType enum"""
        types = [e.value for e in ItemType]
        expected = ["weapon", "armor", "consumable", "treasure", "tool", "quest_item"]
        assert set(types) == set(expected)
    
    @pytest.mark.unit
    def test_action_types(self):
        """Test ActionType enum"""
        types = [e.value for e in ActionType]
        expected = ["move", "dialogue", "item_transfer", "combat", "magic", "world_change", "quest_update"]
        assert set(types) == set(expected)
    
    @pytest.mark.unit
    def test_actor_types(self):
        """Test ActorType enum"""
        types = [e.value for e in ActorType]
        expected = ["player", "npc", "system", "llm"]
        assert set(types) == set(expected)