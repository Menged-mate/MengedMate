from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector, AppContent, StationReview, ReviewReply, PayoutMethod
from .admin_views import DatabaseBackupView, system_stats_view

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
                        '[evmeri] Station Owner Verification Approved',
                        'Your station owner verification has been approved.',
                        settings.DEFAULT_FROM_EMAIL,
                        [station_owner.user.email]
                    )
                    email.attach_alternative(html_content, "text/html")
                    email.send()

                    # Send real-time notification
                    from authentication.notifications import create_notification, Notification
                    create_notification(
                        user=station_owner.user,
                        notification_type=Notification.NotificationType.SYSTEM,
                        title='Account Verified Successfully!',
                        message='Congratulations! Your station owner account has been verified. You can now add and manage charging stations.',
                        link='/dashboard/stations'
                    )
                except Exception as e:
                    pass

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
                    pass 

        self.message_user(request, f'{updated} station owner(s) marked as requiring additional information.')
    reject_verification.short_description = "❌ Request additional information"

    def mark_pending(self, request, queryset):
        updated = queryset.update(verification_status='pending', verified_at=None)
        self.message_user(request, f'{updated} station owner(s) marked as pending verification.')
    mark_pending.short_description = "⏳ Mark as pending verification"

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_company', 'location_display', 'operational_status_badge', 'active_status_badge', 'connector_availability', 'connector_count')
    list_filter = ('status', 'is_active', 'city', 'state', 'country', 'owner')
    search_fields = ('name', 'address', 'city', 'owner__company_name')
    inlines = [ChargingConnectorInline, StationImageInline]
    readonly_fields = ('created_at', 'updated_at', 'available_connectors', 'total_connectors', 'map_preview')
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code', 'country', 'latitude', 'longitude', 'map_preview')
        }),
        ('Operational Status', {
            'fields': ('status', 'is_active', 'is_public', 'opening_hours'),
            'description': 'Control station availability and operational status'
        }),
        ('Connector Information', {
            'fields': ('available_connectors', 'total_connectors'),
            'classes': ('collapse',),
            'description': 'Connector counts are automatically updated'
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

    actions = ['mark_operational', 'mark_under_maintenance', 'mark_closed', 'activate_stations', 'deactivate_stations']

    def owner_company(self, obj):
        if obj.owner and obj.owner.verification_status == 'verified':
            return format_html('{} <span style="color: green;">✓</span>', obj.owner.company_name)
        return obj.owner.company_name if obj.owner else "N/A"
    owner_company.short_description = 'Owner'

    def location_display(self, obj):
        location = f"{obj.city}"
        if obj.state:
            location += f", {obj.state}"
        if obj.country:
            location += f" ({obj.country})"
        return location
    location_display.short_description = 'Location'

    def operational_status_badge(self, obj):
        status_colors = {
            'operational': '#28a745',
            'under_maintenance': '#ffc107',
            'closed': '#dc3545',
            'coming_soon': '#17a2b8'
        }
        status_icons = {
            'operational': '✅',
            'under_maintenance': '🔧',
            'closed': '🚫',
            'coming_soon': '🚧'
        }
        color = status_colors.get(obj.status, '#6c757d')
        icon = status_icons.get(obj.status, '❓')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    operational_status_badge.short_description = 'Operational Status'

    def active_status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">🟢 Active</span>')
        else:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">🔴 Inactive</span>')
    active_status_badge.short_description = 'Active Status'

    def connector_availability(self, obj):
        available = obj.available_connectors
        total = obj.total_connectors
        if available == 0:
            color = '#dc3545'  # Red
            icon = '🔴'
        elif available < total:
            color = '#ffc107'  # Yellow
            icon = '🟡'
        else:
            color = '#28a745'  # Green
            icon = '🟢'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}/{}</span>',
            color, icon, available, total
        )
    connector_availability.short_description = 'Connector Availability'

    def connector_count(self, obj):
        count = obj.connectors.count()
        return count
    connector_count.short_description = 'Total Connectors'

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

    # Admin Actions for Station Status Management
    def mark_operational(self, request, queryset):
        updated = queryset.update(status='operational')
        # Update available connectors for operational stations
        for station in queryset:
            station.update_connector_counts()
        self.message_user(request, f'{updated} station(s) marked as operational.')
    mark_operational.short_description = "✅ Mark as operational"

    def mark_under_maintenance(self, request, queryset):
        updated = queryset.update(status='under_maintenance', available_connectors=0)
        self.message_user(request, f'{updated} station(s) marked as under maintenance.')
    mark_under_maintenance.short_description = "🔧 Mark as under maintenance"

    def mark_closed(self, request, queryset):
        updated = queryset.update(status='closed', available_connectors=0)
        self.message_user(request, f'{updated} station(s) marked as closed.')
    mark_closed.short_description = "🚫 Mark as closed"

    def activate_stations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} station(s) activated.')
    activate_stations.short_description = "🟢 Activate stations"

    def deactivate_stations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} station(s) deactivated.')
    deactivate_stations.short_description = "🔴 Deactivate stations"

@admin.register(ChargingConnector)
class ChargingConnectorAdmin(admin.ModelAdmin):
    list_display = ('connector_type_display', 'station_name', 'power_kw', 'quantity_display', 'availability_status', 'status_badge')
    list_filter = ('connector_type', 'status', 'is_available', 'station__city', 'station__country')
    search_fields = ('station__name', 'connector_type', 'station__city')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('station', 'connector_type', 'power_kw')
        }),
        ('Availability', {
            'fields': ('quantity', 'available_quantity', 'is_available', 'status')
        }),
        ('Pricing', {
            'fields': ('price_per_kwh',)
        }),
        ('Additional Information', {
            'fields': ('description',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_available', 'mark_unavailable', 'mark_out_of_order', 'mark_maintenance']

    def connector_type_display(self, obj):
        return obj.get_connector_type_display()
    connector_type_display.short_description = 'Connector Type'

    def station_name(self, obj):
        return obj.station.name
    station_name.short_description = 'Station'

    def quantity_display(self, obj):
        return f"{obj.available_quantity}/{obj.quantity}"
    quantity_display.short_description = 'Available/Total'

    def availability_status(self, obj):
        if obj.is_available and obj.available_quantity > 0:
            return format_html('<span style="color: green; font-weight: bold;">🟢 Available</span>')
        elif obj.available_quantity == 0:
            return format_html('<span style="color: red; font-weight: bold;">🔴 All Busy</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">🔴 Unavailable</span>')
    availability_status.short_description = 'Availability'

    def status_badge(self, obj):
        status_colors = {
            'available': '#28a745',
            'occupied': '#ffc107',
            'out_of_order': '#dc3545',
            'maintenance': '#6c757d'
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    # Admin Actions
    def mark_available(self, request, queryset):
        updated = queryset.update(is_available=True, status='available')
        self.message_user(request, f'{updated} connector(s) marked as available.')
    mark_available.short_description = "🟢 Mark as available"

    def mark_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False, available_quantity=0)
        self.message_user(request, f'{updated} connector(s) marked as unavailable.')
    mark_unavailable.short_description = "🔴 Mark as unavailable"

    def mark_out_of_order(self, request, queryset):
        updated = queryset.update(is_available=False, status='out_of_order', available_quantity=0)
        self.message_user(request, f'{updated} connector(s) marked as out of order.')
    mark_out_of_order.short_description = "⚠️ Mark as out of order"

    def mark_maintenance(self, request, queryset):
        updated = queryset.update(is_available=False, status='maintenance', available_quantity=0)
        self.message_user(request, f'{updated} connector(s) marked as under maintenance.')
    mark_maintenance.short_description = "🔧 Mark as under maintenance"


@admin.register(AppContent)
class AppContentAdmin(admin.ModelAdmin):
    list_display = ('content_type_display', 'title', 'version', 'is_active', 'updated_at')
    list_filter = ('content_type', 'is_active', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('content_type', 'title', 'version', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def content_type_display(self, obj):
        return obj.get_content_type_display()
    content_type_display.short_description = 'Content Type'


@admin.register(StationReview)
class StationReviewAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'station_name', 'rating_display', 'is_verified_review', 'is_active', 'created_at')
    list_filter = ('rating', 'is_verified_review', 'is_active', 'created_at', 'station__city')
    search_fields = ('user__email', 'station__name', 'review_text')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'station', 'rating', 'review_text')
        }),
        ('Detailed Ratings', {
            'fields': ('charging_speed_rating', 'location_rating', 'amenities_rating'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_verified_review', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    list_per_page = 25
    save_on_top = True

    actions = ['mark_as_verified', 'mark_as_unverified', 'activate_reviews', 'deactivate_reviews']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def station_name(self, obj):
        return obj.station.name
    station_name.short_description = 'Station'

    def rating_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span> <span style="color: #666;">({}/5)</span>',
            stars, obj.rating
        )
    rating_display.short_description = 'Rating'

    # Admin Actions
    def mark_as_verified(self, request, queryset):
        updated = 0
        for review in queryset:
            if not review.is_verified_review:
                review.is_verified_review = True
                review.save()  # This will trigger the notification in the model's save method
                updated += 1

        self.message_user(request, f'{updated} review(s) marked as verified.')
    mark_as_verified.short_description = "✅ Mark as verified reviews"

    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(is_verified_review=False)
        self.message_user(request, f'{updated} review(s) marked as unverified.')
    mark_as_unverified.short_description = "❌ Mark as unverified reviews"

    def activate_reviews(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} review(s) activated.')
    activate_reviews.short_description = "🔄 Activate reviews"

    def deactivate_reviews(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} review(s) deactivated.')
    deactivate_reviews.short_description = "🚫 Deactivate reviews"


# Custom Admin Site with additional functionality
class EvmeriAdminSite(admin.AdminSite):
    site_header = 'evmeri Administration'
    site_title = 'evmeri Admin'
    index_title = 'Welcome to evmeri Administration'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('database-backup/', DatabaseBackupView.as_view(), name='database_backup'),
            path('system-stats/', system_stats_view, name='system_stats'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        """Custom admin index with additional links"""
        extra_context = extra_context or {}
        extra_context['custom_links'] = [
            {
                'title': '🗄️ Database Backup',
                'url': 'admin:database_backup',
                'description': 'Create and manage database backups'
            },
            {
                'title': '📊 System Statistics',
                'url': 'admin:system_stats',
                'description': 'View system statistics and metrics'
            }
        ]
        return super().index(request, extra_context)


# Create custom admin site instance
admin_site = EvmeriAdminSite(name='evmeri_admin')

# Register models with custom admin site
admin_site.register(StationOwner, StationOwnerAdmin)
admin_site.register(ChargingStation, ChargingStationAdmin)
admin_site.register(ChargingConnector, ChargingConnectorAdmin)
admin_site.register(AppContent, AppContentAdmin)
admin_site.register(StationReview, StationReviewAdmin)


@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ('review_info', 'station_owner_name', 'reply_text_preview', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'station_owner__company_name')
    search_fields = ('review__station__name', 'station_owner__company_name', 'reply_text')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('review', 'station_owner', 'reply_text')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def review_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>Review by: {} ({}⭐)</small>',
            obj.review.station.name,
            f"{obj.review.user.first_name} {obj.review.user.last_name}".strip() or obj.review.user.email,
            obj.review.rating
        )
    review_info.short_description = 'Review Information'

    def station_owner_name(self, obj):
        return obj.station_owner.company_name
    station_owner_name.short_description = 'Station Owner'

    def reply_text_preview(self, obj):
        if len(obj.reply_text) > 50:
            return obj.reply_text[:50] + "..."
        return obj.reply_text
    reply_text_preview.short_description = 'Reply Text'


# Register ReviewReply with custom admin site
admin_site.register(ReviewReply, ReviewReplyAdmin)


@admin.register(PayoutMethod)
class PayoutMethodAdmin(admin.ModelAdmin):
    list_display = ('station_owner_name', 'method_type_display', 'masked_details_display', 'is_default', 'is_verified', 'is_active', 'created_at')
    list_filter = ('method_type', 'is_default', 'is_verified', 'is_active', 'created_at')
    search_fields = ('station_owner__company_name', 'station_owner__user__email', 'account_holder_name', 'bank_name')
    readonly_fields = ('created_at', 'updated_at', 'masked_details_display')
    fieldsets = (
        (None, {
            'fields': ('station_owner', 'method_type', 'is_default', 'is_verified', 'is_active')
        }),
        ('Account Details', {
            'fields': ('account_holder_name',)
        }),
        ('Bank Account Details', {
            'fields': ('bank_name', 'account_number', 'routing_number', 'swift_code'),
            'classes': ('collapse',),
        }),
        ('Card Details', {
            'fields': ('card_number', 'card_type', 'expiry_month', 'expiry_year'),
            'classes': ('collapse',),
        }),
        ('Mobile Money Details', {
            'fields': ('phone_number', 'provider'),
            'classes': ('collapse',),
        }),
        ('PayPal Details', {
            'fields': ('paypal_email',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    list_per_page = 25

    actions = ['verify_methods', 'unverify_methods', 'activate_methods', 'deactivate_methods']

    def station_owner_name(self, obj):
        return obj.station_owner.company_name
    station_owner_name.short_description = 'Station Owner'

    def method_type_display(self, obj):
        return obj.get_method_type_display()
    method_type_display.short_description = 'Method Type'

    def masked_details_display(self, obj):
        details = obj.get_masked_details()
        return f"{details['type']}: {details['details']}"
    masked_details_display.short_description = 'Details'

    # Admin Actions
    def verify_methods(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} payout method(s) verified.')
    verify_methods.short_description = "✅ Verify selected methods"

    def unverify_methods(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} payout method(s) unverified.')
    unverify_methods.short_description = "❌ Unverify selected methods"

    def activate_methods(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} payout method(s) activated.')
    activate_methods.short_description = "🟢 Activate methods"

    def deactivate_methods(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} payout method(s) deactivated.')
    deactivate_methods.short_description = "🔴 Deactivate methods"
