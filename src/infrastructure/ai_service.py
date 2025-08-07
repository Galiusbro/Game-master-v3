"""
AI Service for Game Master V3
Handles LLM interactions with context assembly and anti-hallucination guards
"""
import asyncio
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union, AsyncIterator
from uuid import UUID

import openai
import tiktoken
from pydantic import BaseModel, Field

from config.settings import settings
from domain.entities import BaseEntity, EntityType, NPC, NPCPersonality, Player
from monitoring.metrics import track_ai_operation
from infrastructure.command_classification_service import command_classifier

logger = logging.getLogger(__name__)


class AIResponse(BaseModel):
    """Structured AI response with metadata"""
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    tokens_used: int
    response_time: float
    hallucination_detected: bool = False
    cited_entities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PromptTemplate(BaseModel):
    """Template for AI prompts"""
    system_prompt: str
    user_template: str
    max_tokens: int = 1000
    temperature: float = 0.7
    anti_hallucination_instructions: str = ""


class AIService:
    """Central AI service for Game Master operations"""
    
    def __init__(self):
        self.client = None
        self.tokenizer = None
        self.is_initialized = False
        self.cache_service = None
        
        # Prompt templates
        self.templates = {
            "npc_dialogue": PromptTemplate(
                system_prompt="""You are an AI Game Master controlling NPCs in a fantasy RPG world.
You must stay strictly in character and only use information provided in the context.

CRITICAL RULES:
- Never invent new facts, locations, or characters not mentioned in context
- Always respond as the specific NPC described
- Maintain personality consistency throughout the conversation  
- If you lack information to answer something, say so in character
- Reference only entities and facts explicitly provided in context

Your responses should be immersive, in-character dialogue that advances the story.""",
                user_template="""CONTEXT:
{context}

NPC PROFILE:
{npc_profile}

CURRENT SITUATION:
{situation}

PLAYER ACTION: {player_action}

Respond as {npc_name} would, staying true to their personality and the provided context. Format your response as direct dialogue.""",
                max_tokens=1200,
                temperature=0.8,
                anti_hallucination_instructions="Only reference entities, locations, and facts explicitly mentioned in the provided context. Do not invent new information."
            ),
            
            "world_description": PromptTemplate(
                system_prompt="""You are a Master Storyteller and AI Game Master crafting an immersive fantasy RPG experience.
Your mission is to create rich, vivid, and captivating descriptions that transport players into a living world.

EXCELLENCE PRINCIPLES:
- Create cinematic, multi-sensory descriptions (sight, sound, smell, touch, taste)
- Use only information explicitly provided in the context - never invent facts
- Layer details: immediate → atmospheric → character-specific observations
- Maintain perfect consistency with established world lore
- Adapt descriptions to character knowledge (wizards notice magic, rogues spot traps)
- Build appropriate mood and tension for each situation

DESCRIPTION MASTERY:
1. IMMEDIATE IMPACT: What hits their senses first?
2. VISUAL RICHNESS: Colors, textures, lighting, movement
3. ATMOSPHERIC DEPTH: Sounds, smells, temperature, mood
4. CHARACTER INSIGHTS: What would their class/background notice?
5. INTERACTIVE POSSIBILITIES: What can they examine or interact with?

Transform every moment into an memorable scene worthy of an epic fantasy novel.""",
                user_template="""COMPREHENSIVE WORLD CONTEXT:
{context}

ENTITIES AND CHARACTERS PRESENT:
{entities}

CHARACTER BACKGROUND: Consider the player's class, skills, and background for specialized observations.

PLAYER REQUEST: {request}

{dice_context}

Craft a masterful, immersive description that brings this scene to life. Layer rich sensory details and character-specific insights while remaining absolutely faithful to the provided context. Make this moment unforgettable.""",
                max_tokens=1000,
                temperature=0.7,
                anti_hallucination_instructions="Describe only elements explicitly mentioned in context. Use character expertise to highlight relevant details, but never invent new information."
            ),
            
            "dice_outcome_narration": PromptTemplate(
                system_prompt="""You are an AI Game Master narrating the outcome of dice-based actions in a fantasy RPG.
Your job is to describe what happens based on the dice roll results and context.

CRITICAL RULES:
- The dice have already determined SUCCESS or FAILURE - you narrate the result
- For SUCCESS: Describe how the action succeeds, considering the roll quality (high vs low success)
- For FAILURE: Describe how the action fails, considering the roll quality (near miss vs complete failure)
- For CRITICAL SUCCESS (Natural 20): Make it spectacular and memorable
- For CRITICAL FAILURE (Natural 1): Make it dramatically bad but not character-breaking
- Stay consistent with established world facts and character abilities
- Only reference entities and facts from the provided context
- Make the narration cinematic but grounded in the world""",
                user_template="""DICE ROLL RESULTS:
{dice_results}

WORLD CONTEXT:
{context}

CHARACTER INFO:
{character_info}

ACTION ATTEMPTED: {action_description}

Narrate what happens as a result of this dice roll. Be vivid and engaging while respecting the success/failure outcome.""",
                max_tokens=800,
                temperature=0.8,
                anti_hallucination_instructions="Only describe outcomes consistent with the dice results and established context. Do not invent new world elements."
            ),
            
            "action_resolution": PromptTemplate(
                system_prompt="""You are an AI Game Master resolving player actions in a fantasy RPG.
Determine outcomes based on provided context, character abilities, and world state.

CRITICAL RULES:
- Base all outcomes on provided context and character stats
- Consider character abilities, world rules, and current situation
- Provide clear, logical consequences for actions
- Do not create new world elements not in context
- Be fair but challenging in outcome determination""",
                user_template="""WORLD STATE:
{world_state}

PLAYER CHARACTER:
{player_character}

ATTEMPTED ACTION: {action}

RELEVANT CONTEXT:
{context}

Determine the outcome of this action, explaining the reasoning and any consequences.""",
                max_tokens=900,
                temperature=0.6,
                anti_hallucination_instructions="Base outcomes only on provided character stats, world rules, and context. Do not invent new mechanics or rules."
            )
        }
    
    async def initialize(self) -> None:
        """Initialize AI service with OpenAI client"""
        try:
            # Initialize OpenAI client
            openai.api_key = settings.openai_api_key
            self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Initialize tokenizer for token counting
            try:
                self.tokenizer = tiktoken.encoding_for_model(settings.llm_model)
            except KeyError:
                # Fallback to GPT-4 tokenizer for newer models
                logger.warning(f"Model {settings.llm_model} not found in tiktoken, using GPT-4 tokenizer as fallback")
                self.tokenizer = tiktoken.encoding_for_model("gpt-4")
            
            # Initialize cache service
            try:
                from infrastructure.cache_service import cache_service
                self.cache_service = cache_service
                logger.info("AI Service cache integration enabled")
            except Exception as e:
                logger.warning(f"AI Service cache integration failed: {e}")
                self.cache_service = None
            
            # Test connection
            await self._test_connection()
            
            self.is_initialized = True
            logger.info("AI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
            raise
    
    async def _test_connection(self) -> None:
        """Test OpenAI API connection"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            logger.info("OpenAI API connection successful")
        except Exception as e:
            logger.error(f"OpenAI API connection failed: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if not self.tokenizer:
            # Rough estimation if tokenizer not available
            return len(text.split()) * 1.3
        return len(self.tokenizer.encode(text))
    
    def analyze_prompt_tokens(self, messages: List[Dict]) -> Dict[str, int]:
        """Analyze token usage breakdown in prompt"""
        breakdown = {}
        total = 0
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tokens = self.count_tokens(content)
            
            breakdown[role] = breakdown.get(role, 0) + tokens
            total += tokens
        
        breakdown["total"] = total
        return breakdown
    
    def _create_context_hash(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Create a hash for AI request context for caching"""
        context_data = {
            "messages": messages,
            "model": settings.llm_model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Create a stable hash
        content = str(context_data)
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def _get_cached_response(self, context_hash: str) -> Optional[AIResponse]:
        """Get cached AI response"""
        if not self.cache_service:
            return None
        
        try:
            cached_data = await self.cache_service.get_ai_response(context_hash)
            if cached_data:
                logger.debug(f"AI Cache HIT: {context_hash}")
                # Return cached response with zero response time (cached)
                cached_data["response_time"] = 0.001  # Minimal cache access time
                return AIResponse(**cached_data)
        except Exception as e:
            logger.warning(f"AI cache get error: {e}")
        
        logger.debug(f"AI Cache MISS: {context_hash}")
        return None
    
    async def _cache_response(self, context_hash: str, response: AIResponse) -> None:
        """Cache AI response"""
        if not self.cache_service:
            return
        
        try:
            # Cache the response data (excluding response_time for future calls)
            cache_data = response.dict()
            await self.cache_service.set_ai_response(context_hash, cache_data)
            logger.debug(f"AI response cached: {context_hash}")
        except Exception as e:
            logger.warning(f"AI cache set error: {e}")
    
    def _optimize_context_messages(self, messages: List[Dict], target_tokens: int) -> List[Dict]:
        """Smart context optimization preserving quality"""
        optimized = []
        current_tokens = 0
        
        # Always keep system prompts (they're usually small and critical)
        for msg in messages:
            if msg.get("role") == "system":
                tokens = self.count_tokens(msg["content"])
                optimized.append(msg)
                current_tokens += tokens
        
        # Smart optimization of user messages
        for msg in messages:
            if msg.get("role") == "user":
                content = msg["content"]
                tokens = self.count_tokens(content)
                
                if current_tokens + tokens > target_tokens:
                    # Smart context optimization
                    if "CONTEXT:" in content:
                        content = self._smart_truncate_context(content, target_tokens - current_tokens)
                    else:
                        # If no context section, just limit the entire content
                        content = self._truncate_text_smartly(content, target_tokens - current_tokens)
                
                optimized.append({"role": msg["role"], "content": content})
                current_tokens += self.count_tokens(content)
        
        logger.info(f"Smart context optimized: {self.analyze_prompt_tokens(messages)['total']} -> {self.analyze_prompt_tokens(optimized)['total']} tokens")
        return optimized
    
    def _smart_truncate_context(self, content: str, available_tokens: int) -> str:
        """Smart context truncation preserving important information"""
        parts = content.split("CONTEXT:")
        if len(parts) < 2:
            return content
        
        prefix = parts[0]
        context_part = parts[1]
        
        prefix_tokens = self.count_tokens(prefix)
        remaining_tokens = available_tokens - prefix_tokens - 50  # Reserve 50 for formatting
        
        if remaining_tokens < 100:
            # Not enough space for meaningful context
            return prefix + "CONTEXT:\n[Context removed due to space constraints]\n"
        
        # Parse context into entities and prioritize
        context_lines = context_part.split('\n')
        important_lines = []
        regular_lines = []
        
        for line in context_lines:
            line = line.strip()
            if not line:
                continue
                
            # Prioritize lines using modern content classification
            priority, confidence = command_classifier.assess_content_priority(line)
            
            if priority == "high_priority" and confidence > 0.4:
                important_lines.append(line)
            else:
                regular_lines.append(line)
        
        # Build optimized context
        optimized_context = ""
        used_tokens = 0
        
        # Add important lines first
        for line in important_lines:
            test_context = optimized_context + line + "\n"
            tokens = self.count_tokens(test_context)
            if tokens < remaining_tokens:
                optimized_context = test_context
                used_tokens = tokens
            else:
                break
        
        # Add regular lines if space allows
        for line in regular_lines:
            test_context = optimized_context + line + "\n"
            tokens = self.count_tokens(test_context)
            if tokens < remaining_tokens:
                optimized_context = test_context
                used_tokens = tokens
            else:
                break
        
        # Add truncation notice if we removed content
        if len(important_lines) + len(regular_lines) > optimized_context.count('\n'):
            optimized_context += "[Additional context available but truncated for efficiency]\n"
        
        result = prefix + "CONTEXT:\n" + optimized_context
        logger.info(f"Smart truncation: preserved {used_tokens}/{self.count_tokens(context_part)} context tokens")
        return result
    
    def _truncate_text_smartly(self, text: str, available_tokens: int) -> str:
        """Smart text truncation preserving sentence structure"""
        if self.count_tokens(text) <= available_tokens:
            return text
        
        # Try to truncate at sentence boundaries
        sentences = text.split('.')
        truncated = ""
        
        for sentence in sentences:
            test_text = truncated + sentence + "."
            if self.count_tokens(test_text) < available_tokens - 20:  # Reserve space for truncation notice
                truncated = test_text
            else:
                break
        
        if not truncated:
            # Fallback: character-level truncation
            target_chars = int(available_tokens * 4)  # Rough estimate
            truncated = text[:target_chars]
        
        return truncated + " [Content truncated]"
    
    def build_npc_profile_text(self, npc: NPC) -> str:
        """Build comprehensive NPC profile text for prompts"""
        personality = npc.personality
        state = npc.current_state
        
        profile_parts = [
            f"Name: {npc.name}",
            f"Description: {npc.description}",
            "",
            "PERSONALITY:",
            f"Core Traits: {', '.join(personality.core_traits)}",
            f"Speech Patterns: {', '.join(personality.speech_patterns)}",
            f"Likes: {', '.join(personality.likes)}",
            f"Dislikes: {', '.join(personality.dislikes)}",
            f"Fears: {', '.join(personality.fears)}",
            f"Goals: {', '.join(personality.goals)}",
            "",
            f"Backstory: {personality.backstory}",
            "",
            "EXAMPLE PHRASES:",
        ]
        
        for phrase in personality.example_phrases:
            profile_parts.append(f'- "{phrase}"')
        
        profile_parts.extend([
            "",
            "CURRENT STATE:",
            f"Mood: {state.current_mood}",
            f"Activity: {state.current_activity}",
        ])
        
        return "\n".join(profile_parts)
    
    def validate_response_entities(self, response: str, context_entities: List[BaseEntity]) -> Tuple[bool, List[str]]:
        """Validate that response only references entities from context"""
        warnings = []
        hallucination_detected = False
        
        # Extract potential entity names from response (simple regex)
        potential_names = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', response)
        
        # Get valid entity names from context
        valid_names = {entity.name for entity in context_entities}
        
        # Check for references to entities not in context
        for name in potential_names:
            if len(name) > 2 and name not in valid_names:
                # Simple heuristic: if it looks like a proper noun and isn't in context
                if not any(common in name.lower() for common in ['the', 'and', 'you', 'your', 'this', 'that']):
                    warnings.append(f"Potential hallucination: '{name}' not found in context")
                    hallucination_detected = True
        
        return hallucination_detected, warnings
    
    @track_ai_operation("npc_dialogue", settings.llm_model)
    async def generate_npc_dialogue(
        self,
        npc: NPC,
        player_action: str,
        context_entities: List[BaseEntity],
        situation: str = "",
        max_retries: int = 2
    ) -> AIResponse:
        """Generate NPC dialogue response"""
        start_time = time.time()
        
        # Build context from entities
        context_parts = []
        for entity in context_entities:
            if entity.id != npc.id:  # Don't include self in context
                context_parts.append(f"{entity.type.value.title()}: {entity.name} - {entity.description}")
        
        context = "\n".join(context_parts) if context_parts else "No other entities in immediate context."
        
        # Build NPC profile
        npc_profile = self.build_npc_profile_text(npc)
        
        # Get template
        template = self.templates["npc_dialogue"]
        
        # Build prompt
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": template.user_template.format(
                context=context,
                npc_profile=npc_profile,
                situation=situation or "Normal conversation",
                player_action=player_action,
                npc_name=npc.name
            )}
        ]
        
        # Add anti-hallucination reminder
        if template.anti_hallucination_instructions:
            messages.append({
                "role": "system", 
                "content": f"REMINDER: {template.anti_hallucination_instructions}"
            })
        
        # Analyze and optimize context before caching/calling
        token_breakdown = self.analyze_prompt_tokens(messages)
        logger.info(f"NPC dialogue tokens - Total: {token_breakdown['total']}, System: {token_breakdown.get('system', 0)}, User: {token_breakdown.get('user', 0)}")
        
        # Optimize if context is too large (minimal optimization for maximum quality)
        if token_breakdown['total'] > settings.context_max_tokens * 0.95:
            logger.warning(f"Large context detected ({token_breakdown['total']} tokens), optimizing...")
            messages = self._optimize_context_messages(messages, int(settings.context_max_tokens * 0.95))
        
        # Check cache first
        context_hash = self._create_context_hash(messages, template.temperature, template.max_tokens)
        cached_response = await self._get_cached_response(context_hash)
        if cached_response:
            return cached_response
        
        try:
            # Make API call
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=template.max_tokens,
                temperature=template.temperature
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            response_time = time.time() - start_time
            
            # Validate response
            hallucination_detected, warnings = self.validate_response_entities(
                content, context_entities
            )
            
            # Extract cited entities (simple implementation)
            cited_entities = [entity.name for entity in context_entities if entity.name.lower() in content.lower()]
            
            ai_response = AIResponse(
                content=content,
                confidence=0.9 if not hallucination_detected else 0.6,
                tokens_used=tokens_used,
                response_time=response_time,
                hallucination_detected=hallucination_detected,
                cited_entities=cited_entities,
                warnings=warnings
            )
            
            # Cache the response for future use
            await self._cache_response(context_hash, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return AIResponse(
                content=f"*{npc.name} seems distracted and unable to respond properly.*",
                confidence=0.0,
                tokens_used=0,
                response_time=time.time() - start_time,
                hallucination_detected=True,
                warnings=[f"AI generation failed: {str(e)}"]
            )
    
    @track_ai_operation("world_description", settings.llm_model)
    async def generate_world_description(
        self,
        player: Player,
        request: str,
        context_entities: List[BaseEntity],
        dice_context: str = "",
        max_retries: int = 2
    ) -> AIResponse:
        """Generate world/location description"""
        start_time = time.time()
        
        # Build context
        context_parts = []
        entities_parts = []
        
        logger.info(f"Building world context with {len(context_entities)} entities:")
        
        # Add hardcoded dead Barliman to context
        barliman_id = "76afb2a3-894b-4d64-b430-2eb3c2aff980"
        barliman_in_context = any(str(entity.id) == barliman_id for entity in context_entities)
        
        if barliman_in_context:
            logger.info("🪦 Adding dead Barliman to world context")
            context_parts.append("Npc: Barliman Butterbur (DECEASED)")
            context_parts.append("Description: The lifeless body of the former innkeeper lies motionless on the tavern floor. His cheerful smile is gone forever, replaced by the cold stillness of death. Blood stains the wooden boards beneath him.")
            context_parts.append("Status: This NPC has died and cannot speak or interact. Their corpse is a grim reminder of recent violence.")
            context_parts.append("")
            entities_parts.append("- Barliman Butterbur (deceased npc)")
        
        for entity in context_entities:
            # Skip Barliman since we handled him above
            if str(entity.id) == barliman_id:
                continue
                
            logger.debug(f"  - {entity.type.value}: {entity.name}")
            
            # Special handling for dead NPCs (for future cases)
            if (entity.type == EntityType.NPC and 
                hasattr(entity, 'is_alive') and 
                not entity.is_alive):
                context_parts.append(f"{entity.type.value.title()}: {entity.name} (DECEASED)")
                context_parts.append(f"Description: {entity.description}")
                context_parts.append(f"Status: This NPC has died and cannot speak or interact. Their body may still be present.")
                context_parts.append("")
                entities_parts.append(f"- {entity.name} (deceased {entity.type.value})")
            else:
                context_parts.append(f"{entity.type.value.title()}: {entity.name}")
                context_parts.append(f"Description: {entity.description}")
                context_parts.append("")
                entities_parts.append(f"- {entity.name} ({entity.type.value})")
        
        context = "\n".join(context_parts)
        entities = "\n".join(entities_parts)
        
        logger.info(f"Final context length: {len(context)} chars, {len(entities_parts)} entities")
        
        template = self.templates["world_description"]
        
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": template.user_template.format(
                context=context,
                entities=entities,
                request=request,
                dice_context=dice_context
            )}
        ]
        
        # Analyze and optimize context before caching/calling
        token_breakdown = self.analyze_prompt_tokens(messages)
        logger.info(f"World description tokens - Total: {token_breakdown['total']}, System: {token_breakdown.get('system', 0)}, User: {token_breakdown.get('user', 0)}")
        
        # Optimize if context is too large (minimal optimization for maximum quality)
        if token_breakdown['total'] > settings.context_max_tokens * 0.95:
            logger.warning(f"Large world context detected ({token_breakdown['total']} tokens), optimizing...")
            messages = self._optimize_context_messages(messages, int(settings.context_max_tokens * 0.95))
        
        # Check cache first
        context_hash = self._create_context_hash(messages, template.temperature, template.max_tokens)
        cached_response = await self._get_cached_response(context_hash)
        if cached_response:
            return cached_response
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=template.max_tokens,
                temperature=template.temperature
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            response_time = time.time() - start_time
            
            # Validate response
            hallucination_detected, warnings = self.validate_response_entities(
                content, context_entities
            )
            
            cited_entities = [entity.name for entity in context_entities if entity.name.lower() in content.lower()]
            
            ai_response = AIResponse(
                content=content,
                confidence=0.9 if not hallucination_detected else 0.7,
                tokens_used=tokens_used,
                response_time=response_time,
                hallucination_detected=hallucination_detected,
                cited_entities=cited_entities,
                warnings=warnings
            )
            
            # Cache the response for future use
            await self._cache_response(context_hash, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"World description generation failed: {e}")
            return AIResponse(
                content="The area is shrouded in mystery, and details are unclear at this time.",
                confidence=0.0,
                tokens_used=0,
                response_time=time.time() - start_time,
                hallucination_detected=True,
                warnings=[f"Generation failed: {str(e)}"]
            )
    
    @track_ai_operation("dice_outcome", settings.llm_model)
    async def generate_dice_outcome_narration(
        self,
        dice_results: str,
        action_description: str,
        player: Player,
        context_entities: List[BaseEntity],
        max_retries: int = 2
    ) -> AIResponse:
        """Generate narrative description of dice roll outcomes"""
        start_time = time.time()
        
        # Build context text
        context_parts = []
        for entity in context_entities:
            context_parts.append(f"{entity.type.value.title()}: {entity.name}")
            context_parts.append(f"Description: {entity.description}")
            context_parts.append("")
        
        context_text = "\n".join(context_parts) if context_parts else "No additional context available."
        
        # Build character info
        character_info = f"""
Name: {player.name}
Level: {player.stats.level}
Class: {player.stats.character_class.value if player.stats.character_class else 'Unknown'}
Current HP: {player.stats.current_hit_points}/{player.stats.max_hit_points}
Armor Class: {player.stats.armor_class}
"""
        
        template = self.templates["dice_outcome_narration"]
        
        try:
            # Prepare prompt
            user_prompt = template.user_template.format(
                dice_results=dice_results,
                context=context_text,
                character_info=character_info,
                action_description=action_description
            )
            
            logger.debug(f"Generating dice outcome narration for: {action_description}")
            
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": template.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=template.max_tokens,
                temperature=template.temperature
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            response_time = time.time() - start_time
            
            # Validate response
            hallucination_detected, warnings = self.validate_response_entities(
                content, context_entities
            )
            
            # Extract cited entities
            cited_entities = [entity.name for entity in context_entities if entity.name.lower() in content.lower()]
            
            return AIResponse(
                content=content,
                confidence=0.9 if not hallucination_detected else 0.7,
                tokens_used=tokens_used,
                response_time=response_time,
                hallucination_detected=hallucination_detected,
                cited_entities=cited_entities,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Dice outcome narration generation failed: {e}")
            return AIResponse(
                content=f"You attempt {action_description}. The outcome becomes clear through your actions.",
                confidence=0.0,
                tokens_used=0,
                response_time=time.time() - start_time,
                hallucination_detected=True,
                warnings=[f"Generation failed: {str(e)}"]
            )
    
    # STREAMING METHODS FOR REAL-TIME RESPONSES
    async def stream_npc_dialogue(
        self,
        npc: BaseEntity,
        player_action: str,
        context: str,
        situation: str = "ongoing conversation"
    ) -> AsyncIterator[str]:
        """Stream NPC dialogue response in real-time"""
        template = self.templates["npc_dialogue"]
        
        npc_profile = self.build_npc_profile_text(npc) if hasattr(npc, 'personality') else f"Name: {npc.name}\nDescription: {npc.description}"
        
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": template.user_template.format(
                context=context,
                npc_profile=npc_profile,
                situation=situation,
                player_action=player_action,
                npc_name=npc.name
            )}
        ]
        
        # Check cache first
        context_hash = self._create_context_hash(messages, template.temperature, template.max_tokens)
        cached_response = await self._get_cached_response(context_hash)
        if cached_response:
            logger.info("Streaming cached NPC dialogue response")
            # Stream cached response word by word for consistent UX
            words = cached_response.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.05)  # Simulate typing speed
            return
        
        # Stream from OpenAI
        response_text = ""
        async for chunk in self._stream_openai_response(messages, template):
            if chunk:
                response_text += chunk
                yield chunk
        
        # Cache the complete response
        try:
            await self._set_cached_response(context_hash, response_text)
        except Exception as e:
            logger.warning(f"Failed to cache streaming response: {e}")
    
    async def stream_world_description(
        self,
        request: str,
        context: str,
        entities: List[BaseEntity],
        dice_context: str = ""
    ) -> AsyncIterator[str]:
        """Stream world description response in real-time"""
        template = self.templates["world_description"]
        
        entities_text = "\n".join([
            f"- {entity.name} ({entity.type.value}): {entity.description}"
            for entity in entities
        ])
        
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": template.user_template.format(
                context=context,
                entities=entities_text,
                request=request,
                dice_context=dice_context
            )}
        ]
        
        # Check cache first
        context_hash = self._create_context_hash(messages, template.temperature, template.max_tokens)
        cached_response = await self._get_cached_response(context_hash)
        if cached_response:
            logger.info("Streaming cached world description")
            # Stream cached response word by word
            words = cached_response.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.03)  # Slightly faster for descriptions
            return
        
        # Stream from OpenAI
        response_text = ""
        async for chunk in self._stream_openai_response(messages, template):
            if chunk:
                response_text += chunk
                yield chunk
        
        # Cache the complete response
        try:
            await self._set_cached_response(context_hash, response_text)
        except Exception as e:
            logger.warning(f"Failed to cache streaming response: {e}")
    
    async def _stream_openai_response(
        self,
        messages: List[Dict],
        template: PromptTemplate
    ) -> AsyncIterator[str]:
        """Stream response from OpenAI API"""
        try:
            # Optimize context if needed
            token_breakdown = self.analyze_prompt_tokens(messages)
            if token_breakdown['total'] > settings.context_max_tokens * 0.95:
                logger.warning(f"Large context detected ({token_breakdown['total']} tokens), optimizing...")
                messages = self._optimize_context_messages(messages, int(settings.context_max_tokens * 0.95))
            
            # Stream from OpenAI
            stream = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=template.max_tokens,
                temperature=template.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"[Error: Could not stream response - {str(e)}]"


# Global AI service instance
ai_service = AIService()