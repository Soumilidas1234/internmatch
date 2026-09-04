import json
import os
import re
from functools import wraps
from io import BytesIO

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from admin import admin_bp, ensure_admin_schema
from config import DATABASE_URI, DB_FOLDER, DEBUG, SECRET_KEY, validate_settings
from ml.prep import (
    analyze_exam_mistakes,
    build_preparation_plan,
    interview_readiness,
    prioritize_missing,
    role_readiness_for,
    split_known_missing,
    topic_scores_from_results,
    user_target_role,
)
from ml.profile_strength import compute_profile_strength
from ml.recommender import student_has_skills
from ml.resume_fixer import build_resume_fix, render_resume_pdf, stored_resume_text
from ml.roles import ROLE_NAMES, get_role_spec
from models import ExamAttempt, User, db
from seed import ensure_admin_user, ensure_demo_student, ensure_prep_schema, ensure_sample_internships
from tools import (
    DOMAINS,
    analyze_resume,
    detect_scam,
    extract_resume_text,
    get_interview_questions,
    get_interview_rank,
    recommend_projects,
    score_one_answer,
)

validate_settings()

app = Flask(__name__)

# Session signing key comes from the environment, not from source code
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Connect SQLAlchemy to this Flask app
db.init_app(app)
app.register_blueprint(admin_bp)


def login_required(view_func):
    """Send visitors to login if they are not already logged in."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(email and EMAIL_PATTERN.match(email))


def student_match_payload(user):
    resume_skills = session.get("resume_skills", "")
    combined_skills = ", ".join(
        part for part in [user.skills or "", resume_skills] if part
    )
    target = user_target_role(user)
    return {
        "skills": combined_skills,
        "education": user.education or "",
        "preferred_domain": target,
        "preferred_work_mode": user.preferred_work_mode or "",
        "location": user.location or "",
        "target_role": target,
    }


def get_current_user():
    user = db.session.get(User, session.get("user_id"))
    if user is None:
        session.clear()
        flash("Please log in again.", "error")
        return None
    return user


@app.context_processor
def inject_nav_user():
    user = None
    if session.get("user_id"):
        user = db.session.get(User, session["user_id"])
    from config import DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD

    return {
        "nav_user": user,
        "is_admin": bool(user and getattr(user, "is_admin", False)),
        "demo_student_email": DEMO_STUDENT_EMAIL,
        "demo_student_password": DEMO_STUDENT_PASSWORD,
        "show_demo_login": bool(DEMO_STUDENT_PASSWORD),
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        education = request.form.get("education", "").strip()
        cgpa_value = request.form.get("cgpa", "").strip()
        location = request.form.get("location", "").strip()
        preferred_domain = request.form.get("target_role") or request.form.get("preferred_domain", "").strip()
        preferred_work_mode = request.form.get("preferred_work_mode", "").strip() or "Hybrid"
        skills = request.form.get("skills", "").strip()
        target_role = request.form.get("target_role", "").strip() or preferred_domain

        # Check that all fields are filled
        if not all(
            [
                name,
                email,
                password,
                education,
                cgpa_value,
                location,
                preferred_domain,
                skills,
            ]
        ):
            flash("Please fill in all fields.", "error")
            return render_template("register.html", form=request.form, roles=ROLE_NAMES)

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html", form=request.form, roles=ROLE_NAMES)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html", form=request.form, roles=ROLE_NAMES)

        try:
            cgpa = float(cgpa_value)
            if cgpa < 0 or cgpa > 10:
                raise ValueError("CGPA out of range")
        except ValueError:
            flash("Please enter a valid CGPA between 0 and 10.", "error")
            return render_template("register.html", form=request.form, roles=ROLE_NAMES)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("This email is already registered. Please log in.", "error")
            return render_template("register.html", form=request.form, roles=ROLE_NAMES)

        # Hash the password before saving it
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            education=education,
            cgpa=cgpa,
            location=location,
            preferred_domain=preferred_domain,
            preferred_work_mode=preferred_work_mode,
            skills=skills,
            is_admin=False,
            target_role=target_role,
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={}, roles=ROLE_NAMES)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        # Compare the typed password with the stored hash
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login successful.", "success")
            if getattr(user, "is_admin", False):
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        education = request.form.get("education", "").strip()
        cgpa_value = request.form.get("cgpa", "").strip()
        location = request.form.get("location", "").strip()
        preferred_domain = request.form.get("target_role") or request.form.get("preferred_domain", "").strip()
        preferred_work_mode = request.form.get("preferred_work_mode", "").strip() or "Hybrid"
        skills = request.form.get("skills", "").strip()
        target_role = request.form.get("target_role", "").strip() or preferred_domain

        if not all(
            [name, email, education, cgpa_value, location, preferred_domain, skills]
        ):
            flash("Please fill in all profile fields.", "error")
            return render_template("profile.html", user=user, roles=ROLE_NAMES)

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("profile.html", user=user, roles=ROLE_NAMES)

        try:
            cgpa = float(cgpa_value)
            if cgpa < 0 or cgpa > 10:
                raise ValueError("CGPA out of range")
        except ValueError:
            flash("Please enter a valid CGPA between 0 and 10.", "error")
            return render_template("profile.html", user=user, roles=ROLE_NAMES)

        taken = User.query.filter(User.email == email, User.id != user.id).first()
        if taken:
            flash("That email is already used by another account.", "error")
            return render_template("profile.html", user=user, roles=ROLE_NAMES)

        user.name = name
        user.email = email
        user.education = education
        user.cgpa = cgpa
        user.location = location
        user.preferred_domain = preferred_domain
        user.preferred_work_mode = preferred_work_mode
        user.skills = skills
        user.target_role = target_role
        db.session.commit()
        session["user_name"] = user.name
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user, roles=ROLE_NAMES)


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    resume_analyzed = bool(session.get("resume_analyzed"))
    profile = compute_profile_strength(user, resume_analyzed=resume_analyzed)
    student = student_match_payload(user)
    target = user_target_role(user)
    need_skills = not student_has_skills(student)
    match = role_readiness_for(student, target) if not need_skills else None
    have, missing, _required = split_known_missing(student["skills"], target)
    attempts = (
        ExamAttempt.query.filter_by(user_id=user.id)
        .order_by(ExamAttempt.created_at.desc())
        .all()
    )
    last_exam = attempts[0] if attempts else None
    previous = attempts[1] if len(attempts) > 1 else None
    improvement = None
    if last_exam and previous:
        improvement = last_exam.overall_score - previous.overall_score
    readiness = interview_readiness(profile["score"], match or {}, last_exam)
    mistakes = last_exam.mistake_list() if last_exam else []
    plan = build_preparation_plan(student["skills"], target, attempts)

    return render_template(
        "dashboard.html",
        user=user,
        profile=profile,
        target=target,
        match=match,
        have=have,
        missing=missing,
        need_skills=need_skills,
        last_exam=last_exam,
        improvement=improvement,
        readiness=readiness,
        mistakes=mistakes[:4],
        plan=plan,
        attempts=attempts[:5],
    )


@app.route("/recommendations")
@login_required
def recommendations():
    return redirect(url_for("readiness"))


@app.route("/readiness", methods=["GET", "POST"])
@login_required
def readiness():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        custom = request.form.get("custom_role", "").strip()
        chosen = custom or request.form.get("target_role", "").strip()
        if chosen:
            user.target_role = chosen
            user.preferred_domain = chosen
            db.session.commit()
            flash("Target role saved. Role readiness is an estimate, not a job guarantee.", "success")
            return redirect(url_for("readiness"))

    student = student_match_payload(user)
    target = user_target_role(user)
    need_skills = not student_has_skills(student)
    match = None
    have, missing, _required = [], [], []
    if not need_skills:
        match = role_readiness_for(student, target)
        have, missing, _required = split_known_missing(student["skills"], target)

    return render_template(
        "readiness.html",
        user=user,
        target=target,
        match=match,
        have=have,
        missing=missing,
        need_skills=need_skills,
        roles=ROLE_NAMES,
    )


@app.route("/skill-gap")
@login_required
def skill_gap():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    student = student_match_payload(user)
    target = user_target_role(user)
    need_skills = not student_has_skills(student)
    have, missing, _required = split_known_missing(student["skills"], target)
    priority = prioritize_missing(missing)
    return render_template(
        "skill_gap.html",
        user=user,
        target=target,
        have=have,
        missing=missing,
        priority=priority,
        need_skills=need_skills,
    )


def _prep_redirect():
    flash(
        "InternMatch AI helps you prepare. Applications happen on the company's own website.",
        "success",
    )
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))


@app.route("/internships")
def internships():
    return _prep_redirect()


@app.route("/internship/<int:internship_id>")
def internship_detail(internship_id):
    return _prep_redirect()


@app.route("/internship/<int:internship_id>/apply", methods=["POST"])
@login_required
def apply_internship(internship_id):
    return _prep_redirect()


@app.route("/applications")
@login_required
def my_applications():
    return redirect(url_for("progress"))


@app.route("/applications/<int:application_id>/status", methods=["POST"])
@login_required
def update_application_status(application_id):
    return redirect(url_for("progress"))


@app.route("/resume-analyzer", methods=["GET", "POST"])
@login_required
def resume_analyzer():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        try:
            resume_text = extract_resume_text(
                request.files.get("resume_file"),
                request.form.get("resume_text", ""),
            )
            result = analyze_resume(
                resume_text,
                user.skills,
                user.preferred_domain,
                user_target_role(user),
            )
            extracted = [
                skill
                for skill in result.get("found_skills", [])
                if skill != "No clear technical skills detected"
            ]
            session["resume_analyzed"] = True
            session["resume_skills"] = ", ".join(extracted)
            user.last_resume_text = resume_text
            user.resume_analyzed_count = (user.resume_analyzed_count or 0) + 1
            if extracted:
                merged = []
                seen = set()
                for skill in (user.skills or "").split(",") + extracted:
                    clean = skill.strip()
                    key = clean.lower()
                    if clean and key not in seen:
                        seen.add(key)
                        merged.append(clean)
                user.skills = ", ".join(merged)
            db.session.commit()
            flash("Resume uploaded and analyzed. Skills were extracted.", "success")
        except ValueError as error:
            flash(str(error), "error")

    return render_template("resume_analyzer.html", user=user, result=result)


@app.route("/resume-fixer")
@login_required
def resume_fixer():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    resume_text = stored_resume_text(user)
    plan = build_resume_fix(
        user,
        resume_text,
        resume_analyzed=bool(session.get("resume_analyzed") or resume_text),
    )
    return render_template("resume_fixer.html", user=user, plan=plan)


@app.route("/resume-fixer/pdf", methods=["GET", "POST"])
@login_required
def resume_fixer_pdf():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    resume_text = stored_resume_text(user)
    if not resume_text:
        return (
            "No resume text found. Analyze or upload your resume first so the PDF "
            "can be rebuilt from YOUR content.",
            400,
        )

    plan = build_resume_fix(
        user,
        resume_text,
        resume_analyzed=True,
    )
    pdf_bytes = render_resume_pdf(plan["document"])
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=plan["filename"],
    )


@app.route("/career-roadmap", methods=["GET", "POST"])
@login_required
def career_roadmap():
    return redirect(url_for("preparation_plan"))


@app.route("/preparation-plan")
@login_required
def preparation_plan():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    student = student_match_payload(user)
    target = user_target_role(user)
    attempts = (
        ExamAttempt.query.filter_by(user_id=user.id)
        .order_by(ExamAttempt.created_at.desc())
        .all()
    )
    plan = build_preparation_plan(student["skills"], target, attempts)
    return render_template("preparation_plan.html", user=user, plan=plan)


@app.route("/progress")
@login_required
def progress():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    attempts = (
        ExamAttempt.query.filter_by(user_id=user.id)
        .order_by(ExamAttempt.created_at.asc())
        .all()
    )
    return render_template("progress.html", user=user, attempts=attempts)


@app.route("/scam-detector", methods=["GET", "POST"])
@login_required
def scam_detector():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        result = detect_scam(
            request.form.get("company", ""),
            request.form.get("title", ""),
            request.form.get("contact", ""),
            request.form.get("posting", ""),
        )
    return render_template("scam_detector.html", user=user, result=result)


@app.route("/examiner", methods=["GET", "POST"])
@app.route("/interview-arena", methods=["GET", "POST"])
@login_required
def interview_arena():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    role_name = user_target_role(user)
    default_domain = get_role_spec(role_name)["exam_domain"]
    selected = session.get("arena_domain") or default_domain
    current_question = None
    question_number = 0
    total_questions = 5
    feedback = None
    report = None
    average = None
    rank = None
    finished = False
    progress = 0
    mistakes = []
    topic_scores = {}

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start":
            selected = request.form.get("domain", selected) or default_domain
            selected, question_list = get_interview_questions(selected)
            session["arena_domain"] = selected
            session["arena_index"] = 0
            session["arena_results"] = []
            session.pop("arena_feedback", None)
            session.pop("exam_saved", None)
        elif action == "answer":
            selected = session.get("arena_domain", selected)
            selected, question_list = get_interview_questions(selected)
            index = session.get("arena_index", 0)
            result = score_one_answer(question_list[index], request.form.get("answer", ""))
            results = list(session.get("arena_results", []))
            results.append(result)
            session["arena_results"] = results
            session["arena_feedback"] = result
        elif action == "next":
            session.pop("arena_feedback", None)
            session["arena_index"] = session.get("arena_index", 0) + 1
        elif action == "restart":
            session.pop("arena_domain", None)
            session.pop("arena_index", None)
            session.pop("arena_results", None)
            session.pop("arena_feedback", None)
            session.pop("exam_saved", None)
            selected = default_domain

    if session.get("arena_domain"):
        selected, question_list = get_interview_questions(session["arena_domain"])
        total_questions = len(question_list)
        index = session.get("arena_index", 0)
        results = session.get("arena_results", [])
        feedback = session.get("arena_feedback")
        if index >= total_questions:
            finished = True
            report = results
            average = round(sum(item["score"] for item in report) / len(report)) if report else 0
            rank = get_interview_rank(average)
            progress = 100
            mistakes = analyze_exam_mistakes(report)
            topic_scores = topic_scores_from_results(report)
            if report and not session.get("exam_saved"):
                attempt = ExamAttempt(
                    user_id=user.id,
                    target_role=role_name,
                    overall_score=average,
                    topic_scores=json.dumps(topic_scores),
                    mistakes=json.dumps(mistakes),
                )
                db.session.add(attempt)
                db.session.commit()
                session["exam_saved"] = True
        else:
            current_question = question_list[index]
            question_number = index + 1
            progress = int((index / total_questions) * 100)
            if feedback:
                progress = int((question_number / total_questions) * 100)

    return render_template(
        "interview_arena.html",
        user=user,
        selected=selected,
        current_question=current_question,
        question_number=question_number,
        total_questions=total_questions,
        feedback=feedback,
        report=report,
        average=average,
        rank=rank,
        finished=finished,
        progress=progress,
        domains=DOMAINS,
        mistakes=mistakes,
        topic_scores=topic_scores,
        target=role_name,
    )


@app.route("/video-interview")
@login_required
def video_interview():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    return render_template(
        "video_interview.html",
        user=user,
        selected=get_role_spec(user_target_role(user))["exam_domain"],
        domains=DOMAINS,
    )


@app.route("/api/video-interview/start", methods=["POST"])
@login_required
def video_interview_start():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "Please log in."}), 401

    data = request.get_json(silent=True) or {}
    domain = data.get("domain") or user.preferred_domain
    selected, questions = get_interview_questions(domain)
    payload = [{"q": item["q"]} for item in questions]
    return jsonify({"domain": selected, "questions": payload, "name": user.name})


@app.route("/api/video-interview/score", methods=["POST"])
@login_required
def video_interview_score():
    if get_current_user() is None:
        return jsonify({"error": "Please log in."}), 401

    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "Web Development")
    try:
        index = int(data.get("index", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid question number."}), 400

    selected, questions = get_interview_questions(domain)
    if index < 0 or index >= len(questions):
        return jsonify({"error": "Invalid question number."}), 400

    result = score_one_answer(questions[index], data.get("answer", ""))
    return jsonify(result)


@app.route("/project-recommendations", methods=["GET", "POST"])
@login_required
def project_recommendations():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    extra_skills = ""
    if request.method == "POST":
        extra_skills = request.form.get("extra_skills", "")

    combined_skills = (user.skills or "") + ", " + extra_skills
    selected, projects = recommend_projects(combined_skills, user.preferred_domain)
    return render_template(
        "project_recommendations.html",
        user=user,
        selected=selected,
        projects=projects,
        extra_skills=extra_skills,
    )


@app.errorhandler(404)
def not_found(_error):
    return (
        render_template(
            "errors/error.html",
            title="Page not found",
            badge="404",
            heading="We could not find that page",
            message="The link may be outdated, or the page does not exist in InternMatch AI.",
            home_endpoint="home",
            button="Back to home",
        ),
        404,
    )


@app.errorhandler(403)
def forbidden(_error):
    home_endpoint = "login"
    if session.get("user_id"):
        user = db.session.get(User, session["user_id"])
        if user and getattr(user, "is_admin", False):
            home_endpoint = "admin.dashboard"
        else:
            home_endpoint = "dashboard"
    return (
        render_template(
            "errors/error.html",
            title="Access denied",
            badge="403",
            heading="You do not have access to this page",
            message="This area is private. Please use your own dashboard or log in with the correct account.",
            home_endpoint=home_endpoint,
            button="Continue",
        ),
        403,
    )


@app.errorhandler(500)
def server_error(_error):
    return (
        render_template(
            "errors/error.html",
            title="Something went wrong",
            badge="500",
            heading="InternMatch AI hit a problem",
            message="Please try again. If this continues, refresh the page or restart the app.",
            home_endpoint="home",
            button="Back to home",
        ),
        500,
    )


# Create the database folder and tables when the app starts
with app.app_context():
    os.makedirs(DB_FOLDER, exist_ok=True)
    db.create_all()
    ensure_admin_schema()
    ensure_prep_schema()
    ensure_admin_user()
    ensure_demo_student()
    ensure_sample_internships()
    db.session.execute(
        db.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_internship "
            "ON applications (user_id, internship_id)"
        )
    )
    db.session.commit()


if __name__ == "__main__":
    app.run(debug=DEBUG, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
