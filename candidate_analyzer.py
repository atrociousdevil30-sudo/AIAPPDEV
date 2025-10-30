import json
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

class MockDataGenerator:
    """
    A class to generate mock data for the recruitment pipeline.
    """
    
    @staticmethod
    def generate_pipeline_data() -> Dict[str, Any]:
        """Generate comprehensive mock data for the recruitment pipeline."""
        statuses = [
            "Sourced", 
            "Applied", 
            "Phone Screen", 
            "Technical Interview", 
            "Final Interview", 
            "Offer Extended", 
            "Hired"
        ]
        
        positions = [
            "Software Engineer",
            "Data Scientist",
            "Product Manager",
            "UX Designer",
            "DevOps Engineer",
            "ML Engineer",
            "Frontend Developer",
            "Backend Developer"
        ]
        
        # Generate mock candidates
        candidates = []
        for i in range(1, 21):  # Generate 20 mock candidates
            status = random.choice(statuses)
            position = random.choice(positions)
            candidates.append({
                "id": f"CAN-{1000 + i}",
                "name": f"{' '.join(random.choices(['Alex', 'Jordan', 'Taylor', 'Casey', 'Riley', 'Jamie', 'Morgan', 'Quinn'], k=2))}",
                "position": position,
                "email": f"candidate{i}@example.com",
                "phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "score": random.randint(50, 100),
                "status": status,
                "applied_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Calculate pipeline counts
        pipeline = {status: 0 for status in statuses}
        for candidate in candidates:
            pipeline[candidate["status"]] += 1
        
        return {
            "pipeline": pipeline,
            "candidates": candidates,
            "total_candidates": len(candidates),
            "last_updated": datetime.now().isoformat()
        }


class AIAnalyzer:
    """
    A class to handle AI analysis of candidate interview data.
    This provides a centralized way to generate and manage candidate evaluations.
    """
    
    def __init__(self):
        self.skills = [
            'Technical Knowledge',
            'Problem Solving',
            'Communication',
            'Teamwork',
            'Leadership'
        ]
        
        self.insight_templates = {
            'strengths': [
                'Strong technical background in {job_title} technologies',
                'Demonstrated excellent problem-solving abilities through {example_count} specific examples',
                'Clear and effective communication skills throughout the interview',
                'Shows strong potential for {next_role} roles',
                'Exhibited leadership qualities in team-based scenarios'
            ],
            'improvements': [
                'Could benefit from more experience with {missing_skill}',
                'Would benefit from additional training in {area_for_improvement}',
                'Consider developing more industry-specific knowledge in {industry}',
                'Could improve on {skill} with targeted practice',
                'Would benefit from more experience with {tool_or_technology}'
            ]
        }
    
    def analyze_response_quality(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the quality of candidate responses based on transcript.
        
        Args:
            transcript: List of transcript entries with speaker and text
            
        Returns:
            Dictionary containing response analysis metrics
        """
        if not transcript:
            return {
                'score': 0,
                'word_count': 0,
                'response_times': [],
                'sentiment': 'neutral'
            }
            
        # Simple analysis - in a real app, this would use NLP
        candidate_responses = [t for t in transcript if t.get('speaker') == 'Candidate']
        word_count = sum(len(t.get('text', '').split()) for t in candidate_responses)
        avg_response_length = word_count / len(candidate_responses) if candidate_responses else 0
        
        # Generate a score based on response characteristics
        base_score = min(100, max(30, int(avg_response_length * 2 + 50)))
        
        return {
            'score': base_score + random.randint(-10, 10),  # Add some variance
            'word_count': word_count,
            'response_count': len(candidate_responses),
            'avg_response_length': round(avg_response_length, 1),
            'sentiment': random.choice(['positive', 'neutral', 'positive']),  # Bias toward positive
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def assess_skills(self, candidate_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Assess candidate skills based on their interview performance.
        
        Args:
            candidate_data: Dictionary containing candidate information
            
        Returns:
            List of skill assessments with scores
        """
        # In a real app, this would analyze the transcript and other data
        # For now, we'll generate realistic-looking random scores
        job_title = candidate_data.get('position', 'the role').lower()
        
        skills_assessment = []
        for skill in self.skills:
            # Generate a base score with some randomness
            base_score = random.randint(40, 95)
            
            # Adjust based on job relevance
            if 'data' in job_title and 'Technical' in skill:
                base_score = min(100, base_score + 10)
            
            skills_assessment.append({
                'name': skill,
                'score': min(100, max(0, base_score + random.randint(-10, 10))),
                'description': f"Assessed through interview responses and technical evaluation"
            })
            
        return skills_assessment
    
    def generate_insights(self, candidate_data: Dict[str, Any], skills_assessment: List[Dict[str, Any]]) -> List[str]:
        """
        Generate key insights about the candidate's performance.
        
        Args:
            candidate_data: Dictionary containing candidate information
            skills_assessment: List of skill assessments
            
        Returns:
            List of insight strings
        """
        job_title = candidate_data.get('position', 'the role')
        
        # Get top skills
        top_skills = sorted(skills_assessment, key=lambda x: x['score'], reverse=True)[:2]
        
        # Generate insights
        insights = []
        
        # Add strengths
        for template in self.insight_templates['strengths'][:3]:  # Use first 3 strength templates
            if '{job_title}' in template:
                insights.append(template.format(job_title=job_title))
            elif '{next_role}' in template:
                next_role = self._get_next_role(job_title)
                insights.append(template.format(next_role=next_role))
            else:
                insights.append(template)
        
        # Add 1-2 improvement areas
        improvement_count = random.randint(1, 2)
        for template in random.sample(self.insight_templates['improvements'], improvement_count):
            if '{missing_skill}' in template:
                missing = random.choice(['cloud computing', 'agile methodologies', 'data analysis', 'project management'])
                insights.append(template.format(missing_skill=missing))
            elif '{area_for_improvement}' in template:
                area = random.choice(['technical documentation', 'public speaking', 'time management'])
                insights.append(template.format(area_for_improvement=area))
            else:
                insights.append(template)
        
        return insights
    
    def _get_next_role(self, current_role: str) -> str:
        """Helper to suggest a next role based on current role."""
        role_mapping = {
            'junior': 'mid-level',
            'mid': 'senior',
            'senior': 'lead',
            'lead': 'management'
        }
        
        current_role = current_role.lower()
        for level, next_level in role_mapping.items():
            if level in current_role:
                return next_level
        return 'more senior'
    
    def analyze_candidate(self, candidate_data: Dict[str, Any], transcript: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a candidate.
        
        Args:
            candidate_data: Dictionary containing candidate information
            transcript: Optional interview transcript
            
        Returns:
            Dictionary containing complete analysis
        """
        if transcript is None:
            transcript = candidate_data.get('interview_transcript', [])
        
        # Generate analysis components
        response_analysis = self.analyze_response_quality(transcript)
        skills_assessment = self.assess_skills(candidate_data)
        insights = self.generate_insights(candidate_data, skills_assessment)
        
        # Calculate overall score (weighted average of skills and response quality)
        skill_scores = [s['score'] for s in skills_assessment]
        avg_skill_score = sum(skill_scores) / len(skill_scores) if skill_scores else 0
        overall_score = int((avg_skill_score * 0.7) + (response_analysis['score'] * 0.3))
        
        return {
            'overall_score': overall_score,
            'response_analysis': response_analysis,
            'skills_assessment': skills_assessment,
            'key_insights': insights,
            'analysis_date': datetime.utcnow().isoformat(),
            'candidate_id': candidate_data.get('id'),
            'candidate_name': candidate_data.get('name')
        }

# Example usage
if __name__ == "__main__":
    # Example candidate data
    example_candidate = {
        'id': 1,
        'name': 'John Doe',
        'position': 'Data Scientist',
        'interview_transcript': [
            {'speaker': 'Interviewer', 'text': 'Tell me about your experience with Python.'},
            {'speaker': 'Candidate', 'text': 'I have 5 years of experience with Python, including pandas, numpy, and scikit-learn.'},
            # More transcript entries...
        ]
    }
    
    # Create analyzer and analyze candidate
    analyzer = AIAnalyzer()
    analysis = analyzer.analyze_candidate(example_candidate)
    
    # Print results
    print(f"Analysis for {analysis['candidate_name']}:")
    print(f"Overall Score: {analysis['overall_score']}/100")
    print("\nKey Insights:")
    for insight in analysis['key_insights']:
        print(f"- {insight}")
    
    print("\nSkills Assessment:")
    for skill in analysis['skills_assessment']:
        print(f"{skill['name']}: {skill['score']}%")
    
    print(f"\nResponse Analysis:")
    print(f"Average Response Length: {analysis['response_analysis']['avg_response_length']} words")
    print(f"Sentiment: {analysis['response_analysis']['sentiment']}")
