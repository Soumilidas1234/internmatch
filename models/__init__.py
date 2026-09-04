from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# Shared database object used by the whole app
db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    education = db.Column(db.String(200))
    cgpa = db.Column(db.Float)
    location = db.Column(db.String(100))
    preferred_domain = db.Column(db.String(100))
    preferred_work_mode = db.Column(db.String(50))
    skills = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    target_role = db.Column(db.String(120))
    resume_analyzed_count = db.Column(db.Integer, default=0, nullable=False)
    last_resume_text = db.Column(db.Text)

    # One user can have many applications
    applications = db.relationship("Application", back_populates="user", lazy=True)

    def __repr__(self):
        return f"<User {self.name}>"


class Internship(db.Model):
    __tablename__ = "internships"

    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    required_skills = db.Column(db.Text)
    location = db.Column(db.String(100))
    work_mode = db.Column(db.String(50))
    duration = db.Column(db.String(50))
    stipend = db.Column(db.String(50))

    # One internship can have many applications
    applications = db.relationship("Application", back_populates="internship", lazy=True)

    def __repr__(self):
        return f"<Internship {self.title}>"


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("user_id", "internship_id", name="uq_user_internship"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    internship_id = db.Column(db.Integer, db.ForeignKey("internships.id"), nullable=False)
    status = db.Column(db.String(50), default="Applied")
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Links back to the related user and internship
    user = db.relationship("User", back_populates="applications")
    internship = db.relationship("Internship", back_populates="applications")

    def __repr__(self):
        return f"<Application {self.id}>"


class ExamAttempt(db.Model):
    """Stores AI examiner attempts so students can see improvement over time."""

    __tablename__ = "exam_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(120))
    overall_score = db.Column(db.Integer, default=0)
    topic_scores = db.Column(db.Text)
    mistakes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="exam_attempts")

    def topic_map(self):
        import json

        try:
            return json.loads(self.topic_scores or "{}")
        except (TypeError, ValueError):
            return {}

    def mistake_list(self):
        import json

        try:
            return json.loads(self.mistakes or "[]")
        except (TypeError, ValueError):
            return []

    def __repr__(self):
        return f"<ExamAttempt {self.id}>"


class JobAnalysis(db.Model):
    """Saved job-description analyses for one logged-in student. Not an application."""

    __tablename__ = "job_analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_title = db.Column(db.String(150))
    job_description = db.Column(db.Text, nullable=False)
    detected_skills = db.Column(db.Text)
    matching_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    match_score = db.Column(db.Integer, default=0)
    result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="job_analyses")

    def result(self):
        import json

        try:
            return json.loads(self.result_json or "{}")
        except (TypeError, ValueError):
            return {}

    def __repr__(self):
        return f"<JobAnalysis {self.id}>"


class AtsSimulation(db.Model):
    """Saved ATS-style resume simulations. Educational only; not a real ATS result."""

    __tablename__ = "ats_simulations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(120))
    job_description = db.Column(db.Text)
    ats_score = db.Column(db.Integer, default=0)
    keyword_score = db.Column(db.Integer, default=0)
    role_relevance_score = db.Column(db.Integer, default=0)
    structure_score = db.Column(db.Integer, default=0)
    result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="ats_simulations")

    def result(self):
        import json

        try:
            return json.loads(self.result_json or "{}")
        except (TypeError, ValueError):
            return {}

    def __repr__(self):
        return f"<AtsSimulation {self.id}>"


class ResumeInterviewSession(db.Model):
    """Saved resume-based interview practice. Stores Q&A JSON, not the resume."""

    __tablename__ = "resume_interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    difficulty = db.Column(db.String(20))
    question_count = db.Column(db.Integer, default=0)
    result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="resume_interview_sessions")

    def result(self):
        import json

        try:
            return json.loads(self.result_json or "{}")
        except (TypeError, ValueError):
            return {}

    def __repr__(self):
        return f"<ResumeInterviewSession {self.id}>"


class RoleQuestionSet(db.Model):
    """Generated role/JD interview question bank plus practice answers. Not an exam."""

    __tablename__ = "role_question_sets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role = db.Column(db.String(120))
    difficulty = db.Column(db.String(20))
    question_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Integer)
    result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="role_question_sets")

    def result(self):
        import json

        try:
            return json.loads(self.result_json or "{}")
        except (TypeError, ValueError):
            return {}

    def __repr__(self):
        return f"<RoleQuestionSet {self.id}>"


class SavedRoleQuestion(db.Model):
    """Questions a student chose to revisit. Scoped to the logged-in user."""

    __tablename__ = "saved_role_questions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question", name="uq_user_saved_role_question"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    set_id = db.Column(db.Integer, db.ForeignKey("role_question_sets.id"))
    question = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(120))
    category = db.Column(db.String(40))
    difficulty = db.Column(db.String(20))
    priority = db.Column(db.String(20))
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="saved_role_questions")

    def __repr__(self):
        return f"<SavedRoleQuestion {self.id}>"
