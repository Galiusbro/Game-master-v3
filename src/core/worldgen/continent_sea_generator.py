from __future__ import annotations

"""Continent and sea generation system

Provides algorithms for:
- Processing connected components from land/water masks
- Creating continent and sea entities with geographic metadata
- Calculating sizes, perimeters, and other geographic properties
- Managing world-level geographic relationships
"""

from typing import Any, Dict, List, Tuple

import numpy as np

from core.worldgen.geo_engine import center_of_mask
from core.worldgen.utils import create_location_entity, link_to_parent
from core.worldgen.constants import WORLD_AREA_KM2
from core.worldgen.classifiers import (
    classify_continent_type,
    classify_sea_type,
    get_depth_category,
    estimate_climate_zones,
)


def calculate_geographic_properties(mask: np.ndarray, grid_size: int) -> Dict[str, Any]:
    """Calculate geographic properties for a landmass or water body.
    
    Args:
        mask: Binary mask of the geographic feature
        grid_size: Total world grid size for scaling
        
    Returns:
        Dict with calculated properties
    """
    total_pixels = int(mask.sum())
    if total_pixels == 0:
        return {"area_km2": 0, "perimeter_approx": 0, "compactness": 0}
    
    # Calculate area using world constants
    total_world_pixels = grid_size * grid_size
    area_km2 = int((total_pixels / total_world_pixels) * WORLD_AREA_KM2)
    
    # Approximate perimeter by counting edge pixels
    ys, xs = np.where(mask > 0)
    edge_pixels = 0
    for y, x in zip(ys, xs):
        # Check if this pixel is on the edge (has at least one non-mask neighbor)
        for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            ny, nx = y + dy, x + dx
            if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and 
                mask[ny, nx] == 0):
                edge_pixels += 1
                break
    
    # Rough perimeter in km
    pixels_per_km = grid_size / 10000  # pixels per km
    perimeter_approx = int(edge_pixels / pixels_per_km)
    
    # Compactness measure (circle would be 1.0)
    if perimeter_approx > 0:
        compactness = round(4 * np.pi * area_km2 / (perimeter_approx ** 2), 3)
    else:
        compactness = 0
    
    return {
        "area_km2": area_km2,
        "perimeter_approx": perimeter_approx,
        "compactness": min(1.0, compactness),  # Cap at 1.0
        "pixel_count": total_pixels,
    }


# Moved to classifiers.py


# Moved to classifiers.py


async def create_continent_entities(
    land_components: List[np.ndarray],
    grid_size: int,
    world_id: Any,
    max_continents: int = 3,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Create continent entities from land components.
    
    Args:
        land_components: List of land component masks (sorted by size)
        grid_size: World grid size
        world_id: Parent world entity ID
        max_continents: Maximum number of continents to create
        
    Returns:
        Tuple of (continent_ids, continents_info)
    """
    continent_ids: List[str] = []
    continents_info: List[Dict[str, Any]] = []
    
    # Take only the largest components
    selected_components = land_components[:max(1, min(max_continents, len(land_components)))]
    
    for idx, comp in enumerate(selected_components, start=1):
        # Calculate geographic properties
        properties = calculate_geographic_properties(comp, grid_size)
        continent_type = classify_continent_type(properties)
        cx, cy = center_of_mask(comp)
        
        # Create continent entity using utils
        metadata = {
            "continent_type": continent_type,
            "area_km2": properties["area_km2"],
            "perimeter_approx": properties["perimeter_approx"],
            "compactness": properties["compactness"],
            "pixel_count": properties["pixel_count"],
            "exploration_difficulty": round(0.1 + (1 - properties["compactness"]) * 0.3, 2),
            "climate_zones": estimate_climate_zones(properties["area_km2"]),
        }
        
        created_continent = await create_location_entity(
            name=f"Continent {idx}",
            description=f"A {continent_type} with vast lands and diverse regions",
            location_kind="continent",
            parent_id=world_id,
            center=[cx, cy],
            metadata=metadata,
            actor_id=world_id,
        )
        continent_ids.append(str(created_continent.id))
        
        # Store info for further processing
        continents_info.append({
            "id": created_continent.id,
            "mask": comp,
            "center": (cx, cy),
            "type": continent_type,
            "properties": properties,
        })
    
    return continent_ids, continents_info


# Moved to classifiers.py


async def create_sea_entities(
    water_components: List[np.ndarray],
    grid_size: int,
    world_id: Any,
    max_seas: int = 5,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Create sea entities from water components.
    
    Args:
        water_components: List of water component masks (sorted by size)
        grid_size: World grid size
        world_id: Parent world entity ID
        max_seas: Maximum number of seas to create
        
    Returns:
        Tuple of (sea_ids, seas_info)
    """
    sea_ids: List[str] = []
    seas_info: List[Dict[str, Any]] = []
    
    # Take only the largest water bodies
    selected_components = water_components[:max(1, min(max_seas, len(water_components)))]
    
    for idx, comp in enumerate(selected_components, start=1):
        # Calculate geographic properties
        properties = calculate_geographic_properties(comp, grid_size)
        sea_type = classify_sea_type(properties)
        cx, cy = center_of_mask(comp)
        
        # Create sea entity using utils
        metadata = {
            "sea_type": sea_type,
            "area_km2": properties["area_km2"],
            "perimeter_approx": properties["perimeter_approx"],
            "compactness": properties["compactness"],
            "pixel_count": properties["pixel_count"],
            "navigation_difficulty": round(0.2 + (properties["area_km2"] / 100000000) * 0.6, 2),
            "storm_frequency": round(0.1 + (1 - properties["compactness"]) * 0.4, 2),
            "depth_category": get_depth_category(sea_type),
        }
        
        created_sea = await create_location_entity(
            name=f"Sea {idx}",
            description=f"A {sea_type} with deep waters and maritime routes",
            location_kind="sea",
            parent_id=world_id,
            center=[cx, cy],
            metadata=metadata,
            actor_id=world_id,
        )
        sea_ids.append(str(created_sea.id))
        
        # Store info for further processing
        seas_info.append({
            "id": created_sea.id,
            "center": (cx, cy),
            "type": sea_type,
            "properties": properties,
        })
    
    return sea_ids, seas_info


# Moved to classifiers.py


async def generate_continents_and_seas(
    land_components: List[np.ndarray],
    water_components: List[np.ndarray],
    grid_size: int,
    world_id: Any,
) -> Tuple[List[str], List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate all continents and seas from geographic components.
    
    Args:
        land_components: List of land component masks (should be pre-sorted)
        water_components: List of water component masks (should be pre-sorted)
        grid_size: World grid size
        world_id: Parent world entity ID
        
    Returns:
        Tuple of (continent_ids, sea_ids, continents_info, seas_info)
    """
    # Create continents
    continent_ids, continents_info = await create_continent_entities(
        land_components, grid_size, world_id
    )
    
    # Create seas
    sea_ids, seas_info = await create_sea_entities(
        water_components, grid_size, world_id
    )
    
    return continent_ids, sea_ids, continents_info, seas_info
