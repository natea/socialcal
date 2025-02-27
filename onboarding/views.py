from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from allauth.socialaccount.models import SocialApp, SocialAccount
from allauth.socialaccount.views import ConnectionsView
from django.contrib.auth import get_user_model
from allauth.account.views import SignupView
from django.urls import reverse_lazy
from django.utils import timezone

User = get_user_model()

def welcome(request):
    if request.user.is_authenticated and request.user.profile.has_completed_onboarding:
        return redirect('calendar:index')
    return render(request, 'onboarding/welcome.html')

@login_required
def google_oauth(request):
    """Handle Google OAuth flow"""
    next_url = reverse('onboarding:event_types')
    scopes = "openid+email+profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events"
    return redirect(f"/accounts/google/login/?process=oauth&scope={scopes}&next={next_url}")

@login_required
def google_calendar_permissions(request):
    """Handle Google Calendar permissions"""
    return render(request, 'onboarding/google_calendar_permissions.html')

@login_required
def event_types(request):
    # Check if user has a Google account connected
    google_account = SocialAccount.objects.filter(
        user=request.user,
        provider='google'
    ).first()
    
    if request.method == 'POST':
        selected_types = request.POST.getlist('event_types')
        request.user.profile.event_preferences = selected_types
        request.user.profile.save()
        
        # If we have calendar access, skip the calendar sync step
        if request.user.profile.has_google_calendar_access:
            return redirect('onboarding:social_connect')
        return redirect('onboarding:calendar_sync')
    
    context = {
        'has_google_account': bool(google_account),
        'has_calendar_access': request.user.profile.has_google_calendar_access if google_account else False
    }
    return render(request, 'onboarding/event_types.html', context)

@login_required
def calendar_sync(request):
    # Check if user has already connected Google account with calendar scope
    google_account = SocialAccount.objects.filter(
        user=request.user,
        provider='google'
    ).first()
    
    has_calendar_access = request.user.profile.has_google_calendar_access if google_account else False
    
    context = {
        'has_calendar_access': has_calendar_access
    }
    return render(request, 'onboarding/calendar_sync.html', context)

@login_required
def social_connect(request):
    social_apps = [app.provider for app in SocialApp.objects.all()]
    context = {
        'social_apps': social_apps,
    }
    return render(request, 'onboarding/social_connect.html', context)

@login_required
def complete(request):
    request.user.profile.has_completed_onboarding = True
    request.user.profile.save()
    messages.success(request, "Welcome to SocialCal! Your profile is now set up.")
    
    # Get current date for the calendar week view
    today = timezone.localtime()
    return redirect('calendar:week', year=today.year, month=today.month, day=today.day)
