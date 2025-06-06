from django.urls import path
from . import views

app_name = 'docs'

urlpatterns = [
    path('', views.DocumentationHomeView.as_view(), name='home'),
    path('architecture/', views.SystemArchitectureView.as_view(), name='architecture'),
    path('api/', views.APIDocumentationView.as_view(), name='api'),
    path('database/', views.DatabaseSchemaView.as_view(), name='database'),
    path('deployment/', views.DeploymentGuideView.as_view(), name='deployment'),
    path('security/', views.SecurityDocumentationView.as_view(), name='security'),
    path('integrations/', views.IntegrationsView.as_view(), name='integrations'),
    path('troubleshooting/', views.TroubleshootingView.as_view(), name='troubleshooting'),
    path('api/endpoint/<int:endpoint_id>/', views.api_endpoint_detail, name='api_endpoint_detail'),
]
