from __future__ import annotations

"""Basic POI generator (MVP)

Creates simple points of interest near towns/villages: shrine, ruin, guard post, farm.
Kept minimal to avoid bloating the main pipeline.
"""

import random
from typing import Any, Dict, List, Tuple

from core.worldgen.utils import create_location_entity, link_to_parent
from core.world_service import world_service


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


async def generate_basic_poi(
    seed: str,
    settlements: List[Dict[str, Any]],
    per_settlement: int = 2,
) -> List[str]:
    rng = random.Random(f"poi:{seed}")
    created: List[str] = []
    poi_types = [
        ("shrine", ["religion", "pilgrimage"]),
        ("ruin", ["mystery", "danger"]),
        ("guard_post", ["patrol", "safety"]),
        ("farm", ["farming", "supply"]),
    ]

    for s in settlements:
        su, sv = s.get("center", (0.5, 0.5))
        for _ in range(per_settlement):
            kind, hooks = rng.choice(poi_types)
            du = _clamp01(su + (rng.random() - 0.5) * 0.06)
            dv = _clamp01(sv + (rng.random() - 0.5) * 0.06)
            # Create POI using utils
            metadata = {
                "poi_type": kind,
                "hook_tags": hooks,
            }
            
            # Safety rules for POI
            is_safe_value = None if kind not in ("ruin", "lair") else False
            
            created_p = await create_location_entity(
                name=f"{kind.title()} near {str(s['id'])[:6]}",
                description=f"A {kind.replace('_', ' ')}",
                location_kind="poi",
                parent_id=s["id"],
                center=[du, dv],
                metadata=metadata,
                actor_id=s["id"],  # Use settlement as actor
                is_safe=is_safe_value,
            )
            created.append(str(created_p.id))
            # Link to settlement using utils
            await link_to_parent(
                child_id=created_p.id,
                parent_id=s["id"],
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=created_p.id,
            )

    return created


