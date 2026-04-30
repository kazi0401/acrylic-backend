from django.urls import path
from . import views

urlpatterns = [
    path('preclear/', views.PreClearLicenseView.as_view()),
    path('artist-promo/', views.ArtistPromoLicenseView.as_view()),
    path('my-licenses/', views.MyLicensesView.as_view()),
    path('<int:pk>/', views.LicenseDetailView.as_view()),
]