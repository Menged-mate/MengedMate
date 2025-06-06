from django.contrib import admin
from .models import DocumentationSection, APIEndpoint, TechnologyComponent


@admin.register(DocumentationSection)
class DocumentationSectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'section_type', 'order', 'is_active', 'updated_at']
    list_filter = ['section_type', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    ordering = ['order', 'title']
    list_editable = ['order', 'is_active']


@admin.register(APIEndpoint)
class APIEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'method', 'endpoint', 'category', 'authentication_required', 'order', 'is_active']
    list_filter = ['method', 'category', 'authentication_required', 'is_active']
    search_fields = ['name', 'endpoint', 'description']
    ordering = ['category', 'order', 'name']
    list_editable = ['order', 'is_active']


@admin.register(TechnologyComponent)
class TechnologyComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'component_type', 'version', 'is_active', 'updated_at']
    list_filter = ['component_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'purpose']
    ordering = ['component_type', 'name']
    list_editable = ['is_active']
