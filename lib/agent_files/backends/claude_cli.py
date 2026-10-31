"""`claude -p` backend (§5.4.2). Draws on the Agent SDK credit; Claude Code adds its own prompt/tools."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading

from .base import BackendError

CAVEATS = ["claude -p wraps the request in Claude Code's own harness; steps/ records what we sent, not the exact model request"]


def render_prompt(req: dict) -> str:
    parts = []
    for m in req["messages"]:
        parts.append(f"[{'you' if m['role'] == 'user' else 'agent'}]\n{m['content']}")
    return "\n\n".join(parts)


def build_body(req: dict, model: str | None) -> dict:
    return {"model": model, "system": req.get("system", ""), "prompt": render_prompt(req)}


def command(cmd: str, body: dict) -> list:
    # Flags verified against `claude --help` (Claude Code CLI): see docs/m1-build-spec.md §5.4.2.
    args = [cmd, "-p", "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--no-session-persistence", "--tools", "", "--setting-sources", "",
            "--disable-slash-commands", "--strict-mcp-config"]
    if body.get("system"):
        args += ["--system-prompt", body["system"]]
    if body.get("model"):
        args += ["--model", body["model"]]
    return args


def stream(body: dict, ctl, cfg: dict) -> dict:
    cmd = cfg["backends"].get("claude_cli", {}).get("command", "claude")
    env = dict(os.environ, AGENT_FILES_RUNNER="1")
    info = {"stop_reason": "end_turn", "served_model": body.get("model") or "claude-cli", "usage": {},
            "backend": "claude_cli", "backend_caveats": CAVEATS}
    with tempfile.TemporaryDirectory() as cwd:
        try:
            p = subprocess.Popen(command(cmd, body), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, cwd=cwd, env=env)
        except OSError as e:
            raise BackendError("backend", f"cannot run {cmd}: {e}") from e
        errbuf = []
        threading.Thread(target=lambda: errbuf.append(p.stderr.read()), daemon=True).start()
        p.stdin.write(body["prompt"])
        p.stdin.close()
        got_text = False
        try:
            for line in p.stdout:
                ctl.tick()
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("type") == "stream_event":
                    d = ev.get("event", {})
                    if d.get("type") == "content_block_delta" and d.get("delta", {}).get("type") == "text_delta":
                        ctl.text(d["delta"]["text"])
                        got_text = True
                elif ev.get("type") == "assistant" and not got_text:
                    for blk in ev.get("message", {}).get("content", []):
                        if blk.get("type") == "text":
                            ctl.text(blk["text"])
                elif ev.get("type") == "result":
                    info["usage"] = ev.get("usage", {}) or {}
                    if "total_cost_usd" in ev:
                        info["cost_usd"] = ev["total_cost_usd"]
                    if ev.get("is_error"):
                        raise BackendError("api", str(ev.get("result", "claude -p error")))
        finally:
            if p.poll() is None:
                p.kill()
            p.wait()
        if p.returncode not in (0, None) and not got_text:
            raise BackendError("backend", f"{cmd} exited {p.returncode}: {''.join(errbuf)[:300]}")
    return info
