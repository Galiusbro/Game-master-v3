from __future__ import annotations

"""Region generation system

Provides algorithms for:
- Classifying biomes based on elevation and climate
- Sampling region locations within continents
- Creating region entities with appropriate metadata
- Managing region-continent relationships
"""

import random
from typing import Any, Dict, List, Tuple

import numpy as np

from core.worldgen.utils import create_location_entity, link_to_parent
from core.worldgen.classifiers import (
    classify_biome,
    get_biome_characteristics,
    calculate_region_count,
)


# Moved to classifiers.py


# Moved to classifiers.py


# Moved to classifiers.py


async def create_region_entities(
    continent_info: Dict[str, Any],
    region_locations: List[Tuple[int, int, str, float]],
    grid_size: int,
    continent_index: int,
    world_actor_id: Any,
) -> List[Dict[str, Any]]:
    """Create region entities from location data.
    
    Args:
        continent_info: Dict with continent 'id', 'mask', 'center'
        region_locations: List of (y, x, biome, elevation) tuples
        grid_size: World grid size for coordinate normalization
        continent_index: Index of continent for naming
        world_actor_id: Actor ID for entity creation
        
    Returns:
        List of created region info dicts
    """
    created_regions: List[Dict[str, Any]] = []
    
    for ridx, (y, x, biome, elevation) in enumerate(region_locations, start=1):
        # Normalize coordinates
        u, v = x / grid_size, y / grid_size
        
        # Get biome characteristics
        characteristics = get_biome_characteristics(biome)
        
        # Create region entity using utils
        metadata = {
            "biome_type": biome,
            "elevation": round(elevation, 3),
            "fertility": characteristics["fertility"],
            "habitability": characteristics["habitability"],
            "resource_abundance": characteristics["resource_abundance"],
            "typical_resources": characteristics["typical_resources"],
            "climate": characteristics["climate"],
            "terrain_difficulty": characteristics["terrain_difficulty"],
            "explored": False,
            "danger_level": round(0.1 + characteristics["terrain_difficulty"] * 0.3, 2),
        }
        
        created_region = await create_location_entity(
            name=f"Region {continent_index}-{ridx}",
            description=f"A {biome} region with {characteristics['climate']} climate",
            location_kind="region",
            parent_id=continent_info["id"],
            center=[u, v],
            metadata=metadata,
            actor_id=world_actor_id,
        )
        
        # Link to continent using utils
        await link_to_parent(
            child_id=created_region.id,
            parent_id=continent_info["id"],
            relationship_type="LOCATED_IN",
            properties={"biome": biome, "elevation": elevation},
            actor_id=world_actor_id,
        )
        
        created_regions.append({
            "id": created_region.id,
            "center": (u, v),
            "biome": biome,
            "elevation": elevation,
            "characteristics": characteristics,
        })
    
    return created_regions


def sample_region_locations(
    continent_mask: np.ndarray,
    heightmap: np.ndarray,
    sea_level: float,
    region_count: int,
    rng: random.Random,
) -> List[Tuple[int, int, str, float]]:
    """Sample region locations within a continent.
    
    Args:
        continent_mask: Binary mask of continent area
        heightmap: Height values array
        sea_level: Sea level threshold
        region_count: Number of regions to create
        rng: Random number generator
        
    Returns:
        List of (y, x, biome, elevation) tuples for regions
    """
    # Find all land pixels in continent
    ys, xs = np.where(continent_mask > 0)
    if len(ys) == 0:
        return []
    
    # Sample random locations
    if len(ys) <= region_count:
        # Use all available locations
        chosen_indices = list(range(len(ys)))
    else:
        # Sample without replacement
        chosen_indices = rng.sample(range(len(ys)), k=region_count)
    
    # Create region data
    regions = []
    for ci in chosen_indices:
        y, x = int(ys[ci]), int(xs[ci])
        elevation = float(heightmap[y, x])
        biome = classify_biome(elevation, sea_level)
        
        regions.append((y, x, biome, elevation))
    
    return regions


async def generate_regions_for_continent(
    continent_info: Dict[str, Any],
    heightmap: np.ndarray,
    sea_level: float,
    grid_size: int,
    continent_index: int,
    rng: random.Random,
    world_actor_id: Any,
) -> List[Dict[str, Any]]:
    """Generate all regions for a single continent.
    
    Args:
        continent_info: Dict with continent 'id', 'mask', 'center'
        heightmap: Height values array
        sea_level: Sea level threshold
        grid_size: World grid size
        continent_index: Index of continent for naming
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        List of created region info dicts
    """
    continent_mask = continent_info["mask"]
    continent_size = int(continent_mask.sum())
    
    # Calculate number of regions
    region_count = calculate_region_count(continent_size, grid_size)
    
    # Sample region locations
    region_locations = sample_region_locations(
        continent_mask, heightmap, sea_level, region_count, rng
    )
    
    # Create region entities
    created_regions = await create_region_entities(
        continent_info, region_locations, grid_size, continent_index, world_actor_id
    )
    
    return created_regions


async def generate_all_regions(
    continents_info: List[Dict[str, Any]],
    heightmap: np.ndarray,
    sea_level: float,
    grid_size: int,
    rng: random.Random,
    world_actor_id: Any,
) -> Tuple[List[str], Dict[Any, List[Dict[str, Any]]]]:
    """Generate regions for all continents.
    
    Args:
        continents_info: List of continent dicts with 'id', 'mask', 'center'
        heightmap: Height values array
        sea_level: Sea level threshold
        grid_size: World grid size
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        Tuple of (region_ids, regions_by_continent_dict)
    """
    all_region_ids: List[str] = []
    regions_by_continent: Dict[Any, List[Dict[str, Any]]] = {}
    
    for cidx, continent_info in enumerate(continents_info, start=1):
        continent_regions = await generate_regions_for_continent(
            continent_info, heightmap, sea_level, grid_size, cidx, rng, world_actor_id
        )
        
        # Collect region IDs
        region_ids = [str(region["id"]) for region in continent_regions]
        all_region_ids.extend(region_ids)
        
        # Group by continent
        regions_by_continent[continent_info["id"]] = continent_regions
    
    return all_region_ids, regions_by_continent
