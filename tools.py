"""Local helper tools for InternMatch AI. No cloud APIs are used."""

KNOWN_SKILLS = [
    "python", "java", "c++", "c", "html", "css", "javascript", "react",
    "node", "flask", "django", "sql", "mysql", "sqlite", "mongodb",
    "excel", "power bi", "tableau", "pandas", "numpy", "machine learning",
    "figma", "ui", "ux", "git", "github", "android", "kotlin", "php",
    "bootstrap", "communication", "leadership", "data analysis",
]


DOMAINS = [
    "Web Development",
    "Data Analysis",
    "UI/UX Design",
    "Cybersecurity",
    "Android Development",
]


CAREER_ROADMAPS = {
    "Web Development": [
        {"level": "Foundation", "title": "Learn the web basics", "skills": ["HTML", "CSS", "JavaScript"], "goal": "Build 2 static website pages."},
        {"level": "Backend", "title": "Add a Python backend", "skills": ["Python", "Flask", "SQLite"], "goal": "Create a login form that stores users locally."},
        {"level": "Projects", "title": "Make internship-ready projects", "skills": ["Git", "GitHub", "Bootstrap"], "goal": "Put 3 projects on GitHub with README files."},
        {"level": "Internship", "title": "Apply with a focused profile", "skills": ["Communication", "SQL"], "goal": "Apply to web internships that match your stack."},
    ],
    "Data Analysis": [
        {"level": "Foundation", "title": "Get comfortable with data", "skills": ["Excel", "Python"], "goal": "Clean a small CSV file and make a chart."},
        {"level": "Analysis", "title": "Learn analysis tools", "skills": ["SQL", "Pandas", "NumPy"], "goal": "Write queries and summarize a dataset."},
        {"level": "Visuals", "title": "Show insights clearly", "skills": ["Power BI", "Tableau"], "goal": "Build one dashboard with 4 visuals."},
        {"level": "Internship", "title": "Apply to analyst internships", "skills": ["Communication", "Data Analysis"], "goal": "Share a short case-study of your dashboard."},
    ],
    "UI/UX Design": [
        {"level": "Foundation", "title": "Learn design basics", "skills": ["UI", "UX"], "goal": "Study layout, color, and typography."},
        {"level": "Tools", "title": "Practice in Figma", "skills": ["Figma"], "goal": "Redesign one student website screen."},
        {"level": "Portfolio", "title": "Build a case study", "skills": ["Communication"], "goal": "Write problem, process, and final screens."},
        {"level": "Internship", "title": "Apply to design internships", "skills": ["UI", "UX", "Figma"], "goal": "Share 2 case studies with your resume."},
    ],
    "Cybersecurity": [
        {"level": "Foundation", "title": "Learn security basics", "skills": ["Networking basics", "Linux"], "goal": "Understand threats, passwords, and safe browsing."},
        {"level": "Practice", "title": "Try beginner labs", "skills": ["Python"], "goal": "Complete a beginner TryHackMe-style learning path locally documented."},
        {"level": "Projects", "title": "Show practical awareness", "skills": ["Communication"], "goal": "Write a short report on common internship scams."},
        {"level": "Internship", "title": "Apply to SOC/security intern roles", "skills": ["Python", "Linux"], "goal": "Highlight labs and documentation, not hacking claims."},
    ],
    "Android Development": [
        {"level": "Foundation", "title": "Learn app basics", "skills": ["Java", "Kotlin", "XML"], "goal": "Build a simple calculator or notes app."},
        {"level": "Storage", "title": "Save user data", "skills": ["SQLite", "Git"], "goal": "Add local storage and a clean UI."},
        {"level": "Projects", "title": "Publish a mini app", "skills": ["Android", "GitHub"], "goal": "Share screenshots and source code."},
        {"level": "Internship", "title": "Apply to Android internships", "skills": ["Kotlin", "Java"], "goal": "Show 2 apps and what you learned."},
    ],
}


INTERVIEW_BANK = {
    "Web Development": [
        {"q": "What is the difference between HTML, CSS, and JavaScript?", "keywords": ["structure", "style", "behavior", "html", "css", "javascript"], "model": "HTML gives structure, CSS styles the page, and JavaScript adds behavior such as clicks and forms."},
        {"q": "What is a form POST request used for?", "keywords": ["submit", "data", "server", "password", "secure"], "model": "POST sends form data to the server, which is useful for login details and other information that should not sit in the URL."},
        {"q": "How do you make a website look good on mobile?", "keywords": ["responsive", "media", "viewport", "flex", "grid"], "model": "Use a viewport meta tag, responsive CSS, and flex or grid layouts so the page adapts to smaller screens."},
        {"q": "What is Flask used for?", "keywords": ["python", "web", "routes", "backend", "server"], "model": "Flask is a Python web framework used to create routes, pages, and a simple backend for a website."},
        {"q": "Tell me about a project you would mention in an internship interview.", "keywords": ["project", "python", "html", "problem", "learn"], "model": "Mention a real project, the problem it solved, the tools you used, and one thing you learned."},
    ],
    "Data Analysis": [
        {"q": "What is data cleaning?", "keywords": ["missing", "duplicate", "error", "clean", "format"], "model": "Data cleaning means fixing missing values, duplicates, and wrong formats so the analysis is trustworthy."},
        {"q": "What is the difference between a row and a column in a dataset?", "keywords": ["record", "field", "row", "column", "variable"], "model": "A row is one record, and a column is one field or variable such as name, marks, or date."},
        {"q": "Why is SQL useful for internships?", "keywords": ["database", "query", "table", "filter", "join"], "model": "SQL helps you query tables, filter records, and join data stored in a database."},
        {"q": "What is a dashboard?", "keywords": ["chart", "insight", "visual", "kpi", "report"], "model": "A dashboard is a visual report with charts and KPIs that helps people understand insights quickly."},
        {"q": "How do you explain findings to a non-technical manager?", "keywords": ["simple", "insight", "story", "action", "clear"], "model": "Use simple language, one clear insight, and one recommended action instead of heavy technical terms."},
    ],
    "UI/UX Design": [
        {"q": "What is the difference between UI and UX?", "keywords": ["interface", "experience", "look", "feel", "user"], "model": "UI is how the product looks, and UX is how easy and useful the experience feels for the user."},
        {"q": "What is a wireframe?", "keywords": ["layout", "sketch", "structure", "screen", "simple"], "model": "A wireframe is a simple layout sketch that shows screen structure before final colors and visuals."},
        {"q": "Why is contrast important in design?", "keywords": ["readable", "accessibility", "color", "text", "clear"], "model": "Good contrast makes text readable and improves accessibility for more users."},
        {"q": "How do you collect user feedback?", "keywords": ["interview", "survey", "test", "user", "observe"], "model": "You can use user interviews, surveys, and simple usability tests to see what people struggle with."},
        {"q": "What makes a student internship portfolio strong?", "keywords": ["case", "process", "problem", "solution", "figma"], "model": "A strong portfolio shows the problem, your process, and the final solution, not only pretty screens."},
    ],
    "Cybersecurity": [
        {"q": "What is phishing?", "keywords": ["fake", "email", "password", "link", "scam"], "model": "Phishing is a fake message or link used to steal passwords or personal information."},
        {"q": "Why should passwords be hashed?", "keywords": ["hash", "plain", "steal", "database", "secure"], "model": "Hashing stores passwords in a protected form so attackers cannot easily read them if a database is stolen."},
        {"q": "What is a strong password practice?", "keywords": ["long", "unique", "manager", "2fa", "not reuse"], "model": "Use a long unique password, do not reuse it, and add 2FA where possible."},
        {"q": "What is the first thing to check in a suspicious internship offer?", "keywords": ["company", "fee", "payment", "email", "scam"], "model": "Check the company name, official email, and whether anyone is asking for a fee or payment."},
        {"q": "What is confidentiality?", "keywords": ["private", "data", "permission", "secret", "protect"], "model": "Confidentiality means protecting private data and sharing it only with permission."},
    ],
    "Android Development": [
        {"q": "What is an Activity in Android?", "keywords": ["screen", "ui", "activity", "app", "page"], "model": "An Activity is one screen in an Android app where the user sees and uses the UI."},
        {"q": "Why do apps need permissions?", "keywords": ["camera", "storage", "privacy", "user", "access"], "model": "Permissions protect privacy by asking the user before the app uses the camera, storage, or similar features."},
        {"q": "What is the use of XML in Android?", "keywords": ["layout", "ui", "design", "view", "xml"], "model": "XML is used to design Android layouts and arrange views on the screen."},
        {"q": "How can you store data locally in an app?", "keywords": ["sqlite", "shared", "local", "database", "file"], "model": "You can store data locally with SQLite, SharedPreferences, or files on the device."},
        {"q": "What should a beginner Android internship project include?", "keywords": ["ui", "storage", "github", "readme", "feature"], "model": "Include a clear UI, local storage, GitHub code, and a README that explains one useful feature."},
    ],
}


PROJECT_CATALOG = [
    {"title": "Student Internship Portal", "domain": "Web Development", "level": "Intermediate", "skills": ["HTML", "CSS", "Python", "Flask", "SQLite"], "why": "Shows full-stack thinking and is perfect for BCA."},
    {"title": "Personal Portfolio Website", "domain": "Web Development", "level": "Beginner", "skills": ["HTML", "CSS", "JavaScript"], "why": "A must-have when you start interview conversations."},
    {"title": "Campus Event Dashboard", "domain": "Data Analysis", "level": "Beginner", "skills": ["Excel", "Python"], "why": "Proves you can clean data and present insights."},
    {"title": "Placement Statistics Analyzer", "domain": "Data Analysis", "level": "Intermediate", "skills": ["Python", "Pandas", "SQL"], "why": "Looks practical and college-relevant."},
    {"title": "Internship App Redesign", "domain": "UI/UX Design", "level": "Beginner", "skills": ["Figma", "UI", "UX"], "why": "A strong case study for design interviews."},
    {"title": "Student Attendance Mobile App", "domain": "Android Development", "level": "Intermediate", "skills": ["Java", "Kotlin", "SQLite"], "why": "Shows UI plus local storage skills."},
    {"title": "Internship Scam Awareness Page", "domain": "Cybersecurity", "level": "Beginner", "skills": ["HTML", "CSS", "Communication"], "why": "Combines security awareness with a useful student topic."},
    {"title": "Resume Keyword Checker", "domain": "Web Development", "level": "Intermediate", "skills": ["Python", "Flask", "HTML"], "why": "Connects directly to InternMatch AI and your resume tool."},
]


SCAM_RED_FLAGS = [
    ("registration fee", 25, "Asking for a registration or application fee is a major red flag."),
    ("processing fee", 25, "Processing fees are common in internship scams."),
    ("pay to join", 25, "Real internships do not ask you to pay to join."),
    ("whatsapp only", 15, "Contact through WhatsApp only, with no official email, is suspicious."),
    ("send money", 30, "Any request to send money is unsafe."),
    ("bank details", 20, "Do not share bank details for an internship offer."),
    ("upi", 15, "UPI or payment requests in internship chats are risky."),
    ("urgent joining", 10, "Fake urgency is used to stop you from checking the company."),
    ("work from home easy money", 20, "Promises of easy money are often scams."),
    ("laptop after payment", 30, "Paying first to receive a laptop is a classic scam."),
    ("no interview", 10, "A paid offer with no interview can be suspicious."),
    ("gift card", 25, "Gift card payments are not used by real companies."),
    ("crypto", 20, "Crypto payment requests are high risk."),
    ("telegram only", 15, "Official hiring rarely happens only on Telegram."),
]


def split_skills(text):
    if not text:
        return []
    cleaned = text.replace("/", ",").replace("|", ",")
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    return parts


def find_skills(text):
    lowered = (text or "").lower()
    found = []
    for skill in KNOWN_SKILLS:
        if skill in lowered and skill.title() not in found and skill.upper() not in found:
            label = skill.upper() if skill in ["html", "css", "sql", "ui", "ux"] else skill.title()
            if skill == "c++":
                label = "C++"
            if label not in found:
                found.append(label)
    return found


def choose_domain(text, fallback="Web Development"):
    lowered = (text or "").lower()
    mapping = {
        "web": "Web Development",
        "html": "Web Development",
        "flask": "Web Development",
        "data": "Data Analysis",
        "excel": "Data Analysis",
        "ui": "UI/UX Design",
        "ux": "UI/UX Design",
        "figma": "UI/UX Design",
        "cyber": "Cybersecurity",
        "security": "Cybersecurity",
        "android": "Android Development",
        "kotlin": "Android Development",
    }
    for key, domain in mapping.items():
        if key in lowered:
            return domain
    return fallback if fallback in CAREER_ROADMAPS else "Web Development"


def analyze_resume(resume_text, profile_skills="", preferred_domain="", target_role=""):
    text = (resume_text or "").strip()
    found_skills = find_skills(text + " " + profile_skills)
    domain = choose_domain(text + " " + preferred_domain + " " + (target_role or ""), preferred_domain)
    roadmap = CAREER_ROADMAPS.get(domain, CAREER_ROADMAPS["Web Development"])
    needed = []
    for step in roadmap:
        needed.extend(step["skills"])
    if target_role:
        from ml.roles import RoleTarget, resolve_role_name

        needed.extend(RoleTarget(resolve_role_name(target_role)).skills)

    missing = []
    found_lower = [item.lower() for item in found_skills]
    for skill in needed:
        if skill.lower() not in found_lower and skill not in missing:
            missing.append(skill)

    score = 35
    if found_skills:
        score += min(40, len(found_skills) * 6)
    if "project" in text.lower() or "github" in text.lower():
        score += 10
    if "intern" in text.lower() or "education" in text.lower():
        score += 8
    if len(text) > 250:
        score += 7
    score = max(20, min(score, 96))

    suggestions = []
    if missing:
        suggestions.append("Add these skills or projects: " + ", ".join(missing[:5]) + ".")
    if "project" not in text.lower():
        suggestions.append("Mention 2-3 academic or personal projects with tools used.")
    if "github" not in text.lower():
        suggestions.append("Add a GitHub link if you have project code.")
    if len(text) < 200:
        suggestions.append("Your resume text looks short. Add education, skills, and projects.")
    if not suggestions:
        suggestions.append("Strong start. Keep practicing with the AI examiner before real interviews.")

    education_hits = []
    for token in ["bca", "b.sc", "bsc", "mca", "b.tech", "bachelor", "degree", "university", "college"]:
        if token in text.lower():
            education_hits.append(token)
    experience_hits = []
    for token in ["intern", "internship", "experience", "worked", "project intern"]:
        if token in text.lower():
            experience_hits.append(token)
    project_hits = "project" in text.lower() or "github" in text.lower()

    strengths = found_skills[:6] if found_skills else []
    weak = missing[:6]

    return {
        "score": score,
        "domain": domain,
        "found_skills": found_skills or ["No clear technical skills detected"],
        "missing_skills": missing[:6] or ["No major gaps detected from the target-role skill list"],
        "suggestions": suggestions,
        "word_count": len(text.split()),
        "education_found": bool(education_hits) or "education" in text.lower(),
        "experience_found": bool(experience_hits),
        "projects_found": bool(project_hits),
        "strengths": strengths,
        "weak_areas": weak,
    }


def build_roadmap(domain, profile_skills=""):
    selected = choose_domain(domain, domain)
    steps = CAREER_ROADMAPS.get(selected, CAREER_ROADMAPS["Web Development"])
    known = [item.lower() for item in find_skills(profile_skills) + split_skills(profile_skills)]
    result = []
    for step in steps:
        matched = [skill for skill in step["skills"] if skill.lower() in known]
        result.append({
            "level": step["level"],
            "title": step["title"],
            "skills": step["skills"],
            "goal": step["goal"],
            "matched": matched,
            "status": "In progress" if matched else "Up next",
        })
    return selected, result


def detect_scam(company, title, contact, posting):
    blob = " ".join([company, title, contact, posting]).lower()
    flags = []
    score = 0

    for phrase, points, message in SCAM_RED_FLAGS:
        if phrase in blob:
            score += points
            flags.append(message)

    if not company.strip():
        score += 15
        flags.append("No company name was given.")
    if "gmail" in contact.lower() or "yahoo" in contact.lower():
        score += 8
        flags.append("Personal email domains can be less trustworthy than a company email.")
    if "http://" in posting.lower() and "https://" not in posting.lower():
        score += 6
        flags.append("The posting uses an insecure http link.")

    score = min(score, 100)
    if score >= 55:
        verdict = "Likely Scam"
        level = "high"
        advice = "Do not pay or share bank details. Verify the company independently."
    elif score >= 25:
        verdict = "Suspicious"
        level = "medium"
        advice = "Pause and check the company website, LinkedIn, and official career page."
    else:
        verdict = "Looks Safer"
        level = "low"
        advice = "Still verify the company, but no strong scam phrases were found."

    if not flags:
        flags.append("No common scam phrases were detected in this text.")

    return {
        "score": score,
        "verdict": verdict,
        "level": level,
        "flags": flags,
        "advice": advice,
    }


def get_interview_questions(domain):
    selected = choose_domain(domain, domain)
    return selected, INTERVIEW_BANK.get(selected, INTERVIEW_BANK["Web Development"])


def get_interview_rank(average):
    if average >= 80:
        return "Arena Champion"
    if average >= 60:
        return "Strong Contender"
    return "Keep Training"


def score_one_answer(item, answer):
    text = (answer or "").strip()
    lowered = text.lower()
    hits = [word for word in item["keywords"] if word in lowered]
    if len(text) < 12:
        points = 15 if hits else 8
        tip = "Give a longer answer and include a simple example."
    else:
        points = min(100, 40 + (len(hits) * 12) + min(20, len(text.split())))
        if hits:
            tip = "The AI coach liked that you mentioned: " + ", ".join(hits) + "."
        else:
            tip = "Add ideas like: " + ", ".join(item["keywords"][:3]) + "."
    return {
        "question": item["q"],
        "answer": text or "No answer",
        "score": min(points, 100),
        "tip": tip,
        "model": item.get("model", ""),
        "hits": hits,
        "keywords": item.get("keywords", []),
        "topic": item.get("topic") or _topic_from_keywords(item.get("keywords", [])),
    }


def _topic_from_keywords(keywords):
    blob = " ".join(keywords).lower()
    if "sql" in blob or "join" in blob or "query" in blob:
        return "SQL"
    if "python" in blob or "pandas" in blob:
        return "Python"
    if "html" in blob or "css" in blob or "javascript" in blob:
        return "Web"
    if "stat" in blob or "probability" in blob:
        return "Statistics"
    if "excel" in blob or "dashboard" in blob:
        return "Excel"
    if "interview" in blob or "star" in blob or "example" in blob:
        return "Interview"
    return "Technical"



def score_interview(domain, answers):
    selected, questions = get_interview_questions(domain)
    results = []
    total = 0
    for index, item in enumerate(questions):
        answer = answers[index] if index < len(answers) else ""
        item_result = score_one_answer(item, answer)
        total += item_result["score"]
        results.append(item_result)
    average = round(total / len(results)) if results else 0
    rank = get_interview_rank(average)
    return selected, average, rank, results


def recommend_projects(profile_skills, preferred_domain=""):
    domain = choose_domain(preferred_domain + " " + profile_skills, preferred_domain)
    known = [item.lower() for item in find_skills(profile_skills) + split_skills(profile_skills)]
    ranked = []
    for project in PROJECT_CATALOG:
        overlap = [skill for skill in project["skills"] if skill.lower() in known]
        score = len(overlap) * 20
        if project["domain"] == domain:
            score += 25
        if not overlap:
            score += 5
        ranked.append({
            **project,
            "overlap": overlap,
            "match_score": min(score, 99),
        })
    ranked.sort(key=lambda item: item["match_score"], reverse=True)
    return domain, ranked[:5]


def extract_resume_text(file_storage, pasted_text):
    pasted = (pasted_text or "").strip()
    if file_storage and file_storage.filename:
        filename = file_storage.filename.lower()
        data = file_storage.read()
        if filename.endswith(".txt"):
            return data.decode("utf-8", errors="ignore")
        if filename.endswith(".pdf"):
            from io import BytesIO

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            pages = [(page.extract_text() or "") for page in reader.pages]
            return "\n".join(pages)
        raise ValueError("Please upload a .txt or .pdf file.")
    if pasted:
        return pasted
    raise ValueError("Paste your resume or upload a .txt/.pdf file.")
