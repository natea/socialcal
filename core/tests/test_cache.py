from django.test import TestCase
from django.core.cache import cache

class CacheConfigTest(TestCase):
    """Test that the cache configuration works correctly."""
    
    def test_cache_set_get(self):
        """Test that we can set and get values from the cache."""
        cache.set('test_key', 'test_value', 10)
        self.assertEqual(cache.get('test_key'), 'test_value')
        
    def test_cache_delete(self):
        """Test that we can delete values from the cache."""
        cache.set('test_key', 'test_value', 10)
        cache.delete('test_key')
        self.assertIsNone(cache.get('test_key'))
        
    def test_cache_timeout(self):
        """Test that values expire from the cache."""
        cache.set('test_key', 'test_value', 0)  # Expire immediately
        self.assertIsNone(cache.get('test_key')) 