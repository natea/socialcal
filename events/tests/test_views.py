import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, Client
from events.models import Event
from unittest.mock import patch, AsyncMock, MagicMock
import pytz
from requests.exceptions import HTTPError
import json
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.fixture
def authenticated_client(user):
    client = Client()
    client.login(username='testuser', password='testpass')
    return client

@pytest.fixture
def event(user):
    return Event.objects.create(
        user=user,
        title='Test Event',
        description='Test Description',
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(hours=1),
        venue_name='Test Venue',
        venue_address='123 Test St',
        venue_city='Test City',
        venue_state='TS',
        venue_postal_code='12345',
        venue_country='Test Country',
        is_public=True
    )

@pytest.fixture
def unauthenticated_client():
    return Client()

class TestEventViews:
    def test_event_list_view(self, authenticated_client, event):
        url = reverse('events:list')
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert 'Test Event' in str(response.content)

    def test_event_list_view_unauthenticated(self, unauthenticated_client):
        url = reverse('events:list')
        response = unauthenticated_client.get(url)
        assert response.status_code == 302  # Redirects to login

    def test_event_create_view_get(self, authenticated_client):
        url = reverse('events:create')
        response = authenticated_client.get(url)
        assert response.status_code == 200

    def test_event_create_view_post(self, authenticated_client):
        url = reverse('events:create')
        data = {
            'title': 'Test Event',
            'description': 'Test Description',
            'start_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'end_time': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
            'timezone': 'America/New_York'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('events:list')
        assert Event.objects.filter(title='Test Event').exists()

    def test_event_create_view_post_invalid(self, authenticated_client):
        url = reverse('events:create')
        data = {
            'description': 'Test Description',  # Missing title
            'start_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'end_time': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
            'timezone': 'America/New_York'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        form_errors = response.context['form'].errors
        assert 'title' in form_errors
        assert 'This field is required.' in form_errors['title']

    def test_event_detail_view(self, authenticated_client, event):
        url = reverse('events:detail', args=[event.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert event.title in str(response.content)

    def test_event_detail_not_found(self, authenticated_client):
        url = reverse('events:detail', args=[999])
        response = authenticated_client.get(url)
        assert response.status_code == 404

    def test_event_edit_view_get(self, authenticated_client, event):
        url = reverse('events:edit', args=[event.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert event.title in str(response.content)

    def test_event_edit_view_post(self, authenticated_client, event):
        url = reverse('events:edit', args=[event.pk])
        data = {
            'title': 'Updated Event',
            'description': 'Updated Description',
            'start_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'end_time': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
            'timezone': 'America/New_York'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('events:list')
        event.refresh_from_db()
        assert event.title == 'Updated Event'

    def test_event_edit_view_post_invalid(self, authenticated_client, event):
        url = reverse('events:edit', args=[event.pk])
        data = {
            'description': 'Updated Description',  # Missing title
            'start_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'end_time': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
            'timezone': 'America/New_York'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 200
        form_errors = response.context['form'].errors
        assert 'title' in form_errors
        assert 'This field is required.' in form_errors['title']

    def test_event_edit_not_found(self, authenticated_client):
        url = reverse('events:edit', args=[999])
        response = authenticated_client.get(url)
        assert response.status_code == 404

    def test_event_delete_view(self, authenticated_client, event):
        url = reverse('events:delete', args=[event.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 302
        assert response.url == reverse('events:list')
        assert not Event.objects.filter(pk=event.pk).exists()

    def test_event_delete_not_found(self, authenticated_client):
        url = reverse('events:delete', args=[999])
        response = authenticated_client.post(url)
        assert response.status_code == 404

    @pytest.mark.django_db(transaction=True)
    def test_event_import_crawl4ai(self, authenticated_client):
        url = reverse('events:import')
        mock_events = [{
            'title': 'Scraped Event',
            'description': 'Scraped Description',
            'start_time': timezone.now().isoformat(),
            'end_time': (timezone.now() + timezone.timedelta(hours=2)).isoformat(),
            'venue_name': 'Scraped Venue',
            'venue_address': '789 Scraped St',
            'venue_city': 'Scraped City',
            'venue_state': 'SC',
            'venue_postal_code': '13579',
            'venue_country': 'Scraped Country'
        }]
    
        with patch('events.views.scrape_crawl4ai_events', return_value=mock_events):
            data = {
                'scraper_type': 'crawl4ai',
                'source_url': 'http://example.com',
                'async': 'false'
            }
            response = authenticated_client.post(url, data)
            assert response.status_code == 302
            assert response.url == reverse('events:list')

    @pytest.mark.django_db(transaction=True)
    def test_event_import_crawl4ai_error(self, authenticated_client):
        url = reverse('events:import')
        with patch('events.views.scrape_crawl4ai_events', side_effect=HTTPError('Error fetching events')):
            data = {
                'scraper_type': 'crawl4ai',
                'source_url': 'http://example.com',
                'async': 'false'
            }
            response = authenticated_client.post(url, data)
            assert response.status_code == 400
            assert 'Error fetching events' in str(response.content)

    @pytest.mark.django_db(transaction=True)
    def test_event_import_async(self, authenticated_client):
        url = reverse('events:import')
        data = {
            'scraper_type': 'crawl4ai',
            'source_url': 'http://example.com',
            'async': 'true'
        }
    
        with patch('events.views.scrape_crawl4ai_events') as mock_scrape:
            mock_scrape.return_value = [{
                'title': 'Test Event',
                'description': 'Test Description',
                'start_time': timezone.now(),
                'end_time': timezone.now() + timezone.timedelta(hours=1)
            }]
    
            response = authenticated_client.post(url, data)
            assert response.status_code == 200  # Returns JSON response for async jobs
            response_data = json.loads(response.content)
            assert 'job_id' in response_data

    @pytest.mark.django_db(transaction=True)
    def test_event_import_ical(self, authenticated_client):
        url = reverse('events:import')
        mock_events = [{
            'title': 'Test Event',
            'description': 'Test Description',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timezone.timedelta(hours=1)
        }]

        with patch('events.scrapers.ical_scraper.ICalScraper.process_events', return_value=mock_events):
            data = {
                'scraper_type': 'ical',
                'source_url': 'http://example.com/calendar.ics'
            }
            response = authenticated_client.post(url, data)
            assert response.status_code == 302
            assert response.url == reverse('events:list')

    @pytest.mark.django_db(transaction=True)
    def test_event_import_ical_error(self, authenticated_client):
        url = reverse('events:import')
        with patch('events.scrapers.ical_scraper.ICalScraper.process_events', side_effect=HTTPError('Error fetching events')):
            data = {
                'scraper_type': 'ical',
                'source_url': 'http://example.com/calendar.ics'
            }
            response = authenticated_client.post(url, data)
            assert response.status_code == 400

    @pytest.mark.django_db(transaction=True)
    def test_event_import_invalid_scraper(self, authenticated_client):
        url = reverse('events:import')
        data = {
            'scraper_type': 'invalid_scraper',
            'source_url': 'http://example.com'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 400
        assert 'Invalid scraper type' in str(response.content)

    @pytest.mark.django_db(transaction=True)
    def test_event_import_invalid_url(self, authenticated_client):
        url = reverse('events:import')
        data = {
            'scraper_type': 'crawl4ai',
            'source_url': 'not_a_url',
            'async': 'false'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == 400
        assert 'Invalid URL' in str(response.content)

    def test_event_export(self, authenticated_client, user):
        # Create a test event
        event = Event.objects.create(
            user=user,
            title='Test Event',
            description='Test Description',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )

        url = reverse('events:export')
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar'
        assert 'attachment; filename=' in response['Content-Disposition']

    def test_event_access_other_user(self, authenticated_client):
        # Create another user and their event
        User = get_user_model()
        other_user = User.objects.create_user(username='otheruser', password='password123')
        event = Event.objects.create(
            user=other_user,
            title='Other User Event',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        
        # Try to access the event
        url = reverse('events:detail', args=[event.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 404

        # Try to edit the event
        url = reverse('events:edit', args=[event.pk])
        response = authenticated_client.get(url)
        assert response.status_code == 404

        # Try to delete the event
        url = reverse('events:delete', args=[event.pk])
        response = authenticated_client.post(url)
        assert response.status_code == 404
