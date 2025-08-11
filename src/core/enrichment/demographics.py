from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from uuid import UUID

from core.world_service import world_service
from domain.entities import EntityType, BaseEntity, NPC


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    dx = ax - bx
    dy = ay - by
    return (dx * dx + dy * dy) ** 0.5


def _race_prior_for_biome(biome: str) -> Dict[str, float]:
    biome = (biome or "plains").lower()
    # Base priors (weights, not strict percentages)
    if biome in ("mountains", "highlands"):
        return {"human": 30, "dwarf": 45, "elf": 5, "halfling": 5, "gnome": 10, "orc": 3, "tiefling": 2}
    if biome in ("forest", "taiga"):
        return {"human": 35, "dwarf": 5, "elf": 35, "halfling": 10, "gnome": 10, "orc": 3, "tiefling": 2}
    if biome in ("coastal", "swamp"):
        return {"human": 50, "dwarf": 8, "elf": 15, "halfling": 17, "gnome": 5, "orc": 3, "tiefling": 2}
    if biome in ("desert",):
        return {"human": 38, "dwarf": 8, "elf": 10, "halfling": 6, "gnome": 4, "orc": 18, "tiefling": 16}
    # default plains
    return {"human": 55, "dwarf": 10, "elf": 12, "halfling": 15, "gnome": 6, "orc": 1, "tiefling": 1}


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    total = float(sum(max(0.0, w) for w in weights.values())) or 1.0
    return {k: max(0.0, w) / total for k, w in weights.items()}


def _apply_modifiers(base: Dict[str, float], place: BaseEntity) -> Dict[str, float]:
    """Adjust priors by city/town traits: capital diversity, trade specialization, walls, etc."""
    adjusted = dict(base)
    meta = place.metadata or {}

    # Capitals: more diversity → blend towards uniform by 20%
    if meta.get("is_capital"):
        keys = list(adjusted.keys())
        uniform = {k: 1.0 / len(keys) for k in keys}
        adjusted = {k: 0.8 * adjusted[k] + 0.2 * uniform[k] for k in keys}

    # Trade specialization (towns)
    trade = (meta.get("trade_specialization") or "").lower()
    if trade:
        if any(x in trade for x in ["metal", "smith", "ore"]):
            adjusted["dwarf"] = adjusted.get("dwarf", 0.0) * 1.25
            adjusted["gnome"] = adjusted.get("gnome", 0.0) * 1.1
        if any(x in trade for x in ["timber", "forest"]):
            adjusted["elf"] = adjusted.get("elf", 0.0) * 1.2
        if any(x in trade for x in ["fish", "coast", "harbor"]):
            adjusted["human"] = adjusted.get("human", 0.0) * 1.1
            adjusted["halfling"] = adjusted.get("halfling", 0.0) * 1.1

    # Fortified settlements slightly favor humans/dwarves (garrisons)
    if meta.get("has_walls"):
        adjusted["human"] = adjusted.get("human", 0.0) * 1.05
        adjusted["dwarf"] = adjusted.get("dwarf", 0.0) * 1.05

    return _normalize(adjusted)


def _dirichlet_sample(probs: Dict[str, float], concentration: float, seed: int) -> Dict[str, int]:
    keys = list(probs.keys())
    p = np.array([max(1e-6, probs[k]) for k in keys], dtype=float)
    p = p / p.sum()
    alpha = p * concentration
    rng = np.random.default_rng(seed)
    sample = rng.dirichlet(alpha)
    # Convert to integer percentages that sum to 100
    perc = np.round(sample * 100).astype(int)
    # Fix rounding drift
    diff = 100 - int(perc.sum())
    if diff != 0:
        idx = int(np.argmax(sample))
        perc[idx] += diff
    return {k: int(v) for k, v in zip(keys, perc)}


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


async def enrich_city_demographics(
    seed: str,
    world_id: Optional[str] = None,
    include_towns: bool = False,
    max_npcs_per_settlement: int = 100,
) -> Dict[str, Any]:
    rng = random.Random(f"demo:{seed}")
    updated_settlements = 0
    updated_npcs = 0

    # Fetch all locations and split by kind
    all_locations = await world_service.get_entities_by_type(EntityType.LOCATION, limit=10000)
    # Prefer exact subgraph of the specified world if provided
    if world_id:
        from uuid import UUID
        ctx = await world_service.get_entity_context(UUID(world_id), max_depth=3)
        sub_locations = [e for e in ctx if e.type == EntityType.LOCATION]
    else:
        sub_locations = all_locations

    regions = [e for e in sub_locations if (e.metadata or {}).get("location_kind") == "region"]
    region_ids = {str(r.id) for r in regions}

    cities = [e for e in sub_locations if (e.metadata or {}).get("location_kind") == "city"]
    towns = []
    if include_towns:
        towns = [e for e in sub_locations if (e.metadata or {}).get("location_kind") == "town"]

    # Index regions by continent and by id
    regions_by_continent: Dict[str, List[BaseEntity]] = {}
    region_by_id: Dict[str, BaseEntity] = {}
    for reg in regions:
        region_by_id[str(reg.id)] = reg
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

    settlements: List[Tuple[BaseEntity, str]] = [(c, "city") for c in cities] + ([(t, "town") for t in towns] if include_towns else [])

    for place, kind in settlements:
        if kind == "city":
            continent_id = (place.metadata or {}).get("parent_id")
            if not continent_id:
                continue
            rlist = regions_by_continent.get(str(continent_id), [])
            if not rlist:
                continue
            nearest_region = await _nearest_region_for_city(place, rlist)
        else:
            region_id = (place.metadata or {}).get("parent_id")
            nearest_region = region_by_id.get(str(region_id)) if region_id else None

        biome = (nearest_region.metadata or {}).get("primary_biome", "plains") if nearest_region else "plains"
        base = _race_prior_for_biome(str(biome))
        adjusted = _apply_modifiers(base, place)
        # Sample final distribution via Dirichlet for variability per settlement
        seed_int = int(UUID(str(place.id))) % (2**31 - 1)
        dist = _dirichlet_sample(adjusted, concentration=60.0, seed=seed_int)

        place.metadata.setdefault("demographics", {})
        place.metadata["demographics"]["race_distribution"] = dist
        await world_service.update_entity(place, actor_id=place.id)
        updated_settlements += 1

        child_locations = [e for e in all_locations if (e.metadata or {}).get("parent_id") == str(place.id)]
        child_ids = {str(e.id) for e in child_locations}
        second_level = [e for e in all_locations if (e.metadata or {}).get("parent_id") in child_ids]
        second_ids = {str(e.id) for e in second_level}
        target_loc_ids = child_ids | second_ids | ({str(place.id)} if kind == "town" else set())

        assigned = 0
        for loc_id in target_loc_ids:
            for npc in npcs_by_loc.get(loc_id, []) or []:
                if assigned >= max_npcs_per_settlement:
                    break
                if isinstance(npc.metadata, dict) and not npc.metadata.get("race"):
                    race = _weighted_choice(rng, dist)
                    npc.metadata["race"] = race
                    await world_service.update_entity(npc, actor_id=npc.id)
                    updated_npcs += 1
                    assigned += 1
            if assigned >= max_npcs_per_settlement:
                break

    return {"updated_settlements": updated_settlements, "updated_npcs": updated_npcs}


