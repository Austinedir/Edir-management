"""
Management command: import_austin_edir
Imports the Austin Area Mutual Aid EDIR membership data from a tab-delimited
text file (exported from the Excel MasterFile Worksheet #4).

Usage:
    python manage.py import_austin_edir --file path/to/edir_data.tsv

The command:
 - Creates (or updates) the EdirGroup "Austin Area Mutual Aid EDIR"
 - Imports every row as a Member record
 - Maps payment/contribution history to ContributionPeriod + Contribution records
 - Skips under-age (UA) and deceased/expelled placeholders cleanly
 - Is idempotent: safe to run multiple times
"""

import csv
import io
import os
import re
import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


# ── Column indices (0-based) from the TSV header ───────────────────────────
COL = {
    "family_id":         0,
    "membership_id":     1,
    "adult_count":       2,
    "first_name":        3,
    "last_name":         4,
    "gender":            5,
    "status":            6,
    "street":            7,
    "city":              8,
    "state":             9,
    "zip":               10,
    "cell_phone":        11,
    "email":             12,
    "alt_phone":         13,
    "rep_name":          14,
    "rep_phone":         15,
    "dob_minor":         16,
    "admin_fee":         17,
    "reg_fee_1":         18,
    "reg_fee_2":         19,
    "reg_fee_3":         20,
    "reg_paid_full":     21,
    "member_since":      22,
    "notes":             23,
    "total_paid_prev":   24,
    "overdue_prev":      25,
    "admin_2026":        26,
    "pay_method_admin":  27,
    "receipt_admin":     28,
    # Replenishment #27
    "repl27_amount":     29,
    "repl27_method":     30,
    "repl27_receipt":    31,
    # Replenishment #28
    "repl28_amount":     32,
    "repl28_method":     33,
    "repl28_receipt":    34,
    # Tab 4 totals
    "total_collected":   35,
    "overdue_current":   36,
    "adult_count2":      37,
    "payment_due_final": 38,
}

STATUS_MAP = {
    "active":       "active",
    "lapsed":       "suspended",
    "deceased":     "deceased",
    "expelled":     "withdrawn",
    "expelled.":    "withdrawn",
    "explled":      "withdrawn",
    "expelled ":    "withdrawn",
    "withdrawn":    "withdrawn",
    "discontinued": "withdrawn",
    "not a member": "withdrawn",
    "cancelled":    "withdrawn",
    "member discontinued": "withdrawn",
    "voluntarily forgo memebership": "withdrawn",
}

GENDER_MAP = {
    "m": "M", "male": "M", "f": "F", "female": "F",
}


def clean_money(val):
    """Parse a dollar string like '$25.00' or '25' to Decimal, else None."""
    if not val:
        return None
    val = val.strip().replace("$", "").replace(",", "")
    try:
        d = Decimal(val)
        return d if d != 0 else None
    except InvalidOperation:
        return None


def clean_phone(val):
    """Normalize phone to digits only, return empty string if invalid."""
    if not val:
        return ""
    digits = re.sub(r"[^\d+]", "", val)
    # Skip obvious placeholder values
    if digits in ("", "0", "00", "8"):
        return ""
    return val.strip()[:20]


def parse_date(val):
    """Try several date formats, return date object or None."""
    if not val:
        return None
    val = val.strip()
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%d-%b-%y", "%d-%b-%Y",
                "%Y-%m-%d", "%m/%d/%y", "%-m/%-d/%Y"):
        try:
            return datetime.datetime.strptime(val, fmt).date()
        except (ValueError, TypeError):
            pass
    # Try "1-Jan-15" style
    try:
        return datetime.datetime.strptime(val, "%d-%b-%y").date()
    except Exception:
        pass
    return None


def is_under_age_row(row):
    """Return True if this row is an under-age placeholder (no fees paid)."""
    status_raw = row[COL["status"]].strip().lower() if len(row) > COL["status"] else ""
    notes_raw  = row[COL["notes"]].strip().upper()  if len(row) > COL["notes"]  else ""
    return status_raw == "" and ("UA" in notes_raw or notes_raw == "")


class Command(BaseCommand):
    help = "Import Austin Area Mutual Aid EDIR data from a TSV/CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", "-f",
            required=True,
            help="Path to the tab-separated data file (exported from Excel)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without writing to the database",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing members before import (USE WITH CAUTION)",
        )

    def handle(self, *args, **options):
        from apps.members.models import EdirGroup, Member, Beneficiary
        from apps.contributions.models import (
            ContributionPeriod, Contribution,
        )

        filepath = options["file"]
        dry_run  = options["dry_run"]

        if not os.path.exists(filepath):
            raise CommandError(f"File not found: {filepath}")

        self.stdout.write(f"Reading: {filepath}")

        # ── Create or update EdirGroup ─────────────────────────────────────
        if not dry_run:
            edir, created = EdirGroup.objects.update_or_create(
                name="Austin Area Mutual Aid EDIR",
                defaults={
                    "location":             "Austin, TX (Greater Austin Area)",
                    "founded_date":         datetime.date(2015, 1, 1),
                    "monthly_contribution": Decimal("25.00"),
                    "death_payout":         Decimal("7500.00"),
                    "is_active":            True,
                },
            )
            action = "Created" if created else "Found existing"
            self.stdout.write(f"{action} EdirGroup: {edir.name}")
        else:
            self.stdout.write("[DRY RUN] Would create/update EdirGroup")
            edir = None

        # ── Clear if requested ─────────────────────────────────────────────
        if options["clear"] and not dry_run:
            count = Member.objects.filter(edir=edir).count()
            Member.objects.filter(edir=edir).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing members."))

        # ── Read the file ──────────────────────────────────────────────────
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            content = fh.read()

        # Detect delimiter
        delimiter = "\t" if "\t" in content[:2000] else ","
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)

        rows = list(reader)
        self.stdout.write(f"Total rows in file: {len(rows)}")

        # Skip header rows until we find the data
        data_rows = []
        for i, row in enumerate(rows):
            if not row:
                continue
            first = row[0].strip()
            # Data rows start with a numeric family ID or are blank (sub-members)
            if re.match(r"^\d{4}$", first) or first == "":
                data_rows.append(row)

        self.stdout.write(f"Data rows found: {len(data_rows)}")

        # ── Parse & import ─────────────────────────────────────────────────
        imported = skipped = errors = 0
        current_family_id = None

        with transaction.atomic():
            for row_num, row in enumerate(data_rows, 1):
                # Pad short rows
                while len(row) < 40:
                    row.append("")

                # ── Determine family ID ────────────────────────────────────
                family_id_raw = row[COL["family_id"]].strip()
                if re.match(r"^\d{4}$", family_id_raw):
                    current_family_id = family_id_raw
                elif family_id_raw in ("#N/A", "$0.00", "") and current_family_id:
                    pass  # sub-member row, use parent family ID
                else:
                    skipped += 1
                    continue

                membership_id = row[COL["membership_id"]].strip()
                if not membership_id or not re.match(r"^\d{4}\.\d+", membership_id.replace("-", ".")):
                    skipped += 1
                    continue

                first_name = row[COL["first_name"]].strip()
                last_name  = row[COL["last_name"]].strip()
                if not first_name:
                    skipped += 1
                    continue

                # ── Status mapping ─────────────────────────────────────────
                status_raw = row[COL["status"]].strip().lower()
                if not status_raw:
                    # Infer from context: under-age rows have no status
                    dob_val = row[COL["dob_minor"]].strip()
                    if dob_val and dob_val.upper() not in ("N/A", ""):
                        # Under-age family member - import as active minor
                        status_mapped = "active"
                    else:
                        skipped += 1
                        continue
                else:
                    # Normalize
                    status_key = status_raw.strip(".").strip()
                    status_mapped = STATUS_MAP.get(status_key, "active")

                # ── Gender ─────────────────────────────────────────────────
                gender_raw = row[COL["gender"]].strip().lower()
                gender     = GENDER_MAP.get(gender_raw, "M")

                # ── Contact ────────────────────────────────────────────────
                phone   = clean_phone(row[COL["cell_phone"]])
                email   = row[COL["email"]].strip()[:254]
                if email.upper() in ("N/A", "NA", ""):
                    email = ""
                city    = row[COL["city"]].strip()[:100]
                address = row[COL["street"]].strip()
                zip_code = row[COL["zip"]].strip()[:10]
                state   = row[COL["state"]].strip()[:5]
                if zip_code:
                    address_full = f"{address}, {city}, {state} {zip_code}".strip(", ")
                else:
                    address_full = address

                # ── Dates ──────────────────────────────────────────────────
                member_since_raw = row[COL["member_since"]].strip()
                join_date        = parse_date(member_since_raw) or datetime.date(2015, 1, 1)

                dob_raw  = row[COL["dob_minor"]].strip()
                dob      = parse_date(dob_raw) if dob_raw not in ("N/A", "NA", "", "0") else None

                # ── Designee / emergency contact ───────────────────────────
                rep_name  = row[COL["rep_name"]].strip()[:200]
                rep_phone = clean_phone(row[COL["rep_phone"]])[:20]

                # ── Notes ─────────────────────────────────────────────────
                notes = row[COL["notes"]].strip()[:500]

                # ── Build member number from membership_id ─────────────────
                member_number = f"EDR-{membership_id}"

                # ── Financial data ─────────────────────────────────────────
                total_paid   = clean_money(row[COL["total_paid_prev"]])  or Decimal("0")
                overdue      = clean_money(row[COL["overdue_prev"]])     or Decimal("0")
                admin_2026   = clean_money(row[COL["admin_2026"]])
                repl27       = clean_money(row[COL["repl27_amount"]])
                repl28       = clean_money(row[COL["repl28_amount"]])
                repl27_rcpt  = row[COL["repl27_receipt"]].strip()
                repl28_rcpt  = row[COL["repl28_receipt"]].strip()
                overdue_curr = clean_money(row[COL["overdue_current"]]) or Decimal("0")

                # Build summary note with financials
                financial_note = (
                    f"Total paid (through Repl #3): ${total_paid} | "
                    f"Overdue prev: ${overdue} | "
                    f"2026 Admin: ${admin_2026 or 0} | "
                    f"Repl#27: ${repl27 or 0} (rcpt {repl27_rcpt}) | "
                    f"Repl#28: ${repl28 or 0} (rcpt {repl28_rcpt}) | "
                    f"Current overdue: ${overdue_curr}"
                )
                full_notes = f"{notes}\n\n[FINANCIAL] {financial_note}".strip()

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] Would import: {membership_id} {first_name} {last_name} "
                        f"({status_mapped}) joined {join_date}"
                    )
                    imported += 1
                    continue

                try:
                    member, m_created = Member.objects.update_or_create(
                        member_number=member_number,
                        edir=edir,
                        defaults={
                            "first_name":                     first_name,
                            "last_name":                      last_name,
                            "gender":                         gender,
                            "date_of_birth":                  dob,
                            "phone":                          phone,
                            "email":                          email,
                            "address":                        address_full,
                            "city":                           city or "Austin",
                            "status":                         status_mapped,
                            "join_date":                      join_date,
                            "emergency_contact_name":         rep_name,
                            "emergency_contact_phone":        rep_phone,
                            "notes":                          full_notes,
                        },
                    )

                    # ── Create contribution records for replenishments ──────
                    # Repl #27 = Feb 2026 period
                    if repl27 and repl27 > 0:
                        period_27, _ = ContributionPeriod.objects.get_or_create(
                            edir=edir, year=2026, month=2,
                            defaults={
                                "amount":   Decimal("25.00"),
                                "due_date": datetime.date(2026, 2, 11),
                                "notes":    "Replenishment #27 - Shitaye Belay 02/11/2026",
                            },
                        )
                        contrib_27, _ = Contribution.objects.get_or_create(
                            period=period_27, member=member,
                            defaults={"amount": Decimal("25.00")},
                        )
                        if contrib_27.status != Contribution.Status.PAID:
                            contrib_27.status         = Contribution.Status.PAID
                            contrib_27.amount         = repl27
                            contrib_27.payment_method = _map_payment_method(row[COL["repl27_method"]])
                            contrib_27.receipt_number = repl27_rcpt[:50]
                            contrib_27.paid_date      = datetime.date(2026, 2, 11)
                            contrib_27.save()

                    # Repl #28 = Mar 2026 period
                    if repl28 and repl28 > 0:
                        period_28, _ = ContributionPeriod.objects.get_or_create(
                            edir=edir, year=2026, month=3,
                            defaults={
                                "amount":   Decimal("25.00"),
                                "due_date": datetime.date(2026, 3, 6),
                                "notes":    "Replenishment #28 - Ato Ketema Mengesha 03/06/2026",
                            },
                        )
                        contrib_28, _ = Contribution.objects.get_or_create(
                            period=period_28, member=member,
                            defaults={"amount": Decimal("25.00")},
                        )
                        if contrib_28.status != Contribution.Status.PAID:
                            contrib_28.status         = Contribution.Status.PAID
                            contrib_28.amount         = repl28
                            contrib_28.payment_method = _map_payment_method(row[COL["repl28_method"]])
                            contrib_28.receipt_number = repl28_rcpt[:50]
                            contrib_28.paid_date      = datetime.date(2026, 3, 6)
                            contrib_28.save()

                    # Overdue flag: create pending contribution if overdue > 0
                    if overdue_curr and overdue_curr > 0:
                        # Mark in the current period as pending (if not already paid)
                        period_curr, _ = ContributionPeriod.objects.get_or_create(
                            edir=edir, year=2026, month=4,
                            defaults={
                                "amount":   Decimal("25.00"),
                                "due_date": datetime.date(2026, 4, 30),
                                "notes":    "Current period - April 2026",
                            },
                        )
                        Contribution.objects.get_or_create(
                            period=period_curr, member=member,
                            defaults={
                                "amount": Decimal("25.00"),
                                "status": Contribution.Status.PENDING,
                            },
                        )

                    imported += 1
                    verb = "Created" if m_created else "Updated"
                    if imported % 50 == 0:
                        self.stdout.write(f"  ... {imported} members processed")

                except Exception as exc:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ERROR row {row_num} ({membership_id} {first_name} {last_name}): {exc}"
                        )
                    )

        # ── Summary ────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("IMPORT COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Imported/updated : {imported}")
        self.stdout.write(f"  Skipped          : {skipped}")
        self.stdout.write(f"  Errors           : {errors}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN - no data was written"))


def _map_payment_method(raw):
    """Map the spreadsheet payment code to our Contribution.PaymentMethod choices."""
    from apps.contributions.models import Contribution
    MAP = {
        "ZL": Contribution.PaymentMethod.MOBILE,   # Zelle
        "PP": Contribution.PaymentMethod.MOBILE,   # PayPal
        "CA": Contribution.PaymentMethod.CASH,     # Cash / CashApp
        "CH": Contribution.PaymentMethod.CASH,     # Cash
        "CK": Contribution.PaymentMethod.CHEQUE,   # Check
        "SQ": Contribution.PaymentMethod.MOBILE,   # Square
        "MO": Contribution.PaymentMethod.BANK,     # Money Order
        "CR": Contribution.PaymentMethod.BANK,     # Credit/overpayment
    }
    return MAP.get(raw.strip().upper(), Contribution.PaymentMethod.CASH)
