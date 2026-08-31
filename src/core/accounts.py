"""
Accounts and identities

A person is an Account. How they arrive is an Identity: a web login, a
Telegram user, whatever comes next. Keeping the two apart is the whole
point — the same person joining from a group chat and from the browser
is one account with two identities, and adding a third platform costs a
row rather than a migration.

Accounts are not part of any world, so they live in PostgreSQL beside
the event log rather than in the world graph.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import jwt
from sqlalchemy import DateTime, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from config.settings import settings
from core.db import Base

logger = logging.getLogger(__name__)


class AccountModel(Base):
    """A person who plays or authors worlds."""

    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class IdentityModel(Base):
    """One way an account signs in.

    `provider` names the platform ("web", "telegram") and `subject` is
    that platform's id for the person. The pair is unique: one Telegram
    user is one identity, and it belongs to exactly one account.
    """

    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_identity"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class Account:
    """An authenticated caller, as the rest of the app sees them."""

    def __init__(self, id: UUID, display_name: str) -> None:
        self.id = id
        self.display_name = display_name


class AccountService:
    """Resolves who is calling, and hands out tokens saying so."""

    async def resolve_identity(
        self, provider: str, subject: str, display_name: Optional[str] = None
    ) -> Account:
        """Find the account behind a platform identity, creating it once.

        A first sign-in from a new Telegram user or browser makes the
        account; every later one finds it.
        """
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            found = await session.execute(
                select(IdentityModel).where(
                    IdentityModel.provider == provider,
                    IdentityModel.subject == subject,
                )
            )
            identity = found.scalar_one_or_none()

            if identity:
                account = (
                    await session.execute(
                        select(AccountModel).where(
                            AccountModel.id == identity.account_id
                        )
                    )
                ).scalar_one_or_none()
                if account:
                    return Account(account.id, account.display_name)
                # An identity whose account vanished is not something to
                # paper over silently.
                raise LookupError(
                    f"Identity {provider}:{subject} points at a missing account"
                )

            account_row = AccountModel(
                display_name=display_name or f"{provider}:{subject}"
            )
            session.add(account_row)
            await session.flush()
            session.add(
                IdentityModel(
                    account_id=account_row.id, provider=provider, subject=subject
                )
            )
            await session.commit()

            logger.info(
                f"Created account {account_row.id} for identity {provider}:{subject}"
            )
            return Account(account_row.id, account_row.display_name)

    async def link_identity(
        self, account_id: UUID, provider: str, subject: str
    ) -> None:
        """Attach another way of signing in to an existing account.

        This is what makes one person in a browser and in a group chat
        the same player rather than two.
        """
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            session.add(
                IdentityModel(
                    account_id=account_id, provider=provider, subject=subject
                )
            )
            await session.commit()
        logger.info(f"Linked {provider}:{subject} to account {account_id}")

    async def identities_for(self, account_id: UUID) -> List[Dict[str, str]]:
        """Every way this account can sign in."""
        from core.event_sourcing import event_store

        async with event_store.async_session() as session:
            rows = await session.execute(
                select(IdentityModel).where(IdentityModel.account_id == account_id)
            )
            return [
                {"provider": row.provider, "subject": row.subject}
                for row in rows.scalars().all()
            ]

    def issue_token(self, account: Account) -> str:
        """Mint a bearer token naming this account."""
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": str(account.id),
            "name": account.display_name,
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def read_token(self, token: str) -> Account:
        """Recover the account from a token, or raise if it does not hold up."""
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return Account(UUID(payload["sub"]), payload.get("name", ""))


account_service = AccountService()
