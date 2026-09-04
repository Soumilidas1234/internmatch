from ml.resume_fixer import build_resume_fix, recommended_keywords, render_resume_pdf


class FakeUser:
    name = "Asha Kumar"
    email = "asha@test.com"
    education = "BCA"
    cgpa = 8.0
    location = "Pune"
    skills = "Python, HTML, CSS, Figma"
    preferred_domain = "Web Developer"
    target_role = "Web Developer"
    preferred_work_mode = "Hybrid"


def test_rebuild_does_not_invent_jobs_or_companies():
    plan = build_resume_fix(
        FakeUser(),
        "Asha Kumar\nBCA student\nSkills: Python, HTML, CSS",
        resume_analyzed=True,
    )
    blob = plan["preview_text"].lower()
    assert "google" not in blob
    assert "microsoft" not in blob
    assert "suggested" in blob
    assert plan["document"]["experience"] == []
    assert any("work history" in item.lower() for item in plan["document"]["suggested"])


def test_rebuild_keeps_extracted_project_and_marks_keywords():
    text = (
        "Asha Kumar\n"
        "Education\nBCA, City College\n"
        "Skills\nPython, HTML, CSS, Flask\n"
        "Projects\nCampus portal using Flask and SQLite\n"
    )
    plan = build_resume_fix(FakeUser(), text, resume_analyzed=True)
    assert any("Campus portal" in item for item in plan["document"]["projects"])
    assert any("[Suggested:" in line for line in plan["preview_text"].splitlines())
    assert plan["resume_score"] is not None
    assert plan["target"] == "Web Developer"
    assert "Figma" in plan["deemphasize"] or "figma" in " ".join(plan["deemphasize"]).lower()


def test_keywords_come_from_role_catalog():
    words = recommended_keywords("Data Analyst")
    assert "SQL" in words
    assert "Python" in words
    assert "dashboard" in words


def test_pdf_bytes_are_valid():
    plan = build_resume_fix(
        FakeUser(),
        "Asha Kumar\nEducation\nBCA\nSkills\nPython, HTML\nProjects\nPortfolio site",
        resume_analyzed=True,
    )
    pdf = render_resume_pdf(plan["document"])
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 200
