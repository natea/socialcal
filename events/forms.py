from django import forms
from .models import Event
import pytz
from django.conf import settings
from django.utils import timezone

class EventForm(forms.ModelForm):
    timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        initial='America/New_York',
        help_text='Select the timezone for this event'
    )

    class Meta:
        model = Event
        fields = [
            'title', 
            'description', 
            'venue_name',
            'venue_address',
            'venue_city',
            'venue_state',
            'venue_postal_code',
            'venue_country',
            'start_time', 
            'end_time', 
            'url',
            'image_url',
            'is_public'
        ]
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={'rows': 4}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_address': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_city': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_state': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_country': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get timezone from POST data, session, or default to Eastern
        if self.data:
            # If form was submitted, use the submitted timezone
            tz_name = self.data.get('timezone', 'America/New_York')
            self.initial['timezone'] = tz_name
        elif 'timezone' in self.initial:
            # If timezone was provided in initial data, use it
            tz_name = self.initial['timezone']
        else:
            # Default to Eastern Time
            tz_name = 'America/New_York'
            self.initial['timezone'] = tz_name
        
        local_tz = pytz.timezone(tz_name)
        
        # Convert datetime to local time for form display
        if self.instance.pk:
            if self.instance.start_time:
                # Convert times from UTC to local timezone
                local_start = self.instance.start_time.astimezone(local_tz)
                self.initial['start_time'] = local_start.strftime('%Y-%m-%dT%H:%M')
                
            if self.instance.end_time:
                local_end = self.instance.end_time.astimezone(local_tz)
                self.initial['end_time'] = local_end.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        timezone_name = cleaned_data.get('timezone')

        if start_time and timezone_name:
            # Get the target timezone
            tz = pytz.timezone(timezone_name)
            
            # Make sure we have a naive datetime before localizing
            if timezone.is_aware(start_time):
                start_time = start_time.replace(tzinfo=None)
            
            # Localize to the selected timezone and convert to UTC
            start_time = tz.localize(start_time).astimezone(pytz.UTC)
            cleaned_data['start_time'] = start_time

        if end_time and timezone_name:
            # Do the same for end_time
            tz = pytz.timezone(timezone_name)
            
            if timezone.is_aware(end_time):
                end_time = end_time.replace(tzinfo=None)
                
            end_time = tz.localize(end_time).astimezone(pytz.UTC)
            cleaned_data['end_time'] = end_time

        return cleaned_data 