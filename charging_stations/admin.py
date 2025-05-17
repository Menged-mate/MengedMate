from django.contrib import admin
from django.utils.html import format_html
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector

class StationImageInline(admin.TabularInline):
    model = StationImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'

class ChargingConnectorInline(admin.StackedInline):
    model = ChargingConnector
    extra = 1
    fieldsets = (
        (None, {
            'fields': (('connector_type', 'power_kw'), 'is_available')
        }),
        ('Additional Details', {
            'fields': ('description',),
            'classes': ('collapse',),
        }),
    )

@admin.register(StationOwner)
class StationOwnerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user_email', 'verification_badge', 'is_profile_completed', 'created_at')
    list_filter = ('verification_status', 'is_profile_completed', 'created_at')
    search_fields = ('company_name', 'user__email', 'business_registration_number')
    readonly_fields = ('created_at', 'updated_at', 'verified_at', 'document_preview')
    fieldsets = (
        (None, {
            'fields': ('user', 'company_name', 'business_registration_number')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verified_at', 'is_profile_completed')
        }),
        ('Documents', {
            'fields': ('business_document', 'document_preview')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email', 'website')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    list_per_page = 25
    save_on_top = True

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def verification_badge(self, obj):
        if obj.verification_status == 'verified':
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✓ Verified</span>')
        elif obj.verification_status == 'pending':
            return format_html('<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 3px;">⏳ Pending</span>')
        else:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">✗ Rejected</span>')
    verification_badge.short_description = 'Verification'

    def document_preview(self, obj):
        if obj.business_document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.business_document.url)
        return "No document uploaded"
    document_preview.short_description = 'Document Preview'

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_company', 'location_display', 'status_badge', 'connector_count')
    list_filter = ('is_active', 'city', 'state', 'owner')
    search_fields = ('name', 'address', 'city', 'owner__company_name')
    inlines = [ChargingConnectorInline, StationImageInline]
    readonly_fields = ('created_at', 'updated_at', 'map_preview')
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code', 'latitude', 'longitude', 'map_preview')
        }),
        ('Status', {
            'fields': ('is_active', 'opening_hours')
        }),
        ('Amenities', {
            'fields': ('has_restroom', 'has_wifi', 'has_restaurant', 'has_shopping')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    list_per_page = 20
    save_on_top = True

    def owner_company(self, obj):
        if obj.owner and obj.owner.verification_status == 'verified':
            return format_html('{} <span style="color: green;">✓</span>', obj.owner.company_name)
        return obj.owner.company_name if obj.owner else "N/A"
    owner_company.short_description = 'Owner'

    def location_display(self, obj):
        return f"{obj.city}, {obj.state}"
    location_display.short_description = 'Location'

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Active</span>')
        else:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">Inactive</span>')
    status_badge.short_description = 'Status'

    def connector_count(self, obj):
        count = obj.connectors.count()
        return count
    connector_count.short_description = 'Connectors'

    def map_preview(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<div style="width:100%;height:300px;margin-top:10px;">'
                '<iframe width="100%" height="100%" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" '
                'src="https://maps.google.com/maps?q={},{}&z=15&output=embed"></iframe>'
                '</div>', obj.latitude, obj.longitude
            )
        return "Location coordinates not set"
    map_preview.short_description = 'Map Location'

@admin.register(ChargingConnector)
class ChargingConnectorAdmin(admin.ModelAdmin):
    list_display = ('connector_type', 'station_name', 'power_kw', 'availability_status')
    list_filter = ('connector_type', 'is_available', 'station__name')
    search_fields = ('station__name', 'connector_type')

    def station_name(self, obj):
        return obj.station.name
    station_name.short_description = 'Station'

    def availability_status(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green;">Available</span>')
        else:
            return format_html('<span style="color: red;">Unavailable</span>')
    availability_status.short_description = 'Availability'
