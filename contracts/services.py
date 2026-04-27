
import requests
import uuid
from django.conf import settings


def _headers():
    return {
        "X-Api-Key": settings.SIGNWELL_API_KEY,
        "Content-Type": "application/json",
    }

def create_signing_document(user, contract_type, template_id):
    """
    Creates a document from a pre-built SignWell template and returns
    the document_id and embedded_signing_url.
    """

    if settings.SIGNWELL_TEST_MODE:
        # Return a fake document_id and signing_url
        fake_id = f"mock-doc-{uuid.uuid4()}"
        fake_url = f"http://localhost:8000/api/contracts/mock-sign/?doc={fake_id}"
        return fake_id, fake_url


    payload = {
        "test_mode": settings.SIGNWELL_TEST_MODE,  # True in dev, False in prod
        "template_ids": [template_id],
        "subject": f"Acrylic Platform Agreement — {contract_type.title()}",
        "recipients": [
            {
                "id": "1",   # matches the placeholder role in your SignWell template
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "embedded_signing": True,  # keeps user inside your app
            }
        ],
        "redirect_url": f"{settings.FRONTEND_URL}/dashboard?contract=signed",
    }

    response = requests.post(
        f"{settings.SIGNWELL_BASE_URL}/document_templates/",
        json=payload,
        headers=_headers(),
    )
    response.raise_for_status()
    data = response.json()

    document_id = data["id"]
    # signing URL is nested under the recipient
    signing_url = data["recipients"][0]["embedded_signing_url"]

    return document_id, signing_url


def get_signing_url(signwell_document_id, signer_email):
    """
    Refreshes the embedded signing URL for an existing document.
    These URLs are short-lived so you may need to regenerate them.
    """
    response = requests.get(
        f"{settings.SIGNWELL_BASE_URL}/documents/{signwell_document_id}/",
        headers=_headers(),
    )
    response.raise_for_status()
    data = response.json()

    for recipient in data["recipients"]:
        if recipient["email"] == signer_email:
            return recipient["embedded_signing_url"]

    return None