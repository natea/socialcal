from celery import shared_task
from .models import EventSource, Event
from .utils.event_extractor import EventExtractor

@shared_task
def scrape_event_sources(source_id=None):
    """
    Periodic task to scrape event sources
    """
    sources = EventSource.objects.filter(is_active=True)
    if source_id:
        sources = sources.filter(id=source_id)

    extractor = EventExtractor(openai_api_key=settings.OPENAI_API_KEY)

    for source in sources:
        try:
            events_data = extractor.extract_events(source.url)
            
            # Create events
            events_to_create = []
            for event_data in events_data:
                event = Event(
                    title=event_data.get('title'),
                    description=event_data.get('description'),
                    start_datetime=event_data.get('start_datetime'),
                    end_datetime=event_data.get('end_datetime'),
                    location=event_data.get('location'),
                    cost=event_data.get('cost'),
                    url=event_data.get('url'),
                    source=source
                )
                events_to_create.append(event)
            
            # Bulk create to improve performance
            Event.objects.bulk_create(events_to_create)
            
            # Update last scraped time
            source.last_scraped = timezone.now()
            source.save()

        except Exception as e:
            # Log the error
            print(f"Error scraping {source.url}: {e}")