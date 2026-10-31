"""Anthropic Messages API backend (§5.4.1)."""
from __future__ import annotations

import os

from .base import BackendError


def build_body(req: dict, cfg: dict) -> dict:
    body = {"model": req["model"], "max_tokens": req["max_tokens"],
            "messages": [{"role": m["role"], "content": m["content"]} for m in req["messages"]],
            "cache_control": {"type": "ephemeral"},
            "output_config": {"effort": cfg.get("effort", "medium")}}
    if req.get("system"):
        body["system"] = req["system"]
    return body


def stream(body: dict, ctl, cfg: dict) -> dict:
    try:
        import anthropic
    except ImportError as e:
        raise BackendError("config", "the anthropic package is not installed (run via `uv run --script`)") from e
    bcfg = cfg["backends"]["anthropic"]
    key_env = bcfg.get("api_key_env")
    kwargs = {}
    if key_env and os.environ.get(key_env):
        kwargs["api_key"] = os.environ[key_env]
    client = anthropic.Anthropic(**kwargs)
    # cache_control and output_config go via extra_body so older SDKs do not reject them.
    extra = {k: body[k] for k in ("cache_control", "output_config") if k in body}
    args = {k: v for k, v in body.items() if k not in extra}
    caveats = []
    if bcfg.get("fallbacks"):
        # The server-side refusal-fallback option and its beta flag must be taken from the current
        # API docs for the model; not wired up until verified (m1-build-spec §5.4.1).
        caveats.append("fallbacks=true is configured but not yet implemented")
    try:
        with client.messages.stream(extra_body=extra, **args) as s:
            for ev in s:
                ctl.tick()
                if ev.type == "content_block_delta" and getattr(ev.delta, "type", "") == "text_delta":
                    ctl.text(ev.delta.text)
            final = s.get_final_message()
    except anthropic.APIStatusError as e:
        raise BackendError("api", str(getattr(e, "message", e)), getattr(e, "status_code", None)) from e
    except anthropic.APIError as e:
        raise BackendError("api", str(e)) from e
    usage = final.usage.model_dump() if hasattr(final.usage, "model_dump") else dict(final.usage)
    info = {"stop_reason": final.stop_reason, "served_model": final.model, "usage": usage, "backend": "anthropic",
            "backend_caveats": caveats}
    if final.stop_reason == "refusal":
        cat = getattr(getattr(final, "stop_details", None), "category", None) or "unspecified"
        raise BackendError("refusal", f"refusal ({cat})", partial_info=info)
    return info
