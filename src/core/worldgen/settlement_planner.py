from __future__ import annotations

"""Settlement and road planning system

Provides algorithms for:
- Creating capitals for continents
- Placing towns in regions
- Connecting settlements with roads
- Managing settlement hierarchies and relationships
"""

import random
from typing import Any, Dict, List, Tuple

from core.worldgen.utils import (
    create_location_entity,
    link_to_parent,
    calculate_distance_km,
    generate_age_range,
    get_safety_rating,
)
from core.world_service import world_service
from core.worldgen.constants import POPULATION_RANGES, AGE_RANGES
from core.worldgen.classifiers import get_trade_specialization, get_road_terrain


async def create_capital_cities(
    continents_info: List[Dict[str, Any]],
    rng: random.Random,
    world_actor_id: Any,
) -> Dict[Any, Dict[str, Any]]:
    """Create capital cities for each continent.
    
    Args:
        continents_info: List of continent dicts with 'id', 'center', 'mask'
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        Dict mapping continent_id -> {'id': capital_id, 'center': (x, y)}
    """
    capitals: Dict[Any, Dict[str, Any]] = {}
    
    for idx, cinfo in enumerate(continents_info, start=1):
        cx, cy = cinfo["center"]
        
        # Create capital city using utils
        pop_min, pop_max = POPULATION_RANGES["capital"]
        age_min, age_max = AGE_RANGES["capital"]
        
        metadata = {
            "population_estimate": rng.randint(pop_min, pop_max),
            "has_walls": True,
            "is_capital": True,
            "founded_age": generate_age_range(age_min, age_max, rng),
        }
        
        created_city = await create_location_entity(
            name=f"Capital City {idx}",
            description="A major city and seat of power",
            location_kind="city",
            parent_id=cinfo["id"],
            center=[cx, cy],
            metadata=metadata,
            actor_id=world_actor_id,
        )
        
        # Link to continent using utils
        await link_to_parent(
            child_id=created_city.id,
            parent_id=cinfo["id"],
            relationship_type="LOCATED_IN",
            properties=None,
            actor_id=world_actor_id,
        )
        
        capitals[cinfo["id"]] = {
            "id": created_city.id,
            "center": (cx, cy),
            "entity": created_city,
        }
    
    return capitals


async def create_regional_towns(
    regions_by_continent: Dict[Any, List[Dict[str, Any]]],
    rng: random.Random,
    world_actor_id: Any,
    towns_per_continent: Tuple[int, int] = (3, 6),
) -> List[Dict[str, Any]]:
    """Create towns in regions across continents.
    
    Args:
        regions_by_continent: Dict mapping continent_id -> list of region info
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        towns_per_continent: (min, max) towns per continent
        
    Returns:
        List of created town info dicts with 'id', 'center', 'continent_id'
    """
    created_towns: List[Dict[str, Any]] = []
    
    for continent_id, region_list in regions_by_continent.items():
        # Shuffle regions and limit town count
        rng.shuffle(region_list)
        min_towns, max_towns = towns_per_continent
        num_towns = max(min_towns, min(max_towns, len(region_list)))
        selected_regions = region_list[:num_towns]
        
        for ridx, region in enumerate(selected_regions, start=1):
            tu, tv = region["center"]
            biome = region.get("biome", "plains")
            
            # Create town using utils with biome-adjusted characteristics
            base_pop = POPULATION_RANGES["town_base"]
            variation = POPULATION_RANGES["town_variation"]
            
            # Biome adjustments
            if biome == "coastal":
                base_pop = int(base_pop * 1.5)
            elif biome == "mountains":
                base_pop = int(base_pop * 0.75)
            elif biome == "forest":
                base_pop = int(base_pop * 1.25)
            
            age_min, age_max = AGE_RANGES["town"]
            
            metadata = {
                "population_estimate": rng.randint(base_pop, base_pop + variation),
                "has_walls": rng.random() < 0.3,
                "primary_biome": biome,
                "founded_age": generate_age_range(age_min, age_max, rng),
                "trade_specialization": get_trade_specialization(biome, rng),
            }
            
            created_town = await create_location_entity(
                name=f"Town {str(continent_id)[:6]}-{ridx}",
                description=f"A {biome} town with local commerce",
                location_kind="town",
                parent_id=region["id"],
                center=[tu, tv],
                metadata=metadata,
                actor_id=world_actor_id,
            )
            
            # Link to region using utils
            await link_to_parent(
                child_id=created_town.id,
                parent_id=region["id"],
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=world_actor_id,
            )
            
            created_towns.append({
                "id": created_town.id,
                "center": (tu, tv),
                "continent_id": continent_id,
                "region_id": region["id"],
                "biome": biome,
                "entity": created_town,
            })
    
    return created_towns


# Moved to classifiers.py


async def create_road_network(
    capitals: Dict[Any, Dict[str, Any]],
    towns: List[Dict[str, Any]],
    rng: random.Random,
    world_actor_id: Any,
) -> List[str]:
    """Create roads connecting capitals to towns.
    
    Args:
        capitals: Dict mapping continent_id -> capital info
        towns: List of town info dicts
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        List of created road entity IDs
    """
    created_road_ids: List[str] = []
    
    for town in towns:
        continent_id = town["continent_id"]
        capital = capitals.get(continent_id)
        
        if not capital:
            continue
            
        tu, tv = town["center"]
        cu, cv = capital["center"]
        
        # Calculate road properties using utils
        distance_km = calculate_distance_km((cu, cv), (tu, tv))
        
        # Road safety based on biome
        base_safety = 0.6
        terrain_penalty = 0.0
        
        if town.get("biome") == "mountains":
            base_safety = 0.4
            terrain_penalty = 0.2
        elif town.get("biome") == "coastal":
            base_safety = 0.7
        
        # Distance penalty
        distance_penalty = min(0.2, distance_km / 10000.0)
        safety = get_safety_rating(base_safety, distance_penalty, terrain_penalty)
        
        # Create road using utils
        terrain = get_road_terrain(town.get("biome", "plains"), rng)
        
        metadata = {
            "from_id": str(capital["id"]),
            "to_id": str(town["id"]),
            "distance_km": round(distance_km, 1),
            "safety": safety,
            "terrain": terrain,
            "road_type": "primary",
            "maintenance_level": rng.choice(["good", "fair", "poor"]),
            "toll_required": rng.random() < 0.2,
        }
        
        # Mark unsafe if low safety
        is_safe_value = None if safety >= 0.5 else False
        
        created_road = await create_location_entity(
            name=f"Road {str(capital['id'])[:6]}-{str(town['id'])[:6]}",
            description=f"A {terrain} road connecting capital to town",
            location_kind="road",
            parent_id=continent_id,
            center=[(cu + tu) / 2, (cv + tv) / 2],  # Road center
            metadata=metadata,
            actor_id=world_actor_id,
            is_safe=is_safe_value,
        )
        created_road_ids.append(str(created_road.id))
        
        # Connect road to both endpoints using utils
        await link_to_parent(
            child_id=created_road.id,
            parent_id=capital["id"],
            relationship_type="CONNECTS_TO",
            properties={"direction": "from_capital"},
            actor_id=world_actor_id,
        )
        
        await link_to_parent(
            child_id=created_road.id,
            parent_id=town["id"],
            relationship_type="CONNECTS_TO",
            properties={"direction": "to_town"},
            actor_id=world_actor_id,
        )
    
    return created_road_ids


# Moved to classifiers.py


async def generate_settlements_and_roads(
    continents_info: List[Dict[str, Any]],
    regions_by_continent: Dict[Any, List[Dict[str, Any]]],
    rng: random.Random,
    world_actor_id: Any,
) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Generate all settlements and connecting roads.
    
    Args:
        continents_info: List of continent information
        regions_by_continent: Dict mapping continent_id -> regions
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        Tuple of (city_ids, town_ids, road_ids)
    """
    # Create capitals
    capitals = await create_capital_cities(continents_info, rng, world_actor_id)
    city_ids = [str(cap["id"]) for cap in capitals.values()]
    
    # Create towns
    towns = await create_regional_towns(regions_by_continent, rng, world_actor_id)
    
    # Create road network
    road_ids = await create_road_network(capitals, towns, rng, world_actor_id)
    
    return city_ids, towns, road_ids
