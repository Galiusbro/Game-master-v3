"""
Semantic Command Parser - Natural Language to Game Actions

Converts natural language commands like "иду в таверну поговорить с трактирщиком"
into structured game actions with resolved entity IDs.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from uuid import UUID
from dataclasses import dataclass

from infrastructure.vector_db import vector_db
from infrastructure.graph_db import graph_db
from domain.entities import EntityType, BaseEntity, SkillType, AbilityScore
from core.dice_engine import dice_engine

logger = logging.getLogger(__name__)


class GameAction(Enum):
    """Types of game actions that can be parsed"""
    DIALOGUE = "dialogue"
    MOVEMENT = "movement" 
    SEARCH = "search"
    COMBAT = "combat"
    TRADE = "trade"
    INVENTORY = "inventory"
    REST = "rest"
    EXPLORE = "explore"
    MAGIC = "magic"
    
    # New skill check actions
    SKILL_CHECK = "skill_check"
    STEALTH = "stealth"
    PERSUASION = "persuasion"
    DECEPTION = "deception"
    INVESTIGATION = "investigation"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    ATHLETICS = "athletics"
    PERCEPTION = "perception"
    
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Result of semantic parsing"""
    action: GameAction
    raw_command: str
    
    # Resolved entities
    target_npc_id: Optional[UUID] = None
    target_location_id: Optional[UUID] = None
    target_item_id: Optional[UUID] = None
    
    # Extracted information
    message: Optional[str] = None
    intent_details: Dict[str, Any] = None
    confidence: float = 0.0
    
    # Skill check specific data
    requires_roll: bool = False
    skill_type: Optional[SkillType] = None
    ability_type: Optional[AbilityScore] = None
    estimated_dc: Optional[int] = None
    context_modifiers: Dict[str, Any] = None
    
    # Context used for resolution
    context_entities: List[BaseEntity] = None


class SemanticParser:
    """Main semantic parser class"""
    
    def __init__(self):
        self.action_patterns = {
            GameAction.DIALOGUE: [
                r'говор\w*|сказать|спрос\w*|отвеч\w*|диалог|разговор',
                r'talk|speak|say|ask|tell|chat|conversation',
            ],
            GameAction.MOVEMENT: [
                r'ид\w*|ехать|идти|перейти|направ\w*|двигаться',
                r'go|move|walk|travel|head|enter|leave|exit',
            ],
            GameAction.SEARCH: [
                r'иск\w*|найти|смотр\w*|осмотр\w*|обыск\w*',
                r'search|look|find|examine|inspect|investigate',
            ],
            GameAction.COMBAT: [
                r'атак\w*|удар\w*|бой|сраж\w*|напасть|драться|убить|убив\w*|убей\w*',
                r'attack|fight|combat|strike|hit|battle|kill|slay|defeat|destroy',
            ],
            GameAction.TRADE: [
                r'купить|продать|торг\w*|обмен\w*|покуп\w*',
                r'buy|sell|trade|purchase|shop|commerce',
            ],
            GameAction.EXPLORE: [
                r'исследов\w*|изуч\w*|осмотр\w*|обход',
                r'explore|discover|survey|scout|investigate',
            ],
            GameAction.MAGIC: [
                r'заклин\w*|магия|свиток|воскр\w*|лечен\w*|зелье|заговор|ритуал',
                r'cast|spell|magic|scroll|resurrection|resurrect|heal|potion|ritual|enchant',
            ],
            
            # Skill check patterns
            GameAction.STEALTH: [
                r'подкрад\w*|прокрасться|незаметно|тихо|скрытно|спрятаться',
                r'sneak|stealth|hide|quietly|silently|stealthily|creep',
            ],
            GameAction.PERSUASION: [
                r'убед\w*|уговор\w*|склон\w*|договор\w*',
                r'persuade|convince|talk into|negotiate|reason with',
            ],
            GameAction.DECEPTION: [
                r'обман\w*|солг\w*|врать|лгать|притвор\w*',
                r'lie|deceive|bluff|trick|fake|pretend',
            ],
            GameAction.INVESTIGATION: [
                r'расследов\w*|изуч\w*|анализир\w*|разбир\w*',
                r'investigate|analyze|examine carefully|study|research',
            ],
            GameAction.SLEIGHT_OF_HAND: [
                r'укра\w*|своров\w*|карман\w*|ловкость рук',
                r'steal|pickpocket|palm|sleight of hand|pilfer',
            ],
            GameAction.ATHLETICS: [
                r'карабк\w*|лез\w*|прыг\w*|плав\w*|бег\w*',
                r'climb|jump|swim|run|leap|scale',
            ],
            GameAction.PERCEPTION: [
                r'замеч\w*|слыш\w*|чувств\w*|внимательно смотр\w*',
                r'notice|hear|sense|spot|perceive|listen',
            ]
        }
        
        # Skill to SkillType mapping
        self.skill_mapping = {
            GameAction.STEALTH: SkillType.STEALTH,
            GameAction.PERSUASION: SkillType.PERSUASION,
            GameAction.DECEPTION: SkillType.DECEPTION,
            GameAction.INVESTIGATION: SkillType.INVESTIGATION,
            GameAction.SLEIGHT_OF_HAND: SkillType.SLEIGHT_OF_HAND,
            GameAction.ATHLETICS: SkillType.ATHLETICS,
            GameAction.PERCEPTION: SkillType.PERCEPTION,
        }
        
        # Entity type patterns
        self.entity_patterns = {
            EntityType.NPC: [
                r'трактирщик|бармен|кузнец|торговец|стражник|маг|жрец',
                r'bartender|innkeeper|blacksmith|merchant|guard|wizard|priest',
                r'NPC|персонаж|человек|эльф|гном|орк'
            ],
            EntityType.LOCATION: [
                r'таверна|трактир|кузница|магазин|храм|замок|дом|город',
                r'tavern|inn|forge|shop|temple|castle|house|city|village',
                r'комната|зал|улица|площадь|лес|поле|гора'
            ],
            EntityType.ITEM: [
                r'меч|щит|зелье|свиток|кольцо|амулет|книга',
                r'sword|shield|potion|scroll|ring|amulet|book',
                r'предмет|вещь|артефакт|сокровище'
            ]
        }

    async def parse_command(
        self,
        world_id: UUID,
        session_id: UUID, 
        player_id: UUID,
        raw_command: str,
        dialogue_context: Optional[Dict[str, Any]] = None
    ) -> ParsedCommand:
        """Parse natural language command into structured action"""
        
        logger.info(f"Parsing command: '{raw_command}' for player {player_id}")
        
        # 1. Check if this is a dialogue continuation
        if dialogue_context and self._is_dialogue_continuation(raw_command, dialogue_context):
            logger.info("Detected dialogue continuation")
            return ParsedCommand(
                action=GameAction.DIALOGUE,
                raw_command=raw_command,
                target_npc_id=dialogue_context.get('last_npc_id'),
                message=raw_command,
                confidence=0.9,  # High confidence for dialogue continuation
                context_entities=[]
            )
        
        # 2. Detect action intent
        action = self._detect_action(raw_command)
        logger.debug(f"Detected action: {action}")
        
        # 2. Get player context (location, nearby entities)
        context = await self._get_player_context(world_id, session_id, player_id)
        
        # 3. Resolve entities mentioned in command
        entities = await self._resolve_entities(raw_command, context)
        
        # 4. Extract message/details based on action type
        message, details = self._extract_action_details(raw_command, action)
        
        # 5. Check if this action requires dice rolls
        skill_data = self._analyze_skill_requirements(raw_command, action, context)
        
        # 6. Build result
        result = ParsedCommand(
            action=action,
            raw_command=raw_command,
            target_npc_id=entities.get('npc_id'),
            target_location_id=entities.get('location_id'), 
            target_item_id=entities.get('item_id'),
            message=message,
            intent_details=details,
            confidence=entities.get('confidence', 0.5),
            context_entities=context,
            
            # Skill check data
            requires_roll=skill_data['requires_roll'],
            skill_type=skill_data.get('skill_type'),
            ability_type=skill_data.get('ability_type'),
            estimated_dc=skill_data.get('estimated_dc'),
            context_modifiers=skill_data.get('context_modifiers', {})
        )
        
        logger.info(f"Parsed result: {action} -> NPC:{result.target_npc_id}, Location:{result.target_location_id}")
        return result

    def _detect_action(self, command: str) -> GameAction:
        """Detect the primary action intent from command"""
        command_lower = command.lower()
        
        # Score each action type
        action_scores = {}
        for action, patterns in self.action_patterns.items():
            score = 0
            for pattern_list in patterns:
                for pattern in pattern_list.split('|'):
                    if re.search(pattern, command_lower):
                        score += 1
            action_scores[action] = score
        
        # Return action with highest score
        if action_scores:
            best_action = max(action_scores, key=action_scores.get)
            if action_scores[best_action] > 0:
                return best_action
        
        return GameAction.UNKNOWN

    async def _get_player_context(
        self, 
        world_id: UUID, 
        session_id: UUID, 
        player_id: UUID
    ) -> List[BaseEntity]:
        """Get relevant context entities for player"""
        try:
            # For now, get player's current location and nearby entities
            # TODO: Implement proper world slice context
            
            # Get player entity - use dynamic import to avoid circular dependency
            from core.world_service import world_service
            player = await world_service.get_entity(player_id, EntityType.PLAYER)
            if not player:
                logger.warning(f"Player {player_id} not found")
                return []
            
            context_entities = [player]
            
            # Get player's location
            if hasattr(player, 'current_location_id') and player.current_location_id:
                location = await world_service.get_entity(player.current_location_id, EntityType.LOCATION)
                if location:
                    context_entities.append(location)
                    
                    # Get entities in the same location
                    nearby = await world_service.get_entity_context(
                        entity_id=player.current_location_id,
                        max_depth=1,
                        entity_types=[EntityType.NPC, EntityType.ITEM]
                    )
                    context_entities.extend(nearby)
            
            logger.debug(f"Context entities: {len(context_entities)}")
            return context_entities
            
        except Exception as e:
            logger.error(f"Error getting player context: {e}")
            return []

    async def _resolve_entities(
        self, 
        command: str, 
        context: List[BaseEntity]
    ) -> Dict[str, Any]:
        """Resolve entity references in command to actual IDs"""
        
        entities = {'confidence': 0.0}
        
        try:
            # Extract potential entity mentions
            mentions = self._extract_entity_mentions(command)
            logger.info(f"Extracted mentions from '{command}': {mentions}")
            
            # Try to resolve each mention
            for mention_type, mention_text in mentions:
                logger.debug(f"Resolving {mention_type.value}: '{mention_text}'")
                
                # First, search in local context
                local_match = self._find_in_context(mention_text, mention_type, context)
                if local_match:
                    entities[f'{mention_type.value}_id'] = local_match.id
                    entities['confidence'] += 0.3
                    logger.info(f"Found {mention_type.value} in local context: {local_match.name} ({local_match.id})")
                    continue
                
                # Then, search via vector DB
                logger.debug(f"Searching vector DB for {mention_type.value}: '{mention_text}'")
                vector_results = await vector_db.search_entities(
                    query=mention_text,
                    entity_types=[mention_type],
                    limit=1,
                    score_threshold=0.0
                )
                
                if vector_results:
                    entity, score = vector_results[0]
                    entities[f'{mention_type.value}_id'] = entity.id
                    entities['confidence'] += score * 0.5
                    logger.info(f"Found {mention_type.value} via vector search: {entity.name} ({entity.id}) score={score}")
                else:
                    logger.warning(f"No {mention_type.value} found for '{mention_text}'")
            
            # Normalize confidence
            entities['confidence'] = min(entities['confidence'], 1.0)
            logger.info(f"Final resolved entities: {entities}")
            
        except Exception as e:
            logger.error(f"Error resolving entities: {e}")
        
        return entities

    def _extract_entity_mentions(self, command: str) -> List[Tuple[EntityType, str]]:
        """Extract potential entity mentions from command"""
        mentions = []
        command_lower = command.lower()
        
        # Look for known entity type patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern_list in patterns:
                for pattern in pattern_list.split('|'):
                    matches = re.finditer(pattern, command_lower)
                    for match in matches:
                        mentions.append((entity_type, match.group()))
        
        # Also look for proper names (capitalized words)
        # This catches specific NPC names like "Barliman"
        proper_names = re.findall(r'\b[A-Z][a-z]+\b', command)
        for name in proper_names:
            # Assume proper names are NPCs by default
            mentions.append((EntityType.NPC, name))
        
        return mentions

    def _find_in_context(
        self, 
        mention: str, 
        entity_type: EntityType, 
        context: List[BaseEntity]
    ) -> Optional[BaseEntity]:
        """Find entity in local context by name similarity"""
        mention_lower = mention.lower()
        
        for entity in context:
            if entity.type != entity_type:
                continue
                
            if mention_lower in entity.name.lower():
                return entity
                
            # Check description for partial matches
            if hasattr(entity, 'description') and entity.description:
                if mention_lower in entity.description.lower():
                    return entity
        
        return None

    def _extract_action_details(
        self, 
        command: str, 
        action: GameAction
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract action-specific details and message"""
        
        details = {}
        message = None
        
        if action == GameAction.DIALOGUE:
            # Extract quoted speech or message after colon
            quote_match = re.search(r'["\']([^"\']+)["\']', command)
            if quote_match:
                message = quote_match.group(1)
            else:
                # Look for message after colon or common phrases
                colon_match = re.search(r':\s*(.+)$', command)
                if colon_match:
                    message = colon_match.group(1).strip()
        
        elif action == GameAction.MOVEMENT:
            # Extract destination
            movement_words = ['к', 'в', 'на', 'to', 'into', 'towards']
            for word in movement_words:
                pattern = rf'{word}\s+(\w+(?:\s+\w+)*)'
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    details['destination'] = match.group(1)
                    break
        
        elif action == GameAction.SEARCH:
            # Extract what to search for
            search_words = ['ищу', 'найти', 'search', 'look for']
            for word in search_words:
                pattern = rf'{word}\s+(\w+(?:\s+\w+)*)'
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    details['target'] = match.group(1)
                    break
        
        return message, details

    def _is_dialogue_continuation(
        self, 
        command: str, 
        dialogue_context: Dict[str, Any]
    ) -> bool:
        """Check if command is a continuation of ongoing dialogue"""
        
        # Check if we recently had a dialogue
        last_action = dialogue_context.get('last_action')
        last_timestamp = dialogue_context.get('last_timestamp')
        
        if last_action != 'dialogue' or not last_timestamp:
            return False
        
        # Check if command was recent (within 2 minutes)
        import time
        time_diff = time.time() - last_timestamp
        if time_diff > 120:  # 2 minutes
            return False
        
        # Check if it's a short response (likely dialogue continuation)
        if len(command.split()) <= 10:  # Short responses
            # Check if it doesn't contain action words
            command_lower = command.lower()
            action_words = ['go', 'move', 'search', 'look', 'examine', 'иду', 'ищу', 'смотрю']
            
            has_action_words = any(word in command_lower for word in action_words)
            
            # If no clear action words and it's a short response, likely dialogue
            if not has_action_words:
                return True
        
        # Check for dialogue patterns
        dialogue_patterns = [
            r'^(yes|no|да|нет)\b',
            r'^(sure|конечно|хорошо|ладно)\b', 
            r'^(maybe|возможно|может быть)\b',
            r'(please|пожалуйста)',
            r'(thank you|thanks|спасибо)',
            r'(how much|сколько)',
            r'(do you|у вас есть|есть ли)',
        ]
        
        for pattern in dialogue_patterns:
            if re.search(pattern, command.lower()):
                return True
        
        return False
    
    def _analyze_skill_requirements(
        self,
        command: str,
        action: GameAction,
        context: List[BaseEntity]
    ) -> Dict[str, Any]:
        """Analyze if command requires skill checks and determine details"""
        
        result = {
            'requires_roll': False,
            'skill_type': None,
            'ability_type': None,
            'estimated_dc': None,
            'context_modifiers': {}
        }
        
        command_lower = command.lower()
        
        # Check if this action inherently requires a skill check
        if action in self.skill_mapping:
            result['requires_roll'] = True
            result['skill_type'] = self.skill_mapping[action]
            
            # Estimate DC based on command context
            result['estimated_dc'] = dice_engine.determine_difficulty_class(
                command, 
                self._build_context_for_dc(context)
            )
            
        # Check for specific skill check indicators in text
        elif any(word in command_lower for word in [
            'attempt', 'try', 'check', 'roll', 'test',
            'попытаться', 'попробовать', 'проверить', 'бросить'
        ]):
            result['requires_roll'] = True
            
            # Try to determine which skill from context
            if any(word in command_lower for word in ['stealth', 'hide', 'снейк', 'скрыться']):
                result['skill_type'] = SkillType.STEALTH
            elif any(word in command_lower for word in ['persuade', 'convince', 'убедить']):
                result['skill_type'] = SkillType.PERSUASION
            elif any(word in command_lower for word in ['investigate', 'examine', 'расследовать']):
                result['skill_type'] = SkillType.INVESTIGATION
            elif any(word in command_lower for word in ['athletics', 'climb', 'карабкаться']):
                result['skill_type'] = SkillType.ATHLETICS
            else:
                # Default to general ability check
                result['ability_type'] = AbilityScore.WISDOM
            
            result['estimated_dc'] = dice_engine.determine_difficulty_class(
                command,
                self._build_context_for_dc(context)
            )
            
        # Combat actions usually need attack rolls
        elif action == GameAction.COMBAT:
            result['requires_roll'] = True
            result['estimated_dc'] = 15  # Default AC
            
        # Some search actions need perception
        elif action == GameAction.SEARCH and any(word in command_lower for word in [
            'hidden', 'secret', 'carefully', 'thoroughly',
            'скрытый', 'тайный', 'внимательно', 'тщательно'
        ]):
            result['requires_roll'] = True
            result['skill_type'] = SkillType.PERCEPTION
            result['estimated_dc'] = dice_engine.determine_difficulty_class(
                command,
                self._build_context_for_dc(context)
            )
        
        return result
    
    def _build_context_for_dc(self, entities: List[BaseEntity]) -> Dict[str, Any]:
        """Build context dictionary for DC determination"""
        context = {}
        
        # Analyze entities to determine difficulty modifiers
        for entity in entities:
            if entity.type == EntityType.NPC:
                # NPC attitude might affect social checks
                context['target_attitude'] = 'neutral'  # TODO: Determine from NPC state
            elif entity.type == EntityType.LOCATION:
                # Location might affect various checks
                if 'dark' in entity.description.lower() or 'shadow' in entity.description.lower():
                    context['lighting'] = 'dark'
                elif 'bright' in entity.description.lower() or 'sunlight' in entity.description.lower():
                    context['lighting'] = 'bright'
        
        return context


# Global instance
semantic_parser = SemanticParser()