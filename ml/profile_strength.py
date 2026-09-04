"""Score how complete a student profile is for interview preparation."""

from ml.matcher import parse_skills


def strength_label(score):
    if score >= 80:
        return "Excellent", "excellent"
    if score >= 60:
        return "Strong", "strong"
    if score >= 40:
        return "Average", "good"
    return "Weak", "low"


def _has_value(value):
    if value is None:
        return False
    return str(value).strip() != ""


def compute_profile_strength(user, resume_analyzed=False):
    """Return a 0-100 completeness score from existing profile fields."""
    score = 0
    checks = []
    suggestions = []

    fields = [
        ("Name", user.name, 10, "Add your name to the profile."),
        ("Education", user.education, 10, "Add your education."),
        ("CGPA", user.cgpa, 10, "Add your CGPA."),
        ("Location", user.location, 10, "Add your location."),
        ("Preferred domain", user.preferred_domain, 10, "Choose a target role."),
        ("Preferred work mode", user.preferred_work_mode, 10, "Choose a preferred work mode."),
    ]

    for name, value, points, tip in fields:
        done = _has_value(value)
        if done:
            score += points
        else:
            suggestions.append({"text": tip, "href": None})
        checks.append({"name": name, "done": done})

    skills = parse_skills(getattr(user, "skills", "") or "")
    if len(skills) >= 5:
        skill_points = 25
    elif len(skills) >= 3:
        skill_points = 18
    elif len(skills) == 2:
        skill_points = 12
    elif len(skills) == 1:
        skill_points = 8
    else:
        skill_points = 0
    score += skill_points
    checks.append({"name": "Skills", "done": bool(skills)})
    if len(skills) < 3:
        suggestions.append(
            {
                "text": "Add at least 3 skills, or analyze your resume to extract more.",
                "href": "resume_analyzer",
            }
        )

    if resume_analyzed:
        score += 15
    else:
        suggestions.append(
            {
                "text": "Analyze your resume to improve matching and profile strength.",
                "href": "resume_analyzer",
            }
        )
    checks.append({"name": "Resume analyzed", "done": bool(resume_analyzed)})

    score = max(0, min(int(score), 100))
    label, css_class = strength_label(score)

    if score >= 80:
        suggestions.append(
            {
                "text": "Your profile looks strong. Check role readiness or start an AI exam.",
                "href": "recommendations",
            }
        )

    return {
        "score": score,
        "label": label,
        "css_class": css_class,
        "checks": checks,
        "suggestions": suggestions,
        "skill_count": len(skills),
        "resume_analyzed": bool(resume_analyzed),
    }


def collect_skill_gaps(ranked, limit=6):
    """Collect unique missing skills from already-ranked internship matches."""
    counts = {}
    for item in ranked:
        for skill in item.get("missing_skills") or []:
            counts[skill] = counts.get(skill, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [skill for skill, _ in ordered[:limit]]
