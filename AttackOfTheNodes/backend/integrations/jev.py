"""Shared Jev HTTP client. One bounded request, no retries or response logging.

Protocol: https://api.typesafe.ai/openapi.json (checked 2026-10-22).
Credentials are headers only; redirects and environment proxy discovery are off.
"""
import asyncio
from dataclasses import dataclass
import json
import math

import aiohttp

API_URL = 'https://api.typesafe.ai/v1/systemone'
MODEL = 'jev-latest'
MAX_RESPONSE_BYTES = 1024 * 1024


class JevError(Exception):
    """A fixed, safe error code; contains no request or response text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ChoiceResult:
    answer: str
    scores: dict[str, float]
    confidence: float
    model: str
    usage: dict[str, int]

    def details(self):
        return {'scores': dict(self.scores), 'confidence': self.confidence,
                'model': self.model, 'usage': dict(self.usage)}


def _probability(value):
    return (type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value))


def _parse_choice(data, criteria, api_key):
    if not isinstance(data, dict):
        raise JevError('provider_error')
    answers = data.get('answers')
    answer = answers.get('pick') if isinstance(answers, dict) else None
    if not isinstance(answer, dict) or answer.get('type') != 'choice':
        raise JevError('provider_error')
    choice = answer.get('choice')
    if not isinstance(choice, str):
        raise JevError('provider_error')
    if choice not in criteria:
        raise JevError('undeclared_choice')
    scores, confidence = answer.get('probabilities'), answer.get('confidence')
    if (not isinstance(scores, dict) or set(scores) != set(criteria)
            or not all(_probability(p) for p in scores.values())
            or not math.isclose(sum(scores.values()), 1, abs_tol=0.01)
            or not _probability(confidence)):
        raise JevError('provider_error')
    usage, model = data.get('usage'), data.get('model')
    if (not isinstance(usage, dict) or not isinstance(model, str)
            or not model or len(model) > 128):
        raise JevError('provider_error')
    counts = {}
    for name in ('input_tokens', 'output_tokens'):
        count = usage.get(name)
        if type(count) is not int or count < 0:
            raise JevError('provider_error')
        counts[name] = count
    # Only selected, typed fields leave this client. Never retain an echoed key.
    model = model.replace(api_key, '[redacted]')
    return ChoiceResult(choice, dict(scores), confidence, model, counts)


async def pick_one(*, text, question, criteria, api_key, timeout):
    """Select one exact criterion through the fixed hosted endpoint."""
    if (not isinstance(api_key, str) or not api_key.strip()
            or any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
        raise JevError('auth_failed')
    payload = {'model': MODEL, 'state': text, 'questions': {
        'pick': {'type': 'choice', 'instructions': question, 'criteria': dict(criteria)}}}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout, ceil_threshold=math.inf),
                                         trust_env=False) as session:
            async with session.post(API_URL, json=payload,
                                    headers={'Authorization': 'Bearer ' + api_key},
                                    allow_redirects=False) as response:
                if response.status in (401, 403):
                    raise JevError('auth_failed')
                if response.status < 200 or response.status >= 300:
                    raise JevError('provider_error')
                raw = bytearray()
                async for chunk in response.content.iter_chunked(8192):
                    if len(raw) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise JevError('provider_error')
                    raw.extend(chunk)
        data = json.loads(raw)
    except (asyncio.TimeoutError, TimeoutError):
        raise JevError('timed_out') from None
    except (aiohttp.ClientError, OSError, ValueError, RecursionError):
        raise JevError('provider_error') from None
    return _parse_choice(data, criteria, api_key)
