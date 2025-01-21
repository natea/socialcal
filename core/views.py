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