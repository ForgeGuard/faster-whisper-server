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

    # Compare as bytes: compare_digest rejects non-ASCII str inputs with a
    # TypeError (a 500), and utf-8 handles non-ASCII on both sides.
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode("utf-8"), config.API_KEY.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
