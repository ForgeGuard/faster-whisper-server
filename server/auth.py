"""Optional Bearer-token authentication.

When ``API_KEY`` is unset the dependency is a no-op, so the server stays open by
default. When set, protected endpoints require ``Authorization: Bearer <key>``
(the OpenAI client convention). Comparison is constant-time.
"""

import secrets
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server import config

auth_scheme = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme),
) -> None:
    if config.API_KEY is None:
        return

    if credentials is None or not secrets.compare_digest(
        credentials.credentials, config.API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
