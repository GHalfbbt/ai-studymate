"""
Unified LLM client with multi-provider support.

Supports Groq (primary), OpenAI (fallback), and Ollama (local).
All providers use OpenAI-compatible API, making switching seamless.
"""

from typing import Optional, Literal
import json
import re
import os

from openai import OpenAI

LLMProvider = Literal["groq", "openai", "ollama"]


class LLMClient:
    """
    Unified interface for multiple LLM providers.

    All providers use the OpenAI-compatible chat completions API.
    Groq is the primary provider (free tier, fast inference with Llama 3.1).

    Usage:
        client = LLMClient(provider="groq")
        response = client.generate(
            "What is RAG?",
            system_prompt="You are a helpful assistant"
        )
    """

    def __init__(
        self,
        provider: LLMProvider = "groq",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize LLM client with specified provider.

        Args:
            provider: LLM provider to use (groq, openai, ollama)
            api_key: API key override (defaults to env var)
            base_url: Base URL override (for custom endpoints)
        """
        self.provider = provider

        if provider == "groq":
            self.client = OpenAI(
                api_key=api_key or os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
            )
            self.default_model = "llama-3.1-8b-instant"

        elif provider == "openai":
            self.client = OpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
            )
            self.default_model = "gpt-4o-mini"

        elif provider == "ollama":
            self.client = OpenAI(
                api_key="ollama",
                base_url=base_url or "http://localhost:11434/v1",
            )
            self.default_model = "llama3:8b"

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Mensaje en español para el desarrollador
        print(
            f"🤖 Cliente LLM inicializado: {provider} "
            f"(modelo: {self.default_model})"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate text completion from LLM.

        Args:
            prompt: User message content
            system_prompt: System instructions (behavior, constraints)
            temperature: Sampling temperature (0=deterministic, 2=creative)
            max_tokens: Maximum tokens to generate
            model: Override default model

        Returns:
            str: Generated text response
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> dict:
        """
        Generate structured JSON output from LLM.

        Used for exam generation, flashcard creation, and other
        tasks requiring structured data output.

        Args:
            prompt: User message with data context
            system_prompt: System instructions specifying JSON format
            temperature: Low temperature for deterministic output
            model: Override default model

        Returns:
            dict: Parsed JSON response

        Raises:
            ValueError: If response cannot be parsed as valid JSON
        """
        # Enhance system prompt to enforce JSON-only output
        enhanced_system = (
            f"{system_prompt}\n\n"
            "You MUST respond with valid JSON only. "
            "No markdown code blocks, no explanations, no extra text. "
            "Just the raw JSON object or array."
        )

        response = self.generate(
            prompt=prompt,
            system_prompt=enhanced_system,
            temperature=temperature,
            model=model,
        )

        # Try parsing JSON directly
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON from markdown code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
            response,
            re.DOTALL,
        )
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Last resort: find any JSON object or array in the response
        json_match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Failed to parse JSON from LLM response. "
            f"Response preview: {response[:200]}..."
        )
