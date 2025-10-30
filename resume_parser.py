import os
import re
import json
import mimetypes
import spacy
import PyPDF2
import docx
import math
from collections import Counter
from typing import Dict, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime

# ATS Configuration
ATS_CONFIG = {
    'max_resume_length': 2000,  # words
    'min_skills_match_ratio': 0.5,  # 50% of required skills
    'experience_weights': {
        'recent': 1.2,  # Last 2 years
        'mid': 1.0,     # 3-5 years ago
        'old': 0.7      # 5+ years ago
    },
    'keyword_threshold': 0.7,  # Minimum keyword match ratio
    'required_sections': ['experience', 'education', 'skills']
}

# Try to use python-magic-bin if available, otherwise fall back to file extensions
try:
    import magic
    USE_MAGIC = True
except (ImportError, OSError):
    USE_MAGIC = False

# Load the English language model for spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading language model for the spaCy (en_core_web_sm)...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

@dataclass
class ResumeData:
    """Class to store parsed resume data with ATS scoring"""
    # Basic Information
    name: str = ""
    email: str = ""
    phone: str = ""
    raw_text: str = ""
    
    # Parsed Data
    skills: List[Dict] = field(default_factory=list)  # {name: str, category: str, years: int}
    experience: List[Dict] = field(default_factory=list)  # {title: str, company: str, start: str, end: str, description: str}
    education: List[Dict] = field(default_factory=list)  # {degree: str, institution: str, year: int}
    
    # ATS Analysis
    ats_score: float = 0.0
    missing_skills: List[str] = field(default_factory=list)
    keyword_matches: Dict[str, float] = field(default_factory=dict)
    compliance_issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'skills': self.skills,
            'experience': self.experience,
            'education': self.education,
            'ats_score': self.ats_score,
            'missing_skills': self.missing_skills,
            'keyword_matches': self.keyword_matches,
            'compliance_issues': self.compliance_issues
        }

class ResumeParser:
    def __init__(self):
        self.nlp = nlp
        self.skills_db = self._load_skills_database()
        
    def _load_skills_database(self) -> Dict[str, Dict]:
        """Load a categorized database of skills with synonyms and importance"""
        return {
            # Programming Languages
            'Python': {'category': 'programming', 'synonyms': ['Python 3', 'Python 2'], 'importance': 0.9},
            'JavaScript': {'category': 'programming', 'synonyms': ['JS', 'ES6+'], 'importance': 0.9},
            'Java': {'category': 'programming', 'synonyms': [], 'importance': 0.8},
            
            # Frameworks & Libraries
            'React': {'category': 'frontend', 'synonyms': ['React.js', 'ReactJS'], 'importance': 0.9},
            'Node.js': {'category': 'backend', 'synonyms': ['Node', 'NodeJS'], 'importance': 0.85},
            'Django': {'category': 'backend', 'synonyms': [], 'importance': 0.8},
            
            # Tools & Platforms
            'Docker': {'category': 'devops', 'synonyms': ['Docker Compose', 'Docker Swarm'], 'importance': 0.8},
            'AWS': {'category': 'cloud', 'synonyms': ['Amazon Web Services'], 'importance': 0.9},
            'Kubernetes': {'category': 'devops', 'synonyms': ['K8s'], 'importance': 0.85},
            
            # Methodologies
            'Agile': {'category': 'methodology', 'synonyms': ['Scrum', 'Kanban'], 'importance': 0.7},
            'CI/CD': {'category': 'devops', 'synonyms': ['Continuous Integration', 'Continuous Deployment'], 'importance': 0.8}
        }
        
    def _get_skill_info(self, skill_name: str) -> Optional[Dict]:
        """Get skill information from the database with case-insensitive matching"""
        skill_lower = skill_name.lower()
        for skill, info in self.skills_db.items():
            if (skill.lower() == skill_lower or 
                any(s.lower() == skill_lower for s in info['synonyms'])):
                return {'name': skill, **info}
        return None

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file with page numbers and basic formatting"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for i, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {i} ---\n{page_text}\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
        return text.strip()

    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file with paragraph structure"""
        try:
            doc = docx.Document(file_path)
            return "\n".join(
                paragraph.text for paragraph in doc.paragraphs 
                if paragraph.text.strip()
            )
        except Exception as e:
            print(f"Error extracting text from DOCX: {str(e)}")
            return ""
            
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Identify and extract common resume sections"""
        sections = {}
        current_section = "header"
        
        # Common section headers with variations
        section_patterns = {
            'experience': r'(?i)(work\s*experience|employment\s*history|experience)',
            'education': r'(?i)(education|academic\s*background|degrees)',
            'skills': r'(?i)(skills?\s*(?:&|and)?\s*expertise|technical\s*skills?)',
            'projects': r'(?i)(projects|portfolio|key\s*projects)',
            'certifications': r'(?i)(certifications?|licenses?|certificates?)'
        }
        
        # Initialize sections
        for section in section_patterns:
            sections[section] = []
            
        # Split text into lines and process
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            for section, pattern in section_patterns.items():
                if re.search(pattern, line):
                    current_section = section
                    break
            else:
                # Add line to current section
                if current_section and line:
                    sections.setdefault(current_section, []).append(line)
                    
        # Join lines for each section
        return {k: '\n'.join(v) for k, v in sections.items() if v}

    def _get_file_type(self, file_path: str) -> str:
        """Get the MIME type of the file"""
        if USE_MAGIC:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        else:
            # Fallback to file extension check
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type or 'application/octet-stream'

    def extract_text(self, file_path: str) -> str:
        """Extract text from file based on its type"""
        file_type = self._get_file_type(file_path)
        
        if file_type == 'application/pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/msword']:
            return self.extract_text_from_docx(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()

    def analyze_ats_compliance(self, text: str) -> Dict:
        """Check resume for ATS compliance issues"""
        issues = []
        
        # Check length
        word_count = len(text.split())
        if word_count > ATS_CONFIG['max_resume_length']:
            issues.append(f"Resume is too long ({word_count} words, recommended max: {ATS_CONFIG['max_resume_length']})")
            
        # Check for required sections
        sections = self._extract_sections(text)
        missing_sections = [s for s in ATS_CONFIG['required_sections'] if s not in sections]
        if missing_sections:
            issues.append(f"Missing recommended sections: {', '.join(missing_sections)}")
            
        # Check for action verbs
        action_verbs = ['achieved', 'improved', 'increased', 'developed', 'led', 'managed']
        if not any(verb in text.lower() for verb in action_verbs):
            issues.append("Resume may lack action-oriented language")
            
        # Check for metrics
        if not re.search(r'\d+%|\$\d+|\d+\+', text):
            issues.append("Consider adding quantifiable achievements")
            
        return {
            'score': max(0, 100 - (len(issues) * 10)),  # Deduct 10 points per issue
            'issues': issues,
            'word_count': word_count
        }
        
    def calculate_keyword_density(self, text: str, keywords: List[str]) -> Dict[str, float]:
        """Calculate keyword density and match ratio"""
        if not text or not keywords:
            return {}
            
        word_count = len(text.split())
        keyword_counts = {k.lower(): 0 for k in keywords}
        
        # Count keyword occurrences (case-insensitive)
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            if word in keyword_counts:
                keyword_counts[word] += 1
                
        # Calculate density and match ratio
        results = {}
        matched_keywords = 0
        
        for kw, count in keyword_counts.items():
            density = (count / word_count) * 100 if word_count > 0 else 0
            results[kw] = {
                'count': count,
                'density': round(density, 4),
                'matches_required': density >= 0.5  # At least 0.5% density
            }
            if results[kw]['matches_required']:
                matched_keywords += 1
                
        match_ratio = matched_keywords / len(keywords) if keywords else 0
        
        return {
            'keywords': results,
            'match_ratio': match_ratio,
            'is_qualified': match_ratio >= ATS_CONFIG['keyword_threshold']
        }
        
    def extract_name(self, text: str) -> str:
        """Extract candidate name from resume text using NLP"""
        # First try to find name in the first few lines
        first_lines = '\n'.join(text.split('\n')[:10])
        doc = self.nlp(first_lines)
        
        # Look for person names in the document
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
                
        # Fallback: First line that's not empty and not a section header
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line.split()) in [2, 3]:  # Likely a name if 2-3 words
                return line
                
        return "Unknown"

    def extract_email(self, text: str) -> str:
        """Extract email address from resume text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else ""

    def extract_phone(self, text: str) -> str:
        """Extract phone number from resume text"""
        phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else ""

    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text"""
        doc = self.nlp(text.lower())
        found_skills = set()
        
        # Check for exact matches
        for token in doc:
            if token.text in self.skills:
                found_skills.add(token.text)
        
        # Check for n-grams (phrases)
        for i in range(len(doc) - 1):
            phrase = f"{doc[i].text} {doc[i+1].text}"
            if phrase in self.skills:
                found_skills.add(phrase)
        
        return list(found_skills)

    def extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience from resume text"""
        # This is a simplified version - in production, you'd want to use more sophisticated NLP
        experience = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        current_exp = {}
        for i, line in enumerate(lines):
            # Look for job title patterns
            if any(role in line.lower() for role in ['developer', 'engineer', 'manager', 'analyst', 'specialist']):
                if current_exp:
                    experience.append(current_exp)
                    current_exp = {}
                current_exp['title'] = line
            
            # Look for company names (very basic pattern matching)
            elif ' at ' in line.lower() and 'company' not in current_exp:
                current_exp['company'] = line.split(' at ')[-1]
            
            # Look for date ranges (simplified)
            elif re.search(r'\d{4}\s*[-–]\s*(?:Present|\d{4})', line):
                current_exp['duration'] = line
        
        if current_exp:
            experience.append(current_exp)
            
        return experience

    def parse_resume(self, file_path: str, job_description: str = "") -> ResumeData:
        """Parse resume file and return structured data with ATS analysis"""
        try:
            # Extract text from resume
            text = self.extract_text(file_path)
            if not text:
                return ResumeData()
                
            # Initialize resume data with raw text
            resume_data = ResumeData(raw_text=text)
            
            # Extract basic information
            resume_data.name = self.extract_name(text)
            resume_data.email = self.extract_email(text)
            resume_data.phone = self.extract_phone(text)
            
            # Extract structured data
            sections = self._extract_sections(text)
            resume_data.skills = self.extract_skills(sections.get('skills', ''))
            resume_data.experience = self.extract_experience(sections.get('experience', ''))
            resume_data.education = self.extract_education(sections.get('education', ''))
            
            # Perform ATS analysis if job description is provided
            if job_description:
                self.analyze_resume(resume_data, job_description)
            
            return resume_data
            
        except Exception as e:
            print(f"Error parsing resume: {str(e)}")
            import traceback
            traceback.print_exc()
            return ResumeData()
            
    def analyze_resume(self, resume_data: ResumeData, job_description: str) -> None:
        """Perform ATS analysis on the resume"""
        # 1. Check ATS compliance
        compliance = self.analyze_ats_compliance(resume_data.raw_text)
        resume_data.compliance_issues = compliance['issues']
        
        # 2. Extract keywords from job description
        job_keywords = self._extract_keywords(job_description)
        
        # 3. Calculate keyword matches
        keyword_analysis = self.calculate_keyword_density(
            resume_data.raw_text, 
            job_keywords
        )
        resume_data.keyword_matches = keyword_analysis
        
        # 4. Calculate overall ATS score (weighted average of different factors)
        skill_score = self._calculate_skill_score(resume_data.skills, job_keywords)
        exp_score = self._calculate_experience_score(resume_data.experience)
        edu_score = self._calculate_education_score(resume_data.education)
        
        # Calculate weighted score (adjust weights as needed)
        weights = {
            'skills': 0.4,
            'experience': 0.3,
            'education': 0.2,
            'compliance': 0.1
        }
        
        resume_data.ats_score = round(
            (skill_score * weights['skills']) +
            (exp_score * weights['experience']) +
            (edu_score * weights['education']) +
            (compliance['score'] * weights['compliance']),
            2
        )
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text using NLP"""
        if not text:
            return []
            
        # Remove stopwords and get noun chunks
        doc = self.nlp(text.lower())
        keywords = set()
        
        # Add noun chunks
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 2:  # Filter out very short chunks
                keywords.add(chunk.text)
                
        # Add named entities
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'TECH']:
                keywords.add(ent.text)
                
        return list(keywords)
        
    def _calculate_skill_score(self, skills: List[Dict], job_keywords: List[str]) -> float:
        """Calculate skill match score (0-100)"""
        if not skills or not job_keywords:
            return 0.0
            
        # Convert to lowercase for case-insensitive matching
        skill_names = {s['name'].lower() for s in skills}
        job_keywords_lower = {k.lower() for k in job_keywords}
        
        # Calculate match ratio
        matched = skill_names.intersection(job_keywords_lower)
        match_ratio = len(matched) / len(job_keywords_lower) if job_keywords_lower else 0
        
        # Scale to 0-100
        return min(100, match_ratio * 100)
        
    def _calculate_experience_score(self, experience: List[Dict]) -> float:
        """Calculate experience score based on duration and relevance"""
        if not experience:
            return 0.0
            
        total_years = 0
        current_year = datetime.now().year
        
        for exp in experience:
            try:
                start_year = int(exp.get('start_date', str(current_year))[:4])
                end_year = int(exp.get('end_date', str(current_year))[:4] if exp.get('end_date') else current_year)
                years = end_year - start_year
                
                # Apply time-based weighting
                if current_year - end_year <= 2:
                    weight = ATS_CONFIG['experience_weights']['recent']
                elif current_year - end_year <= 5:
                    weight = ATS_CONFIG['experience_weights']['mid']
                else:
                    weight = ATS_CONFIG['experience_weights']['old']
                    
                total_years += years * weight
            except (ValueError, TypeError):
                continue
                
        # Cap at 10 years for scoring
        return min(100, (total_years / 10) * 100)
        
    def _calculate_education_score(self, education: List[Dict]) -> float:
        """Calculate education score based on degrees"""
        if not education:
            return 0.0
            
        # Assign points based on degree level
        degree_scores = {
            'phd': 100,
            'master': 90,
            'bachelor': 80,
            'associate': 60,
            'diploma': 50,
            'certificate': 40
        }
        
        max_score = 0
        for edu in education:
            degree = edu.get('degree', '').lower()
            for level, score in degree_scores.items():
                if level in degree:
                    max_score = max(max_score, score)
                    break
                    
        return max_score

    def to_json(self, resume_data: ResumeData) -> str:
        """Convert ResumeData object to JSON"""
        return json.dumps(asdict(resume_data), indent=2)

# Example usage
if __name__ == "__main__":
    parser = ResumeParser()
    resume_path = input("Enter path to resume file: ")
    if os.path.exists(resume_path):
        result = parser.parse_resume(resume_path)
        print("\nParsed Resume Data:")
        print(parser.to_json(result))
    else:
        print("File not found. Please check the file path.")
