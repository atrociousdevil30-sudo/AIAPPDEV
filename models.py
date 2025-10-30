from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'hr' or 'candidate'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidates = db.relationship('Candidate', 
                               foreign_keys='Candidate.recruiter_id', 
                               backref=db.backref('recruiter', lazy=True), 
                               lazy=True)
    interviews = db.relationship('Interview', 
                               foreign_keys='Interview.interviewer_id',
                               backref=db.backref('interviewer', lazy=True), 
                               lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Candidate(db.Model):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(50), default='new')  # new, in_review, interview_scheduled, etc.
    ats_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', 
                            foreign_keys='Resume.candidate_id', 
                            backref=db.backref('candidate', lazy=True), 
                            lazy=True)
    applications = db.relationship('Application', 
                                 foreign_keys='Application.candidate_id',
                                 backref=db.backref('candidate', lazy=True), 
                                 lazy=True)
    interviews = db.relationship('Interview',
                               secondary='applications',
                               primaryjoin='Application.candidate_id == Candidate.id',
                               secondaryjoin='and_(Application.id == Interview.application_id, Application.candidate_id == Candidate.id)',
                               viewonly=True,
                               lazy=True)
    notes = db.relationship('Note', 
                          foreign_keys='Note.candidate_id',
                          backref=db.backref('candidate', lazy=True), 
                          lazy=True)

class Resume(db.Model):
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    parsed_data = db.Column(db.JSON, nullable=True)  # Store parsed resume data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Extracted fields (also stored in parsed_data for easy access)
    skills = db.relationship('Skill', secondary='resume_skills', backref=db.backref('resumes', lazy=True))
    experiences = db.relationship('Experience', backref='resume', lazy=True)
    education = db.relationship('Education', backref='resume', lazy=True)

class Skill(db.Model):
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=True)

# Association table for many-to-many relationship between resumes and skills
resume_skills = db.Table('resume_skills',
    db.Column('resume_id', db.Integer, db.ForeignKey('resumes.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'), primary_key=True),
    db.Column('relevance', db.Float, default=0.0)  # How relevant is this skill to the job
)

class Experience(db.Model):
    __tablename__ = 'experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Null means current position
    description = db.Column(db.Text, nullable=True)
    is_current = db.Column(db.Boolean, default=False)

class Education(db.Model):
    __tablename__ = 'educations'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    degree = db.Column(db.String(200), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    field_of_study = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    gpa = db.Column(db.Float, nullable=True)

class JobPosting(db.Model):
    __tablename__ = 'job_postings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='job_posting', lazy=True)

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_postings.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    status = db.Column(db.String(50), default='applied')  # applied, in_review, interview, offered, hired, rejected
    ats_score = db.Column(db.Float, nullable=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interviews = db.relationship('Interview', backref='application', lazy=True)
    notes = db.relationship('Note', backref='application', lazy=True)

class Interview(db.Model):
    __tablename__ = 'interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    status = db.Column(db.String(50), default='scheduled')  # scheduled, in_progress, completed, cancelled
    interview_type = db.Column(db.String(50), default='ai')  # ai, phone, video, onsite
    meeting_link = db.Column(db.String(500), nullable=True)
    recording_path = db.Column(db.String(500), nullable=True)
    transcript_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('InterviewQuestion', backref='interview', lazy=True)
    feedback = db.relationship('InterviewFeedback', backref='interview', uselist=False, lazy=True)

class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='behavioral')  # behavioral, technical, situational, etc.
    order = db.Column(db.Integer, nullable=False)
    time_limit_seconds = db.Column(db.Integer, nullable=True)
    
    # Relationships
    answer = db.relationship('InterviewAnswer', backref='question', uselist=False, lazy=True)

class InterviewAnswer(db.Model):
    __tablename__ = 'interview_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_questions.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)
    recording_path = db.Column(db.String(500), nullable=True)
    analysis = db.Column(db.JSON, nullable=True)  # Store AI analysis of the answer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewFeedback(db.Model):
    __tablename__ = 'interview_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'), nullable=False)
    overall_score = db.Column(db.Float, nullable=True)
    technical_skills_score = db.Column(db.Float, nullable=True)
    communication_skills_score = db.Column(db.Float, nullable=True)
    cultural_fit_score = db.Column(db.Float, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    areas_for_improvement = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.String(50), nullable=True)  # strong_yes, yes, no_hire, strong_no_hire
    notes = db.Column(db.Text, nullable=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_ai_generated = db.Column(db.Boolean, default=False)

class Note(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='notes')

class AIConversation(db.Model):
    __tablename__ = 'ai_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('AIMessage', backref='conversation', lazy=True)

class AIMessage(db.Model):
    __tablename__ = 'ai_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    message_metadata = db.Column('metadata', db.JSON, nullable=True)  # Additional metadata like tokens, model used, etc.
