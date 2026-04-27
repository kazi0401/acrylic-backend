
from django.db import models
from django.utils import timezone

class Contract(models.Model):
    CONTRACT_TYPES = [
        ('rightsholder', 'Rightsholder Agreement'),
        ('buyer', 'Buyer Terms of Service'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Signature'),
        ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('declined', 'Declined'),
    ]

    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,  # never delete a contract if user is deleted
        related_name='contracts'
    )
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    version = models.CharField(max_length=10)        # e.g. "v1.0"
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # SignWell references
    signwell_document_id = models.CharField(max_length=255, unique=True)
    embedded_signing_url = models.TextField(blank=True)  # short-lived, regenerated as needed

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Storage (for later when S3 is wired up)
    pdf_storage_key = models.CharField(max_length=500, blank=True)

    class Meta:
        # one active contract per user per type per version
        unique_together = ('user', 'contract_type', 'version')

    def is_valid(self):
        return (
            self.status == 'signed' and
            (self.expires_at is None or self.expires_at > timezone.now())
        )