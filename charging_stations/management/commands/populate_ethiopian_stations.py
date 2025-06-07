from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from charging_stations.models import StationOwner, ChargingStation, ChargingConnector
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with Ethiopian charging stations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if stations already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate Ethiopian charging stations...'))
        
        # Create or get admin user for station ownership
        admin_user, created = User.objects.get_or_create(
            email='admin@evmeri.com',
            defaults={
                'first_name': 'evmeri',
                'last_name': 'Admin',
                'is_verified': True,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Created admin user: {admin_user.email}')
        
        # Create or get station owner
        station_owner, created = StationOwner.objects.get_or_create(
            user=admin_user,
            defaults={
                'company_name': 'evmeri Network Ethiopia',
                'business_registration_number': 'ETH-EV-001',
                'verification_status': 'verified',
                'contact_phone': '+251911123456',
                'contact_email': 'stations@evmeri.com',
                'description': 'Leading EV charging network in Ethiopia',
                'is_profile_completed': True
            }
        )
        
        if created:
            self.stdout.write(f'Created station owner: {station_owner.company_name}')
        
        # Ethiopian charging stations data
        stations_data = [
            {
                'name': 'Bole International Airport Charging Hub',
                'address': 'Bole International Airport, Terminal Area',
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'latitude': Decimal('8.9806'),
                'longitude': Decimal('38.7992'),
                'description': 'Fast charging station at Ethiopia\'s main international airport. Perfect for travelers and airport staff.',
                'opening_hours': '24/7',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': True,
                'has_shopping': True,
                'rating': Decimal('4.5'),
                'rating_count': 23
            },
            {
                'name': 'Meskel Square Charging Station',
                'address': 'Meskel Square, Near Red Terror Martyrs Memorial',
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'latitude': Decimal('9.0120'),
                'longitude': Decimal('38.7634'),
                'description': 'Central charging location in the heart of Addis Ababa. Easy access to city center attractions.',
                'opening_hours': '6:00 AM - 10:00 PM',
                'has_restroom': False,
                'has_wifi': True,
                'has_restaurant': False,
                'has_shopping': False,
                'rating': Decimal('4.2'),
                'rating_count': 18
            },
            {
                'name': 'Mercato Market Charging Point',
                'address': 'Addis Mercato, Main Market Area',
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'latitude': Decimal('9.0370'),
                'longitude': Decimal('38.7468'),
                'description': 'Convenient charging while shopping at Africa\'s largest market. Secure parking available.',
                'opening_hours': '7:00 AM - 8:00 PM',
                'has_restroom': True,
                'has_wifi': False,
                'has_restaurant': True,
                'has_shopping': True,
                'rating': Decimal('3.8'),
                'rating_count': 12
            },
            {
                'name': 'Unity Park Charging Station',
                'address': 'Unity Park, National Palace Grounds',
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'latitude': Decimal('9.0370'),
                'longitude': Decimal('38.7578'),
                'description': 'Eco-friendly charging station near Unity Park. Perfect for tourists visiting the palace.',
                'opening_hours': '8:00 AM - 6:00 PM',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': False,
                'has_shopping': False,
                'rating': Decimal('4.7'),
                'rating_count': 31
            },
            {
                'name': 'Bahir Dar Lakeside Charging Hub',
                'address': 'Lake Tana Shore, Near Blue Nile Bridge',
                'city': 'Bahir Dar',
                'state': 'Amhara',
                'zip_code': '2000',
                'latitude': Decimal('11.5942'),
                'longitude': Decimal('37.3615'),
                'description': 'Scenic charging location by Lake Tana. Great for tourists exploring the Blue Nile source.',
                'opening_hours': '6:00 AM - 9:00 PM',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': True,
                'has_shopping': False,
                'rating': Decimal('4.4'),
                'rating_count': 15
            },
            {
                'name': 'Hawassa Industrial Park Charging Station',
                'address': 'Hawassa Industrial Park, Main Gate',
                'city': 'Hawassa',
                'state': 'SNNPR',
                'zip_code': '3000',
                'latitude': Decimal('7.0621'),
                'longitude': Decimal('38.4668'),
                'description': 'Industrial-grade charging for commercial vehicles and employee cars at the industrial park.',
                'opening_hours': '5:00 AM - 11:00 PM',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': True,
                'has_shopping': False,
                'rating': Decimal('4.1'),
                'rating_count': 27
            },
            {
                'name': 'Dire Dawa Railway Station Charging Point',
                'address': 'Dire Dawa Railway Station, Platform Area',
                'city': 'Dire Dawa',
                'state': 'Dire Dawa',
                'zip_code': '4000',
                'latitude': Decimal('9.5931'),
                'longitude': Decimal('41.8661'),
                'description': 'Strategic charging location at the historic railway station. Perfect for intercity travelers.',
                'opening_hours': '24/7',
                'has_restroom': True,
                'has_wifi': False,
                'has_restaurant': False,
                'has_shopping': False,
                'rating': Decimal('3.9'),
                'rating_count': 8
            },
            {
                'name': 'Mekelle University Charging Hub',
                'address': 'Mekelle University Campus, Main Building',
                'city': 'Mekelle',
                'state': 'Tigray',
                'zip_code': '5000',
                'latitude': Decimal('13.4967'),
                'longitude': Decimal('39.4753'),
                'description': 'University charging station serving students, staff, and visitors. Modern facilities available.',
                'opening_hours': '6:00 AM - 10:00 PM',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': True,
                'has_shopping': False,
                'rating': Decimal('4.3'),
                'rating_count': 19
            },
            {
                'name': 'Jimma Hospital Charging Station',
                'address': 'Jimma University Medical Center, Parking Area',
                'city': 'Jimma',
                'state': 'Oromia',
                'zip_code': '6000',
                'latitude': Decimal('7.6731'),
                'longitude': Decimal('36.8344'),
                'description': 'Essential charging point for medical staff and visitors. 24/7 security and lighting.',
                'opening_hours': '24/7',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': False,
                'has_shopping': False,
                'rating': Decimal('4.0'),
                'rating_count': 14
            },
            {
                'name': 'Adama Wind Farm Charging Station',
                'address': 'Adama Wind Farm, Visitor Center',
                'city': 'Adama',
                'state': 'Oromia',
                'zip_code': '7000',
                'latitude': Decimal('8.5400'),
                'longitude': Decimal('39.2675'),
                'description': 'Green energy charging station powered by wind farm. Educational tours available.',
                'opening_hours': '8:00 AM - 5:00 PM',
                'has_restroom': True,
                'has_wifi': True,
                'has_restaurant': False,
                'has_shopping': False,
                'rating': Decimal('4.6'),
                'rating_count': 22
            }
        ]
        
        # Connector types and their typical power ratings
        connector_configs = [
            {'type': 'ccs2', 'power': Decimal('50.0'), 'price': Decimal('8.50'), 'quantity': 2},
            {'type': 'ccs2', 'power': Decimal('150.0'), 'price': Decimal('12.00'), 'quantity': 1},
            {'type': 'type2', 'power': Decimal('22.0'), 'price': Decimal('5.50'), 'quantity': 3},
            {'type': 'chademo', 'power': Decimal('50.0'), 'price': Decimal('9.00'), 'quantity': 1},
        ]
        
        created_stations = 0
        created_connectors = 0
        
        for station_data in stations_data:
            # Check if station already exists
            existing_station = ChargingStation.objects.filter(
                name=station_data['name'],
                city=station_data['city']
            ).first()

            if existing_station and not options.get('force', False):
                self.stdout.write(f'Station already exists: {station_data["name"]} (use --force to recreate)')
                continue
            elif existing_station and options.get('force', False):
                self.stdout.write(f'Deleting existing station: {station_data["name"]}')
                existing_station.delete()
            
            # Update country to Ethiopia
            station_data['country'] = 'Ethiopia'
            station_data['owner'] = station_owner
            
            # Create the station
            station = ChargingStation.objects.create(**station_data)
            created_stations += 1
            
            # Add random connectors to each station
            num_connector_types = random.randint(2, 4)
            selected_configs = random.sample(connector_configs, num_connector_types)
            
            for config in selected_configs:
                connector = ChargingConnector.objects.create(
                    station=station,
                    connector_type=config['type'],
                    power_kw=config['power'],
                    quantity=config['quantity'],
                    available_quantity=config['quantity'],
                    price_per_kwh=config['price'],
                    is_available=True,
                    status='available',
                    description=f"{config['power']}kW {config['type'].upper()} connector"
                )
                created_connectors += 1
            
            # Update station connector counts
            station.update_connector_counts()
            
            self.stdout.write(f'Created station: {station.name} in {station.city}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_stations} stations and {created_connectors} connectors in Ethiopia!'
            )
        )
