from flask import Flask
from flask_cors import CORS
import os
from pathlib import Path
import logging
from app.military_law_assistant_config import Config

def create_app():
    # Initialize Flask
    app = Flask(__name__, 
               template_folder='templates', 
               static_folder='static',
               static_url_path='/static')
    
    # Load configuration
    app_config = Config()
    app.config.from_object(app_config)
    
    # Create required directories
    required_dirs = [
        app_config.DOCUMENTS_FOLDER,
        app_config.UPLOAD_FOLDER
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.exists():
            raise RuntimeError(f"Failed to create directory: {directory}")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(__file__).parent.parent / 'app.log')
        ]
    )
    
    # Initialize services
    try:
        from app.services.pdf_service import PDFService
        from app.services.audio_service import AudioService
        from app.services.ai_service import AIService
        
        app.pdf_service = PDFService()
        app.audio_service = AudioService()
        app.ai_service = AIService()
        
        # Verify at least one PDF is loaded
        if not app.pdf_service.available_resources:
            logging.error("No PDF resources were loaded. Some functionality may be limited.")
        else:
            logging.info(f"Loaded {len(app.pdf_service.available_resources)} legal documents")
            
    except Exception as e:
        logging.error(f"Service initialization failed: {str(e)}")
        # We can still run without some services? Probably not, but we log the error.
        raise
    
    # Register routes
    from app.routes import init_routes
    init_routes(app)
    
    # Enable CORS if needed
    CORS(app)
    
    return app