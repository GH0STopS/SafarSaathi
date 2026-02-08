from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction


class Command(BaseCommand):
    help = 'Create an admin user for Safar-Saathi'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the admin user')
        parser.add_argument('email', type=str, help='Email for the admin user')
        parser.add_argument('--password', type=str, help='Password for the admin user (optional)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options.get('password')

        if not password:
            password = input('Enter password for admin user: ')

        try:
            with transaction.atomic():
                # Create or get the Admin group
                admin_group, created = Group.objects.get_or_create(name='Admin')
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Admin group'))

                # Create the admin user
                if User.objects.filter(username=username).exists():
                    self.stdout.write(self.style.WARNING(f'User {username} already exists'))
                    user = User.objects.get(username=username)
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        is_staff=True,
                        is_superuser=True
                    )
                    self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))

                # Add user to Admin group if not already
                if not user.groups.filter(name='Admin').exists():
                    user.groups.add(admin_group)
                    self.stdout.write(self.style.SUCCESS(f'Added {username} to Admin group'))

                # Ensure user has staff and superuser status
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Granted staff status to {username}'))

                if not user.is_superuser:
                    user.is_superuser = True
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Granted superuser status to {username}'))

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Admin user {username} is ready. You can now login at /admin_app/dashboard/'
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}'))