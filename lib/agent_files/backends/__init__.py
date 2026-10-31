"""Backend selection by model string (§5.4)."""
from __future__ import annotations

from .base import BackendError, Cancelled, Control, cost_usd  # noqa: F401

MOCKS = ("mock/echo", "mock/slow", "mock/fail", "mock/markers")


def select(model: str, cfg: dict):
    """Return (backend_name, build_body(req)->dict, stream(body, ctl)->info)."""
    if model.startswith("mock/"):
        from . import mock
        if model not in MOCKS:
            raise BackendError("config", f"unknown model {model}")
        return "mock", mock.build_body, lambda b, c: mock.stream(b, c, cfg)
    if model == "claude-cli" or model.startswith("claude-cli/"):
        from . import claude_cli
        name = model.split("/", 1)[1] if "/" in model else None
        return "claude_cli", lambda r: claude_cli.build_body(r, name), lambda b, c: claude_cli.stream(b, c, cfg)
    if model.startswith("claude-"):
        from . import anthropic as ab
        return "anthropic", lambda r: ab.build_body(r, cfg), lambda b, c: ab.stream(b, c, cfg)
    if "/" in model:
        name, _, rest = model.partition("/")
        oc = cfg["backends"].get("openai_compat", {})
        if name in oc:
            from . import openai_compat as ob
            return "openai_compat", lambda r: ob.build_body(r, rest), lambda b, c: ob.stream(b, c, oc[name]["base_url"])
    raise BackendError("config", f"unknown model {model}")
