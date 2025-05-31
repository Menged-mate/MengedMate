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
    list_display = ('company_name', 'user_email', 'verification_badge', 'is_profile_completed', 'documents_uploaded', 'created_at')
    list_filter = ('verification_status', 'is_profile_completed', 'created_at')
    search_fields = ('company_name', 'user__email', 'business_registration_number')
    readonly_fields = ('created_at', 'updated_at', 'verified_at', 'business_document_preview', 'business_license_preview', 'id_proof_preview', 'utility_bill_preview')
    fieldsets = (
        (None, {
            'fields': ('user', 'company_name', 'business_registration_number')
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'verified_at', 'is_profile_completed')
        }),
        ('Business Documents', {
            'fields': ('business_document', 'business_document_preview', 'business_license', 'business_license_preview')
        }),
        ('Identity & Utility Documents', {
            'fields': ('id_proof', 'id_proof_preview', 'utility_bill', 'utility_bill_preview')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email', 'website', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    list_per_page = 25
    save_on_top = True

    actions = ['approve_verification', 'reject_verification', 'mark_pending']

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

    def documents_uploaded(self, obj):
        docs = []
        if obj.business_document:
            docs.append('Business')
        if obj.business_license:
            docs.append('License')
        if obj.id_proof:
            docs.append('ID')
        if obj.utility_bill:
            docs.append('Utility')

        if docs:
            return format_html('<span style="color: green;">✓ {}</span>', ', '.join(docs))
        return format_html('<span style="color: red;">✗ No documents</span>')
    documents_uploaded.short_description = 'Documents'

    def business_document_preview(self, obj):
        if obj.business_document:
            if obj.business_document.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" /><br>'
                    '<a href="{}" target="_blank" style="margin-top: 5px; display: inline-block;">📄 View Full Size</a>'
                    '</div>',
                    obj.business_document.url, obj.business_document.url
                )
            else:
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<a href="{}" target="_blank" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">📄 Download Document</a>'
                    '</div>',
                    obj.business_document.url
                )
        return format_html('<span style="color: #999;">No business document uploaded</span>')
    business_document_preview.short_description = 'Business Document Preview'

    def business_license_preview(self, obj):
        if obj.business_license:
            if obj.business_license.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" /><br>'
                    '<a href="{}" target="_blank" style="margin-top: 5px; display: inline-block;">📄 View Full Size</a>'
                    '</div>',
                    obj.business_license.url, obj.business_license.url
                )
            else:
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<a href="{}" target="_blank" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">📄 Download License</a>'
                    '</div>',
                    obj.business_license.url
                )
        return format_html('<span style="color: #999;">No business license uploaded</span>')
    business_license_preview.short_description = 'Business License Preview'

    def id_proof_preview(self, obj):
        if obj.id_proof:
            if obj.id_proof.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" /><br>'
                    '<a href="{}" target="_blank" style="margin-top: 5px; display: inline-block;">📄 View Full Size</a>'
                    '</div>',
                    obj.id_proof.url, obj.id_proof.url
                )
            else:
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<a href="{}" target="_blank" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">📄 Download ID Proof</a>'
                    '</div>',
                    obj.id_proof.url
                )
        return format_html('<span style="color: #999;">No ID proof uploaded</span>')
    id_proof_preview.short_description = 'ID Proof Preview'

    def utility_bill_preview(self, obj):
        if obj.utility_bill:
            if obj.utility_bill.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" /><br>'
                    '<a href="{}" target="_blank" style="margin-top: 5px; display: inline-block;">📄 View Full Size</a>'
                    '</div>',
                    obj.utility_bill.url, obj.utility_bill.url
                )
            else:
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<a href="{}" target="_blank" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">📄 Download Utility Bill</a>'
                    '</div>',
                    obj.utility_bill.url
                )
        return format_html('<span style="color: #999;">No utility bill uploaded</span>')
    utility_bill_preview.short_description = 'Utility Bill Preview'

    # Admin Actions
    def approve_verification(self, request, queryset):
        from django.utils import timezone
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        updated = 0
        for station_owner in queryset:
            if station_owner.verification_status != 'verified':
                station_owner.verification_status = 'verified'
                station_owner.verified_at = timezone.now()
                station_owner.save()
                updated += 1

                # Send verification email
                try:
                    html_content = render_to_string('station_owner_verification_email.html', {
                        'station_owner': station_owner
                    })

                    email = EmailMultiAlternatives(
                        '[MengedMate] Station Owner Verification Approved',
                        'Your station owner verification has been approved.',
                        settings.DEFAULT_FROM_EMAIL,
                        [station_owner.user.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()
                except Exception as e:
                    pass  # Continue even if email fails

        self.message_user(request, f'{updated} station owner(s) successfully verified.')
    approve_verification.short_description = "✅ Approve selected station owners"

    def reject_verification(self, request, queryset):
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        updated = 0
        for station_owner in queryset:
            if station_owner.verification_status != 'rejected':
                station_owner.verification_status = 'rejected'
                station_owner.verified_at = None
                station_owner.save()
                updated += 1

                # Send rejection email
                try:
                    html_content = render_to_string('station_owner_verification_email.html', {
                        'station_owner': station_owner
                    })

                    email = EmailMultiAlternatives(
                        '[MengedMate] Station Owner Verification - Additional Information Required',
                        'Additional information is required for your station owner verification.',
                        settings.DEFAULT_FROM_EMAIL,
                        [station_owner.user.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()
                except Exception as e:
                    pass  # Continue even if email fails

        self.message_user(request, f'{updated} station owner(s) marked as requiring additional information.')
    reject_verification.short_description = "❌ Request additional information"

    def mark_pending(self, request, queryset):
        updated = queryset.update(verification_status='pending', verified_at=None)
        self.message_user(request, f'{updated} station owner(s) marked as pending verification.')
    mark_pending.short_description = "⏳ Mark as pending verification"

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
