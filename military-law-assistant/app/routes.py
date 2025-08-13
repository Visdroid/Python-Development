from flask import render_template, jsonify, request, current_app
from pathlib import Path
import tempfile
import os
import logging
import re
from typing import Optional, List
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

def init_routes(app):
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/ask', methods=['POST'])
    def ask():
        try:
            if 'question' in request.form:
                return handle_text_question()
            elif 'audio' in request.files:
                return handle_audio_question()
            return jsonify({'error': 'Invalid request'}), 400
        except Exception as e:
            logger.error(f"Route error: {str(e)}")
            return jsonify({'error': 'System error'}), 500

    def handle_text_question():
        question = request.form['question'].strip()
        if not question:
            return jsonify({'error': 'Empty question'}), 400
        
        categories = determine_categories(question)
        context = current_app.pdf_service.extract_text(categories)
        
        try:
            answer = current_app.ai_service.ask_question(question, context)
            return jsonify({
                'question': question,
                'answer': answer,
                'references': extract_references(answer)
            })
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return jsonify({
                'error': 'Processing failed',
                'answer': current_app.ai_service._fallback_response(question),
                'references': []
            })

    def handle_audio_question():
        audio_file = request.files['audio']
        if not audio_file.filename:
            return jsonify({'error': 'No audio file'}), 400
        
        temp_path = None
        try:
            temp_path = Path(tempfile.mktemp(suffix='.webm'))
            audio_file.save(temp_path)
            
            if question := current_app.audio_service.process_audio(temp_path):
                categories = determine_categories(question)
                context = current_app.pdf_service.extract_text(categories)
                answer = current_app.ai_service.ask_question(question, context)
                return jsonify({
                    'question': question,
                    'answer': answer,
                    'references': extract_references(answer)
                })
            return jsonify({'error': 'Audio processing failed'}), 400
        finally:
            if temp_path and temp_path.exists():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def determine_categories(question: str) -> Optional[List[str]]:
        question_lower = question.lower()
        categories = []
        
        if any(kw in question_lower for kw in ['military', 'defence', 'army']):
            categories.append('military')
        if any(kw in question_lower for kw in ['police', 'saps', 'arrest']):
            categories.append('police')
        if 'constitution' in question_lower:
            categories.append('constitutional')
            
        return categories if categories else None

    def extract_references(answer: str) -> List[str]:
        refs = re.findall(r'Section \d+|Act No\. \d+ of \d{4}|Act \d+ of \d{4}', answer)
        return list(set(refs))

    return app