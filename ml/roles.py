"""Target career roles used instead of internship listings.

Student profile text is still compared with TF-IDF, cosine similarity,
skill overlap, and the local MLP. The internship object is replaced by a
role profile with required skills and a short description.
"""

TARGET_ROLES = {
    "Data Analyst": {
        "skills": ["Python", "SQL", "Excel", "Pandas", "Power BI", "Tableau", "Statistics", "Data Analysis"],
        "exam_domain": "Data Analysis",
        "description": (
            "Domain: Data Analysis. A data analyst cleans datasets, writes SQL, "
            "builds Excel or Power BI reports, and explains insights clearly."
        ),
    },
    "Software Developer": {
        "skills": ["Python", "Java", "SQL", "Git", "HTML", "CSS", "Testing"],
        "exam_domain": "Web Development",
        "description": (
            "Domain: Software Development. A software developer writes reliable code, "
            "uses Git, tests features, and works with databases."
        ),
    },
    "Web Developer": {
        "skills": ["HTML", "CSS", "JavaScript", "Python", "Flask", "Git", "Bootstrap"],
        "exam_domain": "Web Development",
        "description": (
            "Domain: Web Development. A web developer builds pages with HTML, CSS, "
            "and JavaScript and can add a Flask backend."
        ),
    },
    "Python Developer": {
        "skills": ["Python", "Flask", "SQL", "Git", "Pandas", "Testing"],
        "exam_domain": "Web Development",
        "description": (
            "Domain: Python Development. A Python developer writes scripts and web "
            "backends, works with SQL, and documents code on GitHub."
        ),
    },
    "ML Engineer": {
        "skills": ["Python", "Machine Learning", "Pandas", "NumPy", "SQL", "Git"],
        "exam_domain": "Data Analysis",
        "description": (
            "Domain: Machine Learning. An ML engineer prepares data, trains beginner "
            "models, and evaluates accuracy with Python."
        ),
    },
    "Java Developer": {
        "skills": ["Java", "SQL", "Git", "HTML", "Testing"],
        "exam_domain": "Android Development",
        "description": (
            "Domain: Java Development. A Java developer writes object-oriented code, "
            "uses Git, and works with databases."
        ),
    },
    "Frontend Developer": {
        "skills": ["HTML", "CSS", "JavaScript", "Bootstrap", "Git", "UI"],
        "exam_domain": "Web Development",
        "description": (
            "Domain: Web Development. A frontend developer builds responsive interfaces "
            "with HTML, CSS, and JavaScript."
        ),
    },
    "Backend Developer": {
        "skills": ["Python", "Flask", "SQL", "Git", "SQLite", "Testing"],
        "exam_domain": "Web Development",
        "description": (
            "Domain: Web Development. A backend developer designs routes, stores data, "
            "and keeps APIs reliable."
        ),
    },
}

ROLE_NAMES = list(TARGET_ROLES.keys())


class RoleTarget:
    """Looks like an Internship to the existing matcher, but represents a career role."""

    def __init__(self, name, spec=None):
        spec = spec or get_role_spec(name)
        self.title = name
        self.company = "Target Role"
        self.description = spec["description"]
        self.required_skills = ", ".join(spec["skills"])
        self.location = ""
        self.work_mode = ""
        self.skills = spec["skills"]
        self.exam_domain = spec["exam_domain"]


def get_role_spec(name):
    if name in TARGET_ROLES:
        return TARGET_ROLES[name]
    custom = (name or "").strip() or "Software Developer"
    return {
        "skills": TARGET_ROLES["Software Developer"]["skills"],
        "exam_domain": "Web Development",
        "description": (
            f"Domain: {custom}. A professional in this role needs core programming, "
            "problem solving, SQL, Git, and clear communication."
        ),
    }


def resolve_role_name(name):
    text = (name or "").strip()
    if not text:
        return "Software Developer"
    for official in ROLE_NAMES:
        if official.lower() == text.lower():
            return official
    return text
