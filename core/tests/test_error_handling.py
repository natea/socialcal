import pytest
from django.urls import reverse
from django.conf import settings
from django.test import override_settings, Client
from django.test.client import RequestFactory
from django.http import HttpResponse
from core.middleware.exception_logging import ExceptionLoggingMiddleware

@pytest.mark.django_db
class TestErrorHandling:
    """Tests for error handling functionality."""
    
    def test_debug_error_view_in_debug_mode(self, client):
        """Test that the debug error view raises an exception in DEBUG mode."""
        with override_settings(DEBUG=True):
            with pytest.raises(Exception) as excinfo:
                client.get(reverse('core:debug_error'))
            assert "This is a test exception to verify error handling" in str(excinfo.value)
    
    def test_debug_error_view_in_production_mode(self, client):
        """Test that the debug error view doesn't raise an exception in production mode."""
        with override_settings(DEBUG=False):
            response = client.get(reverse('core:debug_error'))
            assert response.status_code == 200
            assert "Debug error view only available in DEBUG mode" in response.content.decode()
    
    def test_middleware_processes_exceptions(self):
        """Test that our middleware processes exceptions correctly."""
        # Create a request factory
        factory = RequestFactory()
        
        # Create a simple view that raises an exception
        def view_that_raises_exception(request):
            raise Exception("Test exception")
        
        # Create a simple middleware response
        def get_response(request):
            return HttpResponse("This should not be reached")
        
        # Create the middleware
        middleware = ExceptionLoggingMiddleware(get_response)
        
        # Create a request
        request = factory.get('/test-error/')
        
        # Test with DEBUG=True
        with override_settings(DEBUG=True):
            # Process the exception
            response = middleware.process_exception(request, Exception("Test exception"))
            # Check that we get a response with the exception details
            assert response is not None
            assert response.status_code == 500
            assert "Test exception" in response.content.decode()
        
        # Test with DEBUG=False
        with override_settings(DEBUG=False):
            # Process the exception
            response = middleware.process_exception(request, Exception("Test exception"))
            # In production, middleware should return None to let Django handle it
            assert response is None 