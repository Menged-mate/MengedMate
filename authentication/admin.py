from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom user model."""
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
        (_('EV Details'), {'fields': ('ev_connector_type', 'ev_battery_capacity_kwh')}),
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

    # Jazzmin specific settings
    save_on_top = True
    show_full_result_count = True


admin.site.register(CustomUser, CustomUserAdmin)
