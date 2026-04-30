import os
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings 


def create_stripe_customer(user):
    """
    Creates a Stripe customer for a buyer.
    Returns a Stripe customer ID string.
    """
    if settings.STRIPE_TEST_MODE:
        return f"cus_mock_{user.id}"

    # --- REAL STRIPE INTEGRATION ---
    # import stripe
    # stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    # customer = stripe.Customer.create(
    #     email=user.email,
    #     name=f"{user.first_name} {user.last_name}",
    #     metadata={"user_id": user.id}
    # )
    # return customer.id


def create_stripe_subscription(customer_id, tier):
    """
    Creates a Stripe subscription for a customer on a given tier.
    Returns a dict with subscription id, status, and billing period.
    """
    if settings.STRIPE_TEST_MODE:
        now = timezone.now()
        return {
            "id": f"sub_mock_{customer_id}",
            "status": "active",
            "current_period_start": now,
            "current_period_end": now + timedelta(days=365)
        }

    # --- REAL STRIPE INTEGRATION ---
    # import stripe
    # stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    # subscription = stripe.Subscription.create(
    #     customer=customer_id,
    #     items=[{"price": tier.stripe_price_id}],
    #     metadata={"tier_id": tier.id}
    # )
    # return {
    #     "id": subscription.id,
    #     "status": subscription.status,
    #     "current_period_start": datetime.fromtimestamp(
    #         subscription.current_period_start, tz=timezone.utc
    #     ),
    #     "current_period_end": datetime.fromtimestamp(
    #         subscription.current_period_end, tz=timezone.utc
    #     )
    # }


def cancel_stripe_subscription(subscription_id):
    """
    Cancels an active Stripe subscription.
    Returns a dict with the updated status.
    """
    if settings.STRIPE_TEST_MODE:
        return {"status": "cancelled"}

    # --- REAL STRIPE INTEGRATION ---
    # import stripe
    # stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    # subscription = stripe.Subscription.delete(subscription_id)
    # return {"status": subscription.status}


def create_stripe_payment_intent(amount, currency, customer_id, metadata=None):
    """
    Creates a Stripe PaymentIntent for a one-time per-song PreClear charge.
    Returns a dict with the payment intent id and client secret.
    """
    if settings.STRIPE_TEST_MODE:
        return {
            "id": f"pi_mock_{customer_id}",
            "client_secret": f"pi_mock_{customer_id}_secret",
            "status": "succeeded"
        }

    # --- REAL STRIPE INTEGRATION ---
    # import stripe
    # stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    # intent = stripe.PaymentIntent.create(
    #     amount=int(amount * 100),  # Stripe uses cents
    #     currency=currency,
    #     customer=customer_id,
    #     metadata=metadata or {}
    # )
    # return {
    #     "id": intent.id,
    #     "client_secret": intent.client_secret,
    #     "status": intent.status
    # }


def confirm_stripe_payment_intent(payment_intent_id):
    """
    Confirms a PaymentIntent was successfully paid.
    Used to verify PreClear license payments before creating a License record.
    Returns a dict with the status.
    """
    if settings.STRIPE_TEST_MODE:
        return {"status": "succeeded"}

    # --- REAL STRIPE INTEGRATION ---
    # import stripe
    # stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    # intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    # return {"status": intent.status}