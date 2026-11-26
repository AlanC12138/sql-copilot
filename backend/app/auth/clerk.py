import logging
from typing import Annotated

# clerk-backend-api 7.x moved these out of `jwks_helpers` into `security`.
# The call shape is unchanged: verify_token(token, VerifyTokenOptions(...)).
from clerk_backend_api.security import VerifyTokenOptions, verify_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

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
        return verify_token(
            credentials.credentials,
            VerifyTokenOptions(secret_key=settings.clerk_secret_key),
        )
    except Exception as exc:
        # Logged as well as returned: the detail reaches the browser, but a
        # misconfiguration here (wrong key, unreachable JWKS) is indistinguishable
        # from a genuinely bad token unless the server records why.
        logger.warning("Clerk token verification failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


Claims = Annotated[dict, Depends(require_auth)]
