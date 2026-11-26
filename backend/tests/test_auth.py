"""Clerk token verification.

These exist because the real verification branch shipped broken and nothing
caught it: local development runs with DISABLE_AUTH=true, which returns dev
claims before reaching the Clerk call, so the code below had never executed
once until it was deployed. It imported `TokenVerificationOptions`, a name the
SDK does not have — and because the import sat inside the try/except, the
ImportError surfaced as a plain 401, indistinguishable from a bad token.
"""
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import clerk


def test_sdk_exposes_the_options_class_we_import():
    # Guards the exact failure above: if the SDK renames this, fail here with a
    # clear message rather than as a 401 in production.
    # 7.x moved these from `jwks_helpers` to `security`; this test is what
    # caught that rename during the upgrade, which is the point of it.
    from clerk_backend_api.security import VerifyTokenOptions, verify_token

    assert clerk.VerifyTokenOptions is VerifyTokenOptions
    assert clerk.verify_token is verify_token


def test_dev_claims_returned_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(clerk.settings, "disable_auth", True)
    assert clerk.require_auth(None) == clerk._DEV_CLAIMS


def test_missing_bearer_token_is_rejected(monkeypatch):
    monkeypatch.setattr(clerk.settings, "disable_auth", False)
    with pytest.raises(HTTPException) as exc:
        clerk.require_auth(None)
    assert exc.value.status_code == 401


def test_malformed_token_reaches_real_verification(monkeypatch):
    """A garbage token must fail *verification*, not import or attribute lookup.

    If this raises anything other than a 401 whose detail looks like a JWT
    complaint, the Clerk call is broken rather than the token.
    """
    monkeypatch.setattr(clerk.settings, "disable_auth", False)
    monkeypatch.setattr(clerk.settings, "clerk_secret_key", "sk_test_not_a_real_key")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.jwt")

    with pytest.raises(HTTPException) as exc:
        clerk.require_auth(creds)

    assert exc.value.status_code == 401
    detail = str(exc.value.detail).lower()
    assert "import" not in detail, f"verification never ran: {exc.value.detail}"
    assert "attribute" not in detail, f"verification never ran: {exc.value.detail}"
