from django.db import models
from django.conf import settings
from django.urls import reverse
from profiles.models import Label

class Event(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    labels = models.ManyToManyField(Label, related_name='events', blank=True)
    
    # Venue Information
    venue_name = models.CharField(max_length=200, blank=True)
    venue_address = models.CharField(max_length=200, blank=True)
    venue_city = models.CharField(max_length=100, blank=True)
    venue_state = models.CharField(max_length=100, blank=True)
    venue_postal_code = models.CharField(max_length=20, blank=True)
    venue_country = models.CharField(max_length=100, blank=True, default='United States')
    
    # Event Times
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    
    # URLs
    url = models.URLField(max_length=500, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    
    # Spotify Integration
    spotify_track_id = models.CharField(max_length=100, blank=True)
    spotify_track_name = models.CharField(max_length=200, blank=True)
    spotify_artist_id = models.CharField(max_length=100, blank=True)
    spotify_artist_name = models.CharField(max_length=200, blank=True)
    spotify_preview_url = models.URLField(max_length=500, blank=True)
    spotify_external_url = models.URLField(max_length=500, blank=True)
    
    # Settings
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'events'
        ordering = ['start_time']
        
    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        return reverse('events:detail', kwargs={'pk': self.pk})
        
    @property
    def location(self):
        """Return a formatted string of the venue's full address."""
        parts = [
            self.venue_name,
            self.venue_address,
            self.venue_city,
            self.venue_state,
            self.venue_postal_code,
            self.venue_country
        ]
        return ', '.join(part for part in parts if part)
        
    def get_full_address(self):
        """Return the full address as a string."""
        return self.location

class EventResponse(models.Model):
    RESPONSE_CHOICES = [
        ('going', 'Going'),
        ('not_going', 'Not Going'),
        ('pending', 'Pending'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_responses'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    status = models.CharField(
        max_length=20,
        choices=RESPONSE_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'event']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username}'s response to {self.event.title}: {self.status}"

class StarredEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='starred_events'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='starred_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'event']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} starred {self.event.title}"