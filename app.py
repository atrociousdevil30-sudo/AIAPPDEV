import os
import json
import random
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
# Flask-Login has been removed in favor of session-based authentication
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import random
import sys
from datetime import datetime, timedelta
from functools import wraps
import uuid
import shutil
from pathlib import Path
from resume_parser import ResumeParser  # Import the ResumeParser class initialized to avoid circular imports
from models import db, User, Candidate, Resume, JobPosting, Application, Interview, Note, AIConversation, AIMessage
from resume_parser import ResumeData

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent))

def calculate_match_score(resume_data: ResumeData, job_title: str, job_description: str) -> Dict[str, Any]:
    """Calculate a match score between resume and job description"""
    if not job_description:
        return {
            'score': 0,
            'matched_skills': [],
            'missing_skills': [],
            'experience_match': 0
        }
    
    # Extract skills from job description (simple keyword matching)
    required_skills = {
        'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php',
        'swift', 'kotlin', 'go', 'rust', 'typescript', 'html', 'css',
        'django', 'flask', 'react', 'angular', 'vue', 'node', 'spring',
        'rails', 'laravel', '.net', 'tensorflow', 'pytorch', 'pandas',
        'numpy', 'docker', 'kubernetes', 'git', 'aws', 'azure', 'gcp',
        'mongodb', 'postgresql', 'mysql', 'sql', 'nosql', 'linux', 'ci/cd',
        'jenkins', 'github actions', 'rest', 'graphql', 'api'
    }
    
    # Find matching skills
    resume_skills = set(skill.lower() for skill in (resume_data.skills or []))
    job_skills = set()
    job_desc_lower = job_description.lower()
    
    for skill in required_skills:
        if skill in job_desc_lower:
            job_skills.add(skill)
    
    matched_skills = resume_skills.intersection(job_skills)
    missing_skills = job_skills - resume_skills
    
    # Calculate skill match percentage
    skill_match = 0
    if job_skills:
        skill_match = len(matched_skills) / len(job_skills) * 100
    
    # Check experience level (very basic)
    experience_match = 0
    if resume_data.experience:
        # Simple check for seniority in job title/description
        seniority_keywords = {
            'junior': 1,
            'mid-level': 2,
            'senior': 3,
            'lead': 4,
            'principal': 5,
            'architect': 5
        }
        
        # Check job title for seniority
        job_level = 2  # Default to mid-level
        for keyword, level in seniority_keywords.items():
            if keyword in job_title.lower() or keyword in job_description.lower():
                job_level = level
                break
        
        # Count years of experience (very rough estimate)
        exp_years = 0
        for exp in resume_data.experience:
            if 'duration' in exp:
                # Try to extract years from duration (simplified)
                years = re.findall(r'\d+', exp['duration'])
                if years:
                    exp_years += int(years[0])
        
        # Simple experience match (0-100)
        experience_match = min(exp_years / 10 * 100, 100)  # Cap at 10+ years
    
    # Calculate overall score (weighted average)
    overall_score = (skill_match * 0.7) + (experience_match * 0.3)
    
    return {
        'score': round(overall_score, 1),
        'matched_skills': list(matched_skills),
        'missing_skills': list(missing_skills),
        'experience_match': round(experience_match, 1)
    }

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'

# Custom Jinja2 filter for date formatting
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            # Try to parse the string as a datetime
            value = datetime.strptime(value, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            try:
                # Try a different format if the first one fails
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                return value  # Return as is if we can't parse it
    return value.strftime(format)

# Register custom Jinja2 filters
app.jinja_env.filters['datetimeformat'] = datetimeformat

# Context processor to make 'now' available in all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Session-based authentication is used instead of Flask-Login

# Basic Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'txt'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('CSRF_SECRET_KEY') or 'another-secret-key-please-change-in-production'

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import and register API routes
from api_routes import api as api_blueprint
app.register_blueprint(api_blueprint, url_prefix='/api')

# Create database tables
# Initialize mock database for development
class MockDB:
    def __init__(self, app):
        self.app = app
        with app.app_context():
            db.create_all()
            self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample data for development"""
        # Only add sample data if the database is empty
        if User.query.count() == 0:
            # Create sample users
            hr_user = User(
                email='hr@example.com',
                name='HR Manager',
                role='hr'
            )
            hr_user.set_password('password123')
            db.session.add(hr_user)
            db.session.commit()
            
            # Create sample job posting
            job = JobPosting(
                title='Senior Software Engineer',
                description='We are looking for an experienced software engineer...',
                requirements='5+ years of Python experience, 3+ years with Django/Flask',
                location='Remote',
                is_active=True
            )
            db.session.add(job)
            db.session.commit()
            
            # Create sample candidates and applications
            candidates_data = [
                {
                    'first_name': 'Michael', 'last_name': 'Chen',
                    'email': 'michael.chen@example.com', 'phone': '+1 (555) 123-4567',
                    'status': 'Offer Accepted', 'ats_score': 0.85,
                    'resume_path': '/uploads/resume_1.pdf'
                },
                {
                    'first_name': 'Priya', 'last_name': 'Patel',
                    'email': 'priya.patel@example.com', 'phone': '+1 (555) 987-6543',
                    'status': 'Background Check', 'ats_score': 0.78,
                    'resume_path': '/uploads/resume_2.pdf'
                },
                {
                    'first_name': 'Marcus', 'last_name': 'Rodriguez',
                    'email': 'marcus.rodriguez@example.com', 'phone': '+1 (555) 456-7890',
                    'status': 'Interview Scheduled', 'ats_score': 0.72,
                    'resume_path': '/uploads/resume_3.pdf'
                },
                {
                    'first_name': 'Aisha', 'last_name': 'Johnson',
                    'email': 'aisha.johnson@example.com', 'phone': '+1 (555) 234-5678',
                    'status': 'New Application', 'ats_score': 0.65,
                    'resume_path': '/uploads/resume_4.pdf'
                }
            ]
            
            for i, data in enumerate(candidates_data, 1):
                candidate = Candidate(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    email=data['email'],
                    phone=data['phone'],
                    status=data['status'],
                    ats_score=data['ats_score'],
                    recruiter_id=1  # HR user ID
                )
                db.session.add(candidate)
                db.session.flush()  # Get the candidate ID
                
                # Create a sample resume
                resume = Resume(
                    candidate_id=candidate.id,
                    file_path=data['resume_path'],
                    file_name=f'resume_{i}.pdf',
                    file_type='application/pdf',
                    file_size=1024 * 1024,  # 1MB
                    parsed_data={
                        'skills': ['Python', 'JavaScript', 'SQL', 'Docker', 'AWS'],
                        'experience': [
                            {
                                'title': 'Senior Software Engineer',
                                'company': 'Tech Corp',
                                'start_date': '2020-01-01',
                                'end_date': '2023-12-31',
                                'description': 'Developed and maintained web applications using Python and JavaScript.'
                            }
                        ],
                        'education': [
                            {
                                'degree': 'BSc Computer Science',
                                'institution': 'University of Technology',
                                'year': 2020
                            }
                        ]
                    }
                )
                db.session.add(resume)
                
                # Create a sample application
                application = Application(
                    candidate_id=candidate.id,
                    job_posting_id=1,  # Assuming there's a job posting with ID 1
                    resume_id=resume.id,
                    status=data['status'],
                    ats_score=data['ats_score']
                )
                db.session.add(application)
                
                # For some candidates, create interviews
                if i < 4:  # First 3 candidates have interviews
                    interview = Interview(
                        application=application,
                        interviewer=hr_user,
                        scheduled_time=datetime.utcnow() + timedelta(days=i),
                        duration_minutes=45,
                        status='scheduled' if i < 3 else 'completed',
                        interview_type='video'
                    )
                    db.session.add(interview)
            
            # Create a sample job posting
            job_posting = JobPosting(
                title='Senior Software Engineer',
                description='We are looking for a skilled Senior Software Engineer...',
                requirements='5+ years of experience with Python, JavaScript, and cloud technologies...',
                location='Remote',
                is_active=True
            )
            db.session.add(job_posting)
            
            db.session.commit()
            
            # Refresh the in-memory lists
            self._refresh_data()
    
    def _refresh_data(self):
        """Refresh in-memory data from the database"""
        self.candidates = [
            {
                'id': c.id,
                'name': f"{c.first_name} {c.last_name}",
                'email': c.email,
                'phone': c.phone,
                'status': c.status,
                'ats_score': c.ats_score,
                'resume': c.resumes[0].parsed_data if c.resumes else {}
            }
            for c in Candidate.query.all()
        ]
        
        self.applications = [
            {
                'id': a.id,
                'candidate_id': a.candidate_id,
                'status': a.status,
                'position': a.job_posting.title if a.job_posting else 'Software Engineer',
                'applied_date': a.applied_at.strftime('%Y-%m-%d')
            }
            for a in Application.query.all()
        ]
        
        self.interviews = [
            {
                'id': i.id,
                'candidate_id': i.application.candidate_id,
                'scheduled_time': i.scheduled_time.strftime('%Y-%m-%d %H:%M'),
                'status': i.status,
                'feedback': i.feedback[0].notes if i.feedback else 'No feedback yet'
            }
            for i in Interview.query.all()
        ]

# Initialize mock database for development
if os.environ.get('FLASK_ENV') == 'development':
    mock_db = MockDB(app)
    # Use the real db for operations, mock_db just for sample data

@app.route('/')
def index():
    return redirect(url_for('select_role'))

@app.route('/select-role')
def select_role():
    # Check if user is already logged in
    if 'user_role' in session:
        if session['user_role'] == 'hr':
            return redirect(url_for('hr_dashboard'))
        elif session['user_role'] == 'candidate':
            return redirect(url_for('candidate_dashboard'))
    
    # Clear any existing session data if no valid role
    session.clear()
    # Render the role selection page
    return render_template('role_selection.html')

@app.route('/login/hr')
def login_hr():
    # Set up a mock HR user
    session['user_role'] = 'hr'
    session['user_name'] = 'HR User'
    return redirect(url_for('hr_dashboard'))

@app.route('/login/candidate')
def login_candidate():
    # Set up a mock candidate user
    session['user_role'] = 'candidate'
    session['user_name'] = 'Candidate User'
    return redirect(url_for('candidate_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('select_role'))

@app.route('/dashboard')
def dashboard_route():
    return render_template('dashboard.html')

@app.route('/error')
def error_route():
    return render_template('error.html')

def get_exit_interview_data():
    """Generate comprehensive mock data for the exit interview page"""
    # Exit survey questions
    exit_survey = {
        'id': 'survey1',
        'title': 'Exit Interview Survey',
        'description': 'Please help us improve by sharing your experience and feedback.',
        'sections': [
            {
                'id': 'section1',
                'title': 'Your Experience',
                'questions': [
                    {
                        'id': 'q1',
                        'type': 'rating',
                        'question': 'How would you rate your overall experience working at our company?',
                        'required': True,
                        'options': ['1 - Very Poor', '2', '3 - Neutral', '4', '5 - Excellent']
                    },
                    {
                        'id': 'q2',
                        'type': 'text',
                        'question': 'What did you enjoy most about working here?',
                        'required': True,
                        'placeholder': 'Share your positive experiences...'
                    },
                    {
                        'id': 'q3',
                        'type': 'text',
                        'question': 'What could we improve to make this a better workplace?',
                        'required': True,
                        'placeholder': 'Your suggestions for improvement...'
                    }
                ]
            },
            {
                'id': 'section2',
                'title': 'Your Role',
                'questions': [
                    {
                        'id': 'q4',
                        'type': 'rating',
                        'question': 'How would you rate your job satisfaction?',
                        'required': True,
                        'options': ['1 - Very Dissatisfied', '2', '3 - Neutral', '4', '5 - Very Satisfied']
                    },
                    {
                        'id': 'q5',
                        'type': 'multiselect',
                        'question': 'What factors contributed to your decision to leave? (Select all that apply)',
                        'required': True,
                        'options': [
                            'Career advancement opportunities',
                            'Compensation and benefits',
                            'Work-life balance',
                            'Management style',
                            'Company culture',
                            'Job responsibilities',
                            'Work environment',
                            'Other (please specify)'
                        ]
                    },
                    {
                        'id': 'q6',
                        'type': 'text',
                        'question': 'What would have made you stay?',
                        'required': False,
                        'placeholder': 'Optional feedback...'
                    }
                ]
            },
            {
                'id': 'section3',
                'title': 'Knowledge Transfer',
                'questions': [
                    {
                        'id': 'q7',
                        'type': 'text',
                        'question': 'Please provide details about your current projects and their status',
                        'required': True,
                        'placeholder': 'Project details and current status...'
                    },
                    {
                        'id': 'q8',
                        'type': 'text',
                        'question': 'List any important documents or resources you\'ve created',
                        'required': False,
                        'placeholder': 'Document names and locations...'
                    },
                    {
                        'id': 'q9',
                        'type': 'text',
                        'question': 'Who are the key contacts for your projects?',
                        'required': False,
                        'placeholder': 'Names and contact information...'
                    }
                ]
            }
        ]
    }

    # Offboarding checklist
    offboarding_checklist = {
        'id': 'checklist1',
        'title': 'Offboarding Checklist',
        'items': [
            {
                'id': 'item1',
                'task': 'Return company equipment (laptop, badge, etc.)',
                'status': 'completed',
                'assigned_to': 'Employee',
                'due_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'category': 'Equipment',
                'notes': 'Laptop and badge need to be returned to IT department'
            },
            {
                'id': 'item2',
                'task': 'Complete exit interview',
                'status': 'in_progress',
                'assigned_to': 'HR Department',
                'due_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'category': 'HR',
                'notes': 'Scheduled with Jane Smith from HR'
            },
            {
                'id': 'item3',
                'task': 'Submit final expense reports',
                'status': 'pending',
                'assigned_to': 'Employee',
                'due_date': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'category': 'Finance',
                'notes': 'All receipts must be attached'
            },
            {
                'id': 'item4',
                'task': 'Knowledge transfer to team',
                'status': 'in_progress',
                'assigned_to': 'Team Lead',
                'due_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'category': 'Knowledge Transfer',
                'notes': 'Schedule with Alex and Sam from the team'
            },
            {
                'id': 'item5',
                'task': 'Revoke system access',
                'status': 'not_started',
                'assigned_to': 'IT Department',
                'due_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                'category': 'IT',
                'notes': 'Will be done automatically on last working day'
            },
            {
                'id': 'item6',
                'task': 'Exit survey completion',
                'status': 'in_progress',
                'assigned_to': 'Employee',
                'due_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                'category': 'HR',
                'notes': 'Complete the online exit survey form'
            },
            {
                'id': 'item7',
                'task': 'Beneficiary updates',
                'status': 'pending',
                'assigned_to': 'HR Department',
                'due_date': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                'category': 'Benefits',
                'notes': 'Update or confirm beneficiary information'
            }
        ]
    }

    # Knowledge transfer templates
    knowledge_transfer_templates = [
        {
            'id': 'kt1',
            'name': 'Project Handover Template',
            'description': 'Template for documenting project details, contacts, and next steps',
            'file_type': 'docx',
            'download_url': '/templates/project_handover.docx'
        },
        {
            'id': 'kt2',
            'name': 'Role Responsibilities',
            'description': 'Template for documenting key responsibilities and processes',
            'file_type': 'pdf',
            'download_url': '/templates/role_responsibilities.pdf'
        },
        {
            'id': 'kt3',
            'name': 'Frequently Used Resources',
            'description': 'Template for listing important documents and resources',
            'file_type': 'xlsx',
            'download_url': '/templates/resources_list.xlsx'
        }
    ]

    # Exit interview schedule
    exit_interview_schedule = {
        'id': 'schedule1',
        'scheduled_date': '2023-11-10',
        'scheduled_time': '2:00 PM',
        'location': 'Conference Room A',
        'interviewer': 'Jane Smith (HR Manager)',
        'status': 'scheduled',
        'duration': '60 minutes',
        'prep_notes': 'Please review the exit survey questions before the meeting.'
    }

    return {
        'exit_survey': exit_survey,
        'offboarding_checklist': offboarding_checklist,
        'knowledge_transfer_templates': knowledge_transfer_templates,
        'exit_interview': exit_interview_schedule,
        'employee_info': {
            'name': 'John Doe',
            'employee_id': 'EMP-10045',
            'department': 'Engineering',
            'position': 'Senior Developer',
            'start_date': '2021-05-15',
            'last_working_day': '2023-11-15',
            'manager': 'Sarah Johnson',
            'email': 'john.doe@company.com',
            'phone': '(555) 789-0123'
        }
    }

@app.route('/exit', methods=['GET', 'POST'])
def exit_route():
    if request.method == 'GET':
        # Get mock data for the exit interview page
        exit_data = get_exit_interview_data()
        # Add current date to the template context
        from datetime import datetime
        exit_data['current_date'] = datetime.now().strftime('%Y-%m-%d')
        return render_template('exit.html', **exit_data)
    
    elif request.method == 'POST':
        try:
            # Handle form submission for exit survey
            form_data = request.form
            # In a real application, you would save this data to a database
            print("Exit survey submitted:", form_data)
            return jsonify({'status': 'success', 'message': 'Thank you for your feedback!'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding_route():
    # Get onboarding data
    onboarding_data = get_mock_onboarding_data()
    
    # Sample job positions and descriptions
    job_positions = [
        {
            'id': 1,
            'title': 'Senior Software Engineer',
            'description': 'We are looking for an experienced Senior Software Engineer with expertise in Python, Django, and modern web technologies. The ideal candidate will have 5+ years of experience in building scalable web applications.',
            'required_skills': ['Python', 'Django', 'REST APIs', 'PostgreSQL', 'AWS', 'Docker', 'CI/CD'],
            'experience_required': '5+ years',
            'location': 'Remote',
            'type': 'Full-time'
        },
        {
            'id': 2,
            'title': 'Data Scientist',
            'description': 'Seeking a Data Scientist with strong background in machine learning and data analysis. The role involves developing predictive models and providing data-driven insights.',
            'required_skills': ['Python', 'Machine Learning', 'TensorFlow', 'Pandas', 'SQL', 'Data Visualization'],
            'experience_required': '3+ years',
            'location': 'New York, NY',
            'type': 'Full-time'
        },
        {
            'id': 3,
            'title': 'DevOps Engineer',
            'description': 'Looking for a DevOps Engineer to automate and optimize our infrastructure and deployment processes.',
            'required_skills': ['AWS', 'Docker', 'Kubernetes', 'CI/CD', 'Terraform', 'Linux'],
            'experience_required': '4+ years',
            'location': 'San Francisco, CA',
            'type': 'Full-time'
        }
    ]
    
    # Initialize candidates list from session or use default empty list
    candidates = session.get('candidates', [])
    
    # Handle form submission
    if request.method == 'POST':
        if 'resume' in request.files and 'job_position' in request.form:
            try:
                # Get selected job position
                selected_job_id = int(request.form.get('job_position'))
                selected_job = next((job for job in job_positions if job['id'] == selected_job_id), None)
                
                if not selected_job:
                    flash('Invalid job position selected', 'error')
                    return redirect(url_for('onboarding_route'))
                
                # Handle file upload
                resume_file = request.files['resume']
                if resume_file.filename != '':
                    # Save the file temporarily
                    uploads_dir = os.path.join('uploads')
                    os.makedirs(uploads_dir, exist_ok=True)
                    
                    # Generate a unique filename
                    filename = secure_filename(resume_file.filename)
                    filepath = os.path.join(uploads_dir, filename)
                    resume_file.save(filepath)
                    
                    # Parse the resume
                    parser = ResumeParser()
                    resume_data = parser.parse_resume(filepath)
                    
                    # Calculate match score based on job requirements
                    required_skills = set(skill.lower() for skill in selected_job['required_skills'])
                    candidate_skills = set(skill.lower() for skill in (resume_data.skills or []))
                    matched_skills = required_skills.intersection(candidate_skills)
                    match_score = int((len(matched_skills) / len(required_skills)) * 100) if required_skills else 0
                    
                    # Get experience in years
                    experience_years = 0
                    if resume_data.experience:
                        for exp in resume_data.experience:
                            if 'start_date' in exp and exp['start_date']:
                                try:
                                    start_year = int(exp['start_date'].split('-')[0])
                                    end_year = datetime.now().year
                                    if 'end_date' in exp and exp['end_date'] and exp['end_date'].lower() != 'present':
                                        end_year = int(exp['end_date'].split('-')[0])
                                    experience_years += (end_year - start_year)
                                except (ValueError, IndexError):
                                    pass
                    
                    # Create a new candidate from the parsed resume
                    new_candidate = {
                        'id': len(candidates) + 1,
                        'name': f"{resume_data.first_name} {resume_data.last_name}".strip() or 'New Candidate',
                        'email': resume_data.email or f"candidate{len(candidates) + 1}@example.com",
                        'position': selected_job['title'],
                        'status': 'New',
                        'applied_date': datetime.now().strftime('%Y-%m-%d'),
                        'start_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                        'resume_uploaded': True,
                        'resume_file': filename,
                        'job_position': selected_job,
                        'resume_analysis': {
                            'match_score': match_score,
                            'matched_skills': list(matched_skills),
                            'missing_skills': list(required_skills - candidate_skills),
                            'skills': resume_data.skills or [],
                            'experience': f"{experience_years} years" if experience_years > 0 else 'Not specified',
                            'education': resume_data.education[0]['degree'] if resume_data.education else 'Not specified',
                            'status': 'Pending Review',
                            'summary': resume_data.summary or 'No summary available',
                            'experience_details': [
                                {
                                    'title': exp.get('title', 'Not specified'),
                                    'company': exp.get('company', 'Not specified'),
                                    'duration': f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}",
                                    'description': exp.get('description', 'No description')
                                }
                                for exp in (resume_data.experience or [])[:3]  # Show up to 3 most recent experiences
                            ]
                        },
                        'avatar': f"https://ui-avatars.com/api/?name={resume_data.first_name}+{resume_data.last_name if resume_data.last_name else 'Candidate'}&background=random"
                    }
                    
                    # Add the new candidate to the list
                    candidates.append(new_candidate)
                    session['candidates'] = candidates
                    
                    # Clean up the temporary file
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    
                    flash(f'Resume uploaded and analyzed! Match score: {match_score}% for {selected_job["title"]}', 'success')
                    return redirect(url_for('onboarding_route'))
                else:
                    flash('No file selected', 'error')
                    return redirect(url_for('onboarding_route'))
                    
            except Exception as e:
                import traceback
                print(f"Error processing resume: {str(e)}\n{traceback.format_exc()}")
                flash(f'Error processing resume: {str(e)}', 'error')
                return redirect(url_for('onboarding_route'))
        else:
            flash('Please select both a resume and a job position', 'error')
            return redirect(url_for('onboarding_route'))
    
    # Generate mock candidates if none exist
    if not candidates:
        candidates = [
            {
                'id': 1,
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'position': 'Senior Software Engineer',
                'avatar': 'https://randomuser.me/api/portraits/men/32.jpg',
                'applied_date': '2023-10-28',
                'status': 'New',
                'resume_analysis': {
                    'match_score': 87,
                    'skills': ['Python', 'JavaScript', 'Docker', 'AWS', 'React', 'Node.js'],
                    'experience': '8 years',
                    'education': 'MSc Computer Science'
                }
            },
            {
                'id': 2,
                'name': 'Sarah Johnson',
                'email': 'sarah.j@example.com',
                'position': 'UX/UI Designer',
                'avatar': 'https://randomuser.me/api/portraits/women/44.jpg',
                'applied_date': '2023-10-27',
                'status': 'In Review',
                'resume_analysis': {
                    'match_score': 92,
                    'skills': ['Figma', 'Sketch', 'Adobe XD', 'User Research', 'Prototyping'],
                    'experience': '5 years',
                    'education': 'BFA in Design'
                }
            },
            {
                'id': 3,
                'name': 'Michael Chen',
                'email': 'michael.c@example.com',
                'position': 'Data Scientist',
                'avatar': 'https://randomuser.me/api/portraits/men/67.jpg',
                'applied_date': '2023-10-26',
                'status': 'Screening',
                'resume_analysis': {
                    'match_score': 78,
                    'skills': ['Python', 'Machine Learning', 'TensorFlow', 'Data Analysis', 'SQL'],
                    'experience': '6 years',
                    'education': 'PhD in Data Science'
                }
            }
        ]

    # Mock new hire data
    new_hire = {
        'name': 'New Employee',  # Default name, you can customize this
        'position': 'New Position',
        'start_date': datetime.now().strftime('%B %d, %Y'),
        'department': 'Engineering',
        'manager': 'John Doe',
        'email': 'new.employee@example.com'
    }
    
    # Mock onboarding checklist
    onboarding_checklist = {
        'Pre-arrival': [
            'Complete new hire paperwork',
            'Submit tax forms',
            'Complete I-9 verification',
            'Enroll in benefits',
            'Set up direct deposit'
        ],
        'First Day': [
            'Office tour',
            'IT setup and access',
            'Meet the team',
            'Review company policies',
            'Set up email and accounts'
        ],
        'First Week': [
            'Complete training modules',
            'Meet with manager',
            'Project onboarding',
            'Team introduction',
            'Goal setting session'
        ],
        'First 30 Days': [
            'Complete all required training',
            'Meet with HR for check-in',
            'Deliver first project milestone',
            'Attend team building event',
            '30-day performance review'
        ]
    }
    
    # For GET requests or after successful POST
    return render_template('onboarding.html', 
                         onboarding_data=onboarding_data,
                         candidates=candidates,
                         job_positions=job_positions,
                         sample_candidates=candidates[:2],  # First 2 candidates as sample
                         new_hire=new_hire,
                         onboarding_checklist=onboarding_checklist)

def get_mock_interview_data(candidate_id=None):
    """Generate mock interview data for the interview evaluation page"""
    # List of possible candidates
    candidates = [
        {
            'id': 1,
            'name': 'Louis Litt',
            'email': 'louis.litt@example.com',
            'position': 'Senior Software Engineer',
            'experience': '7 years',
            'status': 'Interview Scheduled',
            'avatar': 'https://randomuser.me/api/portraits/men/32.jpg',
            'applied_date': '2023-10-15',
            'resume_match': '92%',
            'skills': ['Python', 'Django', 'React', 'AWS', 'Docker', 'PostgreSQL'],
            'education': 'MSc in Computer Science, Stanford University',
            'current_company': 'Tech Solutions Inc.',
            'notice_period': '30 days',
            'expected_salary': '$120,000',
            'location': 'San Francisco, CA',
            'phone': '(555) 123-4567',
            'linkedin': 'linkedin.com/in/johndoe',
            'github': 'github.com/johndoe',
            'portfolio': 'johndoe.dev',
            'interview_date': '2023-11-15 14:30',
            'interview_type': 'Technical',
            'interviewer': 'Stanley Lipschitz',
            'interview_notes': 'Strong technical background with extensive experience in full-stack development.',
            'evaluation': {
                'technical_skills': 4,
                'problem_solving': 5,
                'communication': 4,
                'cultural_fit': 4,
                'overall_rating': 4.25,
                'strengths': ['Strong problem-solving skills', 'Deep technical knowledge', 'Good communication'],
                'areas_for_improvement': ['Could demonstrate more leadership experience', 'Limited experience with microservices'],
                'recommendation': 'Strong Hire',
                'notes': 'Candidate performed exceptionally well in the technical assessment.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'Can you tell me about a challenging project you worked on?'},
                {'speaker': 'Candidate', 'text': 'At my current role, I led the migration of our monolith to microservices...'},
                {'speaker': 'Interviewer', 'text': 'How did you handle the database schema changes?'},
                {'speaker': 'Candidate', 'text': 'We used a blue-green deployment strategy with feature flags...'}
            ]
        },
        {
            'id': 2,
            'name': 'Rachel Zane',
            'email': 'rachel.zane@example.com',
            'position': 'Frontend Developer',
            'experience': '5 years',
            'status': 'Technical Interview',
            'avatar': 'https://randomuser.me/api/portraits/women/44.jpg',
            'applied_date': '2023-10-20',
            'resume_match': '88%',
            'skills': ['JavaScript', 'React', 'TypeScript', 'Redux', 'CSS', 'Jest'],
            'education': 'BSc in Computer Science, MIT',
            'current_company': 'WebCraft LLC',
            'notice_period': '15 days',
            'expected_salary': '$110,000',
            'location': 'New York, NY',
            'phone': '(555) 987-6543',
            'linkedin': 'linkedin.com/in/janesmith',
            'github': 'github.com/janesmith',
            'portfolio': 'janesmith.dev',
            'interview_date': '2023-11-16 11:00',
            'interview_type': 'Technical',
            'interviewer': 'Michael Ross',
            'interview_notes': 'Excellent frontend skills with a good eye for design. Strong in React and modern JavaScript.',
            'evaluation': {
                'technical_skills': 5,
                'problem_solving': 4,
                'communication': 5,
                'cultural_fit': 5,
                'overall_rating': 4.75,
                'strengths': ['Exceptional UI/UX skills', 'Strong React knowledge', 'Great team player'],
                'areas_for_improvement': ['Could improve test coverage', 'Limited backend experience'],
                'recommendation': 'Hire',
                'notes': 'Top candidate for the frontend role. Would be a great cultural fit.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How do you approach state management in React applications?'},
                {'speaker': 'Candidate', 'text': 'I prefer using Redux for global state and React Context for theme and auth...'},
                {'speaker': 'Interviewer', 'text': 'Can you explain how you optimize performance in React?'},
                {'speaker': 'Candidate', 'text': 'I use React.memo, useCallback, and useMemo to prevent unnecessary re-renders...'}
            ]
        },
        {
            'id': 3,
            'name': 'Alex James Wheeler',
            'email': 'alex.j@example.com',
            'position': 'DevOps Engineer',
            'experience': '6 years',
            'status': 'Pending Review',
            'avatar': 'https://randomuser.me/api/portraits/men/68.jpg',
            'applied_date': '2023-10-25',
            'resume_match': '95%',
            'skills': ['AWS', 'Kubernetes', 'Docker', 'Terraform', 'CI/CD', 'Python'],
            'education': 'BSc in Computer Engineering, UC Berkeley',
            'current_company': 'CloudScale Inc.',
            'notice_period': '60 days',
            'expected_salary': '$130,000',
            'location': 'Seattle, WA',
            'phone': '(555) 456-7890',
            'linkedin': 'linkedin.com/in/alexjohnson',
            'github': 'github.com/alexjohnson',
            'portfolio': 'alexjohnson.tech',
            'interview_date': '2023-11-17 13:30',
            'interview_type': 'Technical',
            'interviewer': 'David Kim',
            'interview_notes': 'Strong experience with cloud infrastructure and automation. Needs to demonstrate more leadership experience.',
            'evaluation': {
                'technical_skills': 5,
                'problem_solving': 4,
                'communication': 4,
                'cultural_fit': 3,
                'overall_rating': 4.0,
                'strengths': ['Extensive cloud experience', 'Strong automation skills', 'Good problem-solving'],
                'areas_for_improvement': ['Could improve documentation skills', 'Needs more leadership experience'],
                'recommendation': 'Maybe',
                'notes': 'Technically strong but might need more experience leading teams.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How would you design a highly available system on AWS?'},
                {'speaker': 'Candidate', 'text': 'I would use multiple AZs, Auto Scaling Groups, and a combination of ALB and Route 53...'},
                {'speaker': 'Interviewer', 'text': 'How do you handle secrets management?'},
                {'speaker': 'Candidate', 'text': 'I prefer using AWS Secrets Manager with IAM roles and least privilege access...'}
            ]
        },
        {
            'id': 4,
            'name': 'Chloe Decker',
            'email': 'chloe.decker@example.com',
            'position': 'Data Scientist',
            'experience': '4 years',
            'status': 'Technical Interview',
            'avatar': 'https://randomuser.me/api/portraits/women/32.jpg',
            'applied_date': '2023-10-22',
            'resume_match': '89%',
            'skills': ['Python', 'Machine Learning', 'TensorFlow', 'PyTorch', 'SQL', 'Data Visualization'],
            'education': 'MSc in Data Science, University of Washington',
            'current_company': 'DataInsights Inc.',
            'notice_period': '30 days',
            'expected_salary': '$115,000',
            'location': 'Boston, MA',
            'phone': '(555) 234-5678',
            'linkedin': 'linkedin.com/in/priyapatel',
            'github': 'github.com/priyapatel',
            'portfolio': 'priyapatel-ds.com',
            'interview_date': '2023-11-18 10:00',
            'interview_type': 'Technical',
            'interviewer': ' Samantha Williams',
            'interview_notes': 'Strong background in ML with experience in NLP and computer vision. Good communication skills.',
            'evaluation': {
                'technical_skills': 5,
                'problem_solving': 5,
                'communication': 4,
                'cultural_fit': 4,
                'overall_rating': 4.5,
                'strengths': ['Strong ML fundamentals', 'Good presentation skills', 'Experience with big data'],
                'areas_for_improvement': ['Could improve production deployment experience', 'Limited experience with cloud platforms'],
                'recommendation': 'Strong Hire',
                'notes': 'Excellent candidate for our ML team. Strong technical skills and good cultural fit.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'Can you explain how you would approach a classification problem with imbalanced classes?'},
                {'speaker': 'Candidate', 'text': 'For imbalanced datasets, I would first analyze the class distribution and consider techniques like SMOTE...'},
                {'speaker': 'Interviewer', 'text': 'How do you evaluate model performance beyond accuracy?'},
                {'speaker': 'Candidate', 'text': 'I look at precision, recall, F1 score, and ROC-AUC. For imbalanced data, precision-recall curves...'}
            ]
        },
        {
            'id': 5,
            'name': 'James Wilson',
            'email': 'james.wilson@example.com',
            'position': 'Backend Engineer',
            'experience': '5 years',
            'status': 'Technical Interview',
            'avatar': 'https://randomuser.me/api/portraits/men/45.jpg',
            'applied_date': '2023-10-23',
            'resume_match': '91%',
            'skills': ['Java', 'Spring Boot', 'Microservices', 'Kafka', 'MongoDB', 'Docker'],
            'education': 'BSc in Computer Science, University of Texas at Austin',
            'current_company': 'TechNova Solutions',
            'notice_period': '45 days',
            'expected_salary': '$125,000',
            'location': 'Austin, TX',
            'phone': '(555) 345-6789',
            'linkedin': 'linkedin.com/in/jameswilson',
            'github': 'github.com/jameswilson',
            'portfolio': 'jameswilson.dev',
            'interview_date': '2023-11-19 14:30',
            'interview_type': 'Technical',
            'interviewer': 'Walter Rodriguez',
            'interview_notes': 'Strong Java backend experience with microservices. Needs to demonstrate more system design knowledge.',
            'evaluation': {
                'technical_skills': 4,
                'problem_solving': 4,
                'communication': 3,
                'cultural_fit': 4,
                'overall_rating': 3.75,
                'strengths': ['Strong Java skills', 'Experience with distributed systems', 'Good debugging skills'],
                'areas_for_improvement': ['Could improve communication', 'Needs more experience with cloud platforms'],
                'recommendation': 'Maybe',
                'notes': 'Technically strong but would need to improve communication skills.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How would you design a URL shortening service like bit.ly?'},
                {'speaker': 'Candidate', 'text': 'I would start with the API design, then discuss the data model using a key-value store...'},
                {'speaker': 'Interviewer', 'text': 'How would you handle high traffic to popular URLs?'},
                {'speaker': 'Candidate', 'text': 'I would implement caching using Redis and use consistent hashing...'}
            ]
        },
        {
            'id': 6,
            'name': 'Aisha Mohammed',
            'email': 'aisha.m@example.com',
            'position': 'UX/UI Designer',
            'experience': '3 years',
            'status': 'Design Review',
            'avatar': 'https://randomuser.me/api/portraits/women/67.jpg',
            'applied_date': '2023-10-24',
            'resume_match': '87%',
            'skills': ['Figma', 'Sketch', 'User Research', 'Prototyping', 'UI/UX', 'Design Systems'],
            'education': 'BFA in Design, Rhode Island School of Design',
            'current_company': 'DesignCraft Studio',
            'notice_period': '30 days',
            'expected_salary': '$95,000',
            'location': 'Chicago, IL',
            'phone': '(555) 456-7890',
            'linkedin': 'linkedin.com/in/aishamohammed',
            'dribbble': 'dribbble.com/aisham',
            'portfolio': 'aishamohammed.design',
            'interview_date': '2023-11-20 11:00',
            'interview_type': 'Portfolio Review',
            'interviewer': 'Emily Stone',
            'interview_notes': 'Strong visual design skills with good understanding of user-centered design principles.',
            'evaluation': {
                'technical_skills': 4,
                'problem_solving': 4,
                'communication': 5,
                'cultural_fit': 5,
                'overall_rating': 4.5,
                'strengths': ['Strong visual design', 'Good presentation skills', 'User research experience'],
                'areas_for_improvement': ['Limited experience with design systems', 'Could improve prototyping skills'],
                'recommendation': 'Hire',
                'notes': 'Great cultural fit with strong design skills. Would be a valuable addition to the design team.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'Can you walk us through your design process?'},
                {'speaker': 'Candidate', 'text': 'I start with user research to understand pain points, then create user personas...'},
                {'speaker': 'Interviewer', 'text': 'How do you handle feedback on your designs?'},
                {'speaker': 'Candidate', 'text': 'I welcome feedback and use it as an opportunity to improve...'}
            ]
        },
        {
            'id': 7,
            'name': 'Carlos Mendez',
            'email': 'carlos.m@example.com',
            'position': 'Mobile Developer',
            'experience': '4 years',
            'status': 'Code Review',
            'avatar': 'https://randomuser.me/api/portraits/men/52.jpg',
            'applied_date': '2023-10-25',
            'resume_match': '90%',
            'skills': ['Swift', 'iOS', 'SwiftUI', 'Objective-C', 'XCTest', 'Firebase'],
            'education': 'BSc in Computer Science, University of Florida',
            'current_company': 'AppVenture Inc.',
            'notice_period': '30 days',
            'expected_salary': '$110,000',
            'location': 'Miami, FL',
            'phone': '(555) 567-8901',
            'linkedin': 'linkedin.com/in/carlosmendez',
            'github': 'github.com/carlosmendez',
            'portfolio': 'carlosmendez.dev',
            'interview_date': '2023-11-21 13:30',
            'interview_type': 'Technical',
            'interviewer': 'David Kim',
            'interview_notes': 'Strong iOS development skills with experience in both Swift and Objective-C. Good problem-solving abilities.',
            'evaluation': {
                'technical_skills': 5,
                'problem_solving': 4,
                'communication': 4,
                'cultural_fit': 4,
                'overall_rating': 4.25,
                'strengths': ['Strong Swift knowledge', 'Good debugging skills', 'Experience with app store submission'],
                'areas_for_improvement': ['Could improve testing coverage', 'Limited experience with cross-platform development'],
                'recommendation': 'Strong Hire',
                'notes': 'Excellent iOS developer who would be a great addition to our mobile team.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How do you handle memory management in iOS?'},
                {'speaker': 'Candidate', 'text': 'I use ARC and am careful with strong reference cycles...'},
                {'speaker': 'Interviewer', 'text': 'How would you implement offline support in a mobile app?'},
                {'speaker': 'Candidate', 'text': 'I would use Core Data with a sync manager to handle offline operations...'}
            ]
        },
        {
            'id': 8,
            'name': 'Olivia Paulsen',
            'email': 'olivia.paulsen@example.com',
            'position': 'Product Manager',
            'experience': '6 years',
            'status': 'Final Round',
            'avatar': 'https://randomuser.me/api/portraits/women/28.jpg',
            'applied_date': '2023-10-20',
            'resume_match': '93%',
            'skills': ['Product Strategy', 'Agile', 'JIRA', 'SQL', 'A/B Testing', 'Market Research'],
            'education': 'MBA, Harvard Business School',
            'current_company': 'ProductLabs',
            'notice_period': '60 days',
            'expected_salary': '$140,000',
            'location': 'San Francisco, CA',
            'phone': '(555) 678-9012',
            'linkedin': 'linkedin.com/in/oliviapaulsen',
            'portfolio': 'oliviapaulsen.com',
            'interview_date': '2023-11-22 15:00',
            'interview_type': 'Executive',
            'interviewer': 'CEO Sarah Johnson',
            'interview_notes': 'Experienced PM with strong strategic thinking and leadership skills. Has successfully launched multiple products.',
            'evaluation': {
                'technical_skills': 4,
                'problem_solving': 5,
                'communication': 5,
                'cultural_fit': 5,
                'overall_rating': 4.75,
                'strengths': ['Strong leadership', 'Excellent communication', 'Data-driven decision making'],
                'areas_for_improvement': ['Could improve technical depth', 'Limited experience in our industry'],
                'recommendation': 'Strong Hire',
                'notes': 'Exceptional candidate with proven track record. Would be a great addition to the leadership team.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How do you prioritize features for a new product?'},
                {'speaker': 'Candidate', 'text': 'I use a combination of business impact, user value, and technical feasibility...'},
                {'speaker': 'Interviewer', 'text': 'How do you handle conflicts between stakeholders?'},
                {'speaker': 'Candidate', 'text': 'I focus on finding common ground and making data-driven decisions...'}
            ]
        },
        {
            'id': 9,
            'name': 'Marcus Johnson',
            'email': 'marcus.j@example.com',
            'position': 'Security Engineer',
            'experience': '7 years',
            'status': 'Background Check',
            'avatar': 'https://randomuser.me/api/portraits/men/75.jpg',
            'applied_date': '2023-10-18',
            'resume_match': '94%',
            'skills': ['Cybersecurity', 'Penetration Testing', 'SIEM', 'Firewalls', 'Incident Response', 'AWS Security'],
            'education': 'MSc in Cybersecurity, Georgia Tech',
            'current_company': 'SecureNet Inc.',
            'notice_period': '30 days',
            'expected_salary': '$150,000',
            'location': 'Washington, DC',
            'phone': '(555) 789-0123',
            'linkedin': 'linkedin.com/in/marcusjohnson',
            'github': 'github.com/marcusjohnson',
            'portfolio': 'marcusjohnson.security',
            'interview_date': '2023-11-23 10:00',
            'interview_type': 'Technical',
            'interviewer': 'CISO Robert Taylor',
            'interview_notes': 'Extensive experience in cybersecurity with a focus on cloud security and incident response. Holds multiple security certifications.',
            'evaluation': {
                'technical_skills': 5,
                'problem_solving': 5,
                'communication': 4,
                'cultural_fit': 4,
                'overall_rating': 4.5,
                'strengths': ['Deep security expertise', 'Strong problem-solving skills', 'Experience with compliance'],
                'areas_for_improvement': ['Could improve documentation', 'Needs to work on simplifying technical concepts for non-technical stakeholders'],
                'recommendation': 'Hire',
                'notes': 'Top candidate for the security engineering role. Strong technical skills and good cultural fit.'
            },
            'interview_transcript': [
                {'speaker': 'Interviewer', 'text': 'How would you secure a new cloud infrastructure?'},
                {'speaker': 'Candidate', 'text': 'I would start with a secure baseline configuration, implement network segmentation...'},
                {'speaker': 'Interviewer', 'text': 'How do you stay updated with the latest security threats?'},
                {'speaker': 'Candidate', 'text': 'I follow security blogs, attend conferences, and participate in CTF competitions...'}
            ]
        }
    ]
    
    # If a specific candidate ID is provided, return that candidate's data
    if candidate_id:
        for candidate in candidates:
            if candidate['id'] == int(candidate_id):
                return candidate
        return None
    
    # Otherwise return all candidates
    return candidates

@app.route('/interview')
def interview_route():
    # Get candidate ID from query parameters, default to first candidate
    candidate_id = int(request.args.get('candidate_id', 1))
    
    # Get the specific candidate's data
    candidate = get_mock_interview_data(candidate_id)
    
    # If candidate not found, redirect to first candidate
    if not candidate:
        return redirect(url_for('interview_route', candidate_id=1))
    
    # Import AIAnalyzer (moved here to avoid circular imports)
    from candidate_analyzer import AIAnalyzer
    
    # Generate AI analysis for the candidate
    analyzer = AIAnalyzer()
    ai_analysis = analyzer.analyze_candidate(candidate)
    
    # Add AI analysis to candidate data
    candidate['ai_analysis'] = ai_analysis
    
    all_candidates = get_mock_interview_data()
    
    # Get the current candidate's index for navigation
    current_index = next((i for i, c in enumerate(all_candidates) if c['id'] == candidate['id']), 0)
    prev_candidate = all_candidates[current_index - 1] if current_index > 0 else None
    next_candidate = all_candidates[current_index + 1] if current_index < len(all_candidates) - 1 else None
    
    return render_template('interview.html', 
                         candidate=candidate, 
                         candidates=all_candidates,
                         prev_candidate=prev_candidate,
                         next_candidate=next_candidate,
                         ai_analysis=ai_analysis,
                         title=f"Interview Evaluation - {candidate['name']}")

# Initialize the NLP chatbot
try:
    from .nlp.train import NLPChatbot
    # Global chatbot instance
    chatbot = NLPChatbot()
except ImportError:
    print("Warning: Could not import NLPChatbot. Some features may not be available.")
    chatbot = None

@app.route('/ai-training')
@app.route('/ai_training')
def ai_training():
    # Sample data to pass to the template
    sample_data = {
        'training_history': [
            {'date': 'Oct 27, 2025', 'type': 'Recruitment Process', 'status': 'Completed', 'accuracy': '92%'},
            {'date': 'Oct 26, 2025', 'type': 'Exit Interview', 'status': 'Completed', 'accuracy': '88%'},
            {'date': 'Oct 25, 2025', 'type': 'Initial Setup', 'status': 'Completed', 'accuracy': '95%'}
        ]
    }
    return render_template('ai_training.html', **sample_data)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages from the frontend"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Empty message'}), 400
            
        # Get response from the chatbot
        response = chatbot.get_response(message)
        
        return jsonify({
            'response': response,
            'timestamp': datetime.utcnow().strftime('%H:%M')
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your message'}), 500

@app.route('/api/train', methods=['POST'])
def train_chatbot():
    """Endpoint to train the chatbot with new data"""
    try:
        data = request.get_json()
        new_data = data.get('training_data', [])
        
        if not new_data:
            return jsonify({'error': 'No training data provided'}), 400
            
        # Train the chatbot with new data
        chatbot.train(new_data)
        
        return jsonify({'message': 'Chatbot trained successfully'})
        
    except Exception as e:
        print(f"Error in train endpoint: {str(e)}")
        return jsonify({'error': 'An error occurred while training the chatbot'}), 500

def get_mock_onboarding_data():
    """Generate comprehensive mock data for the onboarding page"""
    # Mock data for onboarding progress
    onboarding_progress = {
        'overall_completion': 35,
        'stages': [
            {
                'id': 'pre_arrival',
                'name': 'Pre-Arrival',
                'progress': 40,
                'completed_tasks': 2,
                'total_tasks': 5,
                'tasks': [
                    {'id': 'task1', 'name': 'Send welcome email', 'completed': True, 'completed_date': '2023-10-27'},
                    {'id': 'task2', 'name': 'Collect personal information', 'completed': True, 'completed_date': '2023-10-28'},
                    {'id': 'task3', 'name': 'Setup company email', 'completed': False, 'due_date': '2023-10-30'},
                    {'id': 'task4', 'name': 'Order equipment', 'completed': False, 'due_date': '2023-10-31'},
                    {'id': 'task5', 'name': 'Schedule first day', 'completed': False, 'due_date': '2023-11-01'}
                ]
            },
            {
                'id': 'first_day',
                'name': 'First Day',
                'progress': 20,
                'completed_tasks': 1,
                'total_tasks': 8,
                'tasks': [
                    {'id': 'task6', 'name': 'Office tour', 'completed': True, 'completed_date': '2023-10-29'},
                    {'id': 'task7', 'name': 'Team introductions', 'completed': False, 'due_date': '2023-11-02'},
                    {'id': 'task8', 'name': 'IT setup', 'completed': False, 'due_date': '2023-11-02'},
                    {'id': 'task9', 'name': 'Company policies review', 'completed': False, 'due_date': '2023-11-03'},
                    {'id': 'task10', 'name': 'HR paperwork', 'completed': False, 'due_date': '2023-11-03'}
                ]
            },
            {
                'id': 'first_week',
                'name': 'First Week',
                'progress': 0,
                'completed_tasks': 0,
                'total_tasks': 6,
                'tasks': [
                    {'id': 'task11', 'name': 'Complete training modules', 'completed': False, 'due_date': '2023-11-06'},
                    {'id': 'task12', 'name': 'Meet with mentor', 'completed': False, 'due_date': '2023-11-07'},
                    {'id': 'task13', 'name': 'Project kickoff', 'completed': False, 'due_date': '2023-11-08'}
                ]
            },
            {
                'id': 'first_month',
                'name': 'First Month',
                'progress': 0,
                'completed_tasks': 0,
                'total_tasks': 4,
                'tasks': [
                    {'id': 'task14', 'name': '30-day check-in', 'completed': False, 'due_date': '2023-11-30'},
                    {'id': 'task15', 'name': 'Initial performance review', 'completed': False, 'due_date': '2023-12-01'}
                ]
            }
        ]
    }

    # Mock data for document collection
    documents = [
        {
            'id': 'doc1',
            'name': 'Employment Contract',
            'type': 'pdf',
            'status': 'received',
            'received_date': '2023-10-27',
            'required': True,
            'size': '1.2 MB',
            'uploaded_by': 'HR Department'
        },
        {
            'id': 'doc2',
            'name': 'Tax Forms (W-4)',
            'type': 'pdf',
            'status': 'pending',
            'due_date': '2023-11-03',
            'required': True,
            'size': '450 KB',
            'uploaded_by': None
        },
        {
            'id': 'doc3',
            'name': 'Direct Deposit Form',
            'type': 'docx',
            'status': 'pending',
            'due_date': '2023-11-03',
            'required': True,
            'size': '320 KB',
            'uploaded_by': None
        },
        {
            'id': 'doc4',
            'name': 'Employee Handbook Acknowledgment',
            'type': 'pdf',
            'status': 'not_started',
            'required': True,
            'size': '2.1 MB',
            'uploaded_by': None
        },
        {
            'id': 'doc5',
            'name': 'Emergency Contact Information',
            'type': 'form',
            'status': 'not_started',
            'required': True,
            'size': None,
            'uploaded_by': None
        }
    ]

    # Mock data for team members
    team_members = [
        {
            'id': 'tm1',
            'name': 'Sarah Johnson',
            'title': 'Team Lead',
            'department': 'Engineering',
            'email': 'sarah.johnson@company.com',
            'phone': '(555) 123-4567',
            'photo': 'https://randomuser.me/api/portraits/women/44.jpg',
            'is_mentor': False,
            'bio': '10+ years of experience in software development. Enjoys mentoring new team members and hiking on weekends.'
        },
        {
            'id': 'tm2',
            'name': 'Michael Chen',
            'title': 'Senior Developer',
            'department': 'Engineering',
            'email': 'michael.chen@company.com',
            'phone': '(555) 234-5678',
            'photo': 'https://randomuser.me/api/portraits/men/32.jpg',
            'is_mentor': True,
            'bio': 'Your onboarding mentor. 8 years of experience in full-stack development. Loves open source contributions and coffee.'
        },
        {
            'id': 'tm3',
            'name': 'Priya Patel',
            'title': 'Product Manager',
            'department': 'Product',
            'email': 'priya.patel@company.com',
            'phone': '(555) 345-6789',
            'photo': 'https://randomuser.me/api/portraits/women/68.jpg',
            'is_mentor': False,
            'bio': 'Product management expert with a background in UX design. Enjoys solving complex problems with simple solutions.'
        }
    ]

    # Mock data for training assignments
    training_assignments = [
        {
            'id': 'train1',
            'title': 'Company Policies',
            'type': 'e-learning',
            'status': 'completed',
            'progress': 100,
            'due_date': '2023-10-25',
            'completed_date': '2023-10-24',
            'duration': '30 min',
            'description': 'Overview of company policies, code of conduct, and compliance requirements.'
        },
        {
            'id': 'train2',
            'title': 'Security Awareness',
            'type': 'e-learning',
            'status': 'in_progress',
            'progress': 30,
            'due_date': '2023-11-05',
            'duration': '45 min',
            'description': 'Learn about information security best practices and company policies.'
        },
        {
            'id': 'train3',
            'title': 'Diversity & Inclusion',
            'type': 'in-person',
            'status': 'not_started',
            'progress': 0,
            'due_date': '2023-11-10',
            'duration': '2 hours',
            'description': 'Interactive session on building an inclusive workplace.'
        },
        {
            'id': 'train4',
            'title': 'Technical Onboarding',
            'type': 'workshop',
            'status': 'not_started',
            'progress': 0,
            'due_date': '2023-11-15',
            'duration': '4 hours',
            'description': 'Hands-on workshop for technical team members.'
        }
    ]

    # Mock data for upcoming events
    upcoming_events = [
        {
            'id': 'event1',
            'title': 'Welcome Lunch',
            'type': 'social',
            'date': '2023-11-02',
            'time': '12:00 PM',
            'location': 'Main Cafeteria',
            'description': 'Lunch with your team and manager',
            'organizer': 'HR Department'
        },
        {
            'id': 'event2',
            'title': 'IT Setup Session',
            'type': 'training',
            'date': '2023-11-02',
            'time': '2:00 PM',
            'location': 'IT Department',
            'description': 'Get your laptop and access set up',
            'organizer': 'IT Support'
        },
        {
            'id': 'event3',
            'title': 'Team Meeting',
            'type': 'meeting',
            'date': '2023-11-03',
            'time': '10:00 AM',
            'location': 'Conference Room B',
            'description': 'Weekly team sync',
            'organizer': 'Sarah Johnson'
        }
    ]

    return {
        'onboarding_progress': onboarding_progress,
        'documents': documents,
        'team_members': team_members,
        'training_assignments': training_assignments,
        'upcoming_events': upcoming_events
    }

def onboarding_route():
    from resume_parser import ResumeParser
    
    # Initialize resume parser
    resume_parser = ResumeParser()
    
    # Sample resume data (in a real app, this would come from file uploads)
    sample_resumes = [
        {
            'name': 'Sarah Johnson',
            'email': 'sarah.johnson@example.com',
            'position': 'Senior Software Engineer',
            'resume_text': '''Sarah Johnson
Senior Software Engineer
Email: sarah.johnson@example.com | Phone: (555) 123-4567 | Location: San Francisco, CA

SUMMARY
Experienced Senior Software Engineer with 5+ years of experience in full-stack development. 
Expertise in Python, Django, React, and cloud technologies. Led multiple projects to successful deployment.

TECHNICAL SKILLS
• Programming: Python, JavaScript, TypeScript
• Frameworks: Django, React, Node.js
• Databases: PostgreSQL, MongoDB
• DevOps: Docker, Kubernetes, AWS, CI/CD
• Tools: Git, JIRA, Agile/Scrum

EXPERIENCE
Senior Software Engineer
Tech Solutions Inc. | 2020 - Present
• Led a team of 5 developers in building scalable web applications
• Architected and implemented microservices using Django and React
• Improved application performance by 40% through code optimization

Software Engineer
WebDev Co. | 2018 - 2020
• Developed and maintained RESTful APIs using Django REST Framework
• Implemented frontend components with React and Redux
• Collaborated with cross-functional teams to deliver features on time

EDUCATION
MSc in Computer Science
Stanford University | 2016 - 2018
GPA: 3.8/4.0

BSc in Computer Science
University of California, Berkeley | 2012 - 2016
GPA: 3.7/4.0'''
        },
        {
            'name': 'Michael Chen',
            'email': 'michael.chen@example.com',
            'position': 'Data Scientist',
            'resume_text': '''Michael Chen
Data Scientist
Email: michael.chen@example.com | Phone: (555) 987-6543 | Location: New York, NY

SUMMARY
Data Scientist with 4+ years of experience in machine learning and data analysis. 
Specialized in natural language processing and predictive modeling.

TECHNICAL SKILLS
• Programming: Python, R, SQL
• Machine Learning: TensorFlow, PyTorch, scikit-learn
• Data Analysis: Pandas, NumPy, Matplotlib
• Big Data: Spark, Hadoop
• Cloud: AWS, Google Cloud Platform

EXPERIENCE
Data Scientist
Data Insights Co. | 2019 - Present
• Developed and deployed machine learning models for predictive analytics
• Built NLP pipelines for text classification and sentiment analysis
• Led a team of 3 junior data scientists

Data Analyst
Analytics Pro | 2017 - 2019
• Performed data cleaning and exploratory data analysis
• Created dashboards and reports using Tableau
• Automated data pipelines using Python and SQL

EDUCATION
PhD in Data Science
Massachusetts Institute of Technology | 2013 - 2017
Thesis: "Advanced Machine Learning Techniques for Natural Language Processing"

BSc in Computer Science
Carnegie Mellon University | 2009 - 2013
GPA: 3.9/4.0'''
        }
    ]
    
    # Parse resumes using the resume parser
    candidates = []
    for i, resume in enumerate(sample_resumes):
        # In a real app, we would parse the actual file
        # For now, we'll use the text directly
        parsed_resume = resume_parser.parse_text(resume['resume_text'])
        
        # Calculate ATS score (simplified for this example)
        ats_score = min(100, 70 + (i * 15))  # Just for demo purposes
        
        candidates.append({
            'id': i + 1,
            'name': resume['name'],
            'email': resume['email'],
            'position': resume['position'],
            'status': 'New',
            'start_date': (datetime.now() + timedelta(days=14 + (i * 7))).strftime('%Y-%m-%d'),
            'resume_uploaded': True,
            'resume_file': f"{resume['name'].lower().replace(' ', '_')}_resume.pdf",
            'resume_analysis': {
                'match_score': ats_score,
                'skills': [skill['name'] for skill in parsed_resume.skills][:10],  # Top 10 skills
                'experience': f"{len(parsed_resume.experience)} years",
                'education': parsed_resume.education[0]['degree'] if parsed_resume.education else 'Not specified',
                'status': 'Pending Review',
                'summary': parsed_resume.raw_text[:200] + '...' if parsed_resume.raw_text else 'No summary available',
                'experience_details': [
                    {
                        'title': exp['title'],
                        'company': exp.get('company', 'Unknown Company'),
                        'duration': f"{exp.get('start', 'N/A')} - {exp.get('end', 'Present')}",
                        'description': exp.get('description', 'No description provided')
                    }
                    for exp in parsed_resume.experience[:3]  # Show up to 3 most recent positions
                ],
                'ats_score': ats_score,
                'missing_skills': parsed_resume.missing_skills[:5],  # Top 5 missing skills
                'compliance_issues': parsed_resume.compliance_issues
            },
            'avatar': f"https://ui-avatars.com/api/?name={resume['name'].replace(' ', '+')}&background=random"
        })

    # Handle sample candidate selection
    if request.method == 'POST' and 'use_sample' in request.form:
        sample_id = int(request.form.get('sample_id', 0))
        if sample_id == 1:
            sample_resume = """Sarah Johnson
Senior Software Engineer

CONTACT
Email: sarah.johnson@example.com
Phone: (555) 123-4567
Location: San Francisco, CA
LinkedIn: linkedin.com/in/sarahjohnson

SUMMARY
Experienced full-stack developer with 5+ years of experience in building scalable web applications using Python, Django, and React. Strong background in cloud technologies and DevOps practices.

EXPERIENCE

Senior Software Engineer
Tech Solutions Inc. | 2020 - Present
- Led a team of 5 developers in building a scalable e-commerce platform
- Implemented CI/CD pipelines using GitHub Actions and Docker
- Optimized database queries, reducing page load time by 40%

Software Developer
WebDev Agency | 2018 - 2020
- Developed and maintained RESTful APIs using Django REST Framework
- Created responsive UIs with React and Redux
- Collaborated with cross-functional teams to deliver high-quality software

EDUCATION
MSc in Computer Science
Stanford University | 2016 - 2018

SKILLS
- Programming: Python, JavaScript, TypeScript
- Frameworks: Django, React, Node.js
- Tools: Git, Docker, AWS, Kubernetes
- Databases: PostgreSQL, MongoDB

PROJECTS
E-commerce Platform
- Built a full-stack e-commerce platform with payment integration
- Implemented real-time inventory management
- Technologies: Django, React, PostgreSQL, Redis
"""
            # Create a temporary file with sample resume content
            os.makedirs('uploads', exist_ok=True)
            filepath = os.path.join('uploads', 'sample_resume_1.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sample_resume)
            
            try:
                # Parse the sample resume
                parser = ResumeParser()
                resume_data = parser.parse_resume(filepath)
                
                # Create a new candidate with parsed data
                new_candidate = {
                    'id': max(c['id'] for c in candidates) + 1 if candidates else 1,
                    'name': resume_data.name or 'Sample Candidate',
                    'email': resume_data.email or 'sample@example.com',
                    'position': 'Senior Software Engineer',
                    'status': 'New',
                    'start_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
                    'resume_uploaded': True,
                    'resume_file': 'sample_resume_1.txt',
                    'resume_analysis': {
                        'match_score': 85,
                        'skills': resume_data.skills or ['Python', 'Django', 'React', 'AWS', 'Docker'],
                        'experience': resume_data.experience or '5 years',
                        'education': resume_data.education or 'MSc in Computer Science',
                        'status': 'Sample Resume',
                        'summary': resume_data.summary or 'Experienced full-stack developer with expertise in Python and JavaScript.',
                        'experience_details': [
                            {
                                'title': exp.get('title', 'Unknown Position'),
                                'company': exp.get('company', 'Unknown Company'),
                                'duration': exp.get('duration', ''),
                                'description': exp.get('description', '')
                            } for exp in (resume_data.experience or [])
                        ] or [
                            {
                                'title': 'Senior Software Engineer',
                                'company': 'Tech Solutions Inc.',
                                'duration': '2020 - Present',
                                'description': 'Led a team of developers in building scalable web applications.'
                            }
                        ]
                    },
                    'avatar': f'https://ui-avatars.com/api/?name={(resume_data.name or "Sample").replace(" ", "+")}&background=random'
                }
                
                # Add the new candidate to the list
                candidates.append(new_candidate)
                session['candidates'] = candidates
                
                flash('Sample resume analyzed successfully!', 'success')
                
            except Exception as e:
                flash(f'Error processing sample resume: {str(e)}', 'danger')
                
            finally:
                # Clean up the temporary file
                try:
                    os.remove(filepath)
                except:
                    pass
    
    # Handle file upload
    elif request.method == 'POST' and 'resume' in request.files:
        from resume_parser import ResumeParser
        import os
        import uuid
        
        resume_file = request.files['resume']
        if resume_file.filename != '':
            # Create uploads directory if it doesn't exist
            os.makedirs('uploads', exist_ok=True)
            
            # Save the uploaded file with a unique name
            filename = f"{uuid.uuid4()}_{resume_file.filename}"
            filepath = os.path.join('uploads', filename)
            resume_file.save(filepath)
            
            try:
                # Parse the resume
                parser = ResumeParser()
                resume_data = parser.parse_resume(filepath)
                
                # Create a new candidate with parsed data
                new_candidate = {
                    'id': max(c['id'] for c in candidates) + 1 if candidates else 1,
                    'name': resume_data.name or 'New Candidate',
                    'email': resume_data.email or '',
                    'position': request.form.get('position', 'Not specified'),
                    'status': 'New',
                    'start_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
                    'resume_uploaded': True,
                    'resume_file': resume_file.filename,
                    'resume_analysis': {
                        'match_score': 0,  # You can calculate this based on job requirements
                        'skills': resume_data.skills or [],
                        'experience': resume_data.experience or 'Not specified',
                        'education': resume_data.education or 'Not specified',
                        'status': 'Pending Review',
                        'summary': resume_data.summary or '',
                        'experience_details': [
                            {
                                'title': exp.get('title', 'Unknown Position'),
                                'company': exp.get('company', 'Unknown Company'),
                                'duration': exp.get('duration', ''),
                                'description': exp.get('description', '')
                            } for exp in (resume_data.experience or [])
                        ]
                    },
                    'avatar': f'https://ui-avatars.com/api/?name={(resume_data.name or "New Candidate").replace(" ", "+")}&background=random'
                }
                
                # Add the new candidate to the list
                candidates.append(new_candidate)
                session['candidates'] = candidates
                
                flash('Resume uploaded and analyzed successfully!', 'success')
                
            except Exception as e:
                flash(f'Error processing resume: {str(e)}', 'danger')
                
            finally:
                # Clean up the temporary file
                try:
                    os.remove(filepath)
                except:
                    pass
    
    # Add candidates to the onboarding data
    onboarding_data['candidates'] = candidates
    return render_template('onboarding.html', **onboarding_data)

@app.route('/resume-review')
@app.route('/resume-review/<int:candidate_id>')
def resume_review_route(candidate_id=None):
    # Sample candidates data (same as in onboarding_route)
    candidates = [
        {
            'id': 1,
            'name': 'Sarah Johnson',
            'email': 'sarah.johnson@example.com',
            'position': 'Senior Software Engineer',
            'status': 'New',
            'start_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            'resume_uploaded': True,
            'resume_file': 'sarah_johnson_resume.pdf',
            'resume_analysis': {
                'match_score': 87,
                'skills': ['Python', 'Django', 'React', 'AWS', 'Docker', 'Kubernetes', 'REST APIs', 'Microservices'],
                'experience': '8 years',
                'education': 'Masters in Computer Science',
                'status': 'Pending Review',
                'summary': 'Experienced full-stack developer with strong backend skills in Python and Django, and frontend experience with React. Has led multiple successful projects from conception to deployment.',
                'experience_details': [
                    {
                        'title': 'Senior Software Engineer',
                        'company': 'Tech Solutions Inc.',
                        'duration': '3 years',
                        'description': 'Led a team of 5 developers in building scalable microservices.'
                    },
                    {
                        'title': 'Software Engineer',
                        'company': 'WebCraft Studios',
                        'duration': '4 years',
                        'description': 'Developed and maintained multiple web applications using Django and React.'
                    }
                ]
            },
            'avatar': 'https://randomuser.me/api/portraits/women/44.jpg'
        },
        {
            'id': 2,
            'name': 'Michael Chen',
            'email': 'michael.chen@example.com',
            'position': 'Data Scientist',
            'status': 'In Progress',
            'start_date': (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d'),
            'resume_uploaded': True,
            'resume_file': 'michael_chen_resume.pdf',
            'resume_analysis': {
                'match_score': 92,
                'skills': ['Python', 'Machine Learning', 'TensorFlow', 'SQL', 'Data Visualization', 'Pandas', 'NLP', 'Deep Learning'],
                'experience': '5 years',
                'education': 'PhD in Data Science',
                'status': 'Reviewed',
                'summary': 'Data scientist with expertise in machine learning and deep learning. Strong background in natural language processing and computer vision.',
                'experience_details': [
                    {
                        'title': 'Data Scientist',
                        'company': 'DataInsights Inc.',
                        'duration': '3 years',
                        'description': 'Developed and deployed ML models for customer behavior prediction.'
                    },
                    {
                        'title': 'Machine Learning Engineer',
                        'company': 'AI Research Lab',
                        'duration': '2 years',
                        'description': 'Researched and implemented state-of-the-art deep learning models.'
                    }
                ]
            },
            'avatar': 'https://randomuser.me/api/portraits/men/32.jpg'
        },
        {
            'id': 3,
            'name': 'Emily Rodriguez',
            'email': 'emily.rodriguez@example.com',
            'position': 'UX/UI Designer',
            'status': 'New',
            'start_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'resume_uploaded': False,
            'resume_analysis': None,
            'avatar': 'https://randomuser.me/api/portraits/women/68.jpg'
        },
        {
            'id': 4,
            'name': 'David Kim',
            'email': 'david.kim@example.com',
            'position': 'DevOps Engineer',
            'status': 'In Progress',
            'start_date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'resume_uploaded': True,
            'resume_file': 'david_kim_resume.pdf',
            'resume_analysis': {
                'match_score': 78,
                'skills': ['AWS', 'Terraform', 'Docker', 'Kubernetes', 'CI/CD', 'Linux', 'Bash', 'Jenkins'],
                'experience': '6 years',
                'education': 'Bachelors in Computer Engineering',
                'status': 'Pending Review',
                'summary': 'DevOps engineer with extensive experience in cloud infrastructure and CI/CD pipelines. Strong background in automation and system administration.',
                'experience_details': [
                    {
                        'title': 'DevOps Engineer',
                        'company': 'CloudScale Technologies',
                        'duration': '3 years',
                        'description': 'Managed cloud infrastructure and implemented CI/CD pipelines.'
                    },
                    {
                        'title': 'System Administrator',
                        'company': 'Tech Solutions Inc.',
                        'duration': '3 years',
                        'description': 'Maintained and optimized server infrastructure.'
                    }
                ]
            },
            'avatar': 'https://randomuser.me/api/portraits/men/75.jpg'
        },
        {
            'id': 5,
            'name': 'Priya Patel',
            'email': 'priya.patel@example.com',
            'position': 'Product Manager',
            'status': 'Completed',
            'start_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            'resume_uploaded': True,
            'resume_file': 'priya_patel_resume.pdf',
            'resume_analysis': {
                'match_score': 95,
                'skills': ['Product Strategy', 'Agile', 'JIRA', 'Market Research', 'Roadmapping', 'User Stories', 'Product Lifecycle'],
                'experience': '7 years',
                'education': 'MBA in Technology Management',
                'status': 'Hired',
                'summary': 'Results-driven product manager with a track record of successful product launches. Strong background in agile methodologies and cross-functional team leadership.',
                'experience_details': [
                    {
                        'title': 'Senior Product Manager',
                        'company': 'ProductLabs Inc.',
                        'duration': '4 years',
                        'description': 'Led product strategy and roadmap for multiple successful products.'
                    },
                    {
                        'title': 'Product Owner',
                        'company': 'TechStart Inc.',
                        'duration': '3 years',
                        'description': 'Managed product backlog and worked closely with development teams.'
                    }
                ]
            },
            'avatar': 'https://randomuser.me/api/portraits/women/22.jpg'
        }
    ]
    
    # If a specific candidate is requested, return their data
    if candidate_id:
        candidate = next((c for c in candidates if c['id'] == candidate_id), None)
        if not candidate:
            abort(404)
        return render_template('resume_review.html', 
                            candidate=candidate,
                            candidates=candidates)
    
    # Otherwise, show the first candidate by default
    return render_template('resume_review.html', 
                         candidate=candidates[0] if candidates else None,
                         candidates=candidates)

# Mock data for Data Scientist position
MOCK_DATA_SCIENTIST_DATA = {
    'name': 'John Doe',
    'email': 'john.doe@example.com',
    'phone': '(555) 123-4567',
    'title': 'Data Scientist',
    'skills': [
        'Python', 'Machine Learning', 'Deep Learning', 'Data Analysis',
        'Pandas', 'NumPy', 'Scikit-learn', 'TensorFlow', 'PyTorch',
        'SQL', 'MongoDB', 'Data Visualization', 'Natural Language Processing',
        'Computer Vision', 'AWS', 'Docker', 'Git'
    ],
    'experience': [
        {
            'title': 'Senior Data Scientist',
            'company': 'TechCorp',
            'duration': '3 years',
            'description': 'Led machine learning projects and mentored junior team members.'
        },
        {
            'title': 'Data Scientist',
            'company': 'DataInsights Inc',
            'duration': '2 years',
            'description': 'Developed predictive models and performed data analysis.'
        }
    ],
    'education': [
        {
            'degree': 'MSc in Data Science',
            'institution': 'Tech University',
            'year': '2018'
        },
        {
            'degree': 'BSc in Computer Science',
            'institution': 'State University',
            'year': '2016'
        }
    ]
}

@app.route('/resume-screening', methods=['GET', 'POST'])
def resume_screening_route():
    from resume_parser import ResumeParser
    import os
    from werkzeug.utils import secure_filename
    
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'resume' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['resume']
        
        # If user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Parse the resume
            parser = ResumeParser()
            resume_data = parser.parse_resume(filepath)
            
            # If no resume data was parsed, use mock data
            if not resume_data.skills and not resume_data.experience and not resume_data.education:
                resume_data = type('ResumeData', (), MOCK_DATA_SCIENTIST_DATA)
            
            # Calculate match score with Data Scientist job description
            job_title = 'Data Scientist • 5 years experience'
            job_description = """
            We are looking for an experienced Data Scientist with expertise in machine learning, 
            data analysis, and programming. The ideal candidate should have:
            
            Requirements:
            - 5+ years of experience in data science or related field
            - Strong programming skills in Python
            - Experience with machine learning frameworks (TensorFlow, PyTorch)
            - Knowledge of SQL and NoSQL databases
            - Experience with data visualization tools
            - Strong problem-solving skills
            - Experience with cloud platforms (AWS, GCP, or Azure)
            - Good understanding of software development best practices
            """
            
            match_score = calculate_match_score(resume_data, job_title, job_description)
            
            # Create a candidate object
            candidate = {
                'id': len(db.candidates) + 1,
                'name': resume_data.name or MOCK_DATA_SCIENTIST_DATA['name'],
                'email': resume_data.email or MOCK_DATA_SCIENTIST_DATA['email'],
                'phone': resume_data.phone or MOCK_DATA_SCIENTIST_DATA['phone'],
                'resume_path': filepath,
                'score': match_score['score'],
                'summary': {
                    'skills': resume_data.skills or MOCK_DATA_SCIENTIST_DATA['skills'],
                    'experience': resume_data.experience or MOCK_DATA_SCIENTIST_DATA['experience'],
                    'education': resume_data.education or MOCK_DATA_SCIENTIST_DATA['education'],
                    'match_score': match_score
                },
                'status': 'New',
                'applied_date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # Add to database (or in-memory list for now)
            db.candidates.append(candidate)
            
            # Redirect to the candidate's analysis page
            return redirect(url_for('manual_review', candidate_id=candidate['id']))
    
    # Get candidates with their ATS scores
    candidates = sorted(db.candidates, key=lambda x: x.get('score', 0), reverse=True)
    return render_template('resume_screening.html', candidates=candidates)

@app.route('/resume/review/<int:candidate_id>', methods=['GET', 'POST'])
def manual_review(candidate_id):
    # Find the candidate
    candidate = next((c for c in db.candidates if c['id'] == candidate_id), None)
    if not candidate:
        flash('Candidate not found', 'error')
        return redirect(url_for('resume_screening_route'))
    
    # Get the resume analysis data
    summary = candidate.get('summary', {})
    match_score = summary.get('match_score', {})
    skills = summary.get('skills', [])
    experience = summary.get('experience', [])
    education = summary.get('education', [])
    
    # Calculate skill categories for visualization
    skill_categories = {
        'Programming': len([s for s in skills if any(tech in s.lower() for tech in ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust'])]),
        'Web': len([s for s in skills if any(tech in s.lower() for tech in ['html', 'css', 'javascript', 'react', 'angular', 'vue', 'node', 'django', 'flask'])]),
        'Database': len([s for s in skills if any(tech in s.lower() for tech in ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis'])]),
        'DevOps': len([s for s in skills if any(tech in s.lower() for tech in ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd', 'jenkins'])]),
        'Other': len(skills) - sum([
            len([s for s in skills if any(tech in s.lower() for tech in ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust'])]),
            len([s for s in skills if any(tech in s.lower() for tech in ['html', 'css', 'javascript', 'react', 'angular', 'vue', 'node', 'django', 'flask'])]),
            len([s for s in skills if any(tech in s.lower() for tech in ['sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'redis'])]),
            len([s for s in skills if any(tech in s.lower() for tech in ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd', 'jenkins'])])
        ])
    }
    
    # Prepare data for the template
    analysis_data = {
        'candidate': candidate,
        'skills': skills,
        'experience': experience,
        'education': education,
        'match_score': match_score,
        'skill_categories': skill_categories,
        'missing_skills': match_score.get('missing_skills', []),
        'matched_skills': match_score.get('matched_skills', []),
        'experience_match': match_score.get('experience_match', 0),
        'overall_score': match_score.get('score', 0)
    }
    
    return render_template('resume_review.html', **analysis_data)
    
    if request.method == 'POST':
        # Update candidate status and notes
        candidate['status'] = request.form.get('status', candidate.get('status', 'new'))
        candidate['review_notes'] = request.form.get('review_notes', candidate.get('review_notes', ''))
        flash('Review saved successfully', 'success')
        return redirect(url_for('manual_review', candidate_id=candidate_id))
    
    return render_template('hr_manual_review.html', candidate=candidate)

@app.route('/interview/ai/<int:candidate_id>', methods=['GET'])
def ai_interview(candidate_id):
    # Find the candidate
    candidate = next((c for c in db.candidates if c['id'] == candidate_id), None)
    if not candidate:
        flash('Candidate not found', 'error')
        return redirect(url_for('resume_screening_route'))
    
    return render_template('ai_interview.html', candidate=candidate)

@app.route('/schedule-appointment')
def schedule_appointment_route():
    return render_template('schedule_appointment.html')

@app.route('/hr/schedule', methods=['GET', 'POST'])
def manage_appointments():
    """Manage all appointments and scheduling"""
    if request.method == 'POST':
        # Handle form submission for new appointment
        try:
            candidate_id = request.form.get('candidate_id')
            interview_type = request.form.get('interview_type')
            interview_date = datetime.strptime(request.form.get('interview_date'), '%Y-%m-%dT%H:%M')
            duration = int(request.form.get('duration', 30))
            interviewer = request.form.get('interviewer')
            meeting_link = request.form.get('meeting_link')
            notes = request.form.get('notes', '')
            
            # Create new interview record
            interview = Interview(
                candidate_id=candidate_id,
                interview_type=interview_type,
                interview_date=interview_date,
                duration=duration,
                interviewer=interviewer,
                meeting_link=meeting_link,
                status='scheduled',
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.interviews.append(interview)
            
            # Update candidate status
            candidate = next((c for c in db.candidates if c.id == candidate_id), None)
            if candidate:
                candidate.status = 'interview_scheduled'
                candidate.updated_at = datetime.now()
            
            flash('Interview scheduled successfully!', 'success')
            return redirect(url_for('hr_interviews'))
            
        except Exception as e:
            flash(f'Error scheduling interview: {str(e)}', 'danger')
    
    # For GET request, show scheduling page with available candidates
    available_candidates = [c for c in db.candidates if c.status in ['applied', 'screening']]
    interviewers = ['HR Manager', 'Technical Lead', 'Hiring Manager']
    
    return render_template('schedule_appointment.html',
                         candidates=available_candidates,
                         interviewers=interviewers)

@app.route('/hr/schedule/<int:appointment_id>', methods=['GET', 'POST'])
def manage_appointment(appointment_id):
    """View or edit a specific appointment"""
    interview = next((i for i in db.interviews if i.id == appointment_id), None)
    if not interview:
        flash('Appointment not found', 'danger')
        return redirect(url_for('manage_appointments'))
    
    if request.method == 'POST':
        try:
            # Update interview details
            interview.interview_type = request.form.get('interview_type', interview.interview_type)
            interview_date_str = request.form.get('interview_date')
            if interview_date_str:
                interview.interview_date = datetime.strptime(interview_date_str, '%Y-%m-%dT%H:%M')
            interview.duration = int(request.form.get('duration', interview.duration))
            interview.interviewer = request.form.get('interviewer', interview.interviewer)
            interview.meeting_link = request.form.get('meeting_link', interview.meeting_link)
            interview.notes = request.form.get('notes', interview.notes)
            interview.status = request.form.get('status', interview.status)
            interview.updated_at = datetime.now()
            
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('hr_interviews'))
            
        except Exception as e:
            flash(f'Error updating appointment: {str(e)}', 'danger')
    
    # For GET request, show edit form
    candidates = [c for c in db.candidates]
    interviewers = ['HR Manager', 'Technical Lead', 'Hiring Manager']
    
    return render_template('edit_appointment.html',
                         interview=interview,
                         candidates=candidates,
                         interviewers=interviewers)

@app.route('/api/recruitment-pipeline')
def get_recruitment_pipeline():
    """
    API endpoint to get detailed recruitment pipeline data with enhanced mock data.
    
    The recruitment pipeline consists of the following stages:
    - sourced: Candidates identified through various channels but haven't applied yet
    - applied: Candidates who have submitted job applications
    - phone_screen: Initial screening call to assess basic qualifications
    - technical_interview: In-depth evaluation of technical skills and knowledge
    - final_interview: Final round with key stakeholders/management
    - offer_extended: Job offer has been made to the candidate
    - hired: Candidate has accepted the offer and joined the company
    
    Returns:
        JSON: Pipeline data with candidate counts and details for each stage
    """
    pipeline_data = {}
    
    # Define all pipeline stages with their display names and realistic counts
    stages = [
        {'id': 'sourced', 'name': 'Sourced', 'count_range': (120, 180), 'days_ago_range': (60, 90)},
        {'id': 'applied', 'name': 'Applied', 'count_range': (80, 120), 'days_ago_range': (30, 60)},
        {'id': 'phone_screen', 'name': 'Phone Screen', 'count_range': (40, 60), 'days_ago_range': (15, 30)},
        {'id': 'technical_interview', 'name': 'Technical Interview', 'count_range': (20, 30), 'days_ago_range': (7, 21)},
        {'id': 'final_interview', 'name': 'Final Interview', 'count_range': (8, 15), 'days_ago_range': (3, 14)},
        {'id': 'offer_extended', 'name': 'Offer Extended', 'count_range': (3, 8), 'days_ago_range': (1, 7)},
        {'id': 'hired', 'name': 'Hired', 'count_range': (1, 3), 'days_ago_range': (0, 3)}
    ]
    
    # Common position titles
    positions = [
        'Senior Software Engineer', 'Frontend Developer', 'Backend Developer',
        'Full Stack Developer', 'DevOps Engineer', 'Data Scientist',
        'Machine Learning Engineer', 'Mobile Developer', 'QA Engineer',
        'Product Manager', 'UX/UI Designer', 'Technical Lead'
    ]
    
    # Common first and last names for realistic candidate names
    first_names = ['James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph',
                  'Thomas', 'Charles', 'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth',
                  'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen', 'Lisa', 'Nancy', 'Betty']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
                 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White']
    
    for stage in stages:
        stage_id = stage['id']
        stage_name = stage['name']
        count = random.randint(*stage['count_range'])
        
        candidates = []
        for i in range(1, count + 1):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
            
            # Generate a realistic application date based on stage
            days_ago = random.randint(*stage['days_ago_range'])
            applied_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            # Generate a realistic score that tends to increase through the pipeline
            base_score = {
                'sourced': 50,
                'applied': 60,
                'phone_screen': 65,
                'technical_interview': 70,
                'final_interview': 80,
                'offer_extended': 90,
                'hired': 95
            }[stage_id]
            
            # Add some variation to the score
            score = base_score + random.randint(-5, 5)
            score = max(0, min(100, score))  # Ensure score is between 0-100
            
            candidates.append({
                'id': f"{stage_id[:3].upper()}{i:04d}",
                'name': f"{first_name} {last_name}",
                'email': email,
                'phone': f"+1 (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
                'applied_date': applied_date,
                'status': stage_name,
                'score': score,
                'position': random.choice(positions),
                'experience': f"{random.randint(2, 15)} years",
                'location': f"{random.choice(['San Francisco', 'New York', 'Austin', 'Seattle', 'Boston', 'Chicago', 'Remote'])}",
                'source': random.choice(['LinkedIn', 'Company Website', 'Referral', 'Job Board', 'Campus Recruiting', 'Agency']),
                'last_updated': (datetime.now() - timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d')
            })
        
        pipeline_data[stage_id] = {
            'name': stage_name,
            'count': count,
            'candidates': candidates
        }
    
    return jsonify(pipeline_data)


"""
    API endpoint to get top candidates data with enhanced mock data.
    
    Returns:
        JSON: List of top candidates with detailed information
    """
@app.route('/api/top-candidates')
def get_top_candidates():
    # More comprehensive position titles
    positions = [
        'Senior Software Engineer', 'Frontend Developer', 'Backend Developer',
        'Full Stack Developer', 'DevOps Engineer', 'Data Scientist',
        'Machine Learning Engineer', 'Mobile Developer', 'QA Engineer',
        'Product Manager', 'UX/UI Designer', 'Technical Lead',
        'Cloud Architect', 'Data Engineer', 'Security Engineer',
        'Site Reliability Engineer', 'Engineering Manager', 'CTO'
    ]
    
    # More detailed candidate statuses with realistic weights
    statuses = [
        {'status': 'New Application', 'weight': 25},
        {'status': 'Resume Review', 'weight': 20},
        {'status': 'Phone Screen Scheduled', 'weight': 15},
        {'status': 'Technical Assessment', 'weight': 15},
        {'status': 'Onsite Interview', 'weight': 10},
        {'status': 'Final Interview', 'weight': 8},
        {'status': 'Reference Check', 'weight': 5},
        {'status': 'Offer Extended', 'weight': 2}
    ]
    
    # Skills matrix for different roles
    role_skills = {
        'Senior Software Engineer': ['Python', 'Java', 'System Design', 'Algorithms', 'Microservices'],
        'Frontend Developer': ['React', 'TypeScript', 'JavaScript', 'HTML/CSS', 'Redux'],
        'Backend Developer': ['Node.js', 'Python', 'Java', 'REST APIs', 'Databases'],
        'DevOps Engineer': ['AWS', 'Docker', 'Kubernetes', 'CI/CD', 'Terraform'],
        'Data Scientist': ['Python', 'Machine Learning', 'Pandas', 'SQL', 'Statistics']
    }
    
    # Common first and last names for realistic candidate names
    first_names = ['James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph',
                  'Thomas', 'Charles', 'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth',
                  'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen', 'Lisa', 'Nancy', 'Betty']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
                 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Thompson', 'White']
    
    top_candidates = []
    
    for i in range(1, 31):  # Generate 30 top candidates
        # Select a random position and get relevant skills
        position = random.choice(positions)
        skills = []
        
        # Get relevant skills for the position if available, otherwise use common skills
        for role, role_skills_list in role_skills.items():
            if role.lower() in position.lower():
                skills = role_skills_list
                break
        
        if not skills:  # If no specific skills found, use common ones
            skills = ['Python', 'JavaScript', 'SQL', 'Git', 'REST APIs', 'Problem Solving']
        
        # Add 2-4 more random skills
        all_skills = [
            'React', 'Node.js', 'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'TypeScript', 'Java', 'C#', 'Go', 'Ruby', 'PHP', 'Swift', 'Kotlin',
            'Machine Learning', 'Data Analysis', 'Big Data', 'AI', 'Blockchain',
            'Cybersecurity', 'DevOps', 'Agile', 'Scrum', 'TDD', 'CI/CD', 'Microservices'
        ]
        
        additional_skills = random.sample(
            [s for s in all_skills if s not in skills],
            k=random.randint(2, 4)
        )
        skills.extend(additional_skills)
        
        # Generate candidate details
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
        
        # Generate a realistic score (80-100 for top candidates)
        score = random.randint(80, 100)
        
        # Select status with weights
        status = random.choices(
            [s['status'] for s in statuses],
            weights=[s['weight'] for s in statuses],
            k=1
        )[0]
        
        candidate = {
            'id': f"TC{i:03d}",
            'name': f"{random.choice(['John', 'Jane', 'Robert', 'Emily', 'Michael', 'Sarah'])} {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}",
            'email': f"candidate.top{i}@example.com",
            'phone': f"+1 (555) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            'position': random.choice(positions),
            'score': score,
            'status': status,
            'experience': f"{random.randint(2, 15)}+ years",
            'location': f"{random.choice(['San Francisco', 'New York', 'Remote', 'Austin', 'Seattle'])}",
            'last_updated': (datetime.now() - timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d'),
            'skills': [
                random.choice(['Python', 'JavaScript', 'Java', 'C++', 'TypeScript']),
                random.choice(['React', 'Node.js', 'Django', 'Spring', 'Angular']),
                random.choice(['AWS', 'Docker', 'Kubernetes', 'CI/CD'])
            ]
        }
        
        top_candidates.append(candidate)
    
    # Sort by score in descending order
    top_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'total': len(top_candidates),
        'candidates': top_candidates
    })

# HR Profile
@app.route('/hr/profile')
def hr_profile():
    """HR Profile page"""
    if 'user_role' not in session or session['user_role'] != 'hr':
        return redirect(url_for('select_role'))
    return render_template('hr_profile.html')

# HR Dashboard
@app.route('/hr/dashboard')
def hr_dashboard():
    """HR Dashboard route"""
    # Get counts for dashboard stats using SQLAlchemy queries
    total_candidates = Candidate.query.count()
    total_applications = Application.query.count()
    interviews_scheduled = Application.query.filter_by(status='interview_scheduled').count()
    jobs_posted = JobPosting.query.filter_by(is_active=True).count()
    
    # Calculate average ATS score
    avg_ats_score = db.session.query(db.func.avg(Candidate.ats_score) * 100).scalar() or 0
    avg_ats_score = round(avg_ats_score, 1)
    
    # Calculate hiring rate (assuming 'hired' status means successful hire)
    total_apps = Application.query.count()
    hired_count = Application.query.filter_by(status='hired').count()
    hiring_rate = round((hired_count / total_apps * 100), 1) if total_apps > 0 else 0
    
    # Get recent activities
    recent_applications = Application.query.order_by(Application.updated_at.desc()).limit(10).all()
    recent_activities = get_recent_activities(recent_applications)
    
    # Get top candidates (top 5 by score)
    top_candidates = Candidate.query.filter(Candidate.ats_score.isnot(None))\
                                 .order_by(Candidate.ats_score.desc())\
                                 .limit(5).all()
    
    # Get application status distribution
    status_counts = db.session.query(
        Application.status,
        db.func.count(Application.id)
    ).group_by(Application.status).all()
    
    status_counts = {
        status.replace('_', ' ').title(): count 
        for status, count in status_counts
    }
    
    # Calculate ATS score distribution
    score_distribution = {
        '0-20': Candidate.query.filter(Candidate.ats_score <= 0.2).count(),
        '21-40': Candidate.query.filter(Candidate.ats_score > 0.2, Candidate.ats_score <= 0.4).count(),
        '41-60': Candidate.query.filter(Candidate.ats_score > 0.4, Candidate.ats_score <= 0.6).count(),
        '61-80': Candidate.query.filter(Candidate.ats_score > 0.6, Candidate.ats_score <= 0.8).count(),
        '81-100': Candidate.query.filter(Candidate.ats_score > 0.8).count()
    }
    
    # Get hiring trends (last 6 months)
    current_date = datetime.now()
    hiring_trends = {}
    
    for i in range(5, -1, -1):
        target_date = current_date - timedelta(days=30*i)
        month_year = target_date.strftime('%b %Y')
        
        # Query for hired applications in this month
        month_start = datetime(target_date.year, target_date.month, 1)
        if target_date.month == 12:
            next_month = datetime(target_date.year + 1, 1, 1)
        else:
            next_month = datetime(target_date.year, target_date.month + 1, 1)
            
        hired_count = Application.query.filter(
            Application.status == 'hired',
            Application.updated_at >= month_start,
            Application.updated_at < next_month
        ).count()
        
        hiring_trends[month_year] = hired_count
    
    # Enhanced sentiment analysis data with more detailed metrics
    sentiment_data = {
        'positive': {
            'count': 24,
            'change': 3,  # 3 more than last month
            'trend': 'up',
            'comments': [
                'Great work environment and team collaboration',
                'Management is supportive and approachable',
                'Good work-life balance',
                'Excellent learning opportunities',
                'Competitive compensation and benefits'
            ]
        },
        'neutral': {
            'count': 15,
            'change': -2,  # 2 less than last month
            'trend': 'down',
            'comments': [
                'Standard work environment',
                'Company policies are reasonable',
                'Typical corporate culture',
                'Average benefits package',
                'Management is adequate'
            ]
        },
        'negative': {
            'count': 6,
            'change': 1,  # 1 more than last month
            'trend': 'up',
            'comments': [
                'Limited career growth opportunities',
                'Workload can be overwhelming at times',
                'Communication between departments needs improvement',
                'Salary increments could be better',
                'Some processes are outdated'
            ]
        },
        'sentiment_score': 68,  # Out of 100
        'previous_score': 65,   # Previous month's score
        'total_responses': 45,
        'response_rate': '78%',
        'key_improvement_areas': [
            'Career Development (32% of feedback)',
            'Workload Management (28% of feedback)',
            'Communication (22% of feedback)',
            'Compensation (18% of feedback)'
        ]
    }
    
    # Calculate total responses from sentiment data
    sentiment_total = sum(sentiment_data[category]['count'] for category in ['positive', 'neutral', 'negative'])
    
    # Recruitment pipeline data matching the modal mock data
    recruitment_pipeline = {
        'Sourced': 12,
        'Applied': 8,
        'Phone Screen': 6,
        'Technical Interview': 4,
        'Final Interview': 3,
        'Offer Extended': 2,
        'Hired': 1
    }
    
    # Enhanced top candidates data with more details
    enhanced_top_candidates = [
        {
            'id': 'TC001',
            'name': 'Alex Johnson',
            'email': 'alex.johnson@example.com',
            'score': 98,
            'position': 'Senior Full Stack Developer',
            'status': 'Final Interview',
            'last_updated': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        },
        {
            'id': 'TC002',
            'name': 'Sarah Williams',
            'email': 'sarah.williams@example.com',
            'score': 95,
            'position': 'Data Scientist',
            'status': 'Technical Interview',
            'last_updated': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        },
        {
            'id': 'TC003',
            'name': 'Michael Chen',
            'email': 'michael.chen@example.com',
            'score': 92,
            'position': 'DevOps Engineer',
            'status': 'Phone Screen',
            'last_updated': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        },
        {
            'id': 'TC004',
            'name': 'Emily Davis',
            'email': 'emily.davis@example.com',
            'score': 90,
            'position': 'UX Designer',
            'status': 'Applied',
            'last_updated': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')
        }
    ]
    
    # Skill distribution data - matching the modal
    skill_distribution = {
        'Programming Languages': {
            'Python': 85,
            'JavaScript': 78,
            'Java': 65,
            'C++': 55,
            'TypeScript': 72
        },
        'Frameworks': {
            'React': 82,
            'Node.js': 75,
            'Django': 68,
            'Spring': 58,
            'Angular': 62
        },
        'Cloud & DevOps': {
            'AWS': 78,
            'Docker': 72,
            'Kubernetes': 65,
            'CI/CD': 70,
            'Terraform': 58
        },
        'AI/ML': {
            'TensorFlow': 68,
            'PyTorch': 72,
            'NLP': 65,
            'Computer Vision': 60,
            'Reinforcement Learning': 55
        },
        'Databases': {
            'PostgreSQL': 75,
            'MongoDB': 70,
            'Redis': 65,
            'MySQL': 68,
            'Elasticsearch': 60
        }
    }
    
    # Time to fill positions (in days)
    time_to_fill = {
        'Engineering': random.randint(25, 45),
        'Product': random.randint(20, 40),
        'Design': random.randint(15, 35),
        'Marketing': random.randint(10, 30),
        'Sales': random.randint(5, 25)
    }
    
    return render_template(
        'dashboard.html',
        total_candidates=total_candidates,
        total_applications=total_applications,
        interviews_scheduled=interviews_scheduled,
        jobs_posted=jobs_posted,
        recent_activities=recent_activities,
        top_candidates=enhanced_top_candidates,
        status_counts=status_counts,
        score_distribution=score_distribution,
        hiring_trends=hiring_trends,
        avg_ats_score=avg_ats_score,
        hiring_rate=hiring_rate,
        sentiment_data=sentiment_data,
        sentiment_total=sentiment_total if sentiment_total > 0 else 1,  # Avoid division by zero
        recruitment_pipeline=recruitment_pipeline,
        skill_distribution=skill_distribution,
        time_to_fill=time_to_fill
    )

# Candidate Routes

@app.route('/candidate/documents')
def candidate_documents():
    """Candidate documents management route"""
    if 'user_role' not in session or session['user_role'] != 'candidate':
        return redirect(url_for('login_candidate'))
    
    # In a real app, this would come from the database
    documents = [
        {'id': 1, 'name': 'Resume.pdf', 'type': 'Resume', 'uploaded': '2023-10-01'},
        {'id': 2, 'name': 'Cover_Letter.pdf', 'type': 'Cover Letter', 'uploaded': '2023-10-02'},
    ]
    
    return render_template('candidate_documents.html', documents=documents)


@app.route('/candidate/interviews')
def candidate_interviews():
    """Candidate interviews route"""
    if 'user_role' not in session or session['user_role'] != 'candidate':
        return redirect(url_for('login_candidate'))
    
    # Mock interview data with future dates
    interviews = [
        {
            'id': 1,
            'job_title': 'Senior Developer',
            'company': 'TechCorp Inc.',
            'date': datetime.now().strftime('%Y-%m-%d 14:00'),  # Changed to today
            'type': 'Technical',
            'round': 'Round 2',
            'duration': '1 hour',
            'platform': 'Zoom Meeting',
            'status': 'upcoming',
            'notify_me': False
        },
        {
            'id': 2,
            'job_title': 'Product Manager',
            'company': 'InnovateX',
            'date': (datetime.now() + timedelta(weeks=2, days=3)).strftime('%Y-%m-%d 10:00'),
            'type': 'HR',
            'round': 'Final Round',
            'duration': '45 minutes',
            'platform': 'Phone Call',
            'status': 'upcoming',
            'notify_me': False
        },
        {
            'id': 3,
            'job_title': 'Data Scientist',
            'company': 'DataSphere',
            'date': (datetime.now() + timedelta(weeks=5, days=2)).strftime('%Y-%m-%d 15:30'),
            'type': 'Technical',
            'round': 'Round 1',
            'duration': '1 hour',
            'platform': 'Microsoft Teams',
            'status': 'upcoming',
            'notify_me': False
        }
    ]
    
    # Check if there are any notifications in the session
    notification = session.pop('notification', None)
    
    return render_template('candidate_interviews.html', 
                         interviews=interviews,
                         notification=notification)


@app.route('/candidate/profile', methods=['GET', 'POST'])
def candidate_profile():
    """Candidate profile management route"""
    if 'user_role' not in session or session['user_role'] != 'candidate':
        return redirect(url_for('login_candidate'))
    
    # In a real app, this would come from and update the database
    profile = {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'phone': '+1234567890',
        'location': 'New York, USA',
        'bio': 'Experienced software developer with 5+ years of experience...',
        'skills': ['Python', 'JavaScript', 'React', 'SQL']
    }
    
    if request.method == 'POST':
        # Handle profile update logic here
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('candidate_profile'))
    
    return render_template('candidate_profile.html', profile=profile)

@app.route('/candidate/onboarding', methods=['GET', 'POST'])
def candidate_onboarding():
    """
    Candidate onboarding dashboard
    Handles both displaying the onboarding progress and processing form submissions
    """
    # Authentication check
    if 'user_role' not in session or session['user_role'] != 'candidate':
        return redirect(url_for('login_candidate'))
    
    # Get candidate ID from session
    candidate_id = session.get('user_id')
    
    # In a real app, you would fetch this from the database
    # For now, we'll use mock data
    
    # Check profile completion (mock implementation)
    def is_profile_complete(candidate_id):
        # In a real app, check if all required profile fields are filled
        # For now, we'll assume it's complete if the user has a name
        return bool(session.get('user_name'))
    
    # Check documents (mock implementation)
    def has_uploaded_documents(candidate_id):
        # In a real app, check if required documents are uploaded
        # For now, we'll return False to show the upload prompt
        return False
    
    # Check assessment completion (mock implementation)
    def is_assessment_complete(candidate_id):
        # In a real app, check if assessment is completed
        return False
    
    # Check preferences (mock implementation)
    def are_preferences_set(candidate_id):
        # In a real app, check if job preferences are set
        return False
    
    # Handle form submission for completing steps
    if request.method == 'POST':
        step = request.form.get('step')
        if step == 'complete_profile':
            return redirect(url_for('candidate_profile'))
        elif step == 'upload_documents':
            return redirect(url_for('candidate_documents'))
        elif step == 'start_assessment':
            # In a real app, this would start an assessment
            flash('Assessment started!', 'info')
            return redirect(url_for('candidate_onboarding'))
        elif step == 'set_preferences':
            return redirect(url_for('candidate_profile') + '#preferences')
    
    # Get completion status for each step
    profile_complete = is_profile_complete(candidate_id)
    documents_uploaded = has_uploaded_documents(candidate_id)
    assessment_complete = is_assessment_complete(candidate_id)
    preferences_set = are_preferences_set(candidate_id)
    
    # Calculate progress
    completed_steps = sum([
        profile_complete,
        documents_uploaded,
        assessment_complete,
        preferences_set
    ])
    progress_percentage = min(100, (completed_steps / 4) * 100)
    
    # Determine if onboarding is complete
    onboarding_complete = all([
        profile_complete,
        documents_uploaded,
        assessment_complete,
        preferences_set
    ])
    
    return render_template(
        'candidate_onboarding.html',
        profile_complete=profile_complete,
        documents_uploaded=documents_uploaded,
        assessment_complete=assessment_complete,
        preferences_set=preferences_set,
        progress_percentage=progress_percentage,
        onboarding_complete=onboarding_complete,
        candidate_name=session.get('user_name', 'Candidate')
    )

@app.route('/candidate/settings', methods=['GET', 'POST'])
def candidate_settings():
    """Candidate account settings route"""
    if 'user_role' not in session or session['user_role'] != 'candidate':
        return redirect(url_for('login_candidate'))
    
    if request.method == 'POST':
        # Handle settings update logic here
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('candidate_settings'))
    
    # In a real app, these would come from the database
    settings = {
        'notifications': {
            'email': True,
            'sms': False,
            'push': True,
            'email_notifications': True
        },
        'privacy': {
            'profile_visibility': 'public',
            'search_engine_indexing': True,
            'resume_visibility': 'public'
        },
        'account': {
            'email': session.get('user_email', 'user@example.com'),
            'phone': '+1234567890',
            'timezone': 'UTC'
        }
    }
    
    return render_template('candidate_settings.html', settings=settings)

# Candidate Routes
def get_recent_activities(applications):
    """Generate recent activities from application status updates."""
    activities = []
    
    # Mock activities data if no applications are provided
    if not applications or (isinstance(applications, list) and not applications):
        now = datetime.now()
        
        mock_activities = [
            {
                'title': 'New Application',
                'description': 'John Doe applied for Senior Developer position',
                'status': 'New',
                'status_class': 'primary',
                'time_ago': '5 min ago',
                'user': 'System',
                'date': now - timedelta(minutes=5)
            },
            {
                'title': 'Interview Scheduled',
                'description': 'Interview scheduled with Sarah Williams for Data Scientist role',
                'status': 'Scheduled',
                'status_class': 'info',
                'time_ago': '1 hour ago',
                'user': 'Alex Johnson',
                'date': now - timedelta(hours=1)
            },
            {
                'title': 'Offer Extended',
                'description': 'Offer extended to Michael Chen for DevOps Engineer position',
                'status': 'Offer',
                'status_class': 'success',
                'time_ago': '3 hours ago',
                'user': 'HR Team',
                'date': now - timedelta(hours=3)
            },
            {
                'title': 'Document Uploaded',
                'description': 'Emily Davis uploaded signed offer letter',
                'status': 'Completed',
                'status_class': 'success',
                'time_ago': '1 day ago',
                'user': 'Emily Davis',
                'date': now - timedelta(days=1)
            },
            {
                'title': 'Interview Completed',
                'description': 'Technical interview completed with Robert Brown',
                'status': 'Review',
                'status_class': 'warning',
                'time_ago': '2 days ago',
                'user': 'Interview Panel',
                'date': now - timedelta(days=2)
            },
            {
                'title': 'Resume Shortlisted',
                'description': 'Resume shortlisted for Lisa Ray - Senior UX Designer',
                'status': 'In Review',
                'status_class': 'info',
                'time_ago': '45 min ago',
                'user': 'Design Team',
                'date': now - timedelta(minutes=45)
            },
            {
                'title': 'Assessment Sent',
                'description': 'Coding assessment sent to David Kim for Backend Developer role',
                'status': 'Pending',
                'status_class': 'warning',
                'time_ago': '2 hours ago',
                'user': 'Tech Team',
                'date': now - timedelta(hours=2)
            },
            {
                'title': 'Reference Check',
                'description': 'Reference check completed for Maria Garcia - Project Manager',
                'status': 'Completed',
                'status_class': 'success',
                'time_ago': '4 hours ago',
                'user': 'HR Team',
                'date': now - timedelta(hours=4)
            },
            {
                'title': 'Interview Rescheduled',
                'description': 'Interview with Alex Turner rescheduled to next Monday',
                'status': 'Updated',
                'status_class': 'info',
                'time_ago': '6 hours ago',
                'user': 'Recruitment Team',
                'date': now - timedelta(hours=6)
            },
            {
                'title': 'New Job Posting',
                'description': 'New job posted: Senior Data Engineer (Remote)',
                'status': 'Active',
                'status_class': 'primary',
                'time_ago': '1 day ago',
                'user': 'HR Team',
                'date': now - timedelta(days=1)
            }
        ]
        return mock_activities
    
    # Process real applications if available
    for app in applications:
        if isinstance(app, dict):
            # Handle dictionary format
            activities.append({
                'title': 'Application Received',
                'description': f'New application from {app.get("name", "Candidate")} for {app.get("position", "a position")}',
                'status': 'New',
                'status_class': 'primary',
                'time_ago': 'Recently',
                'user': app.get('name', 'System'),
                'date': app.get('applied_date', datetime.now())
            })
        else:
            # Handle SQLAlchemy model
            activities.append({
                'title': 'Application Received',
                'description': f'New application from {getattr(app, "name", "Candidate")} for {getattr(app, "position", "a position")}',
                'status': 'New',
                'status_class': 'primary',
                'time_ago': 'Recently',
                'user': getattr(app, 'name', 'System'),
                'date': getattr(app, 'applied_date', datetime.now())
            })
    
    # Sort activities by date in descending order and return only the 5 most recent
    activities.sort(key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.min, reverse=True)
    return activities[:5]

@app.route('/candidate/dashboard')
def candidate_dashboard():
    # Get candidate's activities and interviews from database
    candidate_name = session.get('user_name', 'Candidate User')
    # For now, just get the first candidate since we're using mock data
    # In a real app, you'd want to use the authenticated user's ID
    candidate = Candidate.query.first()
    
    # Mock applications data (matching the applications page)
    applications = [
        {
            'id': 1,
            'job_title': 'Senior Software Engineer',
            'company': 'TechNova Systems',
            'applied_date': '2023-11-15',
            'status': 'Interview Scheduled',
            'status_class': 'bg-info',
            'interview_scheduled': '2023-11-25 10:00:00',
            'meeting_link': 'https://meet.google.com/xyz-abc-123',
            'contact_person': 'Sarah Johnson',
            'contact_email': 'hiring@technova.com',
            'application_status': [
                {'date': '2023-11-15', 'status': 'Application Submitted', 'details': 'Your application has been received.'},
                {'date': '2023-11-17', 'status': 'Initial Screening', 'details': 'Your application passed the initial screening.'},
                {'date': '2023-11-20', 'status': 'Technical Assessment', 'details': 'Successfully completed the technical assessment.'},
                {'date': '2023-11-22', 'status': 'Interview Scheduled', 'details': 'Final interview scheduled for November 25, 2023 at 10:00 AM PST.'}
            ]
        },
        {
            'id': 2,
            'job_title': 'Frontend Developer',
            'company': 'WebCraft Solutions',
            'applied_date': '2023-11-10',
            'status': 'Interview Scheduled',
            'status_class': 'bg-info',
            'interview_scheduled': '2023-11-22 14:00:00',
            'meeting_link': 'https://meet.google.com/abc-xyz-123',
            'contact_person': 'Michael Chen',
            'contact_email': 'michael.chen@webcraft.com',
            'application_status': [
                {'date': '2023-11-10', 'status': 'Application Submitted', 'details': 'Your application has been received.'},
                {'date': '2023-11-12', 'status': 'Initial Screening', 'details': 'Your application passed the initial screening.'},
                {'date': '2023-11-18', 'status': 'Technical Interview', 'details': 'Successfully completed the technical interview.'},
                {'date': '2023-11-22', 'status': 'Final Interview Scheduled', 'details': 'Final interview scheduled for November 22, 2023 at 2:00 PM EST.'}
            ]
        },
        {
            'id': 4,
            'job_title': 'Senior DevOps Engineer',
            'company': 'CloudScale Technologies',
            'applied_date': '2023-10-28',
            'status': 'Offer Extended',
            'status_class': 'bg-success',
            'interview_scheduled': None,
            'offer_details': {
                'position': 'Senior DevOps Engineer',
                'start_date': '2023-12-01',
                'salary': '$165,000 per year',
                'bonus': '15% annual target bonus'
            },
            'contact_person': 'Emily Rodriguez',
            'contact_email': 'emily.rodriguez@cloudscale.tech',
            'application_status': [
                {'date': '2023-10-28', 'status': 'Application Submitted', 'details': 'Your application has been received.'},
                {'date': '2023-10-30', 'status': 'Technical Screening', 'details': 'Successfully completed the technical screening.'},
                {'date': '2023-11-05', 'status': 'Technical Interview', 'details': 'Completed the technical interview.'},
                {'date': '2023-11-10', 'status': 'Final Interview', 'details': 'Completed the final interview with the engineering leadership.'},
                {'date': '2023-11-15', 'status': 'Offer Extended', 'details': 'Congratulations! We are excited to extend an offer.'}
            ]
        }
    ]
    
    # Get activities from application status updates
    activities = get_recent_activities(applications)
    
    # If no candidate record exists yet, use mock data (already handled in get_recent_activities)
    
    # Get upcoming interviews from applications
    upcoming_interviews = []
    for app in applications:
        if app.get('interview_scheduled') and app['status'] == 'Interview Scheduled':
            interview_time = datetime.strptime(app['interview_scheduled'], '%Y-%m-%d %H:%M:%S')
            upcoming_interviews.append({
                'id': app['id'],
                'date': interview_time.strftime('%b %d, %Y %I:%M %p'),
                'position': app['job_title'],
                'company': app['company'],
                'interviewer': app['contact_person'],
                'type': 'Technical' if 'Software' in app['job_title'] else 'HR',
                'status': 'Scheduled',
                'meeting_link': app.get('meeting_link')
            })
    
    # Get current datetime for the template
    current_time = datetime.now()
    
    return render_template('candidate_dashboard.html',
                         activities=activities,
                         upcoming_interviews=upcoming_interviews,
                         now=current_time)

@app.route('/candidate/resume/submit', methods=['POST'])
def submit_resume():
    # Check if using mock data
    if request.form.get('use_mock_data') == 'true':
        # Get mock data from session
        mock_data = {
            'personal_info': {
                'name': 'Alex Johnson',
                'email': 'alex.johnson@example.com',
                'phone': '(555) 123-4567',
                'location': 'San Francisco, CA',
                'title': 'Senior Software Engineer'
            },
            'experience': [
                {
                    'title': 'Senior Software Engineer',
                    'company': 'Tech Innovations Inc.',
                    'duration': '2020 - Present',
                    'description': 'Led a team of 5 developers in building scalable web applications using React and Node.js.'
                },
                {
                    'title': 'Software Developer',
                    'company': 'Digital Solutions LLC',
                    'duration': '2018 - 2020',
                    'description': 'Developed and maintained RESTful APIs and implemented new features for the core product.'
                }
            ],
            'education': [
                {
                    'degree': 'M.S. in Computer Science',
                    'institution': 'Stanford University',
                    'year': '2016 - 2018'
                },
                {
                    'degree': 'B.Tech in Information Technology',
                    'institution': 'University of California, Berkeley',
                    'year': '2012 - 2016'
                }
            ],
            'skills': ['JavaScript', 'React', 'Node.js', 'Python', 'AWS', 'Docker', 'Kubernetes', 'CI/CD'],
            'projects': [
                {
                    'name': 'E-commerce Platform',
                    'description': 'Built a full-stack e-commerce platform with React, Node.js, and MongoDB.'
                }
            ]
        }
        
        # Process the mock data
        resume_info = process_resume_data(mock_data, 'sample_resume.pdf')
    else:
        # Handle file upload
        if 'resume' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('candidate_resume_upload'))
        
        file = request.files['resume']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('candidate_resume_upload'))
        
        if file and allowed_file(file.filename):
            # Save the file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the resume (in a real app, you'd use a resume parser here)
            resume_info = process_resume_data({
                'filename': filename,
                'content_type': file.content_type,
                'size': os.path.getsize(filepath)
            }, filename)
        else:
            flash('Invalid file type. Please upload a PDF, DOC, or DOCX file.', 'error')
            return redirect(url_for('candidate_resume_upload'))
    
    # Save resume data to session for display on the submitted page
    session['resume_data'] = resume_info
    
    # Create a new interview record
    try:
        candidate_name = session.get('username', 'Candidate')
        
        # Create or get candidate
        candidate = Candidate.query.filter_by(name=candidate_name).first()
        if not candidate:
            candidate = Candidate(
                name=candidate_name,
                resume_text=str(resume_info.get('parsed_data', '')),
                job_desc=request.form.get('position', 'Software Developer')
            )
            db.session.add(candidate)
            db.session.commit()
        
        # Create interview appointment
        interview_date = datetime.utcnow() + timedelta(days=2)  # Schedule interview 2 days from now
        
        appointment = Appointment(
            candidate_id=candidate.id,
            title=f"Interview for {request.form.get('position', 'Software Developer')}",
            description=f"Technical interview based on the submitted resume for {candidate_name}",
            start_time=interview_date,
            end_time=interview_date + timedelta(hours=1),
            status='scheduled'
        )
        db.session.add(appointment)
        db.session.commit()
        
        # Send confirmation email
        try:
            send_resume_submission_confirmation(
                recipient_email=f"{candidate_name.lower().replace(' ', '.')}@example.com",
                candidate_name=candidate_name
            )
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
        
        return redirect(url_for('candidate_resume_upload'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing resume submission: {e}")
        flash('An error occurred while processing your resume. Please try again.', 'error')
        return redirect(url_for('candidate_resume_upload'))

@app.route('/onboarding')
def onboarding():
    # Sample candidates data for the onboarding page
    sample_candidates = [
        {
            'name': 'John Smith',
            'job_desc': 'Senior Software Engineer',
            'resume_text': 'Experienced software engineer with 5+ years of experience...'
        },
        {
            'name': 'Sarah Johnson',
            'job_desc': 'UX/UI Designer',
            'resume_text': 'Creative designer with expertise in user experience...'
        },
        {
            'name': 'Michael Chen',
            'job_desc': 'Data Scientist',
            'resume_text': 'Data science professional with strong analytical skills...'
        }
    ]
    return render_template('onboarding.html', sample_candidates=sample_candidates)

@app.route('/hr/interviews')
def hr_interviews():
    """HR Interviews management"""
    # For demo purposes, we'll use mock data
    mock_interviews = get_mock_interview_data()
    
    # Group interviews by status
    now = datetime.utcnow()
    upcoming = [i for i in mock_interviews if i['status'] == 'Scheduled' and datetime.strptime(i['scheduled_time'], '%Y-%m-%dT%H:%M') >= now]
    completed = [i for i in mock_interviews if i['status'] == 'Completed']
    cancelled = [i for i in mock_interviews if i['status'] == 'Cancelled']
    
    # Mock candidates for the dropdown
    candidates = [
        {'id': 1, 'name': 'John Doe', 'email': 'john.doe@example.com'},
        {'id': 2, 'name': 'Jane Smith', 'email': 'jane.smith@example.com'},
        {'id': 3, 'name': 'Robert Johnson', 'email': 'robert.j@example.com'}
    ]
    
    # Mock users for the interviewer dropdown
    users = [
        {'id': 1, 'name': 'Sarah Johnson', 'role': 'HR Manager'},
        {'id': 2, 'name': 'Michael Chen', 'role': 'Technical Lead'},
        {'id': 3, 'name': 'David Wilson', 'role': 'Hiring Manager'}
    ]
    
    return render_template('interviews.html', 
                         upcoming=upcoming,
                         completed=completed,
                         cancelled=cancelled,
                         candidates=candidates,
                         users=users,
                         mock_interviews=mock_interviews)

@app.route('/interview/<int:interview_id>')
def view_interview(interview_id):
    """View interview details"""
    # Get the interview from mock data
    interviews = get_mock_interview_data()
    interview = next((i for i in interviews if i['id'] == interview_id), None)
    
    if not interview:
        flash('Interview not found', 'danger')
        return redirect(url_for('hr_interviews'))
    
    # Get related data
    candidates = [
        {'id': 1, 'name': 'John Doe', 'email': 'john.doe@example.com'},
        {'id': 2, 'name': 'Jane Smith', 'email': 'jane.smith@example.com'},
        {'id': 3, 'name': 'Robert Johnson', 'email': 'robert.j@example.com'}
    ]
    
    users = [
        {'id': 1, 'name': 'Sarah Johnson', 'role': 'HR Manager'},
        {'id': 2, 'name': 'Michael Chen', 'role': 'Technical Lead'},
        {'id': 3, 'name': 'David Wilson', 'role': 'Hiring Manager'}
    ]
    
    return render_template('view_interview.html', 
                         interview=interview,
                         candidates=candidates,
                         users=users)

@app.route('/candidate/interview')
def candidate_interview():
    # For candidates, show the interview screen
    return render_template('candidate_interviews.html')

from ai_interview import AIInterviewer
from interview_questions import InterviewQuestionBank, InterviewQuestion
from functools import wraps
import json
from datetime import datetime

# Initialize the question bank
question_bank = InterviewQuestionBank()

def candidate_required(f):
    """Decorator to ensure the user is logged in as a candidate."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'candidate':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to ensure the user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Helper function to convert InterviewQuestion to dict
def question_to_dict(question: InterviewQuestion) -> dict:
    return {
        'id': question.id,
        'category': question.category,
        'question': question.question,
        'difficulty': question.difficulty,
        'tags': question.tags,
        'tips': question.tips,
        'sample_answers': question.sample_answers,
        'created_at': question.created_at,
        'updated_at': question.updated_at
    }

# API Endpoints for Interview Questions

@app.route('/api/interview-questions', methods=['GET'])
@candidate_required
def get_questions():
    """Get all questions with optional filtering."""
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    tag = request.args.get('tag')
    search = request.args.get('search')
    
    questions = []
    
    if category:
        questions = question_bank.get_questions_by_category(category)
    elif difficulty:
        questions = question_bank.get_questions_by_difficulty(difficulty)
    elif tag:
        questions = question_bank.get_questions_by_tag(tag)
    elif search:
        questions = question_bank.search_questions(search)
    else:
        questions = list(question_bank.questions.values())
    
    return jsonify({
        'success': True,
        'count': len(questions),
        'questions': [question_to_dict(q) for q in questions]
    })

@app.route('/api/interview-questions/categories', methods=['GET'])
@candidate_required
def get_question_categories():
    """Get all unique categories."""
    return jsonify({
        'success': True,
        'categories': question_bank.get_all_categories()
    })

@app.route('/api/interview-questions/tags', methods=['GET'])
@candidate_required
def get_question_tags():
    """Get all unique tags."""
    return jsonify({
        'success': True,
        'tags': question_bank.get_all_tags()
    })

@app.route('/api/interview-questions/random', methods=['GET'])
@candidate_required
def get_random_question():
    """Get a random question, optionally filtered by category and/or difficulty."""
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    
    question = question_bank.get_random_question(category, difficulty)
    
    if not question:
        return jsonify({
            'success': False,
            'error': 'No questions found matching the criteria'
        }), 404
    
    return jsonify({
        'success': True,
        'question': question_to_dict(question)
    })

@app.route('/api/interview-questions', methods=['POST'])
@admin_required
def create_question():
    """Create a new interview question (admin only)."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['question', 'category']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create the question
        question = question_bank.add_question(data)
        
        return jsonify({
            'success': True,
            'message': 'Question created successfully',
            'question': question_to_dict(question)
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'An error occurred while creating the question'
        }), 500

@app.route('/api/interview-questions/<question_id>', methods=['GET'])
@candidate_required
def get_question(question_id):
    """Get a specific question by ID."""
    question = question_bank.get_question(question_id)
    
    if not question:
        return jsonify({
            'success': False,
            'error': 'Question not found'
        }), 404
    
    return jsonify({
        'success': True,
        'question': question_to_dict(question)
    })

@app.route('/api/interview-questions/<question_id>', methods=['PUT'])
@admin_required
def update_question(question_id):
    """Update an existing question (admin only)."""
    question = question_bank.get_question(question_id)
    
    if not question:
        return jsonify({
            'success': False,
            'error': 'Question not found'
        }), 404
    
    try:
        data = request.get_json()
        
        # Don't allow updating the question text (would change the ID)
        if 'question' in data:
            del data['question']
        
        updated_question = question_bank.update_question(question_id, data)
        
        if not updated_question:
            return jsonify({
                'success': False,
                'error': 'Failed to update question'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Question updated successfully',
            'question': question_to_dict(updated_question)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'An error occurred while updating the question'
        }), 500

@app.route('/api/interview-questions/<question_id>', methods=['DELETE'])
@admin_required
def delete_question(question_id):
    """Delete a question (admin only)."""
    if not question_bank.get_question(question_id):
        return jsonify({
            'success': False,
            'error': 'Question not found'
        }), 404
    
    success = question_bank.delete_question(question_id)
    
    if not success:
        return jsonify({
            'success': False,
            'error': 'Failed to delete question'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'Question deleted successfully'
    })

# AI interview practice route
@app.route('/ai-interview-practice', methods=['GET', 'POST'])
@candidate_required
def ai_interview_practice():
    """AI-powered interview practice page and API endpoint"""
    # Initialize or retrieve the AI interviewer from the session
    if 'ai_interviewer' not in session:
        session['ai_interviewer'] = AIInterviewer().__dict__
    
    # Handle POST requests (user answers)
    if request.method == 'POST':
        data = request.get_json()
        action = data.get('action')
        
        # Load the current state
        interviewer = AIInterviewer()
        interviewer.__dict__.update(session['ai_interviewer'])
        
        if action == 'get_question':
            # Get the next question
            response = interviewer.get_next_question()
        elif action == 'submit_answer':
            # Process the user's answer
            question = data.get('question', '')
            answer = data.get('answer', '')
            response = interviewer.process_answer(answer, question)
        elif action == 'end_interview':
            # End the interview and get final feedback
            response = interviewer._generate_final_feedback()
            # Clear the interview from session when done
            session.pop('ai_interviewer', None)
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        # Save the updated state
        session['ai_interviewer'] = interviewer.__dict__
        session.modified = True
        
        return jsonify(response)
    
    # For GET requests, just render the template
    return render_template('ai_interview_practice.html')

@app.route('/api/interview/notify-me/<int:interview_id>', methods=['POST'])
def notify_me(interview_id):
    """Handle the 'Notify Me' button click for interviews."""
    try:
        # In a real application, you would:
        # 1. Get the current user's email from the session
        # 2. Get the interview details from the database
        # 3. Schedule a reminder email 24 hours before the interview
        
        # For demo purposes, we'll just log the request and return success
        print(f"Notification requested for interview ID: {interview_id}")
        
        return jsonify({
            'success': True,
            'message': 'Notification scheduled successfully',
            'interview_id': interview_id
        }), 200
    except Exception as e:
        print(f"Error scheduling notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to schedule notification',
            'error': str(e)
        }), 500

@app.route('/interview-complete')
def interview_complete():
    try:
        # Get candidate information
        candidate_name = session.get('username', 'Candidate')
        candidate = Candidate.query.filter_by(name=candidate_name).first()
        
        if not candidate:
            flash('Candidate information not found.', 'error')
            return redirect(url_for('candidate_dashboard'))
            
        # Get the most recent application
        application = Appointment.query.filter_by(
            candidate_id=candidate.id
        ).order_by(Appointment.created_at.desc()).first()
        
        position = application.title if application else 'the position'
        
        # Send immediate follow-up email
        next_steps = ("Our hiring team is currently reviewing your interview responses. "
                     "You'll receive an update from us within 3-5 business days. "
                     "A member of our HR team will reach out to you with the next steps.")
        
        send_interview_followup(
            recipient_email=candidate.email or current_app.config['MAIL_DEFAULT_SENDER'],
            candidate_name=candidate_name,
            next_steps=next_steps
        )
        
        # Schedule the formal update email to be sent in 2 days
        position = application.title if application else 'the position'
        send_post_interview_update.delay(
            recipient_email=candidate.email or current_app.config['MAIL_DEFAULT_SENDER'],
            candidate_name=candidate_name,
            position=position
        )
        
        # Log the interview completion
        current_app.logger.info(f"Interview completed by candidate: {candidate_name}")
        
        # Render the completion page with context
        return render_template('candidate/interview_complete.html', 
                             candidate_name=candidate_name,
                             position=position)
            
    except Exception as e:
        current_app.logger.error(f"Error in interview completion: {str(e)}")
        flash('Thank you for completing the interview! An error occurred while processing your submission.', 'warning')
        return redirect(url_for('candidate_dashboard'))

@app.route('/candidate/applications')
def candidate_applications():
    # Mock data for applications with realistic statuses and details
    applications = [
        {
            'id': 1,
            'job_title': 'Senior Software Engineer',
            'company': 'TechNova Systems',
            'applied_date': '2023-11-15',
            'status': 'Interview Scheduled',
            'status_class': 'bg-info',
            'location': 'San Francisco, CA (Hybrid)',
            'job_type': 'Full-time',
            'salary_range': '$140,000 - $170,000',
            'job_description': 'We are looking for a Senior Software Engineer to join our growing engineering team. You will be responsible for designing, developing, and maintaining high-performance applications while mentoring junior developers.',
            'requirements': [
                '5+ years of professional software development experience',
                'Expertise in Python, Django, and React',
                'Experience with cloud infrastructure (AWS/GCP)',
                'Strong database design and optimization skills',
                'Experience with CI/CD pipelines'
            ],
            'application_status': [
                {'date': '2023-11-15', 'status': 'Application Submitted', 'details': 'Your application has been received.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-17', 'status': 'Initial Screening', 'details': 'Your application passed the initial screening.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-20', 'status': 'Technical Assessment', 'details': 'Successfully completed the technical assessment.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-22', 'status': 'Interview Scheduled', 'details': 'Final interview scheduled for November 25, 2023 at 10:00 AM PST.', 'icon': 'bi-calendar-check', 'current': True}
            ],
            'next_steps': [
                'Prepare for the final interview',
                'Review the company culture and values',
                'Prepare questions about the team'
            ],
            'contact_person': 'Sarah Johnson',
            'contact_email': 'hiring@technova.com',
            'interview_scheduled': '2023-11-25 10:00:00',
            'meeting_link': 'https://meet.google.com/xyz-abc-123',
            'attachments': ['resume.pdf', 'cover_letter.pdf']
        },
        {
            'id': 2,
            'job_title': 'Frontend Developer',
            'company': 'WebCraft Solutions',
            'applied_date': '2023-11-10',
            'status': 'Interview Scheduled',
            'status_class': 'bg-info',
            'location': 'Remote (US Timezones)',
            'job_type': 'Full-time',
            'salary_range': '$110,000 - $140,000',
            'job_description': 'Join our team to build beautiful, responsive web applications using modern JavaScript frameworks. You will work closely with designers and backend developers to implement pixel-perfect UIs.',
            'requirements': [
                '3+ years of frontend development experience',
                'Proficiency in React.js and TypeScript',
                'Experience with state management (Redux/Context API)',
                'Strong CSS/SASS skills',
                'Experience with testing frameworks (Jest, React Testing Library)'
            ],
            'application_status': [
                {'date': '2023-11-10', 'status': 'Application Submitted', 'details': 'Your application has been received.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-12', 'status': 'Initial Screening', 'details': 'Your application passed the initial screening.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-18', 'status': 'Technical Interview', 'details': 'Successfully completed the technical interview.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-22', 'status': 'Final Interview Scheduled', 'details': 'Final interview scheduled for November 22, 2023 at 2:00 PM EST.', 'icon': 'bi-calendar-check', 'current': True}
            ],
            'next_steps': [
                'Prepare for the final interview',
                'Review the company products',
                'Prepare questions about the team'
            ],
            'contact_person': 'Michael Chen',
            'contact_email': 'michael.chen@webcraft.com',
            'interview_scheduled': '2023-11-22 14:00:00',
            'meeting_link': 'https://meet.google.com/abc-xyz-123',
            'attachments': ['resume.pdf', 'portfolio.pdf']
        },
        {
            'id': 3,
            'job_title': 'Full Stack Developer',
            'company': 'Digital Innovations',
            'applied_date': '2023-11-05',
            'status': 'Rejected',
            'status_class': 'bg-danger',
            'location': 'New York, NY (On-site)',
            'job_type': 'Contract (6 months)',
            'salary_range': '$70 - $90 per hour',
            'job_description': 'We are looking for a Full Stack Developer to work on client projects, building scalable web applications from the ground up. You will be involved in all aspects of the development lifecycle.',
            'requirements': [
                'Proven experience with MERN/MEAN stack',
                'Experience with TypeScript',
                'Knowledge of containerization (Docker)',
                'Familiarity with microservices architecture',
                'Strong problem-solving skills'
            ],
            'application_status': [
                {'date': '2023-11-05', 'status': 'Application Submitted', 'details': 'Your application has been received and is pending review.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-10', 'status': 'Initial Review', 'details': 'Your application is being reviewed by our hiring team.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-18', 'status': 'Rejected', 'details': 'We have decided to move forward with other candidates whose experience more closely aligns with our current needs.', 'icon': 'bi-x-circle', 'current': True, 'is_rejection': True}
            ],
            'rejection_reason': 'The position required more experience with microservices architecture than demonstrated in your application.',
            'feedback': 'While your full-stack experience is impressive, we were looking for someone with more hands-on experience with microservices architecture and container orchestration.',
            'next_steps': [
                'Consider gaining more experience with microservices',
                'Look for positions that better match your current skill set',
                'Feel free to apply again in the future as new positions open up'
            ],
            'contact_person': 'Recruitment Team',
            'contact_email': 'careers@digitalinnovations.com',
            'interview_scheduled': None,
            'attachments': ['resume.pdf']
        },
        {
            'id': 4,
            'job_title': 'Senior DevOps Engineer',
            'company': 'CloudScale Technologies',
            'applied_date': '2023-10-28',
            'status': 'Offer Extended',
            'status_class': 'bg-success',
            'location': 'Austin, TX (Remote OK)',
            'job_type': 'Full-time',
            'salary_range': '$150,000 - $180,000',
            'job_description': 'Lead our DevOps initiatives to build and maintain our cloud infrastructure, CI/CD pipelines, and deployment automation. Help us scale our systems and improve developer productivity.',
            'requirements': [
                '5+ years of DevOps/SRE experience',
                'Expertise in AWS/GCP and infrastructure as code',
                'Experience with Kubernetes and Docker',
                'Strong scripting skills (Python/Bash)',
                'Knowledge of security best practices'
            ],
            'application_status': [
                {'date': '2023-10-28', 'status': 'Application Submitted', 'details': 'Your application has been received.', 'icon': 'bi-check-circle'},
                {'date': '2023-10-30', 'status': 'Technical Screening', 'details': 'Successfully completed the technical screening.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-05', 'status': 'Technical Interview', 'details': 'Completed the technical interview.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-10', 'status': 'Final Interview', 'details': 'Completed the final interview with the engineering leadership.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-15', 'status': 'Offer Extended', 'details': 'Congratulations! We are excited to extend an offer.', 'icon': 'bi-award', 'current': True}
            ],
            'next_steps': [
                'Review the offer details',
                'Submit any questions to the hiring manager',
                'Complete the background check process',
                'Prepare for your start date'
            ],
            'contact_person': 'Emily Rodriguez',
            'contact_email': 'emily.rodriguez@cloudscale.tech',
            'interview_scheduled': None,
            'offer_details': {
                'position': 'Senior DevOps Engineer',
                'start_date': '2023-12-01',
                'salary': '$165,000 per year',
                'bonus': '15% annual target bonus',
                'equity': '10,000 RSUs vesting over 4 years',
                'benefits': 'Health, dental, vision, 401(k) matching'
            },
            'attachments': ['offer_letter.pdf', 'benefits_guide.pdf']
        },
        {
            'id': 5,
            'job_title': 'Machine Learning Engineer',
            'company': 'AI Innovations Inc.',
            'applied_date': '2023-11-01',
            'status': 'Rejected',
            'status_class': 'bg-danger',
            'location': 'Boston, MA (Hybrid)',
            'job_type': 'Full-time',
            'salary_range': '$130,000 - $160,000',
            'job_description': 'Join our AI research team to develop and deploy machine learning models that solve complex business problems. Work with large datasets and cutting-edge ML algorithms.',
            'requirements': [
                'Advanced degree in Computer Science or related field',
                '3+ years of experience with machine learning frameworks',
                'Strong programming skills in Python',
                'Experience with deep learning frameworks (TensorFlow/PyTorch)',
                'Knowledge of MLOps practices'
            ],
            'application_status': [
                {'date': '2023-11-01', 'status': 'Application Submitted', 'details': 'Your application has been received.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-05', 'status': 'Initial Screening', 'details': 'Your application passed the initial screening.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-12', 'status': 'Technical Assessment', 'details': 'Completed the technical assessment.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-15', 'status': 'Technical Interview', 'details': 'Completed the technical interview.', 'icon': 'bi-check-circle'},
                {'date': '2023-11-20', 'status': 'Rejected', 'details': 'We appreciate your time and effort, but we have decided to move forward with other candidates.', 'icon': 'bi-x-circle', 'current': True, 'is_rejection': True}
            ],
            'rejection_reason': 'The position required more experience with production ML model deployment than demonstrated in your application.',
            'feedback': 'Your machine learning knowledge is strong, but we were looking for someone with more experience in deploying models to production at scale. We encourage you to gain more experience with MLOps and production deployment pipelines.',
            'next_steps': [
                'Gain experience with model deployment and MLOps',
                'Work on end-to-end ML projects',
                'Consider applying for more junior ML positions to build experience'
            ],
            'contact_person': 'AI Recruitment Team',
            'contact_email': 'talent@ai-innovations.com',
            'interview_scheduled': None,
            'attachments': ['resume.pdf', 'ml_portfolio.pdf']
        }
    ]
    from datetime import datetime
    return render_template('candidate_applications.html', 
                         applications=applications,
                         now=datetime.utcnow())

@app.route('/candidate/application/<int:app_id>')
def view_application(app_id):
    # In a real application, this would fetch the application from the database
    # For now, we'll use the same mock data and find the matching application
    applications = [
        {
            'id': 1,
            'job_title': 'Senior Software Engineer',
            'company': 'Tech Corp Inc.',
            'applied_date': '2023-11-10',
            'status': 'In Review',
            'location': 'San Francisco, CA',
            'job_type': 'Full-time',
            'salary_range': '$120,000 - $150,000',
            'job_description': 'We are looking for an experienced Senior Software Engineer to join our team. The ideal candidate will have 5+ years of experience in software development and a strong background in Python and JavaScript.',
            'requirements': [
                '5+ years of software development experience',
                'Proficiency in Python, JavaScript, and related frameworks',
                'Experience with cloud platforms (AWS/GCP/Azure)',
                'Strong problem-solving skills',
                'Excellent communication skills'
            ],
            'application_status': [
                {'date': '2023-11-10', 'status': 'Application Submitted', 'details': 'Your application has been received and is under review.'},
                {'date': '2023-11-12', 'status': 'In Review', 'details': 'Your application is being reviewed by our hiring team.'}
            ],
            'contact_person': 'Sarah Johnson',
            'contact_email': 'sarah.johnson@techcorp.com',
            'interview_scheduled': None,
            'attachments': ['resume.pdf', 'cover_letter.pdf']
        },
        {
            'id': 2,
            'job_title': 'Frontend Developer',
            'company': 'Web Solutions Ltd.',
            'applied_date': '2023-11-05',
            'status': 'Interview Scheduled',
            'location': 'Remote',
            'job_type': 'Full-time',
            'salary_range': '$90,000 - $120,000',
            'job_description': 'Join our team as a Frontend Developer and help us build amazing user experiences. We use modern JavaScript frameworks and tools to create responsive and accessible web applications.',
            'requirements': [
                '3+ years of frontend development experience',
                'Proficiency in React.js, Vue.js, or Angular',
                'Strong CSS and responsive design skills',
                'Experience with state management',
                'Understanding of web performance optimization'
            ],
            'application_status': [
                {'date': '2023-11-05', 'status': 'Application Submitted', 'details': 'Your application has been received.'},
                {'date': '2023-11-08', 'status': 'In Review', 'details': 'Your application is being reviewed.'},
                {'date': '2023-11-15', 'status': 'Interview Scheduled', 'details': 'Technical interview scheduled for November 20, 2023 at 2:00 PM EST.'}
            ],
            'contact_person': 'Michael Chen',
            'contact_email': 'michael.chen@websolutions.com',
            'interview_scheduled': '2023-11-20 14:00:00',
            'meeting_link': 'https://meet.google.com/abc-xyz-123',
            'attachments': ['resume.pdf', 'portfolio.pdf']
        },
        {
            'id': 3,
            'job_title': 'Full Stack Developer',
            'company': 'Digital Innovations',
            'applied_date': '2023-11-18',
            'status': 'Application Submitted',
            'location': 'New York, NY',
            'job_type': 'Contract',
            'salary_range': '$80 - $100 per hour',
            'job_description': 'We are seeking a skilled Full Stack Developer to work on exciting projects for our clients. You will be responsible for developing and maintaining web applications from concept to deployment.',
            'requirements': [
                'Proven experience as a Full Stack Developer',
                'Knowledge of multiple front-end languages and libraries (e.g., HTML/ CSS, JavaScript, XML, jQuery)',
                'Knowledge of multiple back-end languages (e.g., Python, Java) and JavaScript frameworks (e.g., Angular, React, Node.js)',
                'Familiarity with databases (e.g., MySQL, MongoDB), web servers (e.g., Apache)',
                'Excellent communication and teamwork skills'
            ],
            'application_status': [
                {'date': '2023-11-18', 'status': 'Application Submitted', 'details': 'Your application has been received and is pending review.'}
            ],
            'contact_person': 'David Wilson',
            'contact_email': 'david.wilson@digitalinnovations.com',
            'interview_scheduled': None,
            'attachments': ['resume.pdf']
        }
    ]
    
    # Find the application with the matching ID
    application = next((app for app in applications if app['id'] == app_id), None)
    
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('candidate_applications'))
    
    return render_template('candidate/application_detail.html', application=application)

@app.route('/candidate/resume/upload')
def candidate_resume_upload():
    #def candidate_resume_upload():
    return render_template('candidate_resume_upload.html')

@app.route('/contact-support', methods=['GET', 'POST'])
def contact_support():
    if request.method == 'POST':
        # Handle form submission
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        subject = request.form.get('subject', '')
        message = request.form.get('message', '')
        
        # In a real app, you would process the support request here
        # For example, send an email or save to a database
        
        flash('Your support request has been submitted. We\'ll get back to you soon!', 'success')
        return redirect(url_for('candidate_dashboard'))
    
    # For GET request, show the contact form
    return render_template('contact_support.html')

@app.route('/candidate/resume/review')
def resume_review():
    # Get resume data from session
    resume_data = session.get('resume_data', {})
    
    # If no resume data in session, redirect to upload page
    if not resume_data:
        return redirect(url_for('candidate_resume_upload'))
    
    # Process the resume data to get analysis results
    filename = resume_data.get('filename', 'resume.pdf')
    analysis_results = process_resume_data(resume_data, filename)
    
    return render_template('candidate/resume_review.html', 
                         resume_data=resume_data,
                         analysis_results=analysis_results)

def get_mock_interview_data(interview_id=None):
    """Generate mock interview data for testing"""
    mock_interviews = [
        {
            'id': 1,
            'candidate_name': 'John Doe',
            'candidate_email': 'john.doe@example.com',
            'candidate_phone': '+1 (555) 123-4567',
            'position': 'Senior Software Engineer',
            'interview_type': 'Technical',
            'scheduled_time': (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
            'duration': 60,
            'interviewer': 'Sarah Johnson',
            'status': 'Scheduled',
            'meeting_link': 'https://meet.google.com/abc-xyz-123',
            'feedback': {
                'overall_score': 8,
                'technical_skills': 9,
                'communication': 8,
                'problem_solving': 8,
                'notes': 'Strong candidate with excellent technical skills.'
            },
            'notes': 'Focus on system design and algorithms',
            'resume': 'john_doe_resume.pdf'
        },
        {
            'id': 2,
            'candidate_name': 'Jane Smith',
            'candidate_email': 'jane.smith@example.com',
            'candidate_phone': '+1 (555) 234-5678',
            'position': 'Frontend Developer',
            'interview_type': 'Technical',
            'scheduled_time': (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'feedback': {
                'overall_score': 7,
                'technical_skills': 8,
                'communication': 7,
                'problem_solving': 7,
                'notes': 'Good understanding of frontend technologies.'
            },
            'duration': 45,
            'interviewer': 'Michael Chen',
            'status': 'Scheduled',
            'meeting_link': 'https://meet.google.com/def-456-uvw',
            'notes': 'Focus on React and JavaScript',
            'resume': 'jane_smith_resume.pdf'
        },
        {
            'id': 3,
            'candidate_name': 'Robert Johnson',
            'candidate_email': 'robert.j@example.com',
            'candidate_phone': '+1 (555) 345-6789',
            'position': 'Product Manager',
            'interview_type': 'Behavioral',
            'scheduled_time': (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'feedback': {
                'overall_score': 9,
                'technical_skills': 8,
                'communication': 9,
                'problem_solving': 9,
                'notes': 'Excellent product sense and leadership skills.'
            },
            'duration': 60,
            'interviewer': 'David Wilson',
            'status': 'Completed',
            'meeting_link': 'https://meet.google.com/ghi-789-xyz',
            'notes': 'Focus on product management and leadership skills',
            'resume': 'robert_johnson_resume.pdf'
        }
    ]
    
    if interview_id:
        return next((i for i in mock_interviews if i['id'] == interview_id), None)
    return mock_interviews

@app.route('/api/interviews/mock', methods=['GET'])
def get_mock_interviews():
    """API endpoint to get mock interview data"""
    return jsonify(get_mock_interview_data())

@app.route('/api/interviews/mock/<int:interview_id>', methods=['GET'])
def get_mock_interview(interview_id):
    """API endpoint to get a single mock interview by ID"""
    interview = get_mock_interview_data(interview_id)
    if not interview:
        return jsonify({'error': 'Interview not found'}), 404
    return jsonify(interview)

@app.route('/reschedule-interview/<int:interview_id>', methods=['POST'])
def reschedule_interview(interview_id):
    """Handle interview rescheduling"""
    if request.method == 'POST':
        try:
            # Get form data
            new_date_str = request.form.get('new_date')
            reason = request.form.get('reason', 'No reason provided')
            
            # Convert string to datetime
            new_date = datetime.strptime(new_date_str, '%Y-%m-%dT%H:%M')
            
            # In a real application, you would update the interview in the database here
            # For now, we'll just flash a success message
            flash(f'Interview #{interview_id} has been rescheduled to {new_date.strftime("%B %d, %Y at %I:%M %p")}', 'success')
            
            return redirect(url_for('hr_interviews'))
            
        except Exception as e:
            flash(f'Error rescheduling interview: {str(e)}', 'danger')
            return redirect(url_for('hr_interviews'))

@app.route('/cancel-interview/<int:interview_id>', methods=['POST'])
def cancel_interview(interview_id):
    """Handle interview cancellation"""
    if request.method == 'POST':
        try:
            # Get form data
            reason = request.form.get('reason', 'No reason provided')
            notify_candidate = request.form.get('notify_candidate') == 'on'
            
            # In a real application, you would update the interview status in the database here
            # and send a notification email if notify_candidate is True
            
            flash(f'Interview #{interview_id} has been cancelled. ' + 
                 ('Candidate has been notified.' if notify_candidate else ''), 'warning')
            
            return redirect(url_for('hr_interviews'))
            
        except Exception as e:
            flash(f'Error cancelling interview: {str(e)}', 'danger')
            return redirect(url_for('hr_interviews'))

@app.route('/schedule-interview', methods=['GET', 'POST'])
def schedule_interview():
    """Handle interview scheduling"""
    if request.method == 'POST':
        try:
            # Get form data
            candidate_id = request.form.get('candidate_id')
            interview_type = request.form.get('interview_type')
            interview_date = request.form.get('interview_date')
            duration = request.form.get('duration', 30)
            interviewer_id = request.form.get('interviewer_id')
            meeting_link = request.form.get('meeting_link')
            notes = request.form.get('notes')
            
            # For demo purposes, just show a success message with the form data
            if all([candidate_id, interview_type, interview_date]):
                flash(f'Interview scheduled successfully for candidate ID {candidate_id}!', 'success')
            else:
                flash('Please fill in all required fields', 'error')
            
            return redirect(url_for('hr_interviews'))
            
        except Exception as e:
            app.logger.error(f'Error in schedule_interview: {str(e)}')
            flash('An error occurred while scheduling the interview', 'error')
            return redirect(url_for('hr_interviews'))
    
    # GET request - show the schedule form with mock data
    mock_candidates = [
        {'id': 1, 'name': 'John Doe', 'email': 'john.doe@example.com'},
        {'id': 2, 'name': 'Jane Smith', 'email': 'jane.smith@example.com'},
        {'id': 3, 'name': 'Robert Johnson', 'email': 'robert.j@example.com'}
    ]
    
    mock_users = [
        {'id': 1, 'name': 'Sarah Johnson', 'role': 'HR Manager'},
        {'id': 2, 'name': 'Michael Chen', 'role': 'Technical Lead'},
        {'id': 3, 'name': 'David Wilson', 'role': 'Hiring Manager'}
    ]
    
    return render_template('interviews.html', 
                         candidates=mock_candidates, 
                         users=mock_users,
                         mock_interviews=get_mock_interview_data())

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_manage_appointments():
    if request.method == 'POST':
        data = request.get_json()
        try:
            appointment = Appointment(
                candidate_id=data['candidate_id'],
                title=data['title'],
                description=data.get('description', ''),
                start_time=datetime.fromisoformat(data['start_time']),
                end_time=datetime.fromisoformat(data['end_time']),
                location=data.get('location', ''),
                meeting_link=data.get('meeting_link', ''),
                status='scheduled'
            )
            db.session.add(appointment)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Appointment scheduled successfully',
                'appointment': appointment.to_dict()
            }), 201
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # GET request - return all appointments
    appointments = Appointment.query.all()
    return jsonify([appt.to_dict() for appt in appointments])

@app.route('/api/appointments/<int:appointment_id>', methods=['GET', 'PUT', 'DELETE'])
def api_manage_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if request.method == 'GET':
        return jsonify(appointment.to_dict())
        
    elif request.method == 'PUT':
        data = request.get_json()
        try:
            appointment.title = data.get('title', appointment.title)
            appointment.description = data.get('description', appointment.description)
            appointment.start_time = datetime.fromisoformat(data.get('start_time', appointment.start_time.isoformat()))
            appointment.end_time = datetime.fromisoformat(data.get('end_time', appointment.end_time.isoformat()))
            appointment.location = data.get('location', appointment.location)
            appointment.meeting_link = data.get('meeting_link', appointment.meeting_link)
            appointment.status = data.get('status', appointment.status)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Appointment updated successfully',
                'appointment': appointment.to_dict()
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
            
    elif request.method == 'DELETE':
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Appointment deleted successfully'})

def get_mock_applications():
    """Return a list of mock job applications with interview details."""
    return [
        {
            'id': 1,
            'job_title': 'Senior Software Engineer',
            'company': 'TechNova Systems',
            'status': 'Interview Scheduled',
            'interview_scheduled': '2023-11-25 10:00:00',
            'meeting_link': 'https://meet.google.com/xyz-abc-123',
            'interview_type': 'Technical Interview',
            'interviewer_name': 'Sarah Johnson',
            'interviewer_role': 'Engineering Manager',
            'interview_duration': '60 minutes',
            'interview_format': 'Video Call',
            'preparation_materials': [
                'Review our tech stack: Python, Django, React, AWS',
                'Prepare to discuss system design concepts',
                'Be ready for live coding exercises'
            ],
            'contact_person': 'Sarah Johnson',
            'contact_email': 'sarah.johnson@technova.com',
            'interview_notes': 'Please have your ID ready for verification at the start of the interview.'
        },
        # Add more mock applications as needed
    ]

@app.route('/interview/<int:application_id>')
def interview_screen(application_id):
    """Display the interview details for a specific application."""
    try:
        # Get the application details
        applications = get_mock_applications()
        application = next((app for app in applications if app['id'] == application_id), None)
        
        if not application:
            flash('Application not found', 'error')
            return redirect(url_for('candidate_applications'))
        
        # Check if interview is scheduled
        if not application.get('interview_scheduled'):
            flash('No interview scheduled for this application', 'warning')
            return redirect(url_for('candidate_applications'))
        
        # Prepare interview data with additional details
        interview_data = {
            'job_title': application['job_title'],
            'company': application['company'],
            'scheduled_time': application['interview_scheduled'],
            'formatted_time': datetime.strptime(
                application['interview_scheduled'], 
                '%Y-%m-%d %H:%M:%S'
            ).strftime('%A, %B %d, %Y at %I:%M %p'),
            'time_until': (datetime.strptime(
                application['interview_scheduled'], 
                '%Y-%m-%d %H:%M:%S'
            ) - datetime.now()).days,
            'meeting_link': application.get('meeting_link', '#'),
            'interview_type': application.get('interview_type', 'Interview'),
            'interviewer_name': application.get('interviewer_name', 'Interviewer'),
            'interviewer_role': application.get('interviewer_role', ''),
            'interview_duration': application.get('interview_duration', '60 minutes'),
            'interview_format': application.get('interview_format', 'Video Call'),
            'preparation_materials': application.get('preparation_materials', []),
            'contact_person': application.get('contact_person', 'HR Representative'),
            'contact_email': application.get('contact_email', ''),
            'interview_notes': application.get('interview_notes', '')
        }
        
        return render_template('candidate/interview.html', 
                            application=application,
                            interview=interview_data)
                            
    except Exception as e:
        app.logger.error(f"Error loading interview screen: {str(e)}")
        flash('An error occurred while loading the interview details', 'error')
        return redirect(url_for('candidate_applications'))

@app.route('/workflow.html')
def workflow_route():
    """Route for the workflow page"""
    return render_template('workflow.html')

if __name__ == '__main__':
    with app.app_context():
        # Only create tables if they don't exist
        if not os.path.exists(os.path.join(basedir, 'app.db')):
            db.create_all()
    app.run(debug=True, port=5000)
