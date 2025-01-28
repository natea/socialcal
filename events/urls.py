from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('create/', views.event_create, name='create'),
    path('<int:pk>/', views.event_detail, name='detail'),
    path('<int:pk>/edit/', views.event_edit, name='edit'),
    path('<int:pk>/delete/', views.event_delete, name='delete'),
    path('import/', views.event_import, name='import'),
    path('import/status/<str:job_id>/', views.event_import_status, name='import_status'),
    path('export/', views.event_export, name='export'),
    path('spotify/search/', views.spotify_search, name='spotify_search'),
    path('export/ical/', views.export_ical, name='export_ical'),
]
