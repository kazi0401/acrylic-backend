
from django.urls import path
from django.conf import settings
from .views import InitiateSigningView, SignWellWebhookView, MockSigningView


urlpatterns = [
    path('initiate/', InitiateSigningView.as_view()),
    path('webhook/', SignWellWebhookView.as_view()),
]

if settings.SIGNWELL_TEST_MODE:
    urlpatterns += [
        path('mock-sign/', MockSigningView.as_view()),
    ]