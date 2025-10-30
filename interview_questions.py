from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import os

@dataclass
class InterviewQuestion:
    id: str
    category: str
    question: str
    difficulty: str
    tags: List[str]
    tips: List[str]
    sample_answers: List[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

class InterviewQuestionBank:
    def __init__(self, storage_file: str = 'interview_questions.json'):
        """
        Initialize the question bank with storage file.
        If the file doesn't exist, it will be created with sample questions.
        """
        self.storage_file = storage_file
        self.questions: Dict[str, InterviewQuestion] = {}
        self._load_questions()
    
    def _load_questions(self) -> None:
        """Load questions from the storage file or initialize with sample data."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.questions = {
                        q_id: InterviewQuestion(**q_data) 
                        for q_id, q_data in data.items()
                    }
                return
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error loading questions: {e}")
                # If there's an error, fall back to sample questions
                self.questions = {}
        
        # If we get here, either the file doesn't exist or there was an error
        self._initialize_sample_questions()
    
    def _save_questions(self) -> None:
        """Save questions to the storage file."""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(
                {q_id: q.__dict__ for q_id, q in self.questions.items()},
                f,
                indent=2,
                ensure_ascii=False
            )
    
    def _generate_id(self, question_text: str) -> str:
        """Generate a unique ID for a question based on its text."""
        import hashlib
        return hashlib.md5(question_text.encode('utf-8')).hexdigest()
    
    def _initialize_sample_questions(self) -> None:
        """Initialize with some sample questions."""
        sample_questions = [
            {
                "category": "Introduction",
                "question": "Can you tell me about yourself?",
                "difficulty": "Easy",
                "tags": ["introduction", "personal"],
                "tips": [
                    "Keep it professional but personable",
                    "Focus on your professional background and achievements",
                    "Limit to 1-2 minutes"
                ],
                "sample_answers": [
                    "I'm a recent Computer Science graduate from XYZ University with a passion for web development. During my studies, I completed several projects using Python and JavaScript, and I'm particularly interested in building scalable web applications. I'm excited about the opportunity to bring my skills to your team."
                ]
            },
            {
                "category": "Technical",
                "question": "Explain the difference between SQL and NoSQL databases.",
                "difficulty": "Medium",
                "tags": ["databases", "sql", "nosql", "technical"],
                "tips": [
                    "Compare structure, schema, and scalability",
                    "Mention use cases for each type",
                    "Provide examples if possible"
                ],
                "sample_answers": [
                    "SQL databases are relational, table-based databases that use structured query language for defining and manipulating data. They have a predefined schema and are great for complex queries. NoSQL databases are non-relational, can be document-based, key-value pairs, or graph databases, and are more flexible with schema design. SQL databases are typically vertically scalable, while NoSQL databases are horizontally scalable. For example, MySQL is great for complex transactions, while MongoDB is better for handling large amounts of unstructured data."
                ]
            },
            {
                "category": "Behavioral",
                "question": "Tell me about a time you faced a challenge at work and how you overcame it.",
                "difficulty": "Medium",
                "tags": ["behavioral", "problem-solving", "teamwork"],
                "tips": [
                    "Use the STAR method (Situation, Task, Action, Result)",
                    "Focus on your problem-solving process",
                    "Highlight what you learned"
                ],
                "sample_answers": [
                    "In my previous role, we had a critical bug in production that was causing data inconsistencies. The situation was urgent as it was affecting our customers. My task was to identify and fix the issue while minimizing downtime. I quickly assembled a small team, and we used a systematic approach to debug the problem. We discovered it was a race condition in our data processing pipeline. I implemented a fix with proper locking mechanisms and added automated tests to prevent similar issues. As a result, we resolved the issue within 4 hours with minimal customer impact, and the additional tests helped catch similar issues in development going forward."
                ]
            }
        ]
        
        for q in sample_questions:
            question = InterviewQuestion(
                id=self._generate_id(q["question"]),
                **q
            )
            self.questions[question.id] = question
        
        self._save_questions()
    
    # CRUD Operations
    
    def add_question(self, question_data: dict) -> InterviewQuestion:
        """Add a new question to the bank."""
        if 'question' not in question_data or not question_data['question'].strip():
            raise ValueError("Question text is required")
        
        # Generate ID from question text
        question_id = self._generate_id(question_data['question'])
        
        if question_id in self.questions:
            raise ValueError("A similar question already exists")
        
        # Set default values for optional fields
        defaults = {
            'category': 'General',
            'difficulty': 'Medium',
            'tags': [],
            'tips': [],
            'sample_answers': []
        }
        
        # Merge provided data with defaults
        question_data = {**defaults, **question_data}
        
        # Create and save the question
        question = InterviewQuestion(id=question_id, **question_data)
        self.questions[question_id] = question
        self._save_questions()
        
        return question
    
    def get_question(self, question_id: str) -> Optional[InterviewQuestion]:
        """Get a question by ID."""
        return self.questions.get(question_id)
    
    def update_question(self, question_id: str, update_data: dict) -> Optional[InterviewQuestion]:
        """Update an existing question."""
        if question_id not in self.questions:
            return None
        
        # Don't allow updating the question text (would change the ID)
        if 'question' in update_data:
            del update_data['question']
        
        # Update the question
        question = self.questions[question_id]
        for key, value in update_data.items():
            if hasattr(question, key):
                setattr(question, key, value)
        
        question.updated_at = datetime.now().isoformat()
        self._save_questions()
        
        return question
    
    def delete_question(self, question_id: str) -> bool:
        """Delete a question from the bank."""
        if question_id in self.questions:
            del self.questions[question_id]
            self._save_questions()
            return True
        return False
    
    # Query Methods
    
    def get_questions_by_category(self, category: str) -> List[InterviewQuestion]:
        """Get all questions in a specific category."""
        return [q for q in self.questions.values() if q.category.lower() == category.lower()]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[InterviewQuestion]:
        """Get all questions of a specific difficulty level."""
        return [q for q in self.questions.values() if q.difficulty.lower() == difficulty.lower()]
    
    def get_questions_by_tag(self, tag: str) -> List[InterviewQuestion]:
        """Get all questions with a specific tag."""
        return [q for q in self.questions.values() if tag.lower() in [t.lower() for t in q.tags]]
    
    def search_questions(self, query: str) -> List[InterviewQuestion]:
        """Search questions by text in question or sample answers."""
        query = query.lower()
        results = []
        
        for question in self.questions.values():
            if (query in question.question.lower() or
                any(query in answer.lower() for answer in question.sample_answers)):
                results.append(question)
        
        return results
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories."""
        return sorted(list(set(q.category for q in self.questions.values())))
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        for q in self.questions.values():
            tags.update(tag.lower() for tag in q.tags)
        return sorted(list(tags))
    
    def get_random_question(self, category: str = None, difficulty: str = None) -> Optional[InterviewQuestion]:
        """Get a random question, optionally filtered by category and/or difficulty."""
        import random
        
        filtered = list(self.questions.values())
        
        if category:
            filtered = [q for q in filtered if q.category.lower() == category.lower()]
        if difficulty:
            filtered = [q for q in filtered if q.difficulty.lower() == difficulty.lower()]
        
        return random.choice(filtered) if filtered else None
