"""
Management command: import_excel_data
Imports the Austin Area Mutual Aid EDIR MasterFile Excel data.

Usage:
    python manage.py import_excel_data --file /path/to/edir_data.xlsx
    python manage.py import_excel_data --file /path/to/edir_data.xlsx --clear
    python manage.py import_excel_data --file /path/to/edir_data.xlsx --dry-run
"""
import datetime
import os
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import member data from the EDIR MasterFile Excel spreadsheet'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to the Excel .xlsx file')
        parser.add_argument('--dry-run', action='store_true', help='Parse but do not save')
        parser.add_argument('--clear', action='store_true', help='Clear existing members first')

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('pandas is required: pip install pandas openpyxl')

        filepath = options['file']
        if not os.path.exists(filepath):
            raise CommandError(f'File not found: {filepath}')

        self.stdout.write(self.style.HTTP_INFO(f'\nReading {filepath} ...'))

        # ── Parse Excel ──────────────────────────────────────────────────────
        df = pd.read_excel(filepath, header=None)
        raw = df.iloc[3:, :39].copy()
        raw.columns = list(range(39))
        raw = raw.dropna(how='all').reset_index(drop=True)
        raw = raw[raw[1].notna()].reset_index(drop=True)

        # Forward-fill Family ID (col 0)
        fam_id = None
        for i in range(len(raw)):
            v = raw.at[i, 0]
            if v is not None and str(v).strip() not in ('nan', '', 'NaN'):
                fam_id = str(v).strip().split('.')[0]
            raw.at[i, 'fam_id'] = fam_id

        self.stdout.write(f'  Parsed {len(raw)} member rows')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN – not saving to database.'))
            return

        # ── Imports ──────────────────────────────────────────────────────────
        from apps.members.models import EdirGroup, Member, User
        from apps.contributions.models import ContributionPeriod, Contribution

        # ── Create / get EDIR group ──────────────────────────────────────────
        edir, created = EdirGroup.objects.get_or_create(
            name='Austin Area Mutual Aid EDIR',
            defaults={
                'description': 'ኦስተንና አካባቢው መረዳጃ ዕድር – Austin Area Ethiopian Mutual Aid Fund',
                'location': 'Austin / San Antonio, TX',
                'founded_date': datetime.date(2015, 1, 1),
                'monthly_contribution': Decimal('25.00'),
                'death_payout': Decimal('7500.00'),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Created EDIR group'))
        else:
            self.stdout.write(f'  ✓ Using existing EDIR group: {edir.name}')

        # ── Create superuser if none exists ──────────────────────────────────
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@austinedir.org',
                password='edir2026admin!',
                first_name='EDIR',
                last_name='Admin',
            )
            self.stdout.write(self.style.WARNING(
                '  ✓ Superuser created: admin / edir2026admin! (CHANGE THIS PASSWORD!)'
            ))

        # ── Optionally clear members ─────────────────────────────────────────
        if options['clear']:
            count, _ = Member.objects.filter(edir=edir).delete()
            self.stdout.write(self.style.WARNING(f'  Cleared {count} existing members'))

        # ── Helpers ──────────────────────────────────────────────────────────
        def s(v):
            if v is None:
                return ''
            import pandas as pd
            if pd.isna(v):
                return ''
            return str(v).strip()

        def normalize_status(v):
            t = s(v).lower()
            if 'active' in t:
                return Member.Status.ACTIVE
            if 'deceased' in t:
                return Member.Status.DECEASED
            return Member.Status.WITHDRAWN

        def normalize_gender(v):
            t = s(v).upper()[:1]
            return Member.Gender.FEMALE if t == 'F' else Member.Gender.MALE

        def parse_date(v):
            import pandas as pd
            if v is None or (hasattr(v, '__class__') and pd.isna(v)):
                return None
            if hasattr(v, 'date'):
                return v.date()
            raw_str = str(v).strip()[:10]
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.datetime.strptime(raw_str, fmt).date()
                except (ValueError, TypeError):
                    continue
            return None

        def dec(v):
            try:
                import pandas as pd
                x = float(v)
                if pd.isna(x):
                    return Decimal('0.00')
                return Decimal(str(round(x, 2)))
            except (TypeError, ValueError):
                return Decimal('0.00')

        # ── Import Members ────────────────────────────────────────────────────
        self.stdout.write('\nImporting members...')
        created_count = updated_count = skipped_count = 0
        contribution_data = []

        for i in range(len(raw)):
            r = raw.iloc[i]
            first = s(r[3])
            last = s(r[4])
            mem_id = s(r[1])

            if not first or not mem_id:
                skipped_count += 1
                continue

            fid = s(r['fam_id'])
            member_number = f'EDR-{mem_id}'
            status = normalize_status(r[6])
            gender = normalize_gender(r[5])
            join_date = parse_date(r[22]) or datetime.date(2015, 1, 1)
            dob = parse_date(r[16])
            phone = s(r[11])[:20]
            email = s(r[12])[:254]
            address = s(r[7])
            city = s(r[8])
            state = (s(r[9]) or 'TX')[:10]
            zip_code = s(r[10])[:20]
            rep_name = s(r[14])[:200]
            rep_phone = s(r[15])[:20]
            notes_raw = s(r[23])

            total_paid = dec(r[24])
            current_overdue = dec(r[36])
            admin_2026 = dec(r[26])
            repl27 = dec(r[29])
            repl28 = dec(r[32])

            notes = f'Family ID: {fid} | Membership ID: {mem_id}'
            if notes_raw:
                notes = notes_raw + '\n' + notes
            notes += f'\nTotal Paid: ${total_paid} | Current Overdue: ${current_overdue}'

            defaults = {
                'first_name': first,
                'last_name': last,
                'gender': gender,
                'status': status,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'phone': phone,
                'email': email,
                'join_date': join_date,
                'date_of_birth': dob,
                'emergency_contact_name': rep_name,
                'emergency_contact_phone': rep_phone,
                'notes': notes[:2000],
                'edir': edir,
                'kebele': '',
                'woreda': '',
            }
            if status == Member.Status.DECEASED:
                defaults['exit_date'] = datetime.date(2026, 1, 1)

            try:
                member, was_created = Member.objects.update_or_create(
                    member_number=member_number,
                    defaults=defaults,
                )
                if was_created:
                    created_count += 1
                else:
                    updated_count += 1

                contribution_data.append({
                    'member': member,
                    'repl27': repl27,
                    'repl28': repl28,
                    'admin_2026': admin_2026,
                    'status': status,
                })

                if (created_count + updated_count) % 100 == 0:
                    self.stdout.write(f'  ... {created_count + updated_count} processed')

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Error for {member_number} ({first} {last}): {e}'
                ))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n  ✓ Members: {created_count} created, {updated_count} updated, {skipped_count} skipped'
        ))

        # ── Create Contribution Periods ──────────────────────────────────────
        self.stdout.write('\nCreating contribution periods...')

        period_admin, _ = ContributionPeriod.objects.get_or_create(
            edir=edir, year=2026, month=1,
            defaults={
                'amount': Decimal('10.00'),
                'due_date': datetime.date(2026, 1, 31),
                'notes': '2026 Annual Admin Fee',
            }
        )
        period27, _ = ContributionPeriod.objects.get_or_create(
            edir=edir, year=2026, month=2,
            defaults={
                'amount': Decimal('25.00'),
                'due_date': datetime.date(2026, 2, 11),
                'notes': 'Replenishment #27 – W/o Shitaye Belay 02/11/2026',
            }
        )
        period28, _ = ContributionPeriod.objects.get_or_create(
            edir=edir, year=2026, month=3,
            defaults={
                'amount': Decimal('25.00'),
                'due_date': datetime.date(2026, 3, 6),
                'notes': 'Replenishment #28 – Ato Ketema Mengesha 03/6/2026',
            }
        )
        self.stdout.write('  ✓ Periods: Admin 2026, Repl #27 (Feb), Repl #28 (Mar)')

        # ── Create Contribution Records ──────────────────────────────────────
        self.stdout.write('\nCreating contribution records...')
        contrib_created = 0

        for cd in contribution_data:
            member = cd['member']
            is_active = cd['status'] == Member.Status.ACTIVE
            pending_status = Contribution.Status.PENDING if is_active else Contribution.Status.WAIVED

            # Admin 2026
            if cd['admin_2026'] > 0:
                _, c = Contribution.objects.get_or_create(
                    period=period_admin, member=member,
                    defaults={'amount': Decimal('10.00'), 'status': Contribution.Status.PAID,
                              'paid_date': datetime.date(2026, 1, 15)}
                )
                if c: contrib_created += 1
            else:
                Contribution.objects.get_or_create(
                    period=period_admin, member=member,
                    defaults={'amount': Decimal('10.00'), 'status': pending_status}
                )

            # Replenishment #27
            if cd['repl27'] > 0:
                _, c = Contribution.objects.get_or_create(
                    period=period27, member=member,
                    defaults={'amount': Decimal('25.00'), 'status': Contribution.Status.PAID,
                              'paid_date': datetime.date(2026, 2, 11),
                              'payment_method': Contribution.PaymentMethod.CASH}
                )
                if c: contrib_created += 1
            else:
                Contribution.objects.get_or_create(
                    period=period27, member=member,
                    defaults={'amount': Decimal('25.00'), 'status': pending_status}
                )

            # Replenishment #28
            if cd['repl28'] > 0:
                _, c = Contribution.objects.get_or_create(
                    period=period28, member=member,
                    defaults={'amount': Decimal('25.00'), 'status': Contribution.Status.PAID,
                              'paid_date': datetime.date(2026, 3, 6),
                              'payment_method': Contribution.PaymentMethod.CASH}
                )
                if c: contrib_created += 1
            else:
                Contribution.objects.get_or_create(
                    period=period28, member=member,
                    defaults={'amount': Decimal('25.00'), 'status': pending_status}
                )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Contribution records created: {contrib_created}'))

        # ── Summary ──────────────────────────────────────────────────────────
        total = created_count + updated_count
        active = Member.objects.filter(edir=edir, status='active').count()
        self.stdout.write(self.style.SUCCESS(f'''
╔══════════════════════════════════════════════╗
║         IMPORT COMPLETE                      ║
╠══════════════════════════════════════════════╣
║  Total members imported : {total:<18} ║
║  Active                 : {active:<18} ║
║  Contribution records   : {contrib_created:<18} ║
╠══════════════════════════════════════════════╣
║  Login: admin / edir2026admin!               ║
║  URL  : http://localhost:8000/accounts/login ║
╚══════════════════════════════════════════════╝
'''))
