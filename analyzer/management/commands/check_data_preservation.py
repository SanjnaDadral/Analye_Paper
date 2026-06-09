"""
Management command to monitor data preservation and detect unauthorized deletions.
Run this periodically to ensure data is not being lost.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from analyzer.models import Document, AnalysisResult, PasswordResetOTP
import json
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Monitor database integrity and detect data loss'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check current data and save baseline'
        )
        parser.add_argument(
            '--compare',
            action='store_true',
            help='Compare with previous baseline to detect loss'
        )

    def handle(self, *args, **options):
        log_dir = Path(__file__).resolve().parent.parent.parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        baseline_file = log_dir / 'db_baseline.json'

        if options['check']:
            self.check_and_save_baseline(baseline_file)
        elif options['compare']:
            self.compare_with_baseline(baseline_file)
        else:
            self.stdout.write(self.style.SUCCESS('✓ Data Integrity Monitor'))
            self.stdout.write(f"Database: {self.get_db_info()}")
            self.print_stats()

    def get_db_info(self):
        """Get database type and connection info"""
        from django.conf import settings
        db = settings.DATABASES['default']
        engine = db.get('ENGINE', 'unknown')
        if 'sqlite' in engine:
            return f"SQLite ({db.get('NAME', 'unknown')})"
        elif 'postgresql' in engine:
            return f"PostgreSQL ({db.get('HOST', 'unknown')}:{db.get('PORT', '5432')})"
        elif 'mysql' in engine:
            return f"MySQL ({db.get('HOST', 'unknown')})"
        return engine

    def print_stats(self):
        """Print current statistics"""
        doc_count = Document.objects.count()
        analysis_count = AnalysisResult.objects.count()
        otp_count = PasswordResetOTP.objects.count()

        self.stdout.write(f"\n📊 Current Data Statistics:")
        self.stdout.write(f"  • Documents: {doc_count}")
        self.stdout.write(f"  • Analysis Results: {analysis_count}")
        self.stdout.write(f"  • Password Reset OTPs: {otp_count}")
        self.stdout.write(f"  • Timestamp: {timezone.now().isoformat()}")

    def check_and_save_baseline(self, baseline_file):
        """Save current data count as baseline"""
        baseline = {
            'timestamp': timezone.now().isoformat(),
            'documents': Document.objects.count(),
            'analysis_results': AnalysisResult.objects.count(),
            'password_reset_otps': PasswordResetOTP.objects.count(),
            'database_type': self.get_db_info(),
        }

        with open(baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'✓ Baseline saved to {baseline_file}'))
        self.print_stats()

    def compare_with_baseline(self, baseline_file):
        """Compare current data with baseline"""
        if not baseline_file.exists():
            self.stdout.write(self.style.WARNING('No baseline found. Run with --check first.'))
            return

        with open(baseline_file, 'r') as f:
            baseline = json.load(f)

        current = {
            'documents': Document.objects.count(),
            'analysis_results': AnalysisResult.objects.count(),
            'password_reset_otps': PasswordResetOTP.objects.count(),
        }

        self.stdout.write(f"\n📊 Data Comparison Report")
        self.stdout.write(f"  Baseline Time: {baseline['timestamp']}")
        self.stdout.write(f"  Current Time: {timezone.now().isoformat()}\n")

        has_loss = False
        for key, baseline_count in baseline.items():
            if key not in ['timestamp', 'database_type']:
                current_count = current.get(key, 0)
                diff = baseline_count - current_count
                status = '✓' if diff <= 0 else '⚠️ '
                if diff > 0:
                    has_loss = True
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {status} {key}: {baseline_count} → {current_count} (lost {diff})"
                        )
                    )
                else:
                    self.stdout.write(f"  {status} {key}: {baseline_count} → {current_count}")

        if has_loss:
            self.stdout.write(self.style.ERROR(
                '\n❌ DATA LOSS DETECTED! Check your application for unexpected deletions.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ All data preserved correctly.'
            ))
