"""
Social Engine

First iteration: thin wrapper around existing social_checks and dice_engine.
This provides a stable entrypoint to plug configurable modifiers later
without changing handlers again.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

import logging

from domain.entities import Player, NPC, SkillType
from core.dice_engine import dice_engine
from core.social_checks import (
    compute_social_dc,
    apply_disposition_change,
    set_social_cooldown,
)

logger = logging.getLogger(__name__)


class SocialEngine:
    """Facade for running social checks.

    This initial version delegates to compute_social_dc and dice_engine.
    Future versions will load declarative modifiers and apply them here.
    """

    async def run_social_check(
        self,
        intent: str,
        player: Player,
        npc: NPC,
        message: Optional[str],
    ) -> Dict[str, Any]:
        """Run a social check and mutate NPC disposition and cooldown.

        Returns a dict compatible with dialogue_handler's dice_rolls entry.
        Persistence is handled by the caller.
        """

        # Compute DC and advantage/disadvantage based on current simple rules
        outcome = compute_social_dc(npc=npc, player=player, player_message=message)

        # Map social intent to primary skill (befriend -> persuasion)
        skill = SkillType.PERSUASION if intent == "befriend" else SkillType.PERSUASION

        roll = dice_engine.make_skill_check(
            character=player,
            skill=skill,
            dc=outcome.dc,
            advantage=outcome.advantage,
            disadvantage=outcome.disadvantage,
            description=f"{intent.capitalize()} attempt",
        )

        # Apply disposition change and cooldown policy (mirrors prior logic)
        if roll.is_success:
            delta = 20 if roll.is_critical else 10
            cooldown_minutes = 1
        else:
            delta = -20 if roll.is_fumble else -10
            cooldown_minutes = 10

        new_score = apply_disposition_change(npc, player.id, delta)
        set_social_cooldown(npc, player.id, minutes=cooldown_minutes)

        logger.info(
            f"SocialEngine: {intent} check -> DC {outcome.dc}, roll {roll.total}"
            f" ({'success' if roll.is_success else 'fail'}), delta {delta} -> {new_score}"
        )

        # Relationship label will be computed by NPCState if not explicitly set
        result: Dict[str, Any] = {
            "skill": skill.value,
            "dc": outcome.dc,
            "advantage": outcome.advantage,
            "disadvantage": outcome.disadvantage,
            "reasons": outcome.reasons,
            "roll": {
                "total": roll.total,
                "raw_results": roll.raw_results,
                "modifiers": roll.modifiers,
                "critical": roll.is_critical,
                "fumble": roll.is_fumble,
                "success": roll.is_success,
            },
            "disposition_delta": delta,
            "new_disposition": new_score,
            # relationship label will be set by caller after compute
            "cooldown_minutes": cooldown_minutes,
        }

        return result


social_engine = SocialEngine()

