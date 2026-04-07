"""
Management command: setup_schedules
Run once after migrations to register all Celery Beat periodic tasks.
Usage: python manage.py setup_schedules
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Create default Celery Beat periodic task schedules for EDIR'

    def handle(self, *args, **options):
        # 1. Monthly contribution reminders – 1st of every month at 8:00 AM
        monthly_cron, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='8', day_of_month='1',
            month_of_year='*', day_of_week='*',
        )
        task, created = PeriodicTask.objects.update_or_create(
            name='Monthly Contribution Reminders',
            defaults={
                'crontab': monthly_cron,
                'task': 'apps.notifications.tasks.send_contribution_reminders',
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'}: Monthly Contribution Reminders (1st of month, 08:00)"
        ))

        # 2. Defaulter alerts – every Monday at 9:00 AM
        weekly_cron, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='9', day_of_month='*',
            month_of_year='*', day_of_week='1',
        )
        task, created = PeriodicTask.objects.update_or_create(
            name='Weekly Defaulter Check',
            defaults={
                'crontab': weekly_cron,
                'task': 'apps.notifications.tasks.flag_chronic_defaulters',
                'args': json.dumps([]),
                'enabled': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'}: Weekly Defaulter Check (Mondays, 09:00)"
        ))

        self.stdout.write(self.style.SUCCESS('\n✓ All schedules configured successfully.'))
