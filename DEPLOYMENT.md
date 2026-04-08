# EDIR Deployment Guide
## Austin Area Mutual Aid EDIR – ኦስተንና አካባቢው መረዳጃ ዕድር

---

## Option A — Railway (Recommended, Fastest)

**Cost:** Free $5 credit to start, then ~$15–25/month for web + Postgres + Redis

### Step 1 – Create a GitHub repository

1. Go to **github.com** → sign in → click **New repository**
2. Name it `edir-management`
3. Click **Create repository**
4. Upload this project:
   ```bash
   unzip edir_project_final.zip
   cd edir
   git init
   git add .
   git commit -m "Initial EDIR project"
   git remote add origin https://github.com/YOUR_USERNAME/edir-management.git
   git push -u origin main
   ```

### Step 2 – Deploy on Railway

1. Go to **railway.app** → **Sign in with GitHub**
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `edir-management`
4. Railway will detect the Dockerfile automatically

### Step 3 – Add PostgreSQL

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway automatically sets `DATABASE_URL` as an environment variable

### Step 4 – Add Redis

1. Click **+ New** → **Database** → **Redis**
2. Railway automatically sets `REDIS_URL`

### Step 5 – Set Environment Variables

In your Railway web service, go to **Variables** and add:

```
SECRET_KEY        = (click "Generate" for a random value)
DEBUG             = False
ALLOWED_HOSTS     = .railway.app
EDIR_NAME         = Austin Area Mutual Aid EDIR
EDIR_CURRENCY     = USD
DEFAULT_FROM_EMAIL = noreply@austinedir.org
EMAIL_BACKEND     = django.core.mail.backends.console.EmailBackend
SECURE_SSL_REDIRECT = False
```

### Step 6 – Run migrations and import data

In Railway's **Shell** tab (or locally with Railway CLI):

```bash
python manage.py migrate
python manage.py import_excel_data --file /app/edir_data_as_of_3-2-2026_for_cloude.xlsx
python manage.py setup_schedules
```

> **To upload your Excel file**, add it to your GitHub repository first, or use Railway's volume mount.

### Step 7 – Get your URL

Railway gives you a URL like `https://edir-management-production.railway.app`

**Done!** Login at `https://your-app.railway.app/accounts/login/`
- Username: `admin`
- Password: `edir2026admin!` ← **Change this immediately!**

---

## Option B — Render.com (Free tier available)

**Cost:** Starter plan ~$7/month per service (web + db + redis = ~$21+/month)

### Steps

1. Go to **render.com** → Sign up with GitHub
2. Click **New** → **Blueprint**
3. Upload `render.yaml` from this project to your GitHub repo
4. Render reads `render.yaml` and creates all services automatically

### Set these environment variables in Render dashboard:
```
SECRET_KEY        = (generate a random 50-char string)
EDIR_NAME         = Austin Area Mutual Aid EDIR
DEFAULT_FROM_EMAIL = noreply@austinedir.org
EMAIL_BACKEND     = django.core.mail.backends.console.EmailBackend
```

### After deploy, open the Shell and run:
```bash
python manage.py import_excel_data --file /path/to/edir_data.xlsx
python manage.py setup_schedules
```

---

## Option C — Fly.io

**Cost:** ~$5–10/month (generous free tier for small apps)

### Steps

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup`
3. From the project folder:
   ```bash
   cd edir
   fly launch --no-deploy   # uses fly.toml
   fly postgres create --name edir-db --region dfw
   fly postgres attach edir-db
   fly redis create --name edir-redis
   fly secrets set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
   fly secrets set DEBUG=False
   fly secrets set EDIR_NAME="Austin Area Mutual Aid EDIR"
   fly deploy
   ```
4. Run migrations:
   ```bash
   fly ssh console -C "python manage.py migrate"
   fly ssh console -C "python manage.py import_excel_data --file /path/to/edir_data.xlsx"
   ```

---

## Option D — Your own Linux Server (VPS)

**Best for full control.** Works on DigitalOcean, Linode, Hetzner (~$5–10/month).

```bash
# On your server (Ubuntu 22.04)
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git

git clone https://github.com/YOUR_USERNAME/edir-management.git
cd edir-management

cp .env.example .env
nano .env   # Set SECRET_KEY, email settings, etc.

docker compose up -d

# Import data
docker compose exec web python manage.py migrate
docker compose exec web python manage.py import_excel_data \
  --file /path/to/edir_data_as_of_3-2-2026_for_cloude.xlsx
docker compose exec web python manage.py setup_schedules
docker compose exec web python manage.py collectstatic --noinput
```

For HTTPS, install **Caddy**:
```bash
sudo apt install caddy
# Edit /etc/caddy/Caddyfile:
#   yourdomain.com {
#     reverse_proxy localhost:8000
#   }
sudo systemctl restart caddy
```

---

## After Deployment – Checklist

- [ ] Change admin password at `/accounts/password/change/`
- [ ] Set up real email (Gmail/SendGrid) in environment variables
- [ ] Upload the Excel data file and run the import command
- [ ] Test the public registration form at `/apply/`
- [ ] Test the contact form at `/contact/`
- [ ] Send a test mass email from `/admin-portal/mass-messages/new/`
- [ ] Upload a sample document from `/admin-portal/documents/upload/`
- [ ] Share the site URL with members

---

## Email Setup (for real emails, not console)

Use Gmail with an App Password or SendGrid:

```bash
# Gmail
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=youraddress@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password   # from Google Account > Security > App passwords
DEFAULT_FROM_EMAIL=noreply@austinedir.org

# SendGrid (better for bulk)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your_sendgrid_api_key
```

---

## Generating a SECRET_KEY

```python
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

*Austin Area Mutual Aid EDIR — Management System*
