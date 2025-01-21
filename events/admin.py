from django.contrib import admin
from .models import Event

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
