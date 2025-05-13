from django.contrib import admin
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector

class StationImageInline(admin.TabularInline):
    model = StationImage
    extra = 1

class ChargingConnectorInline(admin.TabularInline):
    model = ChargingConnector
    extra = 1

@admin.register(StationOwner)
class StationOwnerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user_email', 'verification_status', 'is_profile_completed', 'created_at')
    list_filter = ('verification_status', 'is_profile_completed')
    search_fields = ('company_name', 'user__email', 'business_registration_number')
    readonly_fields = ('created_at', 'updated_at', 'verified_at')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_company', 'city', 'state', 'is_active')
    list_filter = ('is_active', 'city', 'state')
    search_fields = ('name', 'address', 'city', 'owner__company_name')
    inlines = [ChargingConnectorInline, StationImageInline]

    def owner_company(self, obj):
        return obj.owner.company_name
    owner_company.short_description = 'Owner'
