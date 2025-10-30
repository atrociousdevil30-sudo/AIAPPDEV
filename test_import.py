import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.nlp import NLPChatbot
    print("Successfully imported NLPChatbot!")
    chatbot = NLPChatbot()
    print("Successfully created NLPChatbot instance!")
except ImportError as e:
    print(f"Error importing NLPChatbot: {e}")
    print(f"Current sys.path: {sys.path}")
