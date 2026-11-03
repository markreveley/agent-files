"""Fake `anthropic` SDK for backend tests: just the surface backends/anthropic.py uses.

Put tests/fakes on PYTHONPATH. FAKE_SDK_SCENARIO picks the outcome:
end_turn (default) | max_tokens | refusal | http_400 | other_model |
stop_mid_stream (creates the file named by FAKE_SDK_STOP after the first text delta) |
error_mid_stream (raises an overloaded error after the first text delta).
The stream yields message_start (input and cache usage), text deltas and message_delta (output usage).
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
        self.message = message
        self.status_code = status_code


class _Usage(dict):
    def model_dump(self):
        return dict(self)


class _Stream:
    def __init__(self, scenario, model):
        self.scenario, self.model = scenario, model

    def __enter__(self):
        if self.scenario == "http_400":
            raise APIStatusError("invalid_request_error: bad request", 400)
        return self

    def __exit__(self, *exc):
        return False

    def served(self):
        return "claude-other" if self.scenario == "other_model" else self.model

    def __iter__(self):
        start = _Usage(input_tokens=1000, output_tokens=1, cache_creation_input_tokens=200, cache_read_input_tokens=300)
        yield NS(type="message_start", message=NS(model=self.served(), usage=start))
        for i, piece in enumerate(("Hello ", "from the fake.\n## you · t9\nEND")):
            if i == 1 and self.scenario == "stop_mid_stream":
                open(os.environ["FAKE_SDK_STOP"], "w").close()
            if i == 1 and self.scenario == "error_mid_stream":
                raise APIStatusError("overloaded_error: Overloaded", 529)
            yield NS(type="content_block_delta", delta=NS(type="text_delta", text=piece))
        yield NS(type="message_delta", delta=NS(stop_reason=self.stop()), usage=_Usage(output_tokens=500))

    def stop(self):
        return {"max_tokens": "max_tokens", "refusal": "refusal"}.get(self.scenario, "end_turn")

    def get_final_message(self):
        stop = self.stop()
        served = self.served()
        usage = _Usage(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=200, cache_read_input_tokens=300)
        details = NS(category="cyber") if stop == "refusal" else None
        return NS(stop_reason=stop, model=served, usage=usage, stop_details=details)


class _Messages:
    def stream(self, **kw):
        log = os.environ.get("FAKE_SDK_LOG")
        if log:
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sdk": "anthropic", **kw}) + "\n")
        return _Stream(os.environ.get("FAKE_SDK_SCENARIO", "end_turn"), kw.get("model"))


class Anthropic:
    def __init__(self, **kw):
        self.messages = _Messages()
