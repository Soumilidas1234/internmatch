from ml.neural_matcher import compute_neural_scores
from ml.recommender import recommend_internships, student_has_skills


class FakeInternship:
    def __init__(self, title, description, skills, location="Bengaluru", work_mode="Hybrid"):
        self.title = title
        self.description = description
        self.required_skills = skills
        self.location = location
        self.work_mode = work_mode
        self.company = "Sample Co"
        self.id = 1


def test_neural_scores_return_one_value_per_internship():
    internships = [
        "Domain: Web Development. HTML CSS Flask pages.",
        "Domain: Machine Learning. Python pandas models.",
        "Domain: Web Development. JavaScript frontend forms.",
    ]
    scores = compute_neural_scores("Python HTML CSS Flask web development", internships)
    assert len(scores) == 3
    assert all(0 <= score <= 100 for score in scores)


def test_neural_scores_empty_and_single_list():
    assert compute_neural_scores("python", []) == []
    assert compute_neural_scores("python", ["only one internship"]) == [0]


def test_student_has_skills():
    assert student_has_skills({"skills": "Python, HTML"}) is True
    assert student_has_skills({"skills": ""}) is False


def test_recommend_internships_ranks_web_student_toward_web_roles():
    student = {
        "skills": "Python, HTML, CSS, Flask",
        "education": "BCA",
        "preferred_domain": "Web Development",
        "preferred_work_mode": "Hybrid",
        "location": "Bengaluru",
    }
    internships = [
        FakeInternship(
            "ML Intern",
            "Domain: Machine Learning. Train models with pandas.",
            "Python, Machine Learning, Pandas",
        ),
        FakeInternship(
            "Web Intern",
            "Domain: Web Development. Build Flask templates.",
            "HTML, CSS, Python, Flask",
        ),
    ]
    ranked = recommend_internships(student, internships, top_n=2)
    assert len(ranked) == 2
    assert ranked[0]["internship"].title == "Web Intern"
    assert "neural_score" in ranked[0]
