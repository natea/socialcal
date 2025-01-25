from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Event
from .forms import EventForm
from .scrapers.generic_crawl4ai import scrape_events as scrape_crawl4ai_events
from .scrapers.ical_scraper import ICalScraper
import io
import logging
import json
from threading import Thread
import time
from requests.exceptions import HTTPError, RequestException
import traceback
import asyncio
from icalendar import Calendar, Event as ICalEvent
from asgiref.sync import sync_to_async, async_to_sync
from django.core.cache import cache
import pickle
from threading import Lock

# Create a string buffer to capture log output
log_stream = io.StringIO()
# Create a handler that writes to the string buffer
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setLevel(logging.DEBUG)
# Add the handler to the logger
logger = logging.getLogger('events.scrapers.generic_scraper')
logger.addHandler(stream_handler)

# Async helper functions
save_event = sync_to_async(lambda event: event.save())
get_event = sync_to_async(get_object_or_404)
filter_events = sync_to_async(lambda **kwargs: list(Event.objects.filter(**kwargs)))

class TimedLock:
    """A lock that automatically releases after a timeout period"""
    def __init__(self, timeout=300):  # 5 minutes default timeout
        self.lock = Lock()
        self.timeout = timeout
        self.acquire_time = None
    
    def acquire(self, blocking=True, timeout=-1):
        # First check if we need to auto-release a stale lock
        if self.acquire_time is not None:
            if time.time() - self.acquire_time > self.timeout:
                logger.warning("Auto-releasing stale lock")
                try:
                    self.release()
                except:
                    pass  # Ignore errors from releasing an already released lock
        
        # Now try to acquire the lock
        result = self.lock.acquire(blocking=blocking, timeout=timeout)
        if result:
            self.acquire_time = time.time()
        return result
    
    def release(self):
        self.acquire_time = None
        self.lock.release()

# Store scraping locks in memory (these are short-lived)
scraping_locks = {}

def get_job_status(job_id):
    """Get job status from Redis cache"""
    status = cache.get(f'scraping_job_{job_id}')
    return pickle.loads(status) if status else None

def set_job_status(job_id, status):
    """Set job status in Redis cache"""
    cache.set(f'scraping_job_{job_id}', pickle.dumps(status), timeout=3600)  # 1 hour timeout

@login_required
def event_list(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'events/list.html', {'events': events})

@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()
            
            # Store the timezone in session for future use
            request.session['event_timezone'] = form.cleaned_data.get('timezone')
            
            messages.success(request, 'Event created successfully!')
            return redirect('events:list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Get the timezone from session or default to America/New_York
        timezone = request.session.get('event_timezone', 'America/New_York')
        form = EventForm(initial={'timezone': timezone})
    return render(request, 'events/form.html', {'form': form, 'action': 'Create'})

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    return render(request, 'events/detail.html', {'event': event})

@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            # Store the timezone in session when form is saved
            request.session['event_timezone'] = form.cleaned_data.get('timezone')
            messages.success(request, 'Event updated successfully!')
            return redirect('events:list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EventForm(instance=event)
    return render(request, 'events/form.html', {'form': form, 'action': 'Edit'})

@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk, user=request.user)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('events:list')
    return render(request, 'events/confirm_delete.html', {'event': event})

@login_required
def event_import_status(request, job_id):
    # Check if the job exists
    status = get_job_status(job_id)
    if not status:
        return JsonResponse({'error': 'Job not found'}, status=404)
    
    # Return the job status
    return JsonResponse(status)

@login_required
def event_import(request):
    return async_to_sync(_event_import)(request)

async def _event_import(request):
    if request.method == 'POST':
        scraper_type = request.POST.get('scraper_type')
        source_url = request.POST.get('source_url')
        is_async = request.POST.get('async', 'false').lower() == 'true'

        # Validate inputs
        if not scraper_type:
            messages.error(request, 'Scraper type is required')
            return HttpResponse('Scraper type is required', status=400)
        if not source_url:
            messages.error(request, 'Source URL is required')
            return HttpResponse('Source URL is required', status=400)
        if scraper_type not in ['crawl4ai', 'ical']:
            messages.error(request, 'Invalid scraper type')
            return HttpResponse('Invalid scraper type', status=400)

        # Basic URL validation
        if not source_url.startswith(('http://', 'https://', 'file://', 'raw:')):
            messages.error(request, 'Invalid URL format')
            return HttpResponse('Invalid URL: URL must start with http://, https://, file://, or raw:', status=400)

        try:
            if scraper_type == 'crawl4ai':
                if is_async:
                    # Generate a unique job ID
                    job_id = str(time.time())
                    set_job_status(job_id, {
                        'status': 'started',
                        'events': [],
                        'message': 'Scraping started'
                    })

                    # Start the scraping in a background thread
                    thread = Thread(target=scrape_crawl4ai_events_async, args=(source_url, job_id, request.user))
                    thread.start()
                    
                    return JsonResponse({
                        'status': 'started',
                        'job_id': job_id,
                        'message': 'Scraping started'
                    })
                else:
                    # Synchronous scraping
                    events = await scrape_crawl4ai_events(source_url)
                    
                    # Process events
                    processed_events = []
                    updated_count = 0
                    created_count = 0
                    
                    for event_data in events:
                        try:
                            # Check for existing event
                            existing = await filter_events(
                                user=request.user,
                                title=event_data.get('title'),
                                start_time=event_data.get('start_time')
                            )
                            existing = existing[0] if existing else None
                            
                            if existing:
                                # Update existing event
                                for field, value in event_data.items():
                                    if hasattr(existing, field):
                                        setattr(existing, field, value)
                                await save_event(existing)
                                updated_count += 1
                            else:
                                # Create new event
                                event = Event(user=request.user)
                                for field, value in event_data.items():
                                    if hasattr(event, field):
                                        setattr(event, field, value)
                                await save_event(event)
                                created_count += 1
                            
                            processed_events.append(event_data)
                        except Exception as e:
                            logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
                    
                    return JsonResponse({
                        'status': 'complete',
                        'events': processed_events,
                        'message': f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
                    })
            elif scraper_type == 'ical':
                # Handle iCal scraping
                scraper = ICalScraper()
                events = await scraper.scrape_events(source_url)
                return JsonResponse({
                    'status': 'complete',
                    'events': events,
                    'message': f'Successfully scraped {len(events)} events'
                })
        except Exception as e:
            logger.error(f"Error in scraping: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return render(request, 'events/import.html')

@login_required
def event_export(request):
    # Get all events for the user
    events = Event.objects.filter(user=request.user)
    
    # Create the calendar
    cal = Calendar()
    cal.add('prodid', '-//SocialCal//Event Calendar//EN')
    cal.add('version', '2.0')
    
    # Add events to the calendar
    for event in events:
        cal_event = ICalEvent()
        cal_event.add('summary', event.title)
        cal_event.add('description', event.description)
        cal_event.add('dtstart', event.start_time)
        cal_event.add('dtend', event.end_time)
        cal_event.add('location', event.get_full_address())
        cal.add_component(cal_event)
    
    # Create the response
    response = HttpResponse(content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="events.ics"'
    response.write(cal.to_ical())
    return response

def scrape_crawl4ai_events_async(source_url, job_id, user):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        events = loop.run_until_complete(scrape_crawl4ai_events(source_url))
        loop.close()
        
        # Process events
        processed_events = []
        updated_count = 0
        created_count = 0
        
        for event_data in events:
            try:
                # Check for existing event
                existing = Event.objects.filter(
                    user=user,
                    title=event_data.get('title'),
                    start_time=event_data.get('start_time')
                ).first()
                
                if existing:
                    # Update existing event
                    for field, value in event_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    existing.save()
                    updated_count += 1
                else:
                    # Create new event
                    event = Event(user=user)
                    for field, value in event_data.items():
                        if hasattr(event, field):
                            setattr(event, field, value)
                    event.save()
                    created_count += 1
                
                processed_events.append(event_data)
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
        
        # Update job status
        set_job_status(job_id, {
            'status': 'complete',
            'events': processed_events,
            'message': f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
        })
    except Exception as e:
        logger.error(f"Error in Crawl4AI scraping: {str(e)}\n{traceback.format_exc()}")
        set_job_status(job_id, {
            'status': 'error',
            'message': str(e)
        })