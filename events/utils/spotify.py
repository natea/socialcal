import os
import base64
import requests
from django.conf import settings
from django.core.cache import cache

class SpotifyAPI:
    TOKEN_URL = 'https://accounts.spotify.com/api/token'
    SEARCH_URL = 'https://api.spotify.com/v1/search'
    ARTIST_URL = 'https://api.spotify.com/v1/artists'
    
    @staticmethod
    def get_access_token():
        # Try to get token from cache first
        token = cache.get('spotify_access_token')
        if token:
            return token
            
        # If no token in cache, get a new one
        client_id = settings.SPOTIFY_CLIENT_ID
        client_secret = settings.SPOTIFY_CLIENT_SECRET
        
        # Encode client credentials
        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        try:
            response = requests.post(SpotifyAPI.TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            token = token_data['access_token']
            expires_in = token_data['expires_in']
            
            # Cache the token for slightly less than its expiry time
            cache.set('spotify_access_token', token, expires_in - 60)
            
            return token
        except Exception as e:
            print(f"Error getting Spotify access token: {str(e)}")
            return None
    
    @staticmethod
    def get_artist_id_from_name(artist_name):
        """Get Spotify artist ID from artist name."""
        token = SpotifyAPI.get_access_token()
        if not token:
            return None
            
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'q': f'artist:"{artist_name}"',
            'type': 'artist',
            'limit': 1
        }
        
        try:
            response = requests.get(
                SpotifyAPI.SEARCH_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            results = response.json()
            artists = results.get('artists', {}).get('items', [])
            
            if not artists:
                return None
                
            return artists[0]['id']
        except Exception as e:
            print(f"Error getting artist ID: {str(e)}")
            return None
    
    @staticmethod
    def get_artist_embed_url(artist_name):
        """Get Spotify embed URL for an artist."""
        artist_id = SpotifyAPI.get_artist_id_from_name(artist_name)
        if not artist_id:
            return None
            
        return f"https://open.spotify.com/embed/artist/{artist_id}?utm_source=generator"
    
    @staticmethod
    def search_track(query, artist_name=None, limit=10):
        token = SpotifyAPI.get_access_token()
        if not token:
            return None
            
        headers = {'Authorization': f'Bearer {token}'}
        
        # If artist name is provided, make the search more specific
        search_query = query
        if artist_name:
            search_query = f'artist:"{artist_name}" {query}'
            
        params = {
            'q': search_query,
            'type': 'track',
            'limit': limit
        }
        
        try:
            response = requests.get(
                SpotifyAPI.SEARCH_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            results = response.json()
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                return None
                
            # If artist name is provided, filter results to only include tracks by that artist
            if artist_name:
                artist_name_lower = artist_name.lower()
                filtered_tracks = [
                    track for track in tracks
                    if any(artist['name'].lower() == artist_name_lower for artist in track['artists'])
                ]
                tracks = filtered_tracks if filtered_tracks else tracks  # Fall back to all tracks if no exact matches
                
            return [{
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'artist_id': track['artists'][0]['id'],  # Include the artist ID
                'artists': [{'name': artist['name'], 'id': artist['id']} for artist in track['artists']],
                'preview_url': track['preview_url'],
                'external_url': track['external_urls']['spotify'],
                'embed_url': f"https://open.spotify.com/embed/track/{track['id']}",
                'album': {
                    'name': track['album']['name'],
                    'images': track['album']['images']  # This includes multiple sizes
                }
            } for track in tracks]
        except Exception as e:
            print(f"Error searching Spotify track: {str(e)}")
            return None 