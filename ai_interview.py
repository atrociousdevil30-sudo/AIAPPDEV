import random
from typing import Dict, List, Optional
from datetime import datetime
import json

class AIInterviewer:
    def __init__(self):
        self.interview_state = {
            'current_question_index': 0,
            'start_time': datetime.now().isoformat(),
            'responses': [],
            'current_topic': 'introduction',
            'interview_complete': False
        }
        
        # Define interview questions by category
        self.questions = {
            'introduction': [
                "Can you tell me about yourself?",
                "Walk me through your resume.",
                "How did you hear about this position?"
            ],
            'technical': [
                "What programming languages are you most comfortable with?",
                "Describe a challenging technical problem you've solved.",
                "How do you stay updated with the latest technology trends?"
            ],
            'behavioral': [
                "Tell me about a time you faced a difficult situation at work and how you handled it.",
                "Describe a time when you had to work with a difficult team member.",
                "Give an example of how you handled a tight deadline."
            ],
            'situational': [
                "What would you do if you disagreed with your manager's decision?",
                "How would you handle a situation where you don't know the answer to a problem?",
                "Describe how you would prioritize tasks when everything is a priority."
            ]
        }
        
        # Feedback templates
        self.feedback_templates = {
            'positive': [
                "Great answer! You provided specific examples which really help illustrate your point.",
                "Excellent response! You demonstrated good communication skills.",
                "Well done! You clearly articulated your thoughts on this topic."
            ],
            'constructive': [
                "Consider expanding on that point with a specific example from your experience.",
                "You might want to structure your response using the STAR method (Situation, Task, Action, Result).",
                "Try to be more specific about your role and contributions in that situation."
            ]
        }

    def get_next_question(self) -> Dict[str, str]:
        """Get the next question based on the current interview state."""
        if self.interview_state['interview_complete']:
            return self._generate_final_feedback()
            
        # Get all questions for current topic
        topic_questions = self.questions.get(self.interview_state['current_topic'], [])
        
        # If we've asked all questions in this topic, move to next topic
        if self.interview_state['current_question_index'] >= len(topic_questions):
            return self._transition_to_next_topic()
        
        # Get the next question
        question = topic_questions[self.interview_state['current_question_index']]
        return {
            'type': 'question',
            'content': question,
            'topic': self.interview_state['current_topic'].title(),
            'question_number': self.interview_state['current_question_index'] + 1,
            'total_questions': len(topic_questions)
        }
    
    def process_answer(self, answer: str, question: str) -> Dict[str, str]:
        """Process the user's answer and generate a response."""
        # Store the response
        self.interview_state['responses'].append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })
        
        # Simple analysis of the answer (in a real app, this would use NLP)
        answer_quality = self._analyze_answer(answer)
        
        # Move to next question
        self.interview_state['current_question_index'] += 1
        
        # Generate feedback
        feedback = self._generate_feedback(answer_quality)
        
        # Check if we should move to the next question or topic
        next_question = self.get_next_question()
        
        return {
            'type': 'feedback',
            'feedback': feedback,
            'next_question': next_question,
            'answer_quality': answer_quality
        }
    
    def _analyze_answer(self, answer: str) -> Dict[str, float]:
        """Analyze the quality of the answer (simplified for demo)."""
        # In a real app, this would use NLP to analyze the response
        word_count = len(answer.split())
        
        # Simple heuristics for demo purposes
        return {
            'length_score': min(word_count / 30, 1.0),  # Max 30 words for good length
            'specificity': random.uniform(0.5, 1.0),    # Random for demo
            'relevance': random.uniform(0.7, 1.0),      # Random for demo
            'clarity': random.uniform(0.6, 1.0)         # Random for demo
        }
    
    def _generate_feedback(self, analysis: Dict[str, float]) -> str:
        """Generate feedback based on answer analysis."""
        feedback = []
        
        # Add positive feedback
        if analysis['length_score'] > 0.7:
            feedback.append(random.choice(self.feedback_templates['positive']))
        
        # Add constructive feedback
        if analysis['length_score'] < 0.4:
            feedback.append("Your answer was quite brief. Try to provide more details or examples to strengthen your response.")
        
        # Add a random constructive tip
        if random.random() > 0.3:  # 70% chance to add a tip
            feedback.append(random.choice(self.feedback_templates['constructive']))
        
        return ' '.join(feedback) if feedback else "Thank you for your answer. Let's move on to the next question."
    
    def _transition_to_next_topic(self) -> Dict[str, str]:
        """Transition to the next topic or end the interview."""
        topics = list(self.questions.keys())
        current_index = topics.index(self.interview_state['current_topic'])
        
        if current_index < len(topics) - 1:
            # Move to next topic
            self.interview_state['current_topic'] = topics[current_index + 1]
            self.interview_state['current_question_index'] = 0
            return self.get_next_question()
        else:
            # End of interview
            self.interview_state['interview_complete'] = True
            return self._generate_final_feedback()
    
    def _generate_final_feedback(self) -> Dict[str, str]:
        """Generate final feedback at the end of the interview."""
        return {
            'type': 'interview_complete',
            'content': 'Thank you for completing the interview! Here are some overall tips based on your responses:',
            'summary': {
                'total_questions_answered': len(self.interview_state['responses']),
                'average_response_length': sum(len(r['answer'].split()) for r in self.interview_state['responses']) / 
                                         max(1, len(self.interview_state['responses'])),
                'suggested_improvements': [
                    "Try to provide more specific examples from your experience.",
                    "Consider structuring your responses using the STAR method (Situation, Task, Action, Result).",
                    "Practice speaking clearly and concisely."
                ]
            }
        }
    
    def get_interview_summary(self) -> Dict:
        """Get a summary of the interview session."""
        return {
            'start_time': self.interview_state['start_time'],
            'end_time': datetime.now().isoformat(),
            'total_questions': len(self.interview_state['responses']),
            'topics_covered': list(set(r['topic'] for r in self.interview_state['responses'])),
            'responses': self.interview_state['responses']
        }
