import requests
import json
import asyncio
import aiohttp
from django.conf import settings

# Synchronous version using requests
def run_recipe(api_key: str, recipe_id: str, source_url: str):
    url = f"https://api.simplescraper.io/v1/recipes/{recipe_id}/run"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    request_body = {
        "sourceUrl": source_url,
        "runAsync": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# Async version using aiohttp
async def run_recipe_async(api_key: str, recipe_id: str, source_url: str):
    url = f"https://api.simplescraper.io/v1/recipes/{recipe_id}/run"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    request_body = {
        "sourceUrl": source_url,
        "runAsync": False
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=request_body) as response:
                response.raise_for_status()
                data = await response.json()
                print(json.dumps(data, indent=2))
                return data
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# Example usage of synchronous version
def test_simplescraper_api():
    api_key = settings.SIMPLESCRAPER_API_KEY
    recipe_id = "uQuCVTiLliKzqvqp9x9s"  # Your recipe ID
    source_url = "https://college.berklee.edu/events/visiting-artist-events"  # URL to scrape
    
    return run_recipe(api_key, recipe_id, source_url)

# Example usage of async version
async def test_simplescraper_api_async():
    api_key = settings.SIMPLESCRAPER_API_KEY
    recipe_id = "uQuCVTiLliKzqvqp9x9s"  # Your recipe ID
    source_url = "https://college.berklee.edu/events/visiting-artist-events"  # URL to scrape
    
    return await run_recipe_async(api_key, recipe_id, source_url)

# To run the async version from sync code (like Django shell)
def run_async_test():
    return asyncio.run(test_simplescraper_api_async()) 