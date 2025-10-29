import os
import json
import random
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory, current_app, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from typing import Dict, List, Any, Tuple, Optional
import re
import pickle
import os
from pathlib import Path
from datetime import datetime

# Import models after db is initialized to avoid circular imports
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

# Initialize CSRF protection
csrf = CSRFProtect(app)

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

@app.route('/logout')
def logout():
    return redirect(url_for('select_role'))

@app.route('/select-role')
def select_role():
    # Set default user as HR for demo purposes
    session['user_id'] = 1
    session['user_role'] = 'hr'
    session['user_name'] = 'Demo HR User'
    return redirect(url_for('hr_dashboard'))

# Public routes for all templates
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/candidate/applications')
def candidate_applications_route():
    return render_template('candidate_applications.html')

@app.route('/candidate/dashboard')
def candidate_dashboard_route():
    return render_template('candidate_dashboard.html')

@app.route('/candidate/interviews')
def candidate_interviews_route():
    return render_template('candidate_interviews.html')

@app.route('/candidate/resume')
def candidate_resume_route():
    return render_template('candidate_resume.html')

@app.route('/dashboard')
def dashboard_route():
    return render_template('dashboard.html')

@app.route('/error')
def error_route():
    return render_template('error.html')

@app.route('/exit')
def exit_route():
    return render_template('exit.html')

@app.route('/interview')
def interview_route():
    return render_template('interview.html')

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

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding_route():
    if request.method == 'POST':
        try:
            # Get form data
            candidate_name = request.form.get('candidateName')
            job_title = request.form.get('jobDescriptionTitle')
            job_description = request.form.get('jobDescription')
            resume_text = request.form.get('resumeText')
            
            # Save the resume text to a temporary file for parsing
            temp_file = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_resume.txt')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(resume_text)
            
            # Parse the resume
            try:
                parser = ResumeParser()
                resume_data = parser.parse_resume(temp_file)
            except Exception as e:
                app.logger.error(f"Error parsing resume: {str(e)}")
                resume_data = ResumeData()  # Create empty ResumeData object if parsing fails
            
            # Add job title from form if not in resume
            if not resume_data.name and candidate_name:
                resume_data.name = candidate_name
            
            # Prepare analysis results
            analysis = {
                'candidate': {
                    'name': resume_data.name or candidate_name,
                    'email': resume_data.email,
                    'phone': resume_data.phone
                },
                'job': {
                    'title': job_title,
                    'description': job_description
                },
                'skills': resume_data.skills or [],
                'experience': resume_data.experience or [],
                'match_score': calculate_match_score(resume_data, job_title, job_description)
            }
            
            # Store in session to display results
            session['last_analysis'] = analysis
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
                
            return redirect(url_for('onboarding_route'))
            
        except Exception as e:
            app.logger.error(f"Error analyzing resume: {str(e)}")
            flash('Error analyzing resume. Please try again.', 'error')
            return redirect(url_for('onboarding_route'))
    
    # For GET requests, show the form with sample candidates
    analysis = session.pop('last_analysis', None)
    sample_resumes = {
        1: """Michael Chen
Senior Software Engineer

EXPERIENCE
Senior Software Engineer
Tech Solutions Inc. | Jan 2020 - Present
- Led team of 5 developers in building scalable microservices
- Implemented CI/CD pipeline reducing deployment time by 60%
- Technologies: Python, Django, React, AWS, Docker

Software Developer
WebApps Co. | Mar 2017 - Dec 2019
- Developed and maintained web applications using Python/Flask
- Improved application performance by 45% through query optimization

EDUCATION
MS in Computer Science
Stanford University | 2015-2017

SKILLS
Python, JavaScript, AWS, Docker, Kubernetes, CI/CD, Microservices
""",
        2: """Priya Patel
Data Scientist

EXPERIENCE
Data Scientist
Data Insights LLC | May 2019 - Present
- Built ML models for predictive analytics with 92% accuracy
- Led data visualization projects using Tableau and D3.js
- Technologies: Python, TensorFlow, PyTorch, SQL, Spark

Data Analyst
Analytics Pro | Jun 2017 - Apr 2019
- Performed data cleaning and analysis for enterprise clients
- Created dashboards that reduced reporting time by 70%

EDUCATION
PhD in Data Science
MIT | 2013-2017

SKILLS
Machine Learning, Python, R, SQL, Tableau, Big Data
""",
        3: """Marcus Rodriguez
DevOps Engineer

EXPERIENCE
DevOps Engineer
CloudScale Inc. | Aug 2018 - Present
- Automated deployment processes reducing manual work by 80%
- Managed Kubernetes clusters with 99.99% uptime
- Technologies: AWS, Kubernetes, Terraform, Ansible, Jenkins

Systems Administrator
TechCorp | Jan 2016 - Jul 2018
- Managed Linux servers and cloud infrastructure
- Implemented monitoring solutions reducing incident response time

EDUCATION
BS in Computer Engineering
UC Berkeley | 2012-2016

SKILLS
AWS, Kubernetes, Docker, Terraform, CI/CD, Linux, Bash
""",
        4: """Aisha Johnson
Frontend Developer

EXPERIENCE
Frontend Developer
WebCraft Studios | Mar 2019 - Present
- Developed responsive web applications using React and TypeScript
- Improved page load performance by 50% through code optimization
- Technologies: React, TypeScript, Redux, GraphQL, Jest

UI/UX Designer
DesignHub | Jun 2017 - Feb 2019
- Created user-centered designs and prototypes
- Conducted user research and usability testing

EDUCATION
BFA in Design
Rhode Island School of Design | 2013-2017

SKILLS
React, TypeScript, JavaScript, CSS, UI/UX, Figma, Responsive Design
"""
    }
    
    # Prepare sample candidates data with resume text
    sample_candidates = []
    
    # If no candidates in database, create sample data
    candidates = Candidate.query.all()
    if not candidates:
        # Create sample candidates with diverse backgrounds
        sample_candidates = [
            {
                'id': 1,
                'name': 'Michael Chen',
                'position': 'Senior Software Engineer',
                'experience': '8 years',
                'status': 'New',
                'email': 'michael.chen@example.com',
                'phone': '(555) 123-4567',
                'job_desc': 'Senior Software Engineer • 8 years experience',
                'resume_text': sample_resumes[1] if 1 in sample_resumes else ''
            },
            {
                'id': 2,
                'name': 'Priya Patel',
                'position': 'Data Scientist',
                'experience': '5 years',
                'status': 'New',
                'email': 'priya.patel@example.com',
                'phone': '(555) 234-5678',
                'job_desc': 'Data Scientist • 5 years experience',
                'resume_text': sample_resumes[2] if 2 in sample_resumes else ''
            },
            {
                'id': 3,
                'name': 'Marcus Rodriguez',
                'position': 'DevOps Engineer',
                'experience': '6 years',
                'status': 'New',
                'email': 'marcus.rodriguez@example.com',
                'phone': '(555) 345-6789',
                'job_desc': 'DevOps Engineer • 6 years experience',
                'resume_text': sample_resumes[3] if 3 in sample_resumes else ''
            },
            {
                'id': 4,
                'name': 'Aisha Johnson',
                'position': 'Frontend Developer',
                'experience': '4 years',
                'status': 'New',
                'email': 'aisha.johnson@example.com',
                'phone': '(555) 456-7890',
                'job_desc': 'Frontend Developer • 4 years experience',
                'resume_text': sample_resumes[4] if 4 in sample_resumes else ''
            }
        ]
    else:
        # Use existing candidates from database
        for candidate in candidates:
            if candidate.id in sample_resumes:
                sample_candidates.append({
                    'id': candidate.id,
                    'name': f"{candidate.first_name} {candidate.last_name}",
                    'position': candidate.current_job_title or 'Not specified',
                    'experience': f"{candidate.years_of_experience or 0} years" if candidate.years_of_experience is not None else 'Experience not specified',
                    'status': candidate.status or 'New',
                    'email': candidate.email,
                    'phone': candidate.phone or 'Not provided',
                    'job_desc': f"{candidate.current_job_title or 'Not specified'} • {candidate.years_of_experience or 0} years experience",
                    'resume_text': sample_resumes[candidate.id]
            })
    
    # Ensure analysis has all required fields with defaults
    analysis = analysis or {}
    analysis.setdefault('candidate', {
        'name': 'Not specified',
        'email': 'Not specified',
        'phone': 'Not specified'
    })
    analysis.setdefault('job', {
        'title': 'Not specified',
        'description': 'Not specified'
    })
    analysis.setdefault('match_score', {
        'score': 0,
        'experience_match': 0,
        'experience_level': 'Not specified',
        'matched_skills': [],
        'missing_skills': []
    })
    
    # Set default values for the template
    match_score = analysis['match_score']
    
    return render_template('onboarding.html', 
                         sample_candidates=sample_candidates,
                         analysis=analysis,
                         match_score=match_score,
                         score=match_score.get('score', 0),
                         experience_match=match_score.get('experience_match', 0),
                         experience_level=match_score.get('experience_level', 'Not specified'))

@app.route('/resume-review')
def resume_review_route():
    return render_template('resume_review.html')

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
    
    # Sample sentiment data (in a real app, this would come from your database)
    sentiment_data = {
        'Positive': random.randint(15, 25),
        'Neutral': random.randint(5, 15),
        'Negative': random.randint(1, 5)
    }
    sentiment_total = sum(sentiment_data.values())
    
    return render_template(
        'dashboard.html',
        total_candidates=total_candidates,
        total_applications=total_applications,
        interviews_scheduled=interviews_scheduled,
        jobs_posted=jobs_posted,
        recent_activities=recent_activities,
        top_candidates=top_candidates,
        status_counts=status_counts,
        score_distribution=score_distribution,
        hiring_trends=hiring_trends,
        avg_ats_score=avg_ats_score,
        hiring_rate=hiring_rate,
        sentiment_data=sentiment_data,
        sentiment_total=sentiment_total if sentiment_total > 0 else 1  # Avoid division by zero
    )

# Candidate Routes
def get_recent_activities(applications):
    """Generate recent activities from application status updates."""
    activities = []
    
    for app in applications:
        # Add application submission as first activity
        activities.append({
            'date': app['applied_date'],
            'description': f'Application submitted for {app["job_title"]} at {app["company"]}',
            'status': 'Submitted',
            'position': app['job_title']
        })
        
        # Add all status updates as activities
        if 'application_status' in app:
            for status_update in app['application_status']:
                if status_update['status'] != 'Application Submitted':  # Skip duplicate of submission
                    activities.append({
                        'date': status_update['date'],
                        'description': f"{status_update['status']}: {app['job_title']} at {app['company']}",
                        'details': status_update.get('details', ''),
                        'status': status_update['status'],
                        'position': app['job_title']
                    })
    
    # Sort activities by date in descending order and return only the 5 most recent
    activities.sort(key=lambda x: x['date'], reverse=True)
    return activities[:5]

@app.route('/candidate/dashboard')
def candidate_dashboard():
    # Get candidate's activities and interviews from database
    candidate_name = session.get('username', 'Candidate')
    candidate = Candidate.query.filter_by(name=candidate_name).first()
    
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
    
    return render_template('candidate_dashboard.html',
                         activities=activities,
                         upcoming_interviews=upcoming_interviews)

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
    # Get all interviews with candidate details
    interviews = []
    for interview in db.interviews:
        candidate = next((c for c in db.candidates if c.id == interview.candidate_id), None)
        if candidate:
            interview.candidate_name = f"{candidate.first_name} {candidate.last_name}"
            interview.candidate_email = candidate.email
            interview.candidate_phone = candidate.phone
            interviews.append(interview)
    
    # Sort interviews by date (most recent first)
    interviews.sort(key=lambda x: x.interview_date, reverse=True)
    
    # Group interviews by status
    upcoming = [i for i in interviews if i.status == 'scheduled' and i.interview_date >= datetime.now()]
    completed = [i for i in interviews if i.status == 'completed']
    cancelled = [i for i in interviews if i.status == 'cancelled']
    
    return render_template('interviews.html', 
                         upcoming=upcoming,
                         completed=completed,
                         cancelled=cancelled)

@app.route('/candidate/interview')
def candidate_interview():
    # For candidates, show the interview screen
    return render_template('candidate/interview_screen.html')

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
    return render_template('candidate/applications.html', applications=applications)

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
    # Resume upload page
    return render_template('candidate/resume_upload.html')

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

@app.route('/schedule-interview/<int:candidate_id>', methods=['GET', 'POST'])
def schedule_interview(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    
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

@app.route('/interview/<int:application_id>')
def interview_screen(application_id):
    # Get the application details
    applications = get_mock_applications()
    application = next((app for app in applications if app['id'] == application_id), None)
    
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('candidate_applications'))
    
    # Check if interview is scheduled
    if not application.get('interview_scheduled'):
        flash('No interview scheduled for this application', 'error')
        return redirect(url_for('candidate_applications'))
    
    # Prepare interview data
    interview_data = {
        'job_title': application['job_title'],
        'company': application['company'],
        'scheduled_time': application['interview_scheduled'],
        'meeting_link': application.get('meeting_link', '#')
    }
    
    return render_template('candidate/interview.html', 
                         application=application,
                         interview=interview_data)

if __name__ == '__main__':
    with app.app_context():
        # Only create tables if they don't exist
        if not os.path.exists(os.path.join(basedir, 'app.db')):
            db.create_all()
    app.run(debug=True, port=5000)
