from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Event
from .forms import EventForm
from .scrapers.events_scraper import EventsScraper
from .scrapers.regattabar_scraper import scrape_events as scrape_regattabar_events
from .scrapers.berklee_scraper import scrape_berklee_events
from .scrapers.generic_scraper import GenericScraper
from .scrapers.generic_crawl4ai import scrape_events as scrape_crawl4ai_events
import io
import logging
import json
from threading import Thread
import time
from requests.exceptions import HTTPError, RequestException
import traceback
import os
import asyncio

# Create a string buffer to capture log output
log_stream = io.StringIO()
# Create a handler that writes to the string buffer
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setLevel(logging.DEBUG)
# Add the handler to the logger
logger = logging.getLogger('events.scrapers.generic_scraper')
logger.addHandler(stream_handler)

# Store scraping jobs in memory (in production, use Redis or similar)
scraping_jobs = {}

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                raise
            delay = initial_delay * (2 ** attempt)  # Exponential backoff
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds: {str(e)}")
            time.sleep(delay)

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
            request.session['event_timezone'] = form.cleaned_data['timezone']
            
            messages.success(request, 'Event created successfully!')
            return redirect('events:detail', pk=event.pk)
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
            request.session['event_timezone'] = form.cleaned_data['timezone']
            messages.success(request, 'Event updated successfully!')
            return redirect('events:detail', pk=event.pk)
    else:
        # Get the timezone from POST data or session, defaulting to America/New_York
        timezone = request.session.get('event_timezone', 'America/New_York')
        form = EventForm(instance=event, initial={'timezone': timezone})
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
    """Check the status of an async scraping job"""
    if job_id not in scraping_jobs:
        return JsonResponse({'status': 'error', 'message': 'Job not found'})
    
    job = scraping_jobs[job_id]
    
    return JsonResponse({
        'status': job['status'],
        'events': job.get('events', []),
        'message': job.get('message', ''),
        'log': job.get('log', '')
    })

@login_required
def event_import(request):
    if request.method == 'POST':
        scraper_type = request.POST.get('scraper_type', 'generic')
        is_async = request.POST.get('async', 'false') == 'true'
        
        try:
            if scraper_type == 'regattabar':
                # Use RegattaBar scraper
                events_data = scrape_regattabar_events()
            elif scraper_type == 'berklee':
                # Use Berklee scraper
                events_data = scrape_berklee_events()
            elif scraper_type == 'crawl4ai':
                # Use Crawl4AI scraper
                source_url = request.POST.get('source_url')
                if not source_url:
                    if is_async:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Please provide a URL to scrape.'
                        })
                    messages.error(request, 'Please provide a URL to scrape.')
                    return redirect('events:import')

                if is_async:
                    try:
                        # Start async scraping job
                        job_id = f"scrape_{len(scraping_jobs)}"
                        scraping_jobs[job_id] = {
                            'status': 'running',
                            'events': [],
                            'log': '',
                            'source_url': source_url,
                            'user': request.user
                        }
                        
                        # Start the scraping in a background thread
                        def scrape_in_background():
                            try:
                                # Get the job from the global dict
                                job = scraping_jobs[job_id]
                                
                                try:
                                    # Use only the Crawl4AI scraper
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    events_data = loop.run_until_complete(scrape_crawl4ai_events(source_url))
                                    loop.close()
                                    
                                    logger.info("Crawl4AI scraping completed successfully")
                                    logger.info(f"Raw events data: {json.dumps(events_data, indent=2)}")
                                    
                                    if events_data:
                                        processed_events = []
                                        for event_data in events_data:
                                            try:
                                                logger.info(f"Processing event: {event_data.get('title')}")
                                                
                                                # Check if event already exists
                                                title = event_data.get('title', '')
                                                start_time = event_data.get('start_time')
                                                venue_name = event_data.get('venue_name', '')
                                                
                                                # Try to find an existing event with same title, date and venue
                                                existing_event = Event.objects.filter(
                                                    user=job['user'],
                                                    title=title,
                                                    start_time=start_time,
                                                    venue_name=venue_name
                                                ).first()
                                                
                                                if existing_event:
                                                    logger.info(f"Event already exists: {title} at {venue_name}")
                                                    continue
                                                
                                                # Create and save the event if it doesn't exist
                                                event = Event(user=job['user'])
                                                for field, value in event_data.items():
                                                    if hasattr(event, field):
                                                        logger.info(f"Setting {field} = {value}")
                                                        setattr(event, field, value)
                                                    else:
                                                        logger.warning(f"Field {field} not found in Event model")
                                                event.save()
                                                logger.info(f"Successfully saved event: {event.title}")
                                                
                                                # Only append the minimal data needed for display
                                                processed_events.append({
                                                    'id': event.id,
                                                    'title': event.title,
                                                    'start_time': event.start_time,
                                                    'venue_name': event.venue_name
                                                })
                                            except Exception as e:
                                                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
                                        
                                        # Update job status
                                        job['status'] = 'complete'
                                        job['events'] = processed_events
                                        job['message'] = f'Successfully imported {len(processed_events)} events'
                                        logger.info(job['message'])
                                    else:
                                        logger.warning("No events found in extraction result")
                                        job['status'] = 'complete'
                                        job['message'] = 'No events found at the provided URL'
                                    
                                except Exception as e:
                                    logger.error(f"Error in Crawl4AI scraping: {str(e)}\n{traceback.format_exc()}")
                                    job['status'] = 'error'
                                    job['message'] = str(e)
                                
                            except Exception as e:
                                logger.error(f"Critical error in background thread: {str(e)}\n{traceback.format_exc()}")
                                if job_id in scraping_jobs:
                                    scraping_jobs[job_id].update({
                                        'status': 'error',
                                        'message': f'Critical error: {str(e)}',
                                        'log': log_stream.getvalue()
                                    })
                            
                            # Update the log
                            job['log'] = log_stream.getvalue()
                        
                        # Start the background thread
                        thread = Thread(target=scrape_in_background)
                        thread.daemon = True
                        thread.start()
                        
                        return JsonResponse({
                            'status': 'started',
                            'job_id': job_id
                        })
                    except Exception as e:
                        logger.error(f"Error starting async scrape: {str(e)}\n{traceback.format_exc()}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Error starting scrape: {str(e)}',
                            'log': log_stream.getvalue()
                        })
                else:
                    # Synchronous scraping (we'll remove this since we always use async)
                    messages.error(request, 'Please enable async scraping for better performance.')
                    return redirect('events:import')
            elif scraper_type == 'generic':
                # Use Generic scraper
                source_url = request.POST.get('source_url')
                if not source_url:
                    if is_async:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Please provide a URL to scrape.'
                        })
                    messages.error(request, 'Please provide a URL to scrape.')
                    return redirect('events:import')
                
                # Clear the log buffer before scraping
                log_stream.seek(0)
                log_stream.truncate()
                
                api_key = os.getenv('FIRECRAWL_API_KEY')
                if not api_key:
                    error_msg = "FIRECRAWL_API_KEY environment variable is not set"
                    if is_async:
                        return JsonResponse({
                            'status': 'error',
                            'message': error_msg
                        })
                    messages.error(request, error_msg)
                    return redirect('events:import')
                
                scraper = GenericScraper(api_key=api_key)
                
                if is_async:
                    try:
                        # Start async scraping job
                        job_id = f"scrape_{len(scraping_jobs)}"
                        scraping_jobs[job_id] = {
                            'status': 'running',
                            'events': [],
                            'log': '',
                            'source_url': source_url,
                            'user': request.user
                        }
                        
                        # Start the scraping in a background thread
                        def scrape_in_background():
                            try:
                                # Get the job from the global dict
                                job = scraping_jobs[job_id]
                                
                                try:
                                    # Use the new retry logic
                                    events_data = scraper.extract_events_with_retry(source_url)
                                    logger.info("Scraping completed successfully")
                                    
                                    if events_data:
                                        processed_events = []
                                        for event_data in events_data:
                                            try:
                                                logger.info(f"Processing event: {event_data.get('title')}")
                                                
                                                # Check if event already exists
                                                title = event_data.get('title', '')
                                                start_time = event_data.get('start_time')
                                                venue_name = event_data.get('venue_name', '')
                                                
                                                # Try to find an existing event with same title, date and venue
                                                existing_event = Event.objects.filter(
                                                    user=job['user'],
                                                    title=title,
                                                    start_time=start_time,
                                                    venue_name=venue_name
                                                ).first()
                                                
                                                if existing_event:
                                                    logger.info(f"Event already exists: {title} at {venue_name}")
                                                    continue
                                                
                                                # Create and save the event if it doesn't exist
                                                event = Event(user=job['user'])
                                                
                                                # Update fields from event_data
                                                for field, value in event_data.items():
                                                    if hasattr(event, field):
                                                        setattr(event, field, value)
                                                
                                                # Save the event
                                                event.save()
                                                
                                                # Only append the minimal data needed for display
                                                processed_events.append({
                                                    'id': event.id,
                                                    'title': event.title,
                                                    'start_time': event.start_time,
                                                    'venue_name': event.venue_name
                                                })
                                                logger.info(f"Processed event: {event_data.get('title')}")
                                            except Exception as e:
                                                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
                                        
                                        # Update job status
                                        job['status'] = 'complete'
                                        job['events'] = processed_events
                                        job['message'] = f'Successfully imported {len(processed_events)} events'
                                    else:
                                        logger.warning("No events found in extraction result")
                                        job['status'] = 'complete'
                                        job['message'] = 'No events found at the provided URL'
                                    
                                except RequestException as e:
                                    logger.error(f"API connection error: {str(e)}")
                                    job['status'] = 'error'
                                    job['message'] = f'API connection error: {str(e)}'
                                except Exception as e:
                                    logger.error(f"Error in background scraping: {str(e)}\n{traceback.format_exc()}")
                                    job['status'] = 'error'
                                    job['message'] = str(e)
                                
                            except Exception as e:
                                logger.error(f"Critical error in background thread: {str(e)}\n{traceback.format_exc()}")
                                if job_id in scraping_jobs:
                                    scraping_jobs[job_id].update({
                                        'status': 'error',
                                        'message': f'Critical error: {str(e)}',
                                        'log': log_stream.getvalue()
                                    })
                            
                            # Update the log
                            job['log'] = log_stream.getvalue()
                        
                        # Start the background thread
                        thread = Thread(target=scrape_in_background)
                        thread.daemon = True
                        thread.start()
                        
                        return JsonResponse({
                            'status': 'started',
                            'job_id': job_id
                        })
                    except Exception as e:
                        logger.error(f"Error starting async scrape: {str(e)}\n{traceback.format_exc()}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Error starting scrape: {str(e)}',
                            'log': log_stream.getvalue()
                        })
                else:
                    # Synchronous scraping (we'll remove this since we always use async)
                    messages.error(request, 'Please enable async scraping for better performance.')
                    return redirect('events:import')
            else:
                if is_async:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Unknown scraper type: {scraper_type}'
                    })
                messages.error(request, f'Unknown scraper type: {scraper_type}')
                return redirect('events:import')

            if not is_async:
                # Process and save events for synchronous requests
                valid_events = []
                skipped_events = []
                
                for event_data in events_data:
                    try:
                        # Create event but don't save yet
                        event = Event(user=request.user)
                        
                        # Update fields from event_data
                        for field, value in event_data.items():
                            if hasattr(event, field):
                                setattr(event, field, value)
                        
                        # Save the event
                        event.save()
                        valid_events.append(event_data)
                    except Exception as e:
                        event_data['reason'] = str(e)
                        skipped_events.append(event_data)
                
                # Show success message with details about skipped events
                success_msg = f'Successfully imported {len(valid_events)} events'
                if skipped_events:
                    success_msg += f'. {len(skipped_events)} events were skipped:'
                    for event in skipped_events:
                        success_msg += f"\n- {event.get('title', 'Unknown event')}: {event.get('reason', 'Unknown error')}"
                
                messages.success(request, success_msg)
                return redirect('events:list')

        except Exception as e:
            logger.error(f"Error during import: {str(e)}\n{traceback.format_exc()}")
            error_msg = f'Failed to import events: {str(e)}'
            log_output = log_stream.getvalue()
            if log_output:
                error_msg += f'\nDebug output:\n{log_output}'
            
            if is_async:
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                })
            messages.error(request, error_msg)
            return redirect('events:list')
    
    return render(request, 'events/import.html')

@login_required
def event_export(request):
    # Add export logic here
    return render(request, 'events/export.html')