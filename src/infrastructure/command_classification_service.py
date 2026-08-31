"""
Command Classification Service - Modern Embedding-based Text Classification
Replaces keyword-based matching with semantic understanding using sentence embeddings.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import re

# Import entity types
from domain.entities import EntityType

# Optional imports for embedding functionality
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]  # optional dependency fallback
    SentenceTransformer = None
    cosine_similarity = None
    EMBEDDINGS_AVAILABLE = False

from domain.entities import SkillType, AbilityScore
from config.settings import settings

logger = logging.getLogger(__name__)


class GameAction(Enum):
    """Types of game actions that can be parsed - copied from semantic_parser to avoid circular imports"""
    DIALOGUE = "dialogue"
    MOVEMENT = "movement" 
    SEARCH = "search"
    COMBAT = "combat"
    TRADE = "trade"
    INVENTORY = "inventory"
    REST = "rest"
    EXPLORE = "explore"
    MAGIC = "magic"
    
    # Skill check actions
    SKILL_CHECK = "skill_check"
    STEALTH = "stealth"
    PERSUASION = "persuasion"
    DECEPTION = "deception"
    INVESTIGATION = "investigation"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    ATHLETICS = "athletics"
    PERCEPTION = "perception"
    
    UNKNOWN = "unknown"


class ClassificationCategory(Enum):
    """Categories for different types of text classification"""
    GAME_ACTION = "game_action"
    SPECIAL_EVENT = "special_event" 
    CONTENT_PRIORITY = "content_priority"
    ABILITY_DETECTION = "ability_detection"
    DIFFICULTY_ASSESSMENT = "difficulty_assessment"
    ENTITY_TYPE = "entity_type"
    LIGHTING_CONDITION = "lighting_condition"
    CONTENT_QUALITY = "content_quality"
    ENTITY_STATE = "entity_state"
    LOCATION_TYPE = "location_type"
    NPC_ATTITUDE = "npc_attitude"
    ACTION_URGENCY = "action_urgency"
    SOCIAL_INTENT = "social_intent"


class GameContext(Enum):
    """Game context types for context-aware classification"""
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    EXPLORATION = "exploration"
    TOWN = "town"
    DUNGEON = "dungeon"
    NEUTRAL = "neutral"


@dataclass
class ClassificationExample:
    """Training example for classification"""
    text: str
    category: str
    subcategory: Optional[str] = None
    confidence: float = 1.0
    language: str = "auto"


@dataclass
class ClassificationResult:
    """Result of text classification"""
    category: str
    subcategory: Optional[str] = None
    confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class CommandClassificationService:
    """
    Centralized service for all text classification needs in the game.
    Uses modern embedding-based approach instead of keyword matching.
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model_name = model_name
        # SentenceTransformer instance once lazily loaded (None until then)
        self.model: Any = None
        self.training_data: Dict[ClassificationCategory, List[ClassificationExample]] = {}
        self.category_embeddings: Dict[str, Any] = {}  # np.ndarray when available
        self._initialize_training_data()
        
    def _load_model(self) -> None:
        """Lazy load the sentence transformer model"""
        # Suppress specific FutureWarning from transformers' BertSdpaSelfAttention about
        # encoder_attention_mask deprecation, which we do not control from here
        import warnings
        warnings.filterwarnings(
            "ignore",
            message=r"`encoder_attention_mask` is deprecated and will be removed in version 4\.55\.0",
            category=FutureWarning,
        )
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Sentence transformers not available, using fallback classification")
            return
            
        if self.model is None:
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence transformer model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                try:
                    # Fallback to simpler model
                    self.model = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("Loaded fallback model: all-MiniLM-L6-v2")
                except Exception as e2:
                    logger.error(f"Failed to load fallback model: {e2}")
                    self.model = None
    
    def _initialize_training_data(self) -> None:
        """Initialize training data for all classification categories from external files"""
        
        # Load data from structured files
        from infrastructure.training_data.game_actions import GameActionTrainingData
        from infrastructure.training_data.entity_types import EntityTypeTrainingData
        from infrastructure.training_data.special_events import SpecialEventTrainingData
        from infrastructure.training_data.content_priority import ContentPriorityTrainingData
        from infrastructure.training_data.ability_detection import AbilityDetectionTrainingData
        from infrastructure.training_data.lighting_conditions import LightingConditionTrainingData
        from infrastructure.training_data.content_quality import ContentQualityTrainingData
        from infrastructure.training_data.entity_states import EntityStateTrainingData
        from infrastructure.training_data.location_types import LocationTypeTrainingData
        from infrastructure.training_data.npc_attitudes import NPCAttitudeTrainingData
        from infrastructure.training_data.action_urgency import ActionUrgencyTrainingData
        from infrastructure.training_data.social_intents import SocialIntentTrainingData
        
        # Load all training data
        self.training_data[ClassificationCategory.GAME_ACTION] = GameActionTrainingData.get_examples()
        self.training_data[ClassificationCategory.ENTITY_TYPE] = EntityTypeTrainingData.get_examples()
        self.training_data[ClassificationCategory.SPECIAL_EVENT] = SpecialEventTrainingData.get_examples()
        self.training_data[ClassificationCategory.CONTENT_PRIORITY] = ContentPriorityTrainingData.get_examples()
        self.training_data[ClassificationCategory.ABILITY_DETECTION] = AbilityDetectionTrainingData.get_examples()
        self.training_data[ClassificationCategory.LIGHTING_CONDITION] = LightingConditionTrainingData.get_examples()
        self.training_data[ClassificationCategory.CONTENT_QUALITY] = ContentQualityTrainingData.get_examples()
        self.training_data[ClassificationCategory.ENTITY_STATE] = EntityStateTrainingData.get_examples()
        self.training_data[ClassificationCategory.LOCATION_TYPE] = LocationTypeTrainingData.get_examples()
        self.training_data[ClassificationCategory.NPC_ATTITUDE] = NPCAttitudeTrainingData.get_examples()
        self.training_data[ClassificationCategory.ACTION_URGENCY] = ActionUrgencyTrainingData.get_examples()
        self.training_data[ClassificationCategory.SOCIAL_INTENT] = SocialIntentTrainingData.get_examples()
        
        logger.info(f"Loaded training data: "
                   f"Game Actions: {len(self.training_data[ClassificationCategory.GAME_ACTION])}, "
                   f"Entity Types: {len(self.training_data[ClassificationCategory.ENTITY_TYPE])}, "
                   f"Special Events: {len(self.training_data[ClassificationCategory.SPECIAL_EVENT])}, "
                   f"Content Priority: {len(self.training_data[ClassificationCategory.CONTENT_PRIORITY])}, "
                   f"Ability Detection: {len(self.training_data[ClassificationCategory.ABILITY_DETECTION])}, "
                   f"Lighting Conditions: {len(self.training_data[ClassificationCategory.LIGHTING_CONDITION])}, "
                   f"Content Quality: {len(self.training_data[ClassificationCategory.CONTENT_QUALITY])}, "
                   f"Entity States: {len(self.training_data[ClassificationCategory.ENTITY_STATE])}, "
                   f"Location Types: {len(self.training_data[ClassificationCategory.LOCATION_TYPE])}, "
                   f"NPC Attitudes: {len(self.training_data[ClassificationCategory.NPC_ATTITUDE])}, "
                   f"Action Urgency: {len(self.training_data[ClassificationCategory.ACTION_URGENCY])}, "
                   f"Social Intent: {len(self.training_data[ClassificationCategory.SOCIAL_INTENT])}")

    def classify_social_intent(self, text: str) -> Tuple[Optional[str], float]:
        """Classify social intent in dialogue (e.g., befriend)"""
        if not EMBEDDINGS_AVAILABLE:
            # Fallback simple rules
            t = text.lower()
            befriend_tokens = ["подруж", "дружить", "be friends", "befriend"]
            if any(tok in t for tok in befriend_tokens):
                return "befriend", 0.5
            return None, 0.0

        try:
            intent, confidence = self._classify_with_embeddings(text, ClassificationCategory.SOCIAL_INTENT)
            if intent == "UNKNOWN":
                return None, 0.0
            return intent, confidence
        except Exception as e:
            logger.warning(f"Social intent classification failed: {e}")
            return None, 0.0

    def _prepare_embeddings(self, category: ClassificationCategory) -> None:
        """Prepare embeddings for a specific category"""
        if category not in self.training_data:
            return

        self._load_model()

        # Group examples by subcategory
        subcategory_texts: Dict[str, List[str]] = {}
        for example in self.training_data[category]:
            subcategory = example.subcategory or example.category
            if subcategory not in subcategory_texts:
                subcategory_texts[subcategory] = []
            subcategory_texts[subcategory].append(example.text)
        
        # Create embeddings for each subcategory
        for subcategory, texts in subcategory_texts.items():
            embeddings = self.model.encode(texts)
            # Use mean embedding as category representation
            mean_embedding = np.mean(embeddings, axis=0)
            self.category_embeddings[f"{category.value}:{subcategory}"] = mean_embedding
    
    def classify_game_action(self, command: str, context: Optional[GameContext] = None) -> Tuple[GameAction, float]:
        """
        Classify a player command into a game action.
        Replaces the keyword-based _detect_action() method.
        """
        # Try embeddings first (main path)
        if EMBEDDINGS_AVAILABLE:
            try:
                action_str, confidence = self._classify_with_embeddings(command, ClassificationCategory.GAME_ACTION, context)
                try:
                    action = GameAction(action_str) if action_str != "UNKNOWN" else GameAction.UNKNOWN
                    return action, confidence
                except ValueError:
                    logger.warning(f"Invalid action returned: {action_str}")
                    return GameAction.UNKNOWN, 0.0
            except Exception as e:
                logger.error(f"Embedding classification failed: {e}")
                # Fall through to fallback
        
        # Fallback only for technical failures
        logger.warning("Using fallback classification due to technical issues")
        return self._fallback_classify_action(command, context)
    
    def _classify_with_embeddings(self, command: str, category: ClassificationCategory, context: Optional[GameContext] = None) -> Tuple[str, float]:
        """Main embedding-based classification logic for any category"""
        if not any(key.startswith(f"{category.value}:") for key in self.category_embeddings):
            self._prepare_embeddings(category)
        
        self._load_model()
        
        if self.model is None:
            raise RuntimeError("Model failed to load")
        
        # Add context to command if provided (only for game actions)
        if category == ClassificationCategory.GAME_ACTION:
            enhanced_command = self._enhance_with_context(command, context)
        else:
            enhanced_command = command
            
        command_embedding = self.model.encode([enhanced_command])[0]
        
        best_result = "UNKNOWN"
        best_confidence = 0.0
        
        category_prefix = f"{category.value}:"
        
        for key, category_embedding in self.category_embeddings.items():
            if not key.startswith(category_prefix):
                continue
                
            similarity = cosine_similarity([command_embedding], [category_embedding])[0][0]
            result_name = key.split(":", 1)[1]
            
            if similarity > best_confidence:
                best_confidence = similarity
                best_result = result_name
        
        # If it's a game action, apply heuristics and context adjustments
        if category == ClassificationCategory.GAME_ACTION:
            # If confidence is too low, try some heuristics to avoid UNKNOWN
            if best_confidence < 0.3:
                try:
                    action = GameAction(best_result) if best_result != "UNKNOWN" else GameAction.UNKNOWN
                    action, best_confidence = self._apply_heuristics(command, action, best_confidence)
                    best_result = action.value
                except ValueError:
                    pass
            
            # Apply context-based adjustments
            try:
                action = GameAction(best_result) if best_result != "UNKNOWN" else GameAction.UNKNOWN
                action = self._apply_context_adjustments(action, command, context, best_confidence)
                best_result = action.value
            except ValueError:
                pass
        
        return best_result, best_confidence
    
    def _apply_heuristics(self, command: str, current_action: GameAction, current_confidence: float) -> Tuple[GameAction, float]:
        """Apply heuristics to improve classification when confidence is low"""
        command_lower = command.lower()
        
        # Simple heuristics to catch obvious cases
        heuristic_patterns = {
            GameAction.TRADE: ["покуп", "куп", "прод", "торг", "buy", "sell", "purchase", "зелье"],
            GameAction.SEARCH: ["осматр", "смотр", "оглядыв", "изуч", "рассматр", "examine", "look", "inspect"],
            GameAction.MOVEMENT: ["иду", "иди", "ехать", "направл", "двигаюсь", "go", "move", "walk", "head"],
            GameAction.DIALOGUE: ["говор", "спраш", "беседую", "общаюсь", "talk", "speak", "ask", "chat"],
            GameAction.COMBAT: ["атак", "удар", "бой", "наступ", "стрел", "attack", "fight", "strike", "shoot"],
            GameAction.MAGIC: ["заклин", "магия", "колд", "лечу", "использую зелье", "cast", "spell", "magic", "heal"],
        }
        
        for action, patterns in heuristic_patterns.items():
            for pattern in patterns:
                if pattern in command_lower:
                    # Found a match, but give it lower confidence than embedding result
                    heuristic_confidence = min(0.6, current_confidence + 0.3)
                    return action, heuristic_confidence
        
        # If no heuristics match, keep original result
        return current_action, current_confidence
    
    def _fallback_classify_action(self, command: str, context: Optional[GameContext] = None) -> Tuple[GameAction, float]:
        """Fallback classification using simple keyword matching when embeddings are not available"""
        command_lower = command.lower()
        
        # Simple keyword patterns (subset of original semantic_parser patterns)
        patterns = {
            GameAction.DIALOGUE: ["говор", "сказать", "спрос", "отвеч", "talk", "speak", "say", "ask", "tell"],
            GameAction.MOVEMENT: ["ид", "ехать", "идти", "перейти", "go", "move", "walk", "travel", "head"],
            GameAction.SEARCH: ["иск", "найти", "смотр", "осматр", "обыск", "search", "look", "find", "examine", "inspect"],
            GameAction.COMBAT: ["атак", "удар", "бой", "сраж", "напасть", "attack", "fight", "combat", "kill", "slay"],
            GameAction.TRADE: ["купить", "продать", "торг", "обмен", "покуп", "buy", "sell", "trade", "purchase", "shop"],
            GameAction.MAGIC: ["заклин", "магия", "свиток", "воскр", "лечен", "зелье", "cast", "spell", "magic", "heal", "potion"],
            GameAction.STEALTH: ["подкрад", "прокрасться", "тихо", "скрытно", "sneak", "stealth", "hide", "quietly"],
        }
        
        best_action = GameAction.UNKNOWN
        best_score = 0
        
        for action, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in command_lower)
            if score > best_score:
                best_score = score
                best_action = action
        
        confidence = min(0.7, best_score * 0.2)  # Lower confidence for fallback
        return best_action, confidence
    
    def classify_batch(
        self, 
        commands: List[str], 
        category: ClassificationCategory,
        contexts: Optional[List[GameContext]] = None
    ) -> List[Tuple[Optional[str], float]]:
        """
        Classify multiple commands at once for better performance.
        """
        if not any(key.startswith(f"{category.value}:") for key in self.category_embeddings):
            self._prepare_embeddings(category)
        
        self._load_model()
        
        # Enhance commands with context if provided
        if contexts:
            enhanced_commands = [
                self._enhance_with_context(cmd, ctx) 
                for cmd, ctx in zip(commands, contexts)
            ]
        else:
            enhanced_commands = commands
        
        # Batch encode all commands
        embeddings = self.model.encode(enhanced_commands)
        results: List[Tuple[Optional[str], float]] = []

        for i, emb in enumerate(embeddings):
            best_match = None
            best_score = 0.0
            
            for key, cat_emb in self.category_embeddings.items():
                if not key.startswith(f"{category.value}:"):
                    continue
                    
                sim = cosine_similarity([emb], [cat_emb])[0][0]
                if sim > best_score:
                    best_score = sim
                    best_match = key.split(":", 1)[1]
            
            results.append((best_match, best_score))
        
        return results
    
    def detect_special_event(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect special events like death or resurrection.
        Replaces keyword-based event detection.
        """
        if not any(key.startswith(f"{ClassificationCategory.SPECIAL_EVENT.value}:") for key in self.category_embeddings):
            self._prepare_embeddings(ClassificationCategory.SPECIAL_EVENT)
        
        self._load_model()
        text_embedding = self.model.encode([text])[0]
        
        best_event = None
        best_confidence = 0.0
        threshold = 0.6  # Minimum confidence for event detection
        
        for key, category_embedding in self.category_embeddings.items():
            if not key.startswith("special_event:"):
                continue
                
            similarity = cosine_similarity([text_embedding], [category_embedding])[0][0]
            
            if similarity > best_confidence and similarity > threshold:
                best_confidence = similarity
                best_event = key.split(":", 1)[1]
        
        return best_event, best_confidence
    
    def assess_content_priority(self, text: str) -> Tuple[str, float]:
        """
        Assess if content has high priority for AI processing.
        Replaces keyword-based priority detection.
        """
        if not any(key.startswith(f"{ClassificationCategory.CONTENT_PRIORITY.value}:") for key in self.category_embeddings):
            self._prepare_embeddings(ClassificationCategory.CONTENT_PRIORITY)
        
        self._load_model()
        text_embedding = self.model.encode([text])[0]
        
        # Check against high priority patterns
        high_priority_key = "content_priority:high_priority"
        if high_priority_key in self.category_embeddings:
            similarity = cosine_similarity([text_embedding], [self.category_embeddings[high_priority_key]])[0][0]
            if similarity > 0.5:
                return "high_priority", similarity
        
        return "normal_priority", 0.0
    
    def detect_ability_focus(self, text: str) -> Tuple[Optional[AbilityScore], float]:
        """
        Detect which ability score a command focuses on.
        Replaces keyword-based ability detection.
        """
        if not any(key.startswith(f"{ClassificationCategory.ABILITY_DETECTION.value}:") for key in self.category_embeddings):
            self._prepare_embeddings(ClassificationCategory.ABILITY_DETECTION)
        
        self._load_model()
        text_embedding = self.model.encode([text])[0]
        
        best_ability = None
        best_confidence = 0.0
        
        for key, category_embedding in self.category_embeddings.items():
            if not key.startswith("ability_detection:"):
                continue
                
            similarity = cosine_similarity([text_embedding], [category_embedding])[0][0]
            ability_name = key.split(":", 1)[1]
            
            try:
                ability = AbilityScore(ability_name)
                if similarity > best_confidence:
                    best_confidence = similarity
                    best_ability = ability
            except ValueError:
                continue
        
        return best_ability, best_confidence
    
    def classify_entity_type(self, text: str) -> Tuple[Optional[EntityType], float]:
        """
        Classify entity type using embeddings.
        
        Args:
            text: Text to classify entity type for
            
        Returns:
            Tuple of (EntityType, confidence) or (None, 0.0) if not found
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_entity_classification(text), 0.3
        
        try:
            entity_type_str, confidence = self._classify_with_embeddings(text, ClassificationCategory.ENTITY_TYPE)
            
            if entity_type_str == "UNKNOWN":
                return None, 0.0
            
            try:
                entity_type = EntityType(entity_type_str)
                return entity_type, confidence
            except ValueError:
                logger.warning(f"Unknown entity type returned: {entity_type_str}")
                return None, 0.0
                
        except Exception as e:
            logger.warning(f"Entity classification failed: {e}")
            return self._fallback_entity_classification(text), 0.3
    
    def _fallback_entity_classification(self, text: str) -> Optional[EntityType]:
        """Simple fallback entity classification when embeddings are not available"""
        text_lower = text.lower()
        
        # Simple keyword patterns (subset of original patterns)
        npc_keywords = ['трактирщик', 'бармен', 'кузнец', 'торговец', 'стражник', 'маг', 'жрец',
                       'bartender', 'innkeeper', 'blacksmith', 'merchant', 'guard', 'wizard', 'priest',
                       'человек', 'эльф', 'гном', 'орк']
        
        location_keywords = ['таверна', 'трактир', 'кузница', 'магазин', 'храм', 'замок', 'дом', 'город',
                           'tavern', 'inn', 'forge', 'shop', 'temple', 'castle', 'house', 'city', 'village',
                           'комната', 'зал', 'улица', 'площадь', 'лес', 'поле', 'гора']
        
        item_keywords = ['меч', 'щит', 'зелье', 'свиток', 'кольцо', 'амулет', 'книга',
                        'sword', 'shield', 'potion', 'scroll', 'ring', 'amulet', 'book',
                        'предмет', 'вещь', 'артефакт', 'сокровище']
        
        for keyword in npc_keywords:
            if keyword in text_lower:
                return EntityType.NPC
        
        for keyword in location_keywords:
            if keyword in text_lower:
                return EntityType.LOCATION
                
        for keyword in item_keywords:
            if keyword in text_lower:
                return EntityType.ITEM
        
        return None
    
    def classify_lighting_condition(self, description: str) -> Tuple[Optional[str], float]:
        """
        Classify lighting conditions from location description.
        
        Args:
            description: Location description text
            
        Returns:
            Tuple of (lighting_condition, confidence) or (None, 0.0) if not determined
            
        Possible lighting conditions: 'dark', 'bright', 'normal', 'magical'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_lighting_classification(description), 0.3
        
        try:
            lighting_condition, confidence = self._classify_with_embeddings(description, ClassificationCategory.LIGHTING_CONDITION)
            
            if lighting_condition == "UNKNOWN":
                return None, 0.0
            
            return lighting_condition, confidence
                
        except Exception as e:
            logger.warning(f"Lighting classification failed: {e}")
            return self._fallback_lighting_classification(description), 0.3
    
    def _fallback_lighting_classification(self, description: str) -> Optional[str]:
        """Simple fallback lighting classification when embeddings are not available"""
        desc_lower = description.lower()
        
        # Simple keyword patterns (subset of original patterns)
        dark_keywords = ['dark', 'shadow', 'dim', 'gloomy', 'murky', 'black', 
                        'темн', 'тень', 'мрак', 'сумрач', 'черн']
        
        bright_keywords = ['bright', 'light', 'sunny', 'brilliant', 'dazzling', 'illuminated',
                          'ярк', 'свет', 'солнеч', 'освещен', 'блест']
        
        magical_keywords = ['magical', 'mystical', 'arcane', 'enchanted', 'divine', 'supernatural',
                           'магическ', 'мистическ', 'волшебн', 'заколдован', 'божествен']
        
        # Check for magical first (most specific)
        for keyword in magical_keywords:
            if keyword in desc_lower:
                return "magical"
        
        # Then check for bright/dark
        for keyword in bright_keywords:
            if keyword in desc_lower:
                return "bright"
                
        for keyword in dark_keywords:
            if keyword in desc_lower:
                return "dark"
        
        # Default to normal if no specific lighting mentioned
        return "normal"
    
    def analyze_content_quality(self, content: str) -> Tuple[str, float]:
        """
        Analyze content quality using semantic understanding.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Tuple of (quality_level, confidence)
            
        Possible quality levels: 'low_quality', 'medium_quality', 'high_quality', 'excellent_quality'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_content_quality_analysis(content), 0.3
        
        try:
            quality_level, confidence = self._classify_with_embeddings(content, ClassificationCategory.CONTENT_QUALITY)
            
            if quality_level == "UNKNOWN":
                return "medium_quality", 0.0
            
            return quality_level, confidence
                
        except Exception as e:
            logger.warning(f"Content quality analysis failed: {e}")
            return self._fallback_content_quality_analysis(content), 0.3
    
    def _fallback_content_quality_analysis(self, content: str) -> str:
        """Simple fallback content quality analysis when embeddings are not available"""
        content_lower = content.lower()
        
        # Simple heuristic indicators
        low_quality_indicators = ['error', 'not found', 'can\'t help', 'sorry', 'undefined', 'lorem ipsum',
                                'что-то происходит', 'ошибка', 'не найден', 'не могу', 'извините']
        
        high_quality_indicators = ['ancient', 'mysterious', 'whisper', 'shimmer', 'glow', 'majestic', 'ethereal',
                                 'древний', 'таинственный', 'шепчет', 'мерцает', 'сияет', 'величественный']
        
        # Check for obvious low quality
        for indicator in low_quality_indicators:
            if indicator in content_lower:
                return "low_quality"
        
        # Check for high quality indicators
        quality_score = sum(1 for indicator in high_quality_indicators if indicator in content_lower)
        
        # Simple length and complexity heuristics
        word_count = len(content.split())
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        
        if quality_score >= 2 and word_count > 20:
            return "high_quality"
        elif word_count > 10 and sentence_count > 1:
            return "medium_quality"
        else:
            return "low_quality"
    
    def detect_entity_state(self, description: str) -> Tuple[str, float]:
        """
        Detect entity state from description text.
        
        Args:
            description: Entity description text
            
        Returns:
            Tuple of (entity_state, confidence)
            
        Possible entity states: 'alive', 'dead', 'unconscious', 'dying'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_entity_state_detection(description), 0.3
        
        try:
            entity_state, confidence = self._classify_with_embeddings(description, ClassificationCategory.ENTITY_STATE)
            
            if entity_state == "UNKNOWN":
                return "alive", 0.0  # Default to alive if uncertain
            
            return entity_state, confidence
                
        except Exception as e:
            logger.warning(f"Entity state detection failed: {e}")
            return self._fallback_entity_state_detection(description), 0.3
    
    def _fallback_entity_state_detection(self, description: str) -> str:
        """Simple fallback entity state detection when embeddings are not available"""
        desc_lower = description.lower()
        
        # Simple keyword patterns for different states
        dead_keywords = ['dead', 'lifeless', 'motionless', 'corpse', 'body', 'deceased', 'fallen',
                        'мёртв', 'безжизненн', 'неподвижн', 'труп', 'тело', 'умерш', 'павш']
        
        dying_keywords = ['dying', 'bleeding', 'wounded', 'poison', 'last breath', 'fading',
                         'умира', 'кровоточ', 'ранен', 'яд', 'последний вздох', 'угаса']
        
        unconscious_keywords = ['unconscious', 'sleeping', 'fainted', 'knocked out', 'stasis',
                               'без сознания', 'спит', 'обморок', 'вырублен', 'стазис']
        
        alive_keywords = ['alive', 'breathing', 'walking', 'talking', 'smiling', 'active',
                         'жив', 'дыш', 'ходит', 'говор', 'улыба', 'активн']
        
        # Check in order of specificity
        for keyword in dead_keywords:
            if keyword in desc_lower:
                return "dead"
        
        for keyword in dying_keywords:
            if keyword in desc_lower:
                return "dying"
                
        for keyword in unconscious_keywords:
            if keyword in desc_lower:
                return "unconscious"
        
        for keyword in alive_keywords:
            if keyword in desc_lower:
                return "alive"
        
        # Default to alive if no specific state detected
        return "alive"
    
    def generate_state_description(self, entity_name: str, state: str, context: str = "") -> str:
        """
        Generate appropriate description text for entity state.
        
        Args:
            entity_name: Name of the entity
            state: Entity state ('alive', 'dead', 'unconscious', 'dying')
            context: Additional context for description
            
        Returns:
            Generated description text
        """
        import random
        
        if state == "dead":
            templates = [
                f"The lifeless body of {entity_name} lies motionless, all warmth of life having departed.",
                f"{entity_name}'s form rests in eternal stillness, no breath escaping their lips.",
                f"Death has claimed {entity_name} - their eyes are closed forever in final peace.",
                f"The cold shell that was once {entity_name} bears no spark of life within.",
                f"{entity_name} has fallen, never again to rise or speak."
            ]
        elif state == "unconscious":
            templates = [
                f"{entity_name} lies unconscious but breathing steadily, lost in deep slumber.",
                f"Knocked unconscious, {entity_name} shows no awareness but vital signs remain strong.",
                f"{entity_name} rests in peaceful unconsciousness, chest rising and falling rhythmically.",
                f"Though unresponsive, {entity_name}'s pulse beats steadily - they live but do not wake.",
                f"{entity_name} sleeps deeply, oblivious to the world around them."
            ]
        elif state == "dying":
            templates = [
                f"{entity_name} draws labored breaths, life ebbing away like sand through fingers.",
                f"The light slowly fades from {entity_name}'s eyes as they hover between life and death.",
                f"{entity_name} fights desperately to cling to life, but time grows short.",
                f"Mortally wounded, {entity_name} lies bleeding heavily, consciousness slipping away.",
                f"{entity_name}'s weakening form struggles against the approaching darkness."
            ]
        else:  # alive
            templates = [
                f"{entity_name} stands alert and vital, eyes bright with life and intelligence.",
                f"Full of energy and awareness, {entity_name} moves with confident purpose.",
                f"{entity_name} breathes easily, their healthy complexion showing vibrant life.",
                f"Very much alive and well, {entity_name} responds with warmth and attention.",
                f"{entity_name}'s lively presence fills the space with dynamic energy."
            ]
        
        return random.choice(templates)
    
    def classify_location_type(self, description: str) -> Tuple[Optional[str], float]:
        """
        Classify location type from description text.
        
        Args:
            description: Location description text
            
        Returns:
            Tuple of (location_type, confidence)
            
        Possible location types: 'dungeon', 'town', 'wilderness', 'indoor', 'underground', 'magical_realm'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_location_classification(description), 0.3
        
        try:
            location_type, confidence = self._classify_with_embeddings(description, ClassificationCategory.LOCATION_TYPE)
            
            if location_type == "UNKNOWN":
                return None, 0.0
            
            return location_type, confidence
                
        except Exception as e:
            logger.warning(f"Location type classification failed: {e}")
            return self._fallback_location_classification(description), 0.3
    
    def _fallback_location_classification(self, description: str) -> Optional[str]:
        """Simple fallback location classification when embeddings are not available"""
        desc_lower = description.lower()
        
        # Keyword patterns for different location types
        dungeon_keywords = ['dungeon', 'cave', 'cavern', 'tomb', 'crypt', 'underground', 'corridor', 'chamber',
                           'подземелье', 'пещера', 'грот', 'гробница', 'склеп', 'коридор', 'камера']
        
        town_keywords = ['town', 'city', 'village', 'market', 'tavern', 'inn', 'shop', 'street', 'square',
                        'город', 'деревня', 'рынок', 'таверна', 'гостиница', 'лавка', 'улица', 'площадь']
        
        wilderness_keywords = ['forest', 'mountain', 'hill', 'plain', 'field', 'meadow', 'tree', 'grass', 'path',
                              'лес', 'гора', 'холм', 'равнина', 'поле', 'луг', 'дерево', 'трава', 'тропа']
        
        indoor_keywords = ['room', 'hall', 'chamber', 'study', 'bedroom', 'kitchen', 'library', 'fireplace',
                          'комната', 'зал', 'кабинет', 'спальня', 'кухня', 'библиотека', 'камин']
        
        magical_keywords = ['magical', 'arcane', 'ethereal', 'plane', 'realm', 'portal', 'enchanted', 'mystical',
                           'магический', 'магия', 'эфирный', 'план', 'мир', 'портал', 'заколдованный']
        
        underground_keywords = ['sewer', 'tunnel', 'passage', 'beneath', 'below', 'underground city',
                               'канализация', 'туннель', 'проход', 'под', 'внизу', 'подземный город']
        
        # Check in order of specificity
        for keyword in magical_keywords:
            if keyword in desc_lower:
                return "magical_realm"
                
        for keyword in dungeon_keywords:
            if keyword in desc_lower:
                return "dungeon"
                
        for keyword in underground_keywords:
            if keyword in desc_lower:
                return "underground"
        
        for keyword in town_keywords:
            if keyword in desc_lower:
                return "town"
                
        for keyword in indoor_keywords:
            if keyword in desc_lower:
                return "indoor"
                
        for keyword in wilderness_keywords:
            if keyword in desc_lower:
                return "wilderness"
        
        # Default to indoor if no specific type detected
        return "indoor"
    
    def classify_npc_attitude(self, description: str) -> Tuple[Optional[str], float]:
        """
        Classify NPC attitude from description text.
        
        Args:
            description: NPC description or behavior text
            
        Returns:
            Tuple of (attitude, confidence)
            
        Possible attitudes: 'friendly', 'neutral', 'hostile', 'suspicious', 'helpful', 'angry', 'fearful'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_npc_attitude_classification(description), 0.3
        
        try:
            attitude, confidence = self._classify_with_embeddings(description, ClassificationCategory.NPC_ATTITUDE)
            
            if attitude == "UNKNOWN":
                return "neutral", 0.0  # Default to neutral if uncertain
            
            return attitude, confidence
                
        except Exception as e:
            logger.warning(f"NPC attitude classification failed: {e}")
            return self._fallback_npc_attitude_classification(description), 0.3
    
    def _fallback_npc_attitude_classification(self, description: str) -> str:
        """Simple fallback NPC attitude classification when embeddings are not available"""
        desc_lower = description.lower()
        
        # Keyword patterns for different attitudes
        hostile_keywords = ['attack', 'hostile', 'aggressive', 'threaten', 'weapon', 'enemy', 'snarl', 'growl',
                           'атак', 'враждебн', 'агрессивн', 'угрожа', 'оружие', 'враг', 'рычит', 'злоб']
        
        angry_keywords = ['angry', 'furious', 'rage', 'shout', 'yell', 'fist', 'indignant', 'storm',
                         'злой', 'яростн', 'гнев', 'кричит', 'орёт', 'кулак', 'негодова', 'мечется']
        
        fearful_keywords = ['afraid', 'scared', 'terrified', 'tremble', 'cower', 'panic', 'flee', 'hide',
                           'боится', 'испуган', 'ужас', 'дрожит', 'съёжив', 'паника', 'бежит', 'прячет']
        
        suspicious_keywords = ['suspicious', 'wary', 'cautious', 'distrust', 'watch', 'guard', 'reluctant',
                              'подозрит', 'настороженн', 'осторожн', 'не доверя', 'следит', 'охраня', 'неохотн']
        
        helpful_keywords = ['help', 'assist', 'guide', 'advice', 'generous', 'support', 'eager', 'willing',
                           'помога', 'содейств', 'проводник', 'совет', 'щедр', 'поддержк', 'готов', 'желает']
        
        friendly_keywords = ['friendly', 'warm', 'smile', 'welcome', 'cheerful', 'kind', 'pleasant', 'happy',
                            'дружелюбн', 'тёпл', 'улыбка', 'приветлив', 'весёл', 'добр', 'приятн', 'счастлив']
        
        # Check in order of specificity (most specific first)
        for keyword in hostile_keywords:
            if keyword in desc_lower:
                return "hostile"
                
        for keyword in angry_keywords:
            if keyword in desc_lower:
                return "angry"
                
        for keyword in fearful_keywords:
            if keyword in desc_lower:
                return "fearful"
                
        for keyword in suspicious_keywords:
            if keyword in desc_lower:
                return "suspicious"
                
        for keyword in helpful_keywords:
            if keyword in desc_lower:
                return "helpful"
                
        for keyword in friendly_keywords:
            if keyword in desc_lower:
                return "friendly"
        
        # Default to neutral if no specific attitude detected
        return "neutral"
    
    def classify_action_urgency(self, command: str) -> Tuple[Optional[str], float]:
        """
        Classify action urgency from command text.
        
        Args:
            command: Player command text
            
        Returns:
            Tuple of (urgency_level, confidence)
            
        Possible urgency levels: 'casual', 'careful', 'urgent', 'desperate'
        """
        if not EMBEDDINGS_AVAILABLE:
            return self._fallback_action_urgency_classification(command), 0.3
        
        try:
            urgency, confidence = self._classify_with_embeddings(command, ClassificationCategory.ACTION_URGENCY)
            
            if urgency == "UNKNOWN":
                return "casual", 0.0  # Default to casual if uncertain
            
            return urgency, confidence
                
        except Exception as e:
            logger.warning(f"Action urgency classification failed: {e}")
            return self._fallback_action_urgency_classification(command), 0.3
    
    def _fallback_action_urgency_classification(self, command: str) -> str:
        """Simple fallback action urgency classification when embeddings are not available"""
        cmd_lower = command.lower()
        
        # Keyword patterns for different urgency levels
        desperate_keywords = ['frantically', 'desperately', 'wildly', 'panic', 'scream', 'throw myself', 'claw',
                             'отчаянно', 'дико', 'паника', 'кричу', 'бросаюсь', 'царапаю', 'слепой']
        
        urgent_keywords = ['quickly', 'fast', 'rush', 'hurry', 'immediately', 'swift', 'rapid', 'sprint',
                          'быстро', 'спешу', 'тороплюсь', 'немедленно', 'стремительно', 'бегу']
        
        careful_keywords = ['carefully', 'slowly', 'cautiously', 'quietly', 'methodically', 'study', 'plan',
                           'осторожно', 'медленно', 'тихо', 'методично', 'изучаю', 'планирую', 'обдумываю']
        
        casual_keywords = ['walk', 'chat', 'browse', 'sit', 'enjoy', 'tell', 'ask', 'look around',
                          'подхожу', 'болтаю', 'просматриваю', 'присаживаюсь', 'наслаждаюсь', 'рассказываю']
        
        # Check in order of specificity (most urgent first)
        for keyword in desperate_keywords:
            if keyword in cmd_lower:
                return "desperate"
                
        for keyword in urgent_keywords:
            if keyword in cmd_lower:
                return "urgent"
                
        for keyword in careful_keywords:
            if keyword in cmd_lower:
                return "careful"
                
        for keyword in casual_keywords:
            if keyword in cmd_lower:
                return "casual"
        
        # Default to casual if no specific urgency detected
        return "casual"
    
    def calculate_urgency_dc_modifier(self, urgency: str, base_action: str) -> int:
        """
        Calculate DC modifier based on action urgency.
        
        Args:
            urgency: Urgency level ('casual', 'careful', 'urgent', 'desperate')
            base_action: Base action type for context
            
        Returns:
            DC modifier (-5 to +5)
        """
        modifiers = {
            'careful': -2,    # Easier DC for careful actions
            'casual': 0,      # No modifier for normal actions
            'urgent': +2,     # Harder DC for rushed actions
            'desperate': +4   # Much harder DC for desperate actions
        }
        
        base_modifier = modifiers.get(urgency, 0)
        
        # Special adjustments based on action type
        if base_action in ['stealth', 'investigation', 'sleight_of_hand']:
            # These actions benefit more from being careful
            if urgency == 'careful':
                base_modifier = -3
            elif urgency == 'desperate':
                base_modifier = +5  # These actions suffer heavily from panic
        
        elif base_action in ['athletics', 'combat']:
            # Physical actions can sometimes benefit from urgency
            if urgency == 'urgent':
                base_modifier = +1  # Less penalty for urgent physical actions
                
        elif base_action in ['persuasion', 'deception']:
            # Social actions need the right timing
            if urgency == 'desperate':
                base_modifier = +3  # Desperation in social situations is bad but not as bad
        
        return base_modifier
    
    def add_training_example(self, category: ClassificationCategory, example: ClassificationExample) -> None:
        """Add a new training example and update embeddings"""
        if category not in self.training_data:
            self.training_data[category] = []
        
        self.training_data[category].append(example)
        
        # Invalidate cached embeddings for this category
        keys_to_remove = [key for key in self.category_embeddings.keys() if key.startswith(f"{category.value}:")]
        for key in keys_to_remove:
            del self.category_embeddings[key]
        
        logger.info(f"Added training example for {category.value}: {example.text}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classification service statistics"""
        stats: Dict[str, Any] = {
            "model_name": self.model_name,
            "model_loaded": self.model is not None,
            "categories": {}
        }

        for category, examples in self.training_data.items():
            subcategories: Dict[str, int] = {}
            for example in examples:
                subcategory = example.subcategory or example.category
                subcategories[subcategory] = subcategories.get(subcategory, 0) + 1
            
            stats["categories"][category.value] = {
                "total_examples": len(examples),
                "subcategories": subcategories
            }
        
        return stats
    
    def _enhance_with_context(self, command: str, context: Optional[GameContext]) -> str:
        """Enhance command with context information for better classification"""
        if not settings.enable_context_classification:
            return command

        if not context or context == GameContext.NEUTRAL:
            return command
        
        # Add context prefix to help with classification
        context_prefixes = {
            GameContext.COMBAT: "During combat: ",
            GameContext.DIALOGUE: "In conversation: ",
            GameContext.EXPLORATION: "While exploring: ",
            GameContext.TOWN: "In town: ",
            GameContext.DUNGEON: "In dungeon: "
        }
        
        prefix = context_prefixes.get(context, "")
        return f"{prefix}{command}"
    
    def _apply_context_adjustments(
        self, 
        action: GameAction, 
        command: str, 
        context: Optional[GameContext],
        confidence: float
    ) -> GameAction:
        """Apply context-based adjustments to classification results"""
        # Without context enhancement these re-classifications would embed the
        # very same string again: no possible change, just wasted work.
        if not settings.enable_context_classification:
            return action

        if not context or confidence < 0.4:  # Don't adjust low-confidence results
            return action
        
        command_lower = command.lower()
        
        # Context-specific adjustments
        if context == GameContext.COMBAT:
            # In combat, movement commands might be combat maneuvers
            # Re-classify with combat context to catch aggressive movement
            combat_enhanced = self._enhance_with_context(command, GameContext.COMBAT)
            combat_action_str, combat_conf = self._classify_with_embeddings(combat_enhanced, ClassificationCategory.GAME_ACTION)
            try:
                combat_action = GameAction(combat_action_str) if combat_action_str != "UNKNOWN" else GameAction.UNKNOWN
                if combat_action == GameAction.COMBAT and combat_conf > confidence + 0.1:
                    return GameAction.COMBAT
            except ValueError:
                pass
                
        elif context == GameContext.DIALOGUE:
            # In dialogue, re-classify to catch conversational actions
            dialogue_enhanced = self._enhance_with_context(command, GameContext.DIALOGUE)
            dialogue_action_str, dialogue_conf = self._classify_with_embeddings(dialogue_enhanced, ClassificationCategory.GAME_ACTION)
            try:
                dialogue_action = GameAction(dialogue_action_str) if dialogue_action_str != "UNKNOWN" else GameAction.UNKNOWN
                if dialogue_action == GameAction.DIALOGUE and dialogue_conf > confidence + 0.1:
                    return GameAction.DIALOGUE
            except ValueError:
                pass
                
        elif context == GameContext.EXPLORATION:
            # In exploration, re-classify to catch investigative actions
            exploration_enhanced = self._enhance_with_context(command, GameContext.EXPLORATION)
            exploration_action_str, exploration_conf = self._classify_with_embeddings(exploration_enhanced, ClassificationCategory.GAME_ACTION)
            try:
                exploration_action = GameAction(exploration_action_str) if exploration_action_str != "UNKNOWN" else GameAction.UNKNOWN
                if exploration_action == GameAction.SEARCH and exploration_conf > confidence + 0.1:
                    return GameAction.SEARCH
            except ValueError:
                pass
        
        return action


# Global instance
command_classifier = CommandClassificationService()