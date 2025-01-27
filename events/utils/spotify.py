import os
import base64
import requests
from django.conf import settings
from django.core.cache import cache

class SpotifyAPI:
    TOKEN_URL = 'https://accounts.spotify.com/api/token'
    SEARCH_URL = 'https://api.spotify.com/v1/search'
    
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
    def search_track(query):
        token = SpotifyAPI.get_access_token()
        if not token:
            return None
            
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'q': query,
            'type': 'track',
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
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                return None
                
            track = tracks[0]
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'preview_url': track['preview_url'],
                'external_url': track['external_urls']['spotify'],
                'embed_url': f"https://open.spotify.com/embed/track/{track['id']}"
            }
        except Exception as e:
            print(f"Error searching Spotify track: {str(e)}")
            return None 