from django.test import TestCase

# contracts/tests.py
#
# Run with:  python manage.py test contracts
#
# These tests cover the full signing flow without hitting
# SignWell's real API. Everything external is mocked.

from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from rest_framework.test import APIClient
from rest_framework import status

from users.models import User
from contracts.models import Contract


# ---------------------------------------------------------------------------
# Shared settings override — forces test mode and provides fake template IDs
# ---------------------------------------------------------------------------
TEST_SETTINGS = {
    "SIGNWELL_TEST_MODE": True,
    "SIGNWELL_API_KEY": "test-api-key",
    "SIGNWELL_WEBHOOK_SECRET": "test-webhook-secret",
    "CURRENT_CONTRACT_VERSION": "v1.0",
    "SIGNWELL_TEMPLATE_IDS": {
        "rightsholder": "template-rightsholder-123",
        "buyer": "template-buyer-456",
    },
    "FRONTEND_URL": "http://localhost:3000",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_user(username, role, password="pass1234"):
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password=password,
        role=role,
    )
    return user


def make_signed_contract(user, version="v1.0"):
    """Creates an already-signed contract for a user."""
    contract_type = "rightsholder" if user.role == "artist" else "buyer"
    return Contract.objects.create(
        user=user,
        contract_type=contract_type,
        version=version,
        status="signed",
        signwell_document_id=f"doc-{user.username}",
        signed_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=365),
    )


# ---------------------------------------------------------------------------
# 1. Contract model
# ---------------------------------------------------------------------------
class ContractModelTests(TestCase):

    def setUp(self):
        self.artist = make_user("artist1", "artist")

    def test_is_valid_returns_true_when_signed_and_not_expired(self):
        contract = make_signed_contract(self.artist)
        self.assertTrue(contract.is_valid())

    def test_is_valid_returns_false_when_status_is_pending(self):
        contract = Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="pending",
            signwell_document_id="doc-pending",
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertFalse(contract.is_valid())

    def test_is_valid_returns_false_when_expired(self):
        contract = Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="signed",
            signwell_document_id="doc-expired",
            signed_at=timezone.now() - timedelta(days=400),
            expires_at=timezone.now() - timedelta(days=35),  # expired 35 days ago
        )
        self.assertFalse(contract.is_valid())

    def test_is_valid_returns_false_when_declined(self):
        contract = Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="declined",
            signwell_document_id="doc-declined",
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.assertFalse(contract.is_valid())


# ---------------------------------------------------------------------------
# 2. HasSignedContract permission
# ---------------------------------------------------------------------------
@override_settings(**TEST_SETTINGS)
class HasSignedContractPermissionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.artist = make_user("artist2", "artist")
        self.buyer = make_user("buyer1", "client")

    def test_artist_blocked_from_upload_without_contract(self):
        self.client.force_authenticate(user=self.artist)
        response = self.client.post("/api/songs/upload/", {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_artist_can_upload_after_signing(self):
        make_signed_contract(self.artist)
        self.client.force_authenticate(user=self.artist)
        # We only care that the permission passes — a 400 means
        # the view was reached but the form was incomplete, which is fine here
        response = self.client.post("/api/songs/upload/", {})
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    
    def test_buyer_blocked_from_play_without_contract(self):
      self.client.force_authenticate(user=self.buyer)
      # Use any valid song ID — we only care about the 403, not the song
      response = self.client.post("/api/songs/99999/play/")
      self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_is_blocked(self):
        response = self.client.post("/api/songs/upload/", {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_contract_is_blocked(self):
        """An expired but previously signed contract should not grant access."""
        Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="signed",
            signwell_document_id="doc-old",
            signed_at=timezone.now() - timedelta(days=400),
            expires_at=timezone.now() - timedelta(days=35),
        )
        self.client.force_authenticate(user=self.artist)
        response = self.client.post("/api/songs/upload/", {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_version_contract_is_blocked(self):
        """A signed contract for an old version should not grant access."""
        Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v0.9",  # old version
            status="signed",
            signwell_document_id="doc-old-version",
            signed_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=365),
        )
        self.client.force_authenticate(user=self.artist)
        response = self.client.post("/api/songs/upload/", {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# 3. InitiateSigningView  (POST /api/contracts/initiate/)
# ---------------------------------------------------------------------------
@override_settings(**TEST_SETTINGS)
class InitiateSigningViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.artist = make_user("artist3", "artist")
        self.buyer = make_user("buyer2", "client")

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post("/api/contracts/initiate/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_artist_gets_signing_url_in_test_mode(self):
        """In test mode, no real SignWell call is made — we get a mock URL back."""
        self.client.force_authenticate(user=self.artist)
        response = self.client.post("/api/contracts/initiate/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("document_id", response.data)
        self.assertIn("signing_url", response.data)
        self.assertIn("mock-sign", response.data["signing_url"])

    def test_contract_row_is_created_in_db(self):
        self.client.force_authenticate(user=self.artist)
        self.client.post("/api/contracts/initiate/")

        contract = Contract.objects.get(user=self.artist)
        self.assertEqual(contract.status, "pending")
        self.assertEqual(contract.contract_type, "rightsholder")
        self.assertEqual(contract.version, "v1.0")

    def test_buyer_gets_buyer_contract_type(self):
        self.client.force_authenticate(user=self.buyer)
        self.client.post("/api/contracts/initiate/")
        contract = Contract.objects.get(user=self.buyer)
        self.assertEqual(contract.contract_type, "buyer")

    def test_already_signed_contract_returns_200_not_201(self):
        """If already signed, we shouldn't create a duplicate."""
        make_signed_contract(self.artist)
        self.client.force_authenticate(user=self.artist)
        response = self.client.post("/api/contracts/initiate/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already signed", response.data["detail"])
        # Should still be only one contract in the DB
        self.assertEqual(Contract.objects.filter(user=self.artist).count(), 1)

    @patch("contracts.services.requests.post")
    def test_real_signwell_api_called_when_not_in_test_mode(self, mock_post):
        """
        When SIGNWELL_TEST_MODE is False, the real API should be called.
        We mock requests.post so no real HTTP goes out.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "real-doc-id-abc",
            "recipients": [
                {"email": "artist3@test.com", "embedded_signing_url": "https://sign.signwell.com/abc"}
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with self.settings(SIGNWELL_TEST_MODE=False):
            self.client.force_authenticate(user=self.artist)
            response = self.client.post("/api/contracts/initiate/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["document_id"], "real-doc-id-abc")
        mock_post.assert_called_once()  # confirms the real HTTP call was made


# ---------------------------------------------------------------------------
# 4. MockSigningView  (GET /api/contracts/mock-sign/)
# ---------------------------------------------------------------------------
@override_settings(**TEST_SETTINGS)
class MockSigningViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.artist = make_user("artist4", "artist")

    def _create_pending_contract(self, doc_id="doc-abc-123"):
        return Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="pending",
            signwell_document_id=doc_id,
            expires_at=timezone.now() + timedelta(days=365),
        )

    def test_mock_sign_marks_contract_as_signed(self):
        contract = self._create_pending_contract()
        response = self.client.get(
            f"/api/contracts/mock-sign/?doc={contract.signwell_document_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contract.refresh_from_db()
        self.assertEqual(contract.status, "signed")
        self.assertIsNotNone(contract.signed_at)

    def test_mock_sign_missing_doc_param_returns_400(self):
        response = self.client.get("/api/contracts/mock-sign/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mock_sign_unknown_doc_id_returns_404(self):
        response = self.client.get("/api/contracts/mock-sign/?doc=does-not-exist")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mock_sign_unavailable_in_production(self):
        self._create_pending_contract()
        with self.settings(SIGNWELL_TEST_MODE=False):
            response = self.client.get("/api/contracts/mock-sign/?doc=doc-abc-123")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# 5. SignWellWebhookView  (POST /api/contracts/webhook/)
# ---------------------------------------------------------------------------
@override_settings(**TEST_SETTINGS)
class WebhookViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.artist = make_user("artist5", "artist")
        self.contract = Contract.objects.create(
            user=self.artist,
            contract_type="rightsholder",
            version="v1.0",
            status="pending",
            signwell_document_id="doc-webhook-test",
            expires_at=timezone.now() + timedelta(days=365),
        )

    def _post_webhook(self, event_type, doc_id, secret="test-webhook-secret"):
        """Helper to POST a webhook event with a valid HMAC signature."""
        import json, hmac, hashlib

        payload = json.dumps({
            "event": {"type": event_type},
            "data": {"id": doc_id},
        }).encode()

        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return self.client.post(
            "/api/contracts/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_X_SIGNWELL_SIGNATURE=signature,
        )

    def test_document_completed_marks_contract_signed(self):
        response = self._post_webhook("document_completed", "doc-webhook-test")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "signed")
        self.assertIsNotNone(self.contract.signed_at)

    def test_document_declined_marks_contract_declined(self):
        response = self._post_webhook("document_declined", "doc-webhook-test")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "declined")

    def test_invalid_hmac_signature_returns_403(self):
        response = self._post_webhook(
            "document_completed", "doc-webhook-test", secret="wrong-secret"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Contract should NOT have been updated
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending")

    def test_unknown_event_type_is_ignored_gracefully(self):
        """Unrecognised events should return 200 without crashing."""
        response = self._post_webhook("document_viewed", "doc-webhook-test")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, "pending")  # unchanged

    def test_missing_document_id_returns_200_without_crash(self):
        """SignWell should always get a 200 back, even for malformed payloads."""
        import json, hmac, hashlib

        payload = json.dumps({"event": {"type": "document_completed"}}).encode()
        signature = hmac.new(
            b"test-webhook-secret", payload, hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            "/api/contracts/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_X_SIGNWELL_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 6. Full end-to-end flow
# ---------------------------------------------------------------------------
@override_settings(**TEST_SETTINGS)
class FullSigningFlowTests(TestCase):
    """
    Walks through the complete flow in one test:
    register → blocked → initiate → mock-sign → unblocked
    """

    def setUp(self):
        self.client = APIClient()
        self.artist = make_user("artist6", "artist")

    def test_full_flow(self):
        self.client.force_authenticate(user=self.artist)

        # 1. Blocked before signing
        response = self.client.post("/api/songs/upload/", {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Initiate signing — get a mock signing URL
        response = self.client.post("/api/contracts/initiate/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_id = response.data["document_id"]

        # 3. Simulate the user signing in the iframe
        response = self.client.get(f"/api/contracts/mock-sign/?doc={doc_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Now unblocked
        response = self.client.post("/api/songs/upload/", {})
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)