import os
import re
from functools import wraps

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from admin import admin_bp, ensure_admin_schema
from config import DEBUG, SECRET_KEY, validate_settings
from ml.profile_strength import collect_skill_gaps, compute_profile_strength
from ml.recommender import recommend_internships, student_has_skills
from models import Application, Internship, User, db
from seed import ensure_admin_user, ensure_demo_student, ensure_sample_internships
from tools import (
    DOMAINS,
    analyze_resume,
    build_roadmap,
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

# Local SQLite database file inside the project
basedir = os.path.abspath(os.path.dirname(__file__))
db_folder = os.path.join(basedir, "database")
db_path = os.path.join(db_folder, "internmatch.db")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
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


APPLICATION_STATUSES = (
    "Applied",
    "Shortlisted",
    "Interview",
    "Selected",
    "Rejected",
)
APPLICATION_PROGRESS = ("Applied", "Shortlisted", "Interview", "Selected")


def normalize_application_status(status):
    if status == "Pending":
        return "Applied"
    if status == "Accepted":
        return "Selected"
    if status in APPLICATION_STATUSES:
        return status
    return "Applied"


def application_timeline(status):
    current = normalize_application_status(status)
    rejected = current == "Rejected"
    steps = []
    current_index = APPLICATION_PROGRESS.index(current) if current in APPLICATION_PROGRESS else 0
    for index, name in enumerate(APPLICATION_PROGRESS):
        if rejected:
            steps.append({"name": name, "done": name == "Applied", "current": False})
        else:
            steps.append(
                {
                    "name": name,
                    "done": index <= current_index,
                    "current": name == current,
                }
            )
    return {"steps": steps, "rejected": rejected, "status": current}


def application_overview(applications):
    statuses = [normalize_application_status(item.status) for item in applications]
    return {
        "total": len(statuses),
        "shortlisted": statuses.count("Shortlisted"),
        "interviews": statuses.count("Interview"),
        "selected": statuses.count("Selected"),
        "rejected": statuses.count("Rejected"),
    }


INTERNSHIP_DOMAINS = [
    "Data Analytics",
    "Data Science",
    "Machine Learning",
    "Python Development",
    "Web Development",
    "Java Development",
    "UI/UX",
    "Cybersecurity",
    "Cloud Computing",
    "Software Testing",
]
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(email and EMAIL_PATTERN.match(email))


def student_match_payload(user):
    resume_skills = session.get("resume_skills", "")
    combined_skills = ", ".join(
        part for part in [user.skills or "", resume_skills] if part
    )
    return {
        "skills": combined_skills,
        "education": user.education or "",
        "preferred_domain": user.preferred_domain or "",
        "preferred_work_mode": user.preferred_work_mode or "",
        "location": user.location or "",
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
        preferred_domain = request.form.get("preferred_domain", "").strip()
        preferred_work_mode = request.form.get("preferred_work_mode", "").strip()
        skills = request.form.get("skills", "").strip()

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
                preferred_work_mode,
                skills,
            ]
        ):
            flash("Please fill in all fields.", "error")
            return render_template("register.html", form=request.form)

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html", form=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html", form=request.form)

        try:
            cgpa = float(cgpa_value)
            if cgpa < 0 or cgpa > 10:
                raise ValueError("CGPA out of range")
        except ValueError:
            flash("Please enter a valid CGPA between 0 and 10.", "error")
            return render_template("register.html", form=request.form)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("This email is already registered. Please log in.", "error")
            return render_template("register.html", form=request.form)

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
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


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
        preferred_domain = request.form.get("preferred_domain", "").strip()
        preferred_work_mode = request.form.get("preferred_work_mode", "").strip()
        skills = request.form.get("skills", "").strip()

        if not all(
            [name, email, education, cgpa_value, location, preferred_domain, preferred_work_mode, skills]
        ):
            flash("Please fill in all profile fields.", "error")
            return render_template("profile.html", user=user)

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("profile.html", user=user)

        try:
            cgpa = float(cgpa_value)
            if cgpa < 0 or cgpa > 10:
                raise ValueError("CGPA out of range")
        except ValueError:
            flash("Please enter a valid CGPA between 0 and 10.", "error")
            return render_template("profile.html", user=user)

        taken = User.query.filter(User.email == email, User.id != user.id).first()
        if taken:
            flash("That email is already used by another account.", "error")
            return render_template("profile.html", user=user)

        user.name = name
        user.email = email
        user.education = education
        user.cgpa = cgpa
        user.location = location
        user.preferred_domain = preferred_domain
        user.preferred_work_mode = preferred_work_mode
        user.skills = skills
        db.session.commit()
        session["user_name"] = user.name
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))
    applications = (
        Application.query.filter_by(user_id=user.id)
        .order_by(Application.applied_date.desc())
        .all()
    )
    overview = application_overview(applications)

    resume_analyzed = bool(session.get("resume_analyzed"))
    profile = compute_profile_strength(user, resume_analyzed=resume_analyzed)
    student = student_match_payload(user)

    internships_available = Internship.query.count() > 0
    need_resume = not student_has_skills(student)
    top_matches = []
    skill_gaps = []
    if internships_available and not need_resume:
        top_matches = recommend_internships(student, Internship.query.all(), top_n=3)
        skill_gaps = collect_skill_gaps(top_matches)

    return render_template(
        "dashboard.html",
        user=user,
        applications=applications,
        overview=overview,
        profile=profile,
        top_matches=top_matches,
        skill_gaps=skill_gaps,
        need_resume=need_resume,
        internships_available=internships_available,
    )


@app.route("/recommendations")
@login_required
def recommendations():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    student = student_match_payload(user)

    internships_available = Internship.query.count() > 0
    need_resume = not student_has_skills(student)
    ranked = []
    if internships_available and not need_resume:
        ranked = recommend_internships(student, Internship.query.all(), top_n=10)

    return render_template(
        "recommendations.html",
        user=user,
        recommendations=ranked,
        need_resume=need_resume,
        internships_available=internships_available,
    )


@app.route("/skill-gap")
@login_required
def skill_gap():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    student = student_match_payload(user)
    internships_available = Internship.query.count() > 0
    need_skills = not student_has_skills(student)
    top_matches = []
    skill_gaps = []
    if internships_available and not need_skills:
        top_matches = recommend_internships(student, Internship.query.all(), top_n=5)
        skill_gaps = collect_skill_gaps(top_matches)

    return render_template(
        "skill_gap.html",
        user=user,
        top_matches=top_matches,
        skill_gaps=skill_gaps,
        need_skills=need_skills,
        internships_available=internships_available,
    )


@app.route("/internships")
def internships():
    search = request.args.get("q", "").strip()
    domain = request.args.get("domain", "").strip()
    location = request.args.get("location", "").strip()
    work_mode = request.args.get("work_mode", "").strip()

    query = Internship.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Internship.title.ilike(like),
                Internship.company.ilike(like),
                Internship.required_skills.ilike(like),
            )
        )

    if domain:
        query = query.filter(Internship.description.ilike(f"%Domain: {domain}%"))

    if location:
        query = query.filter(Internship.location == location)

    if work_mode:
        query = query.filter(Internship.work_mode == work_mode)

    internships_list = query.order_by(Internship.company, Internship.title).all()

    locations = [
        row[0]
        for row in db.session.query(Internship.location)
        .distinct()
        .order_by(Internship.location)
        if row[0]
    ]
    work_modes = [
        row[0]
        for row in db.session.query(Internship.work_mode)
        .distinct()
        .order_by(Internship.work_mode)
        if row[0]
    ]

    return render_template(
        "internships.html",
        internships=internships_list,
        search=search,
        selected_domain=domain,
        selected_location=location,
        selected_work_mode=work_mode,
        domains=INTERNSHIP_DOMAINS,
        locations=locations,
        work_modes=work_modes,
        total=len(internships_list),
        has_filters=bool(search or domain or location or work_mode),
    )


@app.route("/internship/<int:internship_id>")
def internship_detail(internship_id):
    internship = db.session.get(Internship, internship_id)
    if internship is None:
        flash("That internship was not found.", "error")
        return redirect(url_for("internships"))

    already_applied = False
    if session.get("user_id"):
        already_applied = (
            Application.query.filter_by(
                user_id=session["user_id"],
                internship_id=internship.id,
            ).first()
            is not None
        )

    domain = "General"
    if internship.description and internship.description.startswith("Domain:"):
        domain = internship.description.split(".", 1)[0].replace("Domain:", "").strip()

    return render_template(
        "internship_detail.html",
        internship=internship,
        already_applied=already_applied,
        domain=domain,
    )


@app.route("/internship/<int:internship_id>/apply", methods=["POST"])
@login_required
def apply_internship(internship_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    internship = db.session.get(Internship, internship_id)
    if internship is None:
        flash("That internship was not found.", "error")
        return redirect(url_for("internships"))

    existing = Application.query.filter_by(
        user_id=user.id,
        internship_id=internship.id,
    ).first()
    if existing:
        flash("Already Applied", "error")
        return redirect(url_for("internship_detail", internship_id=internship.id))

    application = Application(
        user_id=user.id,
        internship_id=internship.id,
        status="Applied",
    )
    db.session.add(application)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Already Applied", "error")
        return redirect(url_for("internship_detail", internship_id=internship.id))

    flash("Application submitted.", "success")
    return redirect(url_for("my_applications"))


@app.route("/applications")
@login_required
def my_applications():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    applications = (
        Application.query.filter_by(user_id=user.id)
        .order_by(Application.applied_date.desc())
        .all()
    )
    cards = []
    for item in applications:
        timeline = application_timeline(item.status)
        cards.append({"application": item, "timeline": timeline})

    return render_template(
        "applications.html",
        user=user,
        applications=cards,
        statuses=APPLICATION_STATUSES,
    )


@app.route("/applications/<int:application_id>/status", methods=["POST"])
@login_required
def update_application_status(application_id):
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    application = db.session.get(Application, application_id)
    if application is None:
        flash("That application was not found.", "error")
        return redirect(url_for("my_applications"))
    if application.user_id != user.id:
        abort(403)

    new_status = request.form.get("status", "").strip()
    if new_status not in APPLICATION_STATUSES:
        flash("Please choose a valid application status.", "error")
        return redirect(url_for("my_applications"))

    application.status = new_status
    db.session.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("my_applications"))


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
            result = analyze_resume(resume_text, user.skills, user.preferred_domain)
            extracted = [
                skill
                for skill in result.get("found_skills", [])
                if skill != "No clear technical skills detected"
            ]
            session["resume_analyzed"] = True
            session["resume_skills"] = ", ".join(extracted)
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


@app.route("/career-roadmap", methods=["GET", "POST"])
@login_required
def career_roadmap():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    domain = user.preferred_domain
    if request.method == "POST":
        domain = request.form.get("domain", domain)

    selected, steps = build_roadmap(domain, user.skills)
    return render_template(
        "career_roadmap.html",
        user=user,
        selected=selected,
        steps=steps,
        domains=DOMAINS,
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


@app.route("/interview-arena", methods=["GET", "POST"])
@login_required
def interview_arena():
    user = get_current_user()
    if user is None:
        return redirect(url_for("login"))

    selected = session.get("arena_domain") or user.preferred_domain
    current_question = None
    question_number = 0
    total_questions = 5
    feedback = None
    report = None
    average = None
    rank = None
    finished = False
    progress = 0

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start":
            selected = request.form.get("domain", selected)
            selected, question_list = get_interview_questions(selected)
            session["arena_domain"] = selected
            session["arena_index"] = 0
            session["arena_results"] = []
            session.pop("arena_feedback", None)
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
            selected = user.preferred_domain

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
        selected=user.preferred_domain,
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
    os.makedirs(db_folder, exist_ok=True)
    db.create_all()
    ensure_admin_schema()
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
