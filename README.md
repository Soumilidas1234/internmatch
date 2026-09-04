# InternMatch AI

**Make mistakes here. Crack interviews there.**

InternMatch AI is a local Flask web application for **internship and interview preparation**. It is **not** an internship-finding or application website. Students do not browse listings, search internships, or apply through this app.

The platform analyzes a resume, estimates role readiness, finds skill gaps, rebuilds a target-role resume as PDF, runs an AI examiner, reviews mistakes, and tracks progress. Matching uses TF-IDF, cosine similarity, skill overlap, and a local scikit-learn neural score. There are no cloud AI APIs.

This is a final-year academic project. **Readiness, exam, and resume scores are practice estimates. They do not guarantee a job or internship.**

**Live site:** [https://internmatch.pythonanywhere.com](https://internmatch.pythonanywhere.com)

**Source code:** [https://github.com/Soumilidas1234/internmatch](https://github.com/Soumilidas1234/internmatch)

---

## Live demo (for examiners)

```powershell
cd C:\Users\soumi\OneDrive\Desktop\internmatch
.\venv\Scripts\python.exe app.py
```

Then open **http://127.0.0.1:5000/**

| | |
| --- | --- |
| Email | `demo.student@internmatch.local` |
| Password | `Demo@123` |

Use that login to try resume analysis, **Fix Resume** (PDF download), role readiness, skill gap, the 14-day plan, the AI examiner, mock interview, and progress.

The public demo is at **https://internmatch.pythonanywhere.com**. The admin password is not on the website. Set it as `ADMIN_PASSWORD` in `.env` on PythonAnywhere.

---

## Go live for free (PythonAnywhere)

Render often asks you to pay or add a card. Use **PythonAnywhere Beginner** instead: **$0 / month, no credit card**.

Your public URL is:

**https://internmatch.pythonanywhere.com**

### Step 1 — Create a free account

1. Open [https://www.pythonanywhere.com](https://www.pythonanywhere.com)
2. Click **Pricing & signup**
3. Choose **Beginner** / **Create a Beginner account** ($0)
4. Confirm your email

### Step 2 — Download the project on PythonAnywhere

1. Open the **Consoles** tab
2. Click **Bash**
3. Paste:

```bash
git clone https://github.com/Soumilidas1234/internmatch.git
cd internmatch
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

If `python3.10` is not available, try `python3.12` or `python3.11`. On Python 3.10, pip will install scikit-learn 1.7.x (1.9 is not published for that version). Matching still works.

In `.env` set:

- `SECRET_KEY` = a long random string
- `ADMIN_PASSWORD` = a private password
- `FLASK_DEBUG` = `0`
- `FLASK_ENV` = `production`
- `DEMO_STUDENT_PASSWORD` = `Demo@123`

Save: **Ctrl+O**, Enter, then **Ctrl+X**.

### Step 3 — Create the web app

1. Open the **Web** tab
2. Click **Add a new web app**
3. Click **Next**
4. Choose **Manual configuration** (not Django)
5. Pick the same Python version you used for the venv (3.10 or newer)
6. Click **Next**

### Step 4 — Point it at InternMatch

On the Web tab:

1. **Virtualenv** — enter:

```text
/home/InternMatch/internmatch/venv
```

2. **Source code** and **Working directory:** `/home/InternMatch/internmatch`

3. **WSGI configuration file** — paste `pythonanywhere_wsgi.py` from this repo.

4. Click **Reload** at the top of the Web tab.

5. Open **https://internmatch.pythonanywhere.com**

### Step 5 — Logins

- Student: `demo.student@internmatch.local` / `Demo@123`
- Admin: https://internmatch.pythonanywhere.com/admin/login with your `ADMIN_PASSWORD`

### Free-plan notes

- One website, HTTPS included, no card needed.
- Log in about once a month and click **Run until 3 months from today** / extend so the site does not expire.
- SQLite is a file on PythonAnywhere, so data stays unless you delete it.
- If `pip install` fails with “disk quota”, the free 512 MB limit is full. Delete unused files and try again.

Do not put `.env` or your admin password on GitHub.

---

## Table of contents

1. [Purpose](#purpose)
2. [Student navigation](#student-navigation)
3. [Features](#features)
4. [Tech stack](#tech-stack)
5. [Project structure](#project-structure)
6. [System architecture](#system-architecture)
7. [Prerequisites](#prerequisites)
8. [Step-by-step setup](#step-by-step-setup)
9. [How to run the application](#how-to-run-the-application)
10. [Demo and admin accounts](#demo-and-admin-accounts)
11. [Student walkthrough](#student-walkthrough)
12. [Admin walkthrough](#admin-walkthrough)
13. [Matching engine](#matching-engine)
14. [Database models](#database-models)
15. [Limitations](#limitations)
16. [Automated tests](#automated-tests)
17. [Troubleshooting](#troubleshooting)

---

## Purpose

You don't find your internship here. You become ready for it here.

Students often apply unprepared and repeat the same interview mistakes. InternMatch AI is a practice platform:

1. Register and create a profile
2. Upload a resume
3. AI resume analysis
4. Choose a **target role** (not an internship listing)
5. Role readiness / Perfect Match (student ↔ target role)
6. Skill-gap analysis
7. Personalized 14-day preparation plan
8. AI examiner
9. Mistake analysis and retry
10. **Fix Resume** — what to add, what to drop, keywords, score, rebuilt PDF
11. Interview readiness score
12. Apply on the **company’s own website** (not here)

---

## Student navigation

Dashboard · My Profile · Resume Analysis · **Fix Resume** · Skill Gap · Preparation Plan · AI Examiner · Mock Interview · My Progress · Logout

There is no Internships, Find Internship, or Applications menu.

---

## Features

### Student

- Registration, login, and logout with hashed passwords
- Profile with education, CGPA, skills, location, work mode, and **target role**
- Resume upload (`.txt` / `.pdf`) or paste, with local skill extraction
- Resume analysis: extracted skills, education / experience / projects flags, strengths, weak areas, completeness
- **Fix Your Resume:** missing vs off-target content, recommended keywords, score check, HTML preview, downloadable PDF rebuilt for the target role (no invented jobs or companies)
- Interview readiness composite (resume, technical skills, problem solving, communication, exam)
- Role readiness using the same TF-IDF / skill / neural matcher (**student ↔ target role**)
- Skill-gap analysis: what you know, what you are missing, HIGH / MEDIUM / LOW priority
- 14-day preparation plan from gaps and recent exam mistakes
- AI examiner with keyword scoring, topic scores, mistake review, and retake
- Mock (video-style) interview
- Progress history of exam attempts
- Dashboard with profile strength and readiness breakdown

Old internship listing, detail, apply, and application **URLs still exist but redirect** to preparation pages. Internship tables are kept in SQLite and are not dropped.

### Admin

- Separate admin login
- Analytics from real database counts: students, resume analyses, examinations, average exam score when calculable, common skill gaps, common mistakes, most selected target roles
- Student / user management
- Old internship CRUD URLs redirect to analytics (tables are not deleted)

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.12 |
| Web framework | Flask |
| ORM | Flask-SQLAlchemy |
| Database | SQLite (`database/internmatch.db`) |
| Matching | scikit-learn (`TfidfVectorizer`, cosine similarity, MLP) |
| PDF parsing | pypdf |
| Resume PDF export | reportlab |
| Frontend | Jinja2 HTML templates, CSS, JavaScript |
| Authentication | Flask sessions and Werkzeug password hashing |
| Tests | pytest |
| Live hosting | PythonAnywhere (free Beginner plan) |

This project does **not** use MySQL, MongoDB, Firebase, TensorFlow, or external LLM APIs.

---

## Project structure

```text
internmatch/
├── app.py                      # Student routes (prep + Fix Resume + internship URL redirects)
├── admin.py                    # Admin blueprint (/admin) — analytics and users
├── config.py                   # SECRET_KEY and passwords from the environment
├── seed.py                     # Demo student, admin, prep columns
├── tools.py                    # Resume parse/score, exam scoring, extra tools
├── import_internships.py       # Leftover CSV loader (listings are not shown to students)
├── .env.example
├── requirements.txt
├── Procfile                  # Render start command
├── render.yaml               # Optional Render blueprint
├── data/
│   └── internships.csv         # Leftover fictional listings (not shown in the UI)
├── database/
│   └── internmatch.db          # Created automatically on first run (gitignored)
├── ml/
│   ├── matcher.py              # TF-IDF, cosine similarity, weighted score
│   ├── neural_matcher.py       # Local scikit-learn MLP neural scores
│   ├── recommender.py          # score_role_readiness (student ↔ target role)
│   ├── roles.py                # Target role skill catalogs
│   ├── prep.py                 # Gaps, 14-day plan, mistakes, readiness composite
│   ├── resume_fixer.py         # Add/remove/keywords + rebuilt resume PDF
│   └── profile_strength.py     # Profile completeness
├── tests/
├── models/
│   └── __init__.py             # User, ExamAttempt; Internship/Application kept unused in UI
├── static/
└── templates/
```

---

## System architecture

```text
Browser (HTML / CSS / JS)
        │
        ▼
Flask (app.py + admin.py)
        │
        ├── tools.py            Resume parsing and exam scoring
        ├── ml/resume_fixer.py  Target-role resume rebuild + PDF
        ├── ml/                 TF-IDF matching reused as Student ↔ Target Role
        └── Flask-SQLAlchemy
                │
                ▼
        SQLite (internmatch.db)
```

The browser talks only to the local Flask server. Matching, resume analysis, exam scoring, and PDF rebuild run in Python on the same machine.

---

## Prerequisites

1. **Python 3.12** (or a close 3.x version)
2. **pip**
3. A web browser (Chrome, Edge, or Firefox)

```powershell
python --version
```

---

## Step-by-step setup

The commands below are for **Windows PowerShell**. On macOS or Linux, use `python3` and `source venv/bin/activate`.

### Step 1 — Get the project

```powershell
cd C:\Users\soumi\OneDrive\Desktop\internmatch
```

Or clone from GitHub:

```powershell
git clone https://github.com/Soumilidas1234/internmatch.git
cd internmatch
```

### Step 2 — Create a virtual environment

```powershell
python -m venv venv
```

### Step 3 — Activate the virtual environment

```powershell
venv\Scripts\activate
```

### Step 4 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5 — Create a local `.env` file

```powershell
copy .env.example .env
```

Set `SECRET_KEY`, `ADMIN_PASSWORD`, and leave `DEMO_STUDENT_PASSWORD=Demo@123`.

Do not commit `.env`.

---

## How to run the application

```powershell
cd C:\Users\soumi\OneDrive\Desktop\internmatch
.\venv\Scripts\python.exe app.py
```

Then open **http://127.0.0.1:5000/**

Stop the server with `Ctrl + C`. The database file is created at `database/internmatch.db` on first run.

If the homepage shows a 500 error after a code update, stop the old Flask process and run `app.py` again. Debug is off by default, so template changes need a restart.

---

## Demo and admin accounts

### Examiner student

| Field | Value |
| --- | --- |
| Email | `demo.student@internmatch.local` |
| Password | `Demo@123` |

This account is created on startup with a sample BCA profile, skills, and target role **Web Developer**.

### Admin

Admin login is at `/admin/login`. The email defaults to `admin@internmatch.local`. The password comes from `ADMIN_PASSWORD` in `.env`.

---

## Student walkthrough

1. Open http://127.0.0.1:5000/
2. Register or log in with the demo account.
3. Open **My Profile** and choose a target role (for example Data Analyst or Web Developer).
4. Open **Resume Analysis**. Paste a resume or upload a `.txt` / `.pdf` file (maximum 2 MB).
5. Open **Fix Resume** (`/resume-fixer`). Review what to add, what to de-emphasize, keywords, and the score, then **Download PDF Resume**.
6. Open **Check My Readiness** (`/readiness`) for the Student ↔ Target Role score.
7. Open **Skill Gap** to see HIGH / MEDIUM / LOW missing skills.
8. Open **Preparation Plan** for a 14-day plan.
9. Open **AI Examiner**, finish an exam, and review mistakes. Retake to see improvement.
10. Open **Mock Interview** for a video-style practice round.
11. Open **My Progress** to see score history.

Internship browse / apply URLs redirect. Apply on official company sites after you practice.

---

## Admin walkthrough

1. Open http://127.0.0.1:5000/admin/login
2. Sign in with the admin email and password.
3. **Analytics** shows real counts from students, resume analyses, and exam attempts.
4. **User Management** lists registered students (passwords are never shown).

Students who open `/admin` routes receive a 403 error.

---

## Matching engine

All matching is local. No OpenAI or other cloud model is called.

The compared document used to be an internship listing. It is now a **target role profile** with required skills and a short description. The same functions still run:

1. **Resume parsing** — paste, `.txt`, or `.pdf` (pypdf).
2. **Skill extraction** — resume text matched against a built-in skill list.
3. **Student profile text** — skills, education, domain, work mode, and location.
4. **Role text** — title, description, and required skills (`ml/roles.py`).
5. **TF-IDF** — `TfidfVectorizer` with English stop words.
6. **Cosine similarity** — student vector vs role vector, scaled to 0–100.
7. **Final / role-readiness score**
   - 40% skill overlap
   - 20% TF-IDF cosine similarity
   - 15% local neural network (scikit-learn MLP)
   - 10% domain match
   - 10% location / work mode
   - 5% education
8. **Skill gap** — required role skills the student does not have.
9. **Explanation** — a short sentence built from those signals.
10. **Interview readiness composite** — resume strength, technical skills, problem solving, communication, and last exam.
11. **Resume fixer** — rule-based rewrite + keywords from the role catalog; PDF via reportlab. Does not invent work history.

The neural model is a **multi-layer perceptron** (`sklearn.neural_network`). It is not ChatGPT, BERT, or any cloud API.

Function names such as `score_internship()` remain in `ml/matcher.py` so older tests still pass. The student UI calls `score_role_readiness()` instead of listing internships.

---

## Database models

### User

`id`, `name`, `email`, `password` (hashed), `education`, `cgpa`, `location`, `preferred_domain`, `preferred_work_mode`, `skills`, `is_admin`, `target_role`, `resume_analyzed_count`, `last_resume_text`

### ExamAttempt

`id`, `user_id`, `target_role`, `overall_score`, `topic_scores`, `mistakes`, `created_at`

### Internship and Application (kept, not shown)

These tables remain so existing code and SQLite files are not destroyed. The student UI does not list internships or process applications.

- Internship: `id`, `company`, `title`, `description`, `required_skills`, `location`, `work_mode`, `duration`, `stipend`
- Application: `id`, `user_id`, `internship_id`, `status`, `applied_date`

---

## Limitations

- Matching uses TF-IDF, cosine similarity, and a local scikit-learn neural network (MLP). It is not ChatGPT or a transformer LLM.
- Resume skills are limited to the built-in skill list.
- The rebuilt PDF only reorganizes facts from the uploaded resume and profile. Missing items appear as suggested additions, not fake jobs.
- Readiness and exam scores are estimates for practice. They do not guarantee a job.
- The mock interview uses the browser camera and keyword scoring; it is not a live AI video call.
- The leftover scam detector uses keyword flags, not a live company verification service.
- Flask debug mode is off by default (`FLASK_DEBUG=0`).
- SQLite is used for this academic demo. Internship and application tables remain in the database but student UI routes redirect away from them.

---

## Automated tests

```powershell
.\venv\Scripts\python.exe -m pytest
```

Tests cover skill matching, the neural scorer, role readiness, login, skill gap, the examiner, internship URL redirects, and Fix Resume / PDF.

---

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `python` is not recognized | Install Python 3.12 and tick **Add Python to PATH**. Use `.\venv\Scripts\python.exe` instead. |
| PDF resume is not accepted | Use `.txt` or `.pdf` only, and keep the file under 2 MB. |
| Fix Resume says there is no resume | Analyze or paste a resume first on **Resume Analysis**. |
| Readiness looks empty | Log in as the demo student, or add skills on the profile / resume analyzer. |
| Port 5000 is already in use | Close the other program using that port, then run `app.py` again. |
| Homepage 500 after an update | Restart `app.py` so Flask loads the new routes. |
| `SECRET_KEY is missing` | Copy `.env.example` to `.env` and set `SECRET_KEY`. |
| Admin login fails | Use the password from your `.env` `ADMIN_PASSWORD`. |

For a viva, start with this file, then walk through `app.py` (routes), `ml/prep.py` (readiness and plans), `ml/resume_fixer.py` (PDF rebuild), `ml/matcher.py` (scoring), and `models/__init__.py` (database).
