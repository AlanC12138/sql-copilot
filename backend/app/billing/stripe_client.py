import stripe

from app.config import settings

stripe.api_key = settings.stripe_secret_key


def get_or_create_customer(clerk_org_id: str, org_name: str, existing_customer_id: str | None) -> str:
    if existing_customer_id:
        return existing_customer_id
    customer = stripe.Customer.create(name=org_name, metadata={"clerk_org_id": clerk_org_id})
    return customer.id


def create_checkout_session(customer_id: str, success_url: str, cancel_url: str) -> str:
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id_pro, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def create_portal_session(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
