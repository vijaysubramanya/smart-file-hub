from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

class Command(BaseCommand):
    help = 'Creates sample users with password123'

    def handle(self, *args, **kwargs):
        # Create or update admin user
        admin_user, created = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        admin_user.set_password('password123')
        admin_user.save()
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} admin user'))

        # Create or update regular users
        regular_users = ['alice', 'bob', 'carol', 'dave']
        for username in regular_users:
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False
                }
            )
            user.set_password('password123')
            user.save()
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{action} user {username}'))

        self.stdout.write(self.style.SUCCESS('Successfully set up all users')) 