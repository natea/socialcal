from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Event
from .forms import EventForm
from .scrapers.generic_crawl4ai import scrape_events as scrape_crawl4ai_events
import io
import logging
import json
from threading import Thread
import traceback
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
        source_url = request.POST.get('source_url')
        if not source_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Please provide a URL to scrape.'
            })

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
                        # Use Crawl4AI scraper
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
                                        logger.info(f"Skipping duplicate event: {title} at {venue_name}")
                                        continue
                                    
                                    logger.info(f"Importing new event: {title} at {venue_name}")
                                    
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
    
    # If GET request, show the import form
    return render(request, 'events/import.html')

@login_required
def event_export(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'events/export.html', {'events': events})