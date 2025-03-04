from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('create/', views.event_create, name='create'),
    path('<int:pk>/', views.event_detail, name='detail'),
    path('<int:pk>/edit/', views.event_edit, name='edit'),
    path('<int:pk>/delete/', views.event_delete, name='delete'),
    path('import/', views.scraper_list, name='import'),
    path('import/status/<str:job_id>/', views.event_import_status, name='import_status'),
    path('export/', views.event_export, name='export'),
    path('spotify/search/', views.spotify_search, name='spotify_search'),
    path('export/ical/', views.export_ical, name='export_ical'),
    
    # Site Scraper URLs
    path('scrapers/', views.scraper_list, name='scraper_list'),
    path('scrapers/create/', views.scraper_create, name='scraper_create'),
    path('scrapers/<int:pk>/', views.scraper_detail, name='scraper_detail'),
    path('scrapers/<int:pk>/edit/', views.scraper_edit, name='scraper_edit'),
    path('scrapers/<int:pk>/delete/', views.scraper_delete, name='scraper_delete'),
    path('scrapers/<int:pk>/test/', views.scraper_test, name='scraper_test'),
    path('scrapers/test/status/<str:job_id>/', views.scraper_test_status, name='scraper_test_status'),
    path('scrapers/<int:pk>/import/', views.scraper_import, name='scraper_import'),
    path('scrapers/schema/status/<str:job_id>/', views.scraper_schema_status, name='scraper_schema_status'),
    path('scrapers/<int:pk>/regenerate-schema/', views.scraper_regenerate_schema, name='scraper_regenerate_schema'),
]
