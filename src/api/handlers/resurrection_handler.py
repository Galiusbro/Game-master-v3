"""
Resurrection Handler

Handles resurrection scroll usage
"""

import logging
from typing import Optional

from core.world_service import world_service
from domain.entities import Player
from infrastructure.ai_service import ai_service

logger = logging.getLogger(__name__)


async def handle_resurrection(request, player: Player) -> dict:
    """Handle resurrection scroll usage"""
    try:
        logger.info(f"📜 Processing resurrection for {player.name}")
        
        # Restore player to life
        old_hp = player.effective_hit_points
        player.stats.current_hit_points = player.stats.max_hit_points  # Full health restoration
        new_hp = player.effective_hit_points
        
        logger.info(f"✨ {player.name} resurrected: {old_hp} → {new_hp} HP")
        
        # Update player in world service
        await world_service.update_entity(
            entity=player,
            actor_id=request.player_id,
            session_id=request.session_id
        )
        
        # Generate AI response for resurrection
        try:
            if ai_service.is_initialized:
                ai_response = await ai_service.generate_resurrection_response(
                    player_name=player.name,
                    player_class=player.stats.character_class.value if player.stats.character_class else "adventurer",
                    command=request.command
                )
                content = ai_response.content
                confidence = ai_response.confidence
                tokens_used = ai_response.tokens_used
                response_time = ai_response.response_time
                event_id = ai_response.event_id
            else:
                # Fallback resurrection message
                content = f"✨ The scroll glows with divine light as {player.name} is restored to life! Your HP is fully restored to {new_hp}. The adventure continues!"
                confidence = 1.0
                tokens_used = 0
                response_time = 0.0
                event_id = None
                
        except Exception as e:
            logger.warning(f"AI resurrection response failed: {e}")
            content = f"✨ {player.name} has been resurrected! HP restored to {new_hp}. You feel the warmth of life returning to your body."
            confidence = 1.0
            tokens_used = 0
            response_time = 0.0
            event_id = None
        
        return {
            "success": True,
            "action_type": "resurrection",
            "content": content,
            "confidence": confidence,
            "tokens_used": tokens_used,
            "response_time": response_time,
            "resolved_entities": {
                "player_dead": False,
                "player_hp": new_hp,
                "player_max_hp": player.effective_max_hit_points,
                "resurrection_successful": True,
                "hp_restored": new_hp - old_hp
            },
            "parsing_confidence": 1.0,
            "original_command": request.command,
            "warnings": [],
            "event_id": event_id
        }
        
    except Exception as e:
        logger.error(f"Error handling resurrection: {e}")
        return {
            "success": False,
            "action_type": "resurrection",
            "content": f"The scroll flickers but fails to work. Something went wrong with the resurrection.",
            "original_command": request.command,
            "warnings": [f"Resurrection failed: {str(e)}"]
        }