from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import SupportTicket, FAQ, Announcement
from .serializers import SupportTicketSerializer, FAQSerializer
from unittest.mock import patch

User = get_user_model()


class SupportTicketModelTests(TestCase):
    """Test cases for SupportTicket model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.ticket_data = {
            'user': self.user,
            'subject': 'Test Support Ticket',
            'description': 'This is a test support ticket description.',
            'category': 'technical',
            'priority': 'medium'
        }

    def test_create_support_ticket(self):
        """Test creating a support ticket"""
        ticket = SupportTicket.objects.create(**self.ticket_data)
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.subject, 'Test Support Ticket')
        self.assertEqual(ticket.category, 'technical')
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.priority, 'medium')

    def test_ticket_string_representation(self):
        """Test ticket string representation"""
        ticket = SupportTicket.objects.create(**self.ticket_data)
        expected = f"#{ticket.ticket_number} - Test Support Ticket"
        self.assertEqual(str(ticket), expected)

    def test_ticket_number_generation(self):
        """Test automatic ticket number generation"""
        ticket = SupportTicket.objects.create(**self.ticket_data)
        self.assertIsNotNone(ticket.ticket_number)
        self.assertTrue(ticket.ticket_number.startswith('TKT'))

    def test_ticket_status_transitions(self):
        """Test ticket status transitions"""
        ticket = SupportTicket.objects.create(**self.ticket_data)

        # Test status change to in_progress
        ticket.status = 'in_progress'
        ticket.save()
        self.assertEqual(ticket.status, 'in_progress')

        # Test status change to resolved
        ticket.status = 'resolved'
        ticket.save()
        self.assertEqual(ticket.status, 'resolved')
        self.assertIsNotNone(ticket.resolved_at)

        # Test status change to closed
        ticket.status = 'closed'
        ticket.save()
        self.assertEqual(ticket.status, 'closed')

    def test_ticket_priority_validation(self):
        """Test ticket priority validation"""
        # Valid priority
        ticket = SupportTicket.objects.create(**self.ticket_data)
        ticket.full_clean()  # Should not raise ValidationError

        # Invalid priority
        invalid_data = self.ticket_data.copy()
        invalid_data['priority'] = 'invalid_priority'
        with self.assertRaises(ValidationError):
            ticket = SupportTicket(**invalid_data)
            ticket.full_clean()


class FAQModelTests(TestCase):
    """Test cases for FAQ model"""

    def setUp(self):
        self.faq_data = {
            'question': 'How do I charge my electric vehicle?',
            'answer': 'To charge your electric vehicle, follow these steps...',
            'category': 'charging',
            'order': 1
        }

    def test_create_faq(self):
        """Test creating an FAQ"""
        faq = FAQ.objects.create(**self.faq_data)
        self.assertEqual(faq.question, 'How do I charge my electric vehicle?')
        self.assertEqual(faq.category, 'charging')
        self.assertTrue(faq.is_published)
        self.assertEqual(faq.order, 1)

    def test_faq_string_representation(self):
        """Test FAQ string representation"""
        faq = FAQ.objects.create(**self.faq_data)
        self.assertEqual(str(faq), 'How do I charge my electric vehicle?')

    def test_faq_ordering(self):
        """Test FAQ ordering"""
        faq1 = FAQ.objects.create(
            question='First Question',
            answer='First Answer',
            category='general',
            order=1
        )
        faq2 = FAQ.objects.create(
            question='Second Question',
            answer='Second Answer',
            category='general',
            order=2
        )

        faqs = FAQ.objects.filter(category='general').order_by('order')
        self.assertEqual(list(faqs), [faq1, faq2])


class AnnouncementModelTests(TestCase):
    """Test cases for Announcement model"""

    def setUp(self):
        self.announcement_data = {
            'title': 'New Feature Release',
            'content': 'We are excited to announce a new feature...',
            'announcement_type': 'feature',
            'priority': 'medium'
        }

    def test_create_announcement(self):
        """Test creating an announcement"""
        announcement = Announcement.objects.create(**self.announcement_data)
        self.assertEqual(announcement.title, 'New Feature Release')
        self.assertEqual(announcement.announcement_type, 'feature')
        self.assertTrue(announcement.is_active)
        self.assertEqual(announcement.priority, 'medium')

    def test_announcement_string_representation(self):
        """Test announcement string representation"""
        announcement = Announcement.objects.create(**self.announcement_data)
        self.assertEqual(str(announcement), 'New Feature Release')

    def test_announcement_activation(self):
        """Test announcement activation/deactivation"""
        announcement = Announcement.objects.create(**self.announcement_data)

        # Test deactivation
        announcement.is_active = False
        announcement.save()
        self.assertFalse(announcement.is_active)

        # Test reactivation
        announcement.is_active = True
        announcement.save()
        self.assertTrue(announcement.is_active)


class SupportTicketAPITests(APITestCase):
    """Test cases for SupportTicket API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

        self.ticket_data = {
            'subject': 'Test API Ticket',
            'description': 'This is a test ticket created via API.',
            'category': 'technical',
            'priority': 'medium'
        }

    def test_create_ticket_authenticated(self):
        """Test creating ticket as authenticated user"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = self.client.post('/api/support/tickets/', self.ticket_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['subject'], 'Test API Ticket')
        self.assertEqual(response.data['user'], self.user.id)

    def test_create_ticket_unauthenticated(self):
        """Test creating ticket without authentication"""
        response = self.client.post('/api/support/tickets/', self.ticket_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_user_tickets(self):
        """Test listing user's own tickets"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Create a ticket
        SupportTicket.objects.create(user=self.user, **self.ticket_data)

        response = self.client.get('/api/support/tickets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['subject'], 'Test API Ticket')

    def test_ticket_detail_access(self):
        """Test accessing ticket detail"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        ticket = SupportTicket.objects.create(user=self.user, **self.ticket_data)

        response = self.client.get(f'/api/support/tickets/{ticket.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], 'Test API Ticket')

    def test_update_ticket_status(self):
        """Test updating ticket status"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        ticket = SupportTicket.objects.create(user=self.user, **self.ticket_data)

        update_data = {'status': 'resolved'}
        response = self.client.patch(f'/api/support/tickets/{ticket.id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'resolved')


class FAQAPITests(APITestCase):
    """Test cases for FAQ API endpoints"""

    def setUp(self):
        self.client = APIClient()

        # Create test FAQs
        self.faq1 = FAQ.objects.create(
            question='How do I register?',
            answer='To register, go to the registration page...',
            category='account',
            order=1
        )
        self.faq2 = FAQ.objects.create(
            question='How do I find charging stations?',
            answer='You can find charging stations using the map...',
            category='charging',
            order=1
        )

    def test_list_all_faqs(self):
        """Test listing all published FAQs"""
        response = self.client.get('/api/support/faqs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_faqs_by_category(self):
        """Test filtering FAQs by category"""
        response = self.client.get('/api/support/faqs/?category=charging')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['category'], 'charging')

    def test_faq_detail_access(self):
        """Test accessing FAQ detail"""
        response = self.client.get(f'/api/support/faqs/{self.faq1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question'], 'How do I register?')

    def test_unpublished_faq_not_listed(self):
        """Test that unpublished FAQs are not listed"""
        # Create unpublished FAQ
        FAQ.objects.create(
            question='Unpublished FAQ',
            answer='This should not appear',
            category='general',
            is_published=False
        )

        response = self.client.get('/api/support/faqs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only published FAQs
