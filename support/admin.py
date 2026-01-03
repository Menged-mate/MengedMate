from django.contrib import admin
from django.utils.html import format_html
from .models import SupportTicket, FAQ


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subject', 'user_email', 'status', 'priority',
        'created_at', 'has_screenshot'
    ]
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['subject', 'description', 'user__email', 'email']
    readonly_fields = ['created_at', 'updated_at', 'screenshot_preview']

    fieldsets = (
        ('Ticket Information', {
            'fields': ('subject', 'description', 'screenshot', 'screenshot_preview', 'user', 'email', 'phone_number')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def has_screenshot(self, obj):
        if obj.screenshot:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_screenshot.short_description = 'Screenshot'

    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="300" height="auto" style="border: 1px solid #ddd; border-radius: 4px;" />', obj.screenshot)
        return "No Screenshot"
    screenshot_preview.short_description = 'Screenshot Preview'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active', 'view_count', 'updated_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_active']
    readonly_fields = ['view_count', 'created_at', 'updated_at']

    fieldsets = (
        ('FAQ Content', {
            'fields': ('category', 'question', 'answer', 'order', 'is_active')
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
