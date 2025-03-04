import asyncio
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test the website scraper with the updated date parser'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='URL to test the scraper with')

    def handle(self, *args, **options):
        from events.scrapers.test_website import test_website_scraper
        url = options['url']
        self.stdout.write(f'Testing website scraper with URL: {url}')
        
        # Run the async function
        loop = asyncio.get_event_loop()
        events = loop.run_until_complete(test_website_scraper(url))
        
        # Display summary
        if events:
            self.stdout.write(self.style.SUCCESS(f'Successfully extracted {len(events)} events'))
        else:
            self.stdout.write(self.style.ERROR('Failed to extract events')) 