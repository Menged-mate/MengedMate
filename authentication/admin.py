from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import CustomUser, Vehicle


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'full_name', 'is_staff', 'is_active', 'verification_status', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('last_login', 'date_joined')
    list_per_page = 25

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number', 'address', 'city', 'state', 'zip_code', 'profile_picture')}),
        (_('EV Details'), {'fields': ('ev_connector_type', 'ev_battery_capacity_kwh', 'active_vehicle')}),
        (_('Verification'), {'fields': ('is_verified', 'verification_code')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'

    def verification_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green; font-weight: bold;">✓ Verified</span>')
        else:
            return format_html('<span style="color: red;">✗ Unverified</span>')
    verification_status.short_description = 'Verification'


    save_on_top = True
    show_full_result_count = True


class VehicleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user_email', 'connector_type', 'battery_capacity_kwh',
                   'is_primary', 'is_active', 'efficiency_rating', 'last_used_at')
    list_filter = ('connector_type', 'is_primary', 'is_active', 'make', 'year', 'preferred_charging_speed')
    search_fields = ('name', 'make', 'model', 'user__email', 'user__first_name', 'user__last_name', 'license_plate')
    ordering = ('-is_primary', '-last_used_at', '-created_at')
    readonly_fields = ('total_charging_sessions', 'total_energy_charged_kwh', 'last_used_at',
                      'usable_battery_kwh', 'created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'name', 'make', 'model', 'year', 'color', 'license_plate', 'vehicle_image')
        }),
        (_('Battery & Charging'), {
            'fields': ('battery_capacity_kwh', 'usable_battery_kwh', 'connector_type',
                      'max_charging_speed_kw', 'preferred_charging_speed')
        }),
        (_('Performance'), {
            'fields': ('estimated_range_km', 'efficiency_kwh_per_100km')
        }),
        (_('Status & Preferences'), {
            'fields': ('is_primary', 'is_active', 'notes')
        }),
        (_('Usage Statistics'), {
            'fields': ('total_charging_sessions', 'total_energy_charged_kwh', 'last_used_at'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def display_name(self, obj):
        return obj.get_display_name()
    display_name.short_description = 'Vehicle'
    display_name.admin_order_field = 'name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Owner'
    user_email.admin_order_field = 'user__email'

    def efficiency_rating(self, obj):
        rating = obj.get_efficiency_rating()
        colors = {
            'Excellent': 'green',
            'Good': 'blue',
            'Average': 'orange',
            'Poor': 'red',
            'Unknown': 'gray'
        }
        color = colors.get(rating, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{rating}</span>')
    efficiency_rating.short_description = 'Efficiency'

    save_on_top = True
    show_full_result_count = True


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0
    fields = ('name', 'make', 'model', 'year', 'connector_type', 'is_primary', 'is_active')
    readonly_fields = ('created_at',)
    show_change_link = True



class CustomUserAdminWithVehicles(CustomUserAdmin):
    inlines = [VehicleInline]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj: 
            return fieldsets
        else:
            modified_fieldsets = []
            for name, options in fieldsets:
                if name == _('EV Details'):
                    fields = list(options['fields'])
                    if 'active_vehicle' in fields:
                        fields.remove('active_vehicle')
                    options = dict(options)
                    options['fields'] = tuple(fields)
                modified_fieldsets.append((name, options))
            return modified_fieldsets
        return fieldsets


admin.site.register(CustomUser, CustomUserAdminWithVehicles)
admin.site.register(Vehicle, VehicleAdmin)
