
from django.urls import path
from django.conf import settings
from .views import InitiateSigningView, SignWellWebhookView, MockSigningView


urlpatterns = [
    path('contracts/initiate/', InitiateSigningView.as_view()),
    path('contracts/webhook/', SignWellWebhookView.as_view()),
]

if settings.SIGNWELL_TEST_MODE:
    urlpatterns += [
        path('contracts/mock-sign/', MockSigningView.as_view()),
    ]