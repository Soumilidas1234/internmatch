# InternMatch AI

InternMatch AI is a local Flask web application that helps students **prepare** for internship and job interviews. It analyzes a resume, estimates role readiness, finds skill gaps, runs an AI examiner, reviews mistakes, and tracks progress. Matching uses TF-IDF, cosine similarity, skill overlap, and a local scikit-learn neural score. There are no cloud AI APIs.

This is a final-year academic project. **Readiness and exam scores are practice estimates. They do not guarantee a job or internship.**

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

Use that login to try resume analysis, role readiness, skill gap, the 14-day plan, the AI examiner, mock interview, and progress.

There is **no public hosted URL**. Demonstrate the project on the student’s computer.

The admin password is not on the website. Set it as `ADMIN_PASSWORD` in the local `.env` file.

---

## Table of contents

1. [Purpose](#purpose)
2. [Features](#features)
3. [Tech stack](#tech-stack)
4. [Project structure](#project-structure)
5. [System architecture](#system-architecture)
6. [Prerequisites](#prerequisites)
7. [Step-by-step setup](#step-by-step-setup)
8. [How to run the application](#how-to-run-the-application)
9. [Demo and admin accounts](#demo-and-admin-accounts)
10. [Student walkthrough](#student-walkthrough)
11. [Admin walkthrough](#admin-walkthrough)
12. [Matching engine](#matching-engine)
13. [Database models](#database-models)
14. [Limitations](#limitations)
15. [Troubleshooting](#troubleshooting)

---

## Purpose

Students often apply unprepared and repeat the same interview mistakes. InternMatch AI is a practice platform:

1. Analyze the resume
2. Check readiness for a target role
3. See skill gaps
4. Follow a 14-day plan
5. Take an AI exam
6. Review mistakes
7. Retry and track progress

You become ready here. You apply on the company’s own website.

---

## Features

### Student

- Registration, login, and logout with hashed passwords
- Profile with education, CGPA, skills, location, work mode, and **target role**
- Resume upload (`.txt` / `.pdf`) or paste, with local skill extraction
- Interview readiness composite (resume, technical skills, problem solving, communication, exam)
- Role readiness using the same TF-IDF / skill / neural matcher (student ↔ target role)
- Skill-gap analysis with HIGH / MEDIUM / LOW priority
- 14-day preparation plan from gaps and recent exam mistakes
- AI examiner with keyword scoring, topic scores, and mistake review
- Mock (video-style) interview
- Progress history of exam attempts
- Dashboard with profile strength and readiness breakdown

Old internship listing, detail, apply, and application URLs still exist but **redirect** to preparation pages. Internship tables are kept in SQLite and are not dropped.

### Admin

- Separate admin login
- Analytics from real database counts: students, resume analyses, examinations, average exam / readiness when calculable, common skill gaps, common mistakes, most selected target roles
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
| Frontend | Jinja2 HTML templates, CSS, JavaScript |
| Authentication | Flask sessions and Werkzeug password hashing |

This project does **not** use MySQL, MongoDB, Firebase, TensorFlow, or external LLM APIs.

---

## Project structure

```text
internmatch/
├── app.py                      # Student routes (preparation + disabled internship redirects)
├── admin.py                    # Admin blueprint (/admin)
├── config.py                   # Reads SECRET_KEY and passwords from the environment
├── seed.py                     # Demo student, admin, prep columns, leftover sample internships
├── tools.py                    # Resume, exam scoring, mock interview, extra tools
├── import_internships.py       # Kept; leftover sample internship CSV loader
├── .env.example
├── requirements.txt
├── data/
│   └── internships.csv         # Leftover fictional listings (not shown to students)
├── database/
│   └── internmatch.db          # Created automatically on first run
├── ml/
│   ├── matcher.py              # TF-IDF, cosine similarity, weighted score
│   ├── neural_matcher.py       # Local scikit-learn MLP neural scores
│   ├── recommender.py          # Ranked scores; now also score_role_readiness
│   ├── roles.py                # Target role profiles
│   ├── prep.py                 # Gaps, 14-day plan, mistakes, readiness composite
│   └── profile_strength.py     # Profile completeness
├── tests/
├── models/
│   └── __init__.py             # User, Internship, Application, ExamAttempt
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
        ├── tools.py          Resume parsing and exam scoring
        ├── ml/               TF-IDF matching reused as Student ↔ Target Role
        └── Flask-SQLAlchemy
                │
                ▼
        SQLite (internmatch.db)
```

The browser talks only to the local Flask server. Matching, resume analysis, and exam scoring run in Python on the same machine.

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
3. Open **My Profile** and choose a target role.
4. Open **Resume Analysis**. Paste a resume or upload a `.txt` / `.pdf` file (maximum 2 MB).
5. Open **Check My Readiness** (from the dashboard or `/readiness`) to see the Student ↔ Target Role score.
6. Open **Skill Gap** to see HIGH / MEDIUM / LOW missing skills.
7. Open **Preparation Plan** for a 14-day plan.
8. Open **AI Examiner**, finish an exam, and review mistakes.
9. Open **Mock Interview** for a video-style practice round.
10. Open **My Progress** to see score history.

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

Previously the compared document was an internship listing. Now it is a **target role profile** with required skills and a short description. The same functions still run:

1. **Resume parsing** — paste, `.txt`, or `.pdf` (pypdf).
2. **Skill extraction** — resume text matched against a built-in skill list.
3. **Student profile text** — skills, education, domain, work mode, and location.
4. **Role text** — title, description, and required skills.
5. **TF-IDF** — `TfidfVectorizer` with English stop words.
6. **Cosine similarity** — student vector vs role vector, scaled to 0–100.
7. **Final / readiness score**
   - 40% skill overlap
   - 20% TF-IDF cosine similarity
   - 15% local neural network (scikit-learn MLP)
   - 10% domain match
   - 10% location / work mode
   - 5% education
8. **Skill gap** — required role skills the student does not have.
9. **Explanation** — a short sentence built from those signals.
10. **Interview readiness composite** — resume strength, technical skills, problem solving, communication, and last exam.

The neural model is a **multi-layer perceptron** (`sklearn.neural_network`). It is not ChatGPT, BERT, or any cloud API.

---

## Database models

### User

`id`, `name`, `email`, `password` (hashed), `education`, `cgpa`, `location`, `preferred_domain`, `preferred_work_mode`, `skills`, `is_admin`, `target_role`, `resume_analyzed_count`

### Internship (kept, not shown)

`id`, `company`, `title`, `description`, `required_skills`, `location`, `work_mode`, `duration`, `stipend`

### Application (kept, not shown)

`id`, `user_id`, `internship_id`, `status`, `applied_date`

### ExamAttempt

`id`, `user_id`, `target_role`, `overall_score`, `topic_scores`, `mistakes`, `created_at`

---

## Limitations

- Matching uses TF-IDF, cosine similarity, and a local scikit-learn neural network (MLP). It is not ChatGPT or a transformer LLM.
- Resume skills are limited to the built-in skill list.
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

Tests cover skill matching, the neural scorer, the leftover recommender helper, login, readiness, skill gap, the examiner, and the internship redirect.

---

## Troubleshooting

| Problem | What to try |
| --- | --- |
| `python` is not recognized | Install Python 3.12 and tick **Add Python to PATH**. Use `.\venv\Scripts\python.exe` instead. |
| PDF resume is not accepted | Use `.txt` or `.pdf` only, and keep the file under 2 MB. |
| Readiness looks empty | Log in as the demo student, or add skills on the profile / resume analyzer. |
| Port 5000 is already in use | Close the other program using that port, then run `app.py` again. |
| `SECRET_KEY is missing` | Copy `.env.example` to `.env` and set `SECRET_KEY`. |
| Admin login fails | Use the password from your `.env` `ADMIN_PASSWORD`. |

For a viva, start with this file, then walk through `app.py` (routes), `ml/prep.py` (readiness and plans), `ml/matcher.py` (scoring), and `models/__init__.py` (database).
