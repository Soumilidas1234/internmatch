"""Admin dashboard routes for InternMatch AI. Students cannot access these pages."""

from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from models import Application, Internship, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ADMIN_STATUSES = (
    "Pending",
    "Applied",
    "Shortlisted",
    "Interview",
    "Selected",
    "Accepted",
    "Rejected",
)
WORK_MODES = ("Remote", "Hybrid", "On-site")
INTERNSHIP_FIELDS = (
    "company",
    "title",
    "description",
    "required_skills",
    "location",
    "work_mode",
    "duration",
    "stipend",
)


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


def internship_form_data():
    data = {field: request.form.get(field, "").strip() for field in INTERNSHIP_FIELDS}
    missing = [field.replace("_", " ") for field, value in data.items() if not value]
    return data, missing


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
    pending_statuses = ("Pending", "Applied")
    accepted_statuses = ("Accepted", "Selected")

    stats = {
        "students": User.query.filter_by(is_admin=False).count(),
        "internships": Internship.query.count(),
        "applications": Application.query.count(),
        "pending": Application.query.filter(Application.status.in_(pending_statuses)).count(),
        "accepted": Application.query.filter(Application.status.in_(accepted_statuses)).count(),
        "rejected": Application.query.filter_by(status="Rejected").count(),
    }
    recent_applications = (
        Application.query.order_by(Application.applied_date.desc()).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html",
        admin=admin,
        stats=stats,
        recent_applications=recent_applications,
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
    admin = current_admin()
    internships = Internship.query.order_by(Internship.company, Internship.title).all()
    return render_template(
        "admin/internships.html",
        admin=admin,
        internships=internships,
        active_page="internships",
    )


@admin_bp.route("/internships/new", methods=["GET", "POST"])
@admin_required
def add_internship():
    admin = current_admin()
    if request.method == "POST":
        data, missing = internship_form_data()
        if missing:
            flash("Please fill in all internship fields.", "error")
            return render_template(
                "admin/internship_form.html",
                admin=admin,
                internship=data,
                work_modes=WORK_MODES,
                form_title="Add internship",
                active_page="internships",
            )

        internship = Internship(**data)
        db.session.add(internship)
        db.session.commit()
        flash("Internship added.", "success")
        return redirect(url_for("admin.internships"))

    empty = {field: "" for field in INTERNSHIP_FIELDS}
    return render_template(
        "admin/internship_form.html",
        admin=admin,
        internship=empty,
        work_modes=WORK_MODES,
        form_title="Add internship",
        active_page="internships",
    )


@admin_bp.route("/internships/<int:internship_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_internship(internship_id):
    admin = current_admin()
    internship = db.session.get(Internship, internship_id)
    if internship is None:
        flash("That internship was not found.", "error")
        return redirect(url_for("admin.internships"))

    if request.method == "POST":
        data, missing = internship_form_data()
        if missing:
            flash("Please fill in all internship fields.", "error")
            return render_template(
                "admin/internship_form.html",
                admin=admin,
                internship=data,
                internship_id=internship.id,
                work_modes=WORK_MODES,
                form_title="Edit internship",
                active_page="internships",
            )

        for field, value in data.items():
            setattr(internship, field, value)
        db.session.commit()
        flash("Internship updated.", "success")
        return redirect(url_for("admin.internships"))

    return render_template(
        "admin/internship_form.html",
        admin=admin,
        internship=internship,
        internship_id=internship.id,
        work_modes=WORK_MODES,
        form_title="Edit internship",
        active_page="internships",
    )


@admin_bp.route("/internships/<int:internship_id>/delete", methods=["GET", "POST"])
@admin_required
def delete_internship(internship_id):
    admin = current_admin()
    internship = db.session.get(Internship, internship_id)
    if internship is None:
        flash("That internship was not found.", "error")
        return redirect(url_for("admin.internships"))

    related = Application.query.filter_by(internship_id=internship.id).count()
    if request.method == "POST":
        Application.query.filter_by(internship_id=internship.id).delete()
        db.session.delete(internship)
        db.session.commit()
        flash("Internship deleted.", "success")
        return redirect(url_for("admin.internships"))

    return render_template(
        "admin/internship_delete.html",
        admin=admin,
        internship=internship,
        related=related,
        active_page="internships",
    )


@admin_bp.route("/applications")
@admin_required
def applications():
    admin = current_admin()
    applications = (
        Application.query.order_by(Application.applied_date.desc()).all()
    )
    return render_template(
        "admin/applications.html",
        admin=admin,
        applications=applications,
        statuses=ADMIN_STATUSES,
        active_page="applications",
    )


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
@admin_required
def update_application_status(application_id):
    application = db.session.get(Application, application_id)
    if application is None:
        flash("That application was not found.", "error")
        return redirect(url_for("admin.applications"))

    new_status = request.form.get("status", "").strip()
    if new_status not in ADMIN_STATUSES:
        flash("Please choose a valid application status.", "error")
        return redirect(url_for("admin.applications"))

    application.status = new_status
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Could not update that application.", "error")
        return redirect(url_for("admin.applications"))

    flash("Application status updated.", "success")
    return redirect(url_for("admin.applications"))
