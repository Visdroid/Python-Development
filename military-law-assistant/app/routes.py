from flask import render_template, jsonify, request, current_app, send_from_directory, abort, url_for, send_file
from io import BytesIO
from pathlib import Path
import tempfile
import os
import logging
import re
from urllib.parse import quote
from typing import Optional, List, Dict
import requests
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"

CATEGORY_CONFIG: Dict[str, Dict[str, object]] = {
    'constitutional': {
        'label': 'Constitutional',
        'icon': 'bi-bank',
        'description': 'Constitutional rights, court structure, and state authority.',
        'color': '#1976d2',
        'keywords': [
            'constitution', 'constitutional', 'rights', 'bill of rights',
            'freedom', 'parliament', 'court', 'chapter 2'
        ],
        'image_queries': [
            'South African Constitutional Court',
            'South African Parliament',
            'South African constitution'
             'Criminal arrest'
            'Criminal handcuffed'
        ]
    },
    'criminal': {
        'label': 'Criminal',
        'icon': 'bi-exclamation-octagon',
        'description': 'Criminal procedure, offences, arrests, and prosecution steps.',
        'color': '#d32f2f',
        'keywords': [
            'criminal', 'crime', 'arrest', 'bail', 'charge', 'accused',
            'offence', 'offense', 'prosecution', 'warrant', 'detain'
        ],
        'image_queries': [
            'South African courtroom',
            'South African police service',
            'criminal procedure court',
            'Criminal arrest',
            'Suspect handcuffed'
        ]
    },
    'military': {
        'label': 'Military',
        'icon': 'bi-shield-fill',
        'description': 'Defence, command, discipline, military police, and SANDF matters.',
        'color': '#f57c00',
        'keywords': [
            'military', 'defence', 'defense', 'army', 'soldier', 'navy',
            'air force', 'sandt', 'sandf', 'officer', 'uniform',
            'commanding', 'barracks', 'court martial', 'disciplinary',
            'armoured', 'armored', 'mpi', 'military police instruction',
            'military police', 'SAMHS', 'SANDF', 'military police', 'defence act', 'military discipline act'
        ],
        'image_queries': [
            'South African Army armoured vehicle',
            'South African National Defence Force uniform',
            'South African military parade'
        ]
    },
    'labour': {
        'label': 'Labour',
        'icon': 'bi-briefcase-fill',
        'description': 'Employment rights, discipline, labour relations, and equity.',
        'color': '#388e3c',
        'keywords': [
            'labour', 'labor', 'employment', 'employee', 'employer',
            'dismissal', 'disciplinary hearing', 'workplace', 'salary',
            'union', 'ccma'
        ],
        'image_queries': [
            'South African workplace meeting',
            'South African labour union',
            'employment office South Africa'
        ]
    },
    'financial': {
        'label': 'Financial',
        'icon': 'bi-cash-coin',
        'description': 'Banking, fraud, credit, company, and financial compliance topics.',
        'color': '#7b1fa2',
        'keywords': [
            'finance', 'financial', 'money', 'bank', 'loan', 'credit',
            'fraud', 'company', 'companies', 'consumer', 'fica', 'tax',
            'tender', 'procurement'
        ],
        'image_queries': [
            'South African rand money',
            'South Africa banking finance',
            'Johannesburg financial district'
        ]
    },
    'cyber': {
        'label': 'Cyber',
        'icon': 'bi-shield-lock-fill',
        'description': 'Cybercrime, data protection, interception, and digital evidence.',
        'color': '#00838f',
        'keywords': [
            'cyber', 'data', 'privacy', 'popi', 'computer', 'hack',
            'hacking', 'interception', 'rica', 'digital', 'internet'
        ],
        'image_queries': [
            'cybersecurity network',
            'digital privacy lock',
            'computer security operations center'
        ]
    },
    'police': {
        'label': 'Police',
        'icon': 'bi-person-badge-fill',
        'description': 'Policing powers, SAPS functions, arrests, and public safety.',
        'color': '#455a64',
        'keywords': [
            'police', 'saps', 'peace officer', 'investigator',
            'detective', 'search and seizure'
        ],
        'image_queries': [
            'South African Police Service officers',
            'South African police vehicle',
            'police station South Africa'
        ]
    },
    'investigation': {
        'label': 'Investigation',
        'icon': 'bi-search',
        'description': 'Investigation, intelligence, forensics, and disclosures.',
        'color': '#6d4c41',
        'keywords': [
            'investigation', 'intelligence', 'forensic', 'evidence',
            'whistleblower', 'disclosure'
        ],
        'image_queries': [
            'forensic investigation',
            'evidence collection',
            'intelligence office'
        ]
    }
}

STOP_WORDS = {
    'about', 'after', 'again', 'against', 'asked', 'because', 'before',
    'between', 'could', 'display', 'explain', 'guide', 'have', 'into',
    'legal', 'please', 'prompt', 'question', 'regarding', 'should',
    'south', 'their', 'there', 'these', 'those', 'under', 'using',
    'what', 'when', 'which', 'would', 'with', 'your'
}

def init_routes(app):
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/law')
    def law():
        return render_template(
            'index.html',
            resources=build_resource_catalog(),
            case_sources=current_app.case_archive_service.get_sources(),
            operational_resources=build_operational_resources(),
            premium_tts_voices=current_app.ai_service.get_tts_voice_options(),
            default_tts_voice=current_app.ai_service.tts_voice,
            express_api_base_url=current_app.config.get('EXPRESS_API_BASE_URL')
        )

    @app.route('/documents/<path:file_name>')
    def document_file(file_name):
        safe_name = secure_filename(Path(file_name).name)
        if safe_name != Path(file_name).name or not safe_name.lower().endswith('.pdf'):
            abort(404)

        document_path = current_app.pdf_service.documents_dir / safe_name
        if not document_path.exists() or not document_path.is_file():
            abort(404)

        return send_from_directory(
            str(current_app.pdf_service.documents_dir),
            safe_name,
            mimetype='application/pdf',
            as_attachment=False
        )

    @app.route('/document-viewer/<path:file_name>')
    def document_viewer(file_name):
        safe_name = secure_filename(Path(file_name).name)
        if safe_name != Path(file_name).name or not safe_name.lower().endswith('.pdf'):
            abort(404)

        document_path = current_app.pdf_service.documents_dir / safe_name
        if not document_path.exists() or not document_path.is_file():
            abort(404)

        return render_template(
            'pdf_viewer.html',
            pdf_url=build_document_file_url(safe_name),
            title=safe_name.replace('_', ' ').replace('.pdf', '').title()
        )

    @app.route('/speak', methods=['POST'])
    def speak():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get('text', '')).strip()
        language_code = payload.get('language_code')
        voice = payload.get('voice')

        if not text:
            return jsonify({'error': 'No text provided for speech generation.'}), 400

        try:
            audio_bytes = current_app.ai_service.synthesize_speech(text, language_code, voice)
            return send_file(
                BytesIO(audio_bytes),
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name='legal-answer.mp3'
            )
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({'error': str(exc)}), 503

    @app.route('/cases/search', methods=['GET'])
    def case_search():
        query = request.args.get('q', '').strip()
        source_id = request.args.get('source')

        if not query:
            return jsonify({
                'query': '',
                'results': [],
                'sources': current_app.case_archive_service.get_sources(),
                'message': 'Please enter a search query.'
            }), 200

        payload = current_app.case_archive_service.search_public_cases(query, source_id)
        payload['message'] = (
            "Results are federated links into public archives (current and historical coverage varies by source)."
        )
        return jsonify(payload)
    
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

        selected_category = normalize_selected_category(request.form.get('selected_category'))
        language = current_app.ai_service.detect_language(question)
        categories = determine_categories(question, selected_category)
        context = current_app.pdf_service.extract_text(categories)
        
        try:
            answer = current_app.ai_service.ask_question(question, context, language['code'])
            references = extract_references(answer)
            return jsonify({
                'question': question,
                'answer': answer,
                'references': references,
                'reference_links': build_reference_payload(references, categories),
                'categories': categories or [],
                'language': language,
                'visuals': build_visual_payload(question, answer, categories, references, selected_category)
            })
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            fallback_answer = current_app.ai_service._fallback_response(question, language)
            references = extract_references(fallback_answer)
            return jsonify({
                'error': 'Processing failed',
                'answer': fallback_answer,
                'references': references,
                'reference_links': build_reference_payload(references, categories),
                'categories': categories or [],
                'language': language,
                'visuals': build_visual_payload(question, fallback_answer, categories, references, selected_category)
            })

    def handle_audio_question():
        audio_file = request.files['audio']
        if not audio_file.filename:
            return jsonify({'error': 'No audio file'}), 400

        selected_category = normalize_selected_category(request.form.get('selected_category'))
        temp_path = None
        try:
            temp_path = Path(tempfile.mktemp(suffix='.webm'))
            audio_file.save(temp_path)
            
            if question := current_app.audio_service.process_audio(temp_path):
                language = current_app.ai_service.detect_language(question)
                categories = determine_categories(question, selected_category)
                context = current_app.pdf_service.extract_text(categories)
                answer = current_app.ai_service.ask_question(question, context, language['code'])
                references = extract_references(answer)
                return jsonify({
                    'question': question,
                    'answer': answer,
                    'references': references,
                    'reference_links': build_reference_payload(references, categories),
                    'categories': categories or [],
                    'language': language,
                    'visuals': build_visual_payload(question, answer, categories, references, selected_category)
                })
            return jsonify({'error': 'Audio processing failed'}), 400
        finally:
            if temp_path and temp_path.exists():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def normalize_selected_category(selected_category: Optional[str]) -> Optional[str]:
        if not selected_category:
            return None
        normalized = selected_category.strip().lower()
        if normalized == 'all' or normalized not in CATEGORY_CONFIG:
            return None
        return normalized

    def determine_categories(question: str, selected_category: Optional[str] = None) -> Optional[List[str]]:
        question_lower = question.lower()
        categories: List[str] = []

        if selected_category:
            categories.append(selected_category)

        for category, config in CATEGORY_CONFIG.items():
            keywords = config.get('keywords', [])
            if any(kw in question_lower for kw in keywords):
                categories.append(category)

        deduped = list(dict.fromkeys(categories))
        return deduped if deduped else None

    def extract_prompt_keywords(question: str) -> List[str]:
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", question.lower())
        keywords: List[str] = []
        for word in words:
            if len(word) < 4 or word in STOP_WORDS:
                continue
            if word not in keywords:
                keywords.append(word)
            if len(keywords) == 4:
                break
        return keywords

    def calculate_category_scores(question: str, selected_category: Optional[str] = None) -> Dict[str, int]:
        question_lower = question.lower()
        scores: Dict[str, int] = {}
        for category, config in CATEGORY_CONFIG.items():
            score = sum(1 for kw in config.get('keywords', []) if kw in question_lower)
            if selected_category == category:
                score += 2
            if score > 0:
                scores[category] = score

        if not scores and selected_category:
            scores[selected_category] = 2

        return scores

    def count_case_mentions(answer: str) -> int:
        if not answer:
            return 0

        year_mentions = re.findall(r"\b(?:19|20)\d{2}\b", answer)
        case_markers = re.findall(r"\bcase\b|\bprecedent\b|\bv\.\b|\bv\b", answer, flags=re.IGNORECASE)
        return len(set(year_mentions)) + len(case_markers)

    def build_document_file_url(file_name: str) -> str:
        return url_for('document_file', file_name=file_name)

    def build_document_url(file_name: str) -> str:
        return url_for('document_viewer', file_name=file_name)

    def build_resource_catalog() -> List[Dict[str, object]]:
        available_resources = current_app.pdf_service.get_available_resources()
        grouped_resources: Dict[str, Dict[str, object]] = {}

        for resource in available_resources:
            category = resource['category']
            category_meta = CATEGORY_CONFIG.get(category, {
                'label': category.title(),
                'color': '#1976d2',
                'icon': 'bi-file-earmark-pdf'
            })
            file_name = Path(resource['path']).name
            document_url = build_document_url(file_name) if resource['status'] == 'Available' else None
            raw_document_url = build_document_file_url(file_name) if resource['status'] == 'Available' else None

            grouped_resources.setdefault(category, {
                'key': category,
                'label': category_meta['label'],
                'color': category_meta['color'],
                'icon': category_meta['icon'],
                'resources': []
            })
            grouped_resources[category]['resources'].append({
                'name': resource['name'],
                'category': category,
                'category_label': category_meta['label'],
                'status': resource['status'],
                'size': resource['size'],
                'file_name': file_name,
                'document_url': document_url,
                'raw_document_url': raw_document_url,
                'source_url': resource['url']
            })

        ordered_categories = [
            category for category in CATEGORY_CONFIG.keys()
            if category in grouped_resources
        ]
        ordered_categories.extend(
            category for category in grouped_resources.keys()
            if category not in ordered_categories
        )

        return [grouped_resources[category] for category in ordered_categories]

    def build_operational_resources() -> List[Dict[str, str]]:
        return [
            {
                'title': 'Military Police Instructions (MPI) public document search',
                'category': 'military',
                'description': 'Public government-document search for military police instructions and related directives.',
                'url': 'https://www.gov.za/documents?search_query=military+police+instruction'
            },
            {
                'title': 'SAPS National Instructions public document search',
                'category': 'police',
                'description': 'Public search for SAPS instructions, notices, and published policy references.',
                'url': 'https://www.gov.za/documents?search_query=saps+national+instruction'
            },
            {
                'title': 'SAPS official portal',
                'category': 'police',
                'description': 'Official SAPS portal with media statements, forms, and contact resources.',
                'url': 'https://www.saps.gov.za/'
            },
            {
                'title': 'Government Gazette and public documents',
                'category': 'government',
                'description': 'Government publication archive for legal notices, gazettes, and public acts.',
                'url': 'https://www.gov.za/documents'
            }
        ]

    def extract_act_key(text: str) -> Optional[str]:
        match = re.search(r'Act(?: No\.)?\s+(\d+)\s+of\s+(\d{4})', text, flags=re.IGNORECASE)
        if not match:
            return None
        return f"{int(match.group(1))}-{match.group(2)}"

    def build_reference_payload(references: List[str], categories: Optional[List[str]]) -> List[Dict[str, Optional[str]]]:
        resources = current_app.pdf_service.available_resources
        if categories:
            filtered_resources = [resource for resource in resources if resource['category'] in categories]
            if filtered_resources:
                resources = filtered_resources

        act_resource_map: Dict[str, Dict[str, str]] = {}
        for resource in resources:
            act_key = extract_act_key(resource['name'])
            if act_key and act_key not in act_resource_map:
                act_resource_map[act_key] = resource

        default_resource = resources[0] if resources else None
        payload: List[Dict[str, Optional[str]]] = []

        for reference in references:
            linked_resource = act_resource_map.get(extract_act_key(reference) or '')
            if not linked_resource and reference.lower().startswith('section') and default_resource:
                linked_resource = default_resource

            payload.append({
                'label': reference,
                'document_url': build_document_url(linked_resource['path']) if linked_resource else None,
                'source_url': linked_resource['url'] if linked_resource else None
            })

        return payload

    def build_generated_image(category: str, headline: str, subtitle: str) -> Dict[str, str]:
        config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG['constitutional'])
        color = config['color']
        label = config['label']
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 675'>"
            f"<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
            f"<stop offset='0%' stop-color='{color}'/><stop offset='100%' stop-color='#0f172a'/>"
            "</linearGradient></defs>"
            "<rect width='1200' height='675' fill='url(#g)'/>"
            "<rect x='52' y='52' width='1096' height='571' rx='28' fill='rgba(255,255,255,0.08)' "
            "stroke='rgba(255,255,255,0.28)'/>"
            f"<text x='80' y='168' fill='white' font-size='42' font-family='Segoe UI, Arial, sans-serif'>{label} Visual</text>"
            f"<text x='80' y='280' fill='white' font-size='70' font-weight='700' font-family='Segoe UI, Arial, sans-serif'>{headline}</text>"
            f"<text x='80' y='360' fill='white' font-size='34' font-family='Segoe UI, Arial, sans-serif'>{subtitle}</text>"
            "<circle cx='980' cy='220' r='110' fill='rgba(255,255,255,0.12)'/>"
            "<circle cx='1030' cy='420' r='150' fill='rgba(255,255,255,0.08)'/>"
            "<circle cx='870' cy='470' r='80' fill='rgba(255,255,255,0.10)'/>"
            "</svg>"
        )
        data_url = f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"
        return {
            'title': f"{label} illustration",
            'url': data_url,
            'source': 'Generated',
            'source_url': '',
            'alt': f'{label} themed illustration for the current legal question'
        }

    def fetch_prompt_images(question: str, categories: Optional[List[str]]) -> List[Dict[str, str]]:
        category = categories[0] if categories else 'constitutional'
        config = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG['constitutional'])
        prompt_keywords = extract_prompt_keywords(question)
        search_terms = []

        for base_query in config.get('image_queries', []):
            search_terms.append(base_query)
            if prompt_keywords:
                search_terms.append(f"{base_query} {' '.join(prompt_keywords[:2])}")

        images: List[Dict[str, str]] = []
        seen_urls = set()

        for query in search_terms:
            try:
                response = requests.get(
                    WIKIMEDIA_API_URL,
                    params={
                        'action': 'query',
                        'generator': 'search',
                        'gsrsearch': query,
                        'gsrnamespace': 6,
                        'gsrlimit': 6,
                        'prop': 'pageimages|info',
                        'piprop': 'thumbnail',
                        'pithumbsize': 900,
                        'inprop': 'url',
                        'format': 'json'
                    },
                    headers={
                        'Accept': 'application/json',
                        'User-Agent': 'VisdroidLegalAssistant/1.0 (https://github.com/Visdroid/Python-Development)'
                    },
                    timeout=5
                )
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as exc:
                logger.warning(f"Image search failed for '{query}': {exc}")
                continue
            except ValueError as exc:
                logger.warning(f"Invalid image search response for '{query}': {exc}")
                continue

            pages = payload.get('query', {}).get('pages', {})
            sorted_pages = sorted(pages.values(), key=lambda page: page.get('index', 99999))
            for page in sorted_pages:
                thumbnail = page.get('thumbnail', {}).get('source')
                if not thumbnail or thumbnail in seen_urls:
                    continue

                images.append({
                    'title': page.get('title', 'Prompt image').replace('File:', ''),
                    'url': thumbnail,
                    'source': 'Wikimedia Commons',
                    'source_url': page.get('fullurl', ''),
                    'alt': f"{config['label']} visual related to: {question}"
                })
                seen_urls.add(thumbnail)

                if len(images) == 3:
                    return images

        if images:
            return images

        short_question = " ".join(extract_prompt_keywords(question)[:2]) or config['label']
        return [
            build_generated_image(category, config['label'], short_question),
            build_generated_image(category, 'South African law', 'Prompt matched visual'),
        ]

    def build_visual_payload(
        question: str,
        answer: str,
        categories: Optional[List[str]],
        references: List[str],
        selected_category: Optional[str]
    ) -> Dict[str, object]:
        category_scores = calculate_category_scores(question, selected_category)
        resolved_categories = categories or list(category_scores.keys()) or ['constitutional']
        primary_category = resolved_categories[0]
        primary_config = CATEGORY_CONFIG.get(primary_category, CATEGORY_CONFIG['constitutional'])

        available_resources = current_app.pdf_service.available_resources
        matched_resources = [
            resource for resource in available_resources
            if not categories or resource['category'] in categories
        ]

        if not matched_resources:
            matched_resources = available_resources[:6]

        resource_breakdown: Dict[str, int] = {}
        for resource in matched_resources:
            label = CATEGORY_CONFIG.get(resource['category'], {
                'label': resource['category'].title()
            })['label']
            resource_breakdown[label] = resource_breakdown.get(label, 0) + 1

        score_labels = list(category_scores.keys()) or resolved_categories
        chart_labels = [CATEGORY_CONFIG.get(category, {'label': category.title()})['label'] for category in score_labels]
        chart_values = [category_scores.get(category, 1) for category in score_labels]
        prompt_images = fetch_prompt_images(question, resolved_categories)

        return {
            'primary_category': primary_category,
            'primary_label': primary_config['label'],
            'primary_icon': primary_config['icon'],
            'description': primary_config['description'],
            'matched_categories': [
                {
                    'key': category,
                    'label': CATEGORY_CONFIG.get(category, {'label': category.title()})['label']
                }
                for category in resolved_categories
            ],
            'stats': {
                'matched_documents': len(matched_resources),
                'references_found': len(references),
                'case_mentions': count_case_mentions(answer),
                'detected_categories': len(resolved_categories),
                'answer_words': len(answer.split()) if answer else 0
            },
            'charts': {
                'relevance': {
                    'labels': chart_labels,
                    'values': chart_values
                },
                'resources': {
                    'labels': list(resource_breakdown.keys()),
                    'values': list(resource_breakdown.values())
                }
            },
            'images': prompt_images,
            'resources': [
                {
                    'name': resource['name'],
                    'category': resource['category'],
                    'document_url': build_document_url(resource['path']),
                    'raw_document_url': build_document_file_url(resource['path']),
                    'source_url': resource['url'],
                    'status': 'Available'
                }
                for resource in matched_resources[:6]
            ]
        }

    def extract_references(answer: str) -> List[str]:
        refs = re.findall(
            r'Section\s+\d+[A-Za-z0-9()/-]*|Act No\.\s+\d+\s+of\s+\d{4}|Act\s+\d+\s+of\s+\d{4}',
            answer
        )
        return list(set(refs))

    return app