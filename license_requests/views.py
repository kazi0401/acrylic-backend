from django.shortcuts import render

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate


from .models import LicenseRequest
from .serializers import LicenseRequestSerializer, LicenseRequestAdminSerializer

from rest_framework.permissions import IsAuthenticated
from contracts.permissions import HasSignedContract
from users.permissions import IsAdmin


class LicenseRequestView(APIView):
    
    permission_classes = [IsAuthenticated, HasSignedContract]

    def post(self, request):
        serializer = LicenseRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(client=request.user)
            return Response(
                {'message': 'License Request Submitted.'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        requests = LicenseRequest.objects.filter(client=request.user)
        serializer = LicenseRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LicenseRequestDetailView(APIView):
    """Buyer-facing — retrieve own request by ID"""
    permission_classes = [IsAuthenticated, HasSignedContract]

    def get_object(self, pk, user):
        try:
            return LicenseRequest.objects.get(pk=pk, client=user)
        except LicenseRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        license_request = self.get_object(pk, request.user)
        if license_request is None:
            return Response(
                {'error': 'License request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = LicenseRequestSerializer(license_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LicenseRequestAdminView(APIView):
    """Admin-facing — update status and notes on any request"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            license_request = LicenseRequest.objects.get(pk=pk)
        except LicenseRequest.DoesNotExist:
            return Response(
                {'error': 'License request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = LicenseRequestAdminSerializer(
            license_request,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)