"""
Authentication endpoints

Turning a platform identity into a token. How the identity is *proved*
depends on where the caller came from — an OAuth handshake in a browser,
the bot vouching for a Telegram user — and that part is not built yet.
What is built is everything after: one account behind many identities,
and a token that names it.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config.settings import settings
from api.auth import CurrentAccount
from core.accounts import Account, account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class DevTokenRequest(BaseModel):
    """Claim an identity without proving it. Development only."""

    provider: str = Field(..., examples=["web", "telegram"])
    subject: str = Field(..., description="The platform's id for this person")
    display_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: str
    display_name: str


class IdentityLinkRequest(BaseModel):
    """Attach another sign-in to an existing account."""

    account_id: str
    provider: str
    subject: str


@router.post("/dev-token", response_model=TokenResponse)
async def dev_token(request: DevTokenRequest) -> TokenResponse:
    """Mint a token for a claimed identity, for local development.

    This trusts the caller completely, so it exists only outside
    production. Real sign-in has to prove the identity first; this
    endpoint is the seam where that proof will go.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=404, detail="Not available in this environment"
        )

    account = await account_service.resolve_identity(
        provider=request.provider,
        subject=request.subject,
        display_name=request.display_name or None,
    )
    return TokenResponse(
        access_token=account_service.issue_token(account),
        account_id=str(account.id),
        display_name=account.display_name,
    )


@router.post("/identities")
async def link_identity(request: IdentityLinkRequest) -> Dict[str, Any]:
    """Link a second way of signing in to the same account.

    This is what makes one person in a browser and in a group chat the
    same player rather than two.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=404, detail="Not available in this environment"
        )

    await account_service.link_identity(
        account_id=UUID(request.account_id),
        provider=request.provider,
        subject=request.subject,
    )
    return {"linked": f"{request.provider}:{request.subject}"}


@router.get("/me")
async def whoami(account: Account = CurrentAccount) -> Dict[str, Any]:
    """Who the presented token says you are, and how you can sign in."""
    identities: List[Dict[str, str]] = await account_service.identities_for(account.id)
    return {
        "account_id": str(account.id),
        "display_name": account.display_name,
        "identities": identities,
    }
