from django.db import models
from django.utils.translation import gettext_lazy as _


class DocumentationSection(models.Model):
    """Model to store different sections of technical documentation"""

    SECTION_TYPES = [
        ('overview', 'System Overview'),
        ('architecture', 'System Architecture'),
        ('tech_stack', 'Technology Stack'),
        ('deployment', 'Deployment Instructions'),
        ('database', 'Database Design'),
        ('security', 'Security & Authentication'),
        ('integrations', 'Third-Party Integrations'),
        ('scaling', 'Scaling & Performance'),
        ('api_docs', 'API Documentation'),
        ('troubleshooting', 'Troubleshooting'),
    ]

    title = models.CharField(max_length=255)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, unique=True)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Documentation Section'
        verbose_name_plural = 'Documentation Sections'

    def __str__(self):
        return self.title


class APIEndpoint(models.Model):
    """Model to store API endpoint documentation"""

    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]

    name = models.CharField(max_length=255)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    endpoint = models.CharField(max_length=500)
    description = models.TextField()
    parameters = models.JSONField(default=dict, blank=True)
    request_example = models.TextField(blank=True)
    response_example = models.TextField(blank=True)
    authentication_required = models.BooleanField(default=True)
    category = models.CharField(max_length=100, default='General')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', 'name']
        verbose_name = 'API Endpoint'
        verbose_name_plural = 'API Endpoints'

    def __str__(self):
        return f"{self.method} {self.endpoint}"


class TechnologyComponent(models.Model):
    """Model to store information about technology components used"""

    COMPONENT_TYPES = [
        ('backend', 'Backend Framework'),
        ('frontend', 'Frontend Framework'),
        ('database', 'Database'),
        ('payment', 'Payment Gateway'),
        ('deployment', 'Deployment Platform'),
        ('monitoring', 'Monitoring Tool'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES)
    version = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    purpose = models.TextField()
    documentation_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['component_type', 'name']
        verbose_name = 'Technology Component'
        verbose_name_plural = 'Technology Components'

    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"
