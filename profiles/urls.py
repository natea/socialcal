from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.profile_list, name='list'),
    path('<str:username>/', views.profile_detail, name='detail'),
    path('<str:username>/edit/', views.profile_edit, name='edit'),
    path('<str:username>/calendar/', views.profile_calendar, name='calendar'),
] 