"""Thin git wrapper. Failures are returned, never raised (a git problem never fails a turn)."""
from __future__ import annotations

import os
import subprocess
import threading

# `watch` runs each turn on its own thread; unserialised add+commit pairs collide on .git/index.lock.
_commit_lock = threading.Lock()


def run(root: str, *args: str, input: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for k, v in (("GIT_AUTHOR_NAME", "agent-files"), ("GIT_COMMITTER_NAME", "agent-files"),
                 ("GIT_AUTHOR_EMAIL", "agent-files@localhost"), ("GIT_COMMITTER_EMAIL", "agent-files@localhost")):
        env.setdefault(k, v)
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, input=input, env=env)


def init(root: str) -> None:
    if not os.path.isdir(os.path.join(root, ".git")):
        run(root, "init", "-q")


def commit(root: str, paths: list, message: str, trailers: dict | None = None) -> str | None:
    """Stage `paths` (relative to root, existing ones only) and commit them.
    Returns None on success or when there is nothing to commit, else git's error message."""
    existing = [p for p in paths if os.path.exists(os.path.join(root, p))]
    if not existing:
        return None
    if trailers:
        message += "\n\n" + "\n".join(f"{k}: {v}" for k, v in trailers.items())
    with _commit_lock:
        r = run(root, "add", "-A", "--", *existing)
        if r.returncode == 0:
            if run(root, "diff", "--cached", "--quiet", "--", *existing).returncode == 0:
                return None
            r = run(root, "commit", "-q", "-m", message, "--only", "--", *existing)
    if r.returncode == 0:
        return None
    return " ".join((r.stderr or r.stdout).split()) or f"git exited {r.returncode}"
