from django.urls import path
from . import views
from django.conf import settings

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('search/', views.search, name='search'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
]

# Add debug routes only in DEBUG mode
if settings.DEBUG:
    urlpatterns += [
        path('debug/error/', views.debug_error, name='debug_error'),
    ] 