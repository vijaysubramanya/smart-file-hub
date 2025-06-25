from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Sets up sample users for development/testing'

    def handle(self, *args, **kwargs):
        # Load users from fixture
        try:
            call_command('loaddata', 'initial_users.json')
            self.stdout.write(self.style.SUCCESS('Successfully created sample users'))
            
            # Print credentials
            self.stdout.write('\nSample User Credentials:')
            self.stdout.write('------------------------')
            self.stdout.write('1. Admin User:')
            self.stdout.write('   Username: admin')
            self.stdout.write('   Password: password123')
            self.stdout.write('\n2. Regular Users:')
            for username in ['alice', 'bob', 'carol', 'dave']:
                self.stdout.write(f'   Username: {username}')
                self.stdout.write('   Password: password123')
                self.stdout.write('')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating sample users: {str(e)}')) 