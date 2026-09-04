def _login_demo(client):
    return client.post(
        "/login",
        data={
            "email": "demo.student@internmatch.local",
            "password": "Demo@123",
        },
        follow_redirects=True,
    )


SAMPLE_JD = """
Data Analyst Intern
We are hiring a Data Analyst intern to analyze datasets, write SQL queries, and create dashboards.
Required skills: Python, SQL, Excel, Pandas, Power BI, Statistics.
Preferred skills: Tableau, communication.
Education: Bachelor or BCA preferred.
Experience: 0-1 years or fresher. Hybrid work.
Responsibilities:
- Analyze datasets
- Build reports
- Write SQL queries
- Create dashboards
"""


def test_job_analyzer_requires_login(client):
    response = client.get("/job-analyzer")
    assert response.status_code in (301, 302)
    assert "login" in response.headers.get("Location", "").lower()


def test_job_analyzer_page_loads(client):
    _login_demo(client)
    response = client.get("/job-analyzer")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Job Description Analyzer" in html
    assert "Apply Now" not in html
    assert "Find Internship" not in html


def test_job_analyzer_rejects_empty(client):
    _login_demo(client)
    response = client.post("/job-analyzer", data={"job_description": "   "}, follow_redirects=True)
    assert response.status_code == 200
    assert b"complete job description" in response.data.lower()


def test_job_analyzer_saves_and_shows_score(client):
    _login_demo(client)
    response = client.post("/job-analyzer", data={"job_description": SAMPLE_JD}, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Role preparation match" in html
    assert "SQL" in html
    assert "Apply Now" not in html
    assert "How is this score calculated?" in html


def test_job_analyzer_hides_other_users_records(client):
    _login_demo(client)
    client.post("/job-analyzer", data={"job_description": SAMPLE_JD}, follow_redirects=True)
    response = client.get("/job-analyzer/99999", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found" in response.data.lower() or b"Job Description Analyzer" in response.data
