import random
import json
import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
from sentence_transformers import SentenceTransformer, util
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class NLPAnalyzer:
    def __init__(self):
        # Initialize sentiment analysis pipeline
        self.sentiment_analyzer = pipeline("sentiment-analysis", 
                                         model="distilbert-base-uncased-finetuned-sst-2-english")
        
        # Initialize sentence transformer for semantic similarity
        self.sentence_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize stopwords
        self.stop_words = set(stopwords.words('english'))
        
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of the given text."""
        try:
            return self.sentiment_analyzer(text)[0]
        except Exception as e:
            return {"label": "NEUTRAL", "score": 0.5}
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """Extract top N keywords from the text."""
        try:
            words = [word.lower() for word in word_tokenize(text) 
                    if word.isalnum() and word.lower() not in self.stop_words]
            freq_dist = FreqDist(words)
            return [word for word, _ in freq_dist.most_common(top_n)]
        except Exception as e:
            return []
    
    def get_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        try:
            embeddings = self.sentence_encoder.encode([text1, text2], convert_to_tensor=True)
            return util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
        except Exception as e:
            return 0.0

class AIInterviewer:
    def __init__(self):
        self.nlp = NLPAnalyzer()
        self.interview_state = {
            'current_question_index': 0,
            'start_time': datetime.now().isoformat(),
            'responses': [],
            'current_topic': 'introduction',
            'interview_complete': False,
            'extracted_keywords': set(),
            'conversation_history': [],
            'sentiment_scores': []
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
    
    def process_response(self, user_response: str) -> Dict:
        """Process user's response with NLP analysis and return feedback and next question."""
        # Analyze response with NLP
        sentiment = self.nlp.analyze_sentiment(user_response)
        keywords = self.nlp.extract_keywords(user_response)
        
        # Update interview state
        self.interview_state['extracted_keywords'].update(keywords)
        self.interview_state['sentiment_scores'].append(sentiment['score'])
        
        # Store the response with analysis
        response_data = {
            'question': self.questions[self.interview_state['current_topic']][self.interview_state['current_question_index']],
            'answer': user_response,
            'timestamp': datetime.now().isoformat(),
            'sentiment': sentiment,
            'keywords': keywords
        }
        
        # Add to conversation history
        self.interview_state['conversation_history'].append({
            'role': 'user',
            'content': user_response,
            'analysis': {
                'sentiment': sentiment,
                'keywords': keywords
            }
        })
        
        # Generate feedback using NLP
        feedback = self._generate_nlp_feedback(user_response, sentiment, keywords)
        
        # Get next question based on conversation context
        next_question = self._get_contextual_next_question(user_response, keywords)
        
        # Add AI response to conversation history
        if not self.interview_state['interview_complete']:
            self.interview_state['conversation_history'].append({
                'role': 'assistant',
                'content': next_question['content']
            })
        
        return {
            'feedback': feedback,
            'next_question': next_question,
            'interview_complete': self.interview_state['interview_complete'],
            'analysis': {
                'sentiment': sentiment,
                'keywords': keywords
            }
        }
    
    def _generate_nlp_feedback(self, response: str, sentiment: Dict, keywords: List[str]) -> str:
        """Generate feedback using NLP analysis of the response."""
        feedback = []
        
        # Sentiment-based feedback
        if sentiment['label'] == 'POSITIVE' and sentiment['score'] > 0.9:
            feedback.append("Great enthusiasm in your response!")
        
        # Length-based feedback
        word_count = len(response.split())
        if word_count < 15:
            feedback.append("Consider expanding your answer with more details or examples.")
        elif word_count > 150:
            feedback.append("Your answer is quite detailed. Try to be more concise in your responses.")
        
        # Keyword analysis
        if keywords:
            tech_terms = [kw for kw in keywords if kw in self._get_technical_terms()]
            if tech_terms:
                feedback.append(f"Good use of technical terms like: {', '.join(tech_terms[:3])}.")
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
