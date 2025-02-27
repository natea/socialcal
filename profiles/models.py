from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

class Profile(models.Model):
    EVENT_TYPE_CHOICES = [
        ('music', 'Music Concerts'),
        ('sports', 'Sports Events'),
        ('food', 'Food Festivals'),
        ('tech', 'Tech Conferences'),
        ('art', 'Art Exhibitions'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    calendar_public = models.BooleanField(
        default=False,
        verbose_name="Make calendar public",
        help_text="If checked, other users can see your events. If unchecked, your events are private."
    )
    
    # Onboarding fields
    has_completed_onboarding = models.BooleanField(default=False)
    event_preferences = models.JSONField(default=list, blank=True)
    google_calendar_connected = models.BooleanField(default=False)
    has_google_calendar_access = models.BooleanField(default=False)
    
    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return f"{full_name}'s profile"
        return f"{self.user.email}'s profile"

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.user.email

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    try:
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)

class Label(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7)  # For hex color codes
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='labels')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    class Meta:
        unique_together = ['name', 'user']
        ordering = ['name']