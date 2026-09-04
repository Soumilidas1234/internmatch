"""Rank internships for a student using the local matcher."""

from ml.matcher import (
    compute_text_similarities,
    internship_profile_text,
    parse_skills,
    score_internship,
    student_profile_text,
)


def student_has_skills(student):
    return bool(parse_skills(student.get("skills", "")))


def recommend_internships(student, internships, top_n=10):
    if not internships:
        return []

    intern_list = list(internships)
    student_text = student_profile_text(student)
    intern_texts = [internship_profile_text(item) for item in intern_list]
    text_scores = compute_text_similarities(student_text, intern_texts)

    ranked = []
    for internship, text_score in zip(intern_list, text_scores):
        match = score_internship(student, internship, text_score)
        match["internship"] = internship
        ranked.append(match)

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked[:top_n]
