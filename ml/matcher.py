"""Build internship match scores with TF-IDF, cosine similarity, and skill overlap."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def parse_skills(text):
    if not text:
        return []
    cleaned = text.replace("/", ",").replace("|", ",").replace(";", ",")
    skills = []
    seen = set()
    for part in cleaned.split(","):
        skill = " ".join(part.strip().lower().split())
        if skill and skill not in seen and skill != "no clear technical skills detected":
            seen.add(skill)
            skills.append(skill)
    return skills


def display_skill(skill):
    special = {
        "sql": "SQL",
        "html": "HTML",
        "css": "CSS",
        "ui": "UI",
        "ux": "UX",
        "power bi": "Power BI",
        "c++": "C++",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "machine learning": "Machine Learning",
    }
    return special.get(skill, skill.title())


def student_profile_text(student):
    parts = [
        student.get("skills", ""),
        student.get("education", ""),
        student.get("preferred_domain", ""),
        student.get("preferred_work_mode", ""),
        student.get("location", ""),
    ]
    return " ".join(str(part) for part in parts if part)


def internship_profile_text(internship):
    parts = [
        internship.title or "",
        internship.description or "",
        internship.required_skills or "",
        internship.location or "",
        internship.work_mode or "",
    ]
    return " ".join(parts)


def internship_domain_text(internship):
    description = internship.description or ""
    if description.startswith("Domain:"):
        return description.split(".", 1)[0].replace("Domain:", "").strip().lower()
    return (internship.title or "").lower() + " " + description.lower()


def skill_match_score(student_skills, internship_skills):
    student_set = set(student_skills)
    matched = [skill for skill in internship_skills if skill in student_set]
    missing = [skill for skill in internship_skills if skill not in student_set]
    if not internship_skills:
        percent = 0
    else:
        percent = round((len(matched) / len(internship_skills)) * 100)
    return percent, matched, missing


def domain_match_score(preferred_domain, internship):
    if not preferred_domain:
        return 0, False
    preferred = preferred_domain.lower()
    haystack = internship_domain_text(internship)
    title = (internship.title or "").lower()
    aliases = {
        "data analysis": ["data analytics", "data analysis", "data science"],
        "data analytics": ["data analytics", "data analysis", "data science"],
        "web development": ["web development", "frontend", "flask", "html"],
        "ui/ux": ["ui/ux", "ui", "ux", "figma"],
        "ui/ux design": ["ui/ux", "ui", "ux", "figma"],
        "machine learning": ["machine learning", "ml"],
        "python development": ["python"],
        "java development": ["java"],
        "cybersecurity": ["cybersecurity", "security"],
        "cloud computing": ["cloud"],
        "software testing": ["testing", "qa"],
    }
    keywords = aliases.get(preferred, [preferred])
    matched = any(word in haystack or word in title for word in keywords)
    return (100 if matched else 0), matched


def location_work_mode_score(student, internship):
    student_location = (student.get("location") or "").strip().lower()
    intern_location = (internship.location or "").strip().lower()
    student_mode = (student.get("preferred_work_mode") or "").strip().lower()
    intern_mode = (internship.work_mode or "").strip().lower()

    location_points = 0
    if student_location and intern_location:
        if student_location == intern_location or intern_location == "remote":
            location_points = 100
        elif student_location in intern_location or intern_location in student_location:
            location_points = 70

    mode_points = 0
    if student_mode and intern_mode:
        if student_mode == intern_mode:
            mode_points = 100
        elif "hybrid" in (student_mode, intern_mode):
            mode_points = 60
        elif intern_mode == "remote":
            mode_points = 50

    percent = round((location_points + mode_points) / 2)
    matched = percent >= 50
    return percent, matched


def education_match_score(education, internship):
    if not education:
        return 0, False
    edu = education.lower()
    intern_text = internship_profile_text(internship).lower()
    tokens = [word for word in ["bca", "b.sc", "bsc", "bachelor", "computer", "it", "engineering", "graduate"] if word in edu]
    if tokens and any(token in intern_text for token in tokens):
        return 100, True
    # Internships in this dataset are student-friendly
    return 60, True


def match_label(score):
    if score >= 90:
        return "Excellent Match", "excellent"
    if score >= 75:
        return "Strong Match", "strong"
    if score >= 60:
        return "Good Match", "good"
    if score >= 40:
        return "Partial Match", "partial"
    return "Low Match", "low"


def explain_match(result):
    bits = []
    if result["skill_score"] >= 50:
        bits.append("strong skill overlap")
    elif result["matched_skills"]:
        bits.append("some matching skills")
    if result["domain_match"]:
        bits.append("matching domain preference")
    if result["location_work_mode_match"]:
        bits.append("compatible location or work mode")
    if result["education_match"]:
        bits.append("education fits a student internship")
    if not bits:
        return "Limited overlap with this role. Review missing skills before applying."
    return "This role has " + " and ".join(bits) + "."


def compute_text_similarities(student_text, internship_texts):
    """Fit TF-IDF once on all internships, then score the student profile."""
    if not internship_texts:
        return []
    documents = [text if text.strip() else "internship" for text in internship_texts]
    profile = student_text.strip() or "student"
    vectorizer = TfidfVectorizer(stop_words="english", min_df=1)
    try:
        internship_matrix = vectorizer.fit_transform(documents)
        student_vector = vectorizer.transform([profile])
        scores = cosine_similarity(student_vector, internship_matrix).flatten()
    except ValueError:
        return [0] * len(internship_texts)
    return [int(round(float(score) * 100)) for score in scores]


def score_internship(student, internship, text_similarity_score):
    student_skills = parse_skills(student.get("skills", ""))
    intern_skills = parse_skills(internship.required_skills)
    skill_score, matched, missing = skill_match_score(student_skills, intern_skills)
    domain_score, domain_ok = domain_match_score(student.get("preferred_domain", ""), internship)
    loc_score, loc_ok = location_work_mode_score(student, internship)
    edu_score, edu_ok = education_match_score(student.get("education", ""), internship)

    final_score = round(
        (0.50 * skill_score)
        + (0.25 * text_similarity_score)
        + (0.10 * domain_score)
        + (0.10 * loc_score)
        + (0.05 * edu_score)
    )
    final_score = max(0, min(final_score, 100))

    label, score_class_name = match_label(final_score)

    result = {
        "final_score": final_score,
        "skill_score": skill_score,
        "text_similarity_score": text_similarity_score,
        "matched_skills": [display_skill(skill) for skill in matched],
        "missing_skills": [display_skill(skill) for skill in missing],
        "domain_match": domain_ok,
        "location_work_mode_match": loc_ok,
        "education_match": edu_ok,
        "label": label,
        "score_class": score_class_name,
    }
    result["why"] = explain_match(result)
    return result
