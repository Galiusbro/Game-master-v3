"""
Who is calling

A bearer token names an account. Everything downstream asks the account,
never the request body — a client saying "I am player X" is a claim, not
a fact.
"""

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request

from core.accounts import Account, account_service

logger = logging.getLogger(__name__)


def _bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


async def current_account(request: Request) -> Account:
    """The authenticated caller, or 401."""
    token = _bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return account_service.read_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.info(f"Rejected token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def optional_account(request: Request) -> Optional[Account]:
    """The caller if they presented a valid token, otherwise nobody.

    For endpoints that are not yet behind authentication.
    """
    if not _bearer_token(request):
        return None
    try:
        return await current_account(request)
    except HTTPException:
        return None


CurrentAccount = Depends(current_account)
