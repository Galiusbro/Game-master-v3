"""
Social checks (Persuasion, etc.) for NPC interactions

Provides DC computation with contextual modifiers and disposition updates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from domain.entities import NPC, Player, SkillType, CharacterClass

logger = logging.getLogger(__name__)


# Minimum confidence for treating a line as a deliberate attempt to win an
# NPC over, rather than ordinary conversation. Measured on the demo world:
# plain talk ("I ask Barliman for a room") scores up to 0.44, explicit
# attempts ("I want to become friends with Barliman") score from 0.66. The
# gap sits here. Erring high is deliberate — a missed befriend attempt is
# just a normal conversation, while a false positive spends the player's
# social check and puts the NPC on cooldown.
BEFRIEND_INTENT_THRESHOLD = 0.6


class SocialOutcome:
    """Structured result of a social check."""

    def __init__(
        self,
        dc: int,
        advantage: bool,
        disadvantage: bool,
        reasons: List[str],
    ) -> None:
        self.dc = dc
        self.advantage = advantage
        self.disadvantage = disadvantage
        self.reasons = reasons


def _attitude_base_dc(attitude: str) -> int:
    """Map relationship attitude to a base DC."""
    attitude_lower = (attitude or "").lower()
    if attitude_lower == "friendly":
        return 10
    if attitude_lower == "hostile":
        return 20
    return 15  # neutral or unknown


def compute_social_dc(
    npc: NPC,
    player: Player,
    player_message: Optional[str] = None,
) -> SocialOutcome:
    """Compute DC and modifiers for a friendship attempt with an NPC.

    Returns SocialOutcome(dc, advantage, disadvantage, reasons)
    """

    reasons: List[str] = []

    # Base by attitude
    attitude = npc.current_state.compute_relationship_for_player(player.id)
    dc = _attitude_base_dc(attitude)
    reasons.append(f"attitude={attitude} -> base DC {dc}")

    # Importance level makes it harder (cap +3)
    if getattr(npc, "importance_level", 1) > 1:
        inc = min(3, int(npc.importance_level) - 1)
        dc += inc
        reasons.append(f"importance_level={npc.importance_level} -> +{inc}")

    # Mood tweaks
    mood = (npc.current_state.current_mood or "").lower()
    if mood in {"angry", "annoyed", "hostile"}:
        dc += 2
        reasons.append(f"mood={mood} -> +2")
    elif mood in {"happy", "cheerful", "relaxed", "friendly"}:
        dc -= 2
        reasons.append(f"mood={mood} -> -2")

    # Location alignment (if both are at the same location, fine; otherwise block handled elsewhere)
    # We could add additional context effects later

    # Advantage/disadvantage: simple rule for now
    advantage = False
    disadvantage = False

    # Bardic ease of conversation
    if player.stats.character_class == CharacterClass.BARD:
        advantage = True
        reasons.append("class=bard -> advantage")

    # Clamp DC
    dc = max(5, min(30, dc))

    return SocialOutcome(dc=dc, advantage=advantage, disadvantage=disadvantage, reasons=reasons)


def apply_disposition_change(npc: NPC, player_id: UUID, delta: int) -> int:
    """Apply disposition change and clamp to [-100, 100]. Returns new score."""
    current: int = npc.current_state.disposition_to_player.get(player_id, 0)
    new_score = max(-100, min(100, current + int(delta)))
    npc.current_state.disposition_to_player[player_id] = new_score
    return new_score


def set_social_cooldown(npc: NPC, player_id: UUID, minutes: int) -> None:
    """Set social attempt cooldown for a player."""
    until = datetime.utcnow() + timedelta(minutes=minutes)
    npc.current_state.social_cooldowns[player_id] = until.isoformat()


def is_on_social_cooldown(npc: NPC, player_id: UUID) -> bool:
    """Check if player is on cooldown for this NPC."""
    ts = npc.current_state.social_cooldowns.get(player_id)
    if not ts:
        return False
    try:
        until = datetime.fromisoformat(ts)
        return datetime.utcnow() < until
    except Exception:
        return False

