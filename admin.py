"""Admin dashboard routes for InternMatch AI. Students cannot access these pages."""

from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models import ExamAttempt, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def is_admin_user(user):
    return bool(user and getattr(user, "is_admin", False))


def admin_required(view_func):
    """Block anyone who is not a logged-in administrator."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in as an administrator.", "error")
            return redirect(url_for("admin.login"))

        user = db.session.get(User, session.get("user_id"))
        if user is None:
            session.clear()
            flash("Please log in as an administrator.", "error")
            return redirect(url_for("admin.login"))

        if not is_admin_user(user):
            abort(403)

        return view_func(*args, **kwargs)

    return wrapper


def current_admin():
    user = db.session.get(User, session.get("user_id"))
    if not is_admin_user(user):
        return None
    return user


def _prep_admin_redirect():
    flash("Internship management is disabled. Use analytics and student records.", "success")
    return redirect(url_for("admin.dashboard"))


def ensure_admin_schema():
    """Add is_admin to existing SQLite users without wiping data."""
    columns = db.session.execute(db.text("PRAGMA table_info(users)")).fetchall()
    names = {row[1] for row in columns}
    if "is_admin" not in names:
        db.session.execute(
            db.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
        )
        db.session.commit()


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("admin/login.html")

        user = User.query.filter_by(email=email).first()
        if user and is_admin_user(user) and check_password_hash(user.password, password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash("Login successful.", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Invalid admin email or password.", "error")

    return render_template("admin/login.html")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    admin = current_admin()
    students = User.query.filter_by(is_admin=False).all()
    attempts = ExamAttempt.query.order_by(ExamAttempt.created_at.desc()).all()
    role_counts = {}
    gap_counts = {}
    mistake_counts = {}
    readiness_scores = []

    from ml.prep import interview_readiness, role_readiness_for, split_known_missing, user_target_role
    from ml.profile_strength import compute_profile_strength
    from ml.recommender import student_has_skills

    latest_by_user = {}
    for attempt in attempts:
        latest_by_user.setdefault(attempt.user_id, attempt)

    for student in students:
        role = user_target_role(student)
        role_counts[role] = role_counts.get(role, 0) + 1
        _have, missing, _req = split_known_missing(student.skills or "", role)
        for skill in missing:
            gap_counts[skill] = gap_counts.get(skill, 0) + 1
        payload = {
            "skills": student.skills or "",
            "education": student.education or "",
            "preferred_domain": role,
            "preferred_work_mode": student.preferred_work_mode or "",
            "location": student.location or "",
            "target_role": role,
        }
        match = role_readiness_for(payload, role) if student_has_skills(payload) else {}
        profile = compute_profile_strength(
            student,
            resume_analyzed=bool(student.resume_analyzed_count),
        )
        readiness_scores.append(
            interview_readiness(profile["score"], match, latest_by_user.get(student.id))["score"]
        )

    for attempt in attempts:
        for item in attempt.mistake_list():
            topic = item.get("topic") or "General"
            mistake_counts[topic] = mistake_counts.get(topic, 0) + int(item.get("mistakes") or 0)

    avg_exam = (
        round(sum(item.overall_score or 0 for item in attempts) / len(attempts))
        if attempts
        else None
    )
    avg_readiness = (
        round(sum(readiness_scores) / len(readiness_scores)) if readiness_scores else None
    )
    resume_total = sum(student.resume_analyzed_count or 0 for student in students)
    stats = {
        "students": len(students),
        "exams": len(attempts),
        "resume_analyses": resume_total,
        "avg_exam": avg_exam,
        "avg_readiness": avg_readiness,
        "top_role": max(role_counts, key=role_counts.get) if role_counts else "—",
        "top_gap": max(gap_counts, key=gap_counts.get) if gap_counts else "—",
        "top_mistake": max(mistake_counts, key=mistake_counts.get) if mistake_counts else "—",
    }
    return render_template(
        "admin/dashboard.html",
        admin=admin,
        stats=stats,
        role_counts=sorted(role_counts.items(), key=lambda item: -item[1])[:8],
        gap_counts=sorted(gap_counts.items(), key=lambda item: -item[1])[:8],
        mistake_counts=sorted(mistake_counts.items(), key=lambda item: -item[1])[:8],
        active_page="dashboard",
    )


@admin_bp.route("/students")
@admin_required
def students():
    admin = current_admin()
    students = (
        User.query.filter_by(is_admin=False).order_by(User.name.asc()).all()
    )
    return render_template(
        "admin/students.html",
        admin=admin,
        students=students,
        active_page="students",
    )


@admin_bp.route("/internships")
@admin_required
def internships():
    return _prep_admin_redirect()


@admin_bp.route("/internships/new", methods=["GET", "POST"])
@admin_required
def add_internship():
    return _prep_admin_redirect()


@admin_bp.route("/internships/<int:internship_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_internship(internship_id):
    return _prep_admin_redirect()


@admin_bp.route("/internships/<int:internship_id>/delete", methods=["GET", "POST"])
@admin_required
def delete_internship(internship_id):
    return _prep_admin_redirect()


@admin_bp.route("/applications")
@admin_required
def applications():
    return _prep_admin_redirect()


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
@admin_required
def update_application_status(application_id):
    return _prep_admin_redirect()
