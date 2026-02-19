"""
LLM client service for AI text generation.

Supports Groq API (primary) with OpenAI-compatible interface.
Used for RAG responses, exam generation, and flashcard creation.
"""

from typing import List, Optional, Dict

from openai import OpenAI

from app.core.config import settings


class LLMClient:
    """
    LLM client using Groq API with OpenAI-compatible SDK.

    Groq provides extremely fast inference for open-source models
    like Llama 3 and Mixtral via their API.
    """

    def __init__(self):
        """Initialize the Groq client."""
        api_key = settings.GROQ_API_KEY
        if not api_key:
            print("⚠️ GROQ_API_KEY not set — LLM features will not work")
            self.client = None
            return

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.default_model = settings.GROQ_MODEL_NAME
        print(f"✅ LLM Client inicializado (Groq - {self.default_model})")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful study assistant.",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: User message / question
            system_prompt: System instruction for the model
            model: Override model name
            temperature: Sampling temperature (0=deterministic, 1=creative)
            max_tokens: Maximum response length

        Returns:
            Generated text response
        """
        if not self.client:
            return "⚠️ LLM not configured. Please set GROQ_API_KEY in .env"

        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    def generate_with_context(
        self,
        question: str,
        context_chunks: List[str],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a RAG response using retrieved context chunks.

        Args:
            question: User's question
            context_chunks: Relevant document excerpts from vector search
            system_prompt: Custom system prompt (optional)

        Returns:
            AI-generated answer grounded in the provided context
        """
        context = "\n\n---\n\n".join(context_chunks)

        rag_system = system_prompt or (
            "You are an AI study assistant. Answer the student's question "
            "based ONLY on the provided context from their study materials. "
            "If the context doesn't contain enough information to answer, "
            "say so clearly. Always be helpful and educational.\n\n"
            "Format your response with clear structure using markdown when appropriate."
        )

        rag_prompt = (
            f"## Context from study materials:\n\n{context}\n\n"
            f"## Student's question:\n\n{question}\n\n"
            f"## Your answer:"
        )

        return self.generate(
            prompt=rag_prompt,
            system_prompt=rag_system,
            temperature=0.3,  # Lower temperature for factual answers
            max_tokens=3000,
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate a JSON response (for exam/flashcard generation).

        Args:
            prompt: The generation prompt
            system_prompt: System instruction emphasizing JSON output

        Returns:
            Raw string response (caller parses JSON)
        """
        if not self.client:
            return '{"error": "LLM not configured"}'

        response = self.client.chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content
