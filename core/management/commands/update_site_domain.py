"""
Management command to update the site domain.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Update site domain'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, required=True, help='Site domain')
        parser.add_argument('--name', type=str, help='Site name')

    def handle(self, *args, **options):
        domain = options['domain']
        name = options.get('name')
        
        site = Site.objects.get_current()
        site.domain = domain
        if name:
            site.name = name
        site.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated site domain to {domain}')) 