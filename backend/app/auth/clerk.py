from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)

_DEV_CLAIMS: dict = {
    "sub": "user_dev",
    "org_id": "org_dev",
    "org_slug": "dev-org",
}


def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    if settings.disable_auth:
        return _DEV_CLAIMS

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        from clerk_backend_api.jwks_helpers import TokenVerificationOptions, verify_token

        payload = verify_token(
            credentials.credentials,
            TokenVerificationOptions(secret_key=settings.clerk_secret_key),
        )
        return payload
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


Claims = Annotated[dict, Depends(require_auth)]
