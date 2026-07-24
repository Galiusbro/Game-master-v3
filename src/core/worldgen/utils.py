from __future__ import annotations

"""Common utilities for world generation

Provides shared functions for:
- Entity creation patterns
- Relationship management
- Common calculations
- Metadata handling
"""

import random
from typing import Any, Dict, List, Optional

from core.world_service import world_service
from domain.entities import BaseEntity, EntityType, Location


async def create_location_entity(
    name: str,
    description: str,
    location_kind: str,
    parent_id: Any,
    center: List[float],
    metadata: Optional[Dict[str, Any]] = None,
    actor_id: Any = None,
    is_safe: Optional[bool] = None,
) -> BaseEntity:
    """Create a location entity with standard structure.
    
    Args:
        name: Entity name
        description: Entity description
        location_kind: Type of location (continent, region, city, etc.)
        parent_id: ID of parent entity
        center: [x, y] coordinates
        metadata: Additional metadata dict
        actor_id: Actor ID for entity creation
        
    Returns:
        Created entity
    """
    base_metadata = {
        "location_kind": location_kind,
        "parent_id": str(parent_id),
        "center": center,
    }
    
    if metadata:
        base_metadata.update(metadata)
    
    entity = Location(
        name=name,
        description=description,
        metadata=base_metadata,
        is_safe=is_safe if is_safe is not None else True,
    )
    
    return await world_service.create_entity(entity=entity, actor_id=actor_id)


async def link_to_parent(
    child_id: Any,
    parent_id: Any,
    relationship_type: str = "LOCATED_IN",
    properties: Optional[Dict[str, Any]] = None,
    actor_id: Any = None,
) -> None:
    """Create a relationship linking child to parent entity.
    
    Args:
        child_id: ID of child entity
        parent_id: ID of parent entity
        relationship_type: Type of relationship
        properties: Additional relationship properties
        actor_id: Actor ID for relationship creation
    """
    await world_service.create_relationship(
        from_entity_id=child_id,
        to_entity_id=parent_id,
        relationship_type=relationship_type,
        properties=properties,
        actor_id=actor_id,
    )
    # Also create a reverse traversal edge for convenience
    try:
        reverse_type = "CONTAINS" if relationship_type == "LOCATED_IN" else f"HAS_{relationship_type}"
        await world_service.create_relationship(
            from_entity_id=parent_id,
            to_entity_id=child_id,
            relationship_type=reverse_type,
            properties=None,
            actor_id=actor_id,
        )
    except Exception:
        pass


def normalize_coordinates(x: int, y: int, grid_size: int) -> List[float]:
    """Normalize grid coordinates to 0-1 range.
    
    Args:
        x: X coordinate in grid
        y: Y coordinate in grid
        grid_size: Size of the grid
        
    Returns:
        [normalized_x, normalized_y] list
    """
    return [x / grid_size, y / grid_size]


def estimate_population(
    base_pop: int,
    variation: int,
    rng: random.Random,
    multipliers: Optional[Dict[str, float]] = None,
) -> int:
    """Estimate population with random variation and optional multipliers.
    
    Args:
        base_pop: Base population number
        variation: Random variation range
        rng: Random number generator
        multipliers: Optional dict of condition -> multiplier
        
    Returns:
        Estimated population
    """
    population = rng.randint(base_pop, base_pop + variation)
    
    if multipliers:
        for condition, multiplier in multipliers.items():
            # This is a simplified approach - in practice you'd check conditions
            if rng.random() < 0.5:  # 50% chance to apply multiplier
                population = int(population * multiplier)
    
    return population


def calculate_distance_km(
    point1: tuple[float, float],
    point2: tuple[float, float],
    world_scale_km: float = 10000.0,
) -> float:
    """Calculate distance between two normalized coordinate points.
    
    Args:
        point1: (x, y) coordinates (0-1 normalized)
        point2: (x, y) coordinates (0-1 normalized)
        world_scale_km: Scale of world in kilometers
        
    Returns:
        Distance in kilometers
    """
    import math
    
    x1, y1 = point1
    x2, y2 = point2
    
    # Calculate normalized distance
    dx = x2 - x1
    dy = y2 - y1
    normalized_distance = math.hypot(dx, dy)
    
    # Scale to kilometers
    return normalized_distance * world_scale_km


def generate_age_range(
    min_age: int,
    max_age: int,
    rng: random.Random,
    age_type: str = "founded",
) -> int:
    """Generate a random age within specified range.
    
    Args:
        min_age: Minimum age
        max_age: Maximum age
        rng: Random number generator
        age_type: Type of age being generated
        
    Returns:
        Random age in range
    """
    return rng.randint(min_age, max_age)


def get_safety_rating(
    base_safety: float,
    distance_penalty: float = 0.0,
    terrain_penalty: float = 0.0,
    min_safety: float = 0.1,
    max_safety: float = 1.0,
) -> float:
    """Calculate safety rating with various penalties.
    
    Args:
        base_safety: Base safety value
        distance_penalty: Penalty for distance
        terrain_penalty: Penalty for difficult terrain
        min_safety: Minimum allowed safety
        max_safety: Maximum allowed safety
        
    Returns:
        Calculated safety rating
    """
    safety = base_safety - distance_penalty - terrain_penalty
    return max(min_safety, min(max_safety, round(safety, 2)))
