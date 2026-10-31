"""Thin git wrapper. Failures are returned, never raised (a git problem never fails a turn)."""
from __future__ import annotations

import os
import subprocess


def run(root: str, *args: str, input: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for k, v in (("GIT_AUTHOR_NAME", "agent-files"), ("GIT_COMMITTER_NAME", "agent-files"),
                 ("GIT_AUTHOR_EMAIL", "agent-files@localhost"), ("GIT_COMMITTER_EMAIL", "agent-files@localhost")):
        env.setdefault(k, v)
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, input=input, env=env)


def init(root: str) -> None:
    if not os.path.isdir(os.path.join(root, ".git")):
        run(root, "init", "-q")


def commit(root: str, paths: list, message: str, trailers: dict | None = None) -> bool:
    """Stage `paths` (relative to root, existing ones only) and commit. Returns True if a commit was made."""
    existing = [p for p in paths if os.path.exists(os.path.join(root, p))]
    if not existing:
        return False
    r = run(root, "add", "-A", "--", *existing)
    if r.returncode != 0:
        return False
    if trailers:
        message += "\n\n" + "\n".join(f"{k}: {v}" for k, v in trailers.items())
    r = run(root, "commit", "-q", "-m", message, "--only", "--", *existing)
    return r.returncode == 0
