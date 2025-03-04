from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'core/home.html')

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