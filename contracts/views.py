
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Contract
from .services import create_signing_document

import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class InitiateSigningView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        contract_type = 'rightsholder' if user.role == 'artist' else 'buyer'

        # Check if already signed and valid
        existing = Contract.objects.filter(
            user=user,
            contract_type=contract_type,
            version=settings.CURRENT_CONTRACT_VERSION,
            status='signed',
        ).first()

        if existing and existing.is_valid():
            return Response({"detail": "Contract already signed."}, status=200)

        # Create a new SignWell document
        template_id = settings.SIGNWELL_TEMPLATE_IDS[contract_type]
        document_id, signing_url = create_signing_document(
            user, contract_type, template_id
        )

        # Save to DB
        contract = Contract.objects.create(
            user=user,
            contract_type=contract_type,
            version=settings.CURRENT_CONTRACT_VERSION,
            signwell_document_id=document_id,
            embedded_signing_url=signing_url,
            expires_at=timezone.now() + timedelta(days=365),  # annual renewal
        )

        return Response({
            "document_id": document_id,
            "signing_url": signing_url,
        }, status=201)
    

class MockSigningView(APIView):
    """
    Local development only. Simulates the user completing
    the SignWell iframe and triggers the same logic as the
    real webhook would.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        if not settings.SIGNWELL_TEST_MODE:
            return Response({"detail": "Not available."}, status=404)

        doc_id = request.query_params.get("doc")
        if not doc_id:
            return Response({"detail": "Missing doc param."}, status=400)

        # Simulate what the real webhook handler does
        from django.utils import timezone
        updated = Contract.objects.filter(
            signwell_document_id=doc_id
        ).update(
            status='signed',
            signed_at=timezone.now(),
        )

        if updated:
            return Response({
                "detail": "Mock signing complete. Contract marked as signed."
            })
        return Response({"detail": "Contract not found."}, status=404)



@method_decorator(csrf_exempt, name='dispatch')
class SignWellWebhookView(APIView):
    authentication_classes = []  # SignWell calls this, not your users
    permission_classes = []

    def post(self, request):
        # Verify the request actually came from SignWell
        # SignWell sends a signature header — check their docs for the exact header name
        provided_secret = request.headers.get("X-Signwell-Signature", "")
        expected = hmac.new(
            settings.SIGNWELL_WEBHOOK_SECRET.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provided_secret, expected):
            return Response({"detail": "Invalid signature."}, status=403)

        event = request.data
        event_type = event.get("event", {}).get("type")
        document_id = event.get("data", {}).get("id")

        if not document_id:
            return Response(status=200)  # always return 200 to SignWell

        if event_type == "document_completed":
            Contract.objects.filter(
                signwell_document_id=document_id
            ).update(
                status='signed',
                signed_at=timezone.now(),
            )

        elif event_type == "document_declined":
            Contract.objects.filter(
                signwell_document_id=document_id
            ).update(status='declined')

        return Response(status=200)
    

