from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
from events.utils.spotify import SpotifyAPI
from events.views import add_spotify_track_to_event, get_artist_from_event, is_music_event

class TestSpotifyAPI(TestCase):
    def setUp(self):
        cache.clear()
        # Set up a mock access token
        self.mock_token = 'test_token'
        cache.set('spotify_access_token', self.mock_token)
        
    def tearDown(self):
        cache.clear()
        
    @patch('events.utils.spotify.requests.post')
    def test_get_access_token(self, mock_post):
        # Mock successful token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        mock_response.raise_for_status = MagicMock()
        
        # Test getting token
        token = SpotifyAPI.get_access_token()
        self.assertEqual(token, 'test_token')
        
        # Test token caching
        cached_token = cache.get('spotify_access_token')
        self.assertEqual(cached_token, 'test_token')
        
    @patch('events.utils.spotify.requests.get')
    def test_get_artist_id_from_name(self, mock_get):
        # Mock successful artist search response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'artists': {
                'items': [{
                    'id': 'test_artist_id',
                    'name': 'Test Artist'
                }]
            }
        }
        mock_get.return_value = mock_response
        mock_response.raise_for_status = MagicMock()
        
        # Test getting artist ID
        artist_id = SpotifyAPI.get_artist_id_from_name('Test Artist')
        self.assertEqual(artist_id, 'test_artist_id')
        
        # Verify the search query
        args, kwargs = mock_get.call_args
        self.assertIn('artist:"Test Artist"', kwargs['params']['q'])
        
    @patch('events.utils.spotify.requests.get')
    def test_search_track(self, mock_get):
        # Mock successful track search response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'tracks': {
                'items': [{
                    'id': 'test_track_id',
                    'name': 'Test Track',
                    'artists': [{
                        'id': 'test_artist_id',
                        'name': 'Test Artist'
                    }],
                    'album': {
                        'name': 'Test Album',
                        'images': [{'url': 'test_image_url', 'width': 300, 'height': 300}]
                    },
                    'preview_url': 'test_preview_url',
                    'external_urls': {'spotify': 'test_external_url'}
                }]
            }
        }
        mock_get.return_value = mock_response
        mock_response.raise_for_status = MagicMock()
        
        # Test searching tracks
        tracks = SpotifyAPI.search_track('test query')
        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        
        # Verify track data
        self.assertEqual(track['id'], 'test_track_id')
        self.assertEqual(track['name'], 'Test Track')
        self.assertEqual(track['artist'], 'Test Artist')
        self.assertEqual(track['artist_id'], 'test_artist_id')
        self.assertEqual(track['preview_url'], 'test_preview_url')
        self.assertEqual(track['external_url'], 'test_external_url')
        self.assertEqual(track['album']['name'], 'Test Album')
        
    @patch('events.utils.spotify.requests.get')
    def test_search_track_with_artist(self, mock_get):
        # Mock successful track search response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'tracks': {
                'items': [{
                    'id': 'test_track_id',
                    'name': 'Test Track',
                    'artists': [{
                        'id': 'test_artist_id',
                        'name': 'Test Artist'
                    }],
                    'album': {
                        'name': 'Test Album',
                        'images': [{'url': 'test_image_url', 'width': 300, 'height': 300}]
                    },
                    'preview_url': 'test_preview_url',
                    'external_urls': {'spotify': 'test_external_url'}
                }]
            }
        }
        mock_get.return_value = mock_response
        mock_response.raise_for_status = MagicMock()
        
        # Test searching tracks with artist filter
        tracks = SpotifyAPI.search_track('test query', artist_name='Test Artist')
        self.assertEqual(len(tracks), 1)
        
        # Verify the search query included the artist
        args, kwargs = mock_get.call_args
        self.assertIn('artist:"Test Artist"', kwargs['params']['q'])

class TestSpotifyEventIntegration(TestCase):
    def test_is_music_event(self):
        # Test various event titles and descriptions
        event_data = {'title': 'Concert with Test Artist', 'description': 'Live music event'}
        self.assertTrue(is_music_event(event_data))
        
        event_data = {'title': 'Business Meeting', 'description': 'Quarterly review'}
        self.assertFalse(is_music_event(event_data))
        
    def test_get_artist_from_event(self):
        # Test various event title formats
        test_cases = [
            {
                'title': 'Test Artist live at Venue',
                'expected': 'Test Artist'
            },
            {
                'title': 'Venue presents Test Artist',
                'expected': 'Test Artist'
            },
            {
                'title': 'Test Artist in concert',
                'expected': 'Test Artist'
            },
            {
                'title': 'Vista Philharmonic Orchestra - Music Without Boundaries',
                'expected': 'Vista Philharmonic Orchestra'
            },
            {
                'title': 'John Pizzarelli Swing Seven: Dear Mr. Sinatra',
                'expected': 'John Pizzarelli Swing Seven'
            },
            {
                'title': 'Test String Quartet performs Mozart',
                'expected': 'Test String Quartet'
            },
            {
                'title': 'Jazz Ensemble presents: A Night of Swing',
                'expected': 'Jazz Ensemble'
            }
        ]
        
        for case in test_cases:
            artist = get_artist_from_event({'title': case['title']})
            self.assertEqual(artist, case['expected'], f"Failed to extract artist from '{case['title']}'")
            
    @patch('events.views.SpotifyAPI.search_track')
    def test_add_spotify_track_to_event(self, mock_search_track):
        # Mock track search results
        mock_track = {
            'id': 'test_track_id',
            'name': 'Test Track',
            'artist': 'Test Artist',
            'artist_id': 'test_artist_id',
            'artists': [{'name': 'Test Artist', 'id': 'test_artist_id'}],
            'preview_url': 'test_preview_url',
            'external_url': 'test_external_url'
        }
        mock_search_track.return_value = [mock_track]
        
        # Test event data with music event
        event_data = {
            'title': 'Test Artist live at Venue',
            'description': 'Live music event',
            'id': '123',  # Add an ID for caching
            'session': {}  # Mock session for caching
        }
        
        result = add_spotify_track_to_event(event_data)
        
        # Verify Spotify data was added
        self.assertEqual(result['spotify_track_id'], 'test_track_id')
        self.assertEqual(result['spotify_track_name'], 'Test Track')
        self.assertEqual(result['spotify_artist_name'], 'Test Artist')
        self.assertEqual(result['spotify_artist_id'], 'test_artist_id')
        self.assertEqual(result['spotify_preview_url'], 'test_preview_url')
        self.assertEqual(result['spotify_external_url'], 'test_external_url')
        
        # Verify data was cached in session
        cache_key = 'spotify_data_123'
        self.assertIn(cache_key, event_data['session'])
        cached_data = event_data['session'][cache_key]
        self.assertEqual(cached_data['track_id'], 'test_track_id')
        self.assertEqual(cached_data['artist_id'], 'test_artist_id')
        
        # Test that cached data is used on subsequent calls
        mock_search_track.reset_mock()
        result2 = add_spotify_track_to_event(event_data)
        mock_search_track.assert_not_called()  # Should use cached data
        self.assertEqual(result2['spotify_track_id'], 'test_track_id')
        
        # Test non-music event
        event_data = {
            'title': 'Business Meeting',
            'description': 'Quarterly review'
        }
        
        result = add_spotify_track_to_event(event_data)
        
        # Verify no Spotify data was added
        self.assertEqual(result['spotify_track_id'], '')
        self.assertEqual(result['spotify_artist_name'], '') 