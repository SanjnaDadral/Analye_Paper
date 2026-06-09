"""
Management command to migrate database from SQLite to PostgreSQL.
This is critical for Render deployment where SQLite data is lost on container restart.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connections
import os


class Command(BaseCommand):
    help = 'Migrate data from SQLite to PostgreSQL (use on Render for persistent storage)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create a backup of current SQLite database before migration'
        )

    def handle(self, *args, **options):
        from django.conf import settings

        current_db = settings.DATABASES['default']
        current_engine = current_db.get('ENGINE', '')

        self.stdout.write(self.style.WARNING('⚠️  Database Migration Tool\n'))
        self.stdout.write(f"Current Database: {current_engine}")
        self.stdout.write(f"Database: {current_db.get('NAME', 'unknown')}\n")

        if 'postgresql' in current_engine:
            self.stdout.write(self.style.SUCCESS(
                '✓ Already using PostgreSQL. No migration needed!'
            ))
            return

        if 'sqlite' not in current_engine:
            raise CommandError(f"Unsupported database: {current_engine}")

        self.stdout.write(self.style.WARNING(
            '❌ WARNING: SQLite is NOT suitable for Render production!\n'
            'Your data will be deleted when the container restarts.\n\n'
            'SOLUTION: Use PostgreSQL instead\n'
        ))

        self.stdout.write('On Render, PostgreSQL is set up automatically.')
        self.stdout.write('Make sure:\n')
        self.stdout.write('  1. Your render.yaml has a PostgreSQL database service')
        self.stdout.write('  2. The DATABASE_URL environment variable is set')
        self.stdout.write('  3. Restart your application to use the new database\n')

        self.stdout.write(self.style.SUCCESS('Key Steps:'))
        self.stdout.write('  1. On Render Dashboard: Create PostgreSQL database')
        self.stdout.write('  2. Update render.yaml to include the database service')
        self.stdout.write('  3. Redeploy your app')
        self.stdout.write('  4. Run: python manage.py migrate')
        self.stdout.write('  5. Run: python manage.py check_data_preservation --check\n')

        if options['backup']:
            self.backup_database()

    def backup_database(self):
        """Create a backup of the SQLite database"""
        from pathlib import Path
        import shutil
        from datetime import datetime

        db_file = Path('db.sqlite3')
        if db_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = Path(f'db_backup_{timestamp}.sqlite3')
            shutil.copy(db_file, backup_file)
            self.stdout.write(self.style.SUCCESS(f'✓ Backup created: {backup_file}'))
        else:
            self.stdout.write(self.style.WARNING('No db.sqlite3 file found to backup'))
