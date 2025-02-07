from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from .models import Profile, Label
from .forms import ProfileForm, LabelForm
from django.utils import timezone

User = get_user_model()

def profile_list(request):
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'profiles/list.html', {'profiles': profiles})

def profile_detail(request, email):
    user = get_object_or_404(User, email=email)
    profile = get_object_or_404(Profile, user=user)
    
    # Get this week's events
    start_of_week = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timezone.timedelta(days=7)
    
    events_this_week = user.events.filter(
        start_time__gte=start_of_week,
        start_time__lt=end_of_week
    )
    
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
    
    # Get social accounts
    social_accounts = {}
    if hasattr(user, 'socialaccount_set'):
        for account in user.socialaccount_set.all():
            social_accounts[account.provider] = account
    
    # Create forms for labels
    label_form = LabelForm(user=request.user) if request.user.is_authenticated and request.user == user else None
    label_edit_forms = {}
    if request.user.is_authenticated and request.user == user:
        for label in user.labels.all():
            label_edit_forms[label.id] = LabelForm(instance=label, user=request.user)
    
    context = {
        'profile': profile,
        'events': events,
        'events_this_week': events_this_week,
        'social_accounts': social_accounts,
        'can_view_events': (request.user.is_authenticated and request.user == user) or profile.calendar_public,
        'label_form': label_form,
        'label_edit_forms': label_edit_forms,
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

@login_required
def add_label(request):
    if request.method == 'POST':
        form = LabelForm(request.POST, user=request.user)
        if form.is_valid():
            label = form.save(commit=False)
            label.user = request.user
            label.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Label added successfully',
                    'label': {
                        'id': label.id,
                        'name': label.name,
                        'color': label.color
                    }
                })
            messages.success(request, 'Label added successfully.')
            return redirect('profiles:detail', email=request.user.email)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = LabelForm(user=request.user)
    return render(request, 'profiles/label_form.html', {'form': form})

@login_required
def edit_label(request, label_id):
    label = get_object_or_404(Label, id=label_id, user=request.user)
    if request.method == 'POST':
        form = LabelForm(request.POST, instance=label, user=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Label updated successfully',
                    'label': {
                        'id': label.id,
                        'name': label.name,
                        'color': label.color
                    }
                })
            messages.success(request, 'Label updated successfully.')
            return redirect('profiles:detail', email=request.user.email)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = LabelForm(instance=label, user=request.user)
    return render(request, 'profiles/label_form.html', {'form': form, 'label': label})

@login_required
def delete_label(request, label_id):
    label = get_object_or_404(Label, id=label_id, user=request.user)
    if request.method == 'POST':
        label.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Label deleted successfully'
            })
        messages.success(request, 'Label deleted successfully.')
        return redirect('profiles:detail', email=request.user.email)
    return render(request, 'profiles/delete_label.html', {'label': label}) 