"""
Austin Area Mutual Aid EDIR - Data Notes
=========================================

This file documents how the spreadsheet columns map to Django models.

EDIR STRUCTURE
--------------
- The fund is called "Austin Area Mutual Aid EDIR"
- Located in Austin, TX (Greater Austin area incl. Round Rock, Pflugerville,
  Cedar Park, Manor, Hutto, San Antonio, etc.)
- Founded: January 1, 2015
- Each "Replenishment" = one contribution event triggered by a member's death
- Payment amount per replenishment = $25.00 per adult member
- Admin fee = $10/year per adult member

SPREADSHEET → MODEL MAPPING
-----------------------------
Family Member ID       → Member.member_number prefix (e.g., "1001")
Membership ID #        → Member.member_number (e.g., "EDR-1001.1")
Adult Membership count → Used to determine contribution responsibility
First Name / Last Name → Member.first_name / last_name
Male/Female            → Member.gender
Membership Status      → Member.status (mapped below)
Street/City/State/Zip  → Member.address, city
Cell Phone             → Member.phone
E-Mail Address         → Member.email
Name of Designated Rep → Member.emergency_contact_name
Cell Phone of Desig Rep→ Member.emergency_contact_phone
Date of Birth (Minors) → Member.date_of_birth
Member Since           → Member.join_date
Notes                  → Member.notes

Total Paid (Tab #3)    → stored in notes as financial history
Payment overdue (Tab#3)→ stored in notes
2026 Admin Fee         → Contribution record (admin, 2026)
Replenishment #27      → ContributionPeriod(year=2026, month=2) + Contribution
Replenishment #28      → ContributionPeriod(year=2026, month=3) + Contribution
Payment Method codes:
  ZL = Zelle          → PaymentMethod.MOBILE
  PP = PayPal         → PaymentMethod.MOBILE
  CA = CashApp/Cash   → PaymentMethod.CASH
  CH = Cash           → PaymentMethod.CASH
  CK = Check          → PaymentMethod.CHEQUE
  SQ = Square         → PaymentMethod.MOBILE
  MO = Money Order    → PaymentMethod.BANK
  CR = Credit         → PaymentMethod.BANK

STATUS MAPPING
--------------
Active                          → active
Lapsed                          → suspended
Deceased                        → deceased
Expelled / Expelled.            → withdrawn
Expelled (text variants)        → withdrawn
Member Discontinued             → withdrawn
Not a Member                    → withdrawn
Cancelled as requested          → withdrawn
Voluntarily forgo membership    → withdrawn
(blank with DOB = minor)        → active
UA in notes = Under Age         → active (minor family member)

FAMILY STRUCTURE
----------------
Each family has:
  - 1001.1 = primary adult (family head)
  - 1001.2 = spouse or second adult
  - 1001.3+ = additional adults or children

Children under 18:
  - Marked with DOB in "Date of Birth (For Minors only)" column
  - Payment columns show $0 / "UA"
  - Still imported as Member records (status=active, minor=True implied by DOB)

REPLENISHMENT EVENTS (from data)
---------------------------------
Repl #27 = Death of Shitaye Belay, 02/11/2026 → $25.00 per adult
Repl #28 = Death of Ato Ketema Mengesha, 03/06/2026 → $25.00 per adult

OVERDUE AMOUNTS
---------------
"Payment overdue per each member" column shows cumulative arrears.
Members with overdue > 0 get a PENDING contribution for the current period.
Members with high overdue (e.g., $530) are typically expelled/inactive.

HOW TO IMPORT
-------------
1. Export the Excel Worksheet #4 as a .tsv or .csv file
2. Run:
   python manage.py import_austin_edir --file path/to/export.tsv
3. For dry run first:
   python manage.py import_austin_edir --file path/to/export.tsv --dry-run
4. To re-import cleanly:
   python manage.py import_austin_edir --file path/to/export.tsv --clear
"""
