"""
Management command to update Google OAuth credentials.
"""
from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Update Google OAuth credentials'

    def add_arguments(self, parser):
        parser.add_argument('--client_id', type=str, required=True, help='Google OAuth client ID')
        parser.add_argument('--client_secret', type=str, required=True, help='Google OAuth client secret')

    def handle(self, *args, **options):
        client_id = options['client_id']
        client_secret = options['client_secret']
        
        try:
            app = SocialApp.objects.get(provider='google')
            app.client_id = client_id
            app.secret = client_secret
            app.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated Google OAuth credentials'))
        except SocialApp.DoesNotExist:
            self.stdout.write(self.style.ERROR('Google SocialApp not found. Please run setup_social_apps first.')) 