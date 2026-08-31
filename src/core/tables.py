"""
Worlds you own and tables you sit at

Two organisational facts that belong to no world and so live beside the
accounts in PostgreSQL:

- who may touch a world, and who authored it;
- who is at a table, and which character they play there.

A table is the unit of play. A browser room and a Telegram group are the
same thing seen from two sides, and both know only "this table" — so the
world, the party and the characters are all derived from it rather than
announced by the client.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.permissions import NotYours

logger = logging.getLogger(__name__)

OWNER = "owner"
PLAYER = "player"


class WorldMemberModel(Base):
    """An account's standing in a world."""

    __tablename__ = "world_members"
    __table_args__ = (UniqueConstraint("world_id", "account_id", name="uq_world_member"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    world_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=PLAYER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class GameSessionModel(Base):
    """A table: one group playing one world."""

    __tablename__ = "game_sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    world_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class SessionMemberModel(Base):
    """Someone at a table, and the character they play there."""

    __tablename__ = "session_members"
    __table_args__ = (
        UniqueConstraint("session_id", "account_id", name="uq_session_member"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    player_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class TableService:
    """Worlds, tables, and who is allowed at them."""

    # ---------------------------------------------------------------- #
    # Worlds
    # ---------------------------------------------------------------- #

    async def grant_world(
        self, world_id: UUID, account_id: UUID, role: str = OWNER
    ) -> None:
        """Record that an account may touch this world."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            existing = await session.execute(
                select(WorldMemberModel).where(
                    WorldMemberModel.world_id == world_id,
                    WorldMemberModel.account_id == account_id,
                )
            )
            if existing.scalar_one_or_none():
                return
            session.add(
                WorldMemberModel(
                    world_id=world_id, account_id=account_id, role=role
                )
            )
            await session.commit()
        logger.info(f"Account {account_id} is {role} of world {world_id}")

    async def world_role(self, world_id: UUID, account_id: UUID) -> Optional[str]:
        """This account's standing in this world, if any."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            row = await session.execute(
                select(WorldMemberModel).where(
                    WorldMemberModel.world_id == world_id,
                    WorldMemberModel.account_id == account_id,
                )
            )
            member = row.scalar_one_or_none()
            return member.role if member else None

    async def worlds_for(self, account_id: UUID) -> List[Dict[str, Any]]:
        """Every world this account owns or plays in."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            rows = await session.execute(
                select(WorldMemberModel).where(
                    WorldMemberModel.account_id == account_id
                )
            )
            return [
                {"world_id": str(m.world_id), "role": m.role}
                for m in rows.scalars().all()
            ]

    async def require_world_access(self, world_id: UUID, account_id: UUID) -> str:
        """The account's role, or a refusal."""
        role = await self.world_role(world_id, account_id)
        if not role:
            raise NotYours(f"No access to world {world_id}")
        return role

    # ---------------------------------------------------------------- #
    # Tables
    # ---------------------------------------------------------------- #

    async def create_session(
        self, world_id: UUID, name: str, account_id: UUID
    ) -> UUID:
        """Open a table in a world the account may touch."""
        await self.require_world_access(world_id, account_id)

        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            row = GameSessionModel(
                world_id=world_id, name=name, created_by=account_id
            )
            session.add(row)
            await session.flush()
            session.add(
                SessionMemberModel(session_id=row.id, account_id=account_id)
            )
            await session.commit()
            table_id: UUID = row.id

        logger.info(f"Opened table {table_id} in world {world_id}")
        return table_id

    async def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """The table itself: which world, who opened it, when."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as db:
            row = await db.execute(
                select(GameSessionModel).where(GameSessionModel.id == session_id)
            )
            table = row.scalar_one_or_none()
            if not table:
                return None
            return {
                "session_id": table.id,
                "world_id": table.world_id,
                "name": table.name,
                "created_by": table.created_by,
                "created_at": table.created_at,
            }

    async def join_session(
        self, session_id: UUID, account_id: UUID, player_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Take a seat, optionally naming the character you will play."""
        table = await self.get_session(session_id)
        if not table:
            raise LookupError(f"No table {session_id}")

        # Sitting down at a table in a world you were not part of makes you
        # a player in it — that is what an invitation means.
        await self.grant_world(table["world_id"], account_id, role=PLAYER)

        from core.event_sourcing import event_store

        async with event_store.async_session() as db:
            row = await db.execute(
                select(SessionMemberModel).where(
                    SessionMemberModel.session_id == session_id,
                    SessionMemberModel.account_id == account_id,
                )
            )
            member = row.scalar_one_or_none()
            if member:
                if player_id:
                    member.player_id = player_id
            else:
                db.add(
                    SessionMemberModel(
                        session_id=session_id,
                        account_id=account_id,
                        player_id=player_id,
                    )
                )
            await db.commit()

        logger.info(f"Account {account_id} joined table {session_id}")
        return {"session_id": str(session_id), "world_id": str(table["world_id"])}

    async def seat_at(
        self, session_id: UUID, account_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """This account's seat at this table, if they have one."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as db:
            row = await db.execute(
                select(SessionMemberModel).where(
                    SessionMemberModel.session_id == session_id,
                    SessionMemberModel.account_id == account_id,
                )
            )
            member = row.scalar_one_or_none()
            if not member:
                return None
            return {
                "account_id": member.account_id,
                "player_id": member.player_id,
            }

    async def members_of(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Everyone at the table. What a group chat needs to address them."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as db:
            rows = await db.execute(
                select(SessionMemberModel).where(
                    SessionMemberModel.session_id == session_id
                )
            )
            return [
                {
                    "account_id": str(m.account_id),
                    "player_id": str(m.player_id) if m.player_id else None,
                }
                for m in rows.scalars().all()
            ]

    async def sessions_for(self, account_id: UUID) -> List[Dict[str, Any]]:
        """Every table this account sits at."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as db:
            seats = await db.execute(
                select(SessionMemberModel).where(
                    SessionMemberModel.account_id == account_id
                )
            )
            ids = [m.session_id for m in seats.scalars().all()]
            if not ids:
                return []
            rows = await db.execute(
                select(GameSessionModel).where(GameSessionModel.id.in_(ids))
            )
            return [
                {
                    "session_id": str(t.id),
                    "world_id": str(t.world_id),
                    "name": t.name,
                }
                for t in rows.scalars().all()
            ]


table_service = TableService()
