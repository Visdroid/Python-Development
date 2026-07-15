import os
import openai
import logging
import re
import tempfile
from pathlib import Path
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from app.military_law_assistant_config import Config
from typing import Optional, List, Dict

config = Config()
logger = logging.getLogger(__name__)

LANGUAGE_CONFIG: Dict[str, Dict[str, object]] = {
    'en': {
        'name': 'English',
        'markers': ['the', 'what', 'when', 'where', 'law', 'legal', 'right', 'arrest', 'question']
    },
    'af': {
        'name': 'Afrikaans',
        'markers': ['die', 'wat', 'wanneer', 'reg', 'vraag', 'polisie', 'kan', 'word', 'hierdie']
    },
    'zu': {
        'name': 'isiZulu',
        'markers': ['ngabe', 'umthetho', 'icala', 'iphoyisa', 'yini', 'kanjani', 'ukuze', 'kwesigaba']
    },
    'xh': {
        'name': 'isiXhosa',
        'markers': ['ngaba', 'umthetho', 'ityala', 'ipolisa', 'yintoni', 'njani', 'kwesigaba', 'kunye']
    },
    'st': {
        'name': 'Sesotho',
        'markers': ['molao', 'potso', 'na', 'joang', 'tokelo', 'mapolesa', 'kapa', 'tse']
    },
    'tn': {
        'name': 'Setswana',
        'markers': ['molao', 'potso', 'eng', 'jang', 'ditshwanelo', 'mapodise', 'kgotsa', 'tla']
    },
    'nso': {
        'name': 'Sepedi',
        'markers': ['molao', 'potšišo', 'potsiso', 'eng', 'bjang', 'tokelo', 'maphodisa', 'goba']
    },
    'ts': {
        'name': 'Xitsonga',
        'markers': ['na', 'nawu', 'xinawu', 'milawu', 'maphorisa', 'njhani', 'xivutiso', 'mfanelo']
    },
    've': {
        'name': 'Tshivenda',
        'markers': ['mulayo', 'mbudziso', 'mapholisa', 'mini', 'hani', 'pfanelo', 'na', 'zwine']
    },
    'nr': {
        'name': 'isiNdebele',
        'markers': ['umthetho', 'umbuzo', 'ipholisa', 'ngabe', 'yini', 'njani', 'ilungelo', 'lokhu']
    },
    'ss': {
        'name': 'siSwati',
        'markers': ['umtsetfo', 'umbuto', 'liphoyisa', 'yini', 'kanjani', 'lilungelo', 'ngabe', 'kutsi']
    }
}

SUPPORTED_LANGUAGE_NAMES = ", ".join(
    language['name'] for language in LANGUAGE_CONFIG.values()
)

class AIService:
    def __init__(self):
        api_key = config.OPENAI_API_KEY
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
        self.model = config.AI_MODEL
        self.max_tokens = config.MAX_TOKENS
        self.temperature = config.TEMPERATURE
        self.system_prompt = config.SYSTEM_PROMPT
        self.tts_model = config.TTS_MODEL
        self.tts_voice = config.TTS_VOICE
        self.tts_response_format = config.TTS_RESPONSE_FORMAT
        self.military_keywords = [
            'military', 'defence', 'army', 'soldier', 'navy', 'air force',
            'officer', 'commanding', 'rank', 'court martial', 'disciplinary'
        ]
        self.tts_voices = [
            'marin', 'cedar', 'coral', 'nova', 'sage', 'shimmer',
            'alloy', 'ash', 'ballad', 'echo', 'fable', 'onyx', 'verse'
        ]

    def detect_language(self, question: str) -> Dict[str, str]:
        question_lower = question.lower()
        language_scores: Dict[str, int] = {}

        for code, language in LANGUAGE_CONFIG.items():
            markers = language.get('markers', [])
            score = sum(1 for marker in markers if marker in question_lower)
            if score > 0:
                language_scores[code] = score

        if not language_scores:
            return {'code': 'en', 'name': 'English'}

        best_code = max(language_scores, key=language_scores.get)
        best_score = language_scores[best_code]
        tied_codes = [
            code for code, score in language_scores.items()
            if score == best_score
        ]

        if len(tied_codes) > 1:
            preferred_official_languages = ['af', 'zu', 'xh', 'st', 'tn', 'nso', 'ts', 've', 'nr', 'ss']
            for code in preferred_official_languages:
                if code in tied_codes:
                    best_code = code
                    break
            else:
                best_code = 'en'

        return {
            'code': best_code,
            'name': str(LANGUAGE_CONFIG[best_code]['name'])
        }

    def ask_question(self, question: str, context: str, language_code: Optional[str] = None) -> str:
        """Handle questions with military law focus and robust error handling"""
        language = self._resolve_language(language_code, question)
        if not self.client:
            logger.warning("No OpenAI API key configured - using fallback response")
            return self._fallback_response(question, language)
        
        try:
            if not context or "No PDF documents available" in context:
                logger.warning("No context available - using fallback response")
                return self._fallback_response(question, language)

            if self._is_military_officer_question(question):
                return self._handle_officer_question(question, context, language)

            prompt = self._build_prompt(question, context, language)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=30
                )
                answer = response.choices[0].message.content
                return self._enhance_answer(answer, question, language)
                
            except TimeoutError:
                logger.error("OpenAI API timeout")
                return self._timeout_response(question, language)
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return self._api_error_response(question, language)
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return self._fallback_response(question, language)

    def get_tts_voice_options(self) -> List[str]:
        return self.tts_voices.copy()

    def synthesize_speech(
        self,
        text: str,
        language_code: Optional[str] = None,
        voice: Optional[str] = None
    ) -> bytes:
        if not text or not text.strip():
            raise ValueError("No text was provided for audio generation.")

        if not self.client:
            raise RuntimeError("Premium AI voice is unavailable because OPENAI_API_KEY is not configured.")

        language = self._resolve_language(language_code, text)
        selected_voice = voice if voice in self.tts_voices else self.tts_voice

        temp_audio = None
        try:
            suffix = f".{self.tts_response_format}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                temp_audio = Path(tmp_file.name)

            with self.client.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=selected_voice,
                input=text.strip(),
                instructions=self._build_tts_instructions(language),
                response_format=self.tts_response_format
            ) as response:
                response.stream_to_file(temp_audio)

            return temp_audio.read_bytes()
        except (APIError, APIConnectionError, RateLimitError) as exc:
            logger.error(f"Premium TTS API error: {exc}")
            raise RuntimeError("Premium AI voice is currently unavailable. Please try again shortly.") from exc
        except Exception as exc:
            logger.error(f"Premium TTS failed: {exc}")
            raise RuntimeError("Premium AI voice generation failed.") from exc
        finally:
            if temp_audio and temp_audio.exists():
                try:
                    temp_audio.unlink()
                except OSError as exc:
                    logger.warning(f"Could not remove temporary TTS file: {exc}")

    def _resolve_language(self, language_code: Optional[str], question: str) -> Dict[str, str]:
        if language_code and language_code in LANGUAGE_CONFIG:
            return {
                'code': language_code,
                'name': str(LANGUAGE_CONFIG[language_code]['name'])
            }
        return self.detect_language(question)

    def _is_military_officer_question(self, question: str) -> bool:
        """Check if question relates to military officers"""
        question_lower = question.lower()
        has_military_keywords = any(kw in question_lower for kw in self.military_keywords)
        has_officer_terms = ('officer' in question_lower or 'commanding' in question_lower)
        return has_military_keywords and has_officer_terms

    def _handle_officer_question(self, question: str, context: str, language: Dict[str, str]) -> str:
        """Special handling for military officer-related questions"""
        if not self.client:
            return self._fallback_response(question, language)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self._build_officer_prompt(question, context, language)}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
                timeout=20
            )
            base_answer = response.choices[0].message.content
            return self._enhance_officer_answer(base_answer, question, language)
        except Exception:
            return self._fallback_response(question, language)

    def _build_prompt(self, question: str, context: str, language: Dict[str, str]) -> str:
        """Construct prompt for general legal questions"""
        return f"""Legal Context:
{context}

Question: {question}

Answer Requirements:
1. Provide specific references to South African law
2. Cite exact sections from relevant Acts
3. For military questions, reference Defence Act and Military Discipline Act
4. Include recent precedents if available
5. Provide step-by-step procedures where applicable
6. Detect the language used by the user and answer fully in that same language
7. Supported language preference includes these South African official languages: {SUPPORTED_LANGUAGE_NAMES}
8. Keep Act names and section numbers legally precise even if the rest of the answer is translated"""

    def _build_officer_prompt(self, question: str, context: str, language: Dict[str, str]) -> str:
        """Construct specialized prompt for officer questions"""
        return f"""Military Officer Question:
{question}

Legal Context:
{context}

Required Answer Format:
1. Direct answer first
2. Cite sections from:
   - Defence Act (No. 42 of 2002)
   - Military Discipline Supplementary Measures Act
   - Criminal Procedure Act
3. Include 2023-2025 precedents
4. Step-by-step procedures
5. Special considerations for senior officers
6. Answer entirely in {language['name']} because that is the user's language
7. Keep legal citations, section numbers, and Act names precise"""

    def _build_tts_instructions(self, language: Dict[str, str]) -> str:
        return (
            f"Speak in {language['name']} with a warm, natural, professional tone. "
            "Sound human, calm, clear, and reassuring. "
            "Avoid sounding robotic, exaggerated, or overly dramatic. "
            "Read legal citations clearly and pace the answer for easy listening."
        )

    def _enhance_answer(self, answer: str, question: str, language: Dict[str, str]) -> str:
        """Improve answer formatting"""
        if self._is_military_officer_question(question):
            answer = self._enhance_officer_answer(answer, question, language)
        return answer.replace("Section", "\nSection").strip()

    def _enhance_officer_answer(self, answer: str, question: str, language: Dict[str, str]) -> str:
        """Add military-specific information to answer"""
        enhancements = []
        question_lower = question.lower()
        arrest_terms = ['arrest', 'arresteer', 'ukubopha', 'ukubanjwa', 'go swara', 'bopha']
        if any(term in question_lower for term in arrest_terms):
            enhancements.append(
                "\n\nArrest Procedures:\n"
                "- Defence Act Section 104 (Military police powers)\n"
                "- Criminal Procedure Act Section 40 (Peace officer powers)\n"
                "- 2025 Example: Crime Intelligence chief arrest"
            )
        enhancements.append(
            "\n\nRecent Cases:\n"
            "- 2025: Senior SANDF officers disciplined\n"
            "- 2024: SAPS generals suspended"
        )
        return answer + ''.join(enhancements)

    def _fallback_response(self, question: str, language: Dict[str, str]) -> str:
        """Provide fallback when system is unavailable"""
        if self._is_military_officer_question(question):
            return (
                f"{self._localize('military_officer_procedures', language)}\n\n"
                f"1. {self._localize('all_officers_subject', language)}\n"
                f"2. {self._localize('reference_label', language)}\n"
                "   - Defence Act Sections 20-29\n"
                "   - Criminal Procedure Act Section 40\n\n"
                f"{self._localize('recent_example', language)}"
            )
        return self._localize('system_unavailable', language)

    def _timeout_response(self, question: str, language: Dict[str, str]) -> str:
        """Handle timeout cases"""
        return self._fallback_response(question, language)

    def _api_error_response(self, question: str, language: Dict[str, str]) -> str:
        """Handle API errors"""
        return self._fallback_response(question, language)

    def _localize(self, message_key: str, language: Dict[str, str]) -> str:
        code = language['code']
        translations = {
            'system_unavailable': {
                'en': 'System temporarily unavailable. Please try again later.',
                'af': 'Die stelsel is tydelik onbeskikbaar. Probeer asseblief later weer.',
                'zu': 'Uhlelo alutholakali okwamanje. Sicela uzame futhi ngokuhamba kwesikhathi.',
                'xh': 'Inkqubo ayifumaneki okwethutyana. Nceda uzame kwakhona kamva.',
                'st': 'Sisteme ha e fumanehe ka nakwana. Ka kopo leka hape hamorao.',
                'tn': 'Sisteme ga e bonagale ka nakwana. Tsweetswee leka gape moragonyana.',
                'nso': 'Sisteme ga e hwetšagale ga bjale. Hle leka gape ka morago.',
                'ts': 'Sisiteme a yi kumeki swa xinkarhana. Hi kombela u tlhela u ringeta endzhaku.',
                've': 'Sisiteme a i wanali zwino. Ri humbela uri ni dovhe ni lingedze nga murahu.',
                'nr': 'Ihlelo alifumaneki okwesikhatjhana. Sibawa uzame godu ngemva kwesikhathi.',
                'ss': 'Luhlelo alutfolakali okwamanje. Uyacelwa kutsi uphindze utame emuva kwesikhashana.'
            },
            'military_officer_procedures': {
                'en': 'Military Officer Procedures:',
                'af': 'Prosedures vir Militêre Offisiere:',
                'zu': 'Izinqubo Zesikhulu Sezempi:',
                'xh': 'Iinkqubo Zegosa Lomkhosi:',
                'st': 'Mekgwa ya Molaodi wa Sesole:',
                'tn': 'Mekgwa ya Moofisiri wa Sesole:',
                'nso': 'Mekgwa ya Mošomi wa Sesole:',
                'ts': 'Maendlelo ya Nandza wa Vusirheleri:',
                've': 'Mitele ya Muhasho wa Mmbi:',
                'nr': 'Iindlela Zephoyisa Lezempi:',
                'ss': 'Tinqubo Tephoyisa Letempi:'
            },
            'all_officers_subject': {
                'en': 'All officers remain subject to standard arrest procedures.',
                'af': 'Alle offisiere bly onderhewig aan gewone arrestasieprosedures.',
                'zu': 'Wonke amasosha aphezulu asabophezeleke ezinqubweni ezijwayelekile zokubopha.',
                'xh': 'Onke amagosa asahleli ephantsi kweenkqubo eziqhelekileyo zokubanjwa.',
                'st': 'Bohle balaodi ba ntse ba tlamehile mekgoeng e tlwaelehileng ya tshwaro.',
                'tn': 'Batlankedi botlhe ba santse ba laolwa ke ditsamaiso tse di tlwaelegileng tsa go tshwara.',
                'nso': 'Bahlankedi bohle ba sa le ka fase ga mekgwa ya tlwaelo ya go swara.',
                'ts': 'Vatirhela hinkwavo va ha landzelela maendlelo ya ntolovelo ya ku khoma.',
                've': 'Vhahasho vhoṱhe vha kha ḓi tevhela maitele a u fara o ḓoweleaho.',
                'nr': 'Boke abaphathi basesengaphasi kweendlela ezijayelekileko zokubopha.',
                'ss': 'Tindvuna tonkhe tisahleli ngaphasi kwetinqubo letijwayelekile tekubopha.'
            },
            'reference_label': {
                'en': 'Reference:',
                'af': 'Verwysing:',
                'zu': 'Izinkomba:',
                'xh': 'Isalathiso:',
                'st': 'Tshupiso:',
                'tn': 'Tshupetso:',
                'nso': 'Tšhupetšo:',
                'ts': 'Nkombekelo:',
                've': 'Tsumbanḓila:',
                'nr': 'Isiboniso:',
                'ss': 'Sikhombiso:'
            },
            'recent_example': {
                'en': 'Recent example: 2025 arrests of senior officers',
                'af': 'Onlangse voorbeeld: 2025-arrestasies van senior offisiere',
                'zu': 'Isibonelo sakamuva: ukuboshwa kwezikhulu eziphezulu ngo-2025',
                'xh': 'Umzekelo wakutshanje: ukubanjwa kwamagosa aphezulu ngo-2025',
                'st': 'Mohlala wa moraorao: ho tshwarwa ha balaodi ba baholo ka 2025',
                'tn': 'Sekao sa bosheng: go tshwarwa ga batlankedi ba bagolo ka 2025',
                'nso': 'Mohlala wa bjale: go swarwa ga bahlankedi ba bagolo ka 2025',
                'ts': 'Xikombiso xa sweswinyana: ku khomiwa ka vatirhela lavakulu hi 2025',
                've': 'Tsumbo ya zwenezwino: u farwa ha vhahasho vhahulwane nga 2025',
                'nr': 'Isibonelo sanamhlanjesi: ukubotjhwa kwabaphathi abakhulu ngo-2025',
                'ss': 'Sibonelo sakamuva: kuboshwa kwetikhulu letiphezulu nga-2025'
            }
        }
        return translations.get(message_key, {}).get(code, translations.get(message_key, {}).get('en', ''))