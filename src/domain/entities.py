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


class AbilityScore(str, Enum):
    """D&D 5e ability scores"""
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


class SkillType(str, Enum):
    """D&D 5e skills"""
    # Strength-based
    ATHLETICS = "athletics"
    
    # Dexterity-based
    ACROBATICS = "acrobatics"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    STEALTH = "stealth"
    
    # Intelligence-based
    ARCANA = "arcana"
    HISTORY = "history"
    INVESTIGATION = "investigation"
    NATURE = "nature"
    RELIGION = "religion"
    
    # Wisdom-based
    ANIMAL_HANDLING = "animal_handling"
    INSIGHT = "insight"
    MEDICINE = "medicine"
    PERCEPTION = "perception"
    SURVIVAL = "survival"
    
    # Charisma-based
    DECEPTION = "deception"
    INTIMIDATION = "intimidation"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"


class CharacterClass(str, Enum):
    """D&D 5e character classes"""
    BARBARIAN = "barbarian"
    BARD = "bard"
    CLERIC = "cleric"
    DRUID = "druid"
    FIGHTER = "fighter"
    MONK = "monk"
    PALADIN = "paladin"
    RANGER = "ranger"
    ROGUE = "rogue"
    SORCERER = "sorcerer"
    WARLOCK = "warlock"
    WIZARD = "wizard"


class Race(str, Enum):
    """D&D 5e common races"""
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALFLING = "halfling"
    GNOME = "gnome"
    HALF_ORC = "half_orc"
    HALF_ELF = "half_elf"
    TIEFLING = "tiefling"
    DRAGONBORN = "dragonborn"


class DiceRollType(str, Enum):
    """Types of dice rolls"""
    ABILITY_CHECK = "ability_check"
    SKILL_CHECK = "skill_check"
    SAVING_THROW = "saving_throw"
    ATTACK_ROLL = "attack_roll"
    DAMAGE_ROLL = "damage_roll"
    INITIATIVE = "initiative"
    DEATH_SAVE = "death_save"


class PlayerStats(BaseModel):
    """D&D 5e character statistics"""
    # Core ability scores (3-20 range typically)
    ability_scores: Dict[AbilityScore, int] = Field(default_factory=lambda: {
        AbilityScore.STRENGTH: 10,
        AbilityScore.DEXTERITY: 10,
        AbilityScore.CONSTITUTION: 10,
        AbilityScore.INTELLIGENCE: 10,
        AbilityScore.WISDOM: 10,
        AbilityScore.CHARISMA: 10
    })
    
    # Character class and level
    character_class: Optional[CharacterClass] = None
    level: int = 1
    experience_points: int = 0
    
    # Proficiency
    proficiency_bonus: int = Field(default=2)  # +2 at level 1, scales with level
    skill_proficiencies: List[SkillType] = Field(default_factory=list)
    saving_throw_proficiencies: List[AbilityScore] = Field(default_factory=list)
    
    # Combat stats
    armor_class: int = 10  # Base AC without armor
    initiative_bonus: int = 0  # Usually DEX modifier
    speed: int = 30  # Movement speed in feet
    
    # Hit points
    max_hit_points: int = Field(default=8)  # Base + CON modifier
    current_hit_points: int = Field(default=8)
    temporary_hit_points: int = 0
    
    # Spell casting (if applicable)
    spell_slots: Dict[int, int] = Field(default_factory=dict)  # {level: slots}
    spells_known: List[str] = Field(default_factory=list)
    spell_save_dc: Optional[int] = None
    spell_attack_bonus: Optional[int] = None
    
    # Equipment and inventory
    equipped_armor: Optional[UUID] = None
    equipped_weapons: List[UUID] = Field(default_factory=list)
    equipped_shield: Optional[UUID] = None
    
    # Status effects and conditions
    conditions: List[str] = Field(default_factory=list)  # "poisoned", "charmed", etc.
    active_effects: Dict[str, Any] = Field(default_factory=dict)  # Temporary bonuses/penalties
    
    # Custom stats for future expansion
    custom_stats: Dict[str, Any] = Field(default_factory=dict)
    
    def get_ability_modifier(self, ability: AbilityScore) -> int:
        """Calculate ability modifier from score"""
        score = self.ability_scores.get(ability, 10)
        return (score - 10) // 2
    
    def get_skill_bonus(self, skill: SkillType) -> int:
        """Calculate total skill bonus (ability + proficiency if applicable)"""
        # Map skills to their governing abilities
        skill_abilities = {
            SkillType.ATHLETICS: AbilityScore.STRENGTH,
            SkillType.ACROBATICS: AbilityScore.DEXTERITY,
            SkillType.SLEIGHT_OF_HAND: AbilityScore.DEXTERITY,
            SkillType.STEALTH: AbilityScore.DEXTERITY,
            SkillType.ARCANA: AbilityScore.INTELLIGENCE,
            SkillType.HISTORY: AbilityScore.INTELLIGENCE,
            SkillType.INVESTIGATION: AbilityScore.INTELLIGENCE,
            SkillType.NATURE: AbilityScore.INTELLIGENCE,
            SkillType.RELIGION: AbilityScore.INTELLIGENCE,
            SkillType.ANIMAL_HANDLING: AbilityScore.WISDOM,
            SkillType.INSIGHT: AbilityScore.WISDOM,
            SkillType.MEDICINE: AbilityScore.WISDOM,
            SkillType.PERCEPTION: AbilityScore.WISDOM,
            SkillType.SURVIVAL: AbilityScore.WISDOM,
            SkillType.DECEPTION: AbilityScore.CHARISMA,
            SkillType.INTIMIDATION: AbilityScore.CHARISMA,
            SkillType.PERFORMANCE: AbilityScore.CHARISMA,
            SkillType.PERSUASION: AbilityScore.CHARISMA,
        }
        
        governing_ability = skill_abilities.get(skill, AbilityScore.WISDOM)
        ability_mod = self.get_ability_modifier(governing_ability)
        
        # Add proficiency bonus if proficient
        proficiency_mod = self.proficiency_bonus if skill in self.skill_proficiencies else 0
        
        return ability_mod + proficiency_mod
    
    def get_saving_throw_bonus(self, ability: AbilityScore) -> int:
        """Calculate saving throw bonus"""
        ability_mod = self.get_ability_modifier(ability)
        proficiency_mod = self.proficiency_bonus if ability in self.saving_throw_proficiencies else 0
        return ability_mod + proficiency_mod


class DiceRoll(BaseModel):
    """Represents a dice roll with all its components"""
    roll_type: DiceRollType
    dice_notation: str  # "1d20+5", "2d6+3", etc.
    raw_results: List[int] = Field(default_factory=list)  # The actual dice values
    modifiers: int = 0  # Total modifiers applied
    total: int = 0  # Final result
    
    # Context for the roll
    difficulty_class: Optional[int] = None  # Target number to beat
    advantage: bool = False  # Roll twice, take higher
    disadvantage: bool = False  # Roll twice, take lower
    
    # Results
    is_success: Optional[bool] = None
    is_critical: bool = False  # Natural 20 on d20
    is_fumble: bool = False  # Natural 1 on d20
    
    # Metadata
    roller_id: UUID  # Who made the roll
    target_id: Optional[UUID] = None  # What/who was targeted
    description: str = ""  # Human-readable description
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionSequence(BaseModel):
    """A sequence of dice rolls for a complex action"""
    sequence_id: UUID = Field(default_factory=uuid4)
    action_description: str
    actor_id: UUID
    target_id: Optional[UUID] = None
    
    # The rolls in order
    primary_roll: Optional[DiceRoll] = None  # Main action roll
    reaction_rolls: List[DiceRoll] = Field(default_factory=list)  # Opponent reactions
    secondary_rolls: List[DiceRoll] = Field(default_factory=list)  # Damage, effects, etc.
    
    # Final outcome
    success: bool = False
    critical_success: bool = False
    critical_failure: bool = False
    final_result: str = ""  # Description of what happened
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[UUID] = None


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
    """Player entity with D&D 5e statistics"""
    type: EntityType = EntityType.PLAYER
    current_location_id: Optional[UUID] = None
    
    # D&D 5e character stats
    stats: PlayerStats = Field(default_factory=PlayerStats)
    
    # Legacy fields for backward compatibility (will be phased out)
    level: int = Field(default=1, description="Deprecated: use stats.level")
    experience: int = Field(default=0, description="Deprecated: use stats.experience_points")
    health: int = Field(default=100, description="Deprecated: use stats.current_hit_points")
    max_health: int = Field(default=100, description="Deprecated: use stats.max_hit_points")
    
    # Inventory and progression
    inventory: List[UUID] = Field(default_factory=list)
    active_quests: List[UUID] = Field(default_factory=list)
    completed_quests: List[UUID] = Field(default_factory=list)
    
    # Personal world view (fog of war, secrets, etc)
    known_npcs: List[UUID] = Field(default_factory=list)
    known_locations: List[UUID] = Field(default_factory=list)
    personal_notes: Dict[str, str] = Field(default_factory=dict)
    
    # Roll history for this character
    recent_rolls: List[DiceRoll] = Field(default_factory=list, max_items=50)
    
    @property
    def effective_level(self) -> int:
        """Get character level (prefer stats.level over legacy level)"""
        return self.stats.level if self.stats.level > 1 else self.level
    
    @property
    def effective_hit_points(self) -> int:
        """Get current hit points (prefer stats over legacy health)"""
        return self.stats.current_hit_points if self.stats.current_hit_points != 8 else self.health
    
    @property
    def effective_max_hit_points(self) -> int:
        """Get max hit points (prefer stats over legacy max_health)"""
        return self.stats.max_hit_points if self.stats.max_hit_points != 8 else self.max_health
    
    def add_roll_to_history(self, roll: DiceRoll) -> None:
        """Add a dice roll to the character's recent history"""
        self.recent_rolls.append(roll)
        # Keep only the most recent 50 rolls
        if len(self.recent_rolls) > 50:
            self.recent_rolls = self.recent_rolls[-50:]


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
    # Social systems
    disposition_to_player: Dict[UUID, int] = Field(default_factory=dict)  # player_id -> [-100..100]
    social_cooldowns: Dict[UUID, str] = Field(default_factory=dict)  # player_id -> ISO timestamp string
    recent_events: List[UUID] = Field(default_factory=list)  # Recent event IDs
    current_location_id: Optional[UUID] = None

    def compute_relationship_for_player(self, player_id: UUID) -> str:
        """Derive relationship label for a player from disposition if explicit label not set."""
        if player_id in self.relationship_to_player:
            return self.relationship_to_player[player_id]
        score = self.disposition_to_player.get(player_id, 0)
        if score >= 50:
            return "friendly"
        if score <= -50:
            return "hostile"
        return "neutral"


class NPC(BaseEntity):
    """Non-player character entity"""
    type: EntityType = EntityType.NPC
    race: Race = Race.HUMAN
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