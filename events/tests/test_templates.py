import pytest
from django.urls import reverse
from django.utils import timezone
from bs4 import BeautifulSoup
from events.models import Event

@pytest.mark.django_db
class TestWebcalLinks:
    def test_webcal_links_in_templates(self, authenticated_client, user):
        # Create a test event
        event = Event.objects.create(
            user=user,
            title="Test Event",
            description="Test Description",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            venue_name="Test Venue",
            is_public=True
        )

        # Test event detail page
        detail_url = reverse('events:detail', args=[event.id])
        response = authenticated_client.get(detail_url)
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        webcal_link = soup.find('a', attrs={'data-protocol': 'webcal'})
        assert webcal_link is not None
        assert 'Add to Calendar' in webcal_link.text
        
        # Test event list page
        list_url = reverse('events:list')
        response = authenticated_client.get(list_url)
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        webcal_link = soup.find('a', attrs={'data-protocol': 'webcal'})
        assert webcal_link is not None
        assert 'Subscribe to All Events' in webcal_link.text

        # Test calendar month view
        month_url = reverse('calendar:month', kwargs={
            'year': timezone.now().year,
            'month': timezone.now().month
        })
        response = authenticated_client.get(month_url)
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        webcal_link = soup.find('a', attrs={'data-protocol': 'webcal'})
        assert webcal_link is not None
        assert 'Add to Calendar' in webcal_link.text
