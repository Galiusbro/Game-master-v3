from __future__ import annotations

"""City builder (MVP)

Extracted minimal city structure generation to keep the main pipeline lean.
Creates a few districts, streets, and essential buildings (inn, healer/temple,
blacksmith, guardhouse, plus houses) based on whether the city is a capital.
"""

import random
from typing import Any, Dict, List, Tuple

from core.worldgen.utils import create_location_entity, link_to_parent


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


async def build_minimal_city_structure(
    seed: str,
    city_id: Any,
    center: Tuple[float, float],
    is_capital: bool,
) -> Dict[str, List[str]]:
    rng = random.Random(f"city:{seed}:{city_id}")
    created: Dict[str, List[str]] = {"districts": [], "streets": [], "buildings": []}

    cx, cy = center
    base_types = ["market", "common", "temple"]
    extra = ["docks", "noble", "crafts"] if is_capital else ["crafts"]
    types = base_types + (rng.sample(extra, k=min(len(extra), 2)) if extra else [])

    have_inn = False
    have_healer = False
    have_smith = False
    have_guard = False

    for idx, kind in enumerate(types, start=1):
        du = (rng.random() - 0.5) * 0.05
        dv = (rng.random() - 0.5) * 0.05
        du = _clamp01(cx + du)
        dv = _clamp01(cy + dv)
        # Create district using utils
        metadata = {
            "kind": kind,
            "density": round(0.5 + rng.random() * 0.4, 2),
        }
        
        created_d = await create_location_entity(
            name=f"{kind.title()} District",
            description=f"The {kind} quarter of the city",
            location_kind="district",
            parent_id=city_id,
            center=[du, dv],
            metadata=metadata,
            actor_id=city_id,
        )
        created["districts"].append(str(created_d.id))
        # Link district to city using utils
        await link_to_parent(
            child_id=created_d.id,
            parent_id=city_id,
            relationship_type="LOCATED_IN",
            properties=None,
            actor_id=created_d.id,
        )

        # Streets per district (2-4)
        street_count = 3 if is_capital else 2
        for sidx in range(street_count):
            su = _clamp01(du + (rng.random() - 0.5) * 0.02)
            sv = _clamp01(dv + (rng.random() - 0.5) * 0.02)
            # Create street using utils
            metadata = {
                "district_id": str(created_d.id),
                "traffic_level": round(0.3 + rng.random() * 0.6, 2),
            }
            
            created_s = await create_location_entity(
                name=f"{kind.title()} St. {sidx+1}",
                description=f"A street in the {kind} district",
                location_kind="street",
                parent_id=city_id,
                center=[su, sv],
                metadata=metadata,
                actor_id=city_id,
            )
            created["streets"].append(str(created_s.id))
            # Link street to district using utils
            await link_to_parent(
                child_id=created_s.id,
                parent_id=created_d.id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=created_s.id,
            )

        # Essential buildings by district kind
        bdefs: List[Tuple[str, Dict[str, Any]]] = []
        if kind in ("market", "common", "crafts"):
            if not have_inn:
                bdefs.append(("inn", {"shop_kind": "inn"}))
                have_inn = True
            if kind == "crafts" and not have_smith:
                bdefs.append(("blacksmith", {"shop_kind": "blacksmith"}))
                have_smith = True
        if kind in ("temple",) and not have_healer:
            bdefs.append(("healer", {"service": "healing"}))
            have_healer = True
        if kind in ("noble", "market") and not have_guard:
            bdefs.append(("guardhouse", {"service": "law"}))
            have_guard = True

        # Add a couple of houses always
        house_count = 2 if is_capital else 1
        for _ in range(house_count):
            bdefs.append(("house", {}))

        for bkind, meta in bdefs:
            bu = _clamp01(du + (rng.random() - 0.5) * 0.01)
            bv = _clamp01(dv + (rng.random() - 0.5) * 0.01)
            
            # Prepare building metadata
            building_meta: Dict[str, Any] = {"kind": bkind}
            if "shop_kind" in meta:
                building_meta["business_profile"] = {"shop_kind": meta["shop_kind"]}
            if "service" in meta:
                building_meta["service_capability"] = {"kind": meta["service"]}

            # Create building using utils  
            created_b = await create_location_entity(
                name=f"{bkind.title()} {kind.title()} {idx}",
                description=f"A {bkind} in the {kind} district",
                location_kind="building",
                parent_id=created_d.id,
                center=[bu, bv],
                metadata=building_meta,
                actor_id=created_d.id,
            )
            created["buildings"].append(str(created_b.id))
            # Link building to district using utils
            await link_to_parent(
                child_id=created_b.id,
                parent_id=created_d.id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=created_b.id,
            )

    return created
