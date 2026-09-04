"""Preparation helpers: skill gaps, 14-day plans, exam mistakes, readiness.

Matching still uses ml.matcher and ml.neural_matcher. Internship rows are no
longer shown to students; the compared document is a target role profile.
"""

from collections import Counter

from ml.matcher import display_skill, parse_skills
from ml.recommender import score_role_readiness, student_has_skills
from ml.roles import ROLE_NAMES, RoleTarget, get_role_spec, resolve_role_name


PRIORITY_HIGH = {"sql", "python", "statistics", "javascript", "java", "machine learning"}
PRIORITY_MEDIUM = {"power bi", "pandas", "excel", "flask", "html", "css"}


def user_target_role(user):
    return resolve_role_name(getattr(user, "target_role", None) or user.preferred_domain)


def role_readiness_for(student, role_name):
    role = RoleTarget(resolve_role_name(role_name))
    return score_role_readiness(student, role)


def split_known_missing(student_skills, role_name):
    role = RoleTarget(resolve_role_name(role_name))
    known = parse_skills(student_skills)
    required = parse_skills(role.required_skills)
    known_set = set(known)
    have = [display_skill(skill) for skill in required if skill in known_set]
    missing = [display_skill(skill) for skill in required if skill not in known_set]
    return have, missing, required


def prioritize_missing(missing):
    high, medium, low = [], [], []
    for skill in missing:
        key = skill.lower()
        if key in PRIORITY_HIGH or "sql" in key or "stat" in key:
            high.append(skill)
        elif key in PRIORITY_MEDIUM:
            medium.append(skill)
        else:
            low.append(skill)
    return {"high": high, "medium": medium, "low": low}


def build_preparation_plan(student_skills, role_name, exam_attempts=None):
    """Build a 14-day plan from missing skills and recent exam mistakes."""
    _have, missing, _required = split_known_missing(student_skills, role_name)
    priority = prioritize_missing(missing)
    weak_topics = []
    if exam_attempts:
        latest = exam_attempts[0]
        mistakes = latest.mistake_list()
        weak_topics = [item.get("topic") for item in mistakes if item.get("topic")]

    topics = []
    for topic in weak_topics:
        if topic and topic not in topics:
            topics.append(topic)
    for group in (priority["high"], priority["medium"], priority["low"]):
        for skill in group:
            if skill not in topics:
                topics.append(skill)
    if not topics:
        topics = ["Python problem solving", "SQL", "Communication"]

    blocks = [
        (1, 3, topics[0] if topics else "Core skills"),
        (4, 5, topics[1] if len(topics) > 1 else "Practice problems"),
        (6, 7, topics[2] if len(topics) > 2 else "Tools and dashboards"),
        (8, 10, "Python problem solving" if "Python" not in str(topics[:3]) else topics[0]),
        (11, 12, "Technical interview"),
        (13, 13, "HR interview / STAR answers"),
        (14, 14, "Final mock examination"),
    ]
    plan = []
    for start, end, focus in blocks:
        label = f"Day {start}" if start == end else f"Day {start}–{end}"
        plan.append({"days": label, "focus": focus})
    return {
        "role": resolve_role_name(role_name),
        "missing": missing,
        "priority": priority,
        "plan": plan,
        "weak_topics": weak_topics,
    }


def analyze_exam_mistakes(results):
    """Group weak answers by topic using existing keyword scoring."""
    by_topic = {}
    for item in results:
        topic = item.get("topic") or "General"
        bucket = by_topic.setdefault(topic, {"topic": topic, "mistakes": 0, "missed_keywords": [], "tips": []})
        if item.get("score", 0) < 70:
            bucket["mistakes"] += 1
            missed = [word for word in item.get("keywords", []) if word not in (item.get("hits") or [])]
            bucket["missed_keywords"].extend(missed[:2])
            if item.get("tip"):
                bucket["tips"].append(item["tip"])
    analysis = []
    for topic, bucket in by_topic.items():
        if bucket["mistakes"] == 0:
            continue
        common = Counter(bucket["missed_keywords"]).most_common(1)
        problem = common[0][0] if common else "incomplete answers"
        how = bucket["tips"][0] if bucket["tips"] else f"Practice more {topic} questions."
        if "join" in problem.lower():
            how = "Practice SQL JOIN questions."
        elif "probability" in problem.lower() or "stat" in topic.lower():
            how = "Revise probability and statistics basics."
        elif topic.lower() in {"interview", "hr", "communication"}:
            how = "Use the STAR method and add a specific example."
        analysis.append(
            {
                "topic": topic,
                "mistakes": bucket["mistakes"],
                "problem": problem,
                "how": how,
            }
        )
    analysis.sort(key=lambda item: item["mistakes"], reverse=True)
    return analysis


def topic_scores_from_results(results):
    totals = {}
    counts = {}
    for item in results:
        topic = item.get("topic") or "General"
        totals[topic] = totals.get(topic, 0) + int(item.get("score", 0))
        counts[topic] = counts.get(topic, 0) + 1
    return {topic: round(totals[topic] / counts[topic]) for topic in totals}


def interview_readiness(profile_score, role_match, last_exam=None):
    technical = int(role_match.get("skill_score") or 0)
    exam = int(last_exam.overall_score) if last_exam else 50
    communication = 50
    if last_exam:
        topics = last_exam.topic_map()
        communication = int(topics.get("Interview", topics.get("Communication", exam)))
    problem_solving = exam
    resume = int(profile_score or 0)
    overall = round(
        0.25 * resume
        + 0.25 * technical
        + 0.20 * problem_solving
        + 0.15 * communication
        + 0.15 * exam
    )
    overall = max(0, min(overall, 100))
    parts = {
        "Resume": resume,
        "Technical Skills": technical,
        "Problem Solving": problem_solving,
        "Communication": communication,
        "Interview Performance": exam,
    }
    weakest = min(parts, key=parts.get)
    return {
        "score": overall,
        "parts": parts,
        "opportunity": weakest,
        "disclaimer": "AI-generated readiness estimate. This does not guarantee a job or internship.",
    }
