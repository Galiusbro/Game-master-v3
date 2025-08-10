from __future__ import annotations

"""Boss generation (antagonists)

Creates high-level antagonists ("bosses") and places them into lairs.
Prefers existing POIs of type 'ruin'; if none found for a country, creates a
new 'lair' POI inside one of the country's regions.

Relationships:
- LOCATED_IN Boss -> Lair POI
- CONTROLS Boss -> Lair POI
- ENEMY_OF Boss -> Country
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from core.world_service import world_service
from core.worldgen.utils import create_location_entity, link_to_parent
from domain.entities import NPC, NPCState, NPCPersonality, EntityType


BOSS_ARCHETYPES: List[Dict[str, Any]] = [
    {
        "key": "warlord",
        "roles": ["antagonist", "boss", "warlord"],
        "capabilities": {"authority_capability": {"minions": True}, "combat_capability": {"elite": True}},
        "hooks": ["raid", "conquest"],
    },
    {
        "key": "lich",
        "roles": ["antagonist", "boss", "lich"],
        "capabilities": {"combat_capability": {"magic": True}, "knowledge_capability": {"forbidden": True}},
        "hooks": ["phylactery", "undead"],
    },
    {
        "key": "bandit_king",
        "roles": ["antagonist", "boss", "bandit_king"],
        "capabilities": {"authority_capability": {"minions": True}, "combat_capability": {"skilled": True}},
        "hooks": ["tolls", "ambush"],
    },
    {
        "key": "corrupted_mage",
        "roles": ["antagonist", "boss", "mage"],
        "capabilities": {"combat_capability": {"magic": True}, "knowledge_capability": {"forbidden": True}},
        "hooks": ["ritual", "artifact"],
    },
]


async def _pick_country_ruin_poi(poi_ids: List[str]) -> Optional[Any]:
    """Pick a POI with poi_type='ruin' from the provided list.
    Returns the POI entity if found, else None.
    """
    for pid in poi_ids:
        try:
            poi = await world_service.get_entity(UUID(str(pid)))
            if poi and poi.type == EntityType.LOCATION:
                if (poi.metadata or {}).get("poi_type") == "ruin":
                    return poi
        except Exception:
            continue
    return None


async def _ensure_lair_for_country(
    region_ids: List[Any],
    continent_id: Any,
    rng: random.Random,
    world_actor_id: Any,
) -> Any:
    """Create a simple lair POI inside one of the country's regions."""
    region_id = region_ids[0] if region_ids else continent_id
    du = 0.5 + (rng.random() - 0.5) * 0.1
    dv = 0.5 + (rng.random() - 0.5) * 0.1
    lair = await create_location_entity(
        name="Hidden Lair",
        description="A hidden lair of a dangerous foe",
        location_kind="poi",
        parent_id=region_id,
        center=[du, dv],
        metadata={"poi_type": "lair", "hook_tags": ["danger", "plot"]},
        actor_id=world_actor_id,
    )
    await link_to_parent(lair.id, region_id, relationship_type="LOCATED_IN", properties=None, actor_id=world_actor_id)
    return lair


async def generate_bosses(
    seed: str,
    countries_by_continent: Dict[Any, List[Dict[str, Any]]],
    poi_ids: List[str],
    rng: random.Random,
    world_actor_id: Any,
    max_per_continent: int = 1,
) -> List[str]:
    """Generate bosses per continent, 1 per continent by default."""
    created_boss_ids: List[str] = []

    for continent_id, countries in countries_by_continent.items():
        if not countries:
            continue
        rng.shuffle(countries)
        assigned = 0
        for country in countries:
            if assigned >= max_per_continent:
                break

            # Try pick a ruin POI; if none, create lair inside country's region
            ruin = await _pick_country_ruin_poi(poi_ids)
            if ruin is None:
                ruin = await _ensure_lair_for_country(country.get("region_ids", []), continent_id, rng, world_actor_id)

            archetype = rng.choice(BOSS_ARCHETYPES)
            role_name = archetype["key"].replace("_", " ").title()

            personality = NPCPersonality(core_traits=["ambitious"], speech_patterns=["commanding"])
            state = NPCState(current_mood="hostile")
            state.current_location_id = UUID(str(ruin.id))

            npc = NPC(
                name=f"{role_name} of {str(continent_id)[:6]}",
                description=f"A notorious {role_name.lower()} threatening the realm",
                personality=personality,
                current_state=state,
                metadata={
                    "roles": archetype["roles"],
                    "capabilities": archetype["capabilities"],
                    "threat_level": 9,
                    "lair_poi_id": str(ruin.id),
                    "hooks": archetype["hooks"],
                },
            )

            created = await world_service.create_entity(entity=npc, actor_id=world_actor_id)
            created_boss_ids.append(str(created.id))

            # Relationships
            await world_service.create_relationship(
                from_entity_id=created.id,
                to_entity_id=ruin.id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=world_actor_id,
            )
            await world_service.create_relationship(
                from_entity_id=created.id,
                to_entity_id=ruin.id,
                relationship_type="CONTROLS",
                properties={"kind": "lair"},
                actor_id=world_actor_id,
            )
            await world_service.create_relationship(
                from_entity_id=created.id,
                to_entity_id=country["id"],
                relationship_type="ENEMY_OF",
                properties=None,
                actor_id=world_actor_id,
            )

            assigned += 1

    return created_boss_ids


