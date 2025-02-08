import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase, Client, override_settings
from events.models import Event
from unittest.mock import patch, AsyncMock, MagicMock
import pytz
from requests.exceptions import HTTPError
import json
from asgiref.sync import sync_to_async
from django.core.cache import cache
import pickle

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'password': 'testpass'}
    )
    if created:
        user.set_password('testpass')
        user.save()
    return user

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

    def test_event_list_search(self, authenticated_client, user):
        # Create test events
        Event.objects.create(
            user=user,
            title="Birthday Party",
            description="A fun celebration",
            venue_name="Home",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2)
        )
        Event.objects.create(
            user=user,
            title="Tech Conference",
            description="Annual tech gathering",
            venue_name="Convention Center",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=4)
        )
        Event.objects.create(
            user=user,
            title="Music Festival",
            description="Live bands and fun",
            venue_name="City Park",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=8)
        )

        # Test title search
        response = authenticated_client.get(reverse('events:list') + '?q=Tech')
        assert response.status_code == 200
        content = str(response.content)
        assert 'Tech Conference' in content
        assert 'Birthday Party' not in content
        assert 'Showing 1 event' in content

        # Test description search
        response = authenticated_client.get(reverse('events:list') + '?q=fun')
        assert response.status_code == 200
        content = str(response.content)
        assert 'Birthday Party' in content
        assert 'Music Festival' in content
        assert 'Tech Conference' not in content
        assert 'Showing 2 events' in content

        # Test venue search
        response = authenticated_client.get(reverse('events:list') + '?q=center')
        assert response.status_code == 200
        content = str(response.content)
        assert 'Tech Conference' in content
        assert 'Birthday Party' not in content
        assert 'Showing 1 event' in content

    def test_event_list_venue_filter(self, authenticated_client, user):
        # Create test events
        Event.objects.create(
            user=user,
            title="Morning Meeting",
            venue_name="Conference Room A",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        Event.objects.create(
            user=user,
            title="Afternoon Meeting",
            venue_name="Conference Room A",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        Event.objects.create(
            user=user,
            title="Team Lunch",
            venue_name="Cafeteria",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )

        # Test venue filter
        response = authenticated_client.get(reverse('events:list') + '?venue=Conference Room A')
        assert response.status_code == 200
        content = str(response.content)
        assert 'Morning Meeting' in content
        assert 'Afternoon Meeting' in content
        assert 'Team Lunch' not in content
        assert 'Showing 2 events at Conference Room A' in content

    def test_event_list_combined_search_and_filter(self, authenticated_client, user):
        # Create test events
        Event.objects.create(
            user=user,
            title="Morning Team Meeting",
            description="Team A sync",
            venue_name="Conference Room A",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        Event.objects.create(
            user=user,
            title="Afternoon Team Meeting",
            description="Team B sync",
            venue_name="Conference Room A",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        Event.objects.create(
            user=user,
            title="Team Lunch",
            description="Team A lunch",
            venue_name="Cafeteria",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )

        # Test combined search and venue filter
        response = authenticated_client.get(reverse('events:list') + '?q=Team A&venue=Conference Room A')
        assert response.status_code == 200
        content = str(response.content)
        assert 'Morning Team Meeting' in content
        assert 'Afternoon Team Meeting' not in content
        assert 'Team Lunch' not in content
        assert 'Showing 1 event' in content
        assert 'at Conference Room A' in content
        assert 'matching "Team A"' in content

    def test_event_list_empty_results(self, authenticated_client, user):
        # Create a test event
        Event.objects.create(
            user=user,
            title="Test Event",
            venue_name="Test Venue",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )

        # Test search with no matches
        response = authenticated_client.get(reverse('events:list') + '?q=nonexistent')
        assert response.status_code == 200
        content = str(response.content)
        assert 'No events found' in content
        assert 'Showing 0 events' in content

        # Test venue filter with no matches
        response = authenticated_client.get(reverse('events:list') + '?venue=Nonexistent Venue')
        assert response.status_code == 200
        content = str(response.content)
        assert 'No events found' in content
        assert 'Showing 0 events' in content

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
        
        # First test the confirmation page (GET request)
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert 'Delete Event' in str(response.content)
        assert event.title in str(response.content)
        
        # Then test the actual deletion (POST request)
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
            # For non-AJAX requests, expect a redirect
            assert response.status_code == 302
            assert response.url == reverse('events:list')

            # For AJAX requests, expect JSON response
            response = authenticated_client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['status'] == 'complete'
            assert 'redirect_url' in response_data
            assert response_data['redirect_url'] == reverse('events:list')

    @pytest.mark.django_db(transaction=True)
    def test_event_import_crawl4ai_error(self, authenticated_client):
        url = reverse('events:import')
        with patch('events.views.scrape_crawl4ai_events', side_effect=HTTPError('Error fetching events')):
            data = {
                'scraper_type': 'crawl4ai',
                'source_url': 'http://example.com',
                'async': 'false'
            }
            response = authenticated_client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            assert response.status_code == 400
            response_data = json.loads(response.content)
            assert response_data['status'] == 'error'
            assert 'Error fetching events' in response_data['message']

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
    
            response = authenticated_client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['status'] == 'started'
            assert 'job_id' in response_data

    @pytest.mark.django_db(transaction=True)
    def test_event_import_status(self, authenticated_client):
        # Create a test job status
        job_id = '1234567890'
        job_status = {
            'status': 'started',
            'events': [],
            'message': 'Scraping started',
            'progress': {
                'overall': 0,
                'scraping': 0,
                'processing': 0
            },
            'status_message': {
                'scraping': 'Initializing scraper...',
                'processing': 'Waiting to process events...'
            }
        }
        cache.set(f'scraping_job_{job_id}', json.dumps(job_status), timeout=3600)

        # Check the status
        url = reverse('events:import_status', args=[job_id])
        response = authenticated_client.get(url)
        assert response.status_code == 200
        
        response_data = json.loads(response.content)
        assert response_data['status'] == 'started'
        assert response_data['message'] == 'Scraping started'
        assert 'progress' in response_data
        assert 'status_message' in response_data

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
            # Test non-AJAX request
            data = {
                'scraper_type': 'ical',
                'source_url': 'http://example.com/calendar.ics'
            }
            response = authenticated_client.post(url, data)
            assert response.status_code == 302
            assert response.url == reverse('events:list')

            # Test AJAX request
            response = authenticated_client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            assert response.status_code == 200
            response_data = json.loads(response.content)
            assert response_data['status'] == 'complete'
            assert 'redirect_url' in response_data
            assert response_data['redirect_url'] == reverse('events:list')

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
            response_data = json.loads(response.content)
            assert response_data['status'] == 'error'
            assert 'Error fetching events' in response_data['message']

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

    @pytest.mark.django_db(transaction=True)
    def test_export_ical(self, authenticated_client, user):
        # Create test events
        event1 = Event.objects.create(
            user=user,
            title="Test Event 1",
            description="Test Description 1",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            venue_name="Test Venue 1",
            venue_address="123 Test St",
            venue_city="Test City",
            venue_state="TS",
            venue_postal_code="12345",
            is_public=True
        )
        
        event2 = Event.objects.create(
            user=user,
            title="Test Event 2",
            description="Test Description 2",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            venue_name="Test Venue 2",
            venue_address="456 Test Ave",
            venue_city="Test City",
            venue_state="TS",
            venue_postal_code="12345",
            is_public=True
        )
        
        # Test iCal export
        url = reverse('events:export_ical')
        response = authenticated_client.get(url)
        
        # Check response
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar'
        assert 'attachment; filename=events.ics' in response['Content-Disposition']
        
        # Check iCal content
        ical_content = response.content.decode()
        assert 'BEGIN:VCALENDAR' in ical_content
        assert 'VERSION:2.0' in ical_content
        assert 'PRODID:-//SocialCal//EN' in ical_content
        assert 'BEGIN:VEVENT' in ical_content
        assert 'SUMMARY:Test Event 1' in ical_content
        assert 'SUMMARY:Test Event 2' in ical_content
        assert 'DESCRIPTION:Test Description 1' in ical_content
        assert 'DESCRIPTION:Test Description 2' in ical_content
        
        # Check location with escaped commas and line continuation
        assert 'LOCATION:Test Venue 1\\, 123 Test St\\, Test City\\, TS\\, 12345\\, United States' in ical_content.replace('\r\n ', '')

    @pytest.mark.django_db(transaction=True)
    def test_event_detail_calendar_links(self, authenticated_client, user):
        # Create a test event
        event = Event.objects.create(
            user=user,
            title="Test Event",
            description="Test Description",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_public=True
        )
        
        # Get the event detail page
        response = authenticated_client.get(reverse('events:detail', args=[event.id]))
        assert response.status_code == 200
        
        # Check for webcal subscription link
        assert f'href="{reverse("events:export_ical")}?event_id={event.id}"' in response.content.decode()
        assert 'data-protocol="webcal"' in response.content.decode()
        assert 'Download iCal' in response.content.decode()
        
        # Check for iCal download link
        assert f'href="{reverse("events:export_ical")}?event_id={event.id}"' in response.content.decode()
        assert 'Download iCal' in response.content.decode()

    @pytest.mark.django_db(transaction=True)
    def test_event_list_calendar_links(self, authenticated_client, user):
        # Create some test events
        Event.objects.create(
            user=user,
            title="Test Event 1",
            description="Test Description 1",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_public=True
        )
        Event.objects.create(
            user=user,
            title="Test Event 2",
            description="Test Description 2",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            is_public=True
        )
        
        # Get the event list page
        response = authenticated_client.get(reverse('events:list'))
        assert response.status_code == 200
        
        # Check for webcal subscription link for all events
        assert f'href="{reverse("events:export_ical")}"' in response.content.decode()
        assert 'data-protocol="webcal"' in response.content.decode()
        assert 'Subscribe to All Events' in response.content.decode()
        
        # Check for iCal download link for all events
        assert f'href="{reverse("events:export_ical")}"' in response.content.decode()
        assert 'Download All Events' in response.content.decode()

    @pytest.mark.django_db(transaction=True)
    def test_export_ical_webcal_header(self, authenticated_client, user):
        # Create a test event
        event = Event.objects.create(
            user=user,
            title="Test Event",
            description="Test Description",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_public=True
        )
        
        # Test single event export
        response = authenticated_client.get(f'{reverse("events:export_ical")}?event_id={event.id}')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar'
        assert 'X-Webcal-URL' in response
        assert response['X-Webcal-URL'].startswith('webcal://')
        
        # Test all events export
        response = authenticated_client.get(reverse('events:export_ical'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar'
        assert 'X-Webcal-URL' in response
        assert response['X-Webcal-URL'].startswith('webcal://')

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_webcal_javascript_functionality(self, authenticated_client, user):
        # Create a test event
        event = Event.objects.create(
            user=user,
            title="Test Event",
            description="Test Description",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_public=True
        )
        
        # Get the event detail page
        response = authenticated_client.get(reverse('events:detail', args=[event.id]))
        content = response.content.decode()
        
        # Check that the webcal link is present with the correct data attribute
        assert 'data-protocol="webcal"' in content
        assert 'webcal-handler.js' in content
