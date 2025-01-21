from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from allauth.account.views import confirm_email

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication (using django-allauth)
    path('accounts/', include('allauth.urls')),
    re_path(r'^accounts/confirm-email/(?P<key>[-:\w]+)/$', confirm_email, name='account_confirm_email'),

    # Calendar Views
    path('calendar/', include('calendar_app.urls')),

    # Event Management
    path('events/', include('events.urls')),

    # User Profiles
    path('profiles/', include('profiles.urls')),

    # API endpoints
    path('api/', include('api.urls')),

    # Homepage
    path('', include('core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
