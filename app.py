"""InternMatch AI: local Flask app for internship and interview preparation.

Students analyze resumes, check role readiness, practice exams, and rebuild a
resume PDF. Internship browse/apply URLs redirect; applications are not
processed here.
"""

import json
import os
import re
from functools import wraps
from io import BytesIO

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from admin import admin_bp, ensure_admin_schema
from config import DATABASE_URI, DB_FOLDER, DEBUG, IS_PRODUCTION, SECRET_KEY, validate_settings
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
from ml.ats_simulator import simulate_ats
from ml.jd_analyzer import analyze_job_description, validate_job_description
from ml.recommender import student_has_skills
from ml.resume_fixer import build_resume_fix, render_resume_pdf, stored_resume_text
from ml.resume_interview import (
    CATEGORY_LABELS,
    build_hotspots,
    build_report,
    evaluate_resume_answer,
    extract_resume_claims,
    generate_questions,
)
from ml.role_questions import (
    CATEGORY_LABELS as ROLE_Q_CATEGORIES,
    evaluate_role_answer,
    generate_role_questions,
    resolve_generator_role,
    summarize_user_practice,
    topic_performance,
)
from ml.roles import ROLE_NAMES, get_role_spec
from models import (
    AtsSimulation,
    ExamAttempt,
    JobAnalysis,
    ResumeInterviewSession,
    RoleQuestionSet,
    SavedRoleQuestion,
    User,
    db,
)
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
app.config["TEMPLATES_AUTO_RELOAD"] = not IS_PRODUCTION
if IS_PRODUCTION:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["PREFERRED_URL_SCHEME"] = "https"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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
        "nav_endpoints": set(app.view_functions),
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
    role_q_stats = summarize_user_practice(
        RoleQuestionSet.query.filter_by(user_id=user.id).all()
    )

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
        role_q_stats=role_q_stats,
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


@app.route("/job-analyzer", methods=["GET", "POST"])
@login_required
def job_analyzer():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    result = None
    pasted = ""
    if request.method == "POST":
        pasted = request.form.get("job_description", "")
        cleaned, error = validate_job_description(pasted)
        if error:
            flash(error, "error")
        else:
            try:
                student = student_match_payload(user)
                resume_text = stored_resume_text(user) or ""
                result = analyze_job_description(student, cleaned, resume_text)
                analysis = JobAnalysis(
                    user_id=user.id,
                    job_title=result["job_title"] if result["job_title"] != "Not detected" else "Untitled role",
                    job_description=cleaned,
                    detected_skills=json.dumps(result["required_skills"] if isinstance(result["required_skills"], list) else []),
                    matching_skills=json.dumps(result["have"]),
                    missing_skills=json.dumps(result["missing"]),
                    match_score=result["score"],
                    result_json=json.dumps(result),
                )
                db.session.add(analysis)
                db.session.commit()
                return redirect(url_for("job_analyzer_detail", analysis_id=analysis.id))
            except Exception:
                db.session.rollback()
                flash("We could not analyze that description. Please try again with a clearer job post.", "error")

    history = (
        JobAnalysis.query.filter_by(user_id=user.id)
        .order_by(JobAnalysis.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "job_analyzer.html",
        user=user,
        result=result,
        pasted=pasted,
        history=history,
        analysis=None,
    )


@app.route("/job-analyzer/<int:analysis_id>")
@login_required
def job_analyzer_detail(analysis_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    analysis = db.session.get(JobAnalysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        flash("That analysis was not found.", "error")
        return redirect(url_for("job_analyzer"))

    result = analysis.result()
    history = (
        JobAnalysis.query.filter_by(user_id=user.id)
        .order_by(JobAnalysis.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "job_analyzer.html",
        user=user,
        result=result,
        pasted=analysis.job_description,
        history=history,
        analysis=analysis,
    )


@app.route("/ats-simulator", methods=["GET", "POST"])
@login_required
def ats_simulator():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    resume_text = stored_resume_text(user)
    latest_jd = (
        JobAnalysis.query.filter_by(user_id=user.id)
        .order_by(JobAnalysis.created_at.desc())
        .first()
    )
    pasted_jd = (latest_jd.job_description if latest_jd else "") or ""
    selected_role = user_target_role(user)

    if request.method == "POST":
        selected_role = (
            request.form.get("custom_role", "").strip()
            or request.form.get("target_role", "").strip()
            or selected_role
        )
        pasted_jd = request.form.get("job_description", "")
        file_storage = request.files.get("resume_file")
        pasted_resume = request.form.get("resume_text", "")
        upload_text = ""
        if (file_storage and file_storage.filename) or (pasted_resume or "").strip():
            try:
                upload_text = extract_resume_text(file_storage, pasted_resume)
            except ValueError as error:
                flash(str(error), "error")
        if upload_text:
            resume_text = upload_text
            user.last_resume_text = upload_text
            db.session.commit()
        if not resume_text:
            flash("Upload or paste a resume first, or analyze one on Resume Analysis.", "error")
        else:
            try:
                if selected_role:
                    user.target_role = selected_role
                    user.preferred_domain = selected_role
                    db.session.commit()
                student = student_match_payload(user)
                result = simulate_ats(student, resume_text, selected_role, pasted_jd)
                record = AtsSimulation(
                    user_id=user.id,
                    target_role=result["target_role"],
                    job_description=(pasted_jd or "").strip() or None,
                    ats_score=result["ats_score"],
                    keyword_score=result["keyword_score"],
                    role_relevance_score=result["role_relevance_score"],
                    structure_score=result["structure_score"],
                    result_json=json.dumps(result),
                )
                db.session.add(record)
                db.session.commit()
                return redirect(url_for("ats_simulator_detail", simulation_id=record.id))
            except Exception:
                db.session.rollback()
                flash("The simulation could not run. Try a clearer resume or job description.", "error")

    history = (
        AtsSimulation.query.filter_by(user_id=user.id)
        .order_by(AtsSimulation.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "ats_simulator.html",
        user=user,
        result=None,
        resume_text=resume_text,
        pasted_jd=pasted_jd,
        selected_role=selected_role,
        roles=ROLE_NAMES,
        history=history,
        simulation=None,
        latest_jd=latest_jd,
    )


@app.route("/ats-simulator/<int:simulation_id>")
@login_required
def ats_simulator_detail(simulation_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    simulation = db.session.get(AtsSimulation, simulation_id)
    if simulation is None or simulation.user_id != user.id:
        flash("That simulation was not found.", "error")
        return redirect(url_for("ats_simulator"))

    history = (
        AtsSimulation.query.filter_by(user_id=user.id)
        .order_by(AtsSimulation.created_at.desc())
        .limit(8)
        .all()
    )
    resume_text = stored_resume_text(user)
    return render_template(
        "ats_simulator.html",
        user=user,
        result=simulation.result(),
        resume_text=resume_text,
        pasted_jd=simulation.job_description or "",
        selected_role=simulation.target_role or user_target_role(user),
        roles=ROLE_NAMES,
        history=history,
        simulation=simulation,
        latest_jd=None,
    )


RESUME_INTERVIEW_KEY = "resume_interview_id"


def _resume_interview_record(user):
    session_id = session.get(RESUME_INTERVIEW_KEY)
    if not session_id:
        return None
    record = db.session.get(ResumeInterviewSession, session_id)
    if record is None or record.user_id != user.id:
        session.pop(RESUME_INTERVIEW_KEY, None)
        return None
    payload = record.result()
    if payload.get("status") != "in_progress":
        session.pop(RESUME_INTERVIEW_KEY, None)
        return None
    return record


def _save_resume_interview_payload(record, payload):
    record.result_json = json.dumps(payload)
    record.question_count = len(payload.get("answers") or [])
    db.session.commit()


def _renumber_resume_questions(questions):
    total = len(questions)
    for index, item in enumerate(questions, start=1):
        item["index"] = index
        item["total"] = total
    return questions


def _finish_resume_interview(user, record, payload):
    questions = payload.get("questions") or []
    answers = payload.get("answers") or []
    claims = {"skills": payload.get("claims_skills") or []}
    payload["report"] = build_report(questions, answers, claims)
    payload["status"] = "complete"
    payload["feedback"] = None
    record.question_count = len(answers)
    record.difficulty = payload.get("difficulty") or record.difficulty
    _save_resume_interview_payload(record, payload)
    session.pop(RESUME_INTERVIEW_KEY, None)
    return record


@app.route("/resume-interview", methods=["GET", "POST"])
@login_required
def resume_interview():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    resume_text = stored_resume_text(user)
    claims = extract_resume_claims(user, resume_text) if resume_text else None
    target = user_target_role(user)
    hotspots = build_hotspots(claims, target) if claims else []

    if request.method == "POST":
        if not resume_text:
            flash("Upload your resume first to generate personalized interview questions.", "error")
            return redirect(url_for("resume_interview"))
        difficulty = (request.form.get("difficulty") or "mixed").strip().lower()
        if difficulty not in ("beginner", "intermediate", "advanced", "mixed"):
            difficulty = "mixed"
        try:
            count = int(request.form.get("count") or 10)
        except (TypeError, ValueError):
            count = 10
        if count not in (5, 10, 15):
            count = 10
        try:
            questions = generate_questions(claims, target, difficulty, count)
        except Exception:
            questions = []
        if not questions:
            flash(
                "Could not build resume-based questions yet. Add projects and skills on Resume Analysis, then try again.",
                "error",
            )
            return redirect(url_for("resume_interview"))
        payload = {
            "status": "in_progress",
            "difficulty": difficulty,
            "count": count,
            "questions": questions,
            "index": 0,
            "answers": [],
            "feedback": None,
            "followups_added": 0,
            "claims_skills": claims.get("skills") or [],
            "hotspots": hotspots,
            "target_role": target,
        }
        record = ResumeInterviewSession(
            user_id=user.id,
            difficulty=difficulty,
            question_count=0,
            result_json=json.dumps(payload),
        )
        db.session.add(record)
        db.session.commit()
        session[RESUME_INTERVIEW_KEY] = record.id
        return redirect(url_for("resume_interview_play"))

    history = []
    for item in (
        ResumeInterviewSession.query.filter_by(user_id=user.id)
        .order_by(ResumeInterviewSession.created_at.desc())
        .limit(12)
        .all()
    ):
        if item.result().get("status") == "complete":
            history.append(item)
        if len(history) >= 6:
            break
    return render_template(
        "resume_interview.html",
        user=user,
        has_resume=bool(resume_text),
        hotspots=hotspots,
        target=target,
        history=history,
        active_session=bool(_resume_interview_record(user)),
    )


@app.route("/resume-interview/play", methods=["GET", "POST"])
@login_required
def resume_interview_play():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    record = _resume_interview_record(user)
    if not record:
        flash("Start a resume interview from your own resume first.", "error")
        return redirect(url_for("resume_interview"))

    payload = record.result()
    questions = payload.get("questions") or []
    index = int(payload.get("index") or 0)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        try:
            if action == "submit":
                if index >= len(questions):
                    finished = _finish_resume_interview(user, record, payload)
                    return redirect(url_for("resume_interview_report", session_id=finished.id))
                if payload.get("feedback"):
                    flash("Review the feedback, then continue to the next question.", "error")
                else:
                    raw = request.form.get("answer", "")
                    answer = (raw or "").strip()[:4000]
                    current = questions[index]
                    feedback = evaluate_resume_answer(current, answer)
                    followup = feedback.get("followup")
                    if followup and int(payload.get("followups_added") or 0) < 3:
                        questions.insert(index + 1, followup)
                        _renumber_resume_questions(questions)
                        payload["questions"] = questions
                        payload["followups_added"] = int(payload.get("followups_added") or 0) + 1
                        feedback["followup_queued"] = followup.get("question")
                    else:
                        feedback["followup_queued"] = None
                    payload["feedback"] = feedback
                    _save_resume_interview_payload(record, payload)
            elif action == "skip":
                if payload.get("feedback"):
                    flash("Use Next Question to continue.", "error")
                elif index < len(questions):
                    current = questions[index]
                    skipped = evaluate_resume_answer(current, "")
                    skipped["skipped"] = True
                    skipped["answer"] = ""
                    answers = list(payload.get("answers") or [])
                    answers.append(skipped)
                    payload["answers"] = answers
                    payload["feedback"] = None
                    payload["index"] = index + 1
                    _save_resume_interview_payload(record, payload)
                    index = payload["index"]
                    if index >= len(questions):
                        finished = _finish_resume_interview(user, record, payload)
                        return redirect(url_for("resume_interview_report", session_id=finished.id))
            elif action == "next":
                feedback = payload.get("feedback")
                if not feedback:
                    flash("Submit or skip this question first.", "error")
                else:
                    answers = list(payload.get("answers") or [])
                    answers.append(feedback)
                    payload["answers"] = answers
                    payload["feedback"] = None
                    payload["index"] = index + 1
                    _save_resume_interview_payload(record, payload)
                    index = payload["index"]
                    if index >= len(questions):
                        finished = _finish_resume_interview(user, record, payload)
                        return redirect(url_for("resume_interview_report", session_id=finished.id))
            elif action == "quit":
                payload["status"] = "abandoned"
                _save_resume_interview_payload(record, payload)
                session.pop(RESUME_INTERVIEW_KEY, None)
                flash("Resume interview ended. You can start again anytime.", "success")
                return redirect(url_for("resume_interview"))
        except Exception:
            session.pop(RESUME_INTERVIEW_KEY, None)
            flash("The interview session could not continue. Please start again.", "error")
            return redirect(url_for("resume_interview"))

        record = _resume_interview_record(user)
        if not record:
            return redirect(url_for("resume_interview"))
        payload = record.result()
        questions = payload.get("questions") or []
        index = int(payload.get("index") or 0)

    if index >= len(questions):
        finished = _finish_resume_interview(user, record, payload)
        return redirect(url_for("resume_interview_report", session_id=finished.id))

    current = questions[index]
    total = len(questions)
    progress = int((index / total) * 100) if total else 0
    feedback = payload.get("feedback")
    if feedback:
        progress = int(((index + 1) / total) * 100) if total else 0

    return render_template(
        "resume_interview_play.html",
        user=user,
        question=current,
        question_number=index + 1,
        total_questions=total,
        progress=progress,
        feedback=feedback,
        category_label=CATEGORY_LABELS.get(current.get("category"), "Question"),
        difficulty=(current.get("difficulty") or payload.get("difficulty") or "mixed").title(),
    )


@app.route("/resume-interview/<int:session_id>")
@login_required
def resume_interview_report(session_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    record = db.session.get(ResumeInterviewSession, session_id)
    if record is None or record.user_id != user.id:
        flash("That resume interview was not found.", "error")
        return redirect(url_for("resume_interview"))

    result = record.result()
    if result.get("status") == "in_progress":
        session[RESUME_INTERVIEW_KEY] = record.id
        return redirect(url_for("resume_interview_play"))
    if result.get("status") != "complete":
        flash("That resume interview was not found.", "error")
        return redirect(url_for("resume_interview"))

    return render_template(
        "resume_interview_report.html",
        user=user,
        record=record,
        result=result,
        report=result.get("report") or {},
        answers=result.get("answers") or [],
    )


def _role_question_set_for(user, set_id):
    record = db.session.get(RoleQuestionSet, set_id)
    if record is None or record.user_id != user.id:
        return None
    return record


def _save_role_question_payload(record, payload):
    answers = [item for item in (payload.get("answers") or []) if not item.get("skipped")]
    scores = [int(item.get("score") or 0) for item in answers]
    record.avg_score = int(round(sum(scores) / len(scores))) if scores else None
    record.question_count = len(payload.get("questions") or [])
    record.result_json = json.dumps(payload)
    db.session.commit()


def _create_role_question_set(user, generated, difficulty, jd_text=""):
    payload = dict(generated)
    payload["jd_text"] = (jd_text or "")[:20000]
    payload["index"] = 0
    payload["answers"] = []
    payload["feedback"] = None
    payload["followups_added"] = 0
    payload["difficulty"] = difficulty
    record = RoleQuestionSet(
        user_id=user.id,
        target_role=generated.get("role") or "",
        difficulty=difficulty,
        question_count=len(generated.get("questions") or []),
        result_json=json.dumps(payload),
    )
    db.session.add(record)
    db.session.commit()
    return record


@app.route("/interview-questions", methods=["GET", "POST"])
@login_required
def interview_questions():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    student = student_match_payload(user)
    target = user_target_role(user)
    latest_jd = (
        JobAnalysis.query.filter_by(user_id=user.id)
        .order_by(JobAnalysis.created_at.desc())
        .first()
    )
    pasted = (latest_jd.job_description if latest_jd else "") or ""

    if request.method == "POST":
        action = (request.form.get("action") or "generate").strip().lower()
        custom = request.form.get("custom_role", "").strip()
        chosen = custom or request.form.get("target_role", "").strip() or target
        if not chosen:
            flash("Choose a target role or provide a job description to generate relevant interview questions.", "error")
            return redirect(url_for("interview_questions"))
        pasted = request.form.get("job_description", "")
        use_jd = bool(pasted.strip()) and action != "skip_jd"
        if request.form.get("without_jd"):
            use_jd = False
            pasted = ""
        if use_jd:
            cleaned, error = validate_job_description(pasted)
            if error:
                flash(error, "error")
                return redirect(url_for("interview_questions"))
            pasted = cleaned
        else:
            pasted = ""
        difficulty = (request.form.get("difficulty") or "mixed").strip().lower()
        if difficulty not in ("beginner", "intermediate", "advanced", "mixed"):
            difficulty = "mixed"
        try:
            count = int(request.form.get("count") or 20)
        except (TypeError, ValueError):
            count = 20
        if count not in (10, 20, 30):
            count = 20
        quick = action == "quick"
        weak_topics = None
        exclude = []
        if action == "weak":
            stats = summarize_user_practice(RoleQuestionSet.query.filter_by(user_id=user.id).all())
            weak_topics = [stats["weakest"]] if stats.get("weakest") else None
            if not weak_topics:
                flash("Practice a few questions first so weak areas can be detected.", "error")
                return redirect(url_for("interview_questions"))
            for item in RoleQuestionSet.query.filter_by(user_id=user.id).all():
                for question in item.result().get("questions") or []:
                    exclude.append(question.get("question") or "")
        try:
            if chosen:
                user.target_role = resolve_generator_role(chosen)
                user.preferred_domain = user.target_role
                db.session.commit()
            generated = generate_role_questions(
                chosen,
                student_skills=student["skills"],
                jd_text=pasted,
                student=student if pasted else None,
                resume_text=stored_resume_text(user),
                difficulty=difficulty,
                count=5 if quick else count,
                exclude_questions=exclude,
                weak_topics=weak_topics,
                quick=quick,
            )
        except Exception:
            db.session.rollback()
            flash("Questions could not be generated. Try a clearer role or job description.", "error")
            return redirect(url_for("interview_questions"))
        if not generated.get("questions"):
            flash("No supported skills were found for that role or description. Add a target role or a fuller job description.", "error")
            return redirect(url_for("interview_questions"))
        record = _create_role_question_set(user, generated, difficulty, pasted)
        return redirect(url_for("interview_questions_bank", set_id=record.id))

    history = (
        RoleQuestionSet.query.filter_by(user_id=user.id)
        .order_by(RoleQuestionSet.created_at.desc())
        .limit(8)
        .all()
    )
    stats = summarize_user_practice(history)
    saved = (
        SavedRoleQuestion.query.filter_by(user_id=user.id)
        .order_by(SavedRoleQuestion.created_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "interview_questions.html",
        user=user,
        target=target,
        roles=ROLE_NAMES,
        pasted=pasted,
        history=history,
        stats=stats,
        saved=saved,
        bank=None,
        record=None,
    )


@app.route("/interview-questions/saved")
@login_required
def interview_questions_saved():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    saved = (
        SavedRoleQuestion.query.filter_by(user_id=user.id)
        .order_by(SavedRoleQuestion.created_at.desc())
        .all()
    )
    return render_template("interview_questions_saved.html", user=user, saved=saved)


@app.route("/interview-questions/<int:set_id>")
@login_required
def interview_questions_bank(set_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    record = _role_question_set_for(user, set_id)
    if record is None:
        flash("That question set was not found.", "error")
        return redirect(url_for("interview_questions"))
    payload = record.result()
    performance = topic_performance(payload.get("answers"))
    saved_texts = {
        item.question
        for item in SavedRoleQuestion.query.filter_by(user_id=user.id).all()
    }
    return render_template(
        "interview_questions.html",
        user=user,
        target=record.target_role,
        roles=ROLE_NAMES,
        pasted=payload.get("jd_text") or "",
        history=[],
        stats=summarize_user_practice([record]),
        saved=[],
        bank=payload,
        record=record,
        performance=performance,
        saved_texts=saved_texts,
        categories=ROLE_Q_CATEGORIES,
    )


@app.route("/interview-questions/<int:set_id>/save", methods=["POST"])
@login_required
def interview_questions_save(set_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    record = _role_question_set_for(user, set_id)
    if record is None:
        flash("That question set was not found.", "error")
        return redirect(url_for("interview_questions"))
    try:
        index = int(request.form.get("index") or 0)
    except (TypeError, ValueError):
        index = 0
    questions = record.result().get("questions") or []
    if index < 0 or index >= len(questions):
        flash("That question could not be saved.", "error")
        return redirect(url_for("interview_questions_bank", set_id=set_id))
    item = questions[index]
    exists = SavedRoleQuestion.query.filter_by(user_id=user.id, question=item["question"]).first()
    if exists:
        flash("That question is already in My Saved Questions.", "success")
        return redirect(url_for("interview_questions_bank", set_id=set_id))
    db.session.add(
        SavedRoleQuestion(
            user_id=user.id,
            set_id=record.id,
            question=item["question"],
            topic=item.get("topic"),
            category=item.get("category"),
            difficulty=item.get("difficulty"),
            priority=item.get("priority"),
            explanation=item.get("why"),
        )
    )
    db.session.commit()
    flash("Question saved.", "success")
    return redirect(url_for("interview_questions_bank", set_id=set_id))


@app.route("/interview-questions/<int:set_id>/practice", methods=["GET", "POST"])
@login_required
def interview_questions_practice(set_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    record = _role_question_set_for(user, set_id)
    if record is None:
        flash("That question set was not found.", "error")
        return redirect(url_for("interview_questions"))

    payload = record.result()
    questions = payload.get("questions") or []
    if request.method == "GET" and request.args.get("start"):
        try:
            payload["index"] = max(0, min(int(request.args.get("start")), len(questions) - 1))
        except (TypeError, ValueError):
            payload["index"] = 0
        payload["feedback"] = None
        _save_role_question_payload(record, payload)

    index = int(payload.get("index") or 0)

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        try:
            if action == "submit":
                if index >= len(questions):
                    return redirect(url_for("interview_questions_bank", set_id=record.id))
                if payload.get("feedback"):
                    flash("Review the feedback, then continue.", "error")
                else:
                    answer = (request.form.get("answer") or "").strip()[:4000]
                    current = questions[index]
                    feedback = evaluate_role_answer(current, answer)
                    followup = feedback.get("followup")
                    if followup and int(payload.get("followups_added") or 0) < 3:
                        questions.insert(index + 1, followup)
                        payload["questions"] = questions
                        payload["followups_added"] = int(payload.get("followups_added") or 0) + 1
                        feedback["followup_queued"] = followup.get("question")
                    payload["feedback"] = feedback
                    _save_role_question_payload(record, payload)
            elif action == "skip":
                if payload.get("feedback"):
                    flash("Use Next Question to continue.", "error")
                elif index < len(questions):
                    skipped = evaluate_role_answer(questions[index], "")
                    skipped["skipped"] = True
                    answers = list(payload.get("answers") or [])
                    answers.append(skipped)
                    payload["answers"] = answers
                    payload["feedback"] = None
                    payload["index"] = index + 1
                    _save_role_question_payload(record, payload)
                    index = payload["index"]
            elif action == "next":
                feedback = payload.get("feedback")
                if not feedback:
                    flash("Submit or skip this question first.", "error")
                else:
                    answers = list(payload.get("answers") or [])
                    answers.append(feedback)
                    payload["answers"] = answers
                    payload["feedback"] = None
                    payload["index"] = index + 1
                    _save_role_question_payload(record, payload)
                    index = payload["index"]
        except Exception:
            flash("That practice step could not be saved. Please try again.", "error")
            return redirect(url_for("interview_questions_practice", set_id=set_id))
        payload = record.result()
        questions = payload.get("questions") or []
        index = int(payload.get("index") or 0)

    if index >= len(questions):
        flash("Preparation round complete. Review coverage and weak areas below.", "success")
        return redirect(url_for("interview_questions_bank", set_id=record.id))

    current = questions[index]
    total = len(questions)
    progress = int(((index + (1 if payload.get("feedback") else 0)) / total) * 100) if total else 0
    return render_template(
        "interview_questions_practice.html",
        user=user,
        record=record,
        question=current,
        question_number=index + 1,
        total_questions=total,
        progress=progress,
        feedback=payload.get("feedback"),
        category_label=ROLE_Q_CATEGORIES.get(current.get("category"), "Question"),
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
    role_q_stats = summarize_user_practice(
        RoleQuestionSet.query.filter_by(user_id=user.id).all()
    )
    return render_template(
        "progress.html",
        user=user,
        attempts=attempts,
        role_q_stats=role_q_stats,
    )


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
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("PORT") or IS_PRODUCTION else "127.0.0.1"
    app.run(debug=DEBUG, host=host, port=port)
