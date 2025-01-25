from django.db import models
from django.conf import settings
from django.urls import reverse

class Event(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
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