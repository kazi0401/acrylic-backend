
from django.contrib import admin
from .models import Contract

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['user', 'contract_type', 'status', 'version', 'signed_at', 'expires_at']
    list_filter = ['status', 'contract_type']