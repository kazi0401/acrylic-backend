from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from contracts.permissions import HasSignedContract
from .models import SubscriptionTier, BuyerSubscription
from .serializers import SubscriptionTierSerializer, BuyerSubscriptionSerializer

from .stripe_services import \
  create_stripe_customer, create_stripe_subscription, cancel_stripe_subscription


class SubscriptionTierListView(APIView):
    """
    Public endpoint. Lists all active subscription tiers.
    No auth required — buyers should be able to see plans before signing up.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        tiers = SubscriptionTier.objects.filter(is_active=True)
        serializer = SubscriptionTierSerializer(tiers, many=True)
        return Response(serializer.data)


class SubscribeView(APIView):
    """
    Buyer subscribes to a tier.
    Requires JWT + signed buyer contract.
    Creates a Stripe customer and subscription, then saves BuyerSubscription.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def post(self, request):
        # Check the user has a client profile
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients can subscribe."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Block if already has an active subscription
        already_active = BuyerSubscription.objects.filter(
            profile=profile,
            status=BuyerSubscription.Status.ACTIVE
        ).exists()

        if already_active:
            return Response(
                {"detail": "You already have an active subscription."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BuyerSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        tier = serializer.validated_data['tier']

        # Create Stripe customer and subscription (mocked in test mode)
        stripe_customer_id = create_stripe_customer(request.user)
        stripe_subscription = create_stripe_subscription(stripe_customer_id, tier)

        # Save subscription record
        subscription = serializer.save(
            profile=profile,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription['id'],
            status=BuyerSubscription.Status.ACTIVE,
            current_period_start=stripe_subscription['current_period_start'],
            current_period_end=stripe_subscription['current_period_end']
        )

        return Response(
            BuyerSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED
        )


class MySubscriptionView(APIView):
    """
    Buyer views their current active subscription.
    Requires JWT + signed buyer contract.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def get(self, request):
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients have subscriptions."},
                status=status.HTTP_403_FORBIDDEN
            )

        subscription = BuyerSubscription.objects.filter(
            profile=profile,
            status=BuyerSubscription.Status.ACTIVE
        ).first()

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BuyerSubscriptionSerializer(subscription)
        return Response(serializer.data)


class CancelSubscriptionView(APIView):
    """
    Buyer cancels their active subscription.
    Requires JWT + signed buyer contract.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def post(self, request):
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients have subscriptions."},
                status=status.HTTP_403_FORBIDDEN
            )

        subscription = BuyerSubscription.objects.filter(
            profile=profile,
            status=BuyerSubscription.Status.ACTIVE
        ).first()

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Cancel on Stripe side (mocked in test mode)
        cancel_stripe_subscription(subscription.stripe_subscription_id)

        subscription.status = BuyerSubscription.Status.CANCELLED
        subscription.save()

        return Response(
            {"detail": "Subscription cancelled successfully."},
            status=status.HTTP_200_OK
        )