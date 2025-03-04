import json
import os
import pytest
import re
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup

# Import the module to test
from events.scrapers.crawl4ai_demo import demo_json_schema_generation, transform_url


# Fixtures
@pytest.fixture
def sample_html():
    """Return a sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Events Page</title>
    </head>
    <body>
        <div class="event-list">
            <div class="event-card">
                <h3 class="title">Test Event 1</h3>
                <div class="date">2023-01-01</div>
                <div class="location">Test Location 1</div>
                <div class="description">Test Description 1</div>
                <a href="/event/123" class="event-link">Details</a>
                <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=" class="event-image">
            </div>
            <div class="event-card">
                <h3 class="title">Test Event 2</h3>
                <div class="date">2023-01-02</div>
                <div class="location">Test Location 2</div>
                <div class="description">Test Description 2</div>
                <a href="https://example.com/event/456" class="event-link">Details</a>
                <img src="https://example.com/images/event2.jpg" class="event-image">
            </div>
            <div class="event-card">
                <h3 class="title">Test Event 3</h3>
                <div class="date">2023-01-03</div>
                <div class="location">Test Location 3</div>
                <div class="description">Test Description 3</div>
                <a href="https://example.com/event/789" class="event-link">Details</a>
                <div class="event-image" style="background-image: url('https://example.com/images/event3.jpg');background-position: center;"></div>
            </div>
        </div>
        <div class="other-images">
            <img src="https://example.com/images/banner.jpg" class="banner-image">
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_crawler():
    """Create a mock AsyncWebCrawler for testing."""
    with patch('events.scrapers.crawl4ai_demo.AsyncWebCrawler') as mock:
        crawler_instance = AsyncMock()
        mock.return_value = crawler_instance
        yield crawler_instance


def test_transform_url():
    """Test the transform_url function with different URL formats."""
    base_url = "https://example.com/events/"
    
    # Test with absolute URL
    assert transform_url("https://example.org/image.jpg", base_url) == "https://example.org/image.jpg"
    
    # Test with relative URL
    assert transform_url("/images/event.jpg", base_url) == "https://example.com/images/event.jpg"
    
    # Test with base64 image
    assert transform_url("data:image/png;base64,abc123", base_url) is None
    
    # Test with background-image style
    bg_image = "background-image: url('https://example.com/images/bg.jpg');background-position: center;"
    assert transform_url(bg_image, base_url) == "https://example.com/images/bg.jpg"
    
    # Test with invalid background-image style
    invalid_bg = "background-image: url(invalid);background-position: center;"
    assert transform_url(invalid_bg, base_url) is None
    
    # Test with None
    assert transform_url(None, base_url) is None


@pytest.mark.asyncio
async def test_demo_json_schema_generation_success(mock_crawler, sample_html):
    """Test the demo_json_schema_generation function with successful extraction."""
    # Mock the necessary functions
    with patch('builtins.print'):
        with patch('builtins.open', MagicMock()):
            # Mock the result of crawler.arun
            mock_crawler.arun.return_value = MagicMock(
                success=True,
                extracted_content=json.dumps([
                    {
                        "title": "Test Event 1",
                        "date": "2023-01-01",
                        "url": "/event/123"
                    }
                ])
            )
            
            # Run the function
            await demo_json_schema_generation()
            
            # Verify that the crawler was called
            mock_crawler.arun.assert_called_once()


@pytest.mark.asyncio
async def test_demo_json_schema_generation_failure(mock_crawler):
    """Test the demo_json_schema_generation function when crawler fails."""
    # Mock the necessary functions
    with patch('builtins.print'):
        # Mock the result of crawler.arun
        mock_crawler.arun.return_value = MagicMock(
            success=False,
            error="Test error"
        )
        
        # Run the function
        await demo_json_schema_generation()
        
        # Verify that the crawler was called
        mock_crawler.arun.assert_called_once()


@pytest.mark.asyncio
async def test_demo_json_schema_generation_exception():
    """Test the demo_json_schema_generation function when an exception occurs."""
    # Mock the AsyncWebCrawler to raise an exception
    with patch('events.scrapers.crawl4ai_demo.AsyncWebCrawler', side_effect=Exception("Test exception")):
        # Mock the print function to avoid output
        with patch('builtins.print'):
            # Mock the traceback.print_exc function
            with patch('traceback.print_exc'):
                # Run the function and expect an exception
                with pytest.raises(Exception):
                    await demo_json_schema_generation() 