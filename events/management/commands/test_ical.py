from django.core.management.base import BaseCommand
from events.scrapers.ical_scraper import ICalScraper
from events.models import Event
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Import events from any webpage containing an iCal feed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email of the user to associate events with',
            default='natejaune@gmail.com'
        )
        parser.add_argument(
            'url',
            type=str,
            help='URL of the webpage or direct iCal feed'
        )

    def handle(self, *args, **options):
        # Get URL from arguments
        url = options['url']
        
        # Get or create user
        User = get_user_model()
        user_email = options['email']
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stdout.write(f'Creating user with email {user_email}')
            user = User.objects.create_user(
                email=user_email,
                username=user_email.split('@')[0],
                password='changeme123'
            )

        # Initialize scraper
        scraper = ICalScraper()
        
        try:
            # If this is a webpage (not direct iCal URL), try to discover calendar URLs
            if not url.endswith('.ics') and not 'ical=1' in url:
                self.stdout.write('Searching for calendar feeds...')
                discovered_urls = scraper.discover_ical_urls(url)
                if discovered_urls:
                    self.stdout.write(self.style.SUCCESS(f'Found {len(discovered_urls)} potential calendar URLs:'))
                    for discovered_url in discovered_urls:
                        self.stdout.write(f'- {discovered_url}')
                else:
                    self.stdout.write(self.style.WARNING('No calendar URLs found on the page'))
            
            # Get the events
            self.stdout.write('Fetching events...')
            events = scraper.process_events(url)
            
            if not events:
                self.stdout.write(self.style.WARNING('No events found'))
                return

            self.stdout.write(self.style.SUCCESS(f'Found {len(events)} events'))
            
            # Track statistics
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            # Process each event
            for event_data in events:
                # Skip events without required fields
                if not event_data.get('title') or not event_data.get('start_time'):
                    skipped_count += 1
                    continue
                
                # Check for existing event with same title and start time
                existing = Event.objects.filter(
                    title=event_data['title'],
                    start_time=event_data['start_time'],
                    user=user
                ).first()
                
                if existing:
                    # Update existing event
                    for key, value in event_data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                else:
                    # Create new event
                    Event.objects.create(user=user, **event_data)
                    created_count += 1
            
            # Print summary
            self.stdout.write(self.style.SUCCESS(
                f'\nImport complete:\n'
                f'Created: {created_count}\n'
                f'Updated: {updated_count}\n'
                f'Skipped: {skipped_count}'
            ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 