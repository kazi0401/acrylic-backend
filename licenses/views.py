from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from contracts.permissions import HasSignedContract
from subscriptions.models import BuyerSubscription
from .models import License
from .serializers import (
    LicenseSerializer,
    PreClearLicenseSerializer,
    ArtistPromoLicenseSerializer
)
from .permissions import HasActiveSubscription
from subscriptions.stripe_services import (
    create_stripe_customer,
    create_stripe_payment_intent,
    confirm_stripe_payment_intent
)


class PreClearLicenseView(APIView):
    """
    POST — buyer licenses a PreClear track.
    Triggers a Stripe PaymentIntent, confirms it,
    then creates the License record.
    Requires JWT + signed buyer contract.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def post(self, request):
        # Ensure user is a client
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients can license tracks."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PreClearLicenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        song = serializer.validated_data['song']

        # Create Stripe customer and PaymentIntent
        stripe_customer_id = create_stripe_customer(request.user)
        payment_intent = create_stripe_payment_intent(
            amount=song.fixed_price,
            currency='usd',
            customer_id=stripe_customer_id,
            metadata={
                'song_id': song.id,
                'user_id': request.user.id
            }
        )

        # Confirm payment succeeded
        confirmation = confirm_stripe_payment_intent(payment_intent['id'])
        if confirmation['status'] != 'succeeded':
            return Response(
                {"detail": "Payment failed. Please try again."},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # Create license record
        license = serializer.save(
            client=profile,
            license_type=License.LicenseType.PRECLEAR,
            stripe_payment_intent_id=payment_intent['id'],
            price_paid=song.fixed_price,
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )

        return Response(
            LicenseSerializer(license).data,
            status=status.HTTP_201_CREATED
        )


class ArtistPromoLicenseView(APIView):
    """
    POST — buyer licenses an Artist Promo track.
    No charge. Requires active subscription.
    Requires JWT + signed buyer contract + active subscription.
    """
    permission_classes = [IsAuthenticated, HasSignedContract, HasActiveSubscription]

    def post(self, request):
        # Ensure user is a client
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients can license tracks."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ArtistPromoLicenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get active subscription to link to license
        subscription = BuyerSubscription.objects.filter(
            profile=profile,
            status=BuyerSubscription.Status.ACTIVE
        ).first()

        # Create license record — no charge
        license = serializer.save(
            client=profile,
            license_type=License.LicenseType.ARTIST_PROMO,
            subscription=subscription,
            price_paid=None,
            valid_from=timezone.now(),
            status=License.Status.ACTIVE
        )

        return Response(
            LicenseSerializer(license).data,
            status=status.HTTP_201_CREATED
        )


class MyLicensesView(APIView):
    """
    GET — buyer views all their licenses.
    Requires JWT + signed buyer contract.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def get(self, request):
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients have licenses."},
                status=status.HTTP_403_FORBIDDEN
            )

        licenses = License.objects.filter(
            client=profile
        ).order_by('-created_at')

        serializer = LicenseSerializer(licenses, many=True)
        return Response(serializer.data)


class LicenseDetailView(APIView):
    """
    GET — buyer views a single license by id.
    Filters by client so buyers cannot access other buyers' licenses.
    Requires JWT + signed buyer contract.
    """
    permission_classes = [IsAuthenticated, HasSignedContract]

    def get(self, request, pk):
        try:
            profile = request.user.client_profile
        except Exception:
            return Response(
                {"detail": "Only clients have licenses."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            license = License.objects.get(pk=pk, client=profile)
        except License.DoesNotExist:
            return Response(
                {"detail": "License not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LicenseSerializer(license)
        return Response(serializer.data)