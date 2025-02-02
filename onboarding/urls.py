from django.urls import path
from . import views

app_name = 'onboarding'

urlpatterns = [
    path('welcome/', views.welcome, name='welcome'),
    path('event-types/', views.event_types, name='event_types'),
    path('calendar-sync/', views.calendar_sync, name='calendar_sync'),
    path('social-connect/', views.social_connect, name='social_connect'),
    path('complete/', views.complete, name='complete'),
]
