"""
Management command: seed_demo
Creates a demo edir group + sample members + contribution period for quick evaluation.
Usage: python manage.py seed_demo
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone


DEMO_MEMBERS = [
    ('Abebe', 'Girma', 'M', '+251911234001'),
    ('Tigist', 'Haile', 'F', '+251911234002'),
    ('Dawit', 'Bekele', 'M', '+251911234003'),
    ('Meron', 'Tadesse', 'F', '+251911234004'),
    ('Yonas', 'Alemu', 'M', '+251911234005'),
    ('Hiwot', 'Tesfaye', 'F', '+251911234006'),
    ('Bereket', 'Worku', 'M', '+251911234007'),
    ('Selam', 'Getachew', 'F', '+251911234008'),
    ('Mulugeta', 'Assefa', 'M', '+251911234009'),
    ('Rahel', 'Mengistu', 'F', '+251911234010'),
]


class Command(BaseCommand):
    help = 'Seed demo data: edir group, members, and a contribution period'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete existing demo data first')

    def handle(self, *args, **options):
        from apps.members.models import EdirGroup, Member, User
        from apps.contributions.models import ContributionPeriod, Contribution

        # Create superuser if none exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@edir.local',
                password='admin123',
                first_name='Edir',
                last_name='Admin',
            )
            self.stdout.write(self.style.WARNING('Created superuser: admin / admin123'))

        # Create edir group
        edir, _ = EdirGroup.objects.get_or_create(
            name='Addis Ketema Edir',
            defaults={
                'description': 'Demo edir group for the Addis Ketema neighbourhood',
                'location': 'Addis Ketema, Addis Ababa',
                'founded_date': datetime.date(2010, 1, 15),
                'monthly_contribution': 150,
                'death_payout': 7500,
            }
        )
        self.stdout.write(f'Edir group: {edir.name}')

        # Create members
        today = datetime.date.today()
        for i, (first, last, gender, phone) in enumerate(DEMO_MEMBERS):
            join_date = today - datetime.timedelta(days=30 * (12 + i))
            Member.objects.get_or_create(
                first_name=first,
                last_name=last,
                edir=edir,
                defaults={
                    'gender': gender,
                    'phone': phone,
                    'city': 'Addis Ababa',
                    'kebele': f'0{i+1}',
                    'woreda': 'Addis Ketema',
                    'status': 'active',
                    'join_date': join_date,
                }
            )

        member_count = Member.objects.filter(edir=edir).count()
        self.stdout.write(f'Members: {member_count}')

        # Create current month's contribution period
        now = timezone.now()
        period, created = ContributionPeriod.objects.get_or_create(
            edir=edir, year=now.year, month=now.month,
            defaults={
                'amount': edir.monthly_contribution,
                'due_date': today.replace(day=28),
            }
        )

        if created:
            active_members = Member.objects.filter(edir=edir, status='active')
            Contribution.objects.bulk_create([
                Contribution(period=period, member=m, amount=period.amount)
                for m in active_members
            ], ignore_conflicts=True)
            self.stdout.write(f'Created contribution period: {period} with {active_members.count()} records')

        self.stdout.write(self.style.SUCCESS('\n✓ Demo data seeded. Login at /accounts/login/ with admin / admin123'))
