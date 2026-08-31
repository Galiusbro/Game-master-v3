from __future__ import annotations

"""Constants for world generation

Defines common constants, thresholds, and configuration values
used across world generation modules.
"""

from typing import Any, Dict, List, Tuple

# Default race weights for generic world NPC generation (approximate DnD distribution)
RACE_WEIGHTS: Dict[str, float] = {
    "human": 0.45,
    "elf": 0.12,
    "dwarf": 0.1,
    "halfling": 0.08,
    "gnome": 0.07,
    "half_orc": 0.06,
    "half_elf": 0.06,
    "tiefling": 0.04,
    "dragonborn": 0.02,
}

# World scale constants
WORLD_SCALE_KM = 10000.0  # World is ~10,000 km across
WORLD_AREA_KM2 = WORLD_SCALE_KM * WORLD_SCALE_KM  # 100M km²

# Geographic thresholds (in km²)
CONTINENT_THRESHOLDS = {
    "supercontinent": 30_000_000,
    "large_continent": 15_000_000,
    "continent": 5_000_000,
    "subcontinent": 1_000_000,
}

SEA_THRESHOLDS = {
    "ocean": 50_000_000,
    "large_sea": 10_000_000,
    "sea": 1_000_000,
    "gulf": 100_000,
}

# Biome characteristics
BIOME_CHARACTERISTICS = {
    "coastal": {
        "fertility": 0.7,
        "habitability": 0.8,
        "resource_abundance": 0.6,
        "typical_resources": ["fish", "salt", "pearls"],
        "climate": "temperate",
        "terrain_difficulty": 0.2,
    },
    "plains": {
        "fertility": 0.9,
        "habitability": 0.9,
        "resource_abundance": 0.7,
        "typical_resources": ["grain", "livestock", "textiles"],
        "climate": "temperate",
        "terrain_difficulty": 0.1,
    },
    "forest": {
        "fertility": 0.6,
        "habitability": 0.7,
        "resource_abundance": 0.8,
        "typical_resources": ["timber", "herbs", "game"],
        "climate": "temperate",
        "terrain_difficulty": 0.4,
    },
    "mountains": {
        "fertility": 0.3,
        "habitability": 0.5,
        "resource_abundance": 0.9,
        "typical_resources": ["metals", "gems", "stone"],
        "climate": "cold",
        "terrain_difficulty": 0.8,
    },
}

# Trade specializations by biome
TRADE_SPECIALIZATIONS = {
    "coastal": ["fishing", "salt", "trade_hub", "shipbuilding"],
    "mountains": ["mining", "metalwork", "gems", "stone"],
    "forest": ["lumber", "hunting", "herbs", "crafts"],
    "plains": ["agriculture", "livestock", "textiles", "grain"],
}

# Road terrain types by biome
ROAD_TERRAINS = {
    "coastal": ["coastal", "sandy", "mixed"],
    "mountains": ["mountain", "rocky", "winding"],
    "forest": ["forest", "wooded", "muddy"],
    "plains": ["plains", "paved", "dirt"],
}

# Population estimates
POPULATION_RANGES: Dict[str, Any] = {
    "capital": (20_000, 80_000),
    "town_base": 2_000,
    "town_variation": 8_000,
    "village_base": 100,
    "village_variation": 400,
}

# Population multipliers by biome
POPULATION_MULTIPLIERS = {
    "coastal": 1.5,
    "plains": 1.2,
    "forest": 1.0,
    "mountains": 0.75,
}

# Settlement generation ranges
SETTLEMENT_RANGES: Dict[str, Any] = {
    "max_continents": 3,
    "max_seas": 5,
    "regions_per_continent": (3, 7),
    "towns_per_continent": (3, 6),
    "rivers_per_continent": (1, 3),
    "villages_per_region": 2,
    "poi_per_settlement": 2,
}

# Age ranges for different entity types
AGE_RANGES: Dict[str, Any] = {
    "capital": (200, 800),
    "town": (50, 400),
    "village": (20, 200),
    "ancient_ruin": (500, 2000),
}

# Safety and danger ratings
SAFETY_RANGES = {
    "base_road_safety": 0.6,
    "mountain_road_penalty": 0.2,
    "coastal_road_bonus": 0.1,
    "max_distance_penalty": 0.2,
    "min_safety": 0.1,
    "max_safety": 1.0,
}

# Depth categories for water bodies
DEPTH_CATEGORIES = {
    "ocean": "abyssal",
    "large_sea": "deep",
    "sea": "moderate",
    "gulf": "moderate",
    "bay": "shallow",
}

# Relationship types
RELATIONSHIP_TYPES = {
    "location": "LOCATED_IN",
    "connection": "CONNECTS_TO",
    "trade": "TRADES_WITH",
    "governance": "GOVERNED_BY",
}

# Common entity metadata keys
METADATA_KEYS = {
    "location_kind": "location_kind",
    "parent_id": "parent_id",
    "center": "center",
    "population": "population_estimate",
    "founded_age": "founded_age",
    "biome": "biome_type",
    "elevation": "elevation",
    "safety": "safety",
    "terrain_difficulty": "terrain_difficulty",
}
