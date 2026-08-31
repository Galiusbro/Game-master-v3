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
from infrastructure.command_classification_service import command_classifier, GameContext, GameAction
from domain.entities import EntityType, BaseEntity, SkillType, AbilityScore
from core.dice_engine import dice_engine

logger = logging.getLogger(__name__)


# GameAction enum moved to command_classification_service to avoid circular imports


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
    intent_details: Optional[Dict[str, Any]] = None
    confidence: float = 0.0

    # Skill check specific data
    requires_roll: bool = False
    skill_type: Optional[SkillType] = None
    ability_type: Optional[AbilityScore] = None
    estimated_dc: Optional[int] = None
    context_modifiers: Optional[Dict[str, Any]] = None

    # Context used for resolution
    context_entities: Optional[List[BaseEntity]] = None


class SemanticParser:
    """Main semantic parser class"""
    
    def __init__(self) -> None:
        # Note: Action patterns moved to CommandClassificationService
        # This provides better semantic understanding and multilingual support
        
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
        
        # Entity type patterns - REMOVED, now using semantic classification

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
        
        # 2. Get player context (location, nearby entities) - needed for action detection
        context = await self._get_player_context(world_id, session_id, player_id)
        
        # 3. Detect action intent using modern embedding-based classification
        action, action_confidence = self._detect_action(raw_command, context)
        logger.debug(f"Detected action: {action} (confidence: {action_confidence:.2f})")
        
        # 4. Resolve entities mentioned in command
        entities = await self._resolve_entities(raw_command, context)
        
        # 5. Extract message/details based on action type
        message, details = self._extract_action_details(raw_command, action)
        
        # 6. Check if this action requires dice rolls
        skill_data = self._analyze_skill_requirements(raw_command, action, context)
        
        # 7. Build result with improved confidence calculation
        final_confidence = (action_confidence + entities.get('confidence', 0.0)) / 2
        result = ParsedCommand(
            action=action,
            raw_command=raw_command,
            target_npc_id=entities.get('npc_id'),
            target_location_id=entities.get('location_id'), 
            target_item_id=entities.get('item_id'),
            message=message,
            intent_details=details,
            confidence=final_confidence,
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

    def _detect_action(self, command: str, context: List[BaseEntity]) -> Tuple[GameAction, float]:
        """
        Detect the primary action intent from command using modern embedding-based classification.
        Replaces keyword-based approach with semantic understanding.
        """
        # Determine game context from player's situation
        game_context = self._determine_game_context(context)
        
        # Use the new classification service
        action, confidence = command_classifier.classify_game_action(command, game_context)
        
        logger.debug(f"Action classification: '{command}' -> {action} (confidence: {confidence:.2f}, context: {game_context})")
        
        return action, confidence
    
    def _determine_game_context(self, context: List[BaseEntity]) -> GameContext:
        """Determine the current game context from entities around the player"""
        if not context:
            return GameContext.NEUTRAL
        
        # Check for combat indicators
        for entity in context:
            if entity.type == EntityType.NPC:
                # Check if NPC is hostile (this would need to be implemented in NPC metadata)
                if hasattr(entity, 'is_hostile') and getattr(entity, 'is_hostile', False):
                    return GameContext.COMBAT
                # Check if we're in active dialogue
                if hasattr(entity, 'in_dialogue') and getattr(entity, 'in_dialogue', False):
                    return GameContext.DIALOGUE
            
            elif entity.type == EntityType.LOCATION:
                # Use semantic classification to determine location type and context
                if hasattr(entity, 'description'):
                    location_type, location_conf = command_classifier.classify_location_type(entity.description)
                    
                    if location_type and location_conf > 0.4:
                        # Map location types to game contexts
                        if location_type == "dungeon":
                            return GameContext.DUNGEON
                        elif location_type == "town":
                            return GameContext.TOWN
                        elif location_type in ["wilderness", "outdoor"]:
                            return GameContext.EXPLORATION
                        elif location_type == "underground":
                            return GameContext.DUNGEON  # Underground areas are usually dungeon-like
                        elif location_type == "magical_realm":
                            return GameContext.EXPLORATION  # Magical realms are exploration areas
                        # Indoor locations keep neutral context
        
        return GameContext.NEUTRAL

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
            player = await world_service.get_player(player_id)
            if not player:
                logger.warning(f"Player {player_id} not found")
                return []
            
            context_entities: List[BaseEntity] = [player]
            
            # Get player's location
            try:
                current_loc_id = getattr(player, 'current_location_id', None)
            except Exception:
                current_loc_id = None

            if current_loc_id:
                location = await world_service.get_location(current_loc_id)
                if location:
                    context_entities.append(location)
                    
                    # Get entities in the same location
                    try:
                        nearby = await world_service.get_entity_context(
                            entity_id=current_loc_id,
                            max_depth=1,
                            entity_types=[EntityType.NPC, EntityType.ITEM]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get location neighbors: {e}")
                        nearby = []
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
        
        entities: Dict[str, Any] = {'confidence': 0.0}
        
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
        """Extract potential entity mentions using semantic classification"""
        mentions = []
        
        # Split command into words to check each potential entity
        words = re.findall(r'\b\w+\b', command)
        
        # Check individual words and small phrases
        for i, word in enumerate(words):
            # Single word classification
            entity_type, confidence = command_classifier.classify_entity_type(word)
            if entity_type and confidence > 0.5:
                mentions.append((entity_type, word))
            
            # Two-word phrases
            if i < len(words) - 1:
                phrase = f"{word} {words[i+1]}"
                entity_type, confidence = command_classifier.classify_entity_type(phrase)
                if entity_type and confidence > 0.6:  # Higher threshold for phrases
                    mentions.append((entity_type, phrase))
        
        # Also look for proper names (capitalized words) - still assume these are NPCs
        proper_names = re.findall(r'\b[A-Z][a-z]+\b', command)
        for name in proper_names:
            # Check if it's not already classified as something else
            if not any(name.lower() in mention[1].lower() for mention in mentions):
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
            # Use classification to check if it contains clear actions
            detected_action, confidence = command_classifier.classify_game_action(command)
            
            # If no clear action detected and it's a short response, likely dialogue
            if detected_action == GameAction.UNKNOWN or confidence < 0.5:
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
        
        result: Dict[str, Any] = {
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
            
        # Check for specific skill check indicators using classification
        elif 'attempt' in command_lower or 'try' in command_lower or 'check' in command_lower or 'попытаться' in command_lower:
            result['requires_roll'] = True
            
            # Use action classification to determine skill type
            detected_action, action_confidence = command_classifier.classify_game_action(command)
            
            if detected_action.value in ['stealth'] and action_confidence > 0.5:
                result['skill_type'] = SkillType.STEALTH
            elif detected_action.value in ['persuasion'] and action_confidence > 0.5:
                result['skill_type'] = SkillType.PERSUASION
            elif detected_action.value in ['investigation', 'search'] and action_confidence > 0.5:
                result['skill_type'] = SkillType.INVESTIGATION
            elif detected_action.value in ['athletics'] and action_confidence > 0.5:
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
            
        # For search actions, use content priority to determine if it needs perception
        elif action == GameAction.SEARCH:
            # Use semantic classification to detect if this is a careful/detailed search
            priority, priority_conf = command_classifier.assess_content_priority(command)
            if priority == "high_priority" and priority_conf > 0.4:
                result['requires_roll'] = True
                result['skill_type'] = SkillType.PERCEPTION
                result['estimated_dc'] = dice_engine.determine_difficulty_class(
                    command,
                    self._build_context_for_dc(context)
                )
        
        return result
    
    def _build_context_for_dc(self, entities: List[BaseEntity]) -> Dict[str, Any]:
        """Build context dictionary for DC determination"""
        context: Dict[str, Any] = {}
        
        # Analyze entities to determine difficulty modifiers
        for entity in entities:
            if entity.type == EntityType.NPC:
                # Use semantic classification to determine NPC attitude
                if hasattr(entity, 'description'):
                    attitude, attitude_conf = command_classifier.classify_npc_attitude(entity.description)
                    if attitude and attitude_conf > 0.3:
                        context['target_attitude'] = attitude
                        context['attitude_confidence'] = attitude_conf
                    else:
                        context['target_attitude'] = 'neutral'  # Fallback to neutral
                else:
                    context['target_attitude'] = 'neutral'  # No description available
            elif entity.type == EntityType.LOCATION:
                # Use semantic classification to determine lighting conditions
                lighting_condition, confidence = command_classifier.classify_lighting_condition(entity.description)
                if lighting_condition and confidence > 0.4:
                    context['lighting'] = lighting_condition
                    context['lighting_confidence'] = confidence
        
        return context


# Global instance
semantic_parser = SemanticParser()