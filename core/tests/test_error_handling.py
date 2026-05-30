import pytest
from django.urls import reverse
from django.test import override_settings


@pytest.mark.django_db
class TestErrorHandling:
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
