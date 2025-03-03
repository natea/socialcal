"""
Management command to fix duplicate users in the database.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count
from allauth.socialaccount.models import SocialAccount

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix duplicate users in the database'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Dry run without making changes')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # Find emails with multiple users
        duplicate_emails = User.objects.values('email').annotate(
            count=Count('id')
        ).filter(count__gt=1).exclude(email='')
        
        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS('No duplicate users found'))
            return
        
        self.stdout.write(f'Found {len(duplicate_emails)} emails with duplicate users')
        
        for email_data in duplicate_emails:
            email = email_data['email']
            users = User.objects.filter(email=email).order_by('date_joined')
            
            if not users:
                continue
                
            # Keep the oldest user (first created)
            primary_user = users.first()
            duplicate_users = users.exclude(id=primary_user.id)
            
            self.stdout.write(f'Email: {email}')
            self.stdout.write(f'  Primary user: {primary_user.username} (ID: {primary_user.id})')
            self.stdout.write(f'  Duplicate users: {duplicate_users.count()}')
            
            for dup_user in duplicate_users:
                self.stdout.write(f'    - {dup_user.username} (ID: {dup_user.id})')
                
                # Move social accounts to primary user
                social_accounts = SocialAccount.objects.filter(user=dup_user)
                for account in social_accounts:
                    self.stdout.write(f'      Moving social account {account.provider} to primary user')
                    if not dry_run:
                        account.user = primary_user
                        account.save()
                
                # Delete the duplicate user
                self.stdout.write(f'      Deleting duplicate user')
                if not dry_run:
                    dup_user.delete()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('Successfully fixed duplicate users')) 