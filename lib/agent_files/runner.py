"""The replay runtime (build spec §5): init, once, check, watch."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
import threading
import time

from . import assemble, config as cfgmod, fsutil, git
from . import thread as T
from .backends import BackendError, Cancelled, Control, cost_usd, select

_warned: set = set()
_log_lock = threading.Lock()


def log(thread_id: str, event: str, detail: str = "") -> None:
    line = f"{fsutil.iso_now()} {thread_id or '-'} {event} {detail}".rstrip()
    with _log_lock:
        print(line, file=sys.stderr, flush=True)
        try:
            with open(os.path.join(fsutil.state_dir(), "run.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def warn_once(key: str, thread_id: str, msg: str) -> None:
    if key not in _warned:
        _warned.add(key)
        log(thread_id, "warn", msg)


# ---- init -------------------------------------------------------------------

GITIGNORE = "threads/**/status\nthreads/**/seen\nthreads/**/STOP\nthreads/**/last_turn\nthreads/_observed/\n"
DEFAULT_AGENT = """---
model: null
---
You are a helpful, concise assistant. The conversation is a plain-text file the user can edit
at any point; treat the transcript you are shown as the truth.
"""
JOURNAL = """## 2026-11-02
- Used it for:
- Used instead (Claude app / plain TUI), and why:
- Worst friction:
- Forks today: <thread> — helped | hurt | neutral — why
- Searches whose result I used: <pattern> → <thread>
- Read threads in: Neovim | browser view | Warp/other viewer   (view-layer §6)
"""


def init(root: str) -> None:
    os.makedirs(root, exist_ok=True)
    git.init(root)
    created = []
    def put(rel, text):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            return
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        created.append(rel)
    put(".gitignore", GITIGNORE)
    put("config.toml", cfgmod.CONFIG_TEMPLATE)
    put("agents/default.md", DEFAULT_AGENT)
    put("trial/journal.md", JOURNAL)
    put("trial/searches.log", "")
    os.makedirs(os.path.join(root, "threads"), exist_ok=True)
    keep = os.path.join(root, "threads", ".gitkeep")
    if not os.path.exists(keep):
        open(keep, "w").close()
        created.append("threads/.gitkeep")
    if created:
        git.run(root, "add", "-A")
        git.run(root, "commit", "-q", "-m", "init")
    print(f"initialised {root}" if created else f"{root} already initialised")


# ---- helpers ----------------------------------------------------------------

def thread_dir(root: str, tid: str) -> str:
    return os.path.join(root, "threads", *tid.split("/"))


def load_agent(root: str, name: str):
    p = os.path.join(root, "agents", f"{name}.md")
    try:
        with open(p, encoding="utf-8") as f:
            return assemble.split_frontmatter(f.read())
    except OSError:
        return {}, ""


def resolve_model(th: T.Thread, agent_fm: dict, cfg: dict) -> str:
    return th.frontmatter.get("model") or agent_fm.get("model") or cfg["default_model"]


def spend_today(root: str) -> float:
    total = 0.0
    today = time.strftime("%Y-%m-%d")
    for dirpath, dirnames, files in os.walk(os.path.join(root, "threads")):
        if os.path.basename(dirpath) != "steps":
            continue
        for fn in files:
            if fn.endswith(".response.json"):
                p = os.path.join(dirpath, fn)
                if time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(p))) == today:
                    try:
                        with open(p, encoding="utf-8") as f:
                            total += float(json.load(f).get("cost_usd") or 0)
                    except (OSError, ValueError):
                        pass
    return total


def read_thread(root: str, tid: str) -> T.Thread:
    return T.parse_file(os.path.join(thread_dir(root, tid), "thread.md"))


def is_direct(th: T.Thread) -> bool:
    return th.frontmatter.get("runtime") == "direct"


def pending(root: str, tid: str) -> bool:
    d = thread_dir(root, tid)
    try:
        th = read_thread(root, tid)
    except OSError:
        return False
    return is_direct(th) and T.is_send(th, fsutil.read_status(d))


# ---- check ------------------------------------------------------------------

def check(root: str, tid: str) -> int:
    cfg = cfgmod.load(root)
    th = read_thread(root, tid)
    print(f"thread {tid}  status={fsutil.read_status(thread_dir(root, tid))}  pending_send={pending(root, tid)}")
    if th.malformed:
        print("MALFORMED:", th.malformed)
    for w in th.warnings:
        print("warning:", w)
    print(f"{'id':>4}  {'role':<6} {'closed':<12} lines  chars")
    for t in th.turns:
        print(f"t{t.id:<3}  {t.role:<6} {t.closed:<12} {t.start_line+1}-{t.end_line+1}  {len(t.body)}")
    agent_fm, system = load_agent(root, th.frontmatter.get("agent") or "default")
    model = resolve_model(th, agent_fm, cfg)
    req = assemble.build_request(th, system, model, cfg["max_tokens"])
    try:
        _, build, _ = select(model, cfg)
        body = build(req)
    except BackendError as e:
        print("backend error:", e.message)
        body = req
    print(f"model: {model}\n--- request ---")
    print(assemble.dumps(body))
    return 0


# ---- the turn ---------------------------------------------------------------

class Turn:
    """One agent turn, steps 1-13 of §5.2."""

    def __init__(self, root: str, tid: str):
        self.root, self.tid = root, tid
        self.dir = thread_dir(root, tid)
        self.path = os.path.join(self.dir, "thread.md")
        self.cfg = cfgmod.load(root)
        self.expected = ""
        self.sig = None
        self.buf = ""
        self.last_hb = time.time()
        self.conflict = False
        self.stopped = False
        self.out_text: list = []
        self.written_any = False

    # file writes -------------------------------------------------------
    def _stat(self):
        st = os.stat(self.path)
        return (st.st_size, st.st_mtime_ns)

    def read(self) -> str:
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def append(self, text: str) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)
        self.expected += text
        self.sig = self._stat()

    def sync_expected(self) -> None:
        self.expected = self.read()
        self.sig = self._stat()

    def check_foreign(self) -> bool:
        try:
            if self._stat() == self.sig:
                return False
            if self.read() == self.expected:
                self.sig = self._stat()
                return False
        except OSError:
            pass
        return True

    # control callbacks ---------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        if now - self.last_hb >= 60:
            fsutil.write_status(self.dir, "working")
            self.last_hb = now
        if os.path.exists(os.path.join(self.dir, "STOP")):
            self.stopped = True
            raise Cancelled()
        if self.check_foreign():
            self.conflict = True
            raise Cancelled()

    def on_text(self, chunk: str) -> None:
        self.tick()
        self.buf += chunk
        if "\n" not in self.buf:
            return
        head, _, self.buf = self.buf.rpartition("\n")
        lines = head.split("\n")
        self.out_text.append(head + "\n")
        self.append("".join(T.escape_line(l) + "\n" for l in lines))
        self.written_any = True

    # the sequence --------------------------------------------------------
    def run(self) -> None:
        tid, d, cfg = self.tid, self.dir, self.cfg
        th = T.parse_file(self.path)
        you = th.last_turn()
        k = you.id
        agent_fm, system = load_agent(self.root, th.frontmatter.get("agent") or "default")
        model = resolve_model(th, agent_fm, cfg)
        N = T.next_id(th, d)
        rel = os.path.relpath(d, self.root)
        trailers = lambda ev, turn, m: {"Agent-Files-Event": ev, "Agent-Files-Thread": tid,
                                        "Agent-Files-Turn": f"t{turn}", "Agent-Files-Model": m}
        paths = [f"{rel}/thread.md", f"{rel}/steps", f"{rel}/out"]
        fail = None   # (kind, message, http_status)
        info: dict = {}
        started = time.time()
        body = None

        if th.frontmatter.get("context", "replay") == "resume":
            fail = ("config", "context: resume is not supported in M1", None)
        if th.frontmatter.get("grounding"):
            warn_once(f"grounding:{tid}", tid, "grounding is ignored in M1")
        try:
            backend_name, build, stream = select(model, cfg)
        except BackendError as e:
            backend_name, build, stream = "none", None, None
            fail = fail or (e.kind, e.message, e.http_status)
        if not fail:
            cap = float(cfg.get("daily_spend_cap_usd") or 0)
            if cap and spend_today(self.root) >= cap:
                fail = ("spend_cap", f"daily spend cap reached (${cap:.2f})", None)

        git.commit(self.root, paths, f"send {tid} t{k}", trailers("send", k, model))   # step 2
        fsutil.write_status(d, "working")                                                # step 3
        stop = os.path.join(d, "STOP")
        try:   # a STOP left over from before this send must not kill it
            if os.path.getmtime(stop) < os.path.getmtime(self.path):
                os.remove(stop)
        except OSError:
            pass
        os.makedirs(os.path.join(d, "steps"), exist_ok=True)
        if build and not fail:                                                           # step 4
            req = assemble.build_request(th, system, model, cfg["max_tokens"])
            body = build(req)
            rec = {"thread": tid, "turn": f"t{N:04d}", "time": fsutil.iso_now(), "backend": backend_name,
                   "model": model, "request": body}
            fsutil.atomic_write(os.path.join(d, "steps", f"t{N:04d}.request.json"), assemble.dumps(rec) + "\n")
        # step 5
        cur = self.read()
        self.expected = cur
        pre = "" if cur.endswith("\n") else "\n"
        self.sig = self._stat()
        self.append(f"{pre}\n## agent · t{N}\n")
        fsutil.atomic_write(os.path.join(d, "last_turn"), f"t{N}\n")
        log(tid, "start", f"t{N} model={model}")

        if not fail:                                                                     # steps 6-7
            try:
                info = stream(body, Control(self.on_text, self.tick))
            except Cancelled:
                pass
            except BackendError as e:
                fail = (e.kind, e.message, e.http_status)
                info = e.info or {}
            except Exception as e:  # noqa: BLE001 - a backend bug must not wedge the thread
                fail = ("backend", f"{type(e).__name__}: {e}", None)
        # conflict / stop checked once more at the very end
        if not self.conflict and not fail:
            try:
                self.tick()
            except Cancelled:
                pass

        status = "done"
        closing = "END"
        diag: list = []
        if self.conflict:
            os.makedirs(os.path.join(d, "out"), exist_ok=True)
            unsent = self.buf
            fsutil.atomic_write(os.path.join(d, "out", f"t{N:04d}-conflict.txt"),
                                "".join(self.out_text) + unsent)
            status, closing = "interrupted", "END (conflict)"
            with open(self.path, "a", encoding="utf-8") as f:
                f.write("\nEND (conflict)\n")
            log(tid, "conflict", f"t{N} thread.md changed during the turn; output in out/")
        else:
            # flush the last partial line
            if self.buf:
                self.append(T.escape_line(self.buf) + "\n")
                self.out_text.append(self.buf)
                self.buf = ""
            if self.stopped:
                status, closing = "interrupted", "END (interrupted)"
                try:
                    os.remove(os.path.join(d, "STOP"))
                except OSError:
                    pass
            if fail:
                status, closing = "failed", "END (failed)"
                diag.append(f"! error: {fail[1]}".replace("\n", " "))
            elif info.get("stop_reason") == "max_tokens":
                diag.append("! stopped: max_tokens")
            if info.get("served_model") and info["served_model"] != model and backend_name == "anthropic":
                diag.append(f"! served by {info['served_model']}")
            # step 8/9: balance fences, diagnostics, END
            text = self.read()
            agent_start = text.rfind(f"## agent · t{N}\n")
            agent_lines = text[agent_start:].split("\n")[1:]
            fence = T.open_fence_line(agent_lines)
            tail = (fence + "\n") if fence else ""
            if (text + tail) and not (text + tail).endswith("\n\n") and (self.written_any or diag):
                tail += "\n"
            tail += "".join(x + "\n" for x in diag) + closing + "\n"
            self.append(tail)
            self.append(f"\n## you · t{N+1}\n\n")                                       # step 10
            fsutil.atomic_write(os.path.join(d, "last_turn"), f"t{N+1}\n")
        if self.conflict:
            fsutil.atomic_write(os.path.join(d, "last_turn"), f"t{N}\n")

        if info or fail:                                                                  # step 11
            usage = info.get("usage") or {}
            def warn_price(m):
                warn_once(f"price:{m}", tid, f"no [prices] entry for {m}; cost counted as 0")
            served = info.get("served_model") or model
            if "cost_usd" in info:
                cost = float(info["cost_usd"] or 0)
            elif backend_name in ("mock", "openai_compat", "none"):
                cost = 0.0
            else:
                cost = cost_usd(cfg.get("prices", {}), served, usage, warn_price)
            if fail:
                err = {"kind": fail[0], "message": fail[1]}
                if fail[2]:
                    err["http_status"] = fail[2]
                fsutil.atomic_write(os.path.join(d, "steps", f"t{N:04d}.error.json"), assemble.dumps(err) + "\n")
            if info:
                resp = {"backend": backend_name, "served_model": served, "stop_reason": info.get("stop_reason"),
                        "usage": usage, "cost_usd": cost, "duration_ms": int((time.time() - started) * 1000),
                        "chars_out": sum(len(x) for x in self.out_text)}
                if info.get("backend_caveats"):
                    resp["backend_caveats"] = info["backend_caveats"]
                fsutil.atomic_write(os.path.join(d, "steps", f"t{N:04d}.response.json"), assemble.dumps(resp) + "\n")
        fsutil.write_status(d, status)                                                    # step 12
        git.commit(self.root, paths, f"reply {tid} t{N}", trailers("reply", N, model))   # step 13
        log(tid, "done" if status == "done" else status, f"t{N}")


def process(root: str, tid: str) -> bool:
    if not pending(root, tid):
        return False
    try:
        Turn(root, tid).run()
    except Exception as e:  # noqa: BLE001
        log(tid, "error", f"{type(e).__name__}: {e}")
        try:
            fsutil.write_status(thread_dir(root, tid), "failed")
        except OSError:
            pass
    return True


# ---- recovery / watch -------------------------------------------------------

def recover(root: str) -> None:
    for tid, d, bad in fsutil.list_threads(root):
        if bad:
            continue
        try:
            th = T.parse_file(os.path.join(d, "thread.md"))
        except OSError:
            continue
        if not is_direct(th) or fsutil.read_status(d) != "working":
            continue
        last = th.last_turn()
        if last and last.role == "agent" and last.closed == "none" and not th.malformed:
            nid = T.next_id(th, d)
            with open(os.path.join(d, "thread.md"), "a", encoding="utf-8") as f:
                text = open(os.path.join(d, "thread.md"), encoding="utf-8").read()
                f.write(("" if text.endswith("\n") else "\n") + f"END (interrupted)\n\n## you · t{nid}\n\n")
            fsutil.atomic_write(os.path.join(d, "last_turn"), f"t{nid}\n")
        fsutil.write_status(d, "interrupted")
        rel = os.path.relpath(d, root)
        git.commit(root, [f"{rel}/thread.md", f"{rel}/steps", f"{rel}/out"], f"recover {tid}",
                   {"Agent-Files-Event": "recover", "Agent-Files-Thread": tid})
        log(tid, "recover", "closed an interrupted turn")


class Lock:
    def __init__(self):
        self.path = os.path.join(fsutil.state_dir(), "run.lock")
        self.f = open(self.path, "w")

    def acquire(self) -> bool:
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False


def once(root: str, tid: str) -> int:
    lock = Lock()
    if not lock.acquire():
        print("another agent-files-run holds the lock", file=sys.stderr)
        return 2
    recover(root)
    return 0 if process(root, tid) else 3


def watch(root: str) -> int:
    lock = Lock()
    if not lock.acquire():
        print("another agent-files-run holds the lock", file=sys.stderr)
        return 2
    log("-", "watch", f"root={root}")
    recover(root)
    seen: dict = {}
    active: dict = {}
    bad_logged: set = set()
    try:
        while True:
            for tid, d, bad in fsutil.list_threads(root):
                if bad:
                    if tid not in bad_logged:
                        bad_logged.add(tid)
                        log(tid, "ignored", "directory name must match [a-z0-9._-]+")
                    continue
                if tid in active and active[tid].is_alive():
                    continue
                try:
                    st = os.stat(os.path.join(d, "thread.md"))
                except OSError:
                    continue
                sig = (st.st_mtime_ns, st.st_size, fsutil.read_status(d))
                if seen.get(tid) == sig:
                    continue
                seen[tid] = sig
                if pending(root, tid):
                    th = threading.Thread(target=process, args=(root, tid), daemon=True)
                    active[tid] = th
                    th.start()
            time.sleep(0.3)
    except KeyboardInterrupt:
        return 0
