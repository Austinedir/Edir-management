# Austin Area Mutual Aid EDIR
## ኦስተንና አካባቢው መረዳጃ ዕድር

Django-based membership management system for the Austin Area Ethiopian Mutual Aid Fund (Edir).

---

## Quick Start (Docker)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env – set SECRET_KEY, email settings, etc.

# 2. Start all services
docker compose up -d

# 3. Run migrations
docker compose exec web python manage.py migrate

# 4. Collect static files
docker compose exec web python manage.py collectstatic --noinput

# 5. Import your member data from the Excel masterfile
docker compose exec web python manage.py import_excel_data \
  --file /app/edir_data_as_of_3-2-2026_for_cloude.xlsx

# 6. Set up Celery scheduled tasks
docker compose exec web python manage.py setup_schedules

# 7. Open in browser
http://localhost:8000
```

**Login:** `admin` / `edir2026admin!` — **change this password immediately after first login!**

---

## Manual Setup (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env to set DATABASE_URL

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py import_excel_data --file /path/to/edir_data.xlsx
python manage.py runserver
```

---

## Importing Member Data

The `import_excel_data` command reads the official EDIR MasterFile Excel spreadsheet:

```bash
python manage.py import_excel_data --file /path/to/edir_data_as_of_3-2-2026_for_cloude.xlsx
```

Options:
- `--clear` — delete existing members before importing (use with caution)
- `--dry-run` — parse and show counts without saving

After import you will have:
- **1,496 member records** across 484 families
- Contribution periods: Admin 2026, Replenishment #27, Replenishment #28
- Payment status per member based on Excel data

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Redirects to dashboard |
| `/apply/` | **Public** online registration form |
| `/contact/` | **Public** member inquiry form |
| `/portal/` | Member self-service portal |
| `/portal/payments/` | Member payment history |
| `/portal/messages/` | Member inbox |
| `/portal/documents/` | Document archive |
| `/dashboard/` | Admin dashboard |
| `/members/` | Member list (admin) |
| `/contributions/` | Contribution periods |
| `/events/` | Events & payouts |
| `/admin-portal/applications/` | Review membership applications |
| `/admin-portal/messages/` | Admin message inbox |
| `/admin-portal/mass-messages/` | Send mass email/SMS |
| `/admin-portal/documents/upload/` | Upload bank statements |
| `/admin/` | Django admin panel |
| `/accounts/login/` | Login page |

---

## Features (by Functional Requirement)

### FR 1.1 – Existing Member Services
- ✅ Login / logout
- ✅ View member profile and family info
- ✅ Update personal information (pending admin approval)
- ✅ Check payment status with full history
- ✅ Send/receive messages with admin
- ✅ View archived documents

### FR 1.2 – New Member Registration
- ✅ Public online registration form at `/apply/`
- ✅ Registration fee information displayed
- ✅ Auto-email confirmation with pending status sent to applicant

### FR 2.1 – Financial
- ✅ Upload bank statements and financial documents

### FR 2.3 – Financial Reports
- ✅ Payment status reports
- ✅ Financial dashboard with charts
- ✅ Balance due notifications

### FR 2.4 – Application Review
- ✅ Admin reviews applications list
- ✅ Approve application → auto-creates Member record
- ✅ Deny application → with reason
- ✅ Auto-email sent on approval or denial
- ✅ Residential and county verification checkboxes

### FR 3 – Mass Communication
- ✅ Mass email to all active members
- ✅ Mass SMS (requires Twilio configuration)
- ✅ Filter by city or active-only
- ✅ Archive of all mass messages sent

### FR 4 – Communication
- ✅ Contact/inquiry form at `/contact/`
- ✅ Auto-acknowledge email to sender
- ✅ Archive of notices
- ✅ Member messaging system

---

## Architecture

```
edir/
├── apps/
│   ├── members/          # Users, EdirGroup, Member, Application, Message, Document
│   ├── contributions/    # ContributionPeriod, Contribution, SpecialLevy
│   ├── events/           # EdirEvent, Payout, MeetingMinute
│   └── notifications/    # Notification, Announcement, Celery tasks
├── templates/
│   ├── base/             # Shared layout
│   ├── portal/           # Member self-service templates
│   ├── admin_portal/     # Admin workflow templates
│   ├── registration/     # Public registration templates
│   ├── dashboard/        # Admin dashboard
│   ├── members/          # Member CRUD
│   ├── contributions/    # Contribution management
│   ├── events/           # Event management
│   └── notifications/    # Notifications
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── requirements.txt
```

## Services (Docker Compose)

| Service | Description |
|---------|-------------|
| `web` | Django + Gunicorn |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 (Celery broker) |
| `celery` | Celery worker |
| `celery-beat` | Celery Beat scheduler |
| `nginx` | Nginx reverse proxy |

## Scheduled Tasks

- **1st of month, 08:00** — Send monthly contribution reminders
- **Every Monday, 09:00** — Flag members with 3+ months arrears

---

## Payment Methods (from Excel data)

| Code | Meaning |
|------|---------|
| ZL | Zelle |
| CH | Cash |
| CK | Check |
| PP | PayPal |
| CA | CashApp |
| CR | Credit / Overpayment |
| MO | Money Order |
| SQ | Square |
| UA | Under Age |

---

*Built for Austin Area Mutual Aid EDIR. For support, contact your system administrator.*
