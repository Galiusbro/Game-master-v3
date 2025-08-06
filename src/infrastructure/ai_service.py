"""
AI Service for Game Master V3
Handles LLM interactions with context assembly and anti-hallucination guards
"""
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import openai
import tiktoken
from pydantic import BaseModel, Field

from config.settings import settings
from domain.entities import BaseEntity, EntityType, NPC, NPCPersonality, Player
from monitoring.metrics import track_ai_operation

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
                max_tokens=800,
                temperature=0.8,
                anti_hallucination_instructions="Only reference entities, locations, and facts explicitly mentioned in the provided context. Do not invent new information."
            ),
            
            "world_description": PromptTemplate(
                system_prompt="""You are an AI Game Master describing a fantasy world to players.
Provide rich, immersive descriptions based strictly on the provided context.

CRITICAL RULES:
- Only describe what is explicitly provided in the context
- Do not add new details not mentioned in the source material
- Maintain consistency with established world facts
- If asked about something not in context, acknowledge the limitation
- Create atmospheric descriptions while staying factual
- If dice roll results are provided, incorporate them into the description""",
                user_template="""WORLD CONTEXT:
{context}

ENTITIES PRESENT:
{entities}

PLAYER REQUEST: {request}

{dice_context}

Provide an immersive description based solely on the provided context.""",
                max_tokens=600,
                temperature=0.7,
                anti_hallucination_instructions="Describe only what is explicitly mentioned in the context. Do not add fictional details."
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
                max_tokens=400,
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
                max_tokens=500,
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
            
            return AIResponse(
                content=content,
                confidence=0.9 if not hallucination_detected else 0.6,
                tokens_used=tokens_used,
                response_time=response_time,
                hallucination_detected=hallucination_detected,
                cited_entities=cited_entities,
                warnings=warnings
            )
            
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


# Global AI service instance
ai_service = AIService()