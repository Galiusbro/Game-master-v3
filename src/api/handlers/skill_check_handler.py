"""
Skill Check Handler

Handles skill check actions with dice rolling
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException

from core.dice_engine import dice_engine
from core.world_service import world_service
from domain.entities import EntityType
from infrastructure.ai_service import ai_service

logger = logging.getLogger(__name__)


async def handle_skill_check(request, parsed) -> dict:
    """Handle skill check actions with dice rolling"""
    try:
        # Get player entity
        player = await world_service.get_entity(request.player_id, EntityType.PLAYER)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Resolve the action using dice engine
        context = {
            'time_of_day': 'day',  # TODO: Get from world state
            'target_attitude': 'neutral'  # Now determined semantically in semantic_parser.py
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
        
        # Prepare dice rolls data for response
        dice_rolls_data = []
        if sequence.primary_roll:
            dice_rolls_data.append({
                "type": sequence.primary_roll.description,
                "dice_notation": sequence.primary_roll.dice_notation,
                "result": sequence.primary_roll.total,
                "dc": sequence.primary_roll.difficulty_class,
                "success": sequence.success,
                "is_critical": sequence.primary_roll.is_critical,
                "is_fumble": sequence.primary_roll.is_fumble,
                "modifiers": sequence.primary_roll.modifiers,
                "raw_results": sequence.primary_roll.raw_results
            })
        
        return {
            "success": sequence.success,
            "action_type": parsed.action.value,
            "content": response_content,
            "confidence": sequence.primary_roll.total / 20.0 if sequence.primary_roll else 0.5,
            "tokens_used": getattr(ai_response, 'tokens_used', 0),
            "response_time": getattr(ai_response, 'response_time', 0.0),
            "resolved_entities": {
                'target_npc': str(parsed.target_npc_id) if parsed.target_npc_id else None,
                'skill_used': sequence.primary_roll.description if sequence.primary_roll else None,
                'dc': sequence.primary_roll.difficulty_class if sequence.primary_roll else None,
                'roll_total': sequence.primary_roll.total if sequence.primary_roll else None
            },
            "dice_rolls": dice_rolls_data,
            "parsing_confidence": parsed.confidence,
            "original_command": request.command,
            "event_id": sequence.sequence_id
        }
        
    except Exception as e:
        logger.error(f"Error handling skill check: {e}")
        return {
            "success": False,
            "action_type": "skill_check",
            "content": f"You attempt: {request.command}, but something goes wrong.",
            "original_command": request.command,
            "warnings": [f"Skill check failed: {str(e)}"]
        }