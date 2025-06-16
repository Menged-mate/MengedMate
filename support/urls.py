from django.urls import path
from .views import (
    SupportTicketCreateView,
    UserSupportTicketsView,
    FAQListView,
    FAQDetailView
)

app_name = 'support'

urlpatterns = [
    path('tickets/', SupportTicketCreateView.as_view(), name='create-ticket'),
    path('tickets/my/', UserSupportTicketsView.as_view(), name='my-tickets'),
    
    path('faq/', FAQListView.as_view(), name='faq-list'),
    path('faq/<int:faq_id>/', FAQDetailView.as_view(), name='faq-detail'),
]
