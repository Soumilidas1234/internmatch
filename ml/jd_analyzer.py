"""Compare a pasted job description with the logged-in student's profile.

Reuses find_skills, TF-IDF cosine similarity, the local neural matcher, and
score_internship() (Student ↔ JD, same weights as Student ↔ Target Role).
Does not invent skills, titles, or requirements that are not in the text.
"""

import re

from ml.matcher import student_profile_text
from ml.prep import prioritize_missing
from ml.recommender import score_role_readiness
from ml.roles import ROLE_NAMES
from tools import find_skills


MIN_JD_CHARS = 80
MAX_JD_CHARS = 20000

# Same weights as ml.matcher.score_internship
SCORE_WEIGHTS = (
    ("Skill Coverage", 40),
    ("Keyword / TF-IDF similarity", 20),
    ("Neural text match", 15),
    ("Role relevance", 10),
    ("Location / work mode", 10),
    ("Education compatibility", 5),
)

PREP_HINTS = {
    "sql": "Practice SQL joins and aggregation.",
    "power bi": "Review dashboard creation in Power BI.",
    "tableau": "Practice building a simple Tableau or similar dashboard.",
    "statistics": "Revise probability and basic statistics used in analysis.",
    "python": "Practice Python problem solving on small datasets or scripts.",
    "excel": "Practice pivot tables and charts in Excel.",
    "pandas": "Practice cleaning and grouping data with Pandas.",
    "javascript": "Practice DOM basics and one small interactive page.",
    "flask": "Build a small Flask route that reads and stores data.",
    "machine learning": "Review a beginner ML workflow: data, train, evaluate.",
    "communication": "Practice explaining a project with a specific example.",
}


class JDTarget:
    """Internship-shaped object so the existing matcher can score a pasted JD."""

    def __init__(self, title, description, required_skills, location="", work_mode=""):
        self.title = title if title and title != "Not detected" else "Pasted role"
        self.company = "Job Description"
        self.description = description
        self.required_skills = required_skills
        self.location = location
        self.work_mode = work_mode


def _split_preferred_block(text):
    lowered = text.lower()
    markers = (
        "preferred qualification",
        "preferred skills",
        "nice to have",
        "good to have",
        "plus if",
        "bonus",
    )
    idx = -1
    for marker in markers:
        found = lowered.find(marker)
        if found != -1 and (idx == -1 or found < idx):
            idx = found
    if idx == -1:
        return text, ""
    return text[:idx], text[idx:]


def detect_job_title(text):
    lowered = text.lower()
    for role in ROLE_NAMES:
        if role.lower() in lowered:
            return role
    labeled = re.search(
        r"(?:job\s*title|role|position)\s*[:\-]\s*(.+)",
        text,
        re.I,
    )
    if labeled:
        title = labeled.group(1).strip().split("\n")[0].strip(" .:-")
        if 3 <= len(title) <= 80:
            return title
    first = text.strip().split("\n")[0].strip()
    word_count = len(first.split())
    if 2 <= word_count <= 8 and 8 <= len(first) <= 80:
        if not re.search(r"\b(we are|about us|responsib|requirement)\b", first, re.I):
            return first
    return "Not detected"


def detect_education(text):
    match = re.search(
        r"((?:bachelor|master|bca|b\.?tech|b\.?sc|bsc|mca|degree|graduate)[^\n.]{0,80})",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip(" .")
    return "Not detected"


def detect_experience(text):
    match = re.search(
        r"(\d+\+?\s*(?:to\s*\d+\s*)?years?\s+(?:of\s+)?(?:experience|exp))",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip()
    if re.search(r"\b(fresher|entry[-\s]?level|internship|intern)\b", text, re.I):
        found = re.search(r"\b(fresher|entry[-\s]?level|internship|intern)\b", text, re.I)
        return found.group(1)
    return "Not detected"


def detect_work_mode(text):
    lowered = text.lower()
    if "hybrid" in lowered:
        return "Hybrid"
    if "remote" in lowered:
        return "Remote"
    if "on-site" in lowered or "onsite" in lowered or "office" in lowered:
        return "On-site"
    return ""


def detect_responsibilities(text):
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"^([\-•*]|\d+[.)])\s+", line):
            cleaned = re.sub(r"^([\-•*]|\d+[.)])\s+", "", line).strip()
            if 12 <= len(cleaned) <= 180:
                lines.append(cleaned)
    if lines:
        return lines[:8]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    picked = []
    for sentence in sentences:
        if re.search(r"\b(analy[sz]e|build|write|create|develop|design|maintain|collaborate)\b", sentence, re.I):
            cleaned = sentence.strip()
            if 20 <= len(cleaned) <= 180:
                picked.append(cleaned)
        if len(picked) >= 6:
            break
    return picked


def _keyword_list(text, limit=18):
    from sklearn.feature_extraction.text import TfidfVectorizer

    cleaned = (text or "").strip()
    if len(cleaned.split()) < 8:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=40, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([cleaned])
        scores = matrix.toarray()[0]
        names = vectorizer.get_feature_names_out()
        ranked = sorted(zip(names, scores), key=lambda item: item[1], reverse=True)
    except ValueError:
        return []
    skip = {"experience", "team", "work", "role", "job", "ability", "strong", "good"}
    words = []
    for name, score in ranked:
        if score <= 0 or name in skip or len(name) < 3:
            continue
        words.append(name)
        if len(words) >= limit:
            break
    return words


def _prep_suggestion(skill):
    key = skill.lower()
    for needle, hint in PREP_HINTS.items():
        if needle in key:
            return hint
    return f"Study {skill} because the description mentions it and it is not detected in your profile."


def validate_job_description(text):
    cleaned = (text or "").strip()
    if not cleaned:
        return None, "Please paste a complete job description before analyzing."
    if len(cleaned) < MIN_JD_CHARS:
        return None, "Please paste a complete job description before analyzing."
    if len(cleaned) > MAX_JD_CHARS:
        return None, "That description is too long. Paste a shorter job description."
    if len(cleaned.split()) < 12:
        return None, "Please paste a complete job description before analyzing."
    return cleaned, None


def analyze_job_description(student, jd_text, resume_text=""):
    """Return a dict of extracted JD facts plus matcher scores. No invented facts."""
    required_block, preferred_block = _split_preferred_block(jd_text)
    required_skills = find_skills(required_block)
    preferred_skills = find_skills(preferred_block) if preferred_block else []
    preferred_skills = [skill for skill in preferred_skills if skill not in required_skills]
    all_detected = find_skills(jd_text)
    if not required_skills:
        required_skills = all_detected

    title = detect_job_title(jd_text)
    education = detect_education(jd_text)
    experience = detect_experience(jd_text)
    work_mode = detect_work_mode(jd_text)
    responsibilities = detect_responsibilities(jd_text)

    matcher_student = dict(student)
    extra = (resume_text or "").strip()
    if extra:
        matcher_student["skills"] = ", ".join(
            part for part in [student.get("skills") or "", extra] if part
        )

    jd_target = JDTarget(
        title=title,
        description=jd_text,
        required_skills=", ".join(required_skills),
        work_mode=work_mode,
    )
    match = score_role_readiness(matcher_student, jd_target)
    have = match["matched_skills"]
    missing = match["missing_skills"]
    if not required_skills:
        have, missing = [], []

    student_blob = (student_profile_text(matcher_student) + " " + extra).lower()
    jd_keywords = _keyword_list(jd_text)
    matching_keywords = [word for word in jd_keywords if word.lower() in student_blob]
    missing_keywords = [word for word in jd_keywords if word.lower() not in student_blob]

    mention_counts = {skill.lower(): jd_text.lower().count(skill.lower()) for skill in missing}
    high, medium, low = [], [], []
    preferred_set = {skill.lower() for skill in preferred_skills}
    for skill in missing:
        key = skill.lower()
        if key in preferred_set and mention_counts.get(key, 0) <= 1:
            low.append(skill)
        elif mention_counts.get(key, 0) >= 2 or key in {"sql", "python", "java", "javascript"}:
            high.append(skill)
        else:
            medium.append(skill)
    if not high and not medium and not low and missing:
        mapped = prioritize_missing(missing)
        high, medium, low = mapped["high"], mapped["medium"], mapped["low"]

    priority_rows = []
    for skill in high:
        priority_rows.append(
            {
                "skill": skill,
                "level": "High Priority",
                "reason": "Required by the role and currently not detected in your profile.",
            }
        )
    for skill in medium:
        priority_rows.append(
            {
                "skill": skill,
                "level": "Medium Priority",
                "reason": "Mentioned in the description and not clearly present in your profile.",
            }
        )
    for skill in low:
        priority_rows.append(
            {
                "skill": skill,
                "level": "Low Priority",
                "reason": "Listed as preferred or mentioned lightly, and not detected in your profile.",
            }
        )

    suggestions = [_prep_suggestion(item["skill"]) for item in priority_rows[:5]]
    if responsibilities and not suggestions:
        suggestions = ["Practice explaining a project that matches one of the listed responsibilities."]

    tools = [skill for skill in all_detected if skill.lower() in {
        "excel", "power bi", "tableau", "git", "github", "flask", "django",
        "pandas", "numpy", "figma", "mysql", "sqlite", "mongodb",
    }]

    match_public = {key: value for key, value in match.items() if key not in ("role", "internship")}

    return {
        "job_title": title,
        "required_skills": required_skills or "Not detected",
        "preferred_skills": preferred_skills or "Not detected",
        "tools": tools or "Not detected",
        "education": education,
        "experience": experience,
        "responsibilities": responsibilities or "Not detected",
        "keywords": jd_keywords or "Not detected",
        "have": have,
        "missing": missing,
        "priority": {"high": high, "medium": medium, "low": low},
        "priority_rows": priority_rows,
        "matching_keywords": matching_keywords,
        "missing_keywords": missing_keywords,
        "suggestions": suggestions,
        "match": match_public,
        "score": match["final_score"],
        "weights": SCORE_WEIGHTS,
        "work_mode": work_mode or "Not detected",
    }
