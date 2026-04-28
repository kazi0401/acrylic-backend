
from django.urls import path
from .views import LicenseRequestView, LicenseRequestDetailView, LicenseRequestAdminView

urlpatterns = [
    path('', LicenseRequestView.as_view()),                        # POST, GET
    path('<int:pk>/', LicenseRequestDetailView.as_view()),         # buyer GET
    path('<int:pk>/review/', LicenseRequestAdminView.as_view()),   # admin PATCH
]