from django.urls import path
from . import views

app_name = 'calendar'

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('month/<int:year>/<int:month>/', views.month_view, name='month'),
    path('week/<int:year>/<int:week>/', views.week_view, name='week'),
    path('day/<int:year>/<int:month>/<int:day>/', views.day_view, name='day'),
] 