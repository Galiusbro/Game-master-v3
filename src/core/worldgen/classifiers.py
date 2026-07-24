from __future__ import annotations

"""Classification systems for world generation

Provides unified classification functions for:
- Geographic features (continents, seas)
- Biomes and climate zones
- Settlement types and characteristics
"""

import random
from typing import Any, Dict

from .constants import (
    BIOME_CHARACTERISTICS,
    CONTINENT_THRESHOLDS,
    DEPTH_CATEGORIES,
    SEA_THRESHOLDS,
    TRADE_SPECIALIZATIONS,
    ROAD_TERRAINS,
)


def classify_continent_type(properties: Dict[str, Any]) -> str:
    """Classify continent type based on its properties.
    
    Args:
        properties: Geographic properties dict with 'area_km2' and 'compactness'
        
    Returns:
        Continent type classification
    """
    area = properties["area_km2"]
    compactness = properties.get("compactness", 0.5)
    
    # Check area-based classifications first
    for continent_type, threshold in CONTINENT_THRESHOLDS.items():
        if area > threshold:
            return continent_type
    
    # Special cases based on shape
    if compactness < 0.3:
        return "archipelago"
    else:
        return "large_island"


def classify_sea_type(properties: Dict[str, Any]) -> str:
    """Classify sea/ocean type based on its properties.
    
    Args:
        properties: Geographic properties dict with 'area_km2'
        
    Returns:
        Sea type classification
    """
    area = properties["area_km2"]
    
    # Check area-based classifications
    for sea_type, threshold in SEA_THRESHOLDS.items():
        if area > threshold:
            return sea_type
    
    return "bay"  # Smallest category


def classify_biome(elevation: float, sea_level: float, distance_to_water: float = 0.0) -> str:
    """Classify biome based on elevation and other factors.
    
    Args:
        elevation: Height value (0.0 to 1.0)
        sea_level: Sea level threshold
        distance_to_water: Distance to nearest water body (optional)
        
    Returns:
        Biome type string
    """
    # Coastal regions (close to sea level)
    if elevation < sea_level + 0.05:
        return "coastal"
    
    # Plains (slightly above sea level)
    if elevation < sea_level + 0.2:
        return "plains"
    
    # Forest (mid elevations)
    if elevation < 0.7:
        return "forest"
    
    # Mountains (high elevations)
    return "mountains"


def get_biome_characteristics(biome: str) -> Dict[str, Any]:
    """Get characteristic properties for a biome type.
    
    Args:
        biome: Biome type string
        
    Returns:
        Dict with biome characteristics
    """
    return BIOME_CHARACTERISTICS.get(biome, BIOME_CHARACTERISTICS["plains"])


def get_trade_specialization(biome: str, rng: random.Random) -> str:
    """Get trade specialization based on biome.
    
    Args:
        biome: Biome type string
        rng: Random number generator
        
    Returns:
        Trade specialization string
    """
    options = TRADE_SPECIALIZATIONS.get(biome, ["general_trade"])
    return rng.choice(options)


def get_road_terrain(biome: str, rng: random.Random) -> str:
    """Determine road terrain based on biome.
    
    Args:
        biome: Biome type string
        rng: Random number generator
        
    Returns:
        Road terrain type string
    """
    options = ROAD_TERRAINS.get(biome, ["mixed"])
    return rng.choice(options)


def get_depth_category(sea_type: str) -> str:
    """Get depth category based on sea type.
    
    Args:
        sea_type: Sea type classification
        
    Returns:
        Depth category string
    """
    return DEPTH_CATEGORIES.get(sea_type, "moderate")


def estimate_climate_zones(area_km2: int) -> int:
    """Estimate number of climate zones based on landmass size.
    
    Args:
        area_km2: Area in square kilometers
        
    Returns:
        Number of climate zones
    """
    if area_km2 > 20_000_000:
        return 5  # Very large continent
    elif area_km2 > 10_000_000:
        return 4  # Large continent
    elif area_km2 > 5_000_000:
        return 3  # Medium continent
    elif area_km2 > 1_000_000:
        return 2  # Small continent
    else:
        return 1  # Island/small landmass


def calculate_region_count(continent_size: int, grid_size: int, base_regions: tuple[int, int] = (3, 7)) -> int:
    """Calculate appropriate number of regions for a continent.
    
    Args:
        continent_size: Number of pixels in continent
        grid_size: Total grid size
        base_regions: (min, max) regions per continent
        
    Returns:
        Number of regions to create
    """
    min_regions, max_regions = base_regions
    
    # Scale based on continent size relative to total world
    size_factor = continent_size / max(1, (grid_size ** 2) // 20000)
    target_regions = max(min_regions, min(max_regions, int(size_factor)))
    
    return target_regions
