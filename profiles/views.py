from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Profile
from .forms import ProfileForm
from django.utils import timezone

User = get_user_model()

def profile_list(request):
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'profiles/list.html', {'profiles': profiles})

def profile_detail(request, email):
    user = get_object_or_404(User, email=email)
    profile = get_object_or_404(Profile, user=user)
    
    # Show events if the profile owner is viewing or if calendar is public
    events = []
    if (request.user.is_authenticated and request.user == user) or profile.calendar_public:
        events = user.events.filter(
            start_time__gte=timezone.now(),
            is_public=True
        ).order_by('start_time')
        
        # If user is the owner, also show private events
        if request.user.is_authenticated and request.user == user:
            private_events = user.events.filter(
                start_time__gte=timezone.now(),
                is_public=False
            ).order_by('start_time')
            events = list(events) + list(private_events)
    
    context = {
        'profile': profile,
        'events': events,
        'can_view_events': (request.user.is_authenticated and request.user == user) or profile.calendar_public,
    }
    return render(request, 'profiles/detail.html', context)

@login_required
def profile_edit(request, email):
    if request.user.email != email:
        return redirect('profiles:detail', email=email)
    
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profiles:detail', email=email)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profiles/edit.html', {'form': form})

@login_required
def profile_calendar(request, email):
    user = get_object_or_404(User, email=email)
    profile = get_object_or_404(Profile, user=user)
    
    # Only show calendar if the viewer is the owner or calendar is public
    if request.user != user and not profile.calendar_public:
        return redirect('profiles:detail', email=email)
    
    events = user.events.all().order_by('start_time')
    return render(request, 'profiles/calendar.html', {'events': events, 'profile': profile}) 