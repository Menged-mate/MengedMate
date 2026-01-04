from utils.firestore_repo import firestore_repo
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from authentication.authentication import TokenAuthentication
from .serializers_firestore import FirestoreSupportTicketSerializer, FirestoreFAQSerializer

class SupportTicketCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            # Prepare data
            data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()
            # Auto-populate email from user
            if not data.get('email'):
                data['email'] = request.user.email
            
            # Handle serializer validation
            serializer = FirestoreSupportTicketSerializer(data=data)
            if serializer.is_valid():
                # Add system fields
                valid_data = serializer.validated_data
                valid_data['user_id'] = str(request.user.id)
                valid_data['email'] = request.user.email
                if not valid_data.get('phone_number'):
                    # Try to get from profile if not provided
                    profile = firestore_repo.get_user_profile(request.user.id)
                    if profile:
                        valid_data['phone_number'] = profile.get('phone_number')

                # Create in Firestore
                ticket = firestore_repo.create_ticket(valid_data)

                # Send email notification to admin (Keep existing logic)
                try:
                    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@evmeri.com')
                    send_mail(
                        subject=f'New Support Ticket (Firestore) #{ticket.get("id")}: {ticket.get("subject")}',
                        message=f'''
New support ticket submitted:

Ticket ID: #{ticket.get('id')}
User: {request.user.email}
Subject: {ticket.get('subject')}
Description: {ticket.get('description')}

Please check the Firestore console.
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Failed to send admin notification: {e}")

                return Response({
                    'success': True,
                    'message': 'Support ticket submitted successfully',
                    'ticket_id': ticket.get('id')
                }, status=status.HTTP_201_CREATED)

            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSupportTicketsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            tickets = firestore_repo.list_user_tickets(request.user.id)
            serializer = FirestoreSupportTicketSerializer(tickets, many=True)

            return Response({
                'success': True,
                'tickets': serializer.data
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FAQListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            category = request.query_params.get('category')
            search = request.query_params.get('search')
            
            # Fetch generic FAQs from Firestore
            # Optimally we cache this or use specific collection
            faqs = firestore_repo.list_faqs(category)
            
            # Filter in memory if search
            if search:
                search_lower = search.lower()
                faqs = [f for f in faqs if search_lower in f.get('question', '').lower() or search_lower in f.get('answer', '').lower()]

            # Group FAQs by category
            categories = {}
            for faq in faqs:
                cat = faq.get('category', 'general')
                if cat not in categories:
                    # Generic mapping for display names
                    display_names = {
                        'charging': 'Charging',
                        'payments': 'Payments & Wallet',
                        'stations': 'Station Locations',
                        'account': 'Account & Settings',
                        'general': 'General'
                    }
                    categories[cat] = {
                        'category': cat,
                        'category_display': display_names.get(cat, cat.title()),
                        'faqs': []
                    }
                categories[cat]['faqs'].append({
                    'id': faq.get('id'),
                    'question': faq.get('question'),
                    'answer': faq.get('answer'),
                    'view_count': faq.get('view_count', 0)
                })

            return Response({
                'success': True,
                'categories': list(categories.values())
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FAQDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, faq_id):
        try:
            faq = firestore_repo.get_faq(faq_id)
            if not faq:
                 return Response({
                'success': False,
                'message': 'FAQ not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
            # Increment view count (fire and forget update)
            # firestore_repo.increment_faq_view(faq_id) # TODO: Add helper if strict

            serializer = FirestoreFAQSerializer(faq)
            return Response({
                'success': True,
                'faq': serializer.data
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
