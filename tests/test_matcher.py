from ml.matcher import match_label, parse_skills, score_internship, skill_match_score


class FakeInternship:
    def __init__(self):
        self.title = "Web Development Intern"
        self.description = "Domain: Web Development. Build Flask pages for a sample campus portal."
        self.required_skills = "HTML, CSS, Python, Flask"
        self.location = "Bengaluru"
        self.work_mode = "Hybrid"


def test_parse_skills_splits_and_deduplicates():
    skills = parse_skills("Python, HTML, python, SQL")
    assert skills == ["python", "html", "sql"]


def test_skill_match_score_finds_overlap_and_gaps():
    percent, matched, missing = skill_match_score(
        ["python", "html"],
        ["python", "flask", "html"],
    )
    assert percent == 67
    assert matched == ["python", "html"]
    assert missing == ["flask"]


def test_match_label_thresholds():
    assert match_label(92)[0] == "Excellent Match"
    assert match_label(76)[0] == "Strong Match"
    assert match_label(61)[0] == "Good Match"
    assert match_label(41)[0] == "Partial Match"
    assert match_label(10)[0] == "Low Match"


def test_score_internship_includes_neural_weight():
    student = {
        "skills": "Python, HTML, CSS, Flask",
        "education": "BCA",
        "preferred_domain": "Web Development",
        "preferred_work_mode": "Hybrid",
        "location": "Bengaluru",
    }
    result = score_internship(student, FakeInternship(), text_similarity_score=80, neural_score=70)
    assert result["neural_score"] == 70
    assert 0 <= result["final_score"] <= 100
    assert result["skill_score"] == 100
    assert "skill" in result["why"].lower() or "neural" in result["why"].lower()
