from django.core.management.base import BaseCommand
from charging_stations.models import ChargingStation


class Command(BaseCommand):
    help = 'Update connector counts for all charging stations'

    def handle(self, *args, **options):
        stations = ChargingStation.objects.all()
        updated_count = 0
        
        for station in stations:
            old_total = station.total_connectors
            old_available = station.available_connectors
            
            station.update_connector_counts()
            
            if (station.total_connectors != old_total or 
                station.available_connectors != old_available):
                updated_count += 1
                self.stdout.write(
                    f"Updated {station.name}: "
                    f"Total: {old_total} -> {station.total_connectors}, "
                    f"Available: {old_available} -> {station.available_connectors}"
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} stations'
            )
        )
