from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Profile
from .forms import ProfileForm

User = get_user_model()

def profile_list(request):
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'profiles/list.html', {'profiles': profiles})

def profile_detail(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    return render(request, 'profiles/detail.html', {'profile': profile})

@login_required
def profile_edit(request, username):
    if request.user.username != username:
        return redirect('profiles:detail', username=username)
    
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profiles:detail', username=username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profiles/edit.html', {'form': form})

@login_required
def profile_calendar(request, username):
    user = get_object_or_404(User, username=username)
    if request.user != user:
        # Add logic for public/private calendar viewing permissions
        pass
    events = user.events.all()  # Assuming related_name='events' in Event model
    return render(request, 'profiles/calendar.html', {'events': events}) 