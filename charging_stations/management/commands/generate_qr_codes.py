from django.core.management.base import BaseCommand
from charging_stations.models import ChargingConnector


class Command(BaseCommand):
    help = 'Generate QR codes for all charging connectors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Regenerate QR codes for connectors that already have them',
        )

    def handle(self, *args, **options):
        regenerate = options['regenerate']
        
        if regenerate:
            connectors = ChargingConnector.objects.all()
            self.stdout.write('Regenerating QR codes for all connectors...')
        else:
            connectors = ChargingConnector.objects.filter(qr_code_token__isnull=True)
            self.stdout.write('Generating QR codes for connectors without QR codes...')

        total_connectors = connectors.count()
        if total_connectors == 0:
            self.stdout.write(
                self.style.WARNING('No connectors found that need QR code generation.')
            )
            return

        self.stdout.write(f'Found {total_connectors} connectors to process.')

        success_count = 0
        error_count = 0

        for connector in connectors:
            try:
                if regenerate:
                    # Clear existing QR code data
                    connector.qr_code_token = None
                    connector.qr_code_image = None
                
                # Save will trigger QR code generation
                connector.save()
                
                success_count += 1
                self.stdout.write(
                    f'✓ Generated QR code for {connector.station.name} - {connector.get_connector_type_display()}'
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to generate QR code for {connector.station.name} - {connector.get_connector_type_display()}: {e}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nQR code generation completed!\n'
                f'Success: {success_count}\n'
                f'Errors: {error_count}\n'
                f'Total: {total_connectors}'
            )
        )
