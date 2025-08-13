import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Secure configuration with validation"""
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    DOCUMENTS_FOLDER = BASE_DIR / 'documents'
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # AI Settings with validation
    @property
    def OPENAI_API_KEY(self):
        key = os.getenv('OPENAI_API_KEY')
        if not key or len(key) < 30:  # Basic validation
            raise ValueError("Invalid OpenAI API key configuration")
        return key
    
    @property
    def AI_MODEL(self):
        return os.getenv('AI_MODEL', 'gpt-4-turbo')
    
    @property
    def MAX_TOKENS(self):
        try:
            return int(os.getenv('MAX_TOKENS', 4000))
        except ValueError:
            return 4000
    
    @property
    def TEMPERATURE(self):
        try:
            temp = float(os.getenv('TEMPERATURE', 0.5))
            return max(0.1, min(1.0, temp))  # Clamp between 0.1 and 1.0
        except ValueError:
            return 0.5
    
    @property
    def SYSTEM_PROMPT(self):
        return """You are an expert in all aspects of South African law including military law, 
        criminal law, constitutional law, police procedures, and correctional services. 
        Provide accurate, detailed answers with references to specific sections and acts. 
        For military questions, reference the Defence Act and Military Discipline Act. 
        For police questions, reference SAPS Act and Criminal Procedure Act. 
        Always cite exact sections when possible."""