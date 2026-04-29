import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Auto-create superuser from environment variables if not exists'

    def handle(self, *args, **kwargs):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '123')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@paperaizer.com')

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser "{username}" already exists.')
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(f'Superuser "{username}" created successfully.')
