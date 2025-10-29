from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json

api = Blueprint('api', __name__)

# In-memory storage for demo purposes
candidates = {}
interviews = {}

@api.route('/api/candidates', methods=['GET'])
def get_candidates():
    """Get all candidates with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status')
    
    filtered = list(candidates.values())
    
    if status:
        filtered = [c for c in filtered if c.get('status') == status]
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return jsonify({
        'data': paginated,
        'total': len(filtered),
        'page': page,
        'per_page': per_page
    })

@api.route('/api/candidates/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    """Get a single candidate by ID"""
    candidate = candidates.get(candidate_id)
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    return jsonify(candidate)

@api.route('/api/candidates', methods=['POST'])
def create_candidate():
    """Create a new candidate with resume upload"""
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Save the file
    filename = secure_filename(file.filename)
    upload_folder = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    # Parse resume (in a real app, you'd use your resume parser here)
    # For now, we'll just store basic info
    candidate_id = len(candidates) + 1
    candidate = {
        'id': candidate_id,
        'name': request.form.get('name', 'Unknown'),
        'email': request.form.get('email', ''),
        'phone': request.form.get('phone', ''),
        'resume_path': filepath,
        'status': 'new',
        'created_at': datetime.utcnow().isoformat(),
        'ats_score': 0.0,
        'skills': [],
        'experience': [],
        'education': []
    }
    
    candidates[candidate_id] = candidate
    return jsonify(candidate), 201

@api.route('/api/candidates/<int:candidate_id>/review', methods=['POST'])
def save_review(candidate_id):
    """Save review notes and status for a candidate"""
    data = request.get_json()
    candidate = candidates.get(candidate_id)
    
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    # Update candidate data
    if 'notes' in data:
        candidate['review_notes'] = data['notes']
    if 'status' in data:
        candidate['status'] = data['status']
    
    return jsonify({'success': True, 'candidate': candidate})

@api.route('/api/interviews/schedule', methods=['POST'])
def schedule_interview():
    """Schedule an interview for a candidate"""
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    
    if not candidate_id or candidate_id not in candidates:
        return jsonify({'error': 'Invalid candidate ID'}), 400
    
    interview_id = len(interviews) + 1
    interview = {
        'id': interview_id,
        'candidate_id': candidate_id,
        'scheduled_time': f"{data.get('date')} {data.get('time')}",
        'type': data.get('type', 'video'),
        'status': 'scheduled',
        'notes': data.get('notes', ''),
        'created_at': datetime.utcnow().isoformat()
    }
    
    interviews[interview_id] = interview
    
    # Update candidate status
    candidates[candidate_id]['status'] = 'interview_scheduled'
    
    return jsonify({'success': True, 'interview': interview})

@api.route('/api/ai/analyze-answer', methods=['POST'])
def analyze_answer():
    """Analyze a candidate's answer using AI"""
    data = request.get_json()
    question = data.get('question')
    answer = data.get('answer')
    
    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400
    
    # In a real app, you would call your AI service here
    # For demo purposes, we'll return a mock response
    analysis = {
        'relevance': 0.85,
        'clarity': 0.78,
        'technical_accuracy': 0.82,
        'overall_score': 0.82,
        'feedback': "The candidate provided a detailed response that directly addressed the question. " +
                   "They demonstrated good technical knowledge and provided specific examples to support their points. " +
                   "The answer was well-structured and easy to follow.",
        'suggested_follow_up': "Can you elaborate on how you would apply this approach in a team setting?"
    }
    
    return jsonify(analysis)

@api.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get summary analytics for the dashboard"""
    total_candidates = len(candidates)
    candidates_by_status = {}
    
    for candidate in candidates.values():
        status = candidate.get('status', 'unknown')
        candidates_by_status[status] = candidates_by_status.get(status, 0) + 1
    
    return jsonify({
        'total_candidates': total_candidates,
        'candidates_by_status': candidates_by_status,
        'interviews_scheduled': len([i for i in interviews.values() if i['status'] == 'scheduled']),
        'interviews_completed': len([i for i in interviews.values() if i['status'] == 'completed']),
        'average_ats_score': sum(c.get('ats_score', 0) for c in candidates.values()) / total_candidates if total_candidates > 0 else 0
    })

# Register the blueprint in your app.py:
# from api_routes import api as api_blueprint
# app.register_blueprint(api_blueprint)
