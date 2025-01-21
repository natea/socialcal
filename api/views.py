from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from events.models import Event
from profiles.models import Profile
from .serializers import EventSerializer, ProfileSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.action == 'list':
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        profile = self.get_object()
        events = Event.objects.filter(user=profile.user)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data) 