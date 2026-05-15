"""
Management command: notify_exit_deadlines
Generates ExitInterviewNotification rows for interviews whose
approval last-day is within the upcoming-window or already overdue.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta

from App.human_resource.models import ExitInterview, ExitInterviewNotification


class Command(BaseCommand):
    help = 'Generate deadline notifications for exit interviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be created without writing to the database',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        today = date.today()
        created = 0
        skipped = 0

        interviews = ExitInterview.objects.select_related('employee').all()
        self.stdout.write(f"Scanning {interviews.count()} interviews...")

        for interview in interviews:
            day = interview.approved_last_day or interview.desired_last_day
            if not day:
                skipped += 1
                continue

            days_left = (day - today).days

            # ── 30-day review due within 7 days ─────────────────────────────────
            if 0 <= days_left <= 7:
                n, was_created = self._maybe_create(
                    interview, 'upcoming_30day', dry_run
                )
                created += 1 if was_created else 0

            # ── Overdue clearance ───────────────────────────────────────────────
            if days_left < 0:
                n, was_created = self._maybe_create(
                    interview, 'overdue_clearance', dry_run
                )
                created += 1 if was_created else 0

            # ── Clearance deadline (3 days after approved last day) ─────────────
            clearance_deadline = day + timedelta(days=3)
            clearance_days_left = (clearance_deadline - today).days
            if 0 <= clearance_days_left <= 14:
                n, was_created = self._maybe_create(
                    interview, 'upcoming_clearance', dry_run
                )
                created += 1 if was_created else 0

            # ── Overdue final pay (7 days after clearance deadline) ─────────────
            pay_deadline = clearance_deadline + timedelta(days=7)
            if today > pay_deadline:
                n, was_created = self._maybe_create(
                    interview, 'overdue_pay', dry_run
                )
                created += 1 if was_created else 0

        action = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(
            f'{action} {created} notification(s), skipped {skipped} interview(s) without dates.'
        ))

    @staticmethod
    def _maybe_create(interview, notif_type, dry_run):
        """Return (notification, was_created) tuple."""
        if not interview.employee:
            return None, False
        if dry_run:
            exists = ExitInterviewNotification.objects.filter(
                interview=interview, notification_type=notif_type
            ).exists()
            return None, not exists
        return ExitInterviewNotification.objects.get_or_create(
            interview=interview,
            notification_type=notif_type,
        )
