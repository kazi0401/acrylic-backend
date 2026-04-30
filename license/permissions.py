from rest_framework.permissions import BasePermission
from subscriptions.models import BuyerSubscription

class HasActiveSubscription(BasePermission):
    message = "An active subscription is required to license Artist Promo tracks."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            subscription = BuyerSubscription.objects.get(
                profile=request.user.clientprofile
            )
            return subscription.status == 'active'
        except BuyerSubscription.DoesNotExist:
            return False