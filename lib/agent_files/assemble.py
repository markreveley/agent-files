"""Thread -> provider-neutral request (build spec §5.3). Deterministic."""
from __future__ import annotations

import json
import re

from . import thread as T


def split_frontmatter(text: str):
    """(frontmatter dict, body) for agents/<name>.md."""
    th = T.parse(text)
    n = len(th.fm_raw)
    body = "\n".join(text.split("\n")[n:]) if n else text
    return th.frontmatter, body.strip()


def messages_from(th: T.Thread) -> list:
    msgs = []
    for t in th.turns:
        if t.role not in ("you", "agent"):
            continue
        body = t.body
        if not body.strip():
            continue
        msgs.append({"role": "user" if t.role == "you" else "assistant", "content": body})
    merged = []
    for m in msgs:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n\n" + m["content"]
        else:
            merged.append(dict(m))
    if th.carry:
        for m in merged:
            if m["role"] == "user":
                m["content"] = f"<carry>\n{th.carry}\n</carry>\n\n" + m["content"]
                break
    if merged and merged[0]["role"] == "assistant":
        merged.insert(0, {"role": "user", "content": "(conversation continues)"})
    return merged


def build_request(th: T.Thread, system: str, model: str, max_tokens: int) -> dict:
    req = {"model": model, "max_tokens": max_tokens, "messages": messages_from(th)}
    if system:
        req["system"] = system
    return req


def dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
