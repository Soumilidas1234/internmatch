"""Create the demo student, admin account, and prep-schema columns on startup.

Sample internship rows may still be inserted into leftover tables. Those
listings are not shown in the student interface.
"""

from werkzeug.security import generate_password_hash

from config import ADMIN_EMAIL, ADMIN_PASSWORD, DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD
from models import Internship, User, db


def _set_password(user, password):
    user.password = generate_password_hash(password, method="pbkdf2:sha256")


def ensure_admin_user():
    """Create or update the admin account from environment variables."""
    if not ADMIN_PASSWORD:
        return

    admin = User.query.filter_by(email=ADMIN_EMAIL).first()
    if admin:
        admin.is_admin = True
        admin.name = admin.name or "InternMatch Admin"
        _set_password(admin, ADMIN_PASSWORD)
        db.session.commit()
        return

    admin = User(
        name="InternMatch Admin",
        email=ADMIN_EMAIL,
        password=generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256"),
        education="Administrator",
        cgpa=None,
        location="Local",
        preferred_domain="Administration",
        preferred_work_mode="Remote",
        skills="System management",
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()


def ensure_demo_student():
    """Create the examiner demo student with a filled profile."""
    if not DEMO_STUDENT_PASSWORD:
        return

    student = User.query.filter_by(email=DEMO_STUDENT_EMAIL).first()
    profile = {
        "name": "Demo Student",
        "education": "BCA",
        "cgpa": 8.2,
        "location": "Bengaluru",
        "preferred_domain": "Web Development",
        "target_role": "Web Developer",
        "preferred_work_mode": "Hybrid",
        "skills": "Python, HTML, CSS, JavaScript, Flask, SQL, Git",
        "is_admin": False,
    }
    if student:
        for field, value in profile.items():
            setattr(student, field, value)
        _set_password(student, DEMO_STUDENT_PASSWORD)
        db.session.commit()
        return

    student = User(
        email=DEMO_STUDENT_EMAIL,
        password=generate_password_hash(DEMO_STUDENT_PASSWORD, method="pbkdf2:sha256"),
        **profile,
    )
    db.session.add(student)
    db.session.commit()


def ensure_prep_schema():
    """Add preparation columns without wiping existing users."""
    columns = db.session.execute(db.text("PRAGMA table_info(users)")).fetchall()
    names = {row[1] for row in columns}
    if "target_role" not in names:
        db.session.execute(db.text("ALTER TABLE users ADD COLUMN target_role VARCHAR(120)"))
    if "resume_analyzed_count" not in names:
        db.session.execute(
            db.text("ALTER TABLE users ADD COLUMN resume_analyzed_count INTEGER NOT NULL DEFAULT 0")
        )
    if "last_resume_text" not in names:
        db.session.execute(db.text("ALTER TABLE users ADD COLUMN last_resume_text TEXT"))
    db.session.commit()


def ensure_sample_internships():
    """Load fictional sample internships from CSV if the table is empty."""
    if Internship.query.count() > 0:
        return
    from import_internships import import_internships

    import_internships()
