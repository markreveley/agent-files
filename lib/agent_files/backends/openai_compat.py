"""OpenAI-compatible chat completions (Ollama, LM Studio...)."""
from __future__ import annotations

from .base import BackendError


def build_body(req: dict, model_name: str) -> dict:
    msgs = ([{"role": "system", "content": req["system"]}] if req.get("system") else []) + \
           [{"role": m["role"], "content": m["content"]} for m in req["messages"]]
    return {"model": model_name, "messages": msgs, "max_tokens": req["max_tokens"], "stream": True,
            "stream_options": {"include_usage": True}}


def stream(body: dict, ctl, base_url: str) -> dict:
    try:
        import openai
    except ImportError as e:
        raise BackendError("config", "the openai package is not installed (run via `uv run --script`)") from e
    client = openai.OpenAI(base_url=base_url, api_key="none")
    usage, stop = {}, None
    try:
        for chunk in client.chat.completions.create(**body):
            ctl.tick()
            if getattr(chunk, "usage", None):
                usage = {"input_tokens": chunk.usage.prompt_tokens, "output_tokens": chunk.usage.completion_tokens}
            for ch in chunk.choices or []:
                if ch.delta and ch.delta.content:
                    ctl.text(ch.delta.content)
                if ch.finish_reason:
                    stop = ch.finish_reason
    except openai.APIStatusError as e:
        raise BackendError("api", str(e), e.status_code) from e
    except openai.APIError as e:
        raise BackendError("api", str(e)) from e
    return {"stop_reason": "max_tokens" if stop == "length" else "end_turn", "served_model": body["model"],
            "usage": usage, "backend": "openai_compat", "cost_usd": 0.0}
