from __future__ import annotations

"""High-level world generation pipeline (MVP)

Implements the orchestrator that:
- initializes RNG from seed
- generates macro geography (heightmap, water mask, rivers)
- segments regions and assigns biomes
- persists entities via world_service

Detailed algorithms are intentionally simple in MVP and follow docs/World_design.md.
"""

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from collections import Counter
from uuid import UUID

import numpy as np

from core.world_service import world_service
from core.worldgen.villages import generate_basic_villages
from core.worldgen.poi import generate_basic_poi
from core.worldgen.city_builder import build_minimal_city_structure
from core.worldgen.npc_generator import (
    generate_basic_npcs,
    generate_citizens_for_districts,
    generate_rare_specialists,
)
from core.worldgen.geo_engine import (
    generate_fractal_noise,
    derive_water_mask,
    label_connected_components,
    center_of_mask,
    find_coastline_pixels,
)
from core.worldgen.river_system import generate_all_rivers
from core.worldgen.settlement_planner import generate_settlements_and_roads
from core.worldgen.politics import generate_countries_and_laws
from core.worldgen.bosses import generate_bosses
from core.worldgen.encounters import attach_region_encounters
from core.worldgen.region_generator import generate_all_regions
from core.worldgen.continent_sea_generator import generate_continents_and_seas
from core.worldgen.ai_enrichment_service import ai_world_enrichment_service
from domain.entities import BaseEntity, EntityType


# ------------------------------- Data models ------------------------------- #


@dataclass
class WorldGenParams:
    seed: str = "gmv3"
    grid_size: int = 256
    water_ratio: float = 0.65
    mountain_density: float = 0.4
    enable_ai_enrichment: bool = True


# ----------------------------- Helper routines ---------------------------- #


def _rng(seed: str) -> random.Random:
    return random.Random(seed)





# ------------------------------- Orchestrator ------------------------------ #


async def generate_world(params: WorldGenParams | Dict[str, Any]) -> Dict[str, Any]:
    """Generate a minimal world macrograph and persist entities.

    Returns a summary dict with created entity counts and IDs.
    """
    if isinstance(params, dict):
        params = WorldGenParams(
            seed=str(params.get("seed", "gmv3")),
            grid_size=int(params.get("grid_size", 256)),
            water_ratio=float(params.get("water_ratio", 0.65)),
            mountain_density=float(params.get("mountain_density", 0.4)),
            enable_ai_enrichment=bool(params.get("enable_ai_enrichment", True)),
        )

    rng = _rng(params.seed)
    size = params.grid_size

    # 1) Heightmap (simple fractal)
    height = generate_fractal_noise(rng, size=size, octaves=5)

    # 2) Sea level & water mask
    sea_level, is_water = derive_water_mask(height, params.water_ratio)

    # 3) Components → continents and seas (very rough)
    land_mask = (is_water == 0).astype(np.uint8)
    land_components = label_connected_components(land_mask)
    water_components = label_connected_components(is_water)

    # 4) Persist very coarse World, Continents, Seas
    summary: Dict[str, Any] = {
        "continents": [],
        "seas": [],
        "regions": [],
        "rivers": [],
        "cities": [],
        "towns": [],
        "roads": [],
        "districts": [],
        "streets": [],
        "buildings": [],
        "villages": [],
        "poi": [],
        "countries": [],
        "npcs": [],
        "bosses": [],
        "npc_races": {},
    }

    world_entity = BaseEntity(type=EntityType.LOCATION, name="World", description="Generated world")
    world = await world_service.create_entity(entity=world_entity, actor_id=world_entity.id)

    # 4) Continents and seas from connected components
    land_components.sort(key=lambda m: int(m.sum()), reverse=True)
    water_components.sort(key=lambda m: int(m.sum()), reverse=True)
    
    continent_ids, sea_ids, continents_info, seas_info = await generate_continents_and_seas(
        land_components, water_components, size, world.id
    )
    summary["continents"].extend(continent_ids)
    summary["seas"].extend(sea_ids)

    # 5) Regions per continent with biome classification
    region_ids, regions_by_continent = await generate_all_regions(
        continents_info, height, sea_level, size, rng, world.id
    )
    summary["regions"].extend(region_ids)

    # 6) Rivers (downhill walk from high cells to nearest coast)
    # Precompute coastline pixels (land cells adjacent to water)
    land = (is_water == 0)
    coast_mask = find_coastline_pixels(land, is_water)
    cy_coast, cx_coast = np.where(coast_mask == 1)
    coast_uv = None
    if len(cy_coast) > 0:
        coast_uv = np.stack([cx_coast / size, cy_coast / size], axis=1)

    river_ids = await generate_all_rivers(
        continents_info, height, is_water, coast_uv, rng, world.id
    )
    summary["rivers"].extend(river_ids)

    # 7) Settlements & roads: capitals, towns, and connecting infrastructure
    city_ids, towns_data, road_ids = await generate_settlements_and_roads(
        continents_info, regions_by_continent, rng, world.id
    )
    summary["cities"].extend(city_ids)
    summary["towns"].extend([str(t["id"]) for t in towns_data])
    summary["roads"].extend(road_ids)

    # For city structure generation, we need capitals info
    capitals: Dict[Any, Dict[str, Any]] = {}
    for idx, cinfo in enumerate(continents_info, start=1):
        if idx - 1 < len(city_ids):
            capitals[cinfo["id"]] = {
                "id": city_ids[idx - 1], 
                "center": cinfo["center"]
            }

    # 8) Minimal city structure: districts, streets, essential buildings
    def _clamp01(x: float) -> float:
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    async def _create_districts_and_buildings(city_id: Any, center: Tuple[float, float], is_capital: bool) -> None:
        created = await build_minimal_city_structure(params.seed, city_id, center, is_capital)
        summary["districts"].extend(created.get("districts", []))
        summary["streets"].extend(created.get("streets", []))
        summary["buildings"].extend(created.get("buildings", []))

    # Apply to capitals and first couple of towns per continent
    for cinfo in continents_info:
        cap = capitals.get(cinfo["id"])
        if cap:
            await _create_districts_and_buildings(cap["id"], cap["center"], is_capital=True)

        # find towns in this continent (by parent chain stored in metadata)
        # We didn't keep an index; as a simple heuristic, pick any 2 recent towns
        sample_towns = summary["towns"][-2:]
        for tid in sample_towns:
            # Without fetching, place around continent center
            await _create_districts_and_buildings(tid, cinfo["center"], is_capital=False)

    # 9) NPCs for essential buildings (capitals and sample towns)
    building_ids_for_npcs = list(summary["buildings"])[:200]
    created_npcs = await generate_basic_npcs(params.seed, building_ids_for_npcs, world.id)
    summary["npcs"].extend(created_npcs)

    # 9.1) Citizens per district (2-3 per district, a bit больше в столицах)
    district_ids_for_npcs = list(summary["districts"])[:100]
    created_citizens = await generate_citizens_for_districts(params.seed, district_ids_for_npcs, world.id, per_district=3)
    summary["npcs"].extend(created_citizens)

    # 9.2) Rare specialists in capital districts
    specialists = await generate_rare_specialists(params.seed, district_ids_for_npcs, world.id)
    summary["npcs"].extend(specialists)

    # 10) Politics: Countries and basic laws/controls
    # Prepare simple towns info with region mapping
    towns_info: List[Dict[str, Any]] = towns_data
    country_ids, countries_by_continent = await generate_countries_and_laws(
        continents_info, regions_by_continent, capitals, towns_info, rng, world.id
    )
    summary["countries"] = [str(cid) for cid in country_ids]

    # 11) Villages (lightweight)
    villages_created = await generate_basic_villages(params.seed, regions_by_continent, per_region=2)
    summary["villages"] = [str(v["id"]) for v in villages_created]

    # 12) POI around towns and villages (lightweight)
    # Prepare settlements (town centers taken as continent center heuristic; villages have centers)
    settlements_for_poi: List[Dict[str, Any]] = []
    # approximate town centers with their parent region center (not fetched, so skip for now)
    settlements_for_poi.extend(villages_created)
    poi_created = await generate_basic_poi(params.seed, settlements_for_poi, per_settlement=2)
    summary["poi"] = [str(p) for p in poi_created]

    # 13) Bosses (one per continent, prefers ruin/lair POIs)
    bosses = await generate_bosses(params.seed, countries_by_continent, summary["poi"], rng, world.id, max_per_continent=1)
    summary["bosses"].extend(bosses)

    # 14) Encounter tables for regions (MVP)
    await attach_region_encounters(regions_by_continent, rng)

    # 15) AI ENRICHMENT - Batch process all entities for rich descriptions and lore
    if params.enable_ai_enrichment:
        print("🎨 Starting AI world enrichment phase...")
        try:
            summary = await ai_world_enrichment_service.enrich_world_batch(summary, str(world.id))
            print("✅ AI enrichment completed successfully!")
        except Exception as e:
            print(f"⚠️ AI enrichment failed, continuing with basic world: {e}")
            # Continue without enrichment - world is still functional
            summary["ai_enrichment"] = {"enriched": False, "error": str(e)}
    else:
        print("⏭️ AI enrichment disabled, using basic descriptions")
        summary["ai_enrichment"] = {"enriched": False, "reason": "disabled"}

    summary["world_id"] = str(world.id)
    summary["sea_level"] = sea_level
    summary["grid_size"] = size

    # Summarize NPC races (counts)
    try:
        race_counter: Counter[str] = Counter()
        for nid in summary["npcs"]:
            try:
                npc = await world_service.get_entity(UUID(str(nid)), EntityType.NPC)
                if npc and getattr(npc, "race", None) is not None:
                    # npc.race may be an Enum; use its value if available
                    race_value = getattr(npc.race, "value", str(npc.race))
                    race_counter[race_value] += 1
                else:
                    race_counter["unknown"] += 1
            except Exception:
                race_counter["unknown"] += 1
        summary["npc_races"] = dict(race_counter)
    except Exception:
        # Non-critical for generation
        summary["npc_races"] = {}
    return summary


