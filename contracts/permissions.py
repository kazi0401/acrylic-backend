
from rest_framework.permissions import BasePermission
from django.utils import timezone
from .models import Contract
from django.conf import settings

class HasSignedContract(BasePermission):
    message = "You must sign the platform agreement before continuing."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        contract_type = (
            'rightsholder' if request.user.role == 'artist' else 'buyer'
        )

        return Contract.objects.filter(
            user=request.user,
            contract_type=contract_type,
            version=settings.CURRENT_CONTRACT_VERSION,
            status='signed',
            expires_at__gt=timezone.now(),
        ).exists()