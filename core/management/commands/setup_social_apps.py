"""
Management command to set up social apps for allauth.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Set up social apps for allauth'

    def handle(self, *args, **options):
        # Get the current site
        site = Site.objects.get_current()
        
        # Check if Google app already exists
        if SocialApp.objects.filter(provider='google').exists():
            self.stdout.write(self.style.SUCCESS('Google social app already exists'))
        else:
            # Get credentials from settings or environment variables
            client_id = os.environ.get('GOOGLE_CLIENT_ID') or getattr(settings, 'GOOGLE_CLIENT_ID', None)
            secret = os.environ.get('GOOGLE_CLIENT_SECRET') or getattr(settings, 'GOOGLE_SECRET', None)
            
            if not client_id or not secret:
                self.stdout.write(self.style.WARNING(
                    'Google client ID or secret not found in settings or environment variables. '
                    'Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your settings '
                    'or environment variables.'
                ))
                return
            
            # Create Google app
            app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=client_id,
                secret=secret,
            )
            app.sites.add(site)
            
            self.stdout.write(self.style.SUCCESS('Successfully created Google social app')) 