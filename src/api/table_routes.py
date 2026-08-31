"""
Worlds and tables

Creating a world, opening a table in it, and taking a seat. A table is
what a client actually holds on to: a browser room or a Telegram group
knows only "this table", and the world and the party follow from it.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth import CurrentAccount
from core.accounts import Account
from core.permissions import NotYours
from core.tables import OWNER, table_service
from core.world_service import world_service
from domain.entities import Location

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Worlds and tables"])


class WorldCreateRequest(BaseModel):
    name: str
    description: str = ""


class SessionCreateRequest(BaseModel):
    world_id: UUID
    name: str = "Table"


class SessionJoinRequest(BaseModel):
    player_id: Optional[UUID] = None


@router.post("/worlds")
async def create_world(
    request: WorldCreateRequest, account: Account = CurrentAccount
) -> Dict[str, Any]:
    """Create an empty world. The caller owns it."""
    world = await world_service.create_entity(
        entity=Location(name=request.name, description=request.description),
        actor_id=account.id,
    )
    # A world belongs to itself, so that everything generated inside it
    # can be stamped with the same id.
    world.world_id = world.id
    await world_service.update_entity(entity=world, actor_id=account.id)

    await table_service.grant_world(world.id, account.id, role=OWNER)
    return {"world_id": str(world.id), "name": world.name, "role": OWNER}


@router.get("/worlds")
async def my_worlds(account: Account = CurrentAccount) -> List[Dict[str, Any]]:
    """Worlds this account owns or plays in."""
    return await table_service.worlds_for(account.id)


@router.post("/sessions")
async def create_session(
    request: SessionCreateRequest, account: Account = CurrentAccount
) -> Dict[str, Any]:
    """Open a table in a world you may touch."""
    try:
        session_id = await table_service.create_session(
            world_id=request.world_id, name=request.name, account_id=account.id
        )
    except NotYours as e:
        raise HTTPException(status_code=403, detail=str(e))

    return {
        "session_id": str(session_id),
        "world_id": str(request.world_id),
        "name": request.name,
    }


@router.get("/sessions")
async def my_sessions(account: Account = CurrentAccount) -> List[Dict[str, Any]]:
    """Tables this account sits at."""
    return await table_service.sessions_for(account.id)


@router.post("/sessions/{session_id}/join")
async def join_session(
    session_id: UUID,
    request: SessionJoinRequest,
    account: Account = CurrentAccount,
) -> Dict[str, Any]:
    """Take a seat, naming the character you will play."""
    try:
        return await table_service.join_session(
            session_id=session_id,
            account_id=account.id,
            player_id=request.player_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{session_id}/members")
async def session_members(
    session_id: UUID, account: Account = CurrentAccount
) -> List[Dict[str, Any]]:
    """Everyone at the table — what a group chat needs to address them."""
    if not await table_service.seat_at(session_id, account.id):
        raise HTTPException(status_code=403, detail="You are not at this table")
    return await table_service.members_of(session_id)
