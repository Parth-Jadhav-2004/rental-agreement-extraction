"""Muse Spark chat-completions client."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from src.config import (
    API_KEY_ENV,
    BASE_URL,
    MAX_COMPLETION_TOKENS,
    MODEL,
    PROMPT_CACHE_KEY,
    REASONING_EFFORT,
    REQUEST_TIMEOUT_SECONDS,
    ROOT,
    SEED,
)
from src.schema import AgreementExtraction


class ExtractorError(RuntimeError):
    pass


def build_client() -> OpenAI:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise ExtractorError(
            f"Set {API_KEY_ENV} to a Meta Model API key before extracting documents."
        )
    return OpenAI(base_url=BASE_URL, api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)


def complete(client: OpenAI, messages: list[dict]) -> AgreementExtraction:
    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=messages,
        response_format=AgreementExtraction,
        seed=SEED,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        extra_body={
            "reasoning_effort": REASONING_EFFORT,
            "prompt_cache_key": PROMPT_CACHE_KEY,
        },
    )
    choice = response.choices[0]
    message = choice.message
    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ExtractorError(f"Model refused the request: {refusal}")
    parsed = message.parsed
    if parsed is None:
        content = message.content or ""
        if not content.strip():
            raise ExtractorError(
                f"Model returned empty content (finish_reason={choice.finish_reason})."
            )
        parsed = AgreementExtraction.model_validate_json(content)
    return parsed
