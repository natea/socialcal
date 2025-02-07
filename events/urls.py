from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='list'),
    path('starred/', views.starred_events, name='starred'),
    path('create/', views.event_create, name='create'),
    path('<int:pk>/', views.event_detail, name='detail'),
    path('<int:pk>/edit/', views.event_edit, name='edit'),
    path('<int:pk>/delete/', views.event_delete, name='delete'),
    path('import/', views.event_import, name='import'),
    path('import/status/<str:job_id>/', views.event_import_status, name='import_status'),
    path('export/', views.event_export, name='export'),
    path('spotify/search/', views.spotify_search, name='spotify_search'),
    path('export/ical/', views.export_ical, name='export_ical'),
    path('week/', views.WeekView.as_view(), name='week'),
    path('week/<int:year>/<int:month>/<int:day>/', views.WeekView.as_view(), name='week_date'),
    path('api/events/<str:date>/', views.get_day_events, name='day_events'),
    path('<int:pk>/response/', views.update_event_response, name='update_response'),
    path('<int:pk>/star/', views.toggle_star_event, name='toggle_star'),
]
