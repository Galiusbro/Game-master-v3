"""
Domain entities for Game Master V3
Core business objects representing the game world
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities in the game world"""
    PLAYER = "player"
    NPC = "npc"
    LOCATION = "location"
    ITEM = "item"
    EVENT = "event"
    QUEST = "quest"


class ActionType(str, Enum):
    """Types of actions that can be performed"""
    MOVE = "move"
    DIALOGUE = "dialogue"
    ITEM_TRANSFER = "item_transfer"
    COMBAT = "combat"
    WORLD_CHANGE = "world_change"
    QUEST_UPDATE = "quest_update"


class ActorType(str, Enum):
    """Types of actors that can perform actions"""
    PLAYER = "player"
    NPC = "npc"
    SYSTEM = "system"
    LLM = "llm"


class BaseEntity(BaseModel):
    """Base class for all game entities"""
    id: UUID = Field(default_factory=uuid4)
    type: EntityType
    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata with timestamp tracking"""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()


class Player(BaseEntity):
    """Player entity"""
    type: EntityType = EntityType.PLAYER
    current_location_id: Optional[UUID] = None
    level: int = 1
    experience: int = 0
    health: int = 100
    max_health: int = 100
    inventory: List[UUID] = Field(default_factory=list)
    active_quests: List[UUID] = Field(default_factory=list)
    completed_quests: List[UUID] = Field(default_factory=list)
    
    # Personal world view (fog of war, secrets, etc)
    known_npcs: List[UUID] = Field(default_factory=list)
    known_locations: List[UUID] = Field(default_factory=list)
    personal_notes: Dict[str, str] = Field(default_factory=dict)


class NPCPersonality(BaseModel):
    """Fixed personality profile for NPCs"""
    core_traits: List[str] = Field(default_factory=list)
    speech_patterns: List[str] = Field(default_factory=list) 
    likes: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    backstory: str = ""
    example_phrases: List[str] = Field(default_factory=list)


class NPCState(BaseModel):
    """Dynamic state of an NPC"""
    current_mood: str = "neutral"
    current_activity: str = "idle"
    relationship_to_player: Dict[UUID, str] = Field(default_factory=dict)  # player_id -> relationship
    recent_events: List[UUID] = Field(default_factory=list)  # Recent event IDs
    current_location_id: Optional[UUID] = None


class NPC(BaseEntity):
    """Non-player character entity"""
    type: EntityType = EntityType.NPC
    personality: NPCPersonality = Field(default_factory=NPCPersonality)
    current_state: NPCState = Field(default_factory=NPCState)
    is_alive: bool = True
    importance_level: int = 1  # 1-10, affects caching and context priority


class Location(BaseEntity):
    """Location/place entity"""
    type: EntityType = EntityType.LOCATION
    connected_locations: List[UUID] = Field(default_factory=list)
    items_present: List[UUID] = Field(default_factory=list)
    npcs_present: List[UUID] = Field(default_factory=list)
    players_present: List[UUID] = Field(default_factory=list)
    is_safe: bool = True
    exploration_level: int = 0  # How much has been explored
    

class ItemType(str, Enum):
    """Types of items"""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST_ITEM = "quest_item"
    TREASURE = "treasure"
    TOOL = "tool"


class Item(BaseEntity):
    """Item entity"""
    type: EntityType = EntityType.ITEM
    item_type: ItemType
    owner_id: Optional[UUID] = None  # Player or NPC who owns it
    location_id: Optional[UUID] = None  # Location where it's found
    is_unique: bool = False  # Unique items can only exist once
    value: int = 0
    properties: Dict[str, Any] = Field(default_factory=dict)


class Event(BaseEntity):
    """Event entity - something that happened in the world"""
    type: EntityType = EntityType.EVENT
    action_type: ActionType
    actor_id: UUID  # Who performed the action
    actor_type: ActorType
    participants: List[UUID] = Field(default_factory=list)  # Other entities involved
    location_id: Optional[UUID] = None
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    consequences: List[UUID] = Field(default_factory=list)  # Events that resulted from this
    session_id: Optional[UUID] = None
    confidence_score: float = 1.0  # For LLM-generated events


class QuestStatus(str, Enum):
    """Quest status"""
    AVAILABLE = "available"
    ACTIVE = "active" 
    COMPLETED = "completed"
    FAILED = "failed"
    HIDDEN = "hidden"


class Quest(BaseEntity):
    """Quest entity"""
    type: EntityType = EntityType.QUEST
    status: QuestStatus = QuestStatus.AVAILABLE
    giver_id: Optional[UUID] = None  # NPC who gave the quest
    participants: List[UUID] = Field(default_factory=list)  # Players on this quest
    objectives: List[str] = Field(default_factory=list)
    completed_objectives: List[str] = Field(default_factory=list)
    rewards: Dict[str, Any] = Field(default_factory=dict)
    prerequisites: List[UUID] = Field(default_factory=list)  # Required completed quests
    time_limit: Optional[datetime] = None


class WorldSnapshot(BaseModel):
    """Complete snapshot of world state at a point in time"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    players: List[Player] = Field(default_factory=list)
    npcs: List[NPC] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    items: List[Item] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    quests: List[Quest] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChangeLogEntry(BaseModel):
    """Entry in the change log for event sourcing"""
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_id: UUID
    entity_type: EntityType
    entity_id: UUID
    action_type: ActionType
    actor_type: ActorType
    actor_id: UUID
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[UUID] = None
    confidence_score: float = 1.0
    rollback_data: Optional[Dict[str, Any]] = None