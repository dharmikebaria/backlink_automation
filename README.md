# Backlink Automation Tool

> **SEO Backlink Builder** — A Django web dashboard that automates publishing blog content across 8 major platforms (Quora, Medium, Tumblr, Dev.to, Hackernoon, Substack, WritersCafe, Patreon) to build backlinks at scale.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-5.2-green.svg)
![Selenium](https://img.shields.io/badge/Selenium-4.15+-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

---

## What It Does

You write blog content once in `blog.txt`, store your platform credentials through the web UI, then trigger automated posting runs. The tool logs into each platform using a real Chrome browser (undetected mode), creates and publishes the post with optional images, and logs the result to `results.csv`.

### Supported Platforms

| Platform | Script | Notes |
|---|---|---|
| **Quora** | `quora.py` | Logs in, creates a post/answer with blog content |
| **Tumblr** | `tumblr.py` | Posts to Tumblr blog with images via clipboard |
| **Dev.to** | `dev.py` | Creates and publishes article on dev.to |
| **Hackernoon** | `noon.py` | Submits story to Hackernoon |
| **Medium** | `m2.py` | Publishes post to Medium (supports email OTP login) |
| **Substack** | `sub.py` | Creates post on Substack publication |
| **WritersCafe** | `write.py` | Posts to WritersCafe.org |
| **Patreon** | `patreon.py` | Creates a patron post on Patreon |

---

## Architecture

```
project_backlink/
├── backlink/                    # Django project config
│   ├── settings.py              # Settings (SECRET_KEY via .env)
│   └── urls.py                  # Root URL routing
├── backlinkapp/                 # Main Django app
│   ├── models.py                # Credential model (url, email, username, password)
│   ├── views.py                 # 19 view functions
│   ├── urls.py                  # 19 URL endpoints
│   └── utils.py                 # CSV parser + automation runner helpers
├── templates/                   # Django HTML templates
│   ├── base.html                # Shared layout
│   ├── login.html               # Dashboard login
│   ├── dashboard.html           # Main control panel
│   ├── blog_update.html         # Blog content editor
│   ├── analytics.html           # Charts (daily/weekly/monthly/yearly)
│   ├── history.html             # Run history with filters
│   └── image.html               # Image manager
├── Advance Backlink/            # Automation engine (Selenium scripts)
│   ├── script.py                # Main orchestrator — routes to platform handlers
│   ├── website_analyzer.py      # Detects which platform a URL belongs to
│   ├── browser_manager.py       # Shared Chrome driver setup (undetected-chromedriver)
│   ├── quora.py                 # Quora automation handler
│   ├── tumblr.py                # Tumblr automation handler
│   ├── dev.py                   # Dev.to automation handler
│   ├── noon.py                  # Hackernoon automation handler
│   ├── m2.py                    # Medium automation handler
│   ├── sub.py                   # Substack automation handler
│   ├── write.py                 # WritersCafe automation handler
│   ├── patreon.py               # Patreon automation handler
│   ├── blog.txt                 # Blog content to post (edit via dashboard)
│   ├── Image/                   # Images attached to posts
│   └── results.csv              # Run history log (git-ignored)
├── manage.py
├── setup_login.py               # One-time Tumblr browser login helper
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Prerequisites

- **Python 3.10+**
- **Google Chrome** (the automation uses a real Chrome browser)
- **Windows** recommended — some features use Windows-only clipboard APIs (`pywin32`, `win32clipboard`) for pasting images into post editors
- Virtual environment tool (`venv`)

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/backlink_automation.git
cd backlink_automation/project_backlink

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY to a long random string
```

### 3. Set Up Database

```bash
python manage.py migrate
```

### 4. Run the Dashboard

```bash
python manage.py runserver
```

Open **http://localhost:8000** and log in with:
- Username: `backlink`
- Password: `backlink123`

> To change the login credentials, edit the `login_view` function in `backlinkapp/views.py`.

---

## Dashboard Workflow

### Step 1 — Add Credentials
Go to **Dashboard → Add Credential** or upload a bulk Excel/CSV file.

Each credential needs:
- **URL** — the platform login URL (e.g. `https://www.quora.com/`)
- **Email** — login email for that platform
- **Username** — username (if separate from email)
- **Password** — login password

### Step 2 — Write Blog Content
Go to **Blog Update**, write or paste your blog post, and save. This writes to `Advance Backlink/blog.txt`.

### Step 3 — Add Images (Optional)
Go to **Image Manager** and upload `.png`, `.jpg`, `.webp` images to include in posts.

### Step 4 — Run Automation
On the **Dashboard**, select a credential from the dropdown and click **Run**. To post to all active platforms at once, select **Run All**.

The system:
1. Writes a temporary JSON credentials file
2. Spawns `Advance Backlink/script.py` as a subprocess
3. `script.py` uses `WebsiteAnalyzer` to detect the platform from the URL
4. Routes to the correct handler (e.g. `QuoraBlogPoster`, `TumblrHandler`)
5. Opens a real Chrome browser, logs in, creates and publishes the post
6. Logs the result to `results.csv`

### Step 5 — Review Results
- **Dashboard** — shows today's success count, total runs, success rate, last run time
- **Analytics** — daily/weekly/monthly/yearly success/failure charts
- **History** — full paginated run log with date range filters and per-platform breakdown

---

## URL Reference

| URL | View | Description |
|---|---|---|
| `/` | `login_view` | Dashboard login |
| `/dashboard/` | `dashboard_view` | Main control panel |
| `/run/` | `run_automation_view` | Trigger automation run |
| `/blog/update/` | `blog_update_view` | Edit blog.txt content |
| `/analytics/` | `analytics_view` | Success/failure charts |
| `/history/` | `history_view` | Paginated run history |
| `/images/` | `image_manager_view` | Upload/delete/rename images |
| `/credential/add/` | `add_credential_view` | Add single credential |
| `/credential/edit/` | `edit_credential_view` | Edit existing credential |
| `/credential/delete/` | `delete_credential_view` | Delete credential |
| `/upload-excel/` | `upload_excel_view` | Bulk upload from Excel |
| `/upload-csv/` | `upload_csv_view` | Bulk upload from CSV |

---

## Credential Excel Format

The bulk import Excel/CSV must have these columns:

| Column | Required | Description |
|---|---|---|
| `url` | ✅ | Platform login URL |
| `email_selector` | Optional | Login email |
| `password_selector` | ✅ | Login password |
| `username_selector` | Optional | Username (if different from email) |

Alternative column names are also accepted: `email`, `password`, `username`, `website`, `link`.

---

## One-Time Tumblr Setup

Tumblr requires a persistent browser session. Run this once to log in manually and save the session:

```bash
cd project_backlink
python setup_login.py
```

A Chrome window opens. Log in to Tumblr manually. The session is saved to `automation_profile/` and reused by future automation runs.

---

## Security Notes

- **Never commit `.env`** — contains your Django secret key
- **`credentials.xlsx`** is excluded from git — it contains platform passwords
- **`ui_runtime_creds.json`** is excluded from git — runtime credential file written by the automation
- **`*.pkl` files** (e.g. `quora_cookies.pkl`) are excluded — they contain active session cookies
- **`db.sqlite3`** is excluded — contains your credential data
- The dashboard login is hardcoded (`backlink` / `backlink123`) — change it in `views.py` before deploying
- Credentials stored in the Django DB are in **plaintext** — do not expose the DB or the dashboard to the public internet

---

## Platform-Specific Notes

- **Medium** — uses IMAP email access to retrieve OTP login codes. Ensure the email account allows IMAP and has less-secure-app access or an app password configured.
- **Tumblr** — requires the one-time manual login via `setup_login.py` before automation works.
- **Image posting** — uses Windows clipboard (`pywin32`) to paste images into rich text editors. On Linux/Mac, image posting may not work without modification.
- **Anti-detection** — all handlers use `undetected-chromedriver` to avoid bot detection. Keep Chrome updated to match the driver version.

---

## License

This project is proprietary. All rights reserved.
