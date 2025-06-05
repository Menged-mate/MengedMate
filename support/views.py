from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .models import SupportTicket, FAQ
from .serializers import SupportTicketSerializer, FAQSerializer
from authentication.authentication import TokenAuthentication
from rest_framework.authentication import SessionAuthentication


class SupportTicketCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            data = request.data.copy()
            data['user'] = request.user.id
            data['email'] = request.user.email

            serializer = SupportTicketSerializer(data=data)
            if serializer.is_valid():
                ticket = serializer.save()

                # Send email notification to admin
                try:
                    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@evmeri.com')
                    send_mail(
                        subject=f'New Support Ticket #{ticket.id}: {ticket.subject}',
                        message=f'''
New support ticket submitted:

Ticket ID: #{ticket.id}
User: {ticket.user.email}
Subject: {ticket.subject}
Description: {ticket.description}

Please log in to the admin panel to respond.
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
                    'ticket_id': ticket.id
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
            tickets = SupportTicket.objects.filter(user=request.user)
            serializer = SupportTicketSerializer(tickets, many=True)

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

            queryset = FAQ.objects.filter(is_active=True)

            if category:
                queryset = queryset.filter(category=category)

            if search:
                queryset = queryset.filter(
                    Q(question__icontains=search) | Q(answer__icontains=search)
                )

            # Group FAQs by category
            categories = {}
            for faq in queryset:
                if faq.category not in categories:
                    categories[faq.category] = {
                        'category': faq.category,
                        'category_display': faq.get_category_display(),
                        'faqs': []
                    }
                categories[faq.category]['faqs'].append({
                    'id': faq.id,
                    'question': faq.question,
                    'answer': faq.answer,
                    'view_count': faq.view_count
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
            faq = FAQ.objects.get(id=faq_id, is_active=True)
            faq.increment_view_count()

            serializer = FAQSerializer(faq)
            return Response({
                'success': True,
                'faq': serializer.data
            })

        except FAQ.DoesNotExist:
            return Response({
                'success': False,
                'message': 'FAQ not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
