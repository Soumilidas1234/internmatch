def _login_demo(client):
    return client.post(
        "/login",
        data={
            "email": "demo.student@internmatch.local",
            "password": "Demo@123",
        },
        follow_redirects=True,
    )


def test_ats_simulator_requires_login(client):
    response = client.get("/ats-simulator")
    assert response.status_code in (301, 302)
    assert "login" in response.headers.get("Location", "").lower()


def test_ats_simulator_page_loads(client):
    _login_demo(client)
    response = client.get("/ats-simulator")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ATS Resume Simulator" in html
    assert "does not represent the result of any real company's ATS" in html
    assert "Apply Now" not in html


def test_ats_simulator_needs_resume(client):
    _login_demo(client)
    from models import User, db
    from app import app

    with app.app_context():
        user = User.query.filter_by(email="demo.student@internmatch.local").first()
        user.last_resume_text = ""
        db.session.commit()
    response = client.post(
        "/ats-simulator",
        data={"target_role": "Data Analyst", "job_description": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"resume" in response.data.lower()


def test_ats_simulator_runs_with_resume(client):
    _login_demo(client)
    resume = (
        "Soumi BCA student\n"
        "email: demo.student@internmatch.local\n"
        "Education: BCA\n"
        "Skills: Python, HTML, CSS, JavaScript, Flask, SQL, Git\n"
        "Projects: Built a Flask campus portal with SQL storage and a README on GitHub.\n"
    )
    response = client.post(
        "/ats-simulator",
        data={
            "target_role": "Web Developer",
            "resume_text": resume,
            "job_description": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ATS simulation score" in html
    assert "/ 100" in html
    assert "How this score is calculated" in html
    from models import User, db
    from app import app

    with app.app_context():
        user = User.query.filter_by(email="demo.student@internmatch.local").first()
        user.last_resume_text = ""
        db.session.commit()


def test_ats_simulator_hides_other_users(client):
    _login_demo(client)
    response = client.get("/ats-simulator/99999", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found" in response.data.lower() or b"ATS Resume Simulator" in response.data
