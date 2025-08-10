from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from core.world_service import world_service
from domain.entities import EntityType, BaseEntity, NPC


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    dx = ax - bx
    dy = ay - by
    return (dx * dx + dy * dy) ** 0.5


def _race_distribution_for_biome(biome: str) -> Dict[str, int]:
    biome = (biome or "plains").lower()
    # Percent-like weights, sum ~100
    if biome in ("mountains", "highlands"):
        return {"dwarf": 50, "human": 30, "gnome": 10, "elf": 5, "halfling": 5}
    if biome in ("forest", "taiga"):
        return {"elf": 40, "human": 35, "halfling": 10, "gnome": 10, "dwarf": 5}
    if biome in ("coastal", "swamp"):
        return {"human": 50, "halfling": 20, "elf": 15, "dwarf": 10, "gnome": 5}
    if biome in ("desert",):
        return {"human": 40, "tiefling": 20, "orc": 20, "elf": 10, "dwarf": 10}
    # default plains
    return {"human": 60, "halfling": 15, "elf": 10, "dwarf": 10, "gnome": 5}


def _weighted_choice(rng: random.Random, dist: Dict[str, int]) -> str:
    total = sum(dist.values())
    r = rng.randint(1, total)
    acc = 0
    for k, w in dist.items():
        acc += w
        if r <= acc:
            return k
    return next(iter(dist))


async def _nearest_region_for_city(city: BaseEntity, regions: List[BaseEntity]) -> Optional[BaseEntity]:
    c_center = tuple(city.metadata.get("center", [0.5, 0.5]))  # type: ignore
    best = None
    best_d = 10**9
    for reg in regions:
        r_center = tuple(reg.metadata.get("center", [0.5, 0.5]))  # type: ignore
        d = _distance(c_center, r_center)  # normalized distance
        if d < best_d:
            best = reg
            best_d = d
    return best


async def enrich_city_demographics(seed: str, max_npcs_per_city: int = 100) -> Dict[str, Any]:
    rng = random.Random(f"demo:{seed}")
    updated_cities = 0
    updated_npcs = 0

    # Fetch all locations and split by kind
    all_locations = await world_service.get_entities_by_type(EntityType.LOCATION, limit=10000)
    cities = [e for e in all_locations if (e.metadata or {}).get("location_kind") == "city"]
    regions = [e for e in all_locations if (e.metadata or {}).get("location_kind") == "region"]

    # Build region groups by continent
    regions_by_continent: Dict[str, List[BaseEntity]] = {}
    for reg in regions:
        parent = (reg.metadata or {}).get("parent_id")
        if parent:
            regions_by_continent.setdefault(str(parent), []).append(reg)

    # Fetch all NPCs once (limit safety)
    all_npcs = await world_service.get_entities_by_type(EntityType.NPC, limit=10000)
    # Index current_location -> list of NPCs
    npcs_by_loc: Dict[str, List[NPC]] = {}
    for n in all_npcs:
        if not isinstance(n, NPC):
            continue
        loc_id = getattr(getattr(n, "current_state", None), "current_location_id", None)
        if loc_id:
            npcs_by_loc.setdefault(str(loc_id), []).append(n)

    for city in cities:
        # Find continent
        continent_id = (city.metadata or {}).get("parent_id")
        if not continent_id:
            continue
        # Nearest region for biome
        rlist = regions_by_continent.get(str(continent_id), [])
        if not rlist:
            continue
        nearest_region = await _nearest_region_for_city(city, rlist)
        biome = (nearest_region.metadata or {}).get("primary_biome", "plains") if nearest_region else "plains"
        dist = _race_distribution_for_biome(str(biome))

        # Update city demographics
        city.metadata.setdefault("demographics", {})
        city.metadata["demographics"]["race_distribution"] = dist
        await world_service.update_entity(city, actor_id=city.id)
        updated_cities += 1

        # Assign races to NPCs under this city: check two-hop parent chain
        # Strategy: gather district/building IDs under the city by scanning locations with parent_id == city.id or district.parent == city.id
        # Then map npcs whose current_location_id == any of those
        child_locations = [e for e in all_locations if (e.metadata or {}).get("parent_id") == str(city.id)]
        child_ids = {str(e.id) for e in child_locations}
        # second level
        second_level = [e for e in all_locations if (e.metadata or {}).get("parent_id") in child_ids]
        second_ids = {str(e.id) for e in second_level}
        target_loc_ids = child_ids | second_ids

        assigned = 0
        for loc_id in target_loc_ids:
            for npc in npcs_by_loc.get(loc_id, []) or []:
                if assigned >= max_npcs_per_city:
                    break
                # Set race if missing
                if isinstance(npc.metadata, dict) and not npc.metadata.get("race"):
                    race = _weighted_choice(rng, dist)
                    npc.metadata["race"] = race
                    await world_service.update_entity(npc, actor_id=npc.id)
                    updated_npcs += 1
                    assigned += 1
            if assigned >= max_npcs_per_city:
                break

    return {"updated_cities": updated_cities, "updated_npcs": updated_npcs}


