# InternMatch AI

InternMatch AI is a Flask web application that helps students discover internships that fit their skills, education, location, and work-mode preference. Matching uses TF-IDF, cosine similarity, and a weighted scoring model. There are no cloud AI APIs.

This is a final-year academic project. **All internship listings are fictional sample data for demonstration. They are not real job openings.**

**Source code:** [https://github.com/Soumilidas1234/internmatch](https://github.com/Soumilidas1234/internmatch)

---

## Live demo (for examiners)

**Student login (also shown on the website)**

| | |
| --- | --- |
| Email | `demo.student@internmatch.local` |
| Password | `Demo@123` |

Internship listings are **fictional sample data**, not real jobs.

### Hosted URL

After you deploy (one-time, free), the app URL is usually:

`https://internmatch.onrender.com`

Deploy from GitHub with this button:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Soumilidas1234/internmatch)

Or: [Open Render deploy](https://render.com/deploy?repo=https://github.com/Soumilidas1234/internmatch)

Sign in with GitHub, click **Apply**, wait until the service is Live, then copy the `.onrender.com` URL. Send that URL to the examiner with the student login above.

The admin password is **not** on the website. Set it as `ADMIN_PASSWORD` in the host environment (Render generates one if you use `render.yaml`).

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Project structure](#project-structure)
4. [System architecture](#system-architecture)
5. [Prerequisites](#prerequisites)
6. [Step-by-step setup](#step-by-step-setup)
7. [How to run the application](#how-to-run-the-application)
8. [Demo and admin accounts](#demo-and-admin-accounts)
9. [Student walkthrough](#student-walkthrough)
10. [Admin walkthrough](#admin-walkthrough)
11. [Matching engine](#matching-engine)
12. [Database models](#database-models)
13. [Limitations](#limitations)
14. [Troubleshooting](#troubleshooting)

---

## Features

### Student

- Registration, login, and logout with hashed passwords
- Profile with education, CGPA, skills, location, domain, and work mode
- Internship browse, search, and filters
- Resume upload (`.txt` / `.pdf`) or paste, with local skill extraction
- Ranked internship recommendations with match score and explanation
- Skill-gap analysis against top matching roles
- Apply to internships and track application status
- Dashboard with profile-strength meter
- Extra local tools: career roadmap, scam detector, interview arena, video interview, and project ideas

### Admin

- Separate admin login and dashboard
- View registered students (passwords are never shown)
- Add, edit, and delete internships
- View applications and update status

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| Web framework | Flask |
| ORM | Flask-SQLAlchemy |
| Database | SQLite (`database/internmatch.db`) |
| Matching | scikit-learn (`TfidfVectorizer`, cosine similarity) |
| PDF parsing | pypdf |
| Frontend | Jinja2 HTML templates, CSS, JavaScript |
| Authentication | Flask sessions and Werkzeug password hashing |

This project does **not** use MySQL, MongoDB, Firebase, TensorFlow, or external LLM APIs.

---

## Project structure

```text
internmatch/
├── app.py                      # Main Flask application (student routes)
├── admin.py                    # Admin blueprint (/admin)
├── config.py                   # Reads SECRET_KEY and passwords from the environment
├── seed.py                     # Demo student, admin, and sample internship setup
├── tools.py                    # Resume, roadmap, interview, and other tools
├── import_internships.py       # Load sample internships from CSV
├── .env.example                # Environment variable template
├── Procfile                    # Production start command
├── render.yaml                 # Render.com deploy blueprint
├── requirements.txt            # Python dependencies
├── data/
│   └── internships.csv         # Fictional internship dataset
├── database/
│   └── internmatch.db          # Created automatically on first run
├── ml/
│   ├── matcher.py              # TF-IDF, cosine similarity, weighted score
│   ├── recommender.py          # Ranked recommendations
│   └── profile_strength.py     # Profile strength and skill-gap helpers
├── models/
│   └── __init__.py             # User, Internship, Application models
├── static/
│   ├── css/style.css
│   ├── js/video_interview.js
│   └── images/
└── templates/                  # Student, admin, and error pages
```

**Frontend:** `templates/`, `static/css/`, `static/js/`, `static/images/`  
**Backend:** `app.py`, `admin.py`, `tools.py`, `models/`, `ml/`, `import_internships.py`

---

## System architecture

```text
Browser (HTML / CSS / JS)
        │
        ▼
Flask (app.py + admin.py)
        │
        ├── tools.py          Resume parsing and extra tools
        ├── ml/               TF-IDF matching and recommendations
        └── Flask-SQLAlchemy
                │
                ▼
        SQLite (internmatch.db)
                ▲
                │
        data/internships.csv  (imported by import_internships.py)
```

The browser talks only to the local Flask server. Matching and resume analysis run in Python on the same machine.

---

## Prerequisites

Install these before setup:

1. **Python 3.12** (or a close 3.x version)
2. **pip** (included with Python)
3. A web browser (Chrome, Edge, or Firefox)

Confirm Python from a terminal:

```powershell
python --version
```

---

## Step-by-step setup

The commands below are for **Windows PowerShell**. On macOS or Linux, use `python3` and `source venv/bin/activate` instead of `venv\Scripts\activate`.

### Step 1 — Get the project

**Option A — clone from GitHub**

```powershell
git clone https://github.com/Soumilidas1234/internmatch.git
cd internmatch
```

**Option B — use the existing folder**

```powershell
cd C:\Users\soumi\OneDrive\Desktop\internmatch
```

### Step 2 — Create a virtual environment

```powershell
python -m venv venv
```

### Step 3 — Activate the virtual environment

```powershell
venv\Scripts\activate
```

The prompt should show `(venv)` when activation succeeds.

### Step 4 — Install dependencies

```powershell
pip install -r requirements.txt
```

This installs Flask, Flask-SQLAlchemy, scikit-learn, pypdf, python-dotenv, and gunicorn.

### Step 5 — Create a local `.env` file

```powershell
copy .env.example .env
```

Open `.env` and set:

- `SECRET_KEY` to a long random string
- `ADMIN_PASSWORD` to a private admin password
- Leave `DEMO_STUDENT_PASSWORD=Demo@123` so the examiner account works

Do not commit `.env`. It is ignored by git.

Sample internships load automatically on first start from `data/internships.csv`. To reload them:

```powershell
python import_internships.py --replace
```

---

## How to run the application

With the virtual environment still active:

```powershell
python app.py
```

Then open:

**http://127.0.0.1:5000/**

Stop the server with `Ctrl + C` in the terminal.

The database file is created automatically at `database/internmatch.db` on first run.

---

## Demo and admin accounts

### Examiner student (shown on the website)

| Field | Value |
| --- | --- |
| Email | `demo.student@internmatch.local` |
| Password | `Demo@123` |

This account is created on startup. It already has a sample BCA profile and skills so recommendations work immediately.

### Admin

Admin login is at `/admin/login`. The email defaults to `admin@internmatch.local`. The password comes from `ADMIN_PASSWORD` in `.env` (or the host environment). It is not written in the Python source.

---

## Student walkthrough

1. Open http://127.0.0.1:5000/
2. Click **Register** and create an account.
3. Log in. You will land on the dashboard.
4. Open **Profile** and fill education, CGPA, skills, location, domain, and work mode.
5. Open **Resume Analyzer**. Paste a resume or upload a `.txt` / `.pdf` file (maximum 2 MB). Extracted skills are merged into the profile.
6. Open **Recommendations** to see ranked internships, match scores, matched/missing skills, and a short explanation.
7. Open **Skill Gap** to see skills that top matches still require.
8. Open an internship and click **Apply Now**.
9. Open **My Applications** to track status: Applied → Shortlisted → Interview → Selected (or Rejected).

---

## Admin walkthrough

1. Open http://127.0.0.1:5000/admin/login
2. Sign in with the admin email and password.
3. Use the dashboard for counts of students, internships, and applications.
4. **Students** — view registered student profiles.
5. **Internships** — add, edit, or delete listings.
6. **Applications** — update application status.

Students who open `/admin` routes receive a 403 error.

---

## Matching engine

All matching is local. No OpenAI or other cloud model is called.

1. **Resume parsing** — text is taken from paste, `.txt`, or `.pdf` (pypdf).
2. **Skill extraction** — skills are found by matching resume text against a built-in skill list.
3. **Student profile text** — skills, education, domain, work mode, and location.
4. **Internship text** — title, description, required skills, location, and work mode.
5. **TF-IDF** — `TfidfVectorizer` with English stop words, fitted on internship texts.
6. **Cosine similarity** — student vector vs each internship vector, scaled to 0–100.
7. **Final score**
   - 50% skill overlap
   - 25% TF-IDF cosine similarity
   - 10% domain match
   - 10% location / work mode
   - 5% education
8. **Labels** — Excellent (≥90), Strong (≥75), Good (≥60), Partial (≥40), Low.
9. **Skill gap** — required skills that the student does not have.
10. **Explanation** — a short sentence built from those signals (not a neural language model).

---

## Database models

### User

`id`, `name`, `email`, `password` (hashed), `education`, `cgpa`, `location`, `preferred_domain`, `preferred_work_mode`, `skills`, `is_admin`

### Internship

`id`, `company`, `title`, `description`, `required_skills`, `location`, `work_mode`, `duration`, `stipend`

### Application

`id`, `user_id`, `internship_id`, `status`, `applied_date`  
Unique pair: one application per student per internship.

---

## Limitations

- Matching is classical NLP plus rules, not a trained deep-learning model.
- Resume skills are limited to the built-in skill list.
- Internship data is fictional and meant for demonstration.
- The video interview uses the browser camera and keyword scoring; it is not a live AI video call.
- The scam detector uses keyword flags, not a live company verification service.
- Flask debug mode is off by default (`FLASK_DEBUG=0`).
- SQLite is used for this academic demo. Hosted free services may reset the database after idle restarts; sample internships and the demo student are recreated automatically.

---

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `python` is not recognized | Install Python 3.12 and tick **Add Python to PATH**. |
| Internships page is empty | Restart the app. Sample internships are imported automatically. |
| PDF resume is not accepted | Use `.txt` or `.pdf` only, and keep the file under 2 MB. |
| Recommendations are empty | Log in as the demo student, or add skills on the profile. |
| Port 5000 is already in use | Close the other program using that port, then run `python app.py` again. |
| `SECRET_KEY is missing` | Copy `.env.example` to `.env` and set `SECRET_KEY`. |
| Admin login fails | Use the password from your `.env` `ADMIN_PASSWORD`. It is not stored in the code. |

For project documentation or a viva, start with this file, then walk through `app.py` (routes), `ml/matcher.py` (scoring), and `models/__init__.py` (database).
