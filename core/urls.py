from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('search/', views.search, name='search'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    # Always registered so it is reversible regardless of DEBUG; the view
    # itself only raises in DEBUG mode and otherwise returns a harmless
    # response, so it is safe to expose in production.
    path('debug/error/', views.debug_error, name='debug_error'),
] 