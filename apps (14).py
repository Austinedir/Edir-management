"""
Management command: seed_austin_edir
Seeds the database with the Austin Area Mutual Aid EDIR real member data
that was pasted directly into the system.

This command is for immediate deployment without needing the Excel file.
Run: python manage.py seed_austin_edir

For importing from the actual Excel/TSV file use:
  python manage.py import_austin_edir --file yourfile.tsv
"""
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction


# Real member data extracted from the pasted spreadsheet
# Format: (family_id, membership_id, first_name, last_name, gender,
#          status, city, phone, email, join_date, overdue, notes)
REAL_MEMBERS = [
    ("1001", "1001.1", "Million",     "Belete",          "M", "active",   "Pflugerville", "512-809-1965", "millionbelete@gmail.com",      "2015-01-01", 25.00,  ""),
    ("1001", "1001.2", "Gidey",       "Zemichael",       "F", "deceased", "Pflugerville", "",             "",                             "2015-01-01", 0,      "Deceased"),
    ("1002", "1002.1", "Bekele",      "Kassaye",         "M", "active",   "Round Rock",   "512-653-3948", "bekele11@gmail.com",            "2015-01-01", 0,      ""),
    ("1002", "1002.2", "Aster",       "A. Kassaye",      "F", "active",   "Round Rock",   "512-786-9524", "asterk1950@gmail.com",          "2015-01-01", 0,      ""),
    ("1002", "1002.3", "Kassaye",     "B. Kassaye",      "M", "active",   "Round Rock",   "737-247-5043", "kassayebk@gmail.com",           "2015-01-01", 0,      ""),
    ("1002", "1002.4", "Amelework",   "Ashena",          "F", "deceased", "Round Rock",   "",             "",                             "2015-01-01", 0,      "Deceased"),
    ("1003", "1003.1", "Fantu",       "Gayim",           "M", "active",   "Austin",       "512-784-0833", "fantugayim1948@gmail.com",      "2015-01-01", 25.00,  ""),
    ("1003", "1003.2", "Zuriashwork", "Wollie",          "F", "active",   "Austin",       "512-589-1605", "Zuriashwork.Wollie@dshs.state.tx.us", "2015-01-01", 25.00, ""),
    ("1004", "1004.1", "Turubrahan",  "Workineh",        "F", "active",   "Austin",       "512-565-7769", "tebedge@prodigy.net",           "2015-01-01", 35.00,  "No designee signature"),
    ("1004", "1004.2", "Asegedech",   "Kassa Kidanu",    "F", "active",   "Austin",       "512-423-2828", "",                             "2015-01-01", 35.00,  ""),
    ("1004", "1004.3", "Mehone",      "Sleshi Tebege",   "M", "active",   "Austin",       "512-565-7769", "",                             "2015-01-01", 35.00,  ""),
    ("1004", "1004.4", "Robel",       "Sleshi Tebege",   "M", "active",   "Austin",       "512-565-7769", "",                             "2015-01-01", 35.00,  ""),
    ("1004", "1004.5", "Wisley",      "Onsando Tebege",  "F", "active",   "Austin",       "512-565-7769", "",                             "2020-10-03", 35.00,  ""),
    ("1005", "1005.1", "Efrem",       "Borga",           "M", "active",   "Pflugerville", "512-426-9788", "eborga@yahoo.com",              "2015-01-01", 85.00,  ""),
    ("1005", "1005.2", "Belaniesh",   "Hailom",          "F", "active",   "Pflugerville", "512-431-4686", "belay8595@yahoo.com",           "2015-01-01", 85.00,  ""),
    ("1005", "1005.3", "Joshua",      "E. Borga",        "M", "active",   "Pflugerville", "512-590-5070", "jborga10@yahoo.com",            "2015-01-01", 60.00,  ""),
    ("1005", "1005.4", "Jonathan",    "E. Borga",        "M", "active",   "Pflugerville", "512-660-1242", "jonathanborga@gmail.com",       "2015-01-01", 60.00,  ""),
    ("1005", "1005.5", "Kidan",       "E. Borga",        "F", "active",   "Pflugerville", "512-431-1699", "kidanborga@yahoo.com",          "2015-01-01", 50.00,  ""),
    ("1005", "1005.6", "Tigest",      "Borga",           "F", "active",   "Pflugerville", "512-297-1566", "tborga@yahoo.com",              "2015-01-01", 185.00, ""),
    ("1006", "1006.1", "Tesfaye",     "Belay",           "M", "active",   "Cedar Park",   "512-619-2800", "tbelay1@gmail.com",             "2015-01-01", 50.00,  "Paid $35 to ID #1031"),
    ("1006", "1006.2", "Hiwot",       "Berhane",         "F", "active",   "Cedar Park",   "512-619-6241", "hiwotber@gmail.com",            "2015-01-01", 50.00,  ""),
    ("1006", "1006.3", "Filmon",      "Belay",           "M", "active",   "Cedar Park",   "",             "",                             "2015-01-01", 50.00,  ""),
    ("1006", "1006.4", "Melen",       "Belay",           "F", "active",   "Cedar Park",   "",             "",                             "2015-01-01", 50.00,  ""),
    ("1007", "1007.1", "Abeye",       "Teshome",         "M", "active",   "Austin",       "512-921-1770", "onegoro@yahoo.com",             "2015-01-01", 85.00,  ""),
    ("1007", "1007.2", "Viveka",      "Teshome",         "F", "active",   "Austin",       "512-342-7030", "vteshome@yahoo.com",            "2015-01-01", 85.00,  ""),
    ("1007", "1007.3", "Nolawie",     "Teshome",         "M", "active",   "Austin",       "",             "",                             "2015-01-01", 85.00,  ""),
    ("1007", "1007.4", "Nahome",      "Teshome",         "F", "active",   "Austin",       "",             "",                             "2015-01-01", 85.00,  ""),
    ("1007", "1007.5", "Leelai",      "Teshome",         "M", "active",   "Austin",       "",             "",                             "2015-01-01", 85.00,  "Turned 18"),
    ("1007", "1007.6", "Wubet",       "Tsadik",          "F", "active",   "Austin",       "",             "",                             "2015-01-01", 85.00,  ""),
    ("1008", "1008.1", "Gezahgne",    "T. Bogale",       "M", "active",   "Round Rock",   "512-743-2390", "geebogale@yahoo.com",           "2015-01-01", 25.00,  ""),
    ("1008", "1008.2", "Kidist",      "D. Abol",         "F", "active",   "Round Rock",   "512-506-1583", "kidistabol@yahoo.com",          "2015-01-01", 25.00,  ""),
    ("1008", "1008.3", "Taye",        "Gebremichael",    "M", "active",   "Round Rock",   "",             "",                             "2015-01-01", 25.00,  ""),
    ("1008", "1008.4", "Meneber",     "Weldesmayat",     "F", "active",   "Round Rock",   "",             "",                             "2015-01-01", 25.00,  ""),
    ("1009", "1009.1", "Mulualem",    "Getachew",        "F", "active",   "Round Rock",   "512-784-1152", "MUFAYTUZ21@YAHOO.COM",         "2015-01-01", 160.00, ""),
    ("1009", "1009.2", "Aklog",       "Nekeatibeb",      "M", "active",   "Round Rock",   "512-743-9244", "",                             "2015-01-01", 165.00, ""),
    ("1010", "1010.1", "Tsegaye",     "Ashenafi",        "M", "deceased", "Liberty Hill", "",             "",                             "2015-01-01", 0,      "Deceased"),
    ("1010", "1010.2", "Rebecca",     "Ashenafi",        "F", "withdrawn","Liberty Hill", "512-963-4871", "",                             "2015-01-01", 0,      "Expelled"),
    ("1010", "1010.3", "Haymanot",    "Ashenafi",        "F", "withdrawn","Liberty Hill", "512-944-8745", "",                             "2015-01-01", 0,      "Expelled"),
    ("1010", "1010.4", "Bewketu",     "Ashenafi",        "M", "withdrawn","Liberty Hill", "512-983-6746", "",                             "2015-01-01", 0,      "Expelled"),
    ("1011", "1011.1", "Daniel",      "Stephanos",       "M", "active",   "Austin",       "512-797-6872", "dstephanos@gmail.com",          "2015-01-01", 195.00, "Divorced"),
    ("1011", "1011.2", "Rahel",       "Berhane",         "F", "active",   "Austin",       "512-431-5572", "Rxberhane@seton.org",           "2015-01-01", 60.00,  "Divorced"),
    ("1011", "1011.3", "Sessen",      "Stephanos",       "F", "active",   "Austin",       "",             "",                             "2015-01-01", 60.00,  "Turned 18"),
    ("1011", "1011.4", "Senai",       "Stephanos",       "F", "deceased", "Austin",       "",             "",                             "2015-01-01", 0,      "Deceased"),
    ("1011", "1011.5", "Blaine",      "Stephanos",       "M", "active",   "Austin",       "",             "",                             "2015-01-01", 60.00,  "Turned 18"),
    ("1012", "1012.1", "Abesha",      "Haile Michael",   "F", "active",   "Round Rock",   "737-222-9783", "abeshahm@gmail.com",            "2015-01-01", 60.00,  ""),
    ("1012", "1012.2", "Yidnekachew", "Michael Tibebu",  "M", "active",   "Round Rock",   "512-659-4866", "yidnek.tibebu@gmail.com",       "2015-01-01", 60.00,  ""),
    ("1012", "1012.3", "Yilak",       "Michael Tibebu",  "M", "active",   "Round Rock",   "512-696-4173", "",                             "2015-01-01", 60.00,  ""),
]

# Replenishment events
REPLENISHMENTS = [
    {"num": 27, "year": 2026, "month": 2, "day": 11,
     "deceased": "Shitaye Belay", "amount": Decimal("25.00")},
    {"num": 28, "year": 2026, "month": 3, "day": 6,
     "deceased": "Ato Ketema Mengesha", "amount": Decimal("25.00")},
]


class Command(BaseCommand):
    help = "Seed Austin Area Mutual Aid EDIR with real member data (first 50 families + all replenishments)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Seed all members from the full dataset (requires --file)"
        )

    def handle(self, *args, **options):
        from apps.members.models import EdirGroup, Member
        from apps.contributions.models import ContributionPeriod, Contribution

        self.stdout.write("Setting up Austin Area Mutual Aid EDIR...")

        with transaction.atomic():
            # Create superuser if none exists
            from apps.members.models import User
            if not User.objects.filter(is_superuser=True).exists():
                User.objects.create_superuser(
                    username="admin",
                    email="admin@austinedir.org",
                    password="admin123",
                    first_name="EDIR",
                    last_name="Admin",
                )
                self.stdout.write(self.style.WARNING("Created superuser: admin / admin123"))

            # Create EdirGroup
            edir, _ = EdirGroup.objects.update_or_create(
                name="Austin Area Mutual Aid EDIR",
                defaults={
                    "description":          "Ethiopian mutual aid fund serving the Greater Austin area, Texas.",
                    "location":             "Austin, TX (Greater Austin Area)",
                    "founded_date":         datetime.date(2015, 1, 1),
                    "monthly_contribution": Decimal("25.00"),
                    "death_payout":         Decimal("7500.00"),
                    "is_active":            True,
                },
            )
            self.stdout.write(f"EdirGroup: {edir.name}")

            # Create contribution periods for the two replenishments
            periods = {}
            for repl in REPLENISHMENTS:
                period, created = ContributionPeriod.objects.update_or_create(
                    edir=edir,
                    year=repl["year"],
                    month=repl["month"],
                    defaults={
                        "amount":   repl["amount"],
                        "due_date": datetime.date(repl["year"], repl["month"], repl["day"]),
                        "notes":    f"Replenishment #{repl['num']} - {repl['deceased']}",
                    },
                )
                periods[repl["num"]] = period
                verb = "Created" if created else "Found"
                self.stdout.write(f"{verb} period: Replenishment #{repl['num']} ({period})")

            # Import members
            imported = 0
            for (fam_id, mem_id, first, last, gender, status, city,
                 phone, email, join_str, overdue, notes) in REAL_MEMBERS:

                join_date = datetime.datetime.strptime(join_str, "%Y-%m-%d").date()
                member_number = f"EDR-{mem_id}"

                member, m_created = Member.objects.update_or_create(
                    member_number=member_number,
                    edir=edir,
                    defaults={
                        "first_name": first,
                        "last_name":  last,
                        "gender":     gender,
                        "phone":      phone[:20] if phone else "",
                        "email":      email[:254] if email else "",
                        "city":       city,
                        "status":     status,
                        "join_date":  join_date,
                        "notes":      f"{notes}\n[Family ID: {fam_id}] [Overdue: ${overdue}]".strip(),
                    },
                )
                imported += 1

                # Create pending contribution if overdue
                if overdue > 0 and status == "active":
                    curr_period, _ = ContributionPeriod.objects.get_or_create(
                        edir=edir, year=2026, month=4,
                        defaults={
                            "amount":   Decimal("25.00"),
                            "due_date": datetime.date(2026, 4, 30),
                            "notes":    "April 2026 - Current period",
                        },
                    )
                    Contribution.objects.get_or_create(
                        period=curr_period,
                        member=member,
                        defaults={
                            "amount": Decimal("25.00"),
                            "status": Contribution.Status.PENDING,
                        },
                    )

            self.stdout.write(self.style.SUCCESS(f"\n✓ Seeded {imported} members from Austin Area Mutual Aid EDIR"))
            self.stdout.write(self.style.SUCCESS(f"✓ Created {len(periods)} contribution periods (Replenishments #27 & #28)"))
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("  1. Login at /accounts/login/ with: admin / admin123")
            self.stdout.write("  2. To import the FULL dataset from your Excel file:")
            self.stdout.write("     python manage.py import_austin_edir --file yourdata.tsv")
            self.stdout.write("  3. Run python manage.py setup_schedules to activate reminders")
