"""Rule-based resume rebuild for a student's target role.

Uses the existing resume parser and role catalog only. Does not invent
education, companies, dates, or projects that are not in the resume or
the student's own profile fields.
"""

import html as html_lib
import os
import re
from io import BytesIO

from ml.matcher import display_skill
from ml.prep import split_known_missing, user_target_role
from ml.profile_strength import compute_profile_strength
from ml.roles import ROLE_NAMES, TARGET_ROLES, get_role_spec, resolve_role_name
from tools import analyze_resume, find_skills, split_skills

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{8,}\d)")
URL_RE = re.compile(
    r"(?:https?://[^\s]+|www\.[^\s]+|(?:github|linkedin)\.com/[^\s]+)",
    re.I,
)

SECTION_ALIASES = {
    "education": (
        "education",
        "academic",
        "academics",
        "qualification",
        "qualifications",
    ),
    "experience": (
        "experience",
        "work experience",
        "work history",
        "employment",
        "internship",
        "internships",
    ),
    "projects": (
        "projects",
        "academic projects",
        "personal projects",
        "project",
    ),
    "skills": ("skills", "technical skills", "skill set", "technologies"),
    "summary": ("summary", "objective", "profile", "about me", "about"),
    "certifications": ("certifications", "certification", "courses", "achievements"),
}

EDU_HINTS = (
    "bca",
    "b.sc",
    "bsc",
    "mca",
    "b.tech",
    "btech",
    "bachelor",
    "degree",
    "university",
    "college",
    "cgpa",
    "sslc",
    "hsc",
    "12th",
    "10th",
)

EXP_HINTS = ("intern", "internship", "worked at", "work experience", "trainee")
PROJ_HINTS = ("project", "github", "built ", "developed ")

ALWAYS_RELEVANT = {
    "git",
    "github",
    "communication",
    "leadership",
    "python",
    "sql",
    "sqlite",
    "mysql",
    "mongodb",
    "testing",
}

# Known tools that belong to another career track. Used only to de-emphasize.
SPECIALIZED_SKILLS = {
    "figma",
    "ux",
    "android",
    "kotlin",
    "tableau",
    "power bi",
    "machine learning",
    "excel",
    "pandas",
    "numpy",
    "data analysis",
    "php",
    "react",
    "node",
}

ROLE_KEYWORD_EXTRAS = {
    "Data Analyst": ["dashboard", "data cleaning", "visualization", "reporting", "insights"],
    "Software Developer": ["problem solving", "debugging", "version control", "testing"],
    "Web Developer": ["responsive", "frontend", "backend", "REST", "GitHub"],
    "Python Developer": ["scripts", "APIs", "automation", "GitHub", "testing"],
    "ML Engineer": ["model training", "evaluation", "feature engineering", "NumPy"],
    "Java Developer": ["OOP", "debugging", "version control", "testing"],
    "Frontend Developer": ["responsive", "accessibility", "UI", "GitHub"],
    "Backend Developer": ["APIs", "database", "authentication", "testing"],
}

NAVY = "#0F2744"
TEAL = "#0D7377"


def stored_resume_text(user):
    return (getattr(user, "last_resume_text", None) or "").strip()


def resume_pdf_filename(name, role):
    return f"InternMatch_Resume_{_slug(name)}_{_slug(role)}.pdf"


def _slug(value):
    text = re.sub(r"[^\w]+", "_", (value or "").strip())
    return text.strip("_") or "Student"


def _esc(value):
    return html_lib.escape(str(value or ""))


def _normalize_header(line):
    return re.sub(r"[^a-zA-Z\s]", "", line or "").strip().lower()


def _match_section(line):
    cleaned = _normalize_header(line)
    if not cleaned or len(cleaned.split()) > 5:
        return None
    for section, aliases in SECTION_ALIASES.items():
        if cleaned in aliases:
            return section
        if any(cleaned == alias or cleaned.startswith(alias + " ") for alias in aliases):
            return section
    return None


def _extract_phones(text):
    found = []
    seen = set()
    for match in PHONE_RE.findall(text or ""):
        digits = re.sub(r"\D", "", match)
        if 10 <= len(digits) <= 13 and digits not in seen:
            seen.add(digits)
            found.append(re.sub(r"\s+", " ", match).strip())
    return found


def _looks_like_name(line):
    if not line or "@" in line or "http" in line.lower():
        return False
    if _match_section(line):
        return False
    words = [part for part in re.split(r"\s+", line) if part]
    if not (1 <= len(words) <= 4):
        return False
    if any(char.isdigit() for char in line):
        return False
    return all(word[0].isalpha() for word in words if word)


def _line_has_any(line, hints):
    lowered = line.lower()
    return any(hint in lowered for hint in hints)


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        key = " ".join(str(item).split()).strip()
        if not key:
            continue
        folded = key.lower()
        if folded in seen:
            continue
        seen.add(folded)
        result.append(key)
    return result


def recommended_keywords(role_name):
    official = resolve_role_name(role_name)
    spec = get_role_spec(official)
    extras = ROLE_KEYWORD_EXTRAS.get(official, ROLE_KEYWORD_EXTRAS["Software Developer"])
    keywords = []
    for item in list(spec["skills"]) + list(extras):
        if item not in keywords:
            keywords.append(item)
    return keywords


def _role_skill_set(role_name):
    return {skill.lower() for skill in get_role_spec(role_name)["skills"]}


def _other_role_skills(role_name):
    current = _role_skill_set(role_name)
    other = set()
    for name in ROLE_NAMES:
        if name.lower() == resolve_role_name(role_name).lower():
            continue
        for skill in TARGET_ROLES[name]["skills"]:
            key = skill.lower()
            if key not in current and key not in ALWAYS_RELEVANT:
                other.add(key)
    return other


def parse_resume_fields(resume_text, user=None):
    """Pull facts from resume text and, if missing, from the student's profile."""
    text = (resume_text or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    emails = _dedupe_keep_order(EMAIL_RE.findall(text))
    phones = _extract_phones(text)
    links = _dedupe_keep_order(URL_RE.findall(text))

    sections = {key: [] for key in SECTION_ALIASES}
    current = None
    leftover = []
    for line in lines:
        header = _match_section(line)
        if header:
            current = header
            continue
        if current:
            sections[current].append(line)
        else:
            leftover.append(line)

    name = ""
    if leftover and _looks_like_name(leftover[0]):
        name = leftover[0]
        leftover = leftover[1:]
    if not name and user is not None:
        name = (user.name or "").strip()

    education = list(sections["education"])
    experience = list(sections["experience"])
    projects = list(sections["projects"])
    summary_lines = list(sections["summary"])
    certifications = list(sections["certifications"])

    if not education:
        education = [line for line in leftover if _line_has_any(line, EDU_HINTS)]
    if not experience:
        experience = [line for line in leftover if _line_has_any(line, EXP_HINTS)]
    if not projects:
        projects = [line for line in leftover if _line_has_any(line, PROJ_HINTS)]

    education = _dedupe_keep_order(education)
    experience = _dedupe_keep_order(experience)
    projects = _dedupe_keep_order(projects)
    summary_lines = _dedupe_keep_order(summary_lines)
    certifications = _dedupe_keep_order(certifications)

    profile_education = ""
    if user is not None:
        profile_education = (user.education or "").strip()
        if profile_education and user.cgpa is not None:
            profile_education = f"{profile_education} · CGPA {user.cgpa}"
        if not emails and user.email:
            emails = [user.email]
        if not name:
            name = (user.name or "").strip()

    if not education and profile_education:
        education = [profile_education]

    found_skills = find_skills(text)
    profile_skills = split_skills(getattr(user, "skills", "") or "") if user is not None else []
    listed = []
    if sections["skills"]:
        listed.extend(split_skills(", ".join(sections["skills"])))
        for raw in sections["skills"]:
            listed.extend(find_skills(raw))
    skills = _dedupe_keep_order(found_skills + listed + profile_skills)

    location = ""
    if user is not None:
        location = (user.location or "").strip()

    return {
        "name": name or "Student",
        "emails": emails,
        "phones": phones,
        "links": links,
        "location": location,
        "education": education,
        "experience": experience,
        "projects": projects,
        "summary_lines": summary_lines,
        "certifications": certifications,
        "skills": skills,
        "profile_education": profile_education,
        "raw_text": text,
        "word_count": len(text.split()),
    }


def _missing_sections(parsed):
    checks = [
        ("Contact details", bool(parsed["emails"] or parsed["phones"] or parsed["links"])),
        ("Education", bool(parsed["education"])),
        ("Skills", bool(parsed["skills"])),
        ("Projects", bool(parsed["projects"])),
        ("Experience", bool(parsed["experience"])),
        ("Summary", bool(parsed["summary_lines"])),
    ]
    return [name for name, present in checks if not present]


def _classify_skills(skills, role_name):
    role_set = _role_skill_set(role_name)
    other = _other_role_skills(role_name)
    relevant = []
    extra = []
    irrelevant = []
    for skill in skills:
        key = skill.lower()
        if key in role_set or key in ALWAYS_RELEVANT:
            relevant.append(display_skill(key) if key == skill.lower() else skill)
        elif key in other or key in SPECIALIZED_SKILLS:
            irrelevant.append(skill)
        else:
            extra.append(skill)
    return _dedupe_keep_order(relevant), _dedupe_keep_order(extra), _dedupe_keep_order(irrelevant)


def _build_summary(parsed, target_role, relevant_skills):
    if parsed["summary_lines"]:
        return " ".join(parsed["summary_lines"])

    name = parsed["name"]
    parts = [f"{name} is preparing for a {target_role} role."]
    if parsed["education"]:
        parts.append(f"Education on file: {parsed['education'][0]}.")
    if relevant_skills:
        parts.append(f"Skills already present include {', '.join(relevant_skills[:6])}.")
    if parsed["projects"]:
        parts.append("Projects below are taken from the uploaded resume.")
    if parsed["experience"]:
        parts.append("Experience below is taken from the uploaded resume.")
    parts.append(f"This rewrite is for interview preparation toward {target_role}.")
    return " ".join(parts)


def rebuild_document(parsed, target_role, missing_keywords, relevant, extra, missing_sections):
    """Assemble a rebuilt resume using only extracted facts plus marked suggestions."""
    contact_bits = []
    contact_bits.extend(parsed["emails"])
    contact_bits.extend(parsed["phones"])
    if parsed["location"]:
        contact_bits.append(parsed["location"])
    contact_bits.extend(parsed["links"])

    suggested = []
    if missing_sections:
        suggested.append("Missing sections to fill in (only if true for you): " + ", ".join(missing_sections) + ".")
    if missing_keywords:
        suggested.append(
            "Keyword placeholders to add only if you have the skill or experience: "
            + ", ".join(f"[Suggested: {item}]" for item in missing_keywords[:8])
            + "."
        )
    if parsed["word_count"] and parsed["word_count"] < 80:
        suggested.append(
            "The original resume text is short. Add real education, projects, and tools you used — do not invent jobs."
        )
    if not parsed["experience"]:
        suggested.append("No work history was found. Leave this empty rather than inventing internships or companies.")
    if not parsed["projects"]:
        suggested.append("No projects were found. Add 1–2 real academic or personal projects if you have them.")

    return {
        "name": parsed["name"],
        "contact": contact_bits,
        "target_role": target_role,
        "summary": _build_summary(parsed, target_role, relevant),
        "relevant_skills": relevant,
        "other_skills": extra,
        "education": parsed["education"],
        "experience": parsed["experience"],
        "projects": parsed["projects"],
        "certifications": parsed["certifications"],
        "suggested": suggested,
        "missing_keywords": missing_keywords[:8],
    }


def preview_html(document):
    skills = list(document["relevant_skills"])
    if document["other_skills"]:
        skills.extend(document["other_skills"])
    if document["missing_keywords"]:
        skills.extend(f"[Suggested: {item}]" for item in document["missing_keywords"])

    def bullets(items, empty):
        if not items:
            return f"<p class='resume-empty'>{_esc(empty)}</p>"
        return "<ul>" + "".join(f"<li>{_esc(item)}</li>" for item in items) + "</ul>"

    contact = " · ".join(_esc(item) for item in document["contact"])
    return f"""
<article class="resume-sheet">
    <header class="resume-sheet-head">
        <h2>{_esc(document["name"])}</h2>
        <p class="resume-role">{_esc(document["target_role"])}</p>
        <p class="resume-contact">{contact or "Add an email or phone if you want it on the resume."}</p>
    </header>
    <section>
        <h3>Summary</h3>
        <p>{_esc(document["summary"])}</p>
    </section>
    <section>
        <h3>Skills</h3>
        <p>{_esc(", ".join(skills) if skills else "No skills extracted yet.")}</p>
    </section>
    <section>
        <h3>Education</h3>
        {bullets(document["education"], "No education lines were found in the resume or profile.")}
    </section>
    <section>
        <h3>Experience</h3>
        {bullets(document["experience"], "No work history was found in the uploaded resume. Nothing was invented.")}
    </section>
    <section>
        <h3>Projects</h3>
        {bullets(document["projects"], "No projects were found in the uploaded resume. Nothing was invented.")}
    </section>
    {"" if not document["certifications"] else "<section><h3>Certifications / courses</h3>" + bullets(document["certifications"], "") + "</section>"}
    <section class="resume-suggested">
        <h3>Suggested additions</h3>
        {bullets(document["suggested"], "No extra additions flagged.")}
    </section>
</article>
"""


def preview_text(document):
    lines = [
        document["name"],
        document["target_role"],
        " | ".join(document["contact"]),
        "",
        "SUMMARY",
        document["summary"],
        "",
        "SKILLS",
        ", ".join(document["relevant_skills"] + document["other_skills"]),
    ]
    if document["missing_keywords"]:
        lines.append("Suggested keywords: " + ", ".join(f"[Suggested: {item}]" for item in document["missing_keywords"]))
    lines.extend(["", "EDUCATION"])
    lines.extend(document["education"] or ["None found"])
    lines.extend(["", "EXPERIENCE"])
    lines.extend(document["experience"] or ["No work history was found. Nothing was invented."])
    lines.extend(["", "PROJECTS"])
    lines.extend(document["projects"] or ["No projects were found. Nothing was invented."])
    lines.extend(["", "SUGGESTED ADDITIONS"])
    lines.extend(document["suggested"] or ["None"])
    return "\n".join(lines)


def build_resume_fix(user, resume_text, resume_analyzed=False):
    """Score, compare, and rebuild using existing analyzers plus the role catalog."""
    target = user_target_role(user)
    text = (resume_text or "").strip()
    parsed = parse_resume_fields(text, user)
    analysis = None
    if text:
        analysis = analyze_resume(
            text,
            getattr(user, "skills", "") or "",
            getattr(user, "preferred_domain", "") or "",
            target,
        )
    profile = compute_profile_strength(user, resume_analyzed=bool(resume_analyzed or text))

    combined_skills = ", ".join(
        part for part in [getattr(user, "skills", "") or "", ", ".join(parsed["skills"])] if part
    )
    _have, missing_skills, _required = split_known_missing(combined_skills, target)
    relevant, extra, irrelevant = _classify_skills(parsed["skills"], target)

    keywords = recommended_keywords(target)
    blob = f"{text} {getattr(user, 'skills', '') or ''}".lower()
    keywords_present = [item for item in keywords if item.lower() in blob]
    keywords_missing = [item for item in keywords if item.lower() not in blob]

    missing_sections = _missing_sections(parsed) if text else ["Resume upload"] + _missing_sections(parsed)
    if not text:
        missing_sections = _dedupe_keep_order(["Full resume text"] + missing_sections)

    add_these = []
    for section in missing_sections:
        add_these.append(f"Section: {section}")
    for skill in missing_skills:
        add_these.append(f"Skill vs {target}: {skill}")
    for word in keywords_missing[:8]:
        label = f"Keyword: {word}"
        if label not in add_these and f"Skill vs {target}: {word}" not in add_these:
            add_these.append(label)

    document = rebuild_document(
        parsed,
        target,
        keywords_missing,
        relevant,
        extra,
        missing_sections,
    )

    return {
        "target": target,
        "has_resume": bool(text),
        "thin": bool(text) and parsed["word_count"] < 80,
        "word_count": parsed["word_count"],
        "resume_score": analysis["score"] if analysis else None,
        "profile": profile,
        "add_these": add_these,
        "deemphasize": irrelevant,
        "keywords": keywords,
        "keywords_present": keywords_present,
        "keywords_missing": keywords_missing,
        "missing_skills": missing_skills,
        "missing_sections": missing_sections,
        "relevant_skills": relevant,
        "document": document,
        "preview_html": preview_html(document),
        "preview_text": preview_text(document),
        "filename": resume_pdf_filename(parsed["name"], target),
    }


def _pdf_font_name():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont("ResumeBody", path))
                return "ResumeBody"
            except Exception:
                continue
    return "Helvetica"


def _pdf_safe(text, font_name):
    value = str(text or "")
    if font_name == "Helvetica":
        return value.encode("latin-1", "replace").decode("latin-1")
    return value


def render_resume_pdf(document):
    """Create a clean one- or two-page PDF from the rebuilt document."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        KeepTogether,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    font_name = _pdf_font_name()
    bold_name = "Helvetica-Bold" if font_name == "Helvetica" else font_name

    def P(text, style):
        return Paragraph(_pdf_safe(html_lib.escape(text), font_name).replace("\n", "<br/>"), style)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"{document['name']} — {document['target_role']}",
        author="InternMatch AI",
    )

    navy = HexColor(NAVY)
    teal = HexColor(TEAL)
    body = HexColor("#1E293B")
    muted = HexColor("#475569")

    styles = {
        "name": ParagraphStyle(
            "ResumeName",
            fontName=bold_name,
            fontSize=20,
            leading=24,
            textColor=navy,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "role": ParagraphStyle(
            "ResumeRole",
            fontName=font_name,
            fontSize=11,
            leading=14,
            textColor=teal,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "contact": ParagraphStyle(
            "ResumeContact",
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=muted,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "ResumeHeading",
            fontName=bold_name,
            fontSize=11,
            leading=14,
            textColor=teal,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "ResumeBodyText",
            fontName=font_name,
            fontSize=10,
            leading=13,
            textColor=body,
            alignment=TA_LEFT,
        ),
        "suggest": ParagraphStyle(
            "ResumeSuggest",
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=teal,
            alignment=TA_LEFT,
        ),
        "footer": ParagraphStyle(
            "ResumeFooter",
            fontName=font_name,
            fontSize=8,
            leading=10,
            textColor=muted,
            alignment=TA_CENTER,
            spaceBefore=16,
        ),
    }

    story = [
        P(document["name"], styles["name"]),
        P(document["target_role"], styles["role"]),
        P(" · ".join(document["contact"]) or "Add contact details from your resume if you want them listed.", styles["contact"]),
        HRFlowable(width="100%", thickness=1.4, color=navy, spaceAfter=6),
        P("SUMMARY", styles["heading"]),
        P(document["summary"], styles["body"]),
        P("SKILLS", styles["heading"]),
    ]

    skill_bits = list(document["relevant_skills"]) + list(document["other_skills"])
    skill_bits.extend(f"[Suggested: {item}]" for item in document["missing_keywords"])
    story.append(P(", ".join(skill_bits) if skill_bits else "No skills extracted.", styles["body"]))

    def add_list(title, items, empty):
        story.append(P(title, styles["heading"]))
        values = items or [empty]
        bullets = []
        for item in values:
            bullets.append(ListItem(P(item, styles["body"]), leftIndent=8, bulletColor=teal))
        story.append(ListFlowable(bullets, bulletType="bullet", start="•", leftIndent=12, spaceBefore=0))

    add_list(
        "EDUCATION",
        document["education"],
        "No education lines were found in the resume or profile.",
    )
    add_list(
        "EXPERIENCE",
        document["experience"],
        "No work history was found in the uploaded resume. Nothing was invented.",
    )
    add_list(
        "PROJECTS",
        document["projects"],
        "No projects were found in the uploaded resume. Nothing was invented.",
    )
    if document["certifications"]:
        add_list("CERTIFICATIONS / COURSES", document["certifications"], "")

    if document["suggested"]:
        story.append(P("SUGGESTED ADDITIONS", styles["heading"]))
        story.append(
            P("Add these only if they are true for you. InternMatch does not invent jobs or companies.", styles["suggest"])
        )
        bullets = [
            ListItem(P(item, styles["suggest"]), leftIndent=8, bulletColor=teal)
            for item in document["suggested"]
        ]
        story.append(ListFlowable(bullets, bulletType="bullet", start="•", leftIndent=12))

    story.append(
        KeepTogether(
            [
                Spacer(1, 12),
                HRFlowable(width="100%", thickness=0.6, color=HexColor("#94A3B8")),
                P(
                    "InternMatch AI interview-preparation rewrite of YOUR resume. "
                    "This does not apply to companies for you.",
                    styles["footer"],
                ),
            ]
        )
    )

    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(HexColor(TEAL))
        canvas.rect(0, letter[1] - 8, letter[0], 8, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
