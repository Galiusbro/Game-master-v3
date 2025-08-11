from __future__ import annotations

"""Encounter tables (MVP)

Attach basic encounter tables to Regions and Roads in metadata.encounter_table.
Runtime spawning will use these tables; here we only generate data.
"""

import random
from typing import Any, Dict, List
from uuid import UUID

from core.world_service import world_service
from domain.entities import EntityType


def _region_encounters_for_biome(biome: str) -> List[Dict[str, Any]]:
    table: Dict[str, List[Dict[str, Any]]] = {
        "plains": [
            {"id": "bandits", "name": "Bandit group", "tags": ["humanoid"], "weight": 3, "group_size": [3, 6]},
            {"id": "wolves", "name": "Wolf pack", "tags": ["beast"], "weight": 4, "group_size": [2, 5]},
            {"id": "goblins", "name": "Goblin raiders", "tags": ["humanoid"], "weight": 2, "group_size": [3, 7]},
        ],
        "forest": [
            {"id": "wolves", "name": "Wolf pack", "tags": ["beast"], "weight": 4, "group_size": [2, 5]},
            {"id": "bandits", "name": "Highwaymen", "tags": ["humanoid"], "weight": 3, "group_size": [2, 4]},
            {"id": "spiders", "name": "Giant spiders", "tags": ["beast"], "weight": 2, "group_size": [1, 3]},
        ],
        "mountains": [
            {"id": "harpies", "name": "Harpies", "tags": ["monstrous"], "weight": 2, "group_size": [1, 3]},
            {"id": "bandits", "name": "Brigands", "tags": ["humanoid"], "weight": 2, "group_size": [3, 5]},
            {"id": "troll", "name": "Cave troll", "tags": ["monstrous"], "weight": 1, "group_size": [1, 1]},
        ],
        "coastal": [
            {"id": "pirates", "name": "Pirate crew", "tags": ["humanoid"], "weight": 2, "group_size": [3, 6]},
            {"id": "smugglers", "name": "Smugglers", "tags": ["humanoid"], "weight": 3, "group_size": [2, 4]},
            {"id": "sirens", "name": "Sirens", "tags": ["monstrous"], "weight": 1, "group_size": [1, 2]},
        ],
        "desert": [
            {"id": "scorpions", "name": "Giant scorpions", "tags": ["beast"], "weight": 2, "group_size": [1, 3]},
            {"id": "raiders", "name": "Desert raiders", "tags": ["humanoid"], "weight": 3, "group_size": [3, 6]},
        ],
    }
    return table.get(biome, table["plains"])  # default to plains


async def attach_region_encounters(
    regions_by_continent: Dict[Any, List[Dict[str, Any]]],
    rng: random.Random,
) -> None:
    for _, regions in regions_by_continent.items():
        for reg in regions:
            try:
                entity = await world_service.get_entity(UUID(str(reg["id"])))
                if not entity or entity.type != EntityType.LOCATION:
                    continue
                biome = reg.get("biome", "plains")
                entries = _region_encounters_for_biome(biome)
                entity.metadata.setdefault("encounter_table", {})
                base = 0.2
                if biome in ("swamp", "mountains", "desert"):
                    base = 0.35
                elif biome in ("forest",):
                    base = 0.3
                entity.metadata["encounter_table"]["roll_chance"] = round(base + rng.random() * 0.1, 2)
                entity.metadata["encounter_table"]["entries"] = entries
                # Mark unsafe for dangerous biomes
                if biome in ("swamp", "mountains", "desert"):
                    entity.is_safe = False  # type: ignore[attr-defined]
                await world_service.update_entity(entity, actor_id=entity.id)
            except Exception:
                continue


