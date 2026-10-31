"""Atomic writes, root discovery, thread discovery, status files."""
from __future__ import annotations

import os
import re
import time

SLUG_RE = re.compile(r"^[a-z0-9._-]+$")


def default_root() -> str:
    return os.path.abspath(os.path.expanduser(os.environ.get("AGENT_FILES_ROOT") or "~/agent-files"))


def check_root(root: str) -> None:
    """D1: refuse to run when the root is actually the code checkout."""
    if os.path.isfile(os.path.join(root, "bin", "agent-files-run")):
        raise SystemExit(f"error: {root} contains bin/agent-files-run — that is the code checkout, not the data root.\n"
                         "Set AGENT_FILES_ROOT to a different directory (default ~/agent-files).")


def atomic_write(path: str, text: str) -> None:
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def state_dir() -> str:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    d = os.path.join(base, "agent-files")
    os.makedirs(d, exist_ok=True)
    return d


def read_status(thread_dir: str) -> str | None:
    try:
        with open(os.path.join(thread_dir, "status"), encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def write_status(thread_dir: str, status: str) -> None:
    atomic_write(os.path.join(thread_dir, "status"), status + "\n")


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def list_threads(root: str, include_observed: bool = False):
    """Yield (thread_id, dir, bad) for every dir under threads/ containing thread.md.
    `bad` is True when a path segment violates the slug rule."""
    base = os.path.join(root, "threads")
    for dirpath, dirnames, filenames in os.walk(base):
        rel = os.path.relpath(dirpath, base)
        if rel == "." :
            dirnames[:] = [d for d in dirnames if include_observed or d != "_observed"]
            continue
        if "thread.md" in filenames:
            segs = rel.split(os.sep)
            bad = not all(SLUG_RE.match(s) for s in segs) and segs[0] != "_observed"
            yield "/".join(segs), dirpath, bad
        dirnames[:] = [d for d in dirnames if d not in ("steps", "out")]
