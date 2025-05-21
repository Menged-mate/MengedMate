import random
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from charging_stations.models import (
    StationOwner, 
    ChargingStation, 
    ChargingConnector, 
    FavoriteStation
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates sample data for testing the charging stations map'

    def add_arguments(self, parser):
        parser.add_argument('--stations', type=int, default=20, help='Number of stations to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing data before creating new data')

    def handle(self, *args, **options):
        num_stations = options['stations']
        clear_data = options['clear']
        
        if clear_data:
            self.clear_existing_data()
            
        self.create_sample_data(num_stations)
        
    def clear_existing_data(self):
        self.stdout.write('Clearing existing data...')
        ChargingConnector.objects.all().delete()
        FavoriteStation.objects.all().delete()
        ChargingStation.objects.all().delete()
        StationOwner.objects.filter(company_name__startswith='Sample').delete()
        User.objects.filter(email__startswith='sample').delete()
        self.stdout.write(self.style.SUCCESS('Existing data cleared.'))
        
    def create_sample_data(self, num_stations):
        self.stdout.write(f'Creating {num_stations} sample charging stations...')
        
        # Create sample station owners
        owners = self.create_sample_owners(3)
        
        # Create sample stations
        stations = []
        for i in range(num_stations):
            owner = random.choice(owners)
            
            # Create a station with random coordinates around a central point
            # Using Washington DC as the center point
            center_lat = 38.9072
            center_lng = -77.0369
            
            # Random coordinates within ~10km of the center
            lat = center_lat + (random.random() - 0.5) * 0.1
            lng = center_lng + (random.random() - 0.5) * 0.1
            
            station = ChargingStation.objects.create(
                id=uuid.uuid4(),
                owner=owner,
                name=f'Sample Station {i+1}',
                address=f'{random.randint(100, 9999)} Sample St',
                city='Washington',
                state='DC',
                zip_code=f'200{random.randint(10, 99)}',
                country='United States',
                latitude=lat,
                longitude=lng,
                description=f'This is a sample charging station #{i+1} for testing.',
                opening_hours='{"monday": "24 hours", "tuesday": "24 hours", "wednesday": "24 hours", "thursday": "24 hours", "friday": "24 hours", "saturday": "24 hours", "sunday": "24 hours"}',
                is_active=True,
                is_operational=random.random() > 0.1,  # 90% operational
                is_public=True,
                rating=Decimal(str(round(3.5 + random.random() * 1.5, 1))),
                rating_count=random.randint(5, 50),
                price_range='$-$$',
                has_restroom=random.random() > 0.5,
                has_wifi=random.random() > 0.6,
                has_restaurant=random.random() > 0.7,
                has_shopping=random.random() > 0.8,
                marker_icon='default'
            )
            
            # Create random connectors for this station
            self.create_sample_connectors(station)
            
            # Update connector counts
            total = station.connectors.count()
            available = sum(1 for c in station.connectors.all() if c.is_available)
            station.total_connectors = total
            station.available_connectors = available
            station.save()
            
            stations.append(station)
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created {num_stations} sample charging stations.'))
        
        # Create some favorites for the first user
        if User.objects.exists():
            user = User.objects.first()
            for station in random.sample(stations, min(5, len(stations))):
                FavoriteStation.objects.create(user=user, station=station)
            self.stdout.write(self.style.SUCCESS(f'Added favorite stations for user {user.email}'))
        
    def create_sample_owners(self, num_owners):
        owners = []
        for i in range(num_owners):
            # Create user
            email = f'sample.owner{i+1}@example.com'
            
            # Skip if user already exists
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
            else:
                user = User.objects.create_user(
                    email=email,
                    password='password123',
                    first_name=f'Sample{i+1}',
                    last_name='Owner',
                    is_verified=True
                )
            
            # Create or get station owner
            try:
                owner = StationOwner.objects.get(user=user)
            except StationOwner.DoesNotExist:
                owner = StationOwner.objects.create(
                    user=user,
                    company_name=f'Sample Company {i+1}',
                    business_registration_number=f'REG{i+1}12345',
                    verification_status='verified' if i < 2 else 'pending',
                    is_profile_completed=True,
                    verified_at=timezone.now() if i < 2 else None
                )
            
            owners.append(owner)
            
        return owners
    
    def create_sample_connectors(self, station):
        # List of connector types
        connector_types = list(ChargingConnector.ConnectorType.values)
        
        # Create 1-4 random connectors
        num_connectors = random.randint(1, 4)
        for i in range(num_connectors):
            connector_type = random.choice(connector_types)
            power = random.choice([7.2, 11, 22, 50, 150, 350])
            
            ChargingConnector.objects.create(
                station=station,
                connector_type=connector_type,
                power_kw=power,
                quantity=random.randint(1, 4),
                price_per_kwh=Decimal(str(round(0.3 + random.random() * 0.4, 2))),
                is_available=random.random() > 0.2,  # 80% available
                description=f'{connector_type.upper()} connector with {power}kW power'
            )
