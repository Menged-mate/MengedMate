from django.urls import path
from .views import (
    SupportTicketCreateView,
    UserSupportTicketsView,
    FAQListView,
    FAQDetailView
)

app_name = 'support'

urlpatterns = [
    # Support Tickets
    path('tickets/', SupportTicketCreateView.as_view(), name='create-ticket'),
    path('tickets/my/', UserSupportTicketsView.as_view(), name='my-tickets'),
    
    # FAQ
    path('faq/', FAQListView.as_view(), name='faq-list'),
    path('faq/<int:faq_id>/', FAQDetailView.as_view(), name='faq-detail'),
]
