"""Thin wrapper around the Google Gemini API (google-genai SDK)."""

from typing import TypeVar

from pydantic import BaseModel

from app import config

T = TypeVar("T", bound=BaseModel)

_client = None


class LLMError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(config.GEMINI_API_KEY)


def _get_client():
    global _client
    if not enabled():
        raise LLMError("GEMINI_API_KEY is not configured")
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def generate_json(prompt: str, schema: type[T], temperature: float = 0.1) -> T:
    """Ask Gemini for output that conforms to a Pydantic schema."""
    from google.genai import types

    try:
        response = _get_client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        if isinstance(response.parsed, schema):
            return response.parsed
        return schema.model_validate_json(response.text or "")
    except LLMError:
        raise
    except Exception as exc:  # network, quota, validation...
        raise LLMError(f"Gemini request failed: {exc}") from exc


def generate_text(prompt: str, temperature: float = 0.3) -> str:
    from google.genai import types

    try:
        response = _get_client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return (response.text or "").strip()
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"Gemini request failed: {exc}") from exc
