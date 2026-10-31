"""Backend plumbing shared by all backends."""
from __future__ import annotations


class Cancelled(Exception):
    """Raised by Control.tick()/text() when the runner wants the stream to stop."""


class BackendError(Exception):
    def __init__(self, kind: str, message: str, http_status: int | None = None, partial_info: dict | None = None):
        super().__init__(message)
        self.kind = kind            # api | refusal | spend_cap | config | backend
        self.message = message
        self.http_status = http_status
        self.info = partial_info or {}


class Control:
    """Callbacks the runner hands to a backend. Both may raise Cancelled."""
    def __init__(self, on_text, on_tick):
        self.text = on_text
        self.tick = on_tick


def cost_usd(prices: dict, model: str, usage: dict, warn=None) -> float:
    p = prices.get(model)
    if not p:
        if warn:
            warn(model)
        return 0.0
    m = 1_000_000.0
    return round((usage.get("input_tokens", 0) * p.get("input", 0)
                  + usage.get("output_tokens", 0) * p.get("output", 0)
                  + (usage.get("cache_creation_input_tokens") or 0) * p.get("cache_write", 0)
                  + (usage.get("cache_read_input_tokens") or 0) * p.get("cache_read", 0)) / m, 6)
