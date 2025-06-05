from django.core.management.base import BaseCommand
from support.models import FAQ


class Command(BaseCommand):
    help = 'Populate FAQ data'

    def handle(self, *args, **options):
        faqs = [
            # Charging FAQs
            {
                'category': 'charging',
                'question': 'How do I start a charging session?',
                'answer': 'To start a charging session, scan the QR code on the charging connector using the EVመሪ app, select your payment method, and follow the on-screen instructions.',
                'order': 1
            },
            {
                'category': 'charging',
                'question': 'How can I view my transaction history?',
                'answer': 'You can view your transaction history by going to your profile in the app and selecting "Transaction History" or "Charging History".',
                'order': 2
            },
            {
                'category': 'charging',
                'question': 'What do I do if a charging station doesn\'t work?',
                'answer': 'If a charging station is not working, please report it through the app by tapping on the station and selecting "Report Issue". You can also contact our support team.',
                'order': 3
            },
            
            # Payments & Wallet FAQs
            {
                'category': 'payments',
                'question': 'What payment methods are accepted?',
                'answer': 'We accept payments through Chapa, which supports mobile money, bank transfers, and card payments. You can pay directly through the app.',
                'order': 1
            },
            {
                'category': 'payments',
                'question': 'How do I get a refund for a failed charging session?',
                'answer': 'If your payment was processed but charging failed, refunds are automatically processed within 24-48 hours. Contact support if you don\'t receive your refund.',
                'order': 2
            },
            {
                'category': 'payments',
                'question': 'Can I save my payment information?',
                'answer': 'Yes, you can save your payment information securely in the app for faster checkout during future charging sessions.',
                'order': 3
            },
            
            # Station Locations FAQs
            {
                'category': 'stations',
                'question': 'How do I find charging stations near me?',
                'answer': 'Open the EVመሪ app and use the map view to see all nearby charging stations. You can also use the search function to find stations in specific areas.',
                'order': 1
            },
            {
                'category': 'stations',
                'question': 'How do I know if a station is available?',
                'answer': 'The app shows real-time availability for each charging station. Green indicators mean available, yellow means partially occupied, and red means fully occupied.',
                'order': 2
            },
            {
                'category': 'stations',
                'question': 'Can I reserve a charging station?',
                'answer': 'Currently, reservations are not available, but this feature is coming soon. Stations operate on a first-come, first-served basis.',
                'order': 3
            },
            
            # Account & Settings FAQs
            {
                'category': 'account',
                'question': 'How do I update my profile information?',
                'answer': 'Go to Settings > Profile in the app to update your personal information, vehicle details, and preferences.',
                'order': 1
            },
            {
                'category': 'account',
                'question': 'How do I change my password?',
                'answer': 'Go to Settings > Change Password in the app, or use the "Forgot Password" option on the login screen.',
                'order': 2
            },
            {
                'category': 'account',
                'question': 'Can I have multiple vehicle profiles?',
                'answer': 'Yes, you can add multiple vehicles to your profile and switch between them to get personalized charging recommendations.',
                'order': 3
            },
        ]

        for faq_data in faqs:
            faq, created = FAQ.objects.get_or_create(
                category=faq_data['category'],
                question=faq_data['question'],
                defaults={
                    'answer': faq_data['answer'],
                    'order': faq_data['order']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created FAQ: {faq.question}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'FAQ already exists: {faq.question}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated FAQ data')
        )
