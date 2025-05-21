from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from authentication.authentication import AnonymousAuthentication, TokenAuthentication
from rest_framework.authentication import SessionAuthentication

class HomeView(TemplateView):
    """
    View for the home page with the map.
    """
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_base_url'] = settings.API_BASE_URL if hasattr(settings, 'API_BASE_URL') else ''
        context['google_maps_api_key'] = settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'GOOGLE_MAPS_API_KEY') else ''
        return context

class AppConfigView(APIView):
    """
    API view for getting app configuration.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    def get(self, request):
        """
        Return app configuration.
        """
        config = {
            'app_name': 'MengedMate',
            'version': '1.0.0',
            'map': {
                'default_center': {
                    'lat': 38.9072,
                    'lng': -77.0369
                },
                'default_zoom': 13,
                'max_zoom': 18,
                'min_zoom': 3
            },
            'connector_types': [
                {'id': 'type1', 'name': 'Type 1 (J1772)', 'icon': 'type1'},
                {'id': 'type2', 'name': 'Type 2 (Mennekes)', 'icon': 'type2'},
                {'id': 'ccs1', 'name': 'CCS Combo 1', 'icon': 'ccs1'},
                {'id': 'ccs2', 'name': 'CCS Combo 2', 'icon': 'ccs2'},
                {'id': 'chademo', 'name': 'CHAdeMO', 'icon': 'chademo'},
                {'id': 'tesla', 'name': 'Tesla', 'icon': 'tesla'},
                {'id': 'other', 'name': 'Other', 'icon': 'other'}
            ],
            'features': {
                'favorites': True,
                'search': True,
                'filters': True,
                'directions': True,
                'ratings': True
            }
        }
        return Response(config)
