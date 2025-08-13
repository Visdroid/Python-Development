import os
import openai
import logging
import re
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from app.military_law_assistant_config import Config
from typing import Optional, List

config = Config()
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.AI_MODEL
        self.max_tokens = config.MAX_TOKENS
        self.temperature = config.TEMPERATURE
        self.system_prompt = config.SYSTEM_PROMPT
        self.military_keywords = [
            'military', 'defence', 'army', 'soldier', 'navy', 'air force',
            'officer', 'commanding', 'rank', 'court martial', 'disciplinary'
        ]

    def ask_question(self, question: str, context: str) -> str:
        """Handle questions with military law focus and robust error handling"""
        try:
            if not context or "No PDF documents available" in context:
                logger.warning("No context available - using fallback response")
                return self._fallback_response(question)

            if self._is_military_officer_question(question):
                return self._handle_officer_question(question, context)

            prompt = self._build_prompt(question, context)
            
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
                return self._enhance_answer(answer, question)
                
            except TimeoutError:
                logger.error("OpenAI API timeout")
                return self._timeout_response(question)
            except (APIError, APIConnectionError, RateLimitError) as e:
                logger.error(f"OpenAI API error: {str(e)}")
                return self._api_error_response(question)
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return self._fallback_response(question)

    def _is_military_officer_question(self, question: str) -> bool:
        """Check if question relates to military officers"""
        question_lower = question.lower()
        has_military_keywords = any(kw in question_lower for kw in self.military_keywords)
        has_officer_terms = ('officer' in question_lower or 'commanding' in question_lower)
        return has_military_keywords and has_officer_terms

    def _handle_officer_question(self, question: str, context: str) -> str:
        """Special handling for military officer-related questions"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self._build_officer_prompt(question, context)}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
                timeout=20
            )
            base_answer = response.choices[0].message.content
            return self._enhance_officer_answer(base_answer, question)
        except Exception:
            return self._fallback_response(question)

    def _build_prompt(self, question: str, context: str) -> str:
        """Construct prompt for general legal questions"""
        return f"""Legal Context:
{context}

Question: {question}

Answer Requirements:
1. Provide specific references to South African law
2. Cite exact sections from relevant Acts
3. For military questions, reference Defence Act and Military Discipline Act
4. Include recent precedents if available
5. Provide step-by-step procedures where applicable"""

    def _build_officer_prompt(self, question: str, context: str) -> str:
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
5. Special considerations for senior officers"""

    def _enhance_answer(self, answer: str, question: str) -> str:
        """Improve answer formatting"""
        if self._is_military_officer_question(question):
            answer = self._enhance_officer_answer(answer, question)
        return answer.replace("Section", "\nSection").strip()

    def _enhance_officer_answer(self, answer: str, question: str) -> str:
        """Add military-specific information to answer"""
        enhancements = []
        if 'arrest' in question.lower():
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

    def _fallback_response(self, question: str) -> str:
        """Provide fallback when system is unavailable"""
        if self._is_military_officer_question(question):
            return (
                "Military Officer Procedures:\n\n"
                "1. All officers subject to standard arrest procedures\n"
                "2. Reference:\n"
                "   - Defence Act Sections 20-29\n"
                "   - Criminal Procedure Act Section 40\n\n"
                "Recent example: 2025 arrests of senior officers"
            )
        return "System temporarily unavailable. Please try again later."

    def _timeout_response(self, question: str) -> str:
        """Handle timeout cases"""
        return self._fallback_response(question)

    def _api_error_response(self, question: str) -> str:
        """Handle API errors"""
        return self._fallback_response(question)