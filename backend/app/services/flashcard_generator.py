"""
Flashcard generation service.

Uses LLM to extract question-answer pairs from document chunks
for spaced repetition learning.
"""

import json
import re
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.flashcard import Flashcard
from app.services.llm_client import LLMClient


class FlashcardGeneratorService:
    """
    Service for generating flashcards from study materials.

    Flow:
    1. Retrieve document chunks for the given subject/document
    2. Send chunks to LLM with structured prompt
    3. Parse response and create Flashcard records
    """

    FLASHCARD_SYSTEM_PROMPT = """You are an expert flashcard creator for study materials.
Create flashcards that help students memorize and understand key concepts.

You MUST respond with valid JSON in this exact format:
{
  "flashcards": [
    {
      "front": "Clear, concise question or prompt",
      "back": "Complete, accurate answer",
      "difficulty": "medium"
    }
  ]
}

Rules:
- Generate EXACTLY the number of flashcards requested
- Front side: Clear question, definition prompt, or concept to explain
- Back side: Complete answer with enough detail to learn from
- Vary question types: definitions, comparisons, explanations, examples
- difficulty must be one of: "easy", "medium", "hard"
- All content must come from the provided context
- Do NOT invent information not in the context
- Make flashcards progressively test deeper understanding"""

    def __init__(self, db: Session, llm: LLMClient):
        """
        Initialize flashcard generator.

        Args:
            db: Database session
            llm: LLM client for generation
        """
        self.db = db
        self.llm = llm

    def _get_chunks(
        self,
        subject_id: UUID,
        document_id: Optional[UUID] = None,
        max_chunks: int = 15,
    ) -> List[str]:
        """
        Retrieve document chunks for flashcard generation.

        Args:
            subject_id: Subject to get chunks from
            document_id: Optional specific document filter
            max_chunks: Maximum chunks to retrieve

        Returns:
            List of chunk text strings
        """
        query = (
            self.db.query(DocumentChunk)
            .join(Document)
            .filter(
                Document.subject_id == subject_id,
                Document.processing_status == "completed",
            )
        )

        if document_id:
            query = query.filter(Document.id == document_id)

        chunks = query.order_by(DocumentChunk.chunk_index).limit(max_chunks).all()
        return [chunk.content for chunk in chunks]

    def generate_flashcards(
        self,
        subject_id: UUID,
        user_id: UUID,
        count: int = 10,
        document_id: Optional[UUID] = None,
    ) -> List[Flashcard]:
        """
        Generate flashcards from study materials.

        Args:
            subject_id: Subject to generate flashcards for
            user_id: User requesting generation
            count: Number of flashcards to generate (1-50)
            document_id: Specific document to use (optional)

        Returns:
            List of created Flashcard records

        Raises:
            ValueError: If no content available for generation
        """
        # Step 1: Get document chunks
        chunks = self._get_chunks(subject_id, document_id)

        if not chunks:
            raise ValueError(
                "No processed documents found for this subject. "
                "Please upload and wait for document processing to complete."
            )

        # Step 2: Build context
        context = "\n\n---\n\n".join(chunks[:12])

        # Step 3: Build generation prompt
        prompt = (
            f"## Study Material Context:\n\n{context}\n\n"
            f"## Request:\n"
            f"Generate exactly {count} flashcards from this study material.\n"
            f"- Mix easy, medium, and hard difficulty levels\n"
            f"- Cover the most important concepts\n"
            f"- Make each flashcard self-contained (understandable without context)\n"
        )

        # Step 4: Generate with LLM
        raw_response = self.llm.generate_json(
            prompt=prompt,
            system_prompt=self.FLASHCARD_SYSTEM_PROMPT,
            temperature=0.5,
        )

        # Step 5: Parse response
        flashcard_data = self._parse_response(raw_response)

        # Step 6: Create database records
        created = []
        for fc_data in flashcard_data.get("flashcards", [])[:count]:
            flashcard = Flashcard(
                subject_id=subject_id,
                document_id=document_id,
                front=fc_data.get("front", ""),
                back=fc_data.get("back", ""),
                difficulty=fc_data.get("difficulty", "medium"),
            )
            self.db.add(flashcard)
            created.append(flashcard)

        self.db.commit()

        # Refresh all to get IDs
        for fc in created:
            self.db.refresh(fc)

        return created

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response into flashcard data.

        Args:
            raw_response: Raw LLM output string

        Returns:
            Parsed dictionary with flashcards list

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
            f"Failed to parse flashcard JSON from LLM: {raw_response[:300]}..."
        )

    def export_csv(self, subject_id: UUID) -> str:
        """
        Export flashcards as CSV for Anki import.

        Format: front<TAB>back (Anki default import format)

        Args:
            subject_id: Subject to export flashcards from

        Returns:
            CSV string with tab-separated front/back columns
        """
        flashcards = (
            self.db.query(Flashcard)
            .filter(Flashcard.subject_id == subject_id)
            .order_by(Flashcard.created_at)
            .all()
        )

        lines = []
        for fc in flashcards:
            # Escape tabs and newlines for CSV compatibility
            front = fc.front.replace("\t", " ").replace("\n", "<br>")
            back = fc.back.replace("\t", " ").replace("\n", "<br>")
            lines.append(f"{front}\t{back}")

        return "\n".join(lines)

    def update_review(
        self,
        flashcard_id: UUID,
        quality: int,
    ) -> Flashcard:
        """
        Update flashcard after review using simplified SM-2 algorithm.

        Args:
            flashcard_id: Flashcard to update
            quality: Review quality (0-5)
                0: Total blackout
                1: Wrong, but recognized correct answer
                2: Wrong, but easy to recall correct answer
                3: Correct with serious difficulty
                4: Correct with some hesitation
                5: Perfect recall

        Returns:
            Updated Flashcard record
        """
        from datetime import datetime, timedelta

        flashcard = self.db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not flashcard:
            raise ValueError("Flashcard not found")

        # SM-2 ease factor update
        old_ef = flashcard.ease_factor or 2.5
        new_ef = old_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)  # Minimum ease factor

        # Calculate next review interval
        reviews = (flashcard.times_reviewed or 0) + 1
        if quality < 3:
            # Failed review: reset interval
            interval_days = 1
        elif reviews == 1:
            interval_days = 1
        elif reviews == 2:
            interval_days = 3
        else:
            interval_days = int((reviews - 1) * new_ef)

        now = datetime.utcnow()
        flashcard.times_reviewed = reviews
        flashcard.last_reviewed = now
        flashcard.next_review = now + timedelta(days=interval_days)
        flashcard.ease_factor = round(new_ef, 2)

        self.db.commit()
        self.db.refresh(flashcard)

        return flashcard
