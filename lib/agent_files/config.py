"""config.toml (D12): read with tomllib, defaults merged in."""
from __future__ import annotations

import os
import tomllib

DEFAULTS = {
    "default_model": "claude-opus-5-5",
    "max_tokens": 64000,
    "effort": "medium",
    "daily_spend_cap_usd": 5.0,
    "backends": {
        "anthropic": {"api_key_env": "ANTHROPIC_API_KEY", "fallbacks": True},
        "openai_compat": {},
        "claude_cli": {"command": "claude"},
    },
    "prices": {},
}

CONFIG_TEMPLATE = '''# agent-files configuration. Your file; no program writes it after `init`.
default_model = "claude-opus-5-5"     # used when neither thread nor agent sets model
max_tokens    = 64000                 # streaming, so a high cap is safe
effort        = "medium"              # sent as output_config.effort to Claude models that take it

daily_spend_cap_usd = 5.00            # 0 disables; checked before every send

[backends.anthropic]
api_key_env = "ANTHROPIC_API_KEY"     # unset -> the SDK's own credential chain
fallbacks   = true                    # server-side refusal fallback; the served model is recorded in steps/

[backends.openai_compat.ollama]       # model "ollama/<name>"
base_url = "http://localhost:11434/v1"

[backends.openai_compat.lmstudio]     # model "lmstudio/<name>"
base_url = "http://localhost:1234/v1"

[backends.claude_cli]                 # model "claude-cli" or "claude-cli/<model>"
command = "claude"

# USD per million tokens. Fill in from the provider's price page; unknown models count as 0
# and print a warning once per run.
[prices."claude-opus-5-5"]
input = 4.00
output = 20.00
cache_write = 5.00
cache_read = 0.20
'''


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(root: str) -> dict:
    path = os.path.join(root, "config.toml")
    try:
        with open(path, "rb") as f:
            user = tomllib.load(f)
    except FileNotFoundError:
        user = {}
    return _merge(DEFAULTS, user)
