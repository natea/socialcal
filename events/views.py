from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Event
from .forms import EventForm
from .scrapers.ical_scraper import ICalScraper
import io
import logging
import json
from threading import Thread, Lock
import time
from requests.exceptions import HTTPError, RequestException
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
# Lock for preventing multiple scrapes of the same URL
scraping_locks = {}

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
        source_url = request.POST.get('source_url')
        
        # Create a lock for this URL if it doesn't exist
        if source_url not in scraping_locks:
            scraping_locks[source_url] = Lock()
        
        # Try to acquire the lock
        if not scraping_locks[source_url].acquire(blocking=False):
            if is_async:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Another import is already in progress for this URL'
                })
            messages.error(request, 'Another import is already in progress for this URL')
            return redirect('events:import')
        
        try:
            if scraper_type == 'ical':
                # Use iCal scraper
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
                            'user': request.user,
                            'lock': scraping_locks[source_url]  # Store the lock with the job
                        }
                        
                        # Start the scraping in a background thread
                        def scrape_in_background():
                            try:
                                # Get the job from the global dict
                                job = scraping_jobs[job_id]
                                
                                try:
                                    # Initialize iCal scraper
                                    scraper = ICalScraper()
                                    
                                    # Process events
                                    events_data = scraper.process_events(source_url)
                                    logger.info("iCal scraping completed successfully")
                                    
                                    if events_data:
                                        processed_events = []
                                        updated_count = 0
                                        created_count = 0
                                        
                                        for event_data in events_data:
                                            try:
                                                logger.info(f"Processing event: {event_data.get('title')}")
                                                
                                                # Check for existing event
                                                existing = Event.objects.filter(
                                                    user=job['user'],
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
                                                    logger.info(f"Updated existing event: {existing.title}")
                                                else:
                                                    # Create new event
                                                    event = Event(user=job['user'])
                                                    for field, value in event_data.items():
                                                        if hasattr(event, field):
                                                            setattr(event, field, value)
                                                    event.save()
                                                    created_count += 1
                                                    logger.info(f"Created new event: {event.title}")
                                                
                                                processed_events.append(event_data)
                                            except Exception as e:
                                                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
                                        
                                        # Update job status
                                        job['status'] = 'complete'
                                        job['events'] = processed_events
                                        job['message'] = f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
                                        if scraper.selected_url and scraper.selected_url != source_url:
                                            job['message'] += f'\nUsed calendar URL: {scraper.selected_url}'
                                        logger.info(job['message'])
                                    else:
                                        logger.warning("No events found in calendar")
                                        job['status'] = 'complete'
                                        job['message'] = 'No events found in the calendar'
                                    
                                except Exception as e:
                                    logger.error(f"Error in iCal scraping: {str(e)}\n{traceback.format_exc()}")
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
                            finally:
                                # Always release the lock when done
                                job['lock'].release()
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
                        # Release lock if there's an error starting the thread
                        scraping_locks[source_url].release()
                        logger.error(f"Error starting async scrape: {str(e)}\n{traceback.format_exc()}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Error starting scrape: {str(e)}',
                            'log': log_stream.getvalue()
                        })
                else:
                    try:
                        # Synchronous scraping
                        scraper = ICalScraper()
                        events_data = scraper.process_events(source_url)
                        
                        # Add message about which URL was used if it was discovered
                        if scraper.selected_url and scraper.selected_url != source_url:
                            messages.info(request, f'Using calendar URL: {scraper.selected_url}')
                    finally:
                        # Release lock after synchronous scraping
                        scraping_locks[source_url].release()
            elif scraper_type == 'crawl4ai':
                # Use Crawl4AI scraper
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
                            'user': request.user,
                            'lock': scraping_locks[source_url]  # Store the lock with the job
                        }
                        
                        # Start the scraping in a background thread
                        def scrape_in_background():
                            try:
                                # Get the job from the global dict
                                job = scraping_jobs[job_id]
                                
                                try:
                                    # Run the async scraper in a new event loop
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    events_data = loop.run_until_complete(scrape_crawl4ai_events(source_url))
                                    loop.close()
                                    
                                    logger.info("Crawl4AI scraping completed successfully")
                                    logger.info(f"Raw events data: {json.dumps(events_data, indent=2)}")
                                    
                                    if events_data:
                                        processed_events = []
                                        updated_count = 0
                                        created_count = 0
                                        
                                        for event_data in events_data:
                                            try:
                                                logger.info(f"Processing event: {event_data.get('title')}")
                                                
                                                # Check for existing event
                                                existing = Event.objects.filter(
                                                    user=job['user'],
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
                                                    logger.info(f"Updated existing event: {existing.title}")
                                                else:
                                                    # Create new event
                                                    event = Event(user=job['user'])
                                                    for field, value in event_data.items():
                                                        if hasattr(event, field):
                                                            setattr(event, field, value)
                                                    event.save()
                                                    created_count += 1
                                                    logger.info(f"Created new event: {event.title}")
                                                
                                                processed_events.append(event_data)
                                            except Exception as e:
                                                logger.error(f"Error processing event: {str(e)}\n{traceback.format_exc()}")
                                        
                                        # Update job status
                                        job['status'] = 'complete'
                                        job['events'] = processed_events
                                        job['message'] = f'Successfully processed {len(processed_events)} events ({created_count} created, {updated_count} updated)'
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
                            finally:
                                # Always release the lock when done
                                job['lock'].release()
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
                        # Release lock if there's an error starting the thread
                        scraping_locks[source_url].release()
                        logger.error(f"Error starting async scrape: {str(e)}\n{traceback.format_exc()}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Error starting scrape: {str(e)}',
                            'log': log_stream.getvalue()
                        })
                else:
                    try:
                        # Synchronous scraping
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        events_data = loop.run_until_complete(scrape_crawl4ai_events(source_url))
                        loop.close()
                    finally:
                        # Release lock after synchronous scraping
                        scraping_locks[source_url].release()
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
                updated_count = 0
                created_count = 0
                
                for event_data in events_data:
                    try:
                        # Check for existing event
                        existing = Event.objects.filter(
                            user=request.user,
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
                            valid_events.append(event_data)
                        else:
                            # Create new event
                            event = Event(user=request.user)
                            for field, value in event_data.items():
                                if hasattr(event, field):
                                    setattr(event, field, value)
                            event.save()
                            created_count += 1
                            valid_events.append(event_data)
                    except Exception as e:
                        event_data['reason'] = str(e)
                        skipped_events.append(event_data)
                
                # Show success message with details about skipped events
                success_msg = f'Successfully processed {len(valid_events)} events ({created_count} created, {updated_count} updated)'
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
            else:
                messages.error(request, error_msg)
                return redirect('events:import')
    
    # If GET request, show the import form
    return render(request, 'events/import.html')

@login_required
def event_export(request):
    events = Event.objects.filter(user=request.user)
    return render(request, 'events/export.html', {'events': events})