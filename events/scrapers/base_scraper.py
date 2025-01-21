import requests
from abc import ABC, abstractmethod
from django.conf import settings
from typing import List, Dict, Any
from datetime import datetime

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self):
        self.api_key = settings.SIMPLESCRAPER_API_KEY
        self.base_url = "https://api.simplescraper.io/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    @abstractmethod
    def parse_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse scraped data into event format"""
        pass

    def fetch_data(self, recipe_id: str, source_url: str) -> List[Dict[str, Any]]:
        """Fetch data from SimpleScraper API"""
        url = f"{self.base_url}/recipes/{recipe_id}/run"
        
        request_body = {
            "sourceUrl": source_url,
            "runAsync": False
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=request_body)
            response.raise_for_status()
            data = response.json()
            
            # Return the actual events data from the response
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
            
        except Exception as e:
            raise Exception(f"Failed to fetch data from SimpleScraper: {str(e)}")

    def process_events(self, recipe_id: str, source_url: str) -> List[Dict[str, Any]]:
        """Process scraped data into events"""
        raw_data = self.fetch_data(recipe_id, source_url)
        return [self.parse_event(item) for item in raw_data]