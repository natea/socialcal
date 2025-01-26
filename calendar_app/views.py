from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from calendar import monthcalendar
from events.models import Event
from django.utils import timezone
import pytz

@login_required
def calendar_view(request):
    today = timezone.localtime()
    return month_view(request, today.year, today.month)

@login_required
def month_view(request, year, month):
    # Get user's timezone from session or default to Eastern
    user_timezone = pytz.timezone(request.session.get('event_timezone', 'America/New_York'))
    timezone.activate(user_timezone)
    
    try:
        # Create datetime objects for start and end of month in user's timezone
        current_date = datetime(year, month, 1)
        current_date = user_timezone.localize(current_date)
        
        # Get the start and end of the month in user's timezone
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month == 12:
            end_of_month = current_date.replace(year=year + 1, month=1, day=1)
        else:
            end_of_month = current_date.replace(month=month + 1, day=1)
        end_of_month = end_of_month - timedelta(microseconds=1)
        
        # Convert to UTC for database query
        start_of_month_utc = start_of_month.astimezone(pytz.UTC)
        end_of_month_utc = end_of_month.astimezone(pytz.UTC)
        
        # Query events in UTC time range
        events = Event.objects.filter(
            start_time__gte=start_of_month_utc,
            start_time__lte=end_of_month_utc,
            user=request.user
        )
        
        cal = monthcalendar(year, month)
        
        context = {
            'calendar': cal,
            'events': events,
            'current_date': current_date,
            'prev_month': (current_date - timedelta(days=1)).replace(day=1),
            'next_month': (current_date + timedelta(days=32)).replace(day=1),
            'timezone': user_timezone,
        }
        return render(request, 'calendar_app/month.html', context)
    finally:
        # Reset timezone to UTC to avoid affecting other views
        timezone.deactivate()

@login_required
def week_view(request, year, week):
    # Add week view logic
    context = {'year': year, 'week': week}
    return render(request, 'calendar_app/week.html', context)

@login_required
def day_view(request, year, month, day):
    current_date = datetime(year, month, day)
    events = Event.objects.filter(
        start_time__date=current_date.date(),
        user=request.user
    )
    context = {
        'current_date': current_date,
        'events': events,
    }
    return render(request, 'calendar_app/day.html', context) 