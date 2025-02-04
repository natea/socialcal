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

User = get_user_model()

def welcome(request):
    if request.user.is_authenticated:
        if request.user.profile.has_completed_onboarding:
            return redirect('core:home')
        return redirect('onboarding:event_types')
    return render(request, 'onboarding/welcome.html')

@login_required
def event_types(request):
    # If user doesn't have a Google account connected, redirect to welcome
    google_account = SocialAccount.objects.filter(
        user=request.user,
        provider='google'
    ).first()
    
    if not google_account:
        return redirect('onboarding:welcome')

    if request.method == 'POST':
        selected_types = request.POST.getlist('event_types')
        request.user.profile.event_preferences = selected_types
        request.user.profile.save()
        
        # If we have calendar access, skip the calendar sync step
        if request.user.profile.has_google_calendar_access:
            return redirect('onboarding:social_connect')
        return redirect('onboarding:calendar_sync')
        
    return render(request, 'onboarding/event_types.html')

@login_required
def calendar_sync(request):
    # Check if user has already connected Google account with calendar scope
    google_account = SocialAccount.objects.filter(
        user=request.user,
        provider='google'
    ).first()
    
    if google_account and request.user.profile.google_calendar_connected:
        # If already connected with calendar scope, redirect to next step
        return redirect('onboarding:social_connect')
        
    return render(request, 'onboarding/calendar_sync.html')

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
    messages.success(request, "Welcome to SoCal! Your profile is now set up.")
    return render(request, 'onboarding/complete.html')
