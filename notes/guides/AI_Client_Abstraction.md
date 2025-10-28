# AI Client Abstraction

Overview
--------
This document describes the API, contracts, and test harness for the AI client abstraction used across the backend. The goal is to provide a single, well-documented interface that wraps multiple providers (DeepSeek/OpenRouter, Groq, Gemini).

Contract (2–3 bullets)
- Inputs: provider (string), prompt (str), json_mode (bool), max_tokens (int), temperature (float), stop (list[str]|None)
- Outputs: dict {
    'success': bool,
    'text': str,          # the raw text output
    'json': Optional[dict], # parsed JSON when json_mode True (or repaired)
    'provider': str,
    'metadata': dict,     # provider-specific meta (usage, tokens)
}
- Errors: raise ProviderError or return {'success': False, 'error': 'message'} when unrecoverable

Recommended classes & functions
-------------------------------
- ProviderClient base class (abstract)
  - async generate(prompt, **kwargs) -> dict
  - async close()

- AIClientManager
  - lazy-initializes provider clients
  - routes generate requests
  - manages rate-limit handling & backoff
  - exposes cleanup()

Example: ProviderClient interface
---------------------------------
```python
from abc import ABC, abstractmethod

class ProviderClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, json_mode: bool = False, **kwargs) -> dict:
        pass

    @abstractmethod
    async def close(self):
        pass
```

JSON handling policy
--------------------
- If json_mode=True, the manager should attempt three strategies in order:
  1. Parse the model output as-is.
  2. Run a small repair step (heuristic fixes: trailing commas, improper quotes).
  3. Send a short follow-up prompt asking the model to reformat only the previously returned content as pure JSON (no explanation).
- If all attempts fail, return success=False and include raw text in `text` and repair details in `metadata`.

Testing guidance
-----------------
- Implement `FakeProviderClient` that returns canned responses.
- Add tests for:
  - Successful JSON parse
  - Repairable JSON (missing closing brace)
  - Unrecoverable output
  - Rate-limited provider (simulate retry/backoff)

Telemetry & metrics
-------------------
- Emit events: provider_called, provider_succeeded, provider_failed, provider_repaired
- Record tokens used in `metadata` where available

Security notes
--------------
- Never log raw model outputs to non-secure logs (PII risk). Redact sensitive fields when logging.
- Do not store access keys in source. Use environment variables or secrets manager.
