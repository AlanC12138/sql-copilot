import stripe
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.clerk import Claims
from app.billing.stripe_client import (
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
    get_or_create_customer,
)
from app.billing.usage import get_monthly_usage
from app.config import settings
from app.db.app_engine import get_app_engine
from app.models.org import get_or_create_org
from app.models.tables import organizations

router = APIRouter(prefix="/billing", tags=["billing"])


class BillingStatus(BaseModel):
    tier: str
    subscription_status: str | None
    usage_this_month: int
    monthly_limit: int | None


class CheckoutOut(BaseModel):
    url: str


def _require_org_id(claims: dict) -> str:
    clerk_org_id = claims.get("org_id")
    if not clerk_org_id:
        raise HTTPException(status_code=400, detail="No active organization in session")
    return clerk_org_id


@router.get("/status", response_model=BillingStatus)
def billing_status(claims: Claims):
    clerk_org_id = _require_org_id(claims)
    engine = get_app_engine()

    with engine.begin() as conn:
        org_id = get_or_create_org(conn, clerk_org_id, claims.get("org_slug", clerk_org_id))
        org = conn.execute(select(organizations).where(organizations.c.id == org_id)).one()

    usage = get_monthly_usage(engine, org_id)
    limit = None if org.tier == "pro" else settings.free_tier_monthly_query_limit
    return BillingStatus(
        tier=org.tier,
        subscription_status=org.stripe_subscription_status,
        usage_this_month=usage,
        monthly_limit=limit,
    )


@router.post("/checkout", response_model=CheckoutOut)
def checkout(claims: Claims):
    clerk_org_id = _require_org_id(claims)
    engine = get_app_engine()

    with engine.begin() as conn:
        org_id = get_or_create_org(conn, clerk_org_id, claims.get("org_slug", clerk_org_id))
        org = conn.execute(select(organizations).where(organizations.c.id == org_id)).one()

        customer_id = get_or_create_customer(clerk_org_id, org.name, org.stripe_customer_id)
        if customer_id != org.stripe_customer_id:
            conn.execute(
                organizations.update().where(organizations.c.id == org_id).values(stripe_customer_id=customer_id)
            )

    url = create_checkout_session(
        customer_id,
        success_url=f"{settings.frontend_url}/settings/billing?success=true",
        cancel_url=f"{settings.frontend_url}/settings/billing?canceled=true",
    )
    return CheckoutOut(url=url)


@router.post("/portal", response_model=CheckoutOut)
def portal(claims: Claims):
    clerk_org_id = _require_org_id(claims)
    engine = get_app_engine()

    with engine.connect() as conn:
        org_row = conn.execute(
            select(organizations).where(organizations.c.clerk_org_id == clerk_org_id)
        ).first()

    if not org_row or not org_row.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account yet — upgrade first")

    url = create_portal_session(org_row.stripe_customer_id, return_url=f"{settings.frontend_url}/settings/billing")
    return CheckoutOut(url=url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc

    engine = get_app_engine()
    data = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        with engine.begin() as conn:
            conn.execute(
                organizations.update()
                .where(organizations.c.stripe_customer_id == data["customer"])
                .values(
                    tier="pro",
                    stripe_subscription_id=data["subscription"],
                    stripe_subscription_status="active",
                )
            )

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        status_value = data["status"] if event["type"] == "customer.subscription.updated" else "canceled"
        new_tier = "pro" if status_value in ("active", "trialing") else "free"
        with engine.begin() as conn:
            conn.execute(
                organizations.update()
                .where(organizations.c.stripe_customer_id == data["customer"])
                .values(tier=new_tier, stripe_subscription_status=status_value)
            )

    return {"received": True}
