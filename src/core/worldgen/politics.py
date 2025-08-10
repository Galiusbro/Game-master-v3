from __future__ import annotations

"""Political generation (Stage 3)

Creates countries with basic laws/policies and establishes control over regions
and capitals. Keeps relationships consistent with the rest of the worldgen:
- Country is a LOCATION with location_kind=country
- LOCATED_IN edge from Country -> Continent
- CONTROLS edges from Country -> Region
- Capital city is linked via LOCATED_IN City -> Country and CONTROLS Country -> City

MVP: factions are postponed to avoid pipeline bloat.
"""

import random
from typing import Any, Dict, List, Tuple

from core.worldgen.utils import create_location_entity, link_to_parent
from core.world_service import world_service


async def generate_countries_and_laws(
    continents_info: List[Dict[str, Any]],
    regions_by_continent: Dict[Any, List[Dict[str, Any]]],
    capitals: Dict[Any, Dict[str, Any]],
    towns: List[Dict[str, Any]],
    rng: random.Random,
    world_actor_id: Any,
    countries_per_continent: Tuple[int, int] = (2, 4),
) -> Tuple[List[str], Dict[Any, List[Dict[str, Any]]]]:
    """Generate countries, assign regions, and set basic laws.

    Returns:
        - List of created country IDs
        - Mapping continent_id -> list of country info dicts
    """
    created_country_ids: List[str] = []
    countries_by_continent: Dict[Any, List[Dict[str, Any]]] = {}

    # Build index of towns by region for capital selection
    towns_by_region: Dict[Any, List[Dict[str, Any]]] = {}
    for t in towns:
        rid = t.get("region_id")
        if rid is None:
            continue
        towns_by_region.setdefault(rid, []).append(t)

    for cinfo in continents_info:
        continent_id = cinfo["id"]
        region_list = list(regions_by_continent.get(continent_id, []))
        if not region_list:
            countries_by_continent[continent_id] = []
            continue

        rng.shuffle(region_list)
        min_c, max_c = countries_per_continent
        target_countries = max(min_c, min(max_c, max(1, len(region_list) // 3)))

        # Chunk regions into groups for countries (simple partition for MVP)
        chunk_size = max(1, len(region_list) // target_countries)
        region_chunks = [region_list[i : i + chunk_size] for i in range(0, len(region_list), chunk_size)]
        # If we have too many chunks due to rounding, merge the tail
        while len(region_chunks) > target_countries:
            region_chunks[-2].extend(region_chunks[-1])
            region_chunks.pop()

        countries_here: List[Dict[str, Any]] = []

        for idx, assigned_regions in enumerate(region_chunks, start=1):
            if not assigned_regions:
                continue

            # Country name/government/laws
            government = rng.choice(["monarchy", "theocracy", "city_states", "tribal"])
            lawfulness = rng.choice(["strict", "moderate", "lenient"])
            magic_legality = rng.choice(["banned", "licensed", "free"]) if government != "theocracy" else rng.choice(["licensed", "banned"])  # more restrictive
            trade_tax = rng.choice([0, 2, 5, 10])
            curfew = rng.random() < 0.25
            weapons_open_carry = rng.random() < 0.5

            # Place country center near average of region centers
            avg_u = sum(r["center"][0] for r in assigned_regions) / len(assigned_regions)
            avg_v = sum(r["center"][1] for r in assigned_regions) / len(assigned_regions)

            metadata = {
                "government": government,
                "lawfulness": lawfulness,
                "magic_legality": magic_legality,
                "taxes": {"trade_tax": trade_tax},
                "laws": {
                    "magic_permits_required": magic_legality == "licensed",
                    "curfew": curfew,
                    "weapons_open_carry": weapons_open_carry,
                },
            }

            created_country = await create_location_entity(
                name=f"Country {str(continent_id)[:6]}-{idx}",
                description="A sovereign country controlling several regions",
                location_kind="country",
                parent_id=continent_id,
                center=[avg_u, avg_v],
                metadata=metadata,
                actor_id=world_actor_id,
            )
            created_country_ids.append(str(created_country.id))

            # Country LOCATED_IN Continent
            await link_to_parent(
                child_id=created_country.id,
                parent_id=continent_id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=world_actor_id,
            )

            # Country CONTROLS Regions
            for region in assigned_regions:
                await world_service.create_relationship(
                    from_entity_id=created_country.id,
                    to_entity_id=region["id"],
                    relationship_type="CONTROLS",
                    properties=None,
                    actor_id=world_actor_id,
                )

            # Pick a capital: prefer a town inside assigned regions; fallback to continent capital
            capital_city_id = None
            selected_town = None
            for region in assigned_regions:
                tr = towns_by_region.get(region["id"]) or []
                if tr:
                    selected_town = tr[0]
                    break

            if selected_town is not None:
                capital_city_id = selected_town["id"]
            else:
                cap = capitals.get(continent_id)
                if cap:
                    capital_city_id = cap["id"]

            country_info = {
                "id": created_country.id,
                "center": (avg_u, avg_v),
                "region_ids": [r["id"] for r in assigned_regions],
                "capital_id": capital_city_id,
                "metadata": metadata,
            }

            # Add LOCATED_IN for capital and CONTROLS to capital city/town
            if capital_city_id is not None:
                await world_service.create_relationship(
                    from_entity_id=created_country.id,
                    to_entity_id=capital_city_id,
                    relationship_type="CONTROLS",
                    properties={"role": "capital"},
                    actor_id=world_actor_id,
                )
                # Allow city to be "located in" the country as well (multi-parent ok for our graph)
                await link_to_parent(
                    child_id=capital_city_id,
                    parent_id=created_country.id,
                    relationship_type="LOCATED_IN",
                    properties={"note": "capital"},
                    actor_id=world_actor_id,
                )

            # Light upgrade: control & guard presence for towns inside country's regions
            controlled_region_ids = set(country_info["region_ids"])
            lawfulness = metadata.get("lawfulness", "moderate")
            guard_base = {"strict": 0.8, "moderate": 0.6, "lenient": 0.4}.get(lawfulness, 0.6)

            for region in assigned_regions:
                for t in towns_by_region.get(region["id"], []) or []:
                    # CONTROLS Country -> Town
                    await world_service.create_relationship(
                        from_entity_id=created_country.id,
                        to_entity_id=t["id"],
                        relationship_type="CONTROLS",
                        properties={"level": "town"},
                        actor_id=world_actor_id,
                    )
                    # LOCATED_IN Town -> Country (multi-parent)
                    await link_to_parent(
                        child_id=t["id"],
                        parent_id=created_country.id,
                        relationship_type="LOCATED_IN",
                        properties=None,
                        actor_id=world_actor_id,
                    )

                    # Update town guard presence lightly based on lawfulness and walls
                    town_entity = t.get("entity")
                    try:
                        if town_entity is None:
                            # Fallback fetch if entity not passed
                            from uuid import UUID
                            fetched = await world_service.get_entity(UUID(str(t["id"])))
                            town_entity = fetched
                        if town_entity is not None:
                            has_walls = bool(town_entity.metadata.get("has_walls", False))
                            guard_presence = guard_base + (0.1 if has_walls else 0.0)
                            guard_presence = max(0.1, min(1.0, round(guard_presence, 2)))
                            town_entity.metadata["guard_presence"] = guard_presence
                            await world_service.update_entity(town_entity, actor_id=world_actor_id)
                    except Exception:
                        # Non-fatal; continue generating
                        pass

            countries_here.append(country_info)

        countries_by_continent[continent_id] = countries_here

    return created_country_ids, countries_by_continent


