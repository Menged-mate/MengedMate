from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from charging_stations.models import ChargingStation, ChargingConnector, StationOwner
from ocpp_integration.services import OCPPIntegrationService
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Test OCPP integration with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-sample-data',
            action='store_true',
            help='Create sample charging station and user data',
        )
        parser.add_argument(
            '--sync-station',
            type=str,
            help='Sync a specific station by ID to OCPP',
        )
        parser.add_argument(
            '--test-charging',
            action='store_true',
            help='Test the complete charging flow',
        )

    def handle(self, *args, **options):
        if options['create_sample_data']:
            self.create_sample_data()

        if options['sync_station']:
            self.sync_station(options['sync_station'])

        if options['test_charging']:
            self.test_charging_flow()

    def create_sample_data(self):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create a test user
        user, created = User.objects.get_or_create(
            email='testuser@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'User',
                'is_verified': True
            }
        )
        if created:
            user.set_password('testpassword123')
            user.save()
            self.stdout.write(f'Created test user: {user.email}')
        else:
            self.stdout.write(f'Test user already exists: {user.email}')

        # Create a station owner
        owner, created = StationOwner.objects.get_or_create(
            user=user,
            defaults={
                'company_name': 'Test Charging Company',
                'contact_phone': '+251911234567',
                'verification_status': 'verified',
                'is_profile_completed': True
            }
        )
        if created:
            self.stdout.write(f'Created station owner: {owner.company_name}')
        else:
            self.stdout.write(f'Station owner already exists: {owner.company_name}')

        # Create a charging station
        station, created = ChargingStation.objects.get_or_create(
            name='Test OCPP Station',
            defaults={
                'owner': owner,
                'address': '123 Test Street, Addis Ababa',
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'latitude': '9.0320',
                'longitude': '38.7469',
                'is_active': True,
                'is_public': True,
                'is_operational': True,
                'status': 'operational',
                'price_range': '$5.00-6.00/kWh'
            }
        )
        if created:
            self.stdout.write(f'Created charging station: {station.name}')

            # Create connectors
            connector1 = ChargingConnector.objects.create(
                station=station,
                connector_type='ccs2',
                power_kw=50.0,
                is_available=True,
                status='available'
            )

            connector2 = ChargingConnector.objects.create(
                station=station,
                connector_type='type2',
                power_kw=22.0,
                is_available=True,
                status='available'
            )

            self.stdout.write(f'Created connectors: CCS2 (50kW), Type2 (22kW)')
        else:
            self.stdout.write(f'Charging station already exists: {station.name}')

        self.stdout.write(self.style.SUCCESS('Sample data creation completed!'))

    def sync_station(self, station_id):
        try:
            station = ChargingStation.objects.get(id=station_id)
            self.stdout.write(f'Syncing station: {station.name}')

            ocpp_service = OCPPIntegrationService()
            result = ocpp_service.sync_station_to_ocpp(station)

            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'Station synced successfully: {result["data"]}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to sync station: {result["error"]}')
                )

        except ChargingStation.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Charging station with ID {station_id} not found')
            )

    def test_charging_flow(self):
        self.stdout.write(self.style.SUCCESS('Testing complete charging flow...'))

        try:
            # Get test data
            user = User.objects.get(email='testuser@example.com')
            station = ChargingStation.objects.get(name='Test OCPP Station')

            if not hasattr(station, 'ocpp_station'):
                self.stdout.write(
                    self.style.WARNING('Station not synced to OCPP. Syncing now...')
                )
                self.sync_station(str(station.id))

            ocpp_station = station.ocpp_station
            connector = ocpp_station.ocpp_connectors.first()

            if not connector:
                self.stdout.write(
                    self.style.ERROR('No OCPP connectors found for the station')
                )
                return

            # Test payment transaction ID
            payment_id = f'test_payment_{uuid.uuid4().hex[:8]}'

            self.stdout.write(f'Initiating charging session...')
            self.stdout.write(f'Station: {ocpp_station.station_id}')
            self.stdout.write(f'Connector: {connector.connector_id}')
            self.stdout.write(f'User: {user.email}')
            self.stdout.write(f'Payment ID: {payment_id}')

            ocpp_service = OCPPIntegrationService()

            # 1. Initiate charging
            result = ocpp_service.initiate_charging(
                station_id=ocpp_station.station_id,
                connector_id=connector.connector_id,
                user=user,
                payment_transaction_id=payment_id,
                owner_info={
                    'owner_id': str(station.owner.id),
                    'owner_name': station.owner.company_name
                }
            )

            if result['success']:
                session = result['charging_session']
                self.stdout.write(
                    self.style.SUCCESS(f'Charging session initiated: {session.transaction_id}')
                )

                # 2. Get session status
                self.stdout.write('Getting session status...')
                status_result = ocpp_service.get_session_data(session.transaction_id)

                if status_result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(f'Session status retrieved successfully')
                    )
                    if 'charging_session' in status_result:
                        updated_session = status_result['charging_session']
                        self.stdout.write(f'Status: {updated_session.status}')
                        self.stdout.write(f'Energy: {updated_session.energy_consumed_kwh} kWh')
                        self.stdout.write(f'Cost: ${updated_session.estimated_cost}')

                # 3. Stop charging
                self.stdout.write('Stopping charging session...')
                stop_result = ocpp_service.stop_charging(
                    transaction_id=session.transaction_id,
                    user_id=user.id
                )

                if stop_result['success']:
                    self.stdout.write(
                        self.style.SUCCESS('Charging session stopped successfully')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to stop charging: {stop_result["error"]}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to initiate charging: {result["error"]}')
                )

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Test user not found. Run with --create-sample-data first.')
            )
        except ChargingStation.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Test station not found. Run with --create-sample-data first.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during testing: {e}')
            )

        self.stdout.write(self.style.SUCCESS('Charging flow test completed!'))
