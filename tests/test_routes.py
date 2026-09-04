STUDENT_PAGES = (
    "/",
    "/dashboard",
    "/readiness",
    "/skill-gap",
    "/preparation-plan",
    "/examiner",
    "/progress",
    "/resume-analyzer",
    "/resume-fixer",
    "/profile",
    "/job-analyzer",
    "/ats-simulator",
    "/resume-interview",
    "/interview-questions",
)


def _login_demo(client):
    return client.post(
        "/login",
        data={
            "email": "demo.student@internmatch.local",
            "password": "Demo@123",
        },
        follow_redirects=True,
    )


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "InternMatch" in html
    assert "sample" in html.lower() or "demo" in html.lower()
    assert "Find Internship" not in html
    assert "Apply Now" not in html


def test_internships_page_loads(client):
    response = client.get("/internships")
    assert response.status_code in (301, 302)
    location = response.headers.get("Location", "")
    assert location.endswith("/") or "dashboard" in location


def test_internships_redirect_when_logged_in(client):
    _login_demo(client)
    response = client.get("/internships")
    assert response.status_code in (301, 302)
    assert "dashboard" in response.headers.get("Location", "")


def test_login_page_shows_demo_account(client):
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "demo.student@internmatch.local" in html


def test_demo_student_can_log_in(client):
    response = _login_demo(client)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Dashboard" in html or "dashboard" in html.lower()


def test_recommendations_require_login(client):
    response = client.get("/recommendations", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data or b"login" in response.data


def test_readiness_page_loads(client):
    _login_demo(client)
    response = client.get("/readiness")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "readiness" in html.lower()
    assert "Apply Now" not in html


def test_skill_gap_page_loads(client):
    _login_demo(client)
    response = client.get("/skill-gap")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "skill" in html.lower()
    assert "Apply Now" not in html


def test_examiner_page_loads(client):
    _login_demo(client)
    response = client.get("/examiner")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "exam" in html.lower() or "examiner" in html.lower()
    assert "Apply Now" not in html


def test_student_pages_have_no_apply_now(client):
    _login_demo(client)
    for path in STUDENT_PAGES:
        response = client.get(path)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Apply Now" not in html
        assert "Find Internship" not in html


def test_resume_fixer_requires_login(client):
    response = client.get("/resume-fixer")
    assert response.status_code in (301, 302)
    assert "login" in response.headers.get("Location", "").lower()


def test_resume_fixer_page_loads_for_demo(client):
    _login_demo(client)
    response = client.get("/resume-fixer")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Fix Your Resume" in html
    assert "does not apply to companies" in html.lower()
    assert "Apply Now" not in html


def test_resume_fixer_pdf_requires_resume_text(client):
    _login_demo(client)
    response = client.post("/resume-fixer/pdf")
    assert response.status_code == 400
    assert b"resume" in response.data.lower()


def test_resume_fixer_pdf_returns_pdf(client):
    _login_demo(client)
    analyze = client.post(
        "/resume-analyzer",
        data={
            "resume_text": (
                "Demo Student\nBengaluru\ndemo.student@internmatch.local\n"
                "Education\nBCA, Sample College\n"
                "Skills\nPython, HTML, CSS, Flask, SQL\n"
                "Projects\nCampus portal with Flask and SQLite\n"
            )
        },
        follow_redirects=True,
    )
    assert analyze.status_code == 200
    response = client.post("/resume-fixer/pdf")
    assert response.status_code == 200
    assert "pdf" in (response.content_type or "")
    assert response.data.startswith(b"%PDF")
    assert "InternMatch_Resume_" in response.headers.get("Content-Disposition", "")
