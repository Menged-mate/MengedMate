from django.core.management.base import BaseCommand
from docs.models import DocumentationSection, APIEndpoint, TechnologyComponent


class Command(BaseCommand):
    help = 'Populate documentation with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Populating documentation data...')
        
        # Create documentation sections
        self.create_documentation_sections()
        
        # Create technology components
        self.create_technology_components()
        
        # Create API endpoints
        self.create_api_endpoints()
        
        self.stdout.write(self.style.SUCCESS('Documentation data populated successfully!'))

    def create_documentation_sections(self):
        sections = [
            {
                'title': 'System Overview',
                'section_type': 'overview',
                'content': '''
# evmeri System Overview

evmeri is a comprehensive EV charging station management platform that connects EV drivers with charging stations and provides tools for station owners to manage their infrastructure.

## Key Components

- **Backend API**: Django REST Framework-based API
- **Web Frontend**: React.js application for station owners
- **Mobile App**: Flutter application for EV drivers
- **Payment System**: Chapa integration for payments
- **OCPP Integration**: Support for OCPP protocol
                ''',
                'order': 1
            },
            {
                'title': 'System Architecture',
                'section_type': 'architecture',
                'content': '''
# System Architecture

## High-Level Architecture

The evmeri platform follows a microservices-inspired architecture with clear separation of concerns:

### Backend Services
- **Authentication Service**: User management and authentication
- **Charging Stations Service**: Station management and discovery
- **Payments Service**: Payment processing and wallet management
- **OCPP Integration Service**: Communication with charging stations
- **Support Service**: Customer support and help desk

### Frontend Applications
- **Web Dashboard**: React.js application for station owners
- **Mobile App**: Flutter application for EV drivers

### External Integrations
- **Chapa Payment Gateway**: Payment processing
- **OpenStreetMap**: Mapping and location services
- **Email Services**: Notifications and communications

## Data Flow

1. **User Registration**: Users register through mobile app or web interface
2. **Station Discovery**: Mobile app queries backend for nearby stations
3. **Payment Processing**: QR code scanning initiates payment flow
4. **Charging Session**: OCPP protocol manages charging sessions
5. **Monitoring**: Real-time updates on charging status
                ''',
                'order': 2
            }
        ]
        
        for section_data in sections:
            section, created = DocumentationSection.objects.get_or_create(
                section_type=section_data['section_type'],
                defaults=section_data
            )
            if created:
                self.stdout.write(f'Created section: {section.title}')

    def create_technology_components(self):
        components = [
            {
                'name': 'Django',
                'component_type': 'backend',
                'version': '4.2',
                'description': 'High-level Python web framework for rapid development',
                'purpose': 'Backend API development with robust ORM and admin interface',
                'documentation_url': 'https://docs.djangoproject.com/'
            },
            {
                'name': 'Django REST Framework',
                'component_type': 'backend',
                'version': '3.14',
                'description': 'Powerful toolkit for building Web APIs in Django',
                'purpose': 'RESTful API development with serialization and authentication',
                'documentation_url': 'https://www.django-rest-framework.org/'
            },
            {
                'name': 'React.js',
                'component_type': 'frontend',
                'version': '18.x',
                'description': 'JavaScript library for building user interfaces',
                'purpose': 'Web frontend for station owners dashboard',
                'documentation_url': 'https://react.dev/'
            },
            {
                'name': 'Flutter',
                'component_type': 'frontend',
                'version': '3.x',
                'description': 'UI toolkit for building natively compiled applications',
                'purpose': 'Cross-platform mobile app for EV drivers',
                'documentation_url': 'https://flutter.dev/'
            },
            {
                'name': 'PostgreSQL',
                'component_type': 'database',
                'version': '13+',
                'description': 'Advanced open source relational database',
                'purpose': 'Primary database for storing application data',
                'documentation_url': 'https://www.postgresql.org/docs/'
            },
            {
                'name': 'Chapa',
                'component_type': 'payment',
                'version': 'v1',
                'description': 'Ethiopian payment gateway for online transactions',
                'purpose': 'Payment processing for charging sessions',
                'documentation_url': 'https://chapa.co/docs/'
            },
            {
                'name': 'Render',
                'component_type': 'deployment',
                'version': '',
                'description': 'Cloud platform for hosting web applications',
                'purpose': 'Backend API hosting and deployment',
                'documentation_url': 'https://render.com/docs'
            },
            {
                'name': 'Vercel',
                'component_type': 'deployment',
                'version': '',
                'description': 'Platform for frontend frameworks and static sites',
                'purpose': 'Web frontend hosting and deployment',
                'documentation_url': 'https://vercel.com/docs'
            }
        ]
        
        for component_data in components:
            component, created = TechnologyComponent.objects.get_or_create(
                name=component_data['name'],
                component_type=component_data['component_type'],
                defaults=component_data
            )
            if created:
                self.stdout.write(f'Created component: {component.name}')

    def create_api_endpoints(self):
        endpoints = [
            # Authentication endpoints
            {
                'name': 'User Registration',
                'method': 'POST',
                'endpoint': '/api/auth/register/',
                'description': 'Register a new user account',
                'category': 'Authentication',
                'authentication_required': False,
                'parameters': {
                    'email': {'type': 'string', 'required': True, 'description': 'User email address'},
                    'password1': {'type': 'string', 'required': True, 'description': 'Password'},
                    'password2': {'type': 'string', 'required': True, 'description': 'Password confirmation'}
                },
                'request_example': '''POST /api/auth/register/
{
    "email": "user@example.com",
    "password1": "securepassword123",
    "password2": "securepassword123"
}''',
                'response_example': '''HTTP 201 Created
{
    "success": true,
    "message": "Registration successful",
    "data": {
        "user": {
            "id": 1,
            "email": "user@example.com"
        },
        "token": "abc123token"
    }
}''',
                'order': 1
            },
            {
                'name': 'User Login',
                'method': 'POST',
                'endpoint': '/api/auth/login/',
                'description': 'Authenticate user and get access token',
                'category': 'Authentication',
                'authentication_required': False,
                'parameters': {
                    'email': {'type': 'string', 'required': True, 'description': 'User email address'},
                    'password': {'type': 'string', 'required': True, 'description': 'User password'}
                },
                'request_example': '''POST /api/auth/login/
{
    "email": "user@example.com",
    "password": "securepassword123"
}''',
                'response_example': '''HTTP 200 OK
{
    "success": true,
    "message": "Login successful",
    "data": {
        "token": "abc123token",
        "user": {
            "id": 1,
            "email": "user@example.com"
        }
    }
}''',
                'order': 2
            },
            # Charging Stations endpoints
            {
                'name': 'Get Nearby Stations',
                'method': 'GET',
                'endpoint': '/api/public/nearby-stations/',
                'description': 'Get charging stations near a specific location',
                'category': 'Charging Stations',
                'authentication_required': False,
                'parameters': {
                    'lat': {'type': 'float', 'required': True, 'description': 'Latitude coordinate'},
                    'lng': {'type': 'float', 'required': True, 'description': 'Longitude coordinate'},
                    'radius': {'type': 'integer', 'required': False, 'description': 'Search radius in kilometers (default: 10)'}
                },
                'request_example': '''GET /api/public/nearby-stations/?lat=9.0192&lng=38.7525&radius=10''',
                'response_example': '''HTTP 200 OK
{
    "success": true,
    "data": {
        "stations": [
            {
                "id": "uuid",
                "name": "Station Name",
                "latitude": 9.0192,
                "longitude": 38.7525,
                "distance": 2.5,
                "available_connectors": 3,
                "total_connectors": 5
            }
        ]
    }
}''',
                'order': 1
            }
        ]
        
        for endpoint_data in endpoints:
            endpoint, created = APIEndpoint.objects.get_or_create(
                method=endpoint_data['method'],
                endpoint=endpoint_data['endpoint'],
                defaults=endpoint_data
            )
            if created:
                self.stdout.write(f'Created endpoint: {endpoint.method} {endpoint.endpoint}')
