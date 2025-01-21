from rest_framework import serializers
from events.models import Event
from profiles.models import Profile

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'location', 'start_time', 
                 'end_time', 'is_public', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Profile
        fields = ['id', 'username', 'bio', 'location', 'birth_date', 
                 'avatar', 'calendar_public'] 