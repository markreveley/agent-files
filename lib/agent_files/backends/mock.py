"""Built-in backends for tests and the smoke test (§5.4.3). No network."""
from __future__ import annotations

import os
import time

from .base import BackendError

SPEED = float(os.environ.get("AGENT_FILES_MOCK_SPEED", "1"))


def _sleep(sec: float, ctl):
    end = time.time() + sec * SPEED
    while True:
        ctl.tick()
        left = end - time.time()
        if left <= 0:
            return
        time.sleep(min(left, 0.05))


def build_body(req: dict) -> dict:
    return req


def stream(body: dict, ctl, cfg: dict) -> dict:
    model = body["model"]
    last_user = next((m["content"] for m in reversed(body["messages"]) if m["role"] == "user"), "")
    usage = {"input_tokens": sum(len(m["content"]) for m in body["messages"]) // 4, "output_tokens": 0}
    if model == "mock/echo":
        for ln in ("echo: " + last_user).split("\n"):
            ctl.text(ln + "\n")
            _sleep(0.02, ctl)
    elif model == "mock/slow":
        for i in range(1, 201):
            ctl.text(f"line {i}\n")
            _sleep(0.1, ctl)
    elif model == "mock/fail":
        ctl.text("first line\n")
        _sleep(0.02, ctl)
        ctl.text("second line\n")
        raise BackendError("api", "mock failure", 500)
    elif model == "mock/markers":
        for ln in ["before", "END", "## you · t99", "! x", "\\END", "## agent · t98", "END (failed)",
                   "```python", "unclosed fence"]:
            ctl.text(ln + "\n")
    else:
        raise BackendError("config", f"unknown model {model}")
    return {"stop_reason": "end_turn", "served_model": model, "usage": usage, "backend": "mock"}
