from django.core.management.base import BaseCommand
from charging_stations.models import ChargingStation, StationReview


class Command(BaseCommand):
    help = 'Clean up fake reviews and reset station ratings to zero'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all reviews',
        )

    def handle(self, *args, **options):
        if not options.get('confirm', False):
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL reviews and reset station ratings to zero.\n'
                    'Use --confirm to proceed.'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('🧹 Cleaning up fake reviews and resetting ratings...'))

        # Delete all reviews
        review_count = StationReview.objects.count()
        StationReview.objects.all().delete()
        self.stdout.write(f'Deleted {review_count} reviews')

        # Reset all station ratings to zero
        stations = ChargingStation.objects.all()
        updated_stations = 0
        
        for station in stations:
            if station.rating != 0.0 or station.rating_count != 0:
                station.rating = 0.0
                station.rating_count = 0
                station.save(update_fields=['rating', 'rating_count'])
                updated_stations += 1

        self.stdout.write(f'Reset ratings for {updated_stations} stations')

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Cleanup complete! All stations now have 0 reviews and 0.0 rating.'
            )
        )
        self.stdout.write('📱 Users can now add real reviews through the mobile app!')
