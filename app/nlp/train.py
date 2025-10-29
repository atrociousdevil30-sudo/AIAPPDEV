import numpy as np
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string
import pickle

# Download required NLTK data
def download_nltk_data():
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('stopwords', quiet=True)

download_nltk_data()

class NLPChatbot:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english') + list(string.punctuation))
        self.vectorizer = TfidfVectorizer(tokenizer=self._lemmatize_text, stop_words='english')
        self.training_data = []
        self.model = None
        self.responses = {}
        self.model_path = os.path.join(os.path.dirname(__file__), 'chatbot_model.pkl')
        self.training_data_path = os.path.join(os.path.dirname(__file__), 'training_data.json')
        
        # Load existing model if available
        if os.path.exists(self.model_path) and os.path.exists(self.training_data_path):
            self._load_model()
        else:
            self._initialize_default_data()
    
    def _lemmatize_text(self, text):
        tokens = word_tokenize(text.lower())
        return [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stop_words]
    
    def _initialize_default_data(self):
        # Default training data
        self.training_data = [
            ("hello", "greeting"),
            ("hi there", "greeting"),
            ("how are you", "greeting"),
            ("good morning", "greeting"),
            ("good evening", "greeting"),
            ("bye", "goodbye"),
            ("see you later", "goodbye"),
            ("goodbye", "goodbye"),
            ("how to evaluate a candidate", "evaluation_process"),
            ("what makes a good candidate", "evaluation_criteria"),
            ("interview questions for technical role", "interview_questions"),
            ("how to assess communication skills", "skill_assessment"),
            ("what to look for in a resume", "resume_evaluation"),
            ("how to conduct an interview", "interview_conduct")
        ]
        
        self.responses = {
            "greeting": [
                "Hello! How can I assist you with your recruitment process today?",
                "Hi there! I'm here to help with your hiring needs. What would you like to know?",
                "Welcome! How can I help you with your recruitment process?"
            ],
            "goodbye": [
                "Goodbye! Let me know if you need any more help with your recruitment process.",
                "Have a great day! Feel free to come back if you have more questions.",
                "Goodbye! If you need assistance later, I'll be here."
            ],
            "evaluation_process": [
                "When evaluating candidates, consider their technical skills, problem-solving abilities, and cultural fit. Look for a balance of experience, potential, and alignment with your company values.",
                "A good evaluation process includes technical assessments, behavioral interviews, and practical tasks. Don't forget to assess both hard and soft skills.",
                "Start with a resume review, then conduct initial screening calls, followed by technical assessments and cultural fit interviews."
            ],
            "evaluation_criteria": [
                "Look for a combination of technical expertise, problem-solving skills, communication abilities, and cultural fit. Past experience and potential for growth are also important.",
                "Key indicators include relevant experience, ability to articulate thoughts clearly, problem-solving approach, and alignment with your company values.",
                "Focus on their technical skills, adaptability, teamwork, and how they handle challenges. Cultural fit is equally important as technical abilities."
            ],
            "interview_questions": [
                "For technical roles, ask about their problem-solving approach, past projects, and how they handle challenges. Include both theoretical questions and practical coding exercises.",
                "Consider asking about their experience with specific technologies, how they debug issues, and their approach to learning new skills.",
                "Behavioral questions like 'Tell me about a challenging project' or 'How do you handle conflicts in a team?' can reveal a lot about a candidate."
            ],
            "skill_assessment": [
                "Assess communication skills through their ability to explain complex concepts clearly, active listening, and how they respond to feedback during the interview.",
                "Look for clarity of thought, ability to structure responses, and how well they understand and answer the questions asked.",
                "Present them with a problem and evaluate how they break it down and explain their thought process."
            ],
            "resume_evaluation": [
                "Look for relevant experience, measurable achievements, career progression, and skills that match your requirements. Check for any gaps in employment.",
                "Pay attention to the quality of their past work, the impact they've made, and how their experience aligns with the role you're hiring for.",
                "Look for consistency, attention to detail, and evidence of continuous learning and professional development."
            ],
            "interview_conduct": [
                "Start with an introduction, explain the interview structure, ask open-ended questions, allow time for candidate questions, and provide information about next steps.",
                "Create a comfortable environment, ask a mix of technical and behavioral questions, and evaluate both skills and cultural fit.",
                "Be prepared, be on time, explain the process, take notes, and provide a positive candidate experience regardless of the outcome."
            ],
            "default": [
                "I'm not sure I understand. Could you rephrase that?",
                "I'm still learning about recruitment. Could you ask me something else?",
                "I don't have enough information to answer that. Could you provide more details?"
            ]
        }
        
        # Save the default data
        self._save_model()
    
    def train(self, new_data=None):
        """
        Train or retrain the model with new data
        Format of new_data: [("sample text", "intent"), ...]
        """
        if new_data:
            self.training_data.extend(new_data)
        
        # Save the updated training data
        with open(self.training_data_path, 'w') as f:
            json.dump({
                'training_data': self.training_data,
                'responses': self.responses
            }, f)
        
        # Retrain the model
        texts = [item[0] for item in self.training_data]
        self.vectorizer.fit(texts)
        self._save_model()
    
    def _save_model(self):
        """Save the trained model and data"""
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'training_data': self.training_data,
                'responses': self.responses
            }, f)
    
    def _load_model(self):
        """Load the trained model and data"""
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
            self.vectorizer = data['vectorizer']
            self.training_data = data['training_data']
            self.responses = data['responses']
    
    def get_response(self, message):
        """Get a response for the given message"""
        # Vectorize the input
        try:
            # Get the most similar question from training data
            query_vec = self.vectorizer.transform([message])
            train_vecs = self.vectorizer.transform([item[0] for item in self.training_data])
            
            # Calculate similarity scores
            similarity_scores = cosine_similarity(query_vec, train_vecs).flatten()
            
            # Get the most similar question's index
            most_similar_idx = np.argmax(similarity_scores)
            similarity = similarity_scores[most_similar_idx]
            
            # If similarity is above threshold, return the corresponding response
            if similarity > 0.6:  # Threshold can be adjusted
                intent = self.training_data[most_similar_idx][1]
                if intent in self.responses:
                    return np.random.choice(self.responses[intent])
            
            # Default response if no good match found
            return np.random.choice(self.responses.get('default', ["I'm not sure how to respond to that."]))
            
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            return "I'm having trouble understanding. Could you rephrase that?"

def initialize_chatbot():
    """Initialize and return a trained chatbot instance"""
    chatbot = NLPChatbot()
    return chatbot

# For testing
if __name__ == "__main__":
    chatbot = NLPChatbot()
    print("Chatbot initialized. Type 'quit' to exit.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Chatbot: Goodbye!")
            break
        
        response = chatbot.get_response(user_input)
        print(f"Chatbot: {response}")
