"""ATS-style resume simulation against a target role or pasted job description.

This is an educational estimate. It does not represent any real company's ATS.

Reuses:
- stored resume text and section/contact helpers from ml.resume_fixer
- find_skills and role catalog
- TF-IDF keyword extraction from ml.jd_analyzer
- score_role_readiness (Student ↔ Role or Student ↔ JD)

ATS simulation score weights (must sum to 100):
- Keyword Coverage 30%
- Role Relevance (TF-IDF cosine) 25%
- Skills Coverage 25%
- Resume Structure 10%
- Content Completeness 10%
"""

import re

from ml.jd_analyzer import JDTarget, MIN_JD_CHARS, _keyword_list
from ml.recommender import score_role_readiness
from ml.resume_fixer import (
    EDU_HINTS,
    EMAIL_RE,
    EXP_HINTS,
    PHONE_RE,
    PROJ_HINTS,
    recommended_keywords,
    stored_resume_text,
    _match_section,
)
from ml.roles import ROLE_NAMES, RoleTarget, resolve_role_name
from tools import find_skills

ATS_WEIGHTS = (
    ("Keyword Coverage", 30),
    ("Role Relevance", 25),
    ("Skills Coverage", 25),
    ("Resume Structure", 10),
    ("Content Completeness", 10),
)


def _blob(*parts):
    return " ".join(str(part) for part in parts if part).lower()


def resume_structure(text):
    """Detect common sections from extracted text only. Experience is optional for freshers."""
    text = text or ""
    lowered = text.lower()
    headers = set()
    for line in text.splitlines():
        section = _match_section(line)
        if section:
            headers.add(section)

    contact = bool(EMAIL_RE.search(text) or PHONE_RE.findall(text))
    summary = "summary" in headers or bool(re.search(r"\b(objective|about me|profile)\b", lowered))
    education = "education" in headers or any(hint in lowered for hint in EDU_HINTS)
    skills = "skills" in headers or bool(find_skills(text))
    projects = "projects" in headers or any(hint in lowered for hint in PROJ_HINTS)
    experience = "experience" in headers or any(hint in lowered for hint in EXP_HINTS)
    certifications = "certifications" in headers or "certification" in lowered
    achievements = "achievement" in lowered or "achievements" in lowered

    items = [
        {"label": "Contact Information", "ok": contact, "optional": False},
        {"label": "Professional summary/objective", "ok": summary, "optional": True},
        {"label": "Education", "ok": education, "optional": False},
        {"label": "Skills", "ok": skills, "optional": False},
        {"label": "Projects", "ok": projects, "optional": False},
        {"label": "Experience", "ok": experience, "optional": True},
        {"label": "Certifications", "ok": certifications, "optional": True},
        {"label": "Achievements", "ok": achievements, "optional": True},
    ]
    required = [item for item in items if not item["optional"]]
    present = sum(1 for item in required if item["ok"])
    score = round((present / len(required)) * 100) if required else 0
    return items, score


def content_completeness(text, structure_items):
    words = len((text or "").split())
    if words >= 250:
        length_score = 40
    elif words >= 120:
        length_score = 25
    elif words >= 50:
        length_score = 12
    else:
        length_score = 0
    lookup = {item["label"]: item["ok"] for item in structure_items}
    project_score = 30 if lookup.get("Projects") else 0
    contact_score = 30 if lookup.get("Contact Information") else 0
    return min(100, length_score + project_score + contact_score), words


def _keyword_coverage(needed, haystack):
    if not needed:
        return 0, [], []
    blob = haystack.lower()
    matching, missing = [], []
    for word in needed:
        if str(word).lower() in blob:
            matching.append(word)
        else:
            missing.append(word)
    percent = round((len(matching) / len(needed)) * 100)
    return percent, matching, missing


def _repeat_warning(text):
    lines = [re.sub(r"\s+", " ", line.strip().lower()) for line in (text or "").splitlines() if len(line.strip()) > 20]
    seen = {}
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
    return any(count >= 3 for count in seen.values())


def _unclear_projects(text):
    lowered = (text or "").lower()
    if "project" not in lowered and "github" not in lowered:
        return False
    sentences = [part for part in re.split(r"[.\n]", text or "") if "project" in part.lower()]
    if not sentences:
        return True
    return all(len(part.split()) < 8 for part in sentences)


def simulate_ats(student, resume_text, target_role, job_description=""):
    """Compare resume text to a role or pasted JD. Does not invent skills."""
    resume_text = (resume_text or "").strip()
    jd_text = (job_description or "").strip()
    role_name = resolve_role_name(target_role or student.get("target_role") or "Software Developer")
    used_jd = len(jd_text) >= MIN_JD_CHARS

    student_payload = dict(student)
    student_payload["skills"] = ", ".join(
        part for part in [student.get("skills") or "", resume_text] if part
    )
    student_payload["preferred_domain"] = role_name
    student_payload["target_role"] = role_name

    if used_jd:
        jd_skills = find_skills(jd_text)
        target = JDTarget(
            title=role_name,
            description=jd_text,
            required_skills=", ".join(jd_skills),
        )
        needed_keywords = jd_skills or _keyword_list(jd_text, limit=16)
        if not needed_keywords:
            needed_keywords = recommended_keywords(role_name)
    else:
        target = RoleTarget(role_name)
        needed_keywords = recommended_keywords(role_name)

    match = score_role_readiness(student_payload, target)
    match_public = {key: value for key, value in match.items() if key not in ("role", "internship")}

    haystack = _blob(resume_text, student.get("skills"), student.get("education"))
    keyword_score, matching_keywords, missing_keywords = _keyword_coverage(needed_keywords, haystack)
    skills_score = match["skill_score"]
    role_relevance = match["text_similarity_score"]
    structure_items, structure_score = resume_structure(resume_text)
    completeness_score, word_count = content_completeness(resume_text, structure_items)

    ats_score = round(
        0.30 * keyword_score
        + 0.25 * role_relevance
        + 0.25 * skills_score
        + 0.10 * structure_score
        + 0.10 * completeness_score
    )
    ats_score = max(0, min(100, ats_score))

    warnings = []
    if word_count < 80:
        warnings.append("Very little text was extracted. The simulation has little content to score.")
    elif word_count < 150:
        warnings.append("Resume content looks short. Add education, skills, and project detail if you have them.")
    for item in structure_items:
        if not item["ok"] and not item["optional"]:
            warnings.append(f"{item['label']} was not clearly detected in the extracted text.")
    if missing_keywords[:3]:
        warnings.append(
            "These target-role or job-description terms were not detected: "
            + ", ".join(str(item) for item in missing_keywords[:3])
            + "."
        )
    if _repeat_warning(resume_text):
        warnings.append("The same lines appear many times, which can make the resume look unclear.")
    if _unclear_projects(resume_text):
        warnings.append("Project mentions look brief. Say what you built and which tools you used.")
    resume_skills = find_skills(resume_text)
    lookup = {item["label"]: item["ok"] for item in structure_items}
    if resume_skills and not lookup.get("Projects") and not lookup.get("Experience"):
        warnings.append(
            "Skills are listed, but no project or experience section was detected to support them."
        )

    have = match["matched_skills"]
    missing = match["missing_skills"]
    suggestions = []
    for skill in missing[:4]:
        suggestions.append(
            f"Add {skill} only if you genuinely have used it, ideally in a project sentence."
        )
    if _unclear_projects(resume_text) or not lookup.get("Projects"):
        suggestions.append("Describe a project with the outcome and the technologies you used.")
    if have:
        suggestions.append(
            "Highlight relevant skills already detected, such as "
            + ", ".join(have[:3])
            + "."
        )
    if not lookup.get("Contact Information"):
        suggestions.append("Add an email or phone number so a recruiter can contact you.")
    if word_count < 150:
        suggestions.append("Expand education and skills so the extracted text is not too thin.")
    suggestions = suggestions[:7]
    if not suggestions:
        suggestions.append("Keep project descriptions specific and only list skills you actually used.")

    current_issues = []
    improve = []
    for skill in missing_keywords[:4]:
        current_issues.append(f"Missing keyword: {skill}")
        improve.append(f"Mention {skill} only if you genuinely used it.")
    if _unclear_projects(resume_text):
        current_issues.append("Weak or very short project description")
        improve.append("Explain what the project achieved and which technologies were used.")
    if not current_issues:
        current_issues.append("No major keyword gaps were detected from the available text.")
        improve.append("Keep descriptions specific; do not add skills you do not have.")

    have_labels = ", ".join(have[:4]) if have else "few overlapping required skills"
    missing_labels = ", ".join(missing[:4]) if missing else "no extra required skills"
    relevance_why = (
        f"Your resume contains skills relevant to {role_name}, including {have_labels}. "
        f"{missing_labels.capitalize()} were not detected."
        if missing
        else f"Your resume contains several skills relevant to {role_name}, including {have_labels}."
    )

    return {
        "ats_score": ats_score,
        "keyword_score": keyword_score,
        "role_relevance_score": role_relevance,
        "skills_score": skills_score,
        "structure_score": structure_score,
        "completeness_score": completeness_score,
        "weights": ATS_WEIGHTS,
        "target_role": role_name,
        "used_job_description": used_jd,
        "matching_keywords": matching_keywords,
        "missing_keywords": missing_keywords,
        "structure": structure_items,
        "warnings": warnings,
        "suggestions": suggestions,
        "have": have,
        "missing": missing,
        "word_count": word_count,
        "relevance_why": relevance_why,
        "current_issues": current_issues,
        "improve": improve,
        "match": match_public,
    }
