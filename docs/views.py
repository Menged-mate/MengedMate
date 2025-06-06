from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from .models import DocumentationSection, APIEndpoint, TechnologyComponent


class DocumentationHomeView(TemplateView):
    """Main documentation page"""
    template_name = 'docs/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sections'] = DocumentationSection.objects.filter(is_active=True)
        context['api_categories'] = APIEndpoint.objects.filter(is_active=True).values_list('category', flat=True).distinct()
        context['tech_components'] = TechnologyComponent.objects.filter(is_active=True)
        return context


class SystemArchitectureView(TemplateView):
    """System architecture documentation"""
    template_name = 'docs/architecture.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='architecture', is_active=True).first()
        context['tech_components'] = TechnologyComponent.objects.filter(is_active=True)
        return context


class APIDocumentationView(TemplateView):
    """API documentation page"""
    template_name = 'docs/api.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        endpoints = APIEndpoint.objects.filter(is_active=True)

        # Group endpoints by category
        categories = {}
        for endpoint in endpoints:
            if endpoint.category not in categories:
                categories[endpoint.category] = []
            categories[endpoint.category].append(endpoint)

        context['categories'] = categories
        return context


class DatabaseSchemaView(TemplateView):
    """Database schema documentation"""
    template_name = 'docs/database.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='database', is_active=True).first()
        return context


class DeploymentGuideView(TemplateView):
    """Deployment guide documentation"""
    template_name = 'docs/deployment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='deployment', is_active=True).first()
        return context


class SecurityDocumentationView(TemplateView):
    """Security and authentication documentation"""
    template_name = 'docs/security.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='security', is_active=True).first()
        return context


class IntegrationsView(TemplateView):
    """Third-party integrations documentation"""
    template_name = 'docs/integrations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='integrations', is_active=True).first()
        context['payment_components'] = TechnologyComponent.objects.filter(component_type='payment', is_active=True)
        return context


class TroubleshootingView(TemplateView):
    """Troubleshooting guide"""
    template_name = 'docs/troubleshooting.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = DocumentationSection.objects.filter(section_type='troubleshooting', is_active=True).first()
        return context


def api_endpoint_detail(request, endpoint_id):
    """API endpoint detail as JSON"""
    try:
        endpoint = APIEndpoint.objects.get(id=endpoint_id, is_active=True)
        data = {
            'name': endpoint.name,
            'method': endpoint.method,
            'endpoint': endpoint.endpoint,
            'description': endpoint.description,
            'parameters': endpoint.parameters,
            'request_example': endpoint.request_example,
            'response_example': endpoint.response_example,
            'authentication_required': endpoint.authentication_required,
        }
        return JsonResponse(data)
    except APIEndpoint.DoesNotExist:
        return JsonResponse({'error': 'Endpoint not found'}, status=404)
