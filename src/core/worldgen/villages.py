from __future__ import annotations

"""Basic villages generator (MVP)

Keeps logic small and separate from the main pipeline to avoid bloat.
Generates a couple of villages per region with simple farming-oriented metadata.
"""

import random
from typing import Any, Dict, List, Tuple

from core.worldgen.utils import create_location_entity, link_to_parent
from core.worldgen.constants import POPULATION_RANGES


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


async def generate_basic_villages(
    seed: str,
    regions_by_continent: Dict[Any, List[Dict[str, Any]]],
    per_region: int = 2,
) -> List[Dict[str, Any]]:
    """Create small villages around region centers.

    Args:
        seed: RNG seed for determinism
        regions_by_continent: mapping continent_id -> list of regions
        per_region: maximum villages per region (MVP small)

    Returns:
        List of created village IDs as strings
    """
    rng = random.Random(f"villages:{seed}")
    created_settlements: List[Dict[str, Any]] = []

    for _, regions in regions_by_continent.items():
        for reg in regions:
            # generate up to per_region villages per region
            ru, rv = reg.get("center", (0.5, 0.5))
            for _ in range(per_region):
                du = _clamp01(ru + (rng.random() - 0.5) * 0.03)
                dv = _clamp01(rv + (rng.random() - 0.5) * 0.03)
                # Create village using utils
                base_pop = POPULATION_RANGES["village_base"]
                variation = POPULATION_RANGES["village_variation"]
                
                metadata = {
                    "population_estimate": rng.randint(base_pop, base_pop + variation),
                    "economy_tags": rng.sample(
                        ["farming", "pasture", "orchard", "fish"], k=2
                    ),
                    "has_walls": False,
                }
                
                created = await create_location_entity(
                    name=f"Village {str(reg['id'])[:6]}-{rng.randint(100,999)}",
                    description="A small farming village",
                    location_kind="village",
                    parent_id=reg["id"],
                    center=[du, dv],
                    metadata=metadata,
                    actor_id=reg["id"],  # Use region as actor
                )
                created_settlements.append({
                    "id": created.id,
                    "center": [du, dv],
                })
                # Link to region using utils
                await link_to_parent(
                    child_id=created.id,
                    parent_id=reg["id"],
                    relationship_type="LOCATED_IN",
                    properties=None,
                    actor_id=created.id,
                )

    return created_settlements


