"""Role/JD interview question bank. Not the examiner, mock interview, or resume interview.

Questions are emitted only for skills found in the target role spec and/or a
pasted job description (via the existing JD analyzer). No invented technologies.
"""

from ml.jd_analyzer import analyze_job_description
from ml.prep import split_known_missing
from ml.roles import ROLE_NAMES, get_role_spec, resolve_role_name
from tools import find_skills, score_one_answer


ROLE_ALIASES = {
    "data scientist": "ML Engineer",
    "machine learning engineer": "ML Engineer",
    "ml engineer": "ML Engineer",
    "frontend": "Frontend Developer",
    "backend": "Backend Developer",
    "full stack": "Web Developer",
    "fullstack": "Web Developer",
}

# topic, category, qtype, difficulty, question, keywords, expected points, follow-up
TOPIC_BANK = {
    "sql": [
        ("technical", "conceptual", "beginner", "What is the difference between WHERE and HAVING?", ["where", "having", "group", "filter"], ["WHERE filters rows", "HAVING filters groups", "GROUP BY"], "When would you use HAVING instead of WHERE?"),
        ("technical", "conceptual", "intermediate", "Explain the difference between INNER JOIN and LEFT JOIN.", ["inner", "left", "join", "null", "match"], ["Matching rows", "Common column", "LEFT JOIN keeps unmatched left rows"], "When would you use a LEFT JOIN instead of an INNER JOIN?"),
        ("practical", "practical", "intermediate", "How would you find duplicate records in a table?", ["duplicate", "group", "count", "having"], ["GROUP BY", "COUNT > 1", "Identify the key columns"], "How would you then delete extras while keeping one row?"),
        ("practical", "problem", "advanced", "How would you speed up a slow SQL query on a large table?", ["index", "where", "join", "explain"], ["Index on filter columns", "Avoid SELECT *", "Check the join keys"], "What is an index, in simple terms?"),
        ("scenario", "scenario", "intermediate", "A report is missing rows after a JOIN. What would you check first?", ["join", "inner", "left", "null"], ["JOIN type", "NULL keys", "Filter in WHERE vs ON"], None),
    ],
    "excel": [
        ("tools", "conceptual", "beginner", "What is a Pivot Table used for?", ["pivot", "summary", "group", "chart"], ["Summarize data", "Group by fields", "Totals without formulas for every row"], "How is a Pivot Table different from a regular filter?"),
        ("practical", "practical", "intermediate", "How would you clean duplicate rows in Excel?", ["duplicate", "remove", "unique", "filter"], ["Remove Duplicates", "Check the columns used", "Keep a backup"], None),
        ("tools", "conceptual", "intermediate", "Explain VLOOKUP or XLOOKUP in simple terms.", ["lookup", "match", "column", "table"], ["Find a value in a table", "Return a related column", "Exact vs approximate match"], "What goes wrong if the lookup column is not unique?"),
    ],
    "python": [
        ("technical", "conceptual", "beginner", "What is the difference between a list and a tuple in Python?", ["list", "tuple", "mutable", "immutable"], ["List can change", "Tuple cannot", "Use case for each"], None),
        ("practical", "practical", "intermediate", "How is Pandas useful for data analysis?", ["pandas", "dataframe", "clean", "csv"], ["DataFrame as a table", "Clean and filter rows", "Read CSV or Excel"], "How would you handle missing values in a DataFrame?"),
        ("practical", "practical", "intermediate", "How would you handle missing values in a Python dataset?", ["missing", "dropna", "fillna", "null"], ["Drop or fill", "Depends on the column", "Do not guess blindly"], None),
        ("technical", "conceptual", "advanced", "How do you catch and debug errors in Python?", ["try", "except", "error", "trace"], ["try/except", "Read the traceback", "Test a small example"], None),
    ],
    "pandas": [
        ("tools", "conceptual", "beginner", "What is a Pandas DataFrame?", ["dataframe", "row", "column", "table"], ["Table of rows and columns", "Labeled axes", "Used for analysis"], None),
        ("practical", "practical", "intermediate", "How would you group and summarize a dataset with Pandas?", ["groupby", "sum", "mean", "agg"], ["groupby", "Aggregation", "Reset index if needed"], None),
        ("practical", "practical", "advanced", "How would you join two DataFrames?", ["merge", "join", "key", "how"], ["merge on a key", "left/inner how", "Check unmatched rows"], None),
    ],
    "power bi": [
        ("tools", "conceptual", "beginner", "What is the difference between a measure and a calculated column in Power BI?", ["measure", "column", "dax", "filter"], ["Measure calculates in context", "Column is stored per row", "Use measures for KPIs"], "When would a calculated column be the better choice?"),
        ("role", "role", "intermediate", "How would you design a dashboard for this role in Power BI?", ["dashboard", "visual", "filter", "kpi"], ["Few clear visuals", "Filters for the audience", "One main insight per page"], None),
        ("tools", "conceptual", "beginner", "What is a Power BI dashboard used for?", ["visual", "insight", "report", "filter"], ["Charts and KPIs", "Share insights", "Interactive filters"], None),
    ],
    "tableau": [
        ("tools", "conceptual", "beginner", "What is Tableau used for in this role?", ["visual", "chart", "dashboard", "data"], ["Interactive visuals", "Explore data", "Share a dashboard"], None),
        ("practical", "practical", "intermediate", "How would you explain a Tableau worksheet versus a dashboard?", ["worksheet", "dashboard", "visual", "filter"], ["Worksheet is one view", "Dashboard combines views", "Filters can connect them"], None),
    ],
    "statistics": [
        ("technical", "conceptual", "beginner", "What is the difference between mean, median, and mode?", ["mean", "median", "mode", "average"], ["Mean is average", "Median is middle", "Mode is most frequent"], "When is median better than mean?"),
        ("technical", "conceptual", "intermediate", "What is correlation, and why is it not the same as causation?", ["correlation", "causation", "relationship", "variable"], ["Moves together", "Does not prove cause", "Need domain context"], None),
        ("practical", "practical", "advanced", "How would you explain a simple hypothesis test to a manager?", ["hypothesis", "sample", "significant", "null"], ["Question you are testing", "Sample vs population", "Do not overclaim"], None),
    ],
    "flask": [
        ("technical", "conceptual", "beginner", "What is Flask used for in a web project?", ["python", "route", "web", "backend"], ["Python web framework", "Routes and views", "Small backends"], None),
        ("practical", "practical", "intermediate", "How does routing work in a Flask application?", ["route", "url", "function", "request"], ["URL maps to a function", "HTTP method", "Return a response"], "How would you handle a login POST route?"),
        ("role", "role", "intermediate", "Why might a backend role use Flask instead of a heavier framework?", ["simple", "lightweight", "python", "api"], ["Smaller apps", "More control", "Python ecosystem"], None),
    ],
    "django": [
        ("technical", "conceptual", "beginner", "What is an app versus a project in Django?", ["app", "project", "model", "view"], ["Project is the whole site", "App is a feature module", "Models and views live in apps"], None),
        ("tools", "conceptual", "intermediate", "What does Django's ORM help you do?", ["orm", "model", "query", "database"], ["Map tables to models", "Query without raw SQL always", "Migrations"], None),
    ],
    "html": [
        ("technical", "conceptual", "beginner", "What is the purpose of semantic HTML tags?", ["semantic", "heading", "structure", "accessible"], ["Meaning of content", "Headings and landmarks", "Easier for accessibility"], None),
        ("practical", "practical", "intermediate", "How would you structure a simple form in HTML?", ["form", "input", "label", "submit"], ["form tag", "Labeled inputs", "Submit button"], None),
    ],
    "css": [
        ("technical", "conceptual", "beginner", "How can you make a layout work on a smaller screen?", ["responsive", "media", "flex", "mobile"], ["Media queries", "Flexible layout", "Readable font size"], None),
        ("practical", "practical", "intermediate", "What is the difference between margin and padding?", ["margin", "padding", "space", "border"], ["Padding inside the box", "Margin outside", "Border in between"], None),
    ],
    "react": [
        ("tools", "conceptual", "beginner", "What is a component in React?", ["component", "ui", "props", "reuse"], ["Reusable UI piece", "Props in", "Render output"], None),
        ("practical", "practical", "intermediate", "How does state differ from props in React?", ["state", "props", "change", "parent"], ["Props come from parent", "State is local", "Updating state re-renders"], None),
    ],
    "java": [
        ("technical", "conceptual", "beginner", "What is the difference between a class and an object in Java?", ["class", "object", "instance", "method"], ["Class is the blueprint", "Object is an instance", "Methods belong to the class"], None),
        ("practical", "practical", "intermediate", "What is a common way to store a list of items in Java?", ["list", "array", "arraylist", "collection"], ["Array or ArrayList", "Index access", "Size can grow with ArrayList"], None),
    ],
    "git": [
        ("tools", "conceptual", "beginner", "What is the difference between git commit and git push?", ["commit", "push", "local", "remote"], ["Commit saves locally", "Push updates remote", "Pull brings changes down"], None),
        ("practical", "practical", "intermediate", "Why do teams use Git in this role?", ["branch", "history", "collaborate", "review"], ["History of changes", "Collaborate on branches", "Review before merge"], None),
    ],
    "machine learning": [
        ("technical", "conceptual", "beginner", "What is the difference between training data and test data?", ["train", "test", "overfit", "model"], ["Train fits the model", "Test checks unseen data", "Avoid leaking test data"], None),
        ("practical", "practical", "intermediate", "How would you evaluate a simple classification model?", ["accuracy", "metric", "test", "confusion"], ["Hold-out test set", "Accuracy or similar metric", "Look at mistakes"], "Why can accuracy be misleading on imbalanced data?"),
        ("technical", "conceptual", "advanced", "What is overfitting, and how can you reduce it?", ["overfit", "regular", "simple", "validation"], ["Fits training too closely", "Simpler model or more data", "Use validation"], None),
    ],
    "numpy": [
        ("tools", "conceptual", "beginner", "What is a NumPy array used for?", ["array", "number", "vector", "fast"], ["Numeric arrays", "Faster than plain lists for math", "Used in analysis"], None),
    ],
    "sqlite": [
        ("tools", "conceptual", "beginner", "Why might a student or small app use SQLite?", ["file", "local", "database", "simple"], ["File-based", "No separate server", "Good for small apps"], None),
        ("choice", "conceptual", "intermediate", "How is SQLite different from MySQL for this role?", ["file", "server", "local", "concurrent"], ["SQLite is local file", "MySQL is a server", "Concurrency and size limits"], None),
    ],
    "mysql": [
        ("technical", "conceptual", "beginner", "How is a MySQL table different from a spreadsheet?", ["table", "row", "key", "query"], ["Typed columns", "Keys and relations", "SQL queries"], None),
    ],
    "mongodb": [
        ("tools", "conceptual", "beginner", "How is a MongoDB document different from a SQL row?", ["document", "json", "schema", "collection"], ["JSON-like document", "Flexible fields", "Collections instead of tables"], None),
    ],
    "javascript": [
        ("technical", "conceptual", "beginner", "How does JavaScript differ from HTML and CSS on a webpage?", ["behavior", "event", "dom", "script"], ["Behavior and events", "HTML is structure", "CSS is style"], None),
        ("practical", "practical", "intermediate", "How would you validate a form with JavaScript before submit?", ["form", "validate", "event", "empty"], ["Listen to submit", "Check empty fields", "Prevent default if invalid"], None),
    ],
    "bootstrap": [
        ("tools", "conceptual", "beginner", "Why use Bootstrap instead of only custom CSS?", ["responsive", "grid", "component", "layout"], ["Ready layout grid", "Common components", "Faster responsive UI"], None),
    ],
    "ui": [
        ("role", "conceptual", "beginner", "What makes a user interface easy to use?", ["clear", "layout", "contrast", "user"], ["Clear labels", "Consistent layout", "Enough contrast"], None),
    ],
    "data analysis": [
        ("role", "role", "intermediate", "How would you clean a messy dataset before presenting insights?", ["clean", "missing", "duplicate", "outlier"], ["Check missing values", "Remove duplicates", "Confirm types"], "How would you explain one insight to a non-technical manager?"),
        ("scenario", "scenario", "intermediate", "You receive a dataset with duplicate records. What would you do?", ["duplicate", "unique", "key", "count"], ["Define the unique key", "Count duplicates", "Drop extras carefully"], None),
        ("role", "role", "advanced", "How would you decide which chart to use for a finding?", ["chart", "audience", "trend", "compare"], ["Match chart to the question", "Keep it simple", "Label axes"], None),
    ],
    "communication": [
        ("behavioral", "behavioral", "beginner", "Tell me about a time you explained a technical idea to someone non-technical.", ["simple", "example", "audience", "result"], ["Simple language", "One example", "Check they understood"], None),
        ("behavioral", "behavioral", "intermediate", "Tell me about a time you solved a difficult problem.", ["problem", "action", "result", "learn"], ["Situation", "What you did", "Result and lesson"], None),
    ],
    "testing": [
        ("practical", "practical", "intermediate", "Why do developers write tests for this kind of role?", ["test", "bug", "change", "confidence"], ["Catch regressions", "Document expected behavior", "Safer changes"], None),
    ],
}

CATEGORY_LABELS = {
    "technical": "Technical Knowledge",
    "practical": "Practical Problem Solving",
    "tools": "Tools & Technologies",
    "role": "Role-Specific Questions",
    "scenario": "Scenario-Based Questions",
    "behavioral": "Behavioral Questions",
    "jd": "Job-Description Questions",
    "followup": "Follow-Up Questions",
}


def resolve_generator_role(name):
    text = (name or "").strip()
    if not text:
        return "Software Developer"
    lowered = text.lower()
    if lowered in ROLE_ALIASES:
        return ROLE_ALIASES[lowered]
    return resolve_role_name(text)


def _norm(skill):
    return (skill or "").strip().lower()


def _list_skills(value):
    if not value or value == "Not detected":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def _topics_from_text(text):
    extras = []
    lowered = (text or "").lower()
    if "statistic" in lowered or "probability" in lowered:
        extras.append("Statistics")
    if "unit test" in lowered or "testing" in lowered:
        extras.append("Testing")
    return extras


def collect_topic_priorities(role_name, jd_result, have, missing):
    """Return ordered {skill, priority, source} only from role spec and/or JD."""
    have_set = {_norm(item) for item in have}
    missing_set = {_norm(item) for item in missing}
    topics = []
    seen = set()

    def add(skill, priority, source):
        key = _norm(skill)
        if not key or key not in TOPIC_BANK or key in seen:
            return
        seen.add(key)
        topics.append({"skill": skill, "key": key, "priority": priority, "source": source})

    if jd_result:
        required = _list_skills(jd_result.get("required_skills"))
        preferred = _list_skills(jd_result.get("preferred_skills"))
        tools = _list_skills(jd_result.get("tools"))
        for skill in required:
            add(skill, "HIGH", "jd-required")
        for skill in preferred:
            add(skill, "MEDIUM", "jd-preferred")
        for skill in tools:
            add(skill, "MEDIUM" if _norm(skill) not in {_norm(s) for s in required} else "HIGH", "jd-tool")
        for extra in _topics_from_text(
            " ".join(_list_skills(jd_result.get("keywords"))) + " " + " ".join(_list_skills(jd_result.get("responsibilities")))
        ):
            add(extra, "MEDIUM", "jd-text")
    else:
        spec = get_role_spec(role_name)
        for skill in spec["skills"]:
            if _norm(skill) in missing_set:
                add(skill, "HIGH", "role-gap")
            elif _norm(skill) in have_set:
                add(skill, "MEDIUM", "role-known")
            else:
                add(skill, "MEDIUM", "role")

    # Gaps first when personalizing, but keep required skills even if known
    topics.sort(key=lambda item: (0 if item["key"] in missing_set else 1, {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item["priority"]]))
    return topics


def _why_text(item, role_name, has_jd):
    skill = item["skill"]
    if has_jd and item["source"].startswith("jd"):
        if item["priority"] == "HIGH":
            return f"{skill} is explicitly required in the provided job description."
        if item["source"] == "jd-preferred":
            return f"{skill} is listed as a preferred skill in the job description."
        return f"{skill} appears in the job description, so interviewers may ask about it."
    if item["source"] == "role-gap":
        return f"{skill} is expected for {role_name} and is a current skill gap on your profile, so it should be high on your practice list."
    return f"{skill} is commonly used in {role_name} roles."


def generate_role_questions(
    role_name,
    student_skills="",
    jd_text="",
    student=None,
    resume_text="",
    difficulty="mixed",
    count=20,
    exclude_questions=None,
    weak_topics=None,
    quick=False,
):
    role_name = resolve_generator_role(role_name)
    count = 5 if quick else (count if count in (10, 20, 30) else 20)
    difficulty = difficulty if difficulty in ("beginner", "intermediate", "advanced", "mixed") else "mixed"
    exclude = {text.strip().lower() for text in (exclude_questions or []) if text}
    weak = {_norm(item) for item in (weak_topics or [])}

    jd_result = None
    has_jd = bool((jd_text or "").strip())
    if has_jd and student is not None:
        jd_result = analyze_job_description(student, jd_text, resume_text or "")

    have, missing, _required = split_known_missing(student_skills, role_name)
    topics = collect_topic_priorities(role_name, jd_result, have, missing)
    if weak:
        topics.sort(key=lambda item: (0 if item["key"] in weak else 1))

    pool = []
    seen_q = set(exclude)
    for topic in topics:
        for category, qtype, level, question, keywords, points, followup in TOPIC_BANK.get(topic["key"], []):
            key = question.strip().lower()
            if key in seen_q:
                continue
            if difficulty != "mixed" and level != difficulty:
                continue
            seen_q.add(key)
            pool.append(
                {
                    "question": question,
                    "topic": topic["skill"],
                    "category": category,
                    "qtype": qtype,
                    "difficulty": level,
                    "priority": topic["priority"],
                    "keywords": keywords,
                    "expected": points,
                    "why": _why_text(topic, role_name, has_jd),
                    "followup": followup,
                    "source": topic["source"],
                }
            )

    if jd_result:
        responsibilities = jd_result.get("responsibilities")
        if isinstance(responsibilities, list):
            for line in responsibilities[:3]:
                question = f"This job description includes: \"{line}\". How would you approach this in practice?"
                key = question.lower()
                if key in seen_q:
                    continue
                seen_q.add(key)
                pool.append(
                    {
                        "question": question,
                        "topic": jd_result.get("job_title") or role_name,
                        "category": "jd",
                        "qtype": "scenario",
                        "difficulty": "intermediate",
                        "priority": "HIGH",
                        "keywords": ["example", "step", "result", "tool"],
                        "expected": ["Concrete steps", "Tools you would use", "How you would check the result"],
                        "why": "This responsibility is taken from the pasted job description.",
                        "followup": "What would you do first if the data or requirements were unclear?",
                        "source": "jd-responsibility",
                    }
                )

    if quick:
        pool = [item for item in pool if item["priority"] == "HIGH"] or pool
        selected = pool[:5]
    else:
        selected = pool[:count]

    for index, item in enumerate(selected):
        item["qid"] = index

    important = []
    if jd_result:
        important = _list_skills(jd_result.get("required_skills")) or [t["skill"] for t in topics]
    else:
        important = [t["skill"] for t in topics]

    coverage = {}
    for skill in important:
        key = _norm(skill)
        hits = sum(1 for item in selected if _norm(item["topic"]) == key)
        coverage[skill] = min(100, int(round(100 * hits / 2.0))) if hits else 0
    overall = int(round(sum(coverage.values()) / len(coverage))) if coverage else 0
    missing_topics = [skill for skill, pct in coverage.items() if pct < 50]

    return {
        "role": role_name,
        "has_jd": has_jd,
        "jd_title": (jd_result or {}).get("job_title") if jd_result else "",
        "questions": selected,
        "coverage": coverage,
        "coverage_overall": overall,
        "coverage_missing": missing_topics,
        "have": have,
        "missing": missing,
        "topics": topics,
        "disclaimer": "Questions are generated from your target role and, if provided, the pasted job description. They are practice prompts, not a real company interview.",
    }


def evaluate_role_answer(question, answer):
    item = {
        "q": question.get("question", ""),
        "keywords": question.get("keywords") or ["example"],
        "topic": question.get("topic"),
        "model": "; ".join(question.get("expected") or []),
    }
    scored = score_one_answer(item, answer)
    text = (answer or "").strip()[:4000]
    words = len(text.split())
    hits = scored.get("hits") or []
    expected = question.get("expected") or []
    missing = [point for point in expected if not any(word in text.lower() for word in point.lower().split()[:2])]
    if not text:
        relevance = correctness = completeness = technical = clarity = "Needs Improvement"
    else:
        relevance = "Strong" if hits else "Moderate"
        correctness = "Strong" if scored["score"] >= 70 else ("Moderate" if scored["score"] >= 40 else "Needs Improvement")
        completeness = "Strong" if words >= 40 else ("Moderate" if words >= 18 else "Needs Improvement")
        technical = "Strong" if len(hits) >= 2 else ("Moderate" if hits else "Needs Improvement")
        clarity = "Strong" if words >= 20 else "Needs Improvement"
    right = [f"You mentioned: {', '.join(hits)}."] if hits else ["You attempted an answer. Add the expected concepts next time."]
    if words >= 25:
        right.append("You wrote enough to start a real interview answer.")
    improve = []
    if missing:
        improve.append("Cover: " + "; ".join(missing[:3]) + ".")
    if words < 40:
        improve.append("Add a short example from study or a project.")
    improve.append("This is an AI-estimated answer evaluation, not a perfect score.")
    followup = None
    if text and (scored["score"] < 75 or words < 30) and question.get("followup"):
        followup = {
            "question": question["followup"],
            "topic": question.get("topic"),
            "category": "followup",
            "qtype": "followup",
            "difficulty": question.get("difficulty") or "intermediate",
            "priority": question.get("priority") or "MEDIUM",
            "keywords": question.get("keywords") or ["example"],
            "expected": ["Build on your last answer", "Give a concrete case"],
            "why": "This follow-up is based on the previous question so you can go one level deeper.",
            "followup": None,
            "source": "followup",
            "is_followup": True,
        }
    return {
        "score": scored.get("score", 0),
        "relevance": relevance,
        "correctness": correctness,
        "completeness": completeness,
        "technical": technical,
        "clarity": clarity,
        "right": right,
        "missing": missing or ["No major expected point was flagged, but you can still add an example."],
        "improve": improve,
        "expected": expected,
        "skipped": not bool(text),
        "answer": text,
        "question": question.get("question", ""),
        "topic": question.get("topic") or scored.get("topic") or "Technical",
        "followup": followup,
        "disclaimer": "AI-estimated answer evaluation. Keyword overlap is used; exact wording is not required.",
    }


def topic_performance(answers):
    buckets = {}
    for item in answers or []:
        if item.get("skipped"):
            continue
        topic = item.get("topic") or "Technical"
        buckets.setdefault(topic, []).append(int(item.get("score") or 0))
    stats = {topic: int(round(sum(scores) / len(scores))) for topic, scores in buckets.items() if scores}
    if not stats:
        return {"scores": {}, "weakest": None, "weak_topics": []}
    weakest = min(stats, key=stats.get)
    weak_topics = [topic for topic, score in stats.items() if score < 70]
    return {"scores": stats, "weakest": weakest, "weak_topics": weak_topics}


def summarize_user_practice(sets):
    practiced = 0
    scores = []
    topic_scores = {}
    for record in sets or []:
        payload = record.result() if hasattr(record, "result") else record
        for item in payload.get("answers") or []:
            if item.get("skipped"):
                continue
            practiced += 1
            score = int(item.get("score") or 0)
            scores.append(score)
            topic = item.get("topic") or "Technical"
            topic_scores.setdefault(topic, []).append(score)
    if not practiced:
        return {"practiced": 0, "average": None, "weakest": None}
    averages = {topic: int(round(sum(vals) / len(vals))) for topic, vals in topic_scores.items()}
    weakest = min(averages, key=averages.get) if averages else None
    return {
        "practiced": practiced,
        "average": int(round(sum(scores) / len(scores))),
        "weakest": weakest,
        "topics": averages,
    }
