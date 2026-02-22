"""
LLM client service for AI text generation.

Supports multiple providers with automatic fallback:
- Groq (primary, free tier)
- Google Gemini (free tier)
- Ollama (local, unlimited)

Used for RAG responses, exam generation, and flashcard creation.
"""

from typing import List, Optional, Dict

from openai import OpenAI

from app.core.config import settings


class LLMClient:
    """
    Multi-provider LLM client with automatic fallback.

    Provider priority (configurable via LLM_PROVIDER env var):
    1. groq - Fast cloud inference (free tier: 100k tokens/day)
    2. gemini - Google Gemini free tier (generous limits)
    3. ollama - Local inference (unlimited, requires local setup)

    All providers use OpenAI-compatible SDK interface.
    """

    # Provider configurations
    PROVIDERS = {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.3-70b-versatile",
            "json_mode": True,
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "default_model": "gemini-2.0-flash",
            "json_mode": True,
        },
        "ollama": {
            "base_url": "http://host.docker.internal:11434/v1",
            "default_model": "llama3.2",
            "json_mode": False,  # Ollama doesn't always support response_format
        },
    }

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize the LLM client with provider fallback chain.

        Args:
            provider: Force a specific provider. If None or "auto",
                      uses env var LLM_PROVIDER with full fallback chain.
                      If a specific provider name (groq/gemini/ollama),
                      uses ONLY that provider (no fallback).
        """
        self.clients: List[Dict] = []
        self.active_provider: Optional[str] = None
        self._single_provider = False

        # Determine mode: "auto" = fallback chain, specific = single provider
        resolved = provider if provider and provider != "auto" else None
        primary = resolved or settings.LLM_PROVIDER or "groq"

        if resolved:
            # Single provider mode — no fallback
            self._single_provider = True
            provider_order = [resolved]
        else:
            # Auto/fallback mode
            provider_order = self._build_provider_order(primary)

        for prov_name in provider_order:
            client_info = self._init_provider(prov_name)
            if client_info:
                self.clients.append(client_info)

        if self.clients:
            self.active_provider = self.clients[0]["name"]
            print(f"✅ LLM Client initialized: {self.active_provider} ({self.clients[0]['model']})")
            if len(self.clients) > 1:
                fallbacks = [c["name"] for c in self.clients[1:]]
                print(f"   Fallbacks: {' → '.join(fallbacks)}")
        else:
            print("⚠️ No LLM providers configured — LLM features will not work")

    def _build_provider_order(self, primary: str) -> List[str]:
        """Build ordered list of providers to try."""
        all_providers = ["groq", "gemini", "ollama"]
        order = [primary]
        for p in all_providers:
            if p not in order:
                order.append(p)
        return order

    def _init_provider(self, name: str) -> Optional[Dict]:
        """Initialize a single provider, returns None if not configured."""
        config = self.PROVIDERS.get(name)
        if not config:
            return None

        if name == "groq":
            api_key = settings.GROQ_API_KEY
            if not api_key:
                return None
            model = settings.GROQ_MODEL_NAME or config["default_model"]
            return {
                "name": "groq",
                "client": OpenAI(api_key=api_key, base_url=config["base_url"]),
                "model": model,
                "json_mode": config["json_mode"],
            }

        elif name == "gemini":
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                return None
            model = settings.GEMINI_MODEL or config["default_model"]
            return {
                "name": "gemini",
                "client": OpenAI(api_key=api_key, base_url=config["base_url"]),
                "model": model,
                "json_mode": config["json_mode"],
            }

        elif name == "ollama":
            # Ollama is always "available" if configured — it's local
            # We'll try to connect and fail gracefully
            try:
                client = OpenAI(api_key="ollama", base_url=config["base_url"])
                return {
                    "name": "ollama",
                    "client": client,
                    "model": config["default_model"],
                    "json_mode": config["json_mode"],
                }
            except Exception:
                return None

        return None

    def _call_with_fallback(self, call_fn, **kwargs) -> str:
        """
        Execute an LLM call with automatic fallback to next provider.

        Args:
            call_fn: Function that takes (client_info, **kwargs) and returns str

        Returns:
            Generated text response
        """
        last_error = None
        for client_info in self.clients:
            try:
                result = call_fn(client_info, **kwargs)
                # Update active provider if we fell back
                if client_info["name"] != self.active_provider:
                    print(f"🔄 LLM fallback: {self.active_provider} → {client_info['name']}")
                    self.active_provider = client_info["name"]
                return result
            except Exception as e:
                error_str = str(e)
                last_error = e
                # Log the failure
                print(f"⚠️ LLM provider {client_info['name']} failed: {error_str[:200]}")
                # If rate limited, try next provider
                if "429" in error_str or "rate_limit" in error_str.lower():
                    continue
                # For other errors on non-last provider, try next
                if client_info != self.clients[-1]:
                    continue
                raise

        raise last_error or RuntimeError("No LLM providers available")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful study assistant.",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate text from a prompt with automatic provider fallback.

        Args:
            prompt: User message / question
            system_prompt: System instruction for the model
            model: Override model name
            temperature: Sampling temperature (0=deterministic, 1=creative)
            max_tokens: Maximum response length

        Returns:
            Generated text response
        """
        if not self.clients:
            return "⚠️ LLM not configured. Please set GROQ_API_KEY, GEMINI_API_KEY, or configure Ollama."

        def _do_generate(client_info, **kw):
            response = client_info["client"].chat.completions.create(
                model=model or client_info["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        return self._call_with_fallback(_do_generate)

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
            temperature=0.3,
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
        Falls back between providers automatically.

        Args:
            prompt: The generation prompt
            system_prompt: System instruction emphasizing JSON output

        Returns:
            Raw string response (caller parses JSON)
        """
        if not self.clients:
            return '{"error": "LLM not configured"}'

        def _do_json(client_info, **kw):
            create_kwargs = {
                "model": client_info["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": 4000,
            }
            # Only add response_format for providers that support it
            if client_info["json_mode"]:
                create_kwargs["response_format"] = {"type": "json_object"}

            response = client_info["client"].chat.completions.create(**create_kwargs)
            return response.choices[0].message.content

        return self._call_with_fallback(_do_json)

    def get_provider_status(self) -> Dict:
        """
        Get current provider status for debugging/UI display.

        Returns:
            Dict with active provider and available fallbacks
        """
        return {
            "active_provider": self.active_provider,
            "available_providers": [c["name"] for c in self.clients],
            "models": {c["name"]: c["model"] for c in self.clients},
        }
