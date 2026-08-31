from __future__ import annotations

"""River generation system

Provides algorithms for:
- Finding coastlines and water targets
- Tracing river paths from highlands to coast
- Selecting optimal river source points
- Creating river entities with proper metadata
"""

import random
from typing import Any, Dict, List, Tuple

import numpy as np
import numpy.typing as npt

from core.worldgen.utils import create_location_entity, link_to_parent


def find_nearest_coast_point(
    target_u: float, target_v: float, coast_coordinates: npt.NDArray[np.float64] | None
) -> Tuple[float, float]:
    """Find the nearest coastline point to given coordinates.
    
    Args:
        target_u: Target x coordinate (normalized 0-1)
        target_v: Target y coordinate (normalized 0-1)
        coast_coordinates: Array of coast points as [[u1, v1], [u2, v2], ...]
        
    Returns:
        Tuple of (nearest_u, nearest_v) coordinates
    """
    if coast_coordinates is None or coast_coordinates.shape[0] == 0:
        # fallback to world center
        return 0.5, 0.5
    
    du = coast_coordinates[:, 0] - target_u
    dv = coast_coordinates[:, 1] - target_v
    idx = int(np.argmin(du * du + dv * dv))
    return float(coast_coordinates[idx, 0]), float(coast_coordinates[idx, 1])


def trace_river_path(
    start_y: int,
    start_x: int,
    heightmap: npt.NDArray[np.float32],
    water_mask: npt.NDArray[np.uint8],
    coast_coordinates: npt.NDArray[np.float64] | None,
    max_steps: int = 1000,
) -> Tuple[List[Tuple[float, float]], bool]:
    """Trace a river path from source to water using downhill flow.
    
    Args:
        start_y: Starting y coordinate in grid
        start_x: Starting x coordinate in grid
        heightmap: Height values array
        water_mask: Binary water mask
        coast_coordinates: Coastline points for guidance
        max_steps: Maximum pathfinding steps
        
    Returns:
        Tuple of (path_points, reached_water) where path_points are normalized coordinates
    """
    size = heightmap.shape[0]
    y, x = start_y, start_x
    path: List[Tuple[float, float]] = []
    
    # Find target coast for guidance
    target_u, target_v = find_nearest_coast_point(x / size, y / size, coast_coordinates)
    reached_water = False
    
    for _ in range(max_steps):
        path.append((x / size, y / size))
        
        # Check if we've reached water
        if water_mask[y, x]:
            reached_water = True
            break
            
        # Find best next step: prioritize lower elevation, then proximity to coast
        best_pos = (y, x)
        best_score = float("inf")
        
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                    
                ny, nx = y + dy, x + dx
                if 0 <= ny < size and 0 <= nx < size:
                    elevation = float(heightmap[ny, nx])
                    # Distance to target coast (normalized)
                    dist_to_coast = (nx / size - target_u) ** 2 + (ny / size - target_v) ** 2
                    # Heavily weight elevation, lightly weight coast proximity
                    score = elevation * 0.95 + dist_to_coast * 0.05
                    
                    if score < best_score:
                        best_score = score
                        best_pos = (ny, nx)
        
        # If no improvement found, try fallback strategies
        if best_pos == (y, x):
            # Strategy 1: Find any strictly lower neighbor
            current_elevation = float(heightmap[y, x])
            lower_found = False
            
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < size and 0 <= nx < size and 
                        float(heightmap[ny, nx]) < current_elevation):
                        y, x = ny, nx
                        lower_found = True
                        break
                if lower_found:
                    break
            
            # Strategy 2: If still stuck, nudge toward coast
            if not lower_found:
                new_y = y + (1 if target_v > y / size else -1 if target_v < y / size else 0)
                new_x = x + (1 if target_u > x / size else -1 if target_u < x / size else 0)
                
                if 0 <= new_y < size and 0 <= new_x < size:
                    y, x = new_y, new_x
                else:
                    break  # Cannot move further
        else:
            y, x = best_pos
    
    return path, reached_water


def select_river_sources(
    continent_mask: npt.NDArray[np.uint8],
    heightmap: npt.NDArray[np.float32],
    rng: random.Random,
    target_count: Tuple[int, int] = (1, 3),
) -> List[Tuple[int, int]]:
    """Select optimal source points for rivers within a continent.
    
    Args:
        continent_mask: Binary mask of continent area
        heightmap: Height values array
        rng: Random number generator
        target_count: (min, max) rivers to generate
        
    Returns:
        List of (y, x) coordinates for river sources
    """
    # Find all land pixels in continent
    cy, cx = np.where(continent_mask > 0)
    if len(cy) == 0:
        return []
    
    # Try to use upper quartile of elevations as seeds
    heights_in_continent = heightmap[cy, cx]
    elevation_threshold = float(np.quantile(heights_in_continent, 0.9))
    
    # Find high elevation candidates
    high_y, high_x = np.where((continent_mask > 0) & (heightmap >= elevation_threshold))
    
    # Fallback if no high elevations found
    if len(high_y) == 0:
        # Pick highest points from random sample
        sample_size = min(50, len(cy))
        sample_indices = rng.sample(range(len(cy)), k=sample_size)
        candidates = [
            (float(heightmap[cy[i], cx[i]]), int(cy[i]), int(cx[i]))
            for i in sample_indices
        ]
        candidates.sort(reverse=True)  # Highest first
        
        high_y = np.array([c[1] for c in candidates[:5]], dtype=int)
        high_x = np.array([c[2] for c in candidates[:5]], dtype=int)
    
    # Select target number of rivers
    min_rivers, max_rivers = target_count
    num_rivers = max(min_rivers, min(max_rivers, len(high_y)))
    
    if len(high_y) > num_rivers:
        selected_indices = rng.sample(range(len(high_y)), k=num_rivers)
    else:
        selected_indices = list(range(len(high_y)))
    
    return [(int(high_y[i]), int(high_x[i])) for i in selected_indices]


async def generate_rivers_for_continent(
    continent_info: Dict[str, Any],
    heightmap: npt.NDArray[np.float32],
    water_mask: npt.NDArray[np.uint8],
    coast_coordinates: npt.NDArray[np.float64] | None,
    rng: random.Random,
    world_actor_id: Any,
) -> List[str]:
    """Generate rivers for a single continent.
    
    Args:
        continent_info: Dict with 'id', 'mask', 'center' keys
        heightmap: Height values array
        water_mask: Binary water mask
        coast_coordinates: Coastline points for guidance
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        List of created river entity IDs
    """
    continent_mask = continent_info["mask"]
    continent_id = continent_info["id"]
    
    # Select river source points
    river_sources = select_river_sources(continent_mask, heightmap, rng)
    
    created_river_ids: List[str] = []
    
    for i, (source_y, source_x) in enumerate(river_sources, start=1):
        # Trace river path
        path, reached_water = trace_river_path(
            source_y, source_x, heightmap, water_mask, coast_coordinates
        )
        
        # Filter out very short rivers that don't reach water
        if len(path) < 20 and not reached_water:
            continue
        
        # Create river entity using utils
        metadata = {
            "polyline": path,
            "length_km": len(path) * 2.0,  # Rough estimate
            "reaches_sea": reached_water,
        }
        
        created_river = await create_location_entity(
            name=f"River {str(continent_id)[:8]}-{i}",
            description="A winding river",
            location_kind="river",
            parent_id=continent_id,
            center=list(path[0]) if path else [0.5, 0.5],  # River start point
            metadata=metadata,
            actor_id=world_actor_id,
        )
        created_river_ids.append(str(created_river.id))
        
        # Link to continent using utils
        await link_to_parent(
            child_id=created_river.id,
            parent_id=continent_id,
            relationship_type="LOCATED_IN",
            properties=None,
            actor_id=world_actor_id,
        )
    
    return created_river_ids


async def generate_all_rivers(
    continents_info: List[Dict[str, Any]],
    heightmap: npt.NDArray[np.float32],
    water_mask: npt.NDArray[np.uint8],
    coast_coordinates: npt.NDArray[np.float64] | None,
    rng: random.Random,
    world_actor_id: Any,
) -> List[str]:
    """Generate rivers for all continents.
    
    Args:
        continents_info: List of continent dicts with 'id', 'mask', 'center'
        heightmap: Height values array
        water_mask: Binary water mask
        coast_coordinates: Coastline points for guidance
        rng: Random number generator
        world_actor_id: Actor ID for entity creation
        
    Returns:
        List of all created river entity IDs
    """
    all_river_ids: List[str] = []
    
    for continent_info in continents_info:
        continent_rivers = await generate_rivers_for_continent(
            continent_info, heightmap, water_mask, coast_coordinates, rng, world_actor_id
        )
        all_river_ids.extend(continent_rivers)
    
    return all_river_ids
