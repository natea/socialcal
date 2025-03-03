from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse
from django.views.generic import TemplateView

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

def index(request):
    """
    View for the homepage.
    """
    return render(request, 'core/index.html')

def privacy(request):
    """
    View for the privacy policy page.
    """
    return render(request, 'core/privacy.html')

def terms_of_service(request):
    """
    View for the terms of service page.
    """
    return render(request, 'core/terms_of_service.html')

def debug_error(request):
    """
    View that intentionally raises an exception to test error handling.
    Only available in DEBUG mode.
    """
    from django.conf import settings
    if settings.DEBUG:
        # Intentionally raise an exception to test error handling
        raise Exception("This is a test exception to verify error handling")
    return HttpResponse("Debug error view only available in DEBUG mode") 