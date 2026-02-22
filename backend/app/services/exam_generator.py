"""
Exam generation service.

Uses LLM to generate multiple choice and short answer questions
from document chunks stored in the vector database.
"""

import json
import re
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.exam import Exam, ExamQuestion
from app.services.llm_client import LLMClient
from app.services.vector_store import VectorStore
from app.services.embedder import EmbedderService


class ExamGeneratorService:
    """
    Service for generating exams from study materials.

    Flow:
    1. Retrieve document chunks for the given subject/documents
    2. Build a context string from the most relevant chunks
    3. Send to LLM with structured JSON prompt
    4. Parse the response and create Exam + ExamQuestion records
    """

    # System prompt for exam generation
    EXAM_SYSTEM_PROMPT = """You are an expert exam generator for educational content.
Generate exam questions based ONLY on the provided study material context.

You MUST respond with valid JSON in this exact format:
{
  "title": "Exam title based on the content",
  "description": "Brief description of topics covered",
  "questions": [
    {
      "type": "mc",
      "question": "The question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "B",
      "explanation": "Why B is correct",
      "difficulty": "medium",
      "topic": "Topic name"
    },
    {
      "type": "short_answer",
      "question": "The question text",
      "model_answer": "Expected answer",
      "keywords": ["key1", "key2", "key3"],
      "explanation": "Detailed explanation",
      "difficulty": "medium",
      "topic": "Topic name"
    }
  ]
}

Rules:
- Generate EXACTLY the number of questions requested
- Multiple choice questions MUST have the exact number of options requested
- correct_answer for MC must match one of the option letters (e.g. "A", "B", "C" or "A", "B", "C", "D")
- Vary the difficulty according to the requested level
- Questions should test understanding, not just memorization
- Each question must be directly answerable from the context provided
- Do NOT invent information not present in the context"""

    def __init__(self, db: Session, llm: LLMClient):
        """
        Initialize exam generator.

        Args:
            db: Database session
            llm: LLM client for question generation
        """
        self.db = db
        self.llm = llm

    def _get_chunks_for_subject(
        self,
        subject_id: UUID,
        user_id: UUID,
        document_ids: Optional[List[UUID]] = None,
        max_chunks: int = 20,
        course_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> List[str]:
        """
        Retrieve document chunks for exam generation.

        Supports filtering by subject_id, course_id, or workspace_id.
        Priority: document_ids > subject_id > course_id > workspace_id.
        """
        query = (
            self.db.query(DocumentChunk)
            .join(Document)
            .filter(Document.processing_status == "completed")
        )

        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        elif subject_id:
            query = query.filter(Document.subject_id == subject_id)
        elif course_id:
            query = query.filter(Document.course_id == course_id)
        elif workspace_id:
            query = query.filter(Document.workspace_id == workspace_id)

        chunks = query.order_by(DocumentChunk.chunk_index).limit(max_chunks).all()
        return [chunk.content for chunk in chunks]

    def generate_exam(
        self,
        subject_id: Optional[UUID] = None,
        user_id: UUID = None,
        mc_count: int = 5,
        short_answer_count: int = 3,
        difficulty: str = "medium",
        title: Optional[str] = None,
        document_ids: Optional[List[UUID]] = None,
        course_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        num_options: int = 4,
    ) -> Exam:
        """
        Generate an exam from study materials.

        Args:
            subject_id: Subject to generate exam for
            user_id: User requesting the exam
            mc_count: Number of multiple choice questions
            short_answer_count: Number of short answer questions
            difficulty: Target difficulty (easy, medium, hard)
            title: Custom exam title (optional)
            document_ids: Specific documents to use (optional)

        Returns:
            Exam: Created exam with questions

        Raises:
            ValueError: If no content available for generation
        """
        # Step 1: Get document chunks
        chunks = self._get_chunks_for_subject(
            subject_id, user_id, document_ids,
            course_id=course_id, workspace_id=workspace_id,
        )

        if not chunks:
            raise ValueError(
                "No processed documents found for this subject. "
                "Please upload and wait for document processing to complete."
            )

        # Step 2: Build context
        context = "\n\n---\n\n".join(chunks[:6])  # Limit context size

        # Step 3: Build generation prompt with num_options support
        total_questions = mc_count + short_answer_count
        option_letters = [chr(65 + i) for i in range(num_options)]  # A, B, C or A, B, C, D
        options_str = ", ".join(option_letters)
        prompt = (
            f"## Study Material Context:\n\n{context}\n\n"
            f"## Generation Request:\n"
            f"Generate an exam with exactly {total_questions} questions:\n"
            f"- {mc_count} multiple choice questions with exactly {num_options} options each ({options_str})\n"
            f"- {short_answer_count} short answer questions\n"
            f"- Target difficulty: {difficulty}\n"
            f"- Mix multiple choice questions first, then short answer questions\n"
            f"- IMPORTANT: Each MC question must have exactly {num_options} options, correct_answer must be one of: {options_str}\n"
        )

        if title:
            prompt += f"- Exam title: {title}\n"

        # Step 4: Generate with LLM (with retry for transient failures)
        last_error = None
        for attempt in range(3):
            try:
                raw_response = self.llm.generate_json(
                    prompt=prompt,
                    system_prompt=self.EXAM_SYSTEM_PROMPT,
                    temperature=0.4,
                )
                exam_data = self._parse_exam_response(raw_response)
                break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    import time
                    time.sleep(2 * (attempt + 1))  # Backoff: 2s, 4s
                    continue
                raise ValueError(
                    f"Failed to generate exam after 3 attempts: {str(last_error)}"
                )

        # Step 6: Create database records
        exam = Exam(
            subject_id=subject_id,
            title=title or exam_data.get("title", "Generated Exam"),
            description=exam_data.get("description", ""),
            question_count=total_questions,
            mc_count=mc_count,
            short_answer_count=short_answer_count,
            generated_from_document_ids=[str(d) for d in (document_ids or [])],
        )
        self.db.add(exam)
        self.db.flush()

        # Create question records
        for idx, q_data in enumerate(exam_data.get("questions", [])[:total_questions]):
            question = ExamQuestion(
                exam_id=exam.id,
                question_order=idx + 1,
                question_type=q_data.get("type", "mc"),
                question_text=q_data.get("question", ""),
                options=q_data.get("options"),
                correct_answer=q_data.get("correct_answer"),
                model_answer=q_data.get("model_answer"),
                keywords=q_data.get("keywords"),
                explanation=q_data.get("explanation", ""),
                difficulty=q_data.get("difficulty", difficulty),
                topic=q_data.get("topic", ""),
            )
            self.db.add(question)

        self.db.commit()
        self.db.refresh(exam)

        return exam

    def _parse_exam_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response into exam data.

        Handles various JSON formats including markdown code blocks.

        Args:
            raw_response: Raw LLM output string

        Returns:
            Parsed dictionary with exam data

        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL
        )
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding raw JSON object
        json_match = re.search(r"(\{.*\})", raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Failed to parse exam JSON from LLM response: {raw_response[:300]}..."
        )

    def evaluate_short_answer(
        self,
        question_text: str,
        model_answer: str,
        keywords: List[str],
        user_answer: str,
    ) -> Dict[str, Any]:
        """
        Evaluate a short answer question using LLM.

        Args:
            question_text: The original question
            model_answer: Expected correct answer
            keywords: Key concepts that should appear
            user_answer: Student's submitted answer

        Returns:
            Dict with: is_correct (bool), score (0-10), feedback (str)
        """
        eval_prompt = (
            f"## Question:\n{question_text}\n\n"
            f"## Model Answer:\n{model_answer}\n\n"
            f"## Key Concepts Expected:\n{', '.join(keywords or [])}\n\n"
            f"## Student's Answer:\n{user_answer}\n\n"
            f"## Evaluate the answer and respond with JSON:\n"
        )

        eval_system = """You are a fair exam evaluator. Evaluate the student's answer 
comparing it to the model answer and key concepts.

Respond with valid JSON:
{
  "score": 7.5,
  "is_correct": true,
  "feedback": "Detailed feedback explaining what was good and what could be improved"
}

Rules:
- score: 0-10 scale (0=completely wrong, 10=perfect)
- is_correct: true if score >= 5
- feedback: Be constructive and educational
- Consider partial credit for partially correct answers
- Focus on conceptual understanding, not exact wording"""

        raw = self.llm.generate_json(
            prompt=eval_prompt,
            system_prompt=eval_system,
            temperature=0.2,
        )

        try:
            result = json.loads(raw)
            return {
                "is_correct": result.get("is_correct", False),
                "score": min(10, max(0, float(result.get("score", 0)))),
                "feedback": result.get("feedback", "No feedback available."),
            }
        except (json.JSONDecodeError, ValueError):
            # Fallback: keyword matching
            matched = sum(
                1 for kw in (keywords or []) if kw.lower() in user_answer.lower()
            )
            total_kw = len(keywords) if keywords else 1
            score = (matched / total_kw) * 10
            return {
                "is_correct": score >= 5,
                "score": round(score, 1),
                "feedback": f"Matched {matched}/{total_kw} key concepts.",
            }
