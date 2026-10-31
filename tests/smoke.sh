#!/bin/sh
# Automates smoke tests S1-S5 (docs/m1-build-spec.md §10.2) with the mock backend.
# S6-S11 need a real model / editor / claude session and are done by hand.
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
export AGENT_FILES_ROOT="$TMP/root" XDG_STATE_HOME="$TMP/state"
RUN="python3 $HERE/bin/agent-files-run"
STATS="python3 $HERE/bin/agent-files-stats"
PID=""
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null || true; rm -rf "$TMP"; }
trap cleanup EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }
wait_for() { i=0; while ! eval "$1"; do i=$((i+1)); [ $i -gt 100 ] && fail "timeout: $1"; sleep 0.1; done; }
T="$AGENT_FILES_ROOT/threads"
status() { cat "$T/$1/status" 2>/dev/null || true; }

$RUN init >/dev/null
$RUN watch 2>/dev/null & PID=$!
sleep 0.5

# S1 — new thread, send, streamed reply, two commits
mkdir -p "$T/smoke"
printf -- '---\nagent: default\nruntime: direct\nmodel: mock/echo\ncontext: replay\nkind: main\n---\n\n## you · t1\nwhat is up\nEND\n' > "$T/smoke/thread.md"
wait_for '[ "$(status smoke)" = done ]'
grep -q 'echo: what is up' "$T/smoke/thread.md" || fail "S1 reply missing"
wait_for '[ "$(git -C "$AGENT_FILES_ROOT" log --format=%s | grep -c -E "^(send|reply) smoke")" = 2 ]'
git -C "$AGENT_FILES_ROOT" log -1 --format=%B | grep -q '^Agent-Files-Event: reply' || fail "S1 trailers"
echo "S1 ok"

# S2 — edit above END, send again; stats sees one context edit
python3 - "$T/smoke/thread.md" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read()
t = t.replace("what is up", "what is EDITED").replace("## you · t3\n\n", "## you · t3\nsecond\nEND\n")
open(p, "w").write(t)
PY
wait_for '[ "$(grep -c "^## agent" "$T/smoke/thread.md")" = 2 ] && [ "$(status smoke)" = done ]'
grep -q 'EDITED' "$T/smoke/steps/t0004.request.json" || fail "S2 request lacks the edit"
$STATS --json | grep -q '"threads_with_context_edit": 1' || fail "S2 stats"
echo "S2 ok"

# S3 — fork with carry
mkdir -p "$T/smoke/fork"
printf -- '---\nagent: default\nruntime: direct\nmodel: mock/echo\ncontext: replay\ngrounding: []\nkind: fork\nbranched_at: t2\n---\n\n## carry\nquoted line\n\n## you · t1\nq\nEND\n' > "$T/smoke/fork/thread.md"
wait_for '[ "$(status smoke/fork)" = done ]'
grep -q '<carry>' "$T/smoke/fork/steps/t0002.request.json" || fail "S3 carry"
echo "S3 ok"

# S4 — interrupt
mkdir -p "$T/slow"
printf -- '---\nruntime: direct\nmodel: mock/slow\n---\n\n## you · t1\ngo\nEND\n' > "$T/slow/thread.md"
wait_for 'grep -q "line 3" "$T/slow/thread.md"'
touch "$T/slow/STOP"
wait_for '[ "$(status slow)" = interrupted ]'
grep -q 'END (interrupted)' "$T/slow/thread.md" || fail "S4 END"
[ ! -e "$T/slow/STOP" ] || fail "S4 STOP not removed"
echo "S4 ok"

# S5 — kill the runner mid-turn, restart
mkdir -p "$T/crash"
printf -- '---\nruntime: direct\nmodel: mock/slow\n---\n\n## you · t1\ngo\nEND\n' > "$T/crash/thread.md"
wait_for 'grep -q "line 3" "$T/crash/thread.md"'
kill -9 "$PID"; wait "$PID" 2>/dev/null || true
$RUN watch 2>/dev/null & PID=$!
wait_for '[ "$(status crash)" = interrupted ]'
[ "$(grep -c '^## agent' "$T/crash/thread.md")" = 1 ] || fail "S5 duplicate turn"
echo "S5 ok"
echo "smoke S1-S5 passed"
