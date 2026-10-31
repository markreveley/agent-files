"""Thread file format: parser, serializer, escaping, ids, send detection (build spec §4).

The contract shared by every program. Standard library only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

DOT = "·"

RE_CARRY = re.compile(r"^## carry$")
RE_YOU = re.compile(r"^## you (?:·|-|\.) t(\d+)$")
RE_AGENT = re.compile(r"^## agent (?:·|-|\.) t(\d+)$")
RE_NOTE = re.compile(r"^## note · (.+) · t(\d+)$")
RE_END = re.compile(r"^END(?: \((interrupted|failed|conflict)\))?$")
RE_ESCAPABLE = re.compile(r"^\\*(## (carry|you|agent|note)\b|END\b|! )")
RE_UNESCAPABLE = re.compile(r"^\\+(## (carry|you|agent|note)\b|END\b|! )")


def escape_line(line: str) -> str:
    return "\\" + line if RE_ESCAPABLE.match(line) else line


def unescape_line(line: str) -> str:
    return line[1:] if RE_UNESCAPABLE.match(line) else line


def is_fence(line: str) -> bool:
    s = line.strip()
    return s.startswith("```") or s.startswith("~~~")


@dataclass
class Turn:
    role: str                      # you | agent | note
    id: int
    body: str = ""
    closed: str = "none"           # none | ok | interrupted | failed | conflict
    start_line: int = 0            # 0-based index of the header line
    end_line: int = 0              # 0-based index of the last line of the turn (END line if closed)
    source: str | None = None      # notes only
    fence_open: bool = False       # a fence is still open at the end of the body
    raw: list = field(default_factory=list)   # all lines of the turn, header..END
    diagnostics: list = field(default_factory=list)


@dataclass
class Thread:
    frontmatter: dict
    fm_raw: list                   # raw frontmatter lines incl. the --- fences ([] if none)
    pre: list                      # raw lines after frontmatter, before the first section
    carry: str | None
    carry_raw: list
    turns: list
    warnings: list
    malformed: str | None          # reason, or None
    final_newline: bool = True

    def serialize(self) -> str:
        lines = list(self.fm_raw) + list(self.pre) + list(self.carry_raw)
        for t in self.turns:
            lines.extend(t.raw)
        return "\n".join(lines)

    def last_turn(self):
        return self.turns[-1] if self.turns else None

    def max_id(self) -> int:
        return max((t.id for t in self.turns), default=0)


# ---- frontmatter -----------------------------------------------------------

def _scalar(v: str):
    v = v.strip()
    if v in ("null", "~", ""):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return v


def parse_frontmatter(lines: list) -> dict:
    """Flat subset: key: value, key: [a, b], null. Falls back to PyYAML if available."""
    out = {}
    ok = True
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$", ln)
        if not m:
            ok = False
            break
        k, v = m.group(1), (m.group(2) or "").strip()
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            out[k] = [_scalar(x) for x in inner.split(",")] if inner else []
        else:
            out[k] = _scalar(v)
    if ok:
        return out
    try:  # pragma: no cover - optional
        import yaml
        data = yaml.safe_load("\n".join(lines))
        return data if isinstance(data, dict) else {}
    except Exception:
        return out


# ---- parser ----------------------------------------------------------------

def parse(text: str) -> Thread:
    lines = text.split("\n")
    warnings: list = []
    malformed = None
    i = 0
    fm_raw: list = []
    fm: dict = {}
    if lines and lines[0].rstrip() == "---":
        for j in range(1, len(lines)):
            if lines[j].rstrip() == "---":
                fm_raw = lines[: j + 1]
                fm = parse_frontmatter(lines[1:j])
                i = j + 1
                break
    pre: list = []
    carry_raw: list = []
    carry_lines: list = []
    carry_seen = False
    turns: list = []
    cur: Turn | None = None
    section = "pre"            # pre | carry | turn
    in_fence = False
    warned_pre = False

    def finish_turn(t: Turn, end_idx: int, closed: str):
        t.closed = closed
        t.end_line = end_idx
        t.fence_open = False

    body_lines: list = []

    def flush_body(t: Turn):
        b = body_lines[:]
        while b and not b[0].strip():
            b.pop(0)
        while b and not b[-1].strip():
            b.pop()
        t.body = "\n".join(unescape_line(x) for x in b)

    for idx in range(i, len(lines)):
        line = lines[idx]
        stripped = line.rstrip()
        marker = None
        if not in_fence:
            if RE_CARRY.match(stripped):
                marker = ("carry",)
            elif (m := RE_YOU.match(stripped)):
                marker = ("you", int(m.group(1)))
            elif (m := RE_AGENT.match(stripped)):
                marker = ("agent", int(m.group(1)))
            elif (m := RE_NOTE.match(stripped)):
                marker = ("note", int(m.group(2)), m.group(1))
            elif (m := RE_END.match(stripped)) and section == "turn" and cur and cur.closed == "none":
                marker = ("end", m.group(1) or "ok")
        if marker and marker[0] == "carry" and (carry_seen or turns or cur or any(p.strip() for p in pre)):
            warnings.append(f"line {idx+1}: '## carry' is only valid as the first section; treated as text")
            marker = None

        if marker is None:
            if section == "pre":
                pre.append(line)
                if line.strip() and not warned_pre:
                    warnings.append(f"line {idx+1}: text before the first header is ignored")
                    warned_pre = True
            elif section == "carry":
                carry_raw.append(line)
                carry_lines.append(line)
            elif section == "turn":
                cur.raw.append(line)
                if cur.role == "agent" and line.startswith("! ") and not in_fence:
                    cur.diagnostics.append(line[2:])
                else:
                    body_lines.append(line)
            if is_fence(line):
                in_fence = not in_fence
            continue

        kind = marker[0]
        if kind == "end":
            cur.raw.append(line)
            flush_body(cur)
            finish_turn(cur, idx, marker[1])
            turns.append(cur)
            cur = None
            section = "pre_after"
            body_lines = []
            continue

        # a header: close whatever is open
        if section == "carry":
            pass
        if cur is not None:
            if cur.role == "agent":
                malformed = malformed or f"line {idx+1}: header inside unclosed agent turn t{cur.id}"
                flush_body(cur)
                cur.closed = "none"
                cur.end_line = idx - 1
                turns.append(cur)
            else:
                flush_body(cur)
                finish_turn(cur, idx - 1, "ok")
                turns.append(cur)
            cur = None
            body_lines = []
        if kind == "carry":
            carry_seen = True
            section = "carry"
            carry_raw.append(line)
        else:
            cur = Turn(role=kind, id=marker[1], start_line=idx, raw=[line])
            if kind == "note":
                cur.source = marker[2]
            section = "turn"
            body_lines = []
        in_fence = False

    if cur is not None:
        flush_body(cur)
        cur.end_line = len(lines) - 1
        cur.closed = "none"
        cur.fence_open = in_fence
        turns.append(cur)
    if section == "pre_after":
        # stray text between turns (after END, before the next header)
        pass

    carry = None
    if carry_seen:
        b = carry_lines[:]
        while b and not b[0].strip():
            b.pop(0)
        while b and not b[-1].strip():
            b.pop()
        carry = "\n".join(unescape_line(x) for x in b)
    # text between END and the next header was routed to 'pre_after' -> handled below
    return _reattach(Thread(fm, fm_raw, pre, carry, carry_raw, turns, warnings, malformed), lines, i)


def _reattach(th: Thread, lines: list, start: int) -> Thread:
    """Make serialize() byte-identical: stray lines between sections are not in any
    turn's raw; rebuild raw coverage by assigning gaps to the preceding block."""
    # Compute covered ranges.
    blocks = []  # (start_idx, container_list)
    pos = start
    # frontmatter occupies [0, start)
    # pre lines come first, then carry, then turns - but gaps may exist between turns.
    covered = len(th.pre) + len(th.carry_raw)
    cursor = start + covered
    for t in th.turns:
        if t.start_line > cursor:
            # gap lines between previous block and this turn
            gap = lines[cursor:t.start_line]
            if blocks:
                blocks[-1].raw.extend(gap)
            else:
                th.carry_raw.extend(gap) if th.carry is not None else th.pre.extend(gap)
            if gap and any(g.strip() for g in gap):
                th.warnings.append(f"line {cursor+1}: text between turns is ignored")
        cursor = t.start_line + len(t.raw)
        blocks.append(t)
    if cursor < len(lines):
        gap = lines[cursor:]
        if blocks:
            blocks[-1].raw.extend(gap)
            if any(g.strip() for g in gap):
                th.warnings.append(f"line {cursor+1}: text after last turn is ignored")
        elif th.carry is not None:
            th.carry_raw.extend(gap)
        else:
            th.pre.extend(gap)
    return th


def parse_file(path: str) -> Thread:
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


# ---- ids and send detection ------------------------------------------------

def read_last_turn(thread_dir: str) -> int:
    try:
        with open(os.path.join(thread_dir, "last_turn")) as f:
            m = re.search(r"(\d+)", f.read())
            return int(m.group(1)) if m else 0
    except OSError:
        return 0


def next_id(th: Thread, thread_dir: str | None = None) -> int:
    side = read_last_turn(thread_dir) if thread_dir else 0
    return 1 + max(th.max_id(), side)


def is_send(th: Thread, status: str | None) -> bool:
    if th.malformed:
        return False
    last = th.last_turn()
    if last is None or last.role != "you" or last.closed != "ok":
        return False
    if not last.body.strip():
        return False
    if status == "working":
        return False
    if any(t.role == "agent" and t.id > last.id for t in th.turns):
        return False
    return True


def open_fence_line(lines: list) -> str | None:
    """Given the lines of a body, return a fence line that closes an open fence, or None."""
    open_tok = None
    for ln in lines:
        if is_fence(ln):
            if open_tok is None:
                open_tok = ln.strip()[:3]
            else:
                open_tok = None
    return open_tok
