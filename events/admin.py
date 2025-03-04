from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Event, SiteScraper

class UserFilter(admin.SimpleListFilter):
    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        users = get_user_model().objects.filter(
            id__in=Event.objects.values_list('user_id', flat=True)
        ).order_by('username')
        return [(user.id, user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value())
        return queryset

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'venue_name',
        'start_time',
        'end_time',
        'user',
        'is_public',
        'created_at'
    ]
    list_filter = [
        UserFilter,
        'is_public',
        'venue_city',
        'venue_state',
        'created_at',
        'start_time'
    ]
    search_fields = [
        'title',
        'description',
        'venue_name',
        'venue_city'
    ]
    date_hierarchy = 'start_time'
    ordering = ['-start_time']
    actions = ['make_public', 'make_private']
    
    def make_public(self, request, queryset):
        queryset.update(is_public=True)
    make_public.short_description = "Make selected events public"
    
    def make_private(self, request, queryset):
        queryset.update(is_public=False)
    make_private.short_description = "Make selected events private"

    def delete_queryset(self, request, queryset):
        """
        Override the delete_queryset method to delete related records before deleting the events.
        This is needed because there are foreign key relationships with the Event model.
        """
        # Get the IDs of the events to delete
        event_ids = list(queryset.values_list('id', flat=True))
        
        # Delete related records in events_event_labels
        from django.db import connection
        with connection.cursor() as cursor:
            # Use %s as Django will convert it to the appropriate placeholder for the database
            placeholders = ','.join(['%s' for _ in event_ids])
            
            # Delete related records in events_event_labels
            cursor.execute(f'DELETE FROM events_event_labels WHERE event_id IN ({placeholders})', event_ids)
            
            # Delete related records in events_eventresponse
            cursor.execute(f'DELETE FROM events_eventresponse WHERE event_id IN ({placeholders})', event_ids)
            
            # Delete related records in events_starredevent
            cursor.execute(f'DELETE FROM events_starredevent WHERE event_id IN ({placeholders})', event_ids)
        
        # Now delete the events
        super().delete_queryset(request, queryset)

class SiteScraperUserFilter(admin.SimpleListFilter):
    title = 'User'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        users = get_user_model().objects.filter(
            id__in=SiteScraper.objects.values_list('user_id', flat=True)
        ).order_by('username')
        return [(user.id, user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_id=self.value())
        return queryset

@admin.register(SiteScraper)
class SiteScraperAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'url',
        'user',
        'is_active',
        'last_tested',
        'created_at'
    ]
    list_filter = [
        SiteScraperUserFilter,
        'is_active',
        'created_at',
        'last_tested'
    ]
    search_fields = [
        'name',
        'url',
        'description'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "Make selected scrapers active"
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "Make selected scrapers inactive"
