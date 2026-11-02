"""Fake `openai` SDK for backend tests: just the surface backends/openai_compat.py uses.

Put tests/fakes on PYTHONPATH. FAKE_SDK_SCENARIO picks the outcome:
end_turn (default) | max_tokens | http_400.
Each call appends one JSON line (the call's arguments) to FAKE_SDK_LOG, if set.
"""
import json
import os
from types import SimpleNamespace as NS


class APIError(Exception):
    pass


class APIStatusError(APIError):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


def _chunks(scenario):
    if scenario == "http_400":
        raise APIStatusError("Error code: 400 - model not found", 400)
    yield NS(usage=None, choices=[NS(delta=NS(content="local "), finish_reason=None)])
    finish = "length" if scenario == "max_tokens" else "stop"
    yield NS(usage=None, choices=[NS(delta=NS(content="reply"), finish_reason=finish)])
    yield NS(usage=NS(prompt_tokens=40, completion_tokens=2), choices=[])


class _Completions:
    def create(self, **kw):
        log = os.environ.get("FAKE_SDK_LOG")
        if log:
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sdk": "openai", **kw}) + "\n")
        return _chunks(os.environ.get("FAKE_SDK_SCENARIO", "end_turn"))


class OpenAI:
    def __init__(self, **kw):
        self.chat = NS(completions=_Completions())
