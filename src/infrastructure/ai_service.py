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
- Create atmospheric descriptions while staying factual""",
                user_template="""WORLD CONTEXT:
{context}

ENTITIES PRESENT:
{entities}

PLAYER REQUEST: {request}

Provide an immersive description based solely on the provided context.""",
                max_tokens=600,
                temperature=0.7,
                anti_hallucination_instructions="Describe only what is explicitly mentioned in the context. Do not add fictional details."
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
            self.tokenizer = tiktoken.encoding_for_model(settings.llm_model)
            
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
    
    async def generate_world_description(
        self,
        context_entities: List[BaseEntity],
        player_request: str,
        max_retries: int = 2
    ) -> AIResponse:
        """Generate world/location description"""
        start_time = time.time()
        
        # Build context
        context_parts = []
        entities_parts = []
        
        for entity in context_entities:
            context_parts.append(f"{entity.type.value.title()}: {entity.name}")
            context_parts.append(f"Description: {entity.description}")
            context_parts.append("")
            
            entities_parts.append(f"- {entity.name} ({entity.type.value})")
        
        context = "\n".join(context_parts)
        entities = "\n".join(entities_parts)
        
        template = self.templates["world_description"]
        
        messages = [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": template.user_template.format(
                context=context,
                entities=entities,
                request=player_request
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


# Global AI service instance
ai_service = AIService()