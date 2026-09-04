"""Resume-grounded interview questions. Not a generic examiner bank.

Every question includes a `source` snippet copied from the resume or listed
skills. Templates fire only when that skill/project/claim is present.
This is practice feedback, not a perfect interview judgement.
"""

import re

from ml.resume_fixer import parse_resume_fields, stored_resume_text
from ml.roles import resolve_role_name
from tools import score_one_answer


SKILL_TEMPLATES = {
    "flask": [
        ("beginner", "technical", "You listed Flask. What is Flask used for in a web project?", ["python", "web", "route", "backend"]),
        ("intermediate", "choice", "Why did you choose Flask for the application on your resume?", ["simple", "lightweight", "python", "route"]),
        ("advanced", "implementation", "How is routing or authentication handled in your Flask application?", ["route", "login", "session", "database"]),
        ("advanced", "choice", "Why did you use Flask instead of Django, if you considered both?", ["lightweight", "django", "simple", "control"]),
    ],
    "python": [
        ("beginner", "technical", "You listed Python. What is the difference between a list and a tuple?", ["list", "tuple", "mutable", "immutable"]),
        ("intermediate", "claim", "You mention Python on your resume. Which Python concepts have you used in your projects?", ["class", "function", "library", "project"]),
        ("advanced", "depth", "How have you handled errors or testing in your Python work?", ["try", "except", "test", "debug"]),
    ],
    "sql": [
        ("beginner", "technical", "You listed SQL. What is the difference between INNER JOIN and LEFT JOIN?", ["join", "table", "null", "match"]),
        ("intermediate", "implementation", "How did you use SQL in the work described on your resume?", ["query", "table", "database", "filter"]),
        ("advanced", "depth", "How would you speed up a slow SQL query on a large table?", ["index", "join", "filter", "explain"]),
    ],
    "django": [
        ("beginner", "technical", "You listed Django. What is an app versus a project in Django?", ["app", "project", "model", "view"]),
        ("intermediate", "choice", "Why did you choose Django for this work?", ["admin", "orm", "built-in", "security"]),
    ],
    "react": [
        ("beginner", "technical", "You listed React. What is a component in React?", ["component", "ui", "state", "props"]),
        ("intermediate", "implementation", "How did you manage state in your React work?", ["state", "props", "hook", "component"]),
    ],
    "javascript": [
        ("beginner", "technical", "You listed JavaScript. How does it differ from HTML and CSS in a webpage?", ["behavior", "structure", "style", "event"]),
        ("intermediate", "implementation", "How did you use JavaScript in the project on your resume?", ["event", "form", "dom", "function"]),
    ],
    "html": [
        ("beginner", "technical", "You listed HTML. What is the purpose of semantic HTML tags?", ["structure", "heading", "form", "accessible"]),
    ],
    "css": [
        ("beginner", "technical", "You listed CSS. How can you make a layout work on a smaller screen?", ["responsive", "flex", "media", "mobile"]),
    ],
    "java": [
        ("beginner", "technical", "You listed Java. What is the difference between a class and an object?", ["class", "object", "method", "instance"]),
        ("intermediate", "implementation", "How did you use Java in the work on your resume?", ["class", "method", "project", "example"]),
    ],
    "pandas": [
        ("beginner", "technical", "You listed Pandas. What is a DataFrame?", ["table", "row", "column", "data"]),
        ("intermediate", "implementation", "How did you clean or transform data with Pandas in your work?", ["missing", "filter", "group", "csv"]),
    ],
    "excel": [
        ("beginner", "technical", "You listed Excel. What is a pivot table used for?", ["summary", "filter", "chart", "data"]),
    ],
    "power bi": [
        ("beginner", "technical", "You listed Power BI. What is a dashboard used for?", ["chart", "visual", "insight", "report"]),
        ("intermediate", "implementation", "How would you explain a Power BI report you built or studied?", ["visual", "filter", "measure", "data"]),
    ],
    "machine learning": [
        ("beginner", "technical", "You mentioned machine learning. What is the difference between training and testing data?", ["train", "test", "model", "overfit"]),
        ("advanced", "depth", "If you used a model on your resume, how did you evaluate it?", ["accuracy", "metric", "overfit", "test"]),
    ],
    "git": [
        ("beginner", "technical", "You listed Git. What is the difference between commit and push?", ["commit", "push", "local", "remote"]),
    ],
    "github": [
        ("beginner", "technical", "You listed GitHub. How do you share a project so others can understand it?", ["readme", "commit", "repository", "clone"]),
    ],
    "sqlite": [
        ("beginner", "technical", "You listed SQLite. Why might a student project use SQLite?", ["local", "file", "database", "simple"]),
        ("intermediate", "choice", "Why did you choose SQLite for the database work on your resume?", ["simple", "file", "local", "database"]),
    ],
    "mysql": [
        ("beginner", "technical", "You listed MySQL. How is a relational table different from a spreadsheet?", ["table", "row", "key", "query"]),
    ],
    "mongodb": [
        ("beginner", "technical", "You listed MongoDB. How is a document store different from a SQL table?", ["document", "collection", "json", "schema"]),
    ],
    "numpy": [
        ("beginner", "technical", "You listed NumPy. What is a NumPy array used for?", ["array", "number", "vector", "data"]),
    ],
    "bootstrap": [
        ("beginner", "technical", "You listed Bootstrap. Why use a CSS framework instead of only custom CSS?", ["responsive", "grid", "component", "layout"]),
    ],
}

ALGO_HINTS = (
    ("random forest", "Why did you choose Random Forest?", "What other algorithms did you consider besides Random Forest?", "How did you handle overfitting if you used Random Forest?"),
    ("logistic regression", "Why did you choose logistic regression?", "How did you evaluate the logistic regression model?", "What features did you use?"),
    ("linear regression", "What problem were you solving with linear regression?", "How did you evaluate the regression model?", "What would you try if the fit was poor?"),
    ("k-means", "Why did you choose K-means?", "How did you choose the number of clusters?", "How did you evaluate the clustering?"),
    ("esp32", "Why did you choose ESP32 for this project?", "How did the ESP32 communicate with the rest of the system?", "What hardware limits did you hit?"),
)

GENERIC_ANSWER_PHRASES = (
    "it is simple",
    "it is easy",
    "i like it",
    "because it is simple",
    "because it's simple",
    "is simple",
    "it's simple",
    "i don't know",
    "i do not know",
    "not sure",
)

CATEGORY_LABELS = {
    "project": "Project",
    "technical": "Technical Skill",
    "choice": "Technology Choice",
    "implementation": "Implementation",
    "depth": "Depth",
    "claim": "Resume Claim",
    "followup": "Follow-up",
}


def _clip(text, limit=120):
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _mentioned(term, text):
    """Require the claim to appear in resume text (word-boundary when possible)."""
    needle = (term or "").strip().lower()
    blob = (text or "").lower()
    if not needle or not blob:
        return False
    if needle in blob:
        if len(needle) <= 2:
            return bool(re.search(r"(?<![a-z0-9+])" + re.escape(needle) + r"(?![a-z0-9+])", blob))
        return True
    return False


def extract_resume_claims(user, resume_text=""):
    """Facts from stored/pasted resume text only. Profile skills are not mixed in."""
    text = (resume_text or stored_resume_text(user) or "").strip()
    parsed = parse_resume_fields(text, user=None)
    skills = []
    for item in parsed.get("skills") or []:
        if item and _mentioned(item, text):
            skills.append(item)
    projects = [item for item in (parsed.get("projects") or []) if item]
    return {
        "text": text,
        "skills": skills,
        "projects": projects,
        "education": [item for item in (parsed.get("education") or []) if item],
        "experience": [item for item in (parsed.get("experience") or []) if item],
        "certifications": [item for item in (parsed.get("certifications") or []) if item],
    }


def build_hotspots(claims, target_role=""):
    hotspots = []
    for project in claims["projects"][:3]:
        hotspots.append(
            {
                "title": _clip(project, 70),
                "why": "Interviewers often ask you to walk through a listed project: problem, tools, and what you learned.",
            }
        )
    for skill in claims["skills"][:6]:
        hotspots.append(
            {
                "title": skill,
                "why": f"Your resume lists {skill}, so you should be ready to explain how you used it, not only that you know the name.",
            }
        )
    for needle, _q1, _q2, _q3 in ALGO_HINTS:
        if _mentioned(needle, claims["text"]):
            hotspots.append(
                {
                    "title": needle.title(),
                    "why": f"Your resume mentions {needle}, so be ready to explain the choice, how you used it, and how you checked the result.",
                }
            )
            break
    seen = set()
    unique = []
    for item in hotspots:
        key = item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:8]


def _source_in_claims(source, claims):
    src = (source or "").strip()
    if not src:
        return False
    if _mentioned(src, claims["text"]):
        return True
    lowered = src.lower()
    for project in claims["projects"]:
        if lowered in project.lower() or project.lower() in lowered:
            return True
    for skill in claims["skills"]:
        if lowered == skill.lower() or lowered in skill.lower():
            return True
    for bucket in ("education", "experience", "certifications"):
        for item in claims.get(bucket) or []:
            if lowered in item.lower() or item.lower() in lowered:
                return True
    return False


def _add_question(bucket, seen, claims, category, difficulty, question, source, keywords):
    key = question.strip().lower()
    if not _source_in_claims(source, claims) or key in seen:
        return
    seen.add(key)
    bucket.append(
        {
            "category": category,
            "difficulty": difficulty,
            "question": question,
            "source": _clip(source, 160),
            "keywords": keywords,
            "is_followup": False,
        }
    )


def _role_bridge_question(project, role):
    snippet = _clip(project, 70)
    lowered = project.lower()
    role_l = (role or "").lower()
    if any(token in role_l for token in ("analyst", "data")) and any(
        token in lowered for token in ("data", "sensor", "csv", "sql", "excel", "dashboard", "ml", "model")
    ):
        return (
            f"Your project collects or uses data in \"{snippet}\". "
            f"How would you clean and analyze that data before presenting insights for a {role} role?"
        )
    if any(token in role_l for token in ("web", "developer", "software", "python")) and any(
        token in lowered for token in ("web", "flask", "django", "html", "app", "website", "api")
    ):
        return f"How would you explain the technical parts of \"{snippet}\" in a {role} interview?"
    return f"Your target role is {role}. How would the work in \"{snippet}\" help you in that role?"


def generate_questions(claims, target_role="", difficulty="mixed", count=10):
    """Build questions only from claims found in the resume."""
    count = 5 if count not in (5, 10, 15) else count
    difficulty = difficulty if difficulty in ("beginner", "intermediate", "advanced", "mixed") else "mixed"
    role = resolve_role_name(target_role) if target_role else ""
    text = claims.get("text") or ""
    skill_keys = {skill.lower(): skill for skill in claims.get("skills") or []}
    questions = []
    seen = set()

    for project in claims.get("projects") or []:
        snippet = _clip(project, 90)
        _add_question(
            questions,
            seen,
            claims,
            "project",
            "beginner",
            f"You mentioned this on your resume: \"{snippet}\". What problem were you solving?",
            project,
            ["problem", "built", "project", "learn"],
        )
        _add_question(
            questions,
            seen,
            claims,
            "project",
            "intermediate",
            f"What challenges did you face while building \"{snippet}\"?",
            project,
            ["challenge", "debug", "fix", "learn"],
        )
        _add_question(
            questions,
            seen,
            claims,
            "implementation",
            "intermediate",
            f"Explain the architecture or main parts of \"{snippet}\".",
            project,
            ["part", "database", "frontend", "backend", "flow"],
        )
        _add_question(
            questions,
            seen,
            claims,
            "depth",
            "advanced",
            f"If you rebuilt \"{snippet}\", what would you change and why?",
            project,
            ["improve", "change", "learn", "tradeoff"],
        )
        if role:
            _add_question(
                questions,
                seen,
                claims,
                "project",
                "advanced",
                _role_bridge_question(project, role),
                project,
                ["skill", "example", "project", role.split()[0].lower()],
            )

    for key, label in skill_keys.items():
        for level, category, prompt, keywords in SKILL_TEMPLATES.get(key, []):
            _add_question(questions, seen, claims, category, level, prompt, label, keywords)
        if key not in SKILL_TEMPLATES:
            _add_question(
                questions,
                seen,
                claims,
                "technical",
                "intermediate",
                f"You listed {label}. How have you used {label} in a project on your resume?",
                label,
                [key, "project", "used", "example"],
            )

    for needle, beginner_q, mid_q, adv_q in ALGO_HINTS:
        if not _mentioned(needle, text):
            continue
        _add_question(questions, seen, claims, "depth", "beginner", beginner_q, needle, [needle.split()[0], "choose", "why"])
        _add_question(questions, seen, claims, "depth", "intermediate", mid_q, needle, ["evaluate", "metric", "compare"])
        _add_question(questions, seen, claims, "depth", "advanced", adv_q, needle, ["overfit", "alternative", "feature"])

    if claims.get("education"):
        edu = claims["education"][0]
        _add_question(
            questions,
            seen,
            claims,
            "claim",
            "beginner",
            f"Your resume includes \"{_clip(edu, 80)}\". Which coursework or lab work is most relevant to the role you want?",
            edu,
            ["course", "project", "learn", "skill"],
        )
    if claims.get("experience"):
        exp = claims["experience"][0]
        _add_question(
            questions,
            seen,
            claims,
            "claim",
            "intermediate",
            f"You listed \"{_clip(exp, 80)}\". What did you actually do, and what was the result?",
            exp,
            ["did", "result", "learn", "example"],
        )
    if claims.get("certifications"):
        cert = claims["certifications"][0]
        _add_question(
            questions,
            seen,
            claims,
            "claim",
            "intermediate",
            f"Your resume lists \"{_clip(cert, 80)}\". What from that certification have you applied in a project?",
            cert,
            ["learn", "skill", "project", "apply"],
        )

    if difficulty != "mixed":
        filtered = [item for item in questions if item["difficulty"] == difficulty]
        if filtered:
            questions = filtered
    else:
        by_level = {"beginner": [], "intermediate": [], "advanced": []}
        leftover = []
        for item in questions:
            by_level.get(item["difficulty"], leftover).append(item)
        mixed = []
        while len(mixed) < count and (by_level["beginner"] or by_level["intermediate"] or by_level["advanced"] or leftover):
            for level in ("beginner", "intermediate", "advanced"):
                if by_level[level] and len(mixed) < count:
                    mixed.append(by_level[level].pop(0))
            if leftover and len(mixed) < count:
                mixed.append(leftover.pop(0))
            if not (by_level["beginner"] or by_level["intermediate"] or by_level["advanced"] or leftover):
                break
        questions = mixed or questions

    selected = questions[:count]
    for index, item in enumerate(selected, start=1):
        item["index"] = index
        item["total"] = len(selected)
    return selected


def build_followup(question, answer):
    """One follow-up tied to the student's answer. None if the answer is already detailed."""
    if question.get("is_followup"):
        return None
    text = " ".join((answer or "").split())
    words = text.split()
    if len(words) < 4:
        return None
    source = question.get("source") or "that resume item"
    lowered = text.lower()
    if any(phrase in lowered for phrase in GENERIC_ANSWER_PHRASES):
        prompt = f"You said this choice was simple. What advantages did it provide in {source}?"
    elif len(words) < 40:
        snippet = _clip(text, 70)
        prompt = f"You mentioned \"{snippet}\". Can you walk through one concrete example from {source}?"
    else:
        return None
    return {
        "category": "followup",
        "difficulty": question.get("difficulty") or "intermediate",
        "question": prompt,
        "source": source,
        "keywords": ["example", "project", "because"] + list(question.get("keywords") or [])[:2],
        "is_followup": True,
    }


def evaluate_resume_answer(question, answer):
    """Keyword/length feedback. Not a pass/fail interview verdict."""
    item = {
        "q": question.get("question", ""),
        "keywords": question.get("keywords") or ["example", "project"],
    }
    scored = score_one_answer(item, answer)
    text = (answer or "").strip()
    words = len(text.split())
    hits = [word for word in item["keywords"] if word in text.lower()]
    skipped = not bool(text)
    if skipped or words < 12:
        relevance, depth, completeness = "Needs Improvement", "Needs Improvement", "Needs Improvement"
    else:
        relevance = "Strong" if hits else "Moderate"
        depth = "Strong" if len(hits) >= 2 and words >= 40 else "Moderate"
        completeness = "Strong" if words >= 50 else "Needs Improvement"
    well = []
    add = []
    if hits:
        well.append("You mentioned: " + ", ".join(hits) + ".")
    if words >= 30:
        well.append("You gave enough length to start a real interview answer.")
    if not well:
        well.append("You attempted the question. Add a concrete example from your resume next time.")
    if words < 40:
        add.append("Add a specific example from the resume item: " + (question.get("source") or "your project") + ".")
    missing_kw = [word for word in item["keywords"] if word not in text.lower()]
    if missing_kw:
        add.append("You could mention: " + ", ".join(missing_kw[:3]) + ".")
    add.append("This feedback is a practice hint. It cannot perfectly judge an interview answer.")
    followup = None if skipped else build_followup(question, text)
    return {
        "score": scored.get("score", 0),
        "relevance": relevance,
        "technical_depth": depth,
        "completeness": completeness,
        "well": well,
        "add": add,
        "ready": [
            "Be ready to explain the tools named in: " + (question.get("source") or "your resume claim") + ".",
            "Have one challenge and one result ready for this item.",
        ],
        "followup": followup,
        "skipped": skipped,
        "answer": text,
        "question": question.get("question", ""),
        "category": question.get("category", ""),
        "source": question.get("source", ""),
    }


def build_report(questions, answers, claims):
    strong, review, practice = [], [], []
    weak_topics = []
    for question, result in zip(questions, answers):
        if result.get("skipped"):
            review.append(question.get("source") or question["question"][:40])
            practice.append(question["question"])
            continue
        depth = result.get("technical_depth")
        if depth == "Strong":
            strong.append(question.get("source") or question["category"])
        elif depth == "Needs Improvement":
            review.append(question.get("source") or question["category"])
            practice.append(question["question"])
            weak_topics.append((question.get("source") or "").lower())
    alerts = []
    for skill in claims.get("skills") or []:
        key = skill.lower()
        if key in {"python", "machine learning", "sql", "flask", "java"} and any(
            key in topic for topic in weak_topics
        ):
            alerts.append(
                f"Your resume highlights {skill} strongly. Some of your answers suggest that {skill} concepts may need additional preparation."
            )
    return {
        "completed": len(answers),
        "strong": list(dict.fromkeys(strong))[:5] or ["Keep practicing with examples from your resume."],
        "review": list(dict.fromkeys(review))[:5] or ["No major review items were flagged from this session."],
        "practice": practice[:6],
        "alerts": alerts,
        "disclaimer": "This report is practice feedback from keyword and completeness checks. It is not a real interview score.",
    }
