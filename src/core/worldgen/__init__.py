"""
World generation scaffolding (MVP)

This package contains the high-level pipeline and modular generators for:
- macro geography (heightmap, water, rivers)
- climate and biomes
- regional segmentation
- settlements & roads (to be added next)
- persistence into the game's graph and vector indexes

All functions are lightweight stubs or simple implementations suitable for
incremental build-out.
"""

from .pipeline import generate_world  # re-export high-level entrypoint

# Optional helpers (kept separate to avoid pipeline bloat)
from .villages import generate_basic_villages
from .poi import generate_basic_poi
from .city_builder import build_minimal_city_structure
from .geo_engine import (
    generate_fractal_noise,
    derive_water_mask,
    label_connected_components,
    center_of_mask,
    find_coastline_pixels,
)
from .river_system import generate_all_rivers
from .settlement_planner import generate_settlements_and_roads
from .region_generator import generate_all_regions
from .continent_sea_generator import generate_continents_and_seas
from .politics import generate_countries_and_laws
from .npc_generator import generate_basic_npcs
from .bosses import generate_bosses
from .encounters import attach_region_encounters

# Utility modules for common functionality
from .utils import (
    create_location_entity,
    link_to_parent,
    normalize_coordinates,
    calculate_distance_km,
)
from .classifiers import (
    classify_continent_type,
    classify_sea_type,
    classify_biome,
    get_biome_characteristics,
)
from .constants import (
    BIOME_CHARACTERISTICS,
    POPULATION_RANGES,
    SETTLEMENT_RANGES,
)

__all__ = [
    # Core pipeline
    "generate_world",
    
    # Generation modules
    "generate_basic_villages",
    "generate_basic_poi",
    "build_minimal_city_structure",
    "generate_all_rivers",
    "generate_settlements_and_roads",
    "generate_all_regions",
    "generate_continents_and_seas",
    "generate_countries_and_laws",
    "generate_basic_npcs",
    "generate_bosses",
    "attach_region_encounters",
    
    # Geographic engines
    "generate_fractal_noise",
    "derive_water_mask",
    "label_connected_components",
    "center_of_mask",
    "find_coastline_pixels",
    
    # Utilities
    "create_location_entity",
    "link_to_parent",
    "normalize_coordinates",
    "calculate_distance_km",
    
    # Classifiers
    "classify_continent_type",
    "classify_sea_type",
    "classify_biome",
    "get_biome_characteristics",
    
    # Constants
    "BIOME_CHARACTERISTICS",
    "POPULATION_RANGES",
    "SETTLEMENT_RANGES",
]


