from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse

def home(request):
    if request.user.is_authenticated:
        # For authenticated users, redirect to the week view with current date
        today = timezone.now()
        return redirect(reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        }))
    else:
        # For unauthenticated users, redirect to the onboarding welcome page
        return redirect('onboarding:welcome')

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

@login_required
def search(request):
    query = request.GET.get('q', '')
    # Add search logic here
    context = {'query': query, 'results': []}
    return render(request, 'core/search.html', context) 