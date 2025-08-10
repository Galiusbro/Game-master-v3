from __future__ import annotations

"""NPC generation (Stage 7 - minimal seed)

Creates a minimal set of NPCs tied to essential buildings:
- inn → innkeeper (vendor/social)
- healer/temple → healer (service/social)
- blacksmith → blacksmith (vendor/crafting)
- guardhouse → guard captain (authority/combat)

Keeps relationships consistent:
- LOCATED_IN NPC → Building
"""

import random
from typing import Any, Dict, List, Optional
from uuid import UUID

from core.world_service import world_service
from domain.entities import BaseEntity, EntityType, NPC, NPCState, NPCPersonality, Race
from core.worldgen.constants import RACE_WEIGHTS


def _npc_meta_for_building(kind: str) -> Optional[Dict[str, Any]]:
    kind = (kind or "").lower()
    if kind == "inn":
        return {
            "roles": ["innkeeper", "vendor"],
            "capabilities": {
                "trade_capability": {"domains": ["food", "lodging"]},
                "social_capability": {"smalltalk": True},
            },
        }
    if kind == "healer":
        return {
            "roles": ["healer", "service"],
            "capabilities": {
                "service_capability": {"kind": "healing"},
                "knowledge_capability": {"medicine": True},
            },
        }
    if kind == "blacksmith":
        return {
            "roles": ["blacksmith", "vendor", "craftsman"],
            "capabilities": {
                "trade_capability": {"domains": ["weapons", "tools"]},
                "crafting_capability": {"metalwork": True},
            },
        }
    if kind == "guardhouse":
        return {
            "roles": ["guard_captain", "authority"],
            "capabilities": {
                "authority_capability": {"arrest": True},
                "combat_capability": {"trained": True},
            },
        }
    return None


async def generate_basic_npcs(
    seed: str,
    building_ids: List[str],
    world_actor_id: Any,
) -> List[str]:
    rng = random.Random(f"npc:{seed}")
    created_npc_ids: List[str] = []

    for bid in building_ids:
        try:
            building = await world_service.get_entity(UUID(str(bid)))
            if not building or building.type != EntityType.LOCATION:
                continue
            bmeta = building.metadata or {}
            bkind = (bmeta.get("kind") or bmeta.get("business_profile", {}).get("shop_kind") or "").lower()
            npc_meta = _npc_meta_for_building(bkind)
            if npc_meta is None:
                continue

            # Prepare NPC entity
            personality = NPCPersonality(core_traits=["neutral"], speech_patterns=["plain"])
            state = NPCState(current_mood="neutral")
            state.current_location_id = UUID(str(building.id))

            role_name = npc_meta["roles"][0].replace("_", " ").title()
            npc_name = f"{role_name} of {building.name}"
            # Pick race with weighted distribution
            try:
                race_choices = list(RACE_WEIGHTS.keys())
                race_weights = list(RACE_WEIGHTS.values())
                chosen_race = rng.choices(race_choices, weights=race_weights, k=1)[0]
                race_enum = Race(chosen_race)
            except Exception:
                race_enum = Race.HUMAN

            npc = NPC(
                name=npc_name,
                description=f"{role_name} working at {building.name}",
                race=race_enum,
                personality=personality,
                current_state=state,
                metadata={
                    "roles": npc_meta["roles"],
                    "capabilities": npc_meta["capabilities"],
                    "home_building_id": str(building.id),
                },
            )

            created = await world_service.create_entity(entity=npc, actor_id=world_actor_id)
            created_npc_ids.append(str(created.id))

            # Link NPC to building
            await world_service.create_relationship(
                from_entity_id=created.id,
                to_entity_id=building.id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=world_actor_id,
            )

        except Exception:
            # Skip problematic building and continue
            continue

    return created_npc_ids


def _citizen_roles_for_district(kind: str, rng: random.Random) -> List[str]:
    kind = (kind or "").lower()
    if kind == "market":
        base = ["vendor", "trader", "porter", "shop_assistant"]
    elif kind == "temple":
        base = ["acolyte", "pilgrim"]
    elif kind == "docks":
        base = ["sailor", "dock_worker"]
    elif kind == "noble":
        base = ["servant", "scribe"]
    elif kind == "crafts":
        base = ["artisan", "apprentice"]
    else:
        base = ["townsfolk"]
    k = 2 if len(base) >= 2 else 1
    return rng.sample(base, k=k)


async def generate_citizens_for_districts(
    seed: str,
    district_ids: List[str],
    world_actor_id: Any,
    per_district: int = 3,
) -> List[str]:
    rng = random.Random(f"citizens:{seed}")
    created: List[str] = []

    from uuid import UUID
    from domain.entities import EntityType

    for did in district_ids:
        try:
            district = await world_service.get_entity(UUID(str(did)))
            if not district or district.type != EntityType.LOCATION:
                continue
            dmeta = district.metadata or {}
            kind = (dmeta.get("kind") or "").lower()
            parent_city_id = dmeta.get("parent_id")

            is_capital = False
            if parent_city_id:
                city = await world_service.get_entity(UUID(str(parent_city_id)))
                if city and (city.metadata or {}).get("is_capital"):
                    is_capital = True

            # Optionally guarantee a noble in capital noble district
            extra_roles: List[str] = []
            if is_capital and kind == "noble":
                extra_roles.append("noble")

            # Create citizens
            for idx in range(per_district):
                roles = _citizen_roles_for_district(kind, rng)
                roles = roles + ([] if idx > 0 else extra_roles)
                role_name = roles[0] if roles else "citizen"

                personality = NPCPersonality(core_traits=["neutral"], speech_patterns=["plain"])
                state = NPCState(current_mood="neutral")
                state.current_location_id = UUID(str(district.id))

                npc = NPC(
                    name=f"{role_name.title()} of {district.name}",
                    description=f"A {role_name} in the {kind} district",
                    race=(
                        Race(rng.choices(list(RACE_WEIGHTS.keys()), weights=list(RACE_WEIGHTS.values()), k=1)[0])
                        if True else Race.HUMAN
                    ),
                    personality=personality,
                    current_state=state,
                    metadata={
                        "roles": list(set([role_name] + roles)),
                        "capabilities": {"social_capability": {"smalltalk": True}},
                        "home_district_id": str(district.id),
                    },
                )

                created_npc = await world_service.create_entity(entity=npc, actor_id=world_actor_id)
                created.append(str(created_npc.id))

                await world_service.create_relationship(
                    from_entity_id=created_npc.id,
                    to_entity_id=district.id,
                    relationship_type="LOCATED_IN",
                    properties=None,
                    actor_id=world_actor_id,
                )

        except Exception:
            continue

    return created


async def generate_rare_specialists(
    seed: str,
    district_ids: List[str],
    world_actor_id: Any,
) -> List[str]:
    """Create rare specialists in capital districts.

    Mapping:
    - market → jeweler (trade)
    - crafts → alchemist (service/crafting)
    - temple/noble → scribe (service/knowledge)
    """
    rng = random.Random(f"specialists:{seed}")
    created: List[str] = []

    from uuid import UUID

    role_by_district = {
        "market": "jeweler",
        "crafts": "alchemist",
        "temple": "scribe",
        "noble": "scribe",
    }

    for did in district_ids:
        try:
            district = await world_service.get_entity(UUID(str(did)))
            if not district or district.type != EntityType.LOCATION:
                continue
            dmeta = district.metadata or {}
            kind = (dmeta.get("kind") or "").lower()
            parent_city_id = dmeta.get("parent_id")
            if not parent_city_id:
                continue
            city = await world_service.get_entity(UUID(str(parent_city_id)))
            if not city or (city.metadata or {}).get("is_capital") is not True:
                continue

            role = role_by_district.get(kind)
            if not role:
                continue

            personality = NPCPersonality(core_traits=["professional"], speech_patterns=["formal"]) 
            state = NPCState(current_mood="busy")
            state.current_location_id = UUID(str(district.id))

            capabilities: Dict[str, Any] = {"social_capability": {"smalltalk": False}}
            if role == "jeweler":
                capabilities.update({"trade_capability": {"domains": ["gems", "jewelry"]}})
            elif role == "alchemist":
                capabilities.update({
                    "service_capability": {"kind": "alchemy"},
                    "crafting_capability": {"alchemy": True},
                })
            elif role == "scribe":
                capabilities.update({
                    "service_capability": {"kind": "scribe"},
                    "knowledge_capability": {"lore": True},
                })

            npc = NPC(
                name=f"{role.title()} of {district.name}",
                description=f"A renowned {role} serving the capital",
                race=(
                    Race(rng.choices(list(RACE_WEIGHTS.keys()), weights=list(RACE_WEIGHTS.values()), k=1)[0])
                ),
                personality=personality,
                current_state=state,
                metadata={
                    "roles": [role, "specialist"],
                    "capabilities": capabilities,
                    "home_district_id": str(district.id),
                },
            )

            created_npc = await world_service.create_entity(entity=npc, actor_id=world_actor_id)
            created.append(str(created_npc.id))

            await world_service.create_relationship(
                from_entity_id=created_npc.id,
                to_entity_id=district.id,
                relationship_type="LOCATED_IN",
                properties=None,
                actor_id=world_actor_id,
            )
        except Exception:
            continue

    return created


