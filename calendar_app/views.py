from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from calendar import monthcalendar
from events.models import Event
from django.utils import timezone
import pytz

@login_required
def calendar_view(request):
    """Default calendar view - redirects to week view"""
    today = timezone.localtime()
    return week_view(request, today.year, today.month, today.day)

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
            'view_type': 'month',
        }
        return render(request, 'calendar_app/month.html', context)
    finally:
        # Reset timezone to UTC to avoid affecting other views
        timezone.deactivate()

@login_required
def week_view(request, year, month, day):
    # Get user's timezone from session or default to Eastern
    user_timezone = pytz.timezone(request.session.get('event_timezone', 'America/New_York'))
    timezone.activate(user_timezone)
    
    try:
        # Create datetime object for the selected date
        current_date = datetime(year, month, day)
        current_date = user_timezone.localize(current_date)
        
        # Get the start and end of the week
        week_start = current_date - timedelta(days=current_date.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Convert to UTC for database query
        week_start_utc = week_start.astimezone(pytz.UTC)
        week_end_utc = week_end.astimezone(pytz.UTC)
        
        # Query events for the week
        events = Event.objects.filter(
            start_time__gte=week_start_utc,
            start_time__lte=week_end_utc,
            user=request.user
        ).order_by('start_time')
        
        # Generate dates for the week view
        week_dates = []
        for i in range(7):
            date = week_start + timedelta(days=i)
            week_dates.append({
                'date': date,
                'today': date.date() == timezone.localtime().date(),
            })
        
        context = {
            'week_dates': week_dates,
            'events': events,
            'selected_date': current_date,
            'current_date': current_date,
            'timezone': user_timezone,
            'view_type': 'week',
        }
        return render(request, 'calendar_app/week.html', context)
    finally:
        # Reset timezone to UTC to avoid affecting other views
        timezone.deactivate()

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