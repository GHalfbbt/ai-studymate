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
    EXAM_SYSTEM_PROMPT = """You are an expert exam generator. You ONLY output valid JSON. No markdown, no explanations, no text before or after the JSON.

CRITICAL: Your entire response must be a single JSON object. Do NOT write any text outside the JSON. Do NOT use markdown formatting. Do NOT say "Here are the questions" or anything similar.

Output this exact JSON structure:
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
- Your ENTIRE response must be ONLY the JSON object above, nothing else
- Generate EXACTLY the number of questions requested
- Multiple choice questions MUST have the exact number of options requested
- correct_answer for MC must match one of the option letters (e.g. "A", "B", "C" or "A", "B", "C", "D")
- Vary the difficulty according to the requested level
- Questions should test understanding, not just memorization
- Each question must be directly answerable from the context provided
- Do NOT invent information not present in the context
- REMEMBER: Output ONLY valid JSON, no other text"""

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

        # Detect if using Ollama (small local model) — use a simpler, more explicit prompt
        is_ollama = self.llm.active_provider == "ollama"

        if is_ollama:
            # Simplified prompt for small local models that struggle with complex JSON
            prompt = self._build_ollama_prompt(
                context=context,
                mc_count=mc_count,
                short_answer_count=short_answer_count,
                num_options=num_options,
                difficulty=difficulty,
                title=title,
            )
        else:
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

            prompt += "\nREMEMBER: Respond with ONLY a valid JSON object. No markdown, no explanations, no text before or after the JSON.\n"

        # Step 4: Generate with LLM (with retry for transient failures)
        last_error = None
        for attempt in range(3):
            try:
                raw_response = self.llm.generate_json(
                    prompt=prompt,
                    system_prompt=self.EXAM_SYSTEM_PROMPT,
                    temperature=0.4,
                )
                exam_data = self._parse_exam_response(raw_response, mc_count=mc_count, short_answer_count=short_answer_count, num_options=num_options)
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

    def _build_ollama_prompt(
        self,
        context: str,
        mc_count: int,
        short_answer_count: int,
        num_options: int,
        difficulty: str,
        title: Optional[str] = None,
    ) -> str:
        """
        Build a simplified, very explicit prompt for Ollama/small local models.

        Small models (3B-7B) struggle with complex JSON structures.
        This prompt uses a concrete example with fewer instructions
        to maximize the chance of getting valid JSON output.
        """
        option_letters = [chr(65 + i) for i in range(num_options)]
        options_str = ", ".join(option_letters)

        # Build a concrete example with the exact number of options requested
        example_options = [f'"Option {chr(65+i)}"' for i in range(num_options)]
        example_options_str = ", ".join(example_options)

        # Limit context for small models (they have smaller context windows)
        limited_context = context[:3000]

        prompt = f"""Based on this text, create a JSON exam.

Text:
{limited_context}

Create exactly {mc_count} multiple choice questions and {short_answer_count} short answer questions.
Difficulty: {difficulty}

Reply with ONLY this JSON (no other text):
{{"title": "{title or 'Exam'}","description": "Exam questions","questions": ["""

        # Add MC example
        if mc_count > 0:
            prompt += f"""
{{"type": "mc", "question": "Your question here?", "options": [{example_options_str}], "correct_answer": "{option_letters[0]}", "explanation": "Why correct", "difficulty": "{difficulty}", "topic": "Topic"}}"""

        # Add short answer example
        if short_answer_count > 0:
            if mc_count > 0:
                prompt += ","
            prompt += f"""
{{"type": "short_answer", "question": "Your question here?", "model_answer": "The answer", "keywords": ["key1", "key2"], "explanation": "Explanation", "difficulty": "{difficulty}", "topic": "Topic"}}"""

        prompt += """
]}}

IMPORTANT: Generate real questions from the text above. Each MC question needs """ + str(num_options) + f""" options ({options_str}). Output ONLY valid JSON."""

        return prompt

    def _parse_exam_response(self, raw_response: str, mc_count: int = 0, short_answer_count: int = 0, num_options: int = 4) -> Dict[str, Any]:
        """
        Parse LLM response into exam data.

        Tries multiple strategies:
        1. Direct JSON parse
        2. Extract JSON from markdown code blocks
        3. Find raw JSON object in text
        4. Fallback: parse plain-text/markdown questions into JSON structure
        5. Post-process: enforce correct question types based on request

        Args:
            raw_response: Raw LLM output string
            mc_count: Expected number of MC questions (for post-processing)
            short_answer_count: Expected number of short answer questions
            num_options: Expected number of options per MC question

        Returns:
            Parsed dictionary with exam data

        Raises:
            ValueError: If all parsing strategies fail
        """
        result = None

        # Strategy 1: Direct JSON parse
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code block
        if not result:
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL
            )
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Strategy 3: Find raw JSON object in text
        if not result:
            json_match = re.search(r"(\{.*\})", raw_response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Strategy 3b: Truncated JSON repair — Ollama often returns incomplete JSON
        # that was cut off mid-stream due to max_tokens limit
        if not result:
            repaired = self._repair_truncated_json(raw_response)
            if repaired:
                print(f"⚠️ Repaired truncated JSON from LLM response ({len(repaired.get('questions', []))} questions recovered)")
                result = repaired

        # Strategy 4: Fallback — parse plain-text questions from markdown/text
        if not result:
            parsed = self._parse_plain_text_exam(raw_response)
            if parsed and parsed.get("questions"):
                print(f"⚠️ Used plain-text fallback parser for exam generation ({len(parsed['questions'])} questions)")
                result = parsed

        if not result:
            raise ValueError(
                f"Failed to parse exam JSON from LLM response: {raw_response[:300]}..."
            )

        # Post-processing: fix question types if the LLM got them wrong
        result = self._fix_question_types(result, mc_count, short_answer_count, num_options)

        return result

    def _fix_question_types(self, data: Dict[str, Any], mc_count: int, short_answer_count: int, num_options: int) -> Dict[str, Any]:
        """
        Post-process parsed exam data to ensure question types match the request.

        Small models often:
        - Mark all questions as "short_answer" even when they have options
        - Generate MC questions without proper options array
        - Mix up question types

        This method fixes those issues based on the actual content of each question.
        """
        questions = data.get("questions", [])
        if not questions:
            return data

        # First pass: detect actual question type from content (not from LLM's "type" field)
        for q in questions:
            has_options = isinstance(q.get("options"), list) and len(q.get("options", [])) >= 2
            has_correct_letter = (
                q.get("correct_answer", "")
                and len(q.get("correct_answer", "").strip()) == 1
                and q.get("correct_answer", "").strip().upper() in "ABCDEFGH"
            )

            # If it has options array, it's definitely MC regardless of what "type" says
            if has_options:
                q["type"] = "mc"
                # Ensure correct_answer is a letter
                if not has_correct_letter:
                    q["correct_answer"] = "A"
                else:
                    q["correct_answer"] = q["correct_answer"].strip().upper()
                # Pad or trim options to match requested num_options
                while len(q["options"]) < num_options:
                    q["options"].append(f"Option {chr(65 + len(q['options']))}")
                q["options"] = q["options"][:num_options]
            elif q.get("type") == "mc" and not has_options:
                # Marked as MC but no options — convert to short_answer
                q["type"] = "short_answer"
                if not q.get("model_answer"):
                    q["model_answer"] = q.get("correct_answer", "")
                if not q.get("keywords"):
                    q["keywords"] = []

        # Second pass: ensure we have the right count of each type
        mc_questions = [q for q in questions if q["type"] == "mc"]
        sa_questions = [q for q in questions if q["type"] == "short_answer"]

        # If we have too many of one type and not enough of the other,
        # just accept what we got — the LLM generated what it could
        # But reorder: MC first, then short answer
        ordered = mc_questions[:mc_count] + sa_questions[:short_answer_count]

        # If we don't have enough, add remaining questions of any type
        remaining = [q for q in questions if q not in ordered]
        ordered.extend(remaining[:max(0, (mc_count + short_answer_count) - len(ordered))])

        data["questions"] = ordered
        return data

    def _parse_plain_text_exam(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Fallback parser: extract exam questions from plain text / markdown
        when the LLM ignores JSON format instructions (common with Ollama
        and some smaller models).

        Handles formats like:
        - "1. Question text" or "**1.** Question text"
        - "A) Option" or "A. Option" or "a) Option"
        - "Correct answer: B" or "Answer: B"

        Args:
            text: Raw plain-text LLM response

        Returns:
            Dict with title, description, and questions list, or None if parsing fails
        """
        questions = []

        # Split into question blocks by numbered patterns
        # Matches: "1.", "1)", "**1.**", "Question 1:", "Q1.", etc.
        q_blocks = re.split(
            r'(?=(?:^|\n)\s*(?:\*{0,2})(?:Question\s+)?(?:Q)?(\d+)[.):\s])',
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # Alternative: try splitting by double newlines if numbered split didn't work well
        if len(q_blocks) < 2:
            q_blocks = re.split(r'\n\s*\n', text)

        for block in q_blocks:
            block = block.strip()
            if not block or len(block) < 20:
                continue

            # Try to detect if this is a multiple choice question (has A/B/C/D options)
            option_pattern = re.findall(
                r'(?:^|\n)\s*([A-Da-d])[.):\s]\s*(.+?)(?=\n\s*[A-Da-d][.):\s]|\n\s*(?:Correct|Answer|Explanation)|$)',
                block,
                re.DOTALL,
            )

            if len(option_pattern) >= 3:
                # This is a multiple choice question
                q_data = self._parse_mc_block(block, option_pattern)
                if q_data:
                    questions.append(q_data)
            else:
                # Check if it looks like a short answer question
                q_data = self._parse_short_answer_block(block)
                if q_data:
                    questions.append(q_data)

        if not questions:
            return None

        return {
            "title": "Generated Exam",
            "description": "Auto-generated from study materials",
            "questions": questions,
        }

    def _parse_mc_block(self, block: str, options: list) -> Optional[Dict[str, Any]]:
        """Parse a multiple choice question from a text block."""
        # Extract question text (everything before the first option)
        first_option_match = re.search(r'(?:^|\n)\s*[A-Da-d][.):\s]', block)
        if not first_option_match:
            return None

        question_text = block[:first_option_match.start()].strip()
        # Clean up question text: remove leading number, asterisks, etc.
        question_text = re.sub(r'^[\s\d*.):#]+', '', question_text).strip()
        question_text = re.sub(r'^\[.*?\]\s*', '', question_text).strip()  # Remove [MC] tags
        question_text = re.sub(r'^\*+\s*', '', question_text).strip()

        if not question_text or len(question_text) < 10:
            return None

        # Build options list
        option_texts = [opt[1].strip().rstrip('.') for opt in options]

        # Try to find correct answer
        correct_answer = None
        answer_match = re.search(
            r'(?:Correct\s*(?:answer)?|Answer)\s*[:\s]*\*?\*?([A-Da-d])\b',
            block,
            re.IGNORECASE,
        )
        if answer_match:
            correct_answer = answer_match.group(1).upper()
        else:
            # Try to find answer marked with asterisk or bold
            for opt in options:
                letter = opt[0].upper()
                text = opt[1]
                if '**' in text or '✓' in text or '✔' in text or '(correct)' in text.lower():
                    correct_answer = letter
                    break

        if not correct_answer:
            correct_answer = "A"  # Default fallback

        # Try to find explanation
        explanation = ""
        expl_match = re.search(
            r'(?:Explanation|Why)[:\s]*(.+?)(?=\n\s*\d+[.):]|\Z)',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if expl_match:
            explanation = expl_match.group(1).strip()[:500]

        # Try to find difficulty
        difficulty = "medium"
        diff_match = re.search(r'\[(easy|medium|hard)\]', block, re.IGNORECASE)
        if diff_match:
            difficulty = diff_match.group(1).lower()

        return {
            "type": "mc",
            "question": question_text,
            "options": option_texts[:4],  # Max 4 options
            "correct_answer": correct_answer,
            "explanation": explanation,
            "difficulty": difficulty,
            "topic": "",
        }

    def _parse_short_answer_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a short answer question from a text block."""
        # Extract question text
        question_text = block.strip()
        # Remove leading number/formatting
        question_text = re.sub(r'^[\s\d*.):#]+', '', question_text).strip()

        if not question_text or len(question_text) < 15:
            return None

        # Check if there's an answer/model answer
        model_answer = ""
        answer_match = re.search(
            r'(?:Answer|Model\s*answer|Expected\s*answer)[:\s]*(.+?)(?=\n\s*(?:Explanation|Keywords|\d+[.):])|$)',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if answer_match:
            model_answer = answer_match.group(1).strip()[:500]
            # Remove the answer part from the question
            question_text = block[:answer_match.start()].strip()
            question_text = re.sub(r'^[\s\d*.):#]+', '', question_text).strip()

        # Extract keywords if present
        keywords = []
        kw_match = re.search(r'(?:Keywords?|Key\s*concepts?)[:\s]*(.+?)(?=\n|$)', block, re.IGNORECASE)
        if kw_match:
            keywords = [k.strip() for k in kw_match.group(1).split(',') if k.strip()]

        # Try to find explanation
        explanation = ""
        expl_match = re.search(r'(?:Explanation)[:\s]*(.+?)(?=\n\s*\d+[.):]|\Z)', block, re.IGNORECASE | re.DOTALL)
        if expl_match:
            explanation = expl_match.group(1).strip()[:500]

        difficulty = "medium"
        diff_match = re.search(r'\[(easy|medium|hard)\]', block, re.IGNORECASE)
        if diff_match:
            difficulty = diff_match.group(1).lower()

        if not question_text or len(question_text) < 15:
            return None

        return {
            "type": "short_answer",
            "question": question_text,
            "model_answer": model_answer,
            "keywords": keywords,
            "explanation": explanation,
            "difficulty": difficulty,
            "topic": "",
        }

    def _repair_truncated_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair truncated JSON from Ollama/local models.

        When max_tokens is hit, the JSON gets cut off mid-stream.
        This method tries to:
        1. Find the JSON start
        2. Extract as many complete question objects as possible
        3. Close all open brackets/braces to make it valid

        Args:
            raw: Raw truncated LLM output

        Returns:
            Parsed dict with recovered questions, or None if repair fails
        """
        # Find the start of JSON
        json_start = raw.find('{')
        if json_start == -1:
            return None

        text = raw[json_start:]

        # Try to find complete question objects using regex
        # Match complete JSON objects that look like questions
        question_pattern = re.finditer(
            r'\{\s*"type"\s*:\s*"(mc|short_answer|multiple_choice)"'
            r'.*?"question"\s*:\s*"([^"]+)"'
            r'.*?'
            r'(?:\})',
            text,
            re.DOTALL,
        )

        questions = []
        for match in question_pattern:
            q_text = match.group(0)
            try:
                q_obj = json.loads(q_text)
                questions.append(q_obj)
            except json.JSONDecodeError:
                # Try to repair this individual question object
                repaired_q = self._try_close_json_object(q_text)
                if repaired_q:
                    questions.append(repaired_q)

        if not questions:
            # Alternative: try to extract questions array by finding complete objects
            # between the "questions": [ and the truncation point
            questions_start = text.find('"questions"')
            if questions_start == -1:
                return None

            array_start = text.find('[', questions_start)
            if array_start == -1:
                return None

            array_content = text[array_start + 1:]

            # Find complete objects by tracking brace depth
            depth = 0
            obj_start = None
            for i, ch in enumerate(array_content):
                if ch == '{':
                    if depth == 0:
                        obj_start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and obj_start is not None:
                        obj_str = array_content[obj_start:i + 1]
                        try:
                            q_obj = json.loads(obj_str)
                            if q_obj.get("question") or q_obj.get("question_text"):
                                questions.append(q_obj)
                        except json.JSONDecodeError:
                            pass
                        obj_start = None

        if not questions:
            return None

        # Extract title and description if available
        title = "Generated Exam"
        desc = ""
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', text)
        if title_match:
            title = title_match.group(1)
        desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', text)
        if desc_match:
            desc = desc_match.group(1)

        return {
            "title": title,
            "description": desc,
            "questions": questions,
        }

    def _try_close_json_object(self, partial: str) -> Optional[Dict[str, Any]]:
        """Try to close a partial JSON object by adding missing brackets."""
        # Count open/close braces and brackets
        open_braces = partial.count('{') - partial.count('}')
        open_brackets = partial.count('[') - partial.count(']')

        # If we're inside a string, try to close it
        # Count unescaped quotes
        in_string = False
        for i, ch in enumerate(partial):
            if ch == '"' and (i == 0 or partial[i-1] != '\\'):
                in_string = not in_string

        attempt = partial
        if in_string:
            attempt += '"'

        # Close any open arrays and objects
        attempt += ']' * max(0, open_brackets)
        attempt += '}' * max(0, open_braces)

        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            return None

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
