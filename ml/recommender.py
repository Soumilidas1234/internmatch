"""Rank target-role readiness using TF-IDF matching and a local neural network.

recommend_internships() is a legacy helper kept for tests. The student UI
uses score_role_readiness() (Student ↔ Target Role), not internship listings.
"""

from ml.matcher import (
    compute_text_similarities,
    internship_profile_text,
    parse_skills,
    score_internship,
    student_profile_text,
)
from ml.neural_matcher import compute_neural_scores


def student_has_skills(student):
    return bool(parse_skills(student.get("skills", "")))


def recommend_internships(student, internships, top_n=10):
    """Legacy helper kept for tests. Student UI no longer lists internships."""
    if not internships:
        return []

    intern_list = list(internships)
    student_text = student_profile_text(student)
    intern_texts = [internship_profile_text(item) for item in intern_list]
    text_scores = compute_text_similarities(student_text, intern_texts)
    neural_scores = compute_neural_scores(student_text, intern_texts)

    ranked = []
    for internship, text_score, neural_score in zip(intern_list, text_scores, neural_scores):
        match = score_internship(student, internship, text_score, neural_score)
        match["internship"] = internship
        ranked.append(match)

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked[:top_n]


def score_role_readiness(student, role):
    """Compare a student profile with a target role using the same ML pipeline.

    Previously: student ↔ internship listing.
    Now: student ↔ target role skill/description profile.
    """
    student_text = student_profile_text(student)
    role_text = internship_profile_text(role)
    text_scores = compute_text_similarities(student_text, [role_text])
    neural_scores = compute_neural_scores(student_text, [role_text, role_text])
    text_score = text_scores[0] if text_scores else 0
    neural_score = neural_scores[0] if neural_scores else 0
    match = score_internship(student, role, text_score, neural_score)
    match["role"] = role
    match["readiness"] = match["final_score"]
    return match
