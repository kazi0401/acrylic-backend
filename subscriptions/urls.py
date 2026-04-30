from django.urls import path
from . import views

urlpatterns = [
    path('tiers/', views.SubscriptionTierListView.as_view()),
    path('subscribe/', views.SubscribeView.as_view()),
    path('me/', views.MySubscriptionView.as_view()),
    path('cancel/', views.CancelSubscriptionView.as_view()),
]