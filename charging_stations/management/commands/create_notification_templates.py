from django.core.management.base import BaseCommand
from charging_stations.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create default notification templates'

    def handle(self, *args, **options):
        templates = [
            {
                'template_type': 'booking_confirmed',
                'subject': 'Booking Confirmed - evmeri Charging Station',
                'email_body': '''
Dear {user_name},

Your booking has been confirmed!

Booking Details:
- Station: {station_name}
- Connector: {connector_type}
- Date & Time: {booking_time}
- Duration: {duration}

Please arrive on time for your charging session.

Best regards,
evmeri Team
                ''',
                'sms_body': 'Booking confirmed at {station_name} for {booking_time}. See you there! - evmeri'
            },
            {
                'template_type': 'payment_received',
                'subject': 'Payment Received - evmeri',
                'email_body': '''
Dear {user_name},

We have successfully received your payment.

Payment Details:
- Amount: {amount} ETB
- Transaction ID: {transaction_id}
- Date: {payment_date}
- Description: {description}

Thank you for using evmeri!

Best regards,
evmeri Team
                ''',
                'sms_body': 'Payment of {amount} ETB received. Transaction ID: {transaction_id}. Thank you! - evmeri'
            },
            {
                'template_type': 'session_started',
                'subject': 'Charging Session Started - evmeri',
                'email_body': '''
Dear {user_name},

Your charging session has started successfully.

Session Details:
- Station: {station_name}
- Connector: {connector_type}
- Start Time: {start_time}
- Estimated Duration: {duration}

You can monitor your charging progress in the evmeri app.

Best regards,
evmeri Team
                ''',
                'sms_body': 'Charging started at {station_name}. Monitor progress in the evmeri app. - evmeri'
            },
            {
                'template_type': 'session_completed',
                'subject': 'Charging Session Completed - evmeri',
                'email_body': '''
Dear {user_name},

Your charging session has been completed successfully.

Session Summary:
- Station: {station_name}
- Duration: {duration}
- Energy Delivered: {energy_kwh} kWh
- Total Cost: {total_cost} ETB
- End Time: {end_time}

Thank you for choosing evmeri for your charging needs!

Best regards,
evmeri Team
                ''',
                'sms_body': 'Charging completed! {energy_kwh} kWh delivered. Cost: {total_cost} ETB. Thank you! - evmeri'
            },
            {
                'template_type': 'maintenance_required',
                'subject': 'Maintenance Required - evmeri Station Alert',
                'email_body': '''
Dear Station Owner,

One of your charging stations requires maintenance attention.

Station Details:
- Station: {station_name}
- Issue: {issue_description}
- Priority: {priority}
- Reported: {report_time}

Please address this issue as soon as possible to ensure optimal service.

Best regards,
evmeri Support Team
                ''',
                'sms_body': 'Maintenance required at {station_name}: {issue_description}. Priority: {priority} - evmeri'
            },
            {
                'template_type': 'station_offline',
                'subject': 'Station Offline Alert - evmeri',
                'email_body': '''
Dear Station Owner,

Your charging station has gone offline.

Station Details:
- Station: {station_name}
- Last Online: {last_online}
- Duration Offline: {offline_duration}

Please check your station connectivity and contact support if needed.

Best regards,
evmeri Support Team
                ''',
                'sms_body': 'Station {station_name} is offline since {last_online}. Please check connectivity. - evmeri'
            },
            {
                'template_type': 'low_balance',
                'subject': 'Low Wallet Balance - evmeri',
                'email_body': '''
Dear {user_name},

Your evmeri wallet balance is running low.

Current Balance: {current_balance} ETB
Recommended Top-up: {recommended_amount} ETB

Please top up your wallet to continue enjoying uninterrupted charging services.

Best regards,
evmeri Team
                ''',
                'sms_body': 'Low wallet balance: {current_balance} ETB. Top up now to continue charging. - evmeri'
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults={
                    'subject': template_data['subject'],
                    'email_body': template_data['email_body'].strip(),
                    'sms_body': template_data['sms_body'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template_data["template_type"]}')
                )
            else:
                # Update existing template
                template.subject = template_data['subject']
                template.email_body = template_data['email_body'].strip()
                template.sms_body = template_data['sms_body']
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template_data["template_type"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nNotification templates setup complete!\n'
                f'Created: {created_count} templates\n'
                f'Updated: {updated_count} templates'
            )
        )
