"""
Natural Language Game Command API

Handles natural language commands like "иду в таверну поговорить с трактирщиком"
and routes them to appropriate AI endpoints.
"""

import logging
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.semantic_parser import semantic_parser
from infrastructure.command_classification_service import GameAction, command_classifier
from core.world_service import world_service
from core.dice_engine import dice_engine
from api.ai_routes import NPCDialogueRequest, WorldDescriptionRequest
from infrastructure.ai_service import ai_service
from domain.entities import EntityType, Player, AbilityScore, SkillType, CharacterClass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/game", tags=["Natural Language Game Commands"])


class GameCommandRequest(BaseModel):
    """Natural language game command request"""
    world_id: UUID
    session_id: UUID
    player_id: UUID
    command: str
    player_name: Optional[str] = None  # For convenience, can resolve to player_id
    dialogue_context: Optional[dict] = None  # Context for dialogue continuation


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
    resolved_entities: dict = {}
    
    # Parsing details
    parsing_confidence: float = 0.0
    original_command: str = ""
    
    # Additional context
    warnings: list = []
    event_id: Optional[UUID] = None


@router.post("/command", response_model=GameCommandResponse)
async def process_natural_command(
    request: GameCommandRequest,
    background_tasks: BackgroundTasks
):
    """
    Process natural language game command
    
    Examples:
    - "иду в таверну"
    - "говорю с барменом: привет, есть ли комнаты?"
    - "ищу зелья в магазине"
    - "покупаю меч у кузнеца"
    """
    
    logger.info(f"Processing command: '{request.command}' for player {request.player_id}")
    
    try:
        # 1. Parse the natural language command
        parsed = await semantic_parser.parse_command(
            world_id=request.world_id,
            session_id=request.session_id,
            player_id=request.player_id,
            raw_command=request.command,
            dialogue_context=request.dialogue_context
        )
        
        logger.info(f"Parsed action: {parsed.action}, confidence: {parsed.confidence}")
        
        # 2. Route to appropriate handler based on detected action
        if parsed.action == GameAction.DIALOGUE:
            return await _handle_dialogue(request, parsed)
            
        elif parsed.action == GameAction.MOVEMENT:
            return await _handle_movement(request, parsed)
            
        elif parsed.action == GameAction.SEARCH:
            return await _handle_search(request, parsed)
            
        elif parsed.action == GameAction.EXPLORE:
            return await _handle_exploration(request, parsed)
            
        elif parsed.action == GameAction.TRADE:
            return await _handle_trade(request, parsed)
            
        elif parsed.action == GameAction.COMBAT:
            return await _handle_combat(request, parsed)
            
        elif parsed.action == GameAction.MAGIC:
            return await _handle_magic(request, parsed)
            
        # Skill check actions
        elif parsed.action in [GameAction.STEALTH, GameAction.PERSUASION, GameAction.DECEPTION, 
                              GameAction.INVESTIGATION, GameAction.SLEIGHT_OF_HAND, 
                              GameAction.ATHLETICS, GameAction.PERCEPTION, GameAction.SKILL_CHECK]:
            return await _handle_skill_check(request, parsed)
            
        else:
            # Unknown action - let AI try to interpret
            return await _handle_unknown(request, parsed)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is (404, 422, etc.)
        raise
    except Exception as e:
        logger.error(f"Error processing command '{request.command}': {e}")
        raise HTTPException(status_code=500, detail=f"Command processing failed: {str(e)}")


async def _handle_dialogue(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle dialogue with NPC"""
    
    if not parsed.target_npc_id:
        # Try to find NPC through general description
        return GameCommandResponse(
            success=False,
            action_type="dialogue",
            content="I don't see anyone to talk to here. Could you be more specific about who you want to speak with?",
            original_command=request.command,
            warnings=["No NPC resolved from command"]
        )
    
    # CHECK IF NPC IS ALIVE BEFORE DIALOGUE!
    logger.info(f"🔍 Checking NPC status for dialogue: {parsed.target_npc_id}")
    try:
        from core.world_service import world_service
        npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
        
        if npc:
            logger.info(f"✅ NPC found: {npc.name}, is_alive: {getattr(npc, 'is_alive', 'MISSING')}")
            if hasattr(npc, 'is_alive') and not npc.is_alive:
                logger.info(f"💀 Player tried to talk to dead NPC: {npc.name}")
                return GameCommandResponse(
                    success=True,
                    action_type="dialogue",
                    content=f"You approach {npc.name}, but there is no response. The lifeless body lies motionless before you - death has claimed them. No amount of words can reach them now.",
                    original_command=request.command,
                    warnings=[f"Cannot dialogue with deceased NPC: {npc.name}"],
                    resolved_entities={"target_npc": npc.name}
                )
            else:
                logger.info(f"✅ NPC {npc.name} is alive, proceeding with dialogue")
        else:
            logger.warning(f"❌ NPC {parsed.target_npc_id} not found in database")
            return GameCommandResponse(
                success=False,
                action_type="dialogue", 
                content="I don't see that person here anymore.",
                original_command=request.command,
                warnings=["NPC not found in database"]
            )
            
    except Exception as e:
        logger.error(f"❌ Error checking NPC status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Continue with normal dialogue as fallback
    
    # Create dialogue request
    dialogue_req = NPCDialogueRequest(
        player_id=request.player_id,
        npc_id=parsed.target_npc_id,
        player_message=parsed.message or "Hello",
        situation_context="",
        session_id=request.session_id
    )
    
    # Call AI dialogue endpoint with BackgroundTasks
    from api.ai_routes import npc_dialogue
    from fastapi import BackgroundTasks
    bg_tasks = BackgroundTasks()
    ai_response = await npc_dialogue(dialogue_req, bg_tasks)
    
    return GameCommandResponse(
        success=True,
        action_type="dialogue",
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        resolved_entities={
            "npc_id": str(parsed.target_npc_id),
            "npc_found": True
        },
        parsing_confidence=parsed.confidence,
        original_command=request.command,
        warnings=ai_response.warnings,
        event_id=ai_response.event_id
    )


async def _handle_movement(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle movement to location"""
    
    # Create world description request for movement
    movement_request = f"I want to go to {parsed.intent_details.get('destination', 'somewhere')}. {request.command}"
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=movement_request,
        session_id=request.session_id
    )
    
    # Call AI world description endpoint
    from api.ai_routes import describe_world
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return GameCommandResponse(
        success=True,
        action_type="movement",
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        resolved_entities={
            "target_location": parsed.intent_details.get('destination', 'unknown'),
            "location_id": str(parsed.target_location_id) if parsed.target_location_id else None
        },
        parsing_confidence=parsed.confidence,
        original_command=request.command
    )


async def _handle_search(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle search/investigation actions"""
    
    search_request = f"I search for {parsed.intent_details.get('target', 'something')}. {request.command}"
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=search_request,
        session_id=request.session_id
    )
    
    from api.ai_routes import describe_world
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return GameCommandResponse(
        success=True,
        action_type="search",
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        resolved_entities={
            "search_target": parsed.intent_details.get('target', 'unknown')
        },
        parsing_confidence=parsed.confidence,
        original_command=request.command
    )


async def _handle_exploration(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle general exploration"""
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=request.command,
        session_id=request.session_id
    )
    
    from api.ai_routes import describe_world
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return GameCommandResponse(
        success=True,
        action_type="exploration",
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        parsing_confidence=parsed.confidence,
        original_command=request.command
    )


async def _handle_trade(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle trade/commerce actions"""
    
    if parsed.target_npc_id:
        # Trade with specific NPC
        trade_message = f"I want to {request.command}"
        
        dialogue_req = NPCDialogueRequest(
            player_id=request.player_id,
            npc_id=parsed.target_npc_id,
            player_message=trade_message,
            situation_context="trade",
            session_id=request.session_id
        )
        
        from api.ai_routes import npc_dialogue
        bg_tasks = BackgroundTasks()
        ai_response = await npc_dialogue(dialogue_req, bg_tasks)
        
        return GameCommandResponse(
            success=True,
            action_type="trade",
            content=ai_response.content,
            confidence=ai_response.confidence,
            tokens_used=ai_response.tokens_used,
            response_time=ai_response.response_time,
            resolved_entities={"npc_id": str(parsed.target_npc_id)},
            parsing_confidence=parsed.confidence,
            original_command=request.command,
            event_id=ai_response.event_id
        )
    else:
        # General trade description
        return await _handle_exploration(request, parsed)


async def _handle_combat(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle combat actions with state mutations"""
    
    # For now, treat as world description with combat context
    combat_request = f"I attempt to {request.command}"
    
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=combat_request,
        session_id=request.session_id
    )
    
    from api.ai_routes import describe_world
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    # Check if combat resulted in NPC death and update state
    warnings = ["Combat system not fully implemented - using narrative description"]
    
    if parsed.target_npc_id:
        # Check if player command or AI response mentions death/killing using modern classification
        command_death_event, command_death_conf = command_classifier.detect_special_event(request.command)
        ai_death_event, ai_death_conf = command_classifier.detect_special_event(ai_response.content)
        
        command_mentions_death = command_death_event == "death_event" and command_death_conf > 0.5
        ai_mentions_death = ai_death_event == "death_event" and ai_death_conf > 0.5
        
        if command_mentions_death or ai_mentions_death:
            try:
                logger.info(f"🗡️ Death event detected! Command: {command_death_conf:.2f}, AI: {ai_death_conf:.2f}, NPC: {parsed.target_npc_id}")
                
                # Get the NPC entity
                npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
                logger.info(f"📋 Retrieved NPC: {npc.name if npc else 'None'}, is_alive: {npc.is_alive if npc else 'N/A'}")
                
                if npc and npc.is_alive:
                    logger.info(f"💀 Killing NPC {npc.name}...")
                    
                    # Update NPC state to dead
                    npc.is_alive = False
                    npc.current_state.current_mood = "dead"
                    npc.current_state.current_activity = "deceased"
                    
                    logger.info(f"💾 Saving updated NPC state for {npc.name}...")
                    
                    # Save the updated NPC state
                    updated_npc = await world_service.update_entity(
                        entity=npc,
                        actor_id=request.player_id,
                        session_id=request.session_id
                    )
                    
                    logger.info(f"✅ SUCCESS! NPC {npc.name} updated. New state: alive={updated_npc.is_alive}")
                    
                    # CREATE EVENT ENTITY FOR AI MEMORY!
                    try:
                        from domain.entities import Event, ActionType, ActorType
                        from uuid import uuid4
                        
                        death_event = Event(
                            id=uuid4(),
                            name=f"Death of {npc.name}",
                            description=f"{npc.name} was slain in combat. The tragic event occurred in the tavern, forever changing the atmosphere of the place.",
                            action_type=ActionType.COMBAT,
                            actor_id=request.player_id,
                            actor_type=ActorType.PLAYER,
                            participants=[request.player_id, npc.id],
                            location_id=npc.current_state.current_location_id,
                            before_state={"npc_alive": True, "combat_initiated": True},
                            after_state={"npc_alive": False, "death_confirmed": True},
                            session_id=request.session_id,
                            confidence_score=1.0
                        )
                        
                        # Store event in Graph DB for AI memory
                        await world_service.create_entity(
                            death_event,
                            actor_id=request.player_id,
                            session_id=request.session_id
                        )
                        
                        logger.info(f"📚 Created death event entity: {death_event.id}")
                        warnings.append(f"Death event recorded for AI memory")
                        
                    except Exception as e:
                        logger.error(f"Failed to create death event: {e}")
                        warnings.append(f"Warning: Death event not recorded - {e}")
                    
                    warnings.append(f"NPC {npc.name} state updated to deceased")
                    
                    # Override AI response if it refused to cooperate
                    ai_content_lower = ai_response.content.lower()
                    if "can't assist" in ai_content_lower or "sorry" in ai_content_lower:
                        ai_response.content = f"In a tragic turn of events, {npc.name} has fallen. The tavern falls silent as the gravity of what has transpired settles over the room."
                        warnings.append("AI response overridden due to content policy - death event processed")
                else:
                    logger.warning(f"⚠️ Cannot kill NPC: npc={npc}, is_alive={npc.is_alive if npc else 'N/A'}")
                    
            except Exception as e:
                logger.error(f"💥 CRITICAL ERROR updating NPC state: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"💥 Stack trace: {traceback.format_exc()}")
                warnings.append(f"Failed to update NPC state: {e}")
    
    return GameCommandResponse(
        success=True,
        action_type="combat",
        content=ai_response.content,
        confidence=ai_response.confidence,
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        parsing_confidence=parsed.confidence,
        original_command=request.command,
        warnings=warnings,
        event_id=ai_response.event_id
    )


async def _handle_unknown(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle unknown/unclear commands"""
    
    # Let AI try to interpret the command
    world_req = WorldDescriptionRequest(
        player_id=request.player_id,
        request=f"I try to: {request.command}",
        session_id=request.session_id
    )
    
    from api.ai_routes import describe_world
    bg_tasks = BackgroundTasks()
    ai_response = await describe_world(world_req, bg_tasks)
    
    return GameCommandResponse(
        success=True,
        action_type="unknown",
        content=ai_response.content,
        confidence=ai_response.confidence * 0.5,  # Lower confidence for unknown actions
        tokens_used=ai_response.tokens_used,
        response_time=ai_response.response_time,
        parsing_confidence=parsed.confidence,
        original_command=request.command,
        warnings=["Command action type unclear - using general interpretation"]
    )


@router.get("/help")
async def get_command_help():
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


async def _handle_magic(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle magic spells and rituals with automatic event creation"""
    logger.info(f"🔮 Processing magic action: {parsed.raw_command}")
    
    # Detect resurrection magic using modern classification
    resurrection_event, resurrection_conf = command_classifier.detect_special_event(parsed.raw_command)
    is_resurrection = resurrection_event == "resurrection_event" and resurrection_conf > 0.5
    
    if is_resurrection and parsed.target_npc_id:
        logger.info(f"✨ Resurrection spell detected! Confidence: {resurrection_conf:.2f}, NPC: {parsed.target_npc_id}")
        
        try:
            from core.world_service import world_service
            npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
            
            if npc and hasattr(npc, 'is_alive') and not npc.is_alive:
                logger.info(f"💀➡️😇 Resurrecting {npc.name}!")
                
                # RESURRECT THE NPC!
                npc.is_alive = True
                npc.current_state.current_mood = "confused but grateful"
                npc.current_state.current_activity = "slowly awakening"
                npc.description = f"A stout, cheerful man with graying hair and a welcoming smile. He looks slightly bewildered but very much alive, with a faint glow still lingering around him from recent magical revival."
                
                # Save the resurrection
                updated_npc = await world_service.update_entity(
                    entity=npc, 
                    actor_id=request.player_id, 
                    session_id=request.session_id
                )
                
                # CREATE RESURRECTION EVENT ENTITY FOR AI MEMORY!
                try:
                    from domain.entities import Event, ActionType, ActorType
                    from uuid import uuid4
                    
                    resurrection_event = Event(
                        id=uuid4(),
                        name=f"Magical Resurrection of {npc.name}",
                        description=f"Through ancient magic and a scroll of resurrection, {npc.name} was brought back from death to life in the tavern. His soul was restored to his body by powerful magic.",
                        action_type=ActionType.MAGIC,
                        actor_id=request.player_id,
                        actor_type=ActorType.PLAYER,
                        participants=[request.player_id, npc.id],
                        location_id=npc.current_state.current_location_id,
                        before_state={"npc_alive": False, "spell_cast": "resurrection"},
                        after_state={"npc_alive": True, "resurrection_successful": True},
                        session_id=request.session_id,
                        confidence_score=1.0
                    )
                    
                    # Store event in Graph DB for AI memory
                    await world_service.create_entity(
                        resurrection_event,
                        actor_id=request.player_id,
                        session_id=request.session_id
                    )
                    
                    logger.info(f"📚 Created resurrection event entity: {resurrection_event.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create resurrection event: {e}")
                
                logger.info(f"✅ {npc.name} successfully resurrected!")
                
                return GameCommandResponse(
                    success=True,
                    action_type="magic",
                    content=f"The scroll glows with brilliant light as ancient magic courses through {npc.name}'s lifeless form. Suddenly, his eyes flutter open and he draws a sharp, gasping breath! The color returns to his cheeks as life floods back into his body. {npc.name} sits up slowly, looking around in confusion but very much alive. 'What... what happened?' he whispers, his voice hoarse but real.",
                    original_command=request.command,
                    resolved_entities={"resurrected_npc": npc.name},
                    warnings=[f"Successfully resurrected {npc.name}", "Resurrection event recorded for AI memory"]
                )
                
            elif npc and getattr(npc, 'is_alive', True):
                return GameCommandResponse(
                    success=True,
                    action_type="magic",
                    content=f"You attempt to cast resurrection on {npc.name}, but the magic fizzles harmlessly - {npc.name} is already very much alive and well!",
                    original_command=request.command,
                    warnings=["Target is already alive"]
                )
            else:
                return GameCommandResponse(
                    success=False,
                    action_type="magic",
                    content="The scroll glows, but there is no suitable target for resurrection magic here.",
                    original_command=request.command,
                    warnings=["No dead NPC found to resurrect"]
                )
                
        except Exception as e:
            logger.error(f"Error in resurrection magic: {e}")
            return GameCommandResponse(
                success=False,
                action_type="magic",
                content="The magical energies swirl chaotically and then dissipate. Something went wrong with the spell.",
                original_command=request.command,
                warnings=[f"Magic failed: {str(e)}"]
            )
    
    # For other magic, use general AI response
    return await _handle_unknown(request, parsed)


async def _handle_skill_check(request: GameCommandRequest, parsed) -> GameCommandResponse:
    """Handle skill check actions with dice rolling"""
    try:
        # Get player entity
        player = await world_service.get_entity(request.player_id, EntityType.PLAYER)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Resolve the action using dice engine
        context = {
            'time_of_day': 'day',  # TODO: Get from world state
            'target_attitude': 'neutral'  # TODO: Determine from target NPC
        }
        
        # Get target AC if it's a combat action
        if parsed.target_npc_id:
            target_npc = await world_service.get_entity(parsed.target_npc_id, EntityType.NPC)
            if target_npc:
                context['target_ac'] = 15  # TODO: Calculate from NPC stats
        
        # Resolve the complex action with dice rolls
        sequence = dice_engine.resolve_complex_action(
            actor=player,
            action_description=request.command,
            target_id=parsed.target_npc_id or parsed.target_item_id,
            context=context
        )
        
        # Update player in the world service
        await world_service.update_entity(
            entity=player,
            actor_id=request.player_id,
            session_id=request.session_id
        )
        
        # Generate AI response based on the dice results
        if sequence.primary_roll:
            # Build context for AI about the dice roll
            dice_context = f"""
DICE ROLL RESULT:
- Action: {sequence.action_description}
- Roll: {sequence.primary_roll.dice_notation} = {sequence.primary_roll.total}
- DC: {sequence.primary_roll.difficulty_class}
- Result: {'SUCCESS' if sequence.success else 'FAILURE'}
"""
            
            if sequence.primary_roll.is_critical:
                dice_context += "- CRITICAL SUCCESS! (Natural 20)\n"
            elif sequence.primary_roll.is_fumble:
                dice_context += "- CRITICAL FAILURE! (Natural 1)\n"
            
            # Use AI service to generate narrative response
            try:
                if ai_service.is_initialized:
                    ai_response = await ai_service.generate_dice_outcome_narration(
                        dice_results=dice_context,
                        action_description=request.command,
                        player=player,
                        context_entities=parsed.context_entities or []
                    )
                    response_content = ai_response.content
                else:
                    # Fallback when AI service is not available
                    result_word = "SUCCESS" if sequence.success else "FAILURE"
                    critical_text = ""
                    if sequence.primary_roll.is_critical:
                        critical_text = " with spectacular results!"
                    elif sequence.primary_roll.is_fumble:
                        critical_text = " with disastrous consequences!"
                    
                    response_content = f"🎲 {sequence.primary_roll.description}: {sequence.primary_roll.total} vs DC {sequence.primary_roll.difficulty_class} = {result_word}{critical_text}"
            except Exception as e:
                logger.warning(f"AI narration failed, using fallback: {e}")
                result_word = "SUCCESS" if sequence.success else "FAILURE"
                response_content = f"🎲 {sequence.primary_roll.description}: {sequence.primary_roll.total} vs DC {sequence.primary_roll.difficulty_class} = {result_word}"
            
        else:
            response_content = f"You attempt: {request.command}. The outcome is unclear."
        
        return GameCommandResponse(
            success=sequence.success,
            action_type=parsed.action.value,
            content=response_content,
            confidence=sequence.primary_roll.total / 20.0 if sequence.primary_roll else 0.5,
            tokens_used=getattr(ai_response, 'tokens_used', 0),
            response_time=getattr(ai_response, 'response_time', 0.0),
            resolved_entities={
                'target_npc': str(parsed.target_npc_id) if parsed.target_npc_id else None,
                'skill_used': sequence.primary_roll.description if sequence.primary_roll else None,
                'dc': sequence.primary_roll.difficulty_class if sequence.primary_roll else None,
                'roll_total': sequence.primary_roll.total if sequence.primary_roll else None
            },
            parsing_confidence=parsed.confidence,
            original_command=request.command,
            event_id=sequence.sequence_id
        )
        
    except Exception as e:
        logger.error(f"Error handling skill check: {e}")
        return GameCommandResponse(
            success=False,
            action_type="skill_check",
            content=f"You attempt: {request.command}, but something goes wrong.",
            original_command=request.command,
            warnings=[f"Skill check failed: {str(e)}"]
        )


# Character management endpoints
class CharacterStatsRequest(BaseModel):
    """Request to view or update character stats"""
    player_id: UUID


class CharacterCreationRequest(BaseModel):
    """Request to create a new character"""
    name: str
    character_class: CharacterClass
    ability_scores: dict  # {"strength": 15, "dexterity": 14, etc.}
    background: str = "Custom"
    

@router.post("/character/create", response_model=GameCommandResponse)
async def create_character(request: CharacterCreationRequest):
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
async def get_character_stats(player_id: UUID):
    """Get character statistics"""
    try:
        player = await world_service.get_entity(player_id, EntityType.PLAYER)
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