SAMPLE_JD = """
Job Title: Data Analyst Intern
We are hiring a Data Analyst intern to analyze datasets, write SQL queries, and create dashboards.
Required skills:
- SQL
- Excel
- Python
- Power BI
Responsibilities:
- Clean and analyze weekly sales data
- Build Power BI dashboards for stakeholders
Preferred:
- Tableau
"""


def _login_demo(client):
    return client.post(
        "/login",
        data={
            "email": "demo.student@internmatch.local",
            "password": "Demo@123",
        },
        follow_redirects=True,
    )


def test_role_questions_use_target_skills_only():
    from ml.role_questions import generate_role_questions

    result = generate_role_questions(
        "Data Analyst",
        student_skills="Python, Excel",
        difficulty="mixed",
        count=20,
    )
    blob = " ".join(item["question"] for item in result["questions"]).lower()
    topics = {item["topic"].lower() for item in result["questions"]}
    assert result["questions"]
    assert "sql" in blob or "sql" in topics
    assert "kubernetes" not in blob
    assert "django" not in blob
    assert any(item.get("why") for item in result["questions"])
    assert any(item["priority"] == "HIGH" for item in result["questions"])


def test_role_questions_follow_jd_skills():
    from ml.role_questions import generate_role_questions

    student = {
        "skills": "Python, HTML",
        "education": "BCA",
        "preferred_domain": "Data Analyst",
        "preferred_work_mode": "Hybrid",
        "location": "Bengaluru",
        "target_role": "Data Analyst",
    }
    result = generate_role_questions(
        "Data Analyst",
        student_skills=student["skills"],
        jd_text=SAMPLE_JD,
        student=student,
        count=20,
    )
    blob = " ".join(item["question"] for item in result["questions"]).lower()
    assert "sql" in blob
    assert "flask" not in blob
    assert result["has_jd"]
    assert result["coverage"]


def test_interview_questions_requires_login(client):
    response = client.get("/interview-questions")
    assert response.status_code in (301, 302)
    assert "login" in response.headers.get("Location", "").lower()


def test_interview_questions_page_loads(client):
    _login_demo(client)
    response = client.get("/interview-questions")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "AI Interview Question Generator" in html
    assert "Paste Job Description" in html
    assert "Apply Now" not in html
    assert "Resume Hotspots" not in html


def test_interview_questions_generate_without_jd(client):
    _login_demo(client)
    response = client.post(
        "/interview-questions",
        data={
            "target_role": "Data Analyst",
            "difficulty": "beginner",
            "count": "10",
            "without_jd": "1",
            "action": "generate",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "HIGH PRIORITY" in html
    assert "Why this question?" in html
    assert "SQL" in html or "Python" in html or "Excel" in html


def test_interview_questions_practice_and_save(client):
    _login_demo(client)
    start = client.post(
        "/interview-questions",
        data={
            "target_role": "Web Developer",
            "without_jd": "1",
            "action": "quick",
            "difficulty": "mixed",
        },
        follow_redirects=True,
    )
    assert start.status_code == 200
    html = start.get_data(as_text=True)
    assert "Practice Question" in html
    from app import app
    from models import RoleQuestionSet, User

    with app.app_context():
        user = User.query.filter_by(email="demo.student@internmatch.local").first()
        record = (
            RoleQuestionSet.query.filter_by(user_id=user.id)
            .order_by(RoleQuestionSet.created_at.desc())
            .first()
        )
        set_id = record.id
    save = client.post(
        f"/interview-questions/{set_id}/save",
        data={"index": "0"},
        follow_redirects=True,
    )
    assert save.status_code == 200
    assert b"saved" in save.data.lower()
    practice = client.post(
        f"/interview-questions/{set_id}/practice",
        data={"action": "submit", "answer": "HTML is structure, CSS is style, and JavaScript adds behavior."},
        follow_redirects=True,
    )
    assert practice.status_code == 200
    text = practice.get_data(as_text=True)
    assert "AI-estimated answer evaluation" in text
    assert "/ 100" in text


def test_interview_questions_hides_other_users(client):
    _login_demo(client)
    response = client.get("/interview-questions/99999", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found" in response.data.lower() or b"AI Interview Question Generator" in response.data


def test_existing_features_not_replaced(client):
    _login_demo(client)
    examiner = client.get("/examiner").get_data(as_text=True)
    assert "Enter the arena" in examiner or "AI Examiner" in examiner or "exam" in examiner.lower()
    resume = client.get("/resume-interview").get_data(as_text=True)
    assert "Resume" in resume
    jd = client.get("/job-analyzer").get_data(as_text=True)
    assert "Job Description" in jd
