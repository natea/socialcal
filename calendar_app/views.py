from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from calendar import monthcalendar
from events.models import Event

@login_required
def calendar_view(request):
    today = datetime.today()
    return month_view(request, today.year, today.month)

@login_required
def month_view(request, year, month):
    current_date = datetime(year, month, 1)
    cal = monthcalendar(year, month)
    events = Event.objects.filter(
        start_time__year=year,
        start_time__month=month,
        user=request.user
    )
    
    context = {
        'calendar': cal,
        'events': events,
        'current_date': current_date,
        'prev_month': (current_date - timedelta(days=1)).replace(day=1),
        'next_month': (current_date + timedelta(days=32)).replace(day=1),
    }
    return render(request, 'calendar_app/month.html', context)

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