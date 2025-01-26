from django.apps import apps
from django.test import TestCase
from accounts.apps import AccountsConfig

class TestAccountsConfig(TestCase):
    def test_apps_config(self):
        # Test that the accounts app is configured correctly
        self.assertEqual(AccountsConfig.name, 'accounts')
        self.assertEqual(apps.get_app_config('accounts').name, 'accounts') 