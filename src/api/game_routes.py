"""
Natural Language Game Command API

Handles natural language commands like "иду в таверну поговорить с трактирщиком"
and routes them to appropriate AI endpoints.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.world_service import world_service
from domain.entities import Player, AbilityScore, SkillType, CharacterClass
from core.actions import GameCommand, execute_command
from core.narration import EntityNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["Natural Language Game Commands"])


class GameCommandRequest(BaseModel):
    """Natural language game command request"""
    world_id: UUID
    session_id: UUID
    player_id: UUID
    command: str
    player_name: Optional[str] = None  # For convenience, can resolve to player_id
    dialogue_context: Optional[Dict[str, Any]] = None  # Context for dialogue continuation


class GameCommandResponse(BaseModel):
    """Unified response for any game command"""
    success: bool
    action_type: str
    content: str
    
    # AI response details
    confidence: float = 0.0
    tokens_used: int = 0
    response_time: float = 0.0
    
    # Resolved entities
    resolved_entities: Dict[str, Any] = {}

    # Dice roll results
    dice_rolls: List[Any] = []
    
    # Parsing details
    parsing_confidence: float = 0.0
    original_command: str = ""
    
    # Additional context
    warnings: List[Any] = []
    event_id: Optional[UUID] = None


@router.post("/command", response_model=GameCommandResponse)
async def process_natural_command(request: GameCommandRequest) -> GameCommandResponse:
    """
    Process natural language game command

    Examples:
    - "иду в таверну"
    - "говорю с барменом: привет, есть ли комнаты?"
    - "ищу зелья в магазине"
    - "покупаю меч у кузнеца"

    This endpoint is an adapter: it turns an HTTP request into a
    GameCommand, lets the core play it out, and renders the result.
    """
    try:
        result = await execute_command(
            GameCommand(
                world_id=request.world_id,
                session_id=request.session_id,
                player_id=request.player_id,
                text=request.command,
                dialogue_context=request.dialogue_context,
            )
        )
        return GameCommandResponse(**result)

    except HTTPException:
        raise
    except EntityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing command '{request.command}': {e}")
        raise HTTPException(status_code=500, detail=f"Command processing failed: {str(e)}")


@router.get("/help")
async def get_command_help() -> Dict[str, Any]:
    """Get help about natural language commands"""
    return {
        "supported_actions": [
            {
                "action": "dialogue",
                "examples": [
                    "говорю с барменом: привет!",
                    "спрашиваю у кузнеца про мечи",
                    "разговариваю с трактирщиком"
                ]
            },
            {
                "action": "movement", 
                "examples": [
                    "иду в таверну",
                    "направляюсь к кузнице",
                    "выхожу из города"
                ]
            },
            {
                "action": "search",
                "examples": [
                    "ищу зелья",
                    "осматриваю комнату",
                    "обыскиваю сундук"
                ]
            },
            {
                "action": "trade",
                "examples": [
                    "покупаю меч у кузнеца",
                    "продаю зелье торговцу",
                    "торгуюсь с продавцом"
                ]
            }
        ],
        "tips": [
            "Используйте естественный язык",
            "Будьте конкретны в описаниях",
            "Система умеет находить NPC и локации по описанию",
            "Можно использовать кавычки для прямой речи",
            "Магические свитки и заклинания работают автоматически"
        ]
    }




# Character management endpoints
class CharacterStatsRequest(BaseModel):
    """Request to view or update character stats"""
    player_id: UUID


class CharacterCreationRequest(BaseModel):
    """Request to create a new character"""
    name: str
    character_class: CharacterClass
    ability_scores: Dict[str, Any]  # {"strength": 15, "dexterity": 14, etc.}
    background: str = "Custom"
    

@router.post("/character/create", response_model=GameCommandResponse)
async def create_character(request: CharacterCreationRequest) -> GameCommandResponse:
    """Create a new D&D character"""
    try:
        from domain.entities import PlayerStats
        
        # Validate ability scores
        total_points = sum(request.ability_scores.values())
        if total_points < 60 or total_points > 90:
            raise HTTPException(status_code=400, detail="Invalid ability scores total")
        
        # Create character stats
        stats = PlayerStats(
            ability_scores={
                AbilityScore.STRENGTH: request.ability_scores.get('strength', 10),
                AbilityScore.DEXTERITY: request.ability_scores.get('dexterity', 10),
                AbilityScore.CONSTITUTION: request.ability_scores.get('constitution', 10),
                AbilityScore.INTELLIGENCE: request.ability_scores.get('intelligence', 10),
                AbilityScore.WISDOM: request.ability_scores.get('wisdom', 10),
                AbilityScore.CHARISMA: request.ability_scores.get('charisma', 10),
            },
            character_class=request.character_class,
            level=1,
            experience_points=0
        )
        
        # Calculate derived stats
        con_mod = stats.get_ability_modifier(AbilityScore.CONSTITUTION)
        stats.max_hit_points = 8 + con_mod  # Base HP for level 1
        stats.current_hit_points = stats.max_hit_points
        stats.armor_class = 10 + stats.get_ability_modifier(AbilityScore.DEXTERITY)
        
        # Set class-specific proficiencies
        if request.character_class == CharacterClass.ROGUE:
            stats.skill_proficiencies = [SkillType.STEALTH, SkillType.SLEIGHT_OF_HAND, SkillType.PERCEPTION, SkillType.INVESTIGATION]
            stats.saving_throw_proficiencies = [AbilityScore.DEXTERITY, AbilityScore.INTELLIGENCE]
        elif request.character_class == CharacterClass.FIGHTER:
            stats.skill_proficiencies = [SkillType.ATHLETICS, SkillType.INTIMIDATION]
            stats.saving_throw_proficiencies = [AbilityScore.STRENGTH, AbilityScore.CONSTITUTION]
        elif request.character_class == CharacterClass.WIZARD:
            stats.skill_proficiencies = [SkillType.ARCANA, SkillType.HISTORY, SkillType.INVESTIGATION]
            stats.saving_throw_proficiencies = [AbilityScore.INTELLIGENCE, AbilityScore.WISDOM]
        # TODO: Add more classes
        
        # Create player entity
        player = Player(
            name=request.name,
            description=f"A level 1 {request.character_class.value}",
            stats=stats
        )
        
        # Save to world
        created_player = await world_service.create_entity(
            entity=player,
            actor_id=player.id  # Self-created
        )
        
        return GameCommandResponse(
            success=True,
            action_type="character_creation",
            content=f"Character '{request.name}' created successfully! Class: {request.character_class.value.title()}, HP: {stats.max_hit_points}, AC: {stats.armor_class}",
            resolved_entities={
                'player_id': str(created_player.id),
                'character_class': request.character_class.value,
                'level': 1,
                'hit_points': stats.max_hit_points
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (400, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error creating character: {e}")
        raise HTTPException(status_code=500, detail=f"Character creation failed: {str(e)}")


@router.get("/character/{player_id}/stats")
async def get_character_stats(player_id: UUID) -> Dict[str, Any]:
    """Get character statistics"""
    try:
        player = await world_service.get_player(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return {
            'character_name': player.name,
            'level': player.stats.level,
            'class': player.stats.character_class.value if player.stats.character_class else None,
            'experience': player.stats.experience_points,
            'hit_points': {
                'current': player.stats.current_hit_points,
                'max': player.stats.max_hit_points,
                'temporary': player.stats.temporary_hit_points
            },
            'armor_class': player.stats.armor_class,
            'speed': player.stats.speed,
            'proficiency_bonus': player.stats.proficiency_bonus,
            'ability_scores': dict(player.stats.ability_scores),
            'ability_modifiers': {
                ability.value: player.stats.get_ability_modifier(ability)
                for ability in AbilityScore
            },
            'skills': {
                skill.value: player.stats.get_skill_bonus(skill)
                for skill in SkillType
            },
            'saving_throws': {
                ability.value: player.stats.get_saving_throw_bonus(ability)
                for ability in AbilityScore
            },
            'proficiencies': {
                'skills': [skill.value for skill in player.stats.skill_proficiencies],
                'saving_throws': [ability.value for ability in player.stats.saving_throw_proficiencies]
            },
            'conditions': player.stats.conditions,
            'recent_rolls': [
                {
                    'type': roll.roll_type.value,
                    'description': roll.description,
                    'total': roll.total,
                    'success': roll.is_success,
                    'critical': roll.is_critical,
                    'timestamp': roll.timestamp.isoformat()
                }
                for roll in player.recent_rolls[-10:]  # Last 10 rolls
            ]
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error getting character stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get character stats: {str(e)}")