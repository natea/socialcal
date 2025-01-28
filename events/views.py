from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from .models import Event
from .forms import EventForm
from .scrapers.generic_crawl4ai import scrape_events as scrape_crawl4ai_events
from .scrapers.ical_scraper import ICalScraper
from .utils.spotify import SpotifyAPI
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
from django.urls import reverse
import re
from django.db import models
from django.utils import timezone

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
    
    # Get search query and venue filter from query params
    search_query = request.GET.get('q')
    venue_filter = request.GET.get('venue')
    
    # Apply search filter if provided
    if search_query:
        events = events.filter(
            models.Q(title__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(venue_name__icontains=search_query)
        )
    
    # Apply venue filter if provided
    if venue_filter:
        events = events.filter(venue_name__icontains=venue_filter)
    
    # Get distinct venues for the filter dropdown
    venues = Event.objects.filter(user=request.user).exclude(venue_name='').values_list('venue_name', flat=True).distinct().order_by('venue_name')
    
    # Truncate long venue names for the dropdown (keep original for filtering)
    venue_display_names = {
        venue: (venue[:50] + '...' if len(venue) > 50 else venue)
        for venue in venues
    }
    
    return render(request, 'events/list.html', {
        'events': events,
        'venues': venues,
        'venue_display_names': venue_display_names,
        'selected_venue': venue_filter,
        'search_query': search_query
    })

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
    return render(request, 'events/delete.html', {'event': event})

@login_required
def event_import_status(request, job_id):
    # Check if the job exists
    status = get_job_status(job_id)
    if not status:
        return JsonResponse({'error': 'Job not found'}, status=404)
    
    # Return the job status
    return JsonResponse(status)

def run_async_in_thread(coroutine, *args, **kwargs):
    """Helper function to run async code in a thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine(*args, **kwargs))
    finally:
        loop.close()

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
                        'message': 'Scraping started',
                        'progress': {
                            'overall': 0,
                            'scraping': 0,
                            'processing': 0
                        },
                        'status_message': {
                            'scraping': 'Initializing scraper...',
                            'processing': 'Waiting to process events...'
                        }
                    })

                    # Start the scraping in a background thread with proper async handling
                    thread = Thread(
                        target=run_async_in_thread,
                        args=(scrape_crawl4ai_events_async, source_url, job_id, request.user)
                    )
                    thread.start()
                    
                    return JsonResponse({
                        'status': 'started',
                        'job_id': job_id,
                        'message': 'Scraping started'
                    })
                else:
                    try:
                        # Synchronous scraping
                        events = await scrape_crawl4ai_events(source_url)
                        
                        # Process events
                        processed_events = []
                        updated_count = 0
                        created_count = 0
                        
                        for event_data in events:
                            try:
                                # Add Spotify track if it's a music event
                                event_data = await add_spotify_track_to_event(event_data)
                                
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
                        
                        success_message = f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
                        messages.success(request, success_message)
                        
                        # Return JSON for AJAX requests, redirect for regular form submissions
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'status': 'complete',
                                'message': success_message,
                                'redirect_url': reverse('events:list'),
                                'events': processed_events
                            })
                        else:
                            return redirect('events:list')
                    except HTTPError as e:
                        logger.error(f"Error in scraping: {str(e)}\n{traceback.format_exc()}")
                        messages.error(request, str(e))
                        return JsonResponse({
                            'status': 'error',
                            'message': str(e)
                        }, status=400)
                    except Exception as e:
                        logger.error(f"Error in scraping: {str(e)}\n{traceback.format_exc()}")
                        messages.error(request, str(e))
                        return JsonResponse({
                            'status': 'error',
                            'message': str(e)
                        }, status=400)
            elif scraper_type == 'ical':
                # Handle iCal scraping
                try:
                    scraper = ICalScraper()
                    events = await scraper.scrape_events(source_url)
                    
                    # Process events
                    processed_events = []
                    updated_count = 0
                    created_count = 0
                    
                    for event_data in events:
                        try:
                            # Add Spotify track if it's a music event
                            event_data = await add_spotify_track_to_event(event_data)
                            
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
                    
                    success_message = f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
                    messages.success(request, success_message)
                    
                    # Return JSON for AJAX requests, redirect for regular form submissions
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'complete',
                            'message': success_message,
                            'redirect_url': reverse('events:list'),
                            'events': processed_events
                        })
                    else:
                        return redirect('events:list')
                except Exception as e:
                    logger.error(f"Error in scraping: {str(e)}\n{traceback.format_exc()}")
                    messages.error(request, str(e))
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=400)
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

def is_music_event(event_data):
    """Check if an event is likely a music event based on its data."""
    music_keywords = {
        'concert', 'live music', 'band', 'performance', 'gig', 'show',
        'musician', 'singer', 'performer', 'dj', 'jazz', 'rock', 'blues',
        'hip hop', 'rap', 'electronic', 'classical', 'orchestra', 'ensemble',
        'quartet', 'trio', 'recital', 'festival'
    }
    
    # Check title and description for music-related keywords
    text_to_check = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
    return any(keyword in text_to_check for keyword in music_keywords)

def get_artist_from_event(event_data):
    """Extract potential artist name from event data."""
    title = event_data.get('title', '')
    
    # Common patterns in music event titles
    patterns = [
        # Full ensemble/band name patterns
        r"^([\w\s]+(?:Orchestra|Band|Ensemble|Quartet|Trio|Quintet|Sextet|Septet|Octet|Group|Seven))\s*(?:[-–]\s*|:|$)",
        r"^([\w\s]+(?:Orchestra|Band|Ensemble|Quartet|Trio|Quintet|Sextet|Septet|Octet|Group|Seven))\s+(?:presents|performs|in|at)",
        # Artist with location/venue
        r"^(.+?)\s+(?:live at|at|@)",
        # Artist after presenting words
        r"(?:presents|featuring|feat\.|ft\.|with)\s+(.+?)(?:\s+at|\s+in|\s*$)",
        # Artist before event type
        r"^(.+?)\s+(?:in concert|concert|performance|show|gig)",
        # Artist with descriptive text
        r"^(.+?),\s*(?:live|in concert|performing)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no patterns match, return the first part of the title before any common separators
    separators = [' at ', ' in ', ' with ', ' - ', ' @ ', ' presents ', ': ']
    for separator in separators:
        if separator.lower() in title.lower():
            return title.split(separator)[0].strip()
    
    # If still no match, return the whole title
    return title.strip()

def add_spotify_track_to_event(event_data):
    """Search for and add a Spotify track to the event data if it's a music event."""
    # Initialize Spotify fields with empty values
    spotify_defaults = {
        'spotify_track_id': '',
        'spotify_track_name': '',
        'spotify_artist_id': '',
        'spotify_artist_name': '',
        'spotify_artist_id': '',
        'spotify_preview_url': '',
        'spotify_external_url': ''
    }
    event_data.update(spotify_defaults)
    
    if not is_music_event(event_data):
        return event_data
        
    # Check if we already have Spotify data
    if event_data.get('spotify_track_id') and event_data.get('spotify_artist_id'):
        return event_data
        
    # Check for cached data in session
    if 'session' in event_data and isinstance(event_data['session'], dict):
        cache_key = f'spotify_data_{event_data.get("id")}'
        cached_data = event_data['session'].get(cache_key)
        if cached_data:
            event_data.update({
                'spotify_track_id': cached_data['track_id'],
                'spotify_track_name': cached_data['track_name'],
                'spotify_artist_name': cached_data['artist_name'],
                'spotify_artist_id': cached_data['artist_id'],
                'spotify_preview_url': cached_data['preview_url'],
                'spotify_external_url': cached_data['external_url']
            })
            return event_data
        
    artist = get_artist_from_event(event_data)
    if not artist:
        return event_data
        
    try:
        # Search for tracks by the specific artist
        tracks = SpotifyAPI.search_track("", artist_name=artist)
        if tracks and len(tracks) > 0:
            # Use the first track that matches
            track = tracks[0]
            event_data.update({
                'spotify_track_id': track['id'],
                'spotify_track_name': track['name'],
                'spotify_artist_id': track.get('artist_id', ''),
                'spotify_artist_name': track['artist'],
                'spotify_artist_id': track['artist_id'],
                'spotify_preview_url': track['preview_url'] or '',
                'spotify_external_url': track['external_url']
            })
            
            # Cache the results in the session if available
            if 'session' in event_data and isinstance(event_data['session'], dict):
                cache_key = f'spotify_data_{event_data.get("id")}'
                event_data['session'][cache_key] = {
                    'track_id': track['id'],
                    'track_name': track['name'],
                    'artist_name': track['artist'],
                    'artist_id': track['artist_id'],
                    'preview_url': track['preview_url'] or '',
                    'external_url': track['external_url']
                }
    except Exception as e:
        logger.error(f"Error searching Spotify for artist {artist}: {str(e)}")
        # Keep the default empty values on error
    
    return event_data

async def scrape_crawl4ai_events_async(source_url, job_id, user):
    loop = None
    try:
        # Initialize status with progress tracking
        set_job_status(job_id, {
            'status': 'started',
            'events': [],
            'message': 'Starting scraping process...',
            'progress': {
                'overall': 0,
                'scraping': 0,
                'processing': 0
            },
            'status_message': {
                'scraping': 'Initializing scraper...',
                'processing': 'Waiting to process events...'
            },
            'stats': {
                'found': 0,
                'created': 0,
                'updated': 0
            }
        })

        # Start scraping
        events = await scrape_crawl4ai_events(source_url)
        
        # Update progress after scraping
        set_job_status(job_id, {
            'status': 'running',
            'progress': {
                'overall': 40,
                'scraping': 100,
                'processing': 0
            },
            'status_message': {
                'scraping': 'Event scraping complete',
                'processing': 'Starting to process events...'
            },
            'stats': {
                'found': len(events),
                'created': 0,
                'updated': 0
            }
        })
        
        # Process events
        processed_events = []
        updated_count = 0
        created_count = 0
        
        total_events = len(events)
        for index, event_data in enumerate(events, 1):
            try:
                # Calculate progress
                processing_progress = int((index / total_events) * 100)
                overall_progress = 40 + int((index / total_events) * 60)
                
                # Update progress during processing
                set_job_status(job_id, {
                    'status': 'running',
                    'progress': {
                        'overall': overall_progress,
                        'scraping': 100,
                        'processing': processing_progress
                    },
                    'status_message': {
                        'scraping': 'Event scraping complete',
                        'processing': f'Processing event {index} of {total_events}...'
                    },
                    'stats': {
                        'found': total_events,
                        'created': created_count,
                        'updated': updated_count
                    },
                    'events': processed_events
                })
                
                # Add Spotify track if it's a music event
                event_data = add_spotify_track_to_event(event_data)
                
                # Check for existing event
                existing = await filter_events(
                    user=user,
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
                    event = Event(user=user)
                    for field, value in event_data.items():
                        if hasattr(event, field):
                            setattr(event, field, value)
                    await save_event(event)
                    created_count += 1
                
                processed_events.append(event_data)
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
        
        # Update final status
        final_status = {
            'status': 'complete',
            'events': processed_events,
            'message': f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)',
            'progress': {
                'overall': 100,
                'scraping': 100,
                'processing': 100
            },
            'status_message': {
                'scraping': 'Event scraping complete',
                'processing': 'All events processed successfully'
            },
            'stats': {
                'found': total_events,
                'created': created_count,
                'updated': updated_count
            },
            'redirect_url': reverse('events:list')
        }
        set_job_status(job_id, final_status)
        
    except Exception as e:
        logger.error(f"Error in scraping: {str(e)}\n{traceback.format_exc()}")
        error_status = {
            'status': 'error',
            'message': str(e),
            'progress': {
                'overall': 0,
                'scraping': 0,
                'processing': 0
            },
            'status_message': {
                'scraping': 'Error occurred during scraping',
                'processing': 'Process stopped due to error'
            },
            'log': log_stream.getvalue()
        }
        set_job_status(job_id, error_status)
    finally:
        if loop:
            loop.stop()
            loop.close()
            asyncio.set_event_loop(None)  # Clear the event loop

@login_required
def spotify_search(request):
    """Handle AJAX requests for Spotify track search."""
    query = request.GET.get('q')
    if not query:
        return JsonResponse({'error': 'No search query provided'}, status=400)
        
    tracks = SpotifyAPI.search_track(query)
    if not tracks:
        return JsonResponse({'error': 'No tracks found'}, status=404)
        
    return JsonResponse(tracks, safe=False)

def export_ical(request, events=None):
    """Export events as iCalendar feed."""
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//SocialCal//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    
    # If event_id is provided, export only that event
    event_id = request.GET.get('event_id')
    if event_id:
        try:
            events = [Event.objects.get(id=event_id, is_public=True)]
        except Event.DoesNotExist:
            events = []
    # If no events provided and no event_id, get all public events
    elif events is None:
        events = Event.objects.filter(is_public=True)
    
    # Add events to calendar
    for event in events:
        cal_event = ICalEvent()
        cal_event.add('summary', event.title)
        cal_event.add('description', event.description)
        cal_event.add('dtstart', event.start_time)
        if event.end_time:
            cal_event.add('dtend', event.end_time)
        if event.location:
            cal_event.add('location', event.location)
        cal_event.add('url', request.build_absolute_uri(event.get_absolute_url()))
        cal_event.add('dtstamp', timezone.now())
        cal_event.add('uid', f'{event.id}@socialcal')
        cal.add_component(cal_event)
    
    # Return calendar as response
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    filename = f"event_{event_id}.ics" if event_id else "events.ics"
    response['Content-Disposition'] = f'attachment; filename={filename}'
    return response