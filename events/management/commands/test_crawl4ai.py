from django.core.management.base import BaseCommand
import asyncio
from events.scrapers.generic_crawl4ai import GenericCrawl4AIScraper

class Command(BaseCommand):
    help = 'Test the Crawl4AI scraper'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='URL to scrape')

    def handle(self, *args, **options):
        url = options['url']
        scraper = GenericCrawl4AIScraper()
        
        async def run():
            events = await scraper.extract_events(url)
            self.stdout.write(self.style.SUCCESS(f'Found {len(events)} events:'))
            for event in events:
                self.stdout.write(str(event))
        
        asyncio.run(run())
