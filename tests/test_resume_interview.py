SAMPLE_RESUME = """
Demo Student
Bengaluru
demo.student@internmatch.local

Education
BCA, Sample College

Skills
Python, HTML, CSS, Flask, SQL, Git

Projects
Weather Monitoring System using ESP32 and Python
Developed a Flask web application with SQLite authentication
Built a machine learning model using Random Forest
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


def _save_resume(client, text=SAMPLE_RESUME):
    return client.post(
        "/resume-analyzer",
        data={"resume_text": text},
        follow_redirects=True,
    )


def _clear_demo_resume():
    from app import app
    from models import User, db

    with app.app_context():
        user = User.query.filter_by(email="demo.student@internmatch.local").first()
        if user is not None:
            user.last_resume_text = ""
            db.session.commit()


def test_questions_are_grounded_in_resume():
    from ml.resume_interview import extract_resume_claims, generate_questions

    claims = extract_resume_claims(None, SAMPLE_RESUME)
    questions = generate_questions(claims, "Web Developer", "mixed", 10)
    blob = " ".join(item["question"] for item in questions).lower()
    assert questions
    assert any("flask" in item["question"].lower() or "weather" in item["question"].lower() for item in questions)
    assert "random forest" in blob
    assert "django" not in blob or "flask" in blob
    assert "tableau" not in blob
    assert "kubernetes" not in blob
    for item in questions:
        assert item.get("source")


def test_questions_omit_missing_claims():
    from ml.resume_interview import extract_resume_claims, generate_questions

    slim = """
    Skills
    HTML, CSS
    Projects
    Personal portfolio website with HTML and CSS
    """
    claims = extract_resume_claims(None, slim)
    questions = generate_questions(claims, "Frontend Developer", "beginner", 5)
    blob = " ".join(item["question"] for item in questions).lower()
    assert "random forest" not in blob
    assert "esp32" not in blob
    assert "flask" not in blob


def test_followup_uses_student_answer():
    from ml.resume_interview import build_followup

    followup = build_followup(
        {"question": "Why Flask?", "source": "Flask web application", "keywords": ["simple"], "is_followup": False},
        "Because Flask is simple.",
    )
    assert followup
    assert "simple" in followup["question"].lower()
    assert "flask web application" in followup["question"].lower()


def test_resume_interview_requires_login(client):
    response = client.get("/resume-interview")
    assert response.status_code in (301, 302)
    assert "login" in response.headers.get("Location", "").lower()


def test_resume_interview_needs_resume(client):
    _login_demo(client)
    from app import app
    from models import User, db

    with app.app_context():
        user = User.query.filter_by(email="demo.student@internmatch.local").first()
        user.last_resume_text = ""
        db.session.commit()
    response = client.get("/resume-interview")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Upload your resume first" in html
    assert "Resume Analysis" in html
    assert "Apply Now" not in html


def test_resume_interview_shows_hotspots_and_starts(client):
    _login_demo(client)
    try:
        analyze = _save_resume(client)
        assert analyze.status_code == 200
        page = client.get("/resume-interview")
        html = page.get_data(as_text=True)
        assert page.status_code == 200
        assert "Your Resume Hotspots" in html
        assert "Flask" in html or "Python" in html or "Weather" in html
        start = client.post(
            "/resume-interview",
            data={"difficulty": "beginner", "count": "5"},
            follow_redirects=True,
        )
        assert start.status_code == 200
        play = start.get_data(as_text=True)
        assert "QUESTION 1 /" in play
        assert "Submit Answer" in play
        assert "Skip" in play
        lowered = play.lower()
        assert "flask" in lowered or "python" in lowered or "weather" in lowered or "sql" in lowered
    finally:
        _clear_demo_resume()


def test_resume_interview_feedback_and_followup(client):
    _login_demo(client)
    try:
        _save_resume(client)
        client.post("/resume-interview", data={"difficulty": "mixed", "count": "5"})
        response = client.post(
            "/resume-interview/play",
            data={"action": "submit", "answer": "Because it is simple."},
            follow_redirects=True,
        )
        html = response.get_data(as_text=True)
        assert "ANSWER FEEDBACK" in html
        assert "What You Did Well" in html
        assert "Next Question" in html
        assert "perfectly judge" in html.lower() or "practice hint" in html.lower()
        assert "Follow-up queued next" in html
    finally:
        _clear_demo_resume()


def test_resume_interview_hides_other_users(client):
    _login_demo(client)
    response = client.get("/resume-interview/99999", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found" in response.data.lower() or b"Resume Interview" in response.data


def test_existing_examiner_still_separate(client):
    _login_demo(client)
    response = client.get("/examiner")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Enter the arena" in html or "AI Examiner" in html or "exam" in html.lower()
    assert "Resume Hotspots" not in html
