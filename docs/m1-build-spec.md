# M1 build spec — the first build

> Status: draft · 2026-10-31 · implements [m1-plan.md](m1-plan.md) §3 against [ARCHITECTURE.md](../ARCHITECTURE.md) §4, with steps 0–1 of [view-layer.md](view-layer.md)
> Audience: whoever writes the code. Where this spec and the plan disagree, this spec wins for M1; where it is silent, the plan and the architecture apply.

**Summary.** The first M1 build is four small programs and one Neovim plugin, all reading and writing the same plain-text files: `agent-files-run` (the replay runtime), `agent-files-hook` (observed status for hand-started `claude` sessions), `agent-files-stats` (trial measurement), `agent-files-grep` (logged cross-thread search), and `agents.nvim`, which also makes threads readable in Neovim (view-layer steps 0–1). The optional HTML view (`agent-files-render`, view-layer step 2) is specified there, not here; this spec only fixes how it plugs in (§12). The build is done when the automated tests pass and the smoke test in §10 passes by hand; then the ten-day trial starts. This document pins down everything the plan left open: the exact grammar and parser, turn numbering, escaping, request assembly, backends, git commits, configuration, and the acceptance tests.

## 1. Decisions this spec makes

Things the plan and architecture left open or inconsistent, settled here for M1:

| # | Question | Decision |
|---|---|---|
| D1 | Where does the code live vs. the data root? | Code in this repo; data root at `$AGENT_FILES_ROOT`, default `~/agent-files/`. **Do not clone this repo to `~/agent-files/`** — that path is the data root. Every program refuses to run if the root contains a `bin/agent-files-run` file. |
| D2 | `steps/` file names | `steps/t0002.request.json` (zero-padded to 4 digits, so `ls` sorts). The plan's `tN` is shorthand. |
| D3 | How turn ids are assigned | Global and sequential across both roles in a thread (`you · t1`, `agent · t2`, `you · t3`…). Next id = 1 + max(highest id in `thread.md`, the `last_turn` sidecar). The sidecar stops ids being reused after you delete trailing turns. |
| D4 | Where `## carry` goes in the request | In the first user message, wrapped in `<carry>…</carry>`, before the text of `t1`. Not in the system prompt: carry is quoted material, not instructions. |
| D5 | Thinking blocks in replay | **Never sent back.** Assistant turns are replayed as plain text from the file. Current Claude models reject edited history that carries thinking blocks ("preserved thinking"); text-only history makes edits above `END` safe. Verified by smoke test S7. |
| D6 | How edits above `END` are measured (H1) | Two commits per exchange: a **send** commit (your turn, plus any edits you made) and a **reply** commit (the agent turn). An edit above `END` is a send commit whose diff does more than append below the previous last `END` (§7.2). |
| D7 | Runner errors in the transcript | A line starting `! ` at column 0 inside an agent turn is a runner diagnostic: visible to you, excluded from requests. Model output that starts with `! ` is escaped like any marker. |
| D8 | File watching in the runner | Polling (`stat` every 300 ms), standard library only. Tens of threads; no dependency, same behaviour on macOS and Linux. |
| D9 | Sending on start-up | A thread whose last turn is yours, closed with `END`, and whose status is not `working` is a pending send. `watch` processes pending sends at start-up (you sent while the runner was down) and logs each one. |
| D10 | Recursion via `claude -p` | The runner sets `AGENT_FILES_RUNNER=1` for child processes; `agent-files-hook` exits at once when it is set, so the runner's own `claude -p` calls never create observed threads. |
| D11 | Sidecars in git | `status`, `seen`, `STOP`, `last_turn` and `threads/_observed/` are git-ignored (live state, noise in history). `thread.md`, `steps/` and `trial/` are committed. |
| D12 | Configuration | One file, `$AGENT_FILES_ROOT/config.toml`, read with `tomllib`. Your file; no program writes it after `init`. |
| D13 | Reading threads | Neovim is the reading surface for the trial: view-layer step 0 (editor setup) is a prerequisite of the smoke test, and step 1 (thread-aware display) is part of `agents.nvim`. The HTML view is optional and outside the M1 go/no-go. |
| D14 | One parser | Every program that reads `thread.md` — runner, stats, the HTML renderer — imports `lib/agent_files/thread.py`. view-layer §5.3's line rules are a summary of §4 here, not a second grammar: fences, escapes (`\END`) and `## note · <source> · tN` headers are handled the same way everywhere. |

## 2. Code layout (this repo)

```
bin/
  agent-files-run          # Python 3.11+, PEP 723 script header, run with `uv run --script`
  agent-files-hook         # Python 3.11+, standard library only (must start fast)
  agent-files-stats        # Python 3.11+, standard library only
  agent-files-grep         # POSIX sh: rg wrapper that logs the search
  agent-files-render       # optional, after the core build — view-layer step 2 (§12)
lib/agent_files/           # shared Python, imported by the bin scripts
  thread.py                # parser, serializer, escaping (§4) — the contract, most tested
  assemble.py              # thread → request (§5.3)
  backends/{anthropic,openai_compat,claude_cli,mock}.py
  git.py  config.py  fsutil.py  # atomic writes, root discovery
nvim/
  lua/agents/init.lua      # setup(), commands, autocmds
  lua/agents/thread.lua    # minimal Lua parser: last END, last header, turn ids
  lua/agents/status.lua    # status/seen reading, marks, tabline component
  lua/agents/display.lua   # highlights, folds, end-of-thread status mark (§9.5)
  plugin/agents.lua
tests/
  test_thread.py  test_assemble.py  test_run.py  test_hook.py  test_stats.py
  fixtures/                # sample thread.md files, hook input JSON
                           # also parses docs/examples/view-fixture/ (view-layer §5.5) — one fixture for parser, plugin and renderer
  nvim/test_agents.lua     # run with `nvim --headless -l`
  smoke.sh                 # end-to-end with the mock backend (§10)
install.sh                 # symlinks bin/* into ~/.local/bin, prints the hook config
```

Python dependencies (in `agent-files-run`'s PEP 723 header only): `anthropic`, `openai`, `pyyaml`. The hook, stats and tests of the parser use the standard library; `thread.py` parses frontmatter with a small built-in reader for the flat subset used in M1 (`key: value`, `key: [a, b]`, `null`) and falls back to PyYAML when it is importable.

## 3. The data root

### 3.1 `agent-files-run init`

Creates, if missing (never overwrites):

```
$AGENT_FILES_ROOT/
├── .git/                  # git init
├── .gitignore             # D11
├── config.toml            # §3.2, commented
├── agents/default.md      # frontmatter `model: null`, a short default system prompt
├── threads/
└── trial/
    ├── journal.md         # §7.4 template
    └── searches.log       # empty; appended by agent-files-grep
```

`.gitignore`:

```
threads/**/status
threads/**/seen
threads/**/STOP
threads/**/last_turn
threads/_observed/
```

Then one commit: `init`.

### 3.2 `config.toml`

```toml
default_model = "claude-opus-5-5"     # used when neither thread nor agent sets model
max_tokens    = 64000                 # streaming, so a high cap is safe
effort        = "medium"              # sent as output_config.effort to Claude models that take it

daily_spend_cap_usd = 5.00            # 0 disables; checked before every send (§5.6)

[backends.anthropic]
api_key_env = "ANTHROPIC_API_KEY"     # unset → the SDK's own credential chain
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
```

## 4. Thread format — the contract

This module is shared by every Python program and mirrored (read-only subset) in Lua. It is the part most worth getting exactly right; everything else can be rewritten later.

### 4.1 Files in a thread directory

| File | Writer | Content |
|---|---|---|
| `thread.md` | runner (agent turns, scaffolds, closing `END`s) + you (everything else) | §4.2 |
| `status` | runner (direct) or hook (observed) | one line: `working`, `blocked`, `done`, `interrupted`, `failed` — replaced atomically (write temp, `rename`) |
| `seen` | the editor | empty; only its mtime matters |
| `STOP` | you | empty; the runner deletes it after handling |
| `last_turn` | runner | one line, e.g. `t7` |
| `steps/tNNNN.request.json`, `.response.json`, `.error.json` | runner | §5.5 |

A thread is any directory under `threads/` that contains `thread.md`, excluding `threads/_observed/`. Its id is its path relative to `threads/`. Directory names must match `[a-z0-9._-]+`; the runner ignores (and logs once) any thread whose path has a segment that does not.

### 4.2 Frontmatter (fields M1 reads)

| Field | Values | Default | M1 behaviour |
|---|---|---|---|
| `agent` | name of `agents/<name>.md` | `default` | system prompt from the file body; `model` from its frontmatter |
| `runtime` | `direct`, `observed` | — | the runner owns only `direct`; anything else is ignored |
| `model` | §5.4 | agent's, then `default_model` | read fresh at every send (model switching) |
| `context` | `replay` | `replay` | `resume` is rejected with a diagnostic in M1 |
| `kind` | `main`, `fork` | `main` | informational; stats counts forks |
| `branched_at` | `tN` or `null` | `null` | informational |
| `grounding` | list | `[]` | ignored in M1; a non-empty list logs a warning once |

Unknown fields are preserved and ignored. The runner never writes the frontmatter.

### 4.3 Line grammar

The parser is a single pass over lines. State: `in_fence` (toggled by a line whose stripped form starts with ```` ``` ```` or `~~~`, at any indentation), the current section.

A line is a **marker** only if `in_fence` is false and the line, exactly (trailing whitespace stripped), matches one of:

| Marker | Regex | Notes |
|---|---|---|
| carry header | `^## carry$` | only valid as the first section after frontmatter |
| you header | `^## you · t(\d+)$` | `·` is U+00B7; the parser also accepts ` - ` and ` . ` for typing convenience, the runner always writes `·` |
| agent header | `^## agent · t(\d+)$` | |
| note header | `^## note · (.+) · t(\d+)$` | parsed, never written in M1 |
| end | `^END$` or `^END \((interrupted\|failed\|conflict)\)$` | |
| diagnostic | `^! ` | only inside agent turns (D7) |

The parser returns: frontmatter, optional carry text, and a list of turns `{role, id, body, closed: none|ok|interrupted|failed|conflict, start_line, end_line}`. A body is the text between header and `END`, with diagnostics removed and escapes undone.

**Errors are tolerated, not fatal.** Text before the first header (after frontmatter and carry) is ignored with a warning. A header inside an unclosed turn closes the previous turn implicitly as `ok` for human turns; for agent turns it is reported as a malformed file and the thread is skipped until fixed (status untouched, one log line).

### 4.4 Escaping (runner output)

Every line the runner writes from model output passes through `escape_line`:

- if the line matches `^\\*(## (carry|you|agent|note)\b|END\b|! )` — i.e. a marker, possibly already preceded by backslashes — prefix one `\`.

`unescape_line` removes exactly one leading `\` from a line matching `^\\+(## (carry|you|agent|note)\b|END\b|! )`. The pair is lossless: `unescape(escape(x)) == x` for every line (property test). Escaping is applied regardless of fences, so model output can never close its own turn.

**Fence balance.** Before writing the closing `END` of an agent turn, the runner checks whether the turn left a fence open; if so it first writes the matching fence line. A human turn with an unclosed fence has its `END` inside the fence, so it is not a send — `:AgentsSend` warns about this case.

### 4.5 Send detection

`is_send(thread)` is true iff:

1. the last turn is `role == you` and `closed == ok`;
2. its body is not empty after stripping whitespace;
3. `status` is not `working`;
4. no agent turn with a larger id exists.

Evaluated by the runner after it sees `thread.md` change (mtime or size), and at start-up (D9). It is a pure function of the files.

## 5. `agent-files-run`

### 5.1 Command line

```
agent-files-run init
agent-files-run watch            # long-running; owns every direct thread under threads/
agent-files-run once <thread>    # process one pending send (if any), then exit
agent-files-run check <thread>   # parse and print the turn table and the assembled request; never calls a model
```

Exit codes: 0 ok; 1 usage or config error; 2 another runner holds the lock; 3 `once` found nothing to send.

**Single runner.** `watch` and `once` take an exclusive `flock` on `$XDG_STATE_HOME/agent-files/run.lock` (default `~/.local/state/agent-files/run.lock`); a second instance exits 2. This is the M1 enforcement of "one writer per thread". Logs go to stderr and `$XDG_STATE_HOME/agent-files/run.log`, one line per event: `ISO-time thread event detail`.

### 5.2 The turn, step by step

For a thread where `is_send` is true, with your turn `tK`:

1. **Spend check** (§5.6). Over the cap → go to step 9 with reason `spend cap`.
2. **Send commit.** `git add <thread dir>` and commit `send <thread id> tK` with trailers (§7.1).
3. Write `working` to `status`.
4. Assemble the request (§5.3); write `steps/tNNNN.request.json` where `NNNN` is the agent turn id `N = next_id()` (D3).
5. Append `\n## agent · tN\n` to `thread.md`; write `last_turn`. Record the file's size and a hash of its contents: this is the **expected state**.
6. Stream. Buffer output by line; for each complete line, escape and append; update the expected state after each write. Every 60 s, rewrite `status` (`working`) as a heartbeat so the plugin does not mark it stale.
7. Between writes (at least every 300 ms), check:
   - `STOP` exists → cancel the stream; close with `END (interrupted)`; status `interrupted`; delete `STOP`.
   - `thread.md` no longer matches the expected state → **conflict**: cancel; write the remaining buffered text to `out/tNNNN-conflict.txt`; do *not* write to `thread.md` again for this turn except to append `END (conflict)` at the end; status `interrupted`.
8. On normal completion: flush the last partial line, balance fences, append `END`.
9. **On failure** (API error, refusal, spend cap, unknown backend): append any partial output, then a `! error: <one-line reason>` diagnostic, then `END (failed)`; write `steps/tNNNN.error.json`; status `failed`. If the failure happened before step 5, write the header first, so every send gets an agent turn.
10. Append the scaffold `\n## you · t(N+1)\n\n` and update `last_turn`.
11. Write `steps/tNNNN.response.json` (if there was a response).
12. Status: `done` (or the abnormal status set above).
13. **Reply commit.** `git add <thread dir>`; commit `reply <thread id> tN` with trailers.

Git failures are logged and never fail the turn.

**Start-up recovery** (`watch` and `once`, before anything else): for each direct thread with status `working` — if the last turn is an open agent turn, append `END (interrupted)` and the scaffold; set `interrupted`; commit `recover <thread id>`. Then process pending sends (D9).

**Concurrency.** `watch` runs each active turn in its own thread; at most one turn per thread directory; no global limit in M1.

### 5.3 Assembly (replay)

Input: the parsed thread. Output: a provider-neutral request `{system, messages, model, max_tokens}`.

1. `system` = body of `agents/<agent>.md` (frontmatter stripped). Empty → omitted.
2. Walk the turns in order; map `you → user`, `agent → assistant`. Bodies are already unescaped and stripped of diagnostics. The current turn is included; the empty `## agent` header just appended is not.
3. If there is a carry section, prefix the first user message with `<carry>\n…\n</carry>\n\n` (D4).
4. Drop turns whose body is empty (an interrupted or failed turn with no output).
5. Merge consecutive messages of the same role, joined by a blank line (happens after step 4).
6. If the first message is `assistant`, prepend a user message `(conversation continues)`. The last message is always `user` (send detection guarantees it).

Assembly is deterministic: the same file gives byte-identical JSON, which keeps prompt caching effective and makes `diff steps/t0004.request.json steps/t0006.request.json` meaningful. Test it.

### 5.4 Backends

Chosen by the `model` string:

| `model` | Backend | Notes |
|---|---|---|
| `claude-*` | Anthropic Messages API | §5.4.1 |
| `<name>/<model>` where `<name>` is a key in `[backends.openai_compat]` | OpenAI-compatible chat completions, streaming | `system` sent as a `system` message; no caching; usage recorded if the server returns it |
| `claude-cli` or `claude-cli/<model>` | `claude -p` subprocess | §5.4.2 |
| `mock/echo`, `mock/slow`, `mock/fail`, `mock/markers` | built-in, no network | §5.4.3 — for tests and the smoke test |
| anything else | — | failed turn: `! error: unknown model <x>` |

#### 5.4.1 Anthropic

- Official `anthropic` Python SDK, `client.messages.stream(...)`, text deltas appended as they arrive, final message from `get_final_message()`.
- Request: `model`, `max_tokens` (config), `system`, `messages` (text content only — D5), `cache_control: {type: "ephemeral"}` at the top level (automatic caching of the longest stable prefix), `output_config: {effort: <config>}` for models that take it. No `temperature`/`top_p`/`top_k` (current models reject them). No `thinking` parameter: current Opus/Sonnet run adaptive thinking by default, and the runner ignores thinking blocks in the response.
- Refusal fallback: when `fallbacks = true`, send the server-side fallback option with its beta flag, as documented for the model at build time. Record the model that actually served the turn in `response.json`; if it differs from `model:`, add a diagnostic `! served by <model>` so a fallback is never silent.
- `stop_reason`: `end_turn` → normal; `max_tokens` → normal close plus `! stopped: max_tokens`; `refusal` (with no fallback, or after fallback) → failed turn with `! error: refusal (<category>)`.
- Errors: rate limit / overload / 5xx → the SDK's own retries, then a failed turn. 4xx → failed turn immediately, with the API's message in the diagnostic.

#### 5.4.2 `claude -p`

Draws on the Agent SDK monthly credit on Pro/Max. Claude Code adds its own system prompt and tools, so `steps/` records what we sent, not the exact model request.

- Render the assembled messages as one transcript prompt (`[you]` / `[agent]` blocks) on stdin; the agent's system prompt via the flag that replaces the system prompt.
- Run in an empty temporary directory, with all tools disabled, session persistence off, project/user settings not loaded, `--output-format stream-json`, and `AGENT_FILES_RUNNER=1` in the environment.
- **Verify every flag against `claude --help` at build time** (open question m1-plan §9.1). If a flag is missing, document the gap in `steps/` (`"backend_caveats": [...]`) rather than silently dropping it.
- Cost: take `total_cost_usd` from the final result event if present.

#### 5.4.3 Mock

| Model | Behaviour |
|---|---|
| `mock/echo` | Streams back `echo: ` + the last user message, one line every 20 ms |
| `mock/slow` | Streams 200 numbered lines, one every 100 ms (for interrupt and conflict tests) |
| `mock/fail` | Streams two lines, then raises an API-style error |
| `mock/markers` | Streams lines that look like `END`, `## you · t99`, `! x`, `\END`, and an unclosed ```` ``` ```` fence (for escaping tests) |

Mock turns write `steps/` like real ones, with `"backend": "mock"`.

### 5.5 `steps/` records

`tNNNN.request.json`:

```json
{"thread": "fix-auth-timeout", "turn": "t0006", "time": "2026-11-02T10:14:03Z",
 "backend": "anthropic", "model": "claude-opus-5-5",
 "request": { "...": "the exact body sent to the provider" }}
```

`tNNNN.response.json`: `backend`, `served_model`, `stop_reason`, `usage` (as returned — for Anthropic including `cache_creation_input_tokens` and `cache_read_input_tokens`), `cost_usd` (computed from `[prices]`, or reported by `claude -p`), `duration_ms`, `chars_out`. The text is not duplicated; it is in `thread.md`.

`tNNNN.error.json`: `kind` (`api`, `refusal`, `spend_cap`, `config`, `backend`), `message`, `http_status` if any.

### 5.6 Spend cap

Before each send, sum `cost_usd` from every `steps/*.response.json` modified today (local time) across the root. Over `daily_spend_cap_usd` → failed turn, `! error: daily spend cap reached ($5.00)`. Mock and local backends cost 0. Scanning is fine at trial scale; no cache file.

## 6. `agent-files-hook`

Configured once in `~/.claude/settings.json` (`install.sh` prints the block):

```json
{ "hooks": {
  "SessionStart":     [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "PreToolUse":       [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "PostToolUse":      [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "Notification":     [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "Stop":             [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }],
  "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }]
}}
```

Verify the exact settings shape, event names and the `Notification` input fields against the current Claude Code hooks docs at build time; add the failure event if one exists.

**Behaviour.** Reads one JSON object on stdin (`session_id`, `transcript_path`, `cwd`, `hook_event_name`, plus event fields). Always exits 0 and prints nothing; must finish in under 100 ms (standard library only, no network). Exits immediately if `AGENT_FILES_RUNNER` is set (D10).

- Thread directory: `threads/_observed/<project>-<sid8>/` where `<project>` is the slugified basename of `cwd` and `<sid8>` the first 8 characters of `session_id`, lowercased.
- On the first event for a session (directory missing): create it with a frontmatter-only `thread.md`:

  ```markdown
  ---
  runtime: observed
  project: /Users/mark/code/api
  transcript: /Users/mark/.claude/projects/…/<session>.jsonl
  started: 2026-11-02T10:14:03Z
  ---
  ```

- Status mapping:

  | Event | Status |
  |---|---|
  | `SessionStart` | `done` |
  | `UserPromptSubmit`, `PreToolUse`, `PostToolUse` | `working` |
  | `Notification`, type `permission_prompt` | `blocked` |
  | `Notification`, type `idle_prompt` or other | no change |
  | `Stop` | `done` |
  | failure event (if it exists) | `failed` |
  | `SessionEnd` | delete the directory |

- Status writes are atomic replacements. Hooks for one session can race (Pre/PostToolUse in quick succession); the last writer wins, which is acceptable for a status mirror.
- Append one line per status change to `trial/observed.log` (`ISO-time<TAB>thread<TAB>status`) for the fallback measure (and observed-session counts, printed as information since H4 was dropped). Lines under `PIPE_BUF`, opened with `O_APPEND`, so concurrent appends are safe.

## 7. Measurement

### 7.1 Commit trailers

Every runner commit message ends with trailers that `git log --format=%(trailers)` can read:

```
send fix-auth-timeout/retry-logic t5

Agent-Files-Event: send            # send | reply | recover
Agent-Files-Thread: fix-auth-timeout/retry-logic
Agent-Files-Turn: t5
Agent-Files-Model: claude-opus-5-5
```

### 7.2 Classifying a send commit

For each `send` commit, compare `thread.md` before (the thread's previous commit) and after:

- **Context edit (H1):** the "before" body up to and including its last `END` line is not a byte-for-byte prefix of the "after" body. Frontmatter is excluded from both sides first. (Edits to `## carry` count.)
- **Model switch:** the frontmatter `model` value differs.
- **Frontmatter edit:** any other frontmatter change.

A thread's first send has no "before" and counts as neither. Edits you save but never send are picked up by the next send commit; edits in a thread you never send to again are not measured (journal them).

### 7.3 `agent-files-stats`

```
agent-files-stats [--since YYYY-MM-DD] [--json]
```

Prints, from `git log` (trailers + the diffs in §7.2), `threads/`, `trial/searches.log` and `trial/observed.log`:

```
threads                     23   (forks 7)
turns per thread            median 6, max 31
threads with 6+ turns       11
  with a context edit        4   (36%)    H1 go ≥ 20%, kill < 5%
forks                        7            H2 go ≥ 5,   kill < 2
  carry size                median 14 lines / 1.1k chars
model switches               3
searches (agent-files-grep) 18            H3: "used" count is in the journal
observed sessions           41   blocked events 19
spend                       $3.12 (today $0.40)
```

`--json` prints the same numbers as one object. Forks are threads with `kind: fork` present now, plus fork directories deleted later (found as `thread.md` paths in history).

### 7.4 Journal template (`trial/journal.md`)

```markdown
## 2026-11-02
- Used it for:
- Used instead (Claude app / plain TUI), and why:
- Worst friction:
- Forks today: <thread> — helped | hurt | neutral — why
- Searches whose result I used: <pattern> → <thread>
- Read threads in: Neovim | browser view | Warp/other viewer   (view-layer §6)
```

## 8. `agent-files-grep`

```
agent-files-grep <pattern> [rg options…]
```

Runs `rg --vimgrep <pattern> $AGENT_FILES_ROOT/threads --glob thread.md --glob '!_observed/**'`, prints the results, and appends `ISO-time<TAB>pattern<TAB>hit-count` to `trial/searches.log`. Exit code is `rg`'s. `:AgentsGrep` calls this, so searches from the shell and from Neovim are counted the same way.

## 9. `agents.nvim`

Neovim 0.10+. Configured with `require('agents').setup({ root = '~/agent-files' })`; `$AGENT_FILES_ROOT` wins if set.

### 9.1 Buffers and watching

- A buffer is a thread buffer if its path is `<root>/threads/**/thread.md` (observed threads included, read-only, no commands that write turns).
- For each thread buffer: one `vim.uv.new_fs_event` on the thread directory. On any event, debounced 100 ms: re-read `status` and `seen`, `:checktime` the buffer, refresh marks.
- While `status` is `working`: `modifiable = false`, `readonly = true`. Restored when it changes.
- **Draft re-apply.** Before a reload (`FileChangedShell`, and set `v:fcs_choice = 'reload'` so there is never a prompt): if the buffer is modified, save the text after the last closed turn's `END` (the draft region). After reload, if the file's new last section is an empty `## you · tN` scaffold, put the draft there; otherwise append it at the end. Notify once: "draft re-applied".

### 9.2 Marks and status line

`require('agents').status(bufnr)` returns a short string; a default tabline is installed if `setup({ tabline = true })`.

| State | Mark |
|---|---|
| `working`, status mtime < 10 min old | `⠋` (spinner, advanced on a 120 ms timer only while any thread is working) |
| `working`, ≥ 10 min old | `?` stale |
| `blocked` | `●` red |
| `failed` | `✗` red |
| `done` / `interrupted`, status newer than `seen` | `✓` / `⏸` (unseen) |
| status older than `seen`, or no status | nothing (idle) |

Plus `~Nk` tokens: `ceil(characters of thread.md / 4 / 1000)`.

### 9.3 Commands

| Command | Does | Shell equivalent |
|---|---|---|
| `:AgentsSend` | Refuse if `working`, if the last section is not a `## you` turn, if its body is empty, or if it leaves a fence open (with a message saying which). Otherwise append `END` (on its own line, after trimming trailing blank lines) and `:write`. | `echo END >> thread.md` |
| `:AgentsStop` | `touch <dir>/STOP` | same |
| `:AgentsNew <slug>` | Validate the slug; create `<root>/threads/<slug>/thread.md` (frontmatter `agent: default`, `runtime: direct`, `model: null`, `context: replay`, `kind: main`; then `## you · t1` and an empty line); open it with the cursor on the empty line | `mkdir` + heredoc |
| `:'<,'>AgentsFork <slug>` | Create `<this thread dir>/<slug>/thread.md`: parent frontmatter fields `agent`, `runtime`, `model`, `context`, `grounding`; `kind: fork`; `branched_at:` the id of the turn containing the selection's first line (or the last turn, with no range); a `## carry` section with the selected lines verbatim; `## you · t1`. Open it. | same |
| `:AgentsNext` | Quickfix list of threads needing you: blocked, then failed, then unseen done/interrupted, then stale; each entry points at the thread's last header line (observed threads: line 1). Jumps to the first. | `grep -rlx blocked --include=status threads/` |
| `:AgentsBlocked` | Same list, blocked and failed only. | same |
| `:AgentsGrep <pattern>` | Run `agent-files-grep` and load its `--vimgrep` output into quickfix (title `AgentsGrep: <pattern>`). | `agent-files-grep <pattern>` |

### 9.4 Seen

Touch `seen` when a thread buffer is entered (`BufEnter`) and on `FocusGained` while one is the current buffer, and after a reload while it is visible in the current window. Never for buffers that are only loaded.

### 9.5 Display (view-layer step 1)

Thread-aware display on top of whatever generic markdown renderer step 0 installed. Applied to thread buffers only; must not fight `render-markdown.nvim` / `markview.nvim` (use our own highlight groups and extmark namespace, priority above theirs).

- **Highlight groups**, linked to sensible defaults so colorschemes can override: `AgentsYou` (`## you · tN`), `AgentsAgent` (`## agent · tN`), `AgentsNote`, `AgentsCarry`, `AgentsEnd` (`END` and `END (…)`, dimmed), `AgentsEndAbnormal` (`END (interrupted|failed|conflict)`), `AgentsDiag` (`! ` lines), `AgentsTool` (`▸` lines). Matching uses the Lua parser, so markers inside fences are not highlighted.
- **Folds:** `foldmethod=expr` with an expression that opens a fold at each `▸` line and includes the indented lines below it, closed by default. M1's runner writes no `▸` lines (no tools), so this is exercised by the fixture and later milestones; it costs nothing now.
- **End mark:** virtual text at the end of the last `END` line (or of the last header, during a turn) showing the thread's mark from §9.2 plus the status word, e.g. `  ⠋ working · ~12k`. Updated with the marks.
- Settings for thread buffers: `conceallevel=2`, `wrap`, `linebreak` (step 0 recommends them globally for markdown; the plugin sets them locally so threads read well either way).

## 10. Acceptance



### 10.1 Automated tests (must pass before the smoke test)

| Area | Tests |
|---|---|
| Parser | every marker; markers inside fences; ` · ` alternatives; implicit closes; malformed agent turn; text before the first header; frontmatter subset; round trip `parse → serialize` on fixtures is byte-identical |
| Escaping | property test `unescape(escape(x)) == x`; `mock/markers` output never yields an extra turn or `END` |
| Turn ids | next id after deletes uses `last_turn`; gaps are kept |
| Send detection | draft (no `END`) → no; `END` + `working` → no; empty body → no; `END` inside an unclosed fence → no; pending send at start-up → yes |
| Assembly | carry placement; empty turns dropped; same-role merge; diagnostics excluded; determinism (same file → identical JSON) |
| Runner (mock) | full turn writes header, body, `END`, scaffold, `done`, two commits with trailers; `STOP` → `END (interrupted)`; foreign write → `END (conflict)` + `out/`; crash (kill -9 mid-turn) then restart → recovered; `mock/fail` → `END (failed)` + `! error`; spend cap; second runner exits 2 |
| Hook | fixture events → statuses; `idle_prompt` no change; `SessionEnd` deletes; `AGENT_FILES_RUNNER` set → no-op; always exit 0, even on garbage input |
| Stats | a scripted git history with known edits, switches and forks → expected numbers |
| Plugin (headless) | `:AgentsNew`, `:AgentsSend` refusals and success, `:AgentsFork` output, read-only while `working`, draft re-apply; on the view fixture: highlight groups land on the right lines (none inside the fenced fake marker), the `▸` fold is closed, the end mark shows the status |

### 10.2 Smoke test (by hand, real editor; `tests/smoke.sh` automates S1–S5 with the mock backend)

**Prerequisite:** view-layer step 0 is done and its exit check passes — you can read `docs/examples/view-fixture/thread.md` (table, long tool output) in Neovim without another viewer. A trial that fails because threads are unpleasant to read tests the editor setup, not the thesis (m1-plan §7).


| # | Do | Pass when |
|---|---|---|
| S1 | `:AgentsNew smoke`, write a question, `:AgentsSend` with `model: mock/echo` | An agent turn streams in live; the buffer is read-only during it; `✓` then idle after you look; two commits |
| S2 | Edit a line above the last `END`, send another turn | `steps/` request contains the edited text; `agent-files-stats` reports one context edit |
| S3 | Select two lines, `:AgentsFork smoke-fork`, send | Child exists with `## carry`, `kind: fork`, `branched_at`; the request starts with `<carry>` |
| S4 | `model: mock/slow`, send, `:AgentsStop` | `END (interrupted)`, status `interrupted`, `STOP` gone, scaffold present |
| S5 | `model: mock/slow`, send, kill the runner, restart it | Turn closed `END (interrupted)` on restart; no duplicate turn |
| S6 | Switch to `model: claude-opus-5-5`, send twice within 5 minutes | Real reply; second `response.json` shows `cache_read_input_tokens > 0` |
| S7 | Delete a whole earlier agent turn, rewrite your first turn, send | Reply arrives (no 400 from edited history — D5) |
| S8 | Switch to a local model (`ollama/<name>`), send | Reply; `cost_usd: 0` |
| S9 | Start `claude` by hand in a project, give it a task that needs a permission | `_observed/<project>-<sid>/` appears; `:AgentsNext` shows it `blocked`; then `working`, `done`; gone after exit |
| S10 | `:AgentsGrep <word from S1>` | Quickfix hits; one line in `trial/searches.log` |
| S11 | Open S1's thread and the view fixture | Turn headers and `END` are highlighted; the end mark shows the status and token estimate; the fixture's tool fold is closed |

When S1–S11 pass, record the date at the top of `trial/journal.md`: day 1 of the trial.

## 11. Build order

Each step ends with its tests passing; together under a week, matching m1-plan §8.

1. `thread.py` + tests (parser, escaping, ids, send detection). **The contract — do it first and carefully.**
2. `assemble.py` + the mock backend + `agent-files-run once`/`check` + runner tests.
3. `watch`, the lock, `STOP`, conflicts, recovery; git commits with trailers.
4. Anthropic backend, spend cap, `steps/`; S6, S7 by hand.
5. View-layer step 0 (editor setup, about an hour) and the view fixture (`docs/examples/view-fixture/`). Then `agents.nvim`: buffers, watcher, read-only, `:AgentsNew`/`:AgentsSend`/`:AgentsStop`; then marks, `:AgentsFork`, `:AgentsNext`, draft re-apply; then display (§9.5).
6. `agent-files-hook` + `install.sh`; S9.
7. `agent-files-grep`, `agent-files-stats`, journal template; OpenAI-compatible and `claude -p` backends.
8. Full smoke test; start the trial.
9. *Optional, in parallel with the trial:* `agent-files-render` (view-layer step 2), built on `thread.py` (§12).

## 12. The HTML view — how it plugs in

`agent-files-render` is specified in [view-layer.md §5](view-layer.md#step-2--the-html-prototype-agent-files-render) and is not needed for the trial. If it is built, these rules from this spec apply to it:

- **Parser:** it imports `lib/agent_files/thread.py` (D14) — same markers, fence handling and unescaping as the runner; a turn's `closed` state drives its styling (draft, `END (interrupted)` etc.).
- **Diagnostics:** `! ` lines in agent turns are shown, styled as runner messages, not as model text.
- **Sidecars:** status from `status` and `seen` with the same rules as §9.2 (idle, unseen, stale); the token estimate is the same characters ÷ 4.
- **Read-only and outside the root:** it writes only under `~/.cache/agent-files/view/`, which is outside the root repo, so it never shows up in git or in `agent-files-stats`.
- **Not measured as a hypothesis.** Its keep/drop question (view-layer §6) is answered from the journal's "read threads in" line, separately from H1–H3.

## 13. Not in this build

Exactly as m1-plan §2: no tools in the runner (so no `▸` folds, `out/` only for conflicts, no `? PERMISSION`), no `inbox/` or notes, no sub-threads, `:AgentsClose` or `:AgentsPrune`, no doorbell, no grounding, no compaction, no `resume` context, no multi-machine use, no browser actions that write files (view-layer step 3). The parser already accepts note headers so later milestones don't change the format.

## 14. Open questions for the build

1. **`claude -p` flags** (m1-plan §9.1): verify at step 7; if Claude Code's own prompt cannot be removed, the backend is still useful for cheap iteration but its turns should be excluded from cache and request comparisons.
2. **Effort per thread.** M1 uses one `effort` from config. If the trial wants a per-thread knob, add an optional `effort:` frontmatter field — a format addition, not a change.
3. **Spinner cost.** A 120 ms timer redrawing the tabline is cheap, but if it flickers in Ghostty, fall back to a static `…`.
