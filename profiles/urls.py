from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.profile_list, name='list'),
    path('<str:email>/', views.profile_detail, name='detail'),
    path('<str:email>/edit/', views.profile_edit, name='edit'),
    path('<str:email>/calendar/', views.profile_calendar, name='calendar'),
] 