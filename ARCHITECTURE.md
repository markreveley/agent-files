# agent-files — Architecture

> Status: draft v0.3 · 2026-10-31 · this document describes the **target** architecture; what gets built is gated by the M1 trial ([docs/m1-plan.md](docs/m1-plan.md)).
> Collapse the agent interface down to **files, processes, and an editor**.
> Supplemental: [docs/m1-plan.md](docs/m1-plan.md) — the M1 trial and go/no-go criteria · [docs/juggler-analysis.md](docs/juggler-analysis.md) — reference comparison, storage format tradeoff, own agent loop · [docs/role-of-neovim.md](docs/role-of-neovim.md) — Neovim's role and the doorbell · [docs/view-layer.md](docs/view-layer.md) — readable text in Neovim, rich HTML view in the browser.

## 1. Thesis

Most agent UIs are chat panels bolted onto a harness. Here we flip that:

- A **thread is a file** — `thread.md`, in a directory of its own. The conversation, tool calls and permission questions live in plain markdown on disk; live state (status, session) sits beside it in tiny sidecar files.
- An **agent is a declaration** (a file naming its runtime, model, tools, permissions and grounding). The **process** that runs it is ephemeral — it exists only while there is work to do.
- **Neovim is a viewer/editor**, not the host. It watches files, shows status, and is where you write. Anything else that can read files (`grep`, `cat`, a phone reading a synced folder) is also a client.
- **Memory is files too:** threads are scratch; durable knowledge is promoted into a small DAG knowledge base that new threads are grounded in.

Unix analogy: program vs. process. The file is the program and its state; the runner is just a process.

### Non-goals

- Being a terminal. Ghostty renders; tmux hosts long-lived sessions. Interactive TUIs (lazygit, an agent's own TUI) stay in a real terminal.
- Being the main coding harness. Claude Code, Codex, etc. own the heavy coding loop. We sit above them and own *context assembly, routing, status, and the record*. A small native loop for lighter, transparent work is proposed separately (see the supplemental analysis).

## 2. Principles — the agent you can `cat`

> **State lives in files, formats are plain text, extensions are executables, history is git, and structure is directories.**

1. **State lives in files.** Everything that matters is on disk. Kill every process and nothing is lost; restarting means re-reading files. Processes may cache state, never own it.
2. **Formats are plain text.** Markdown + YAML frontmatter for what humans read and write; one-line files for live state; JSONL for event logs; JSON for single records. No binary format in the source of truth.
3. **Extensions are executables.** A feature is a program on `PATH` named `agent-files-<name>` (like `git` subcommands): arguments and/or JSON on stdin in, JSON (or nothing) on stdout out, meaning in the exit code unless its spec says otherwise. Any language.
4. **History is git.** Undo, audit, blame and multi-machine sync go through git. Runtimes may commit at turn boundaries; nothing rewrites git history.
5. **Structure is directories.** A thread is a directory; a branch is a subdirectory; its id is its path. `ls` and `tree` are the index.
6. **Processes are disposable.** Runners start and stop freely. Control is a file (`touch STOP` in the thread's directory) or a signal. Any long-lived process state must be rebuildable from files.
7. **Indexes are caches.** Any database or index (search, the KB graph) is derived: delete it and rebuild it from files.
8. **Protocols are doorbells.** RPC, sockets and channels only say "look at this file". Content travels through files. (Streams from harnesses at the edge — ACP, SDK, stream-json — are written to files as they arrive.)
9. **The editor is a client.** Neovim is the best viewer, not a dependency. Every operation can be done from a shell.
10. **Humans author, machines append.** You write the human parts of a thread (§4.3); the thread's runtime appends the rest. Text a human did not write never enters the interactive tier.
11. **One machine writer per file.** Every file has exactly one process allowed to write it (§4.4). Many readers, one writer, no locks to get wrong.

**The cat test.** A feature passes if you can see it with `cat`, find it with `grep`, undo it with `git`, and do it by hand from a shell. A feature that fails the test needs its reason written down.

## 3. Concepts

| Concept | Is | Lives in |
|---|---|---|
| Root | The directory that holds everything below; its own git repo, separate from code repos | `~/agent-files/` by default (one per project is allowed) |
| Thread | One conversation; its id is its path under `threads/` | `threads/<id>/thread.md` |
| Branch | A fork or sub-thread of a thread (`kind:` says which) | a subdirectory of that thread's directory |
| Turn | One `## you · tN` or `## agent · tN` section ending in `END`; `tN` is a stable id | inside `thread.md` |
| Note | System-written text for a thread (a child's report, a retraction warning) — never a human turn | `inbox/` until consumed, then a `## note` section |
| Agent | Declaration: runtime, model, tools, permissions, grounding; body = system prompt | `agents/<name>.md` |
| Process | The one runtime instance that owns a thread while it runs | in memory; its state is the sidecar files |
| Status | `working \| blocked \| done \| interrupted \| failed \| closed` — written only by the thread's runtime | `threads/<id>/status` (one line) |
| Seen | Your acknowledgment; a thread whose status is older than `seen` shows as idle | `threads/<id>/seen` (empty file; its mtime) |
| Control file | An out-of-band request to a running turn | `threads/<id>/STOP`, present only until handled |
| Snippet | Reusable prompt text, expanded from `/name` (tiers 2–3) | `snippets/<name>.md` (+ `.claude/commands`, skills) |
| KB node | One fact / claim / ref / decision / question | `kb/<node id>.md` |

An agent declaration, minimally:

```markdown
---
runtime: headless       # default for threads using this agent
model: claude-opus-5-5
tools: [read, grep]
grounding: [auth-flow]
---
You are a careful reviewer…
```

A thread's frontmatter overrides its agent's fields (`runtime`, `model`, `grounding`); the agent file supplies the rest.

## 4. Threads — layout, grammar, ownership

### 4.1 Layout: threads are directories, branches are subdirectories

```
~/agent-files/                 # the root: its own git repo
├── agents/  snippets/  kb/
└── threads/
    └── fix-auth-timeout/
        ├── thread.md              # the conversation (main line)
        ├── status                 # one line, e.g. "done" — written only by the runtime
        ├── session                # harness session id (resume mode) — written only by the runtime
        ├── seen                   # touched by the editor when you view the thread
        ├── STOP                   # control file: exists only while an interrupt is pending
        ├── inbox/                 # notes waiting to be consumed (one file per note)
        ├── steps/                 # exact request/response per model call, where we call the model API ourselves
        │   ├── t0002.request.json
        │   └── t0002.response.json
        ├── out/                   # large tool outputs, linked from turns
        ├── archive/               # originals replaced by compaction (nothing is thrown away)
        ├── reviews/               # council output: <model>.md + synthesis.md
        ├── events.jsonl           # optional event log (history); `status` is authoritative for the current state
        ├── explore-pool/          # sub-thread (kind: subthread) — reports back when closed
        │   └── thread.md
        └── retry-logic/           # fork (kind: fork, branched_at: t7) — never reports back
            └── thread.md
```

- Directory names are slugs: `[a-z0-9._-]+`. A thread's id is its path under `threads/` (e.g. `fix-auth-timeout/retry-logic`); there is no `id:` field to drift when you `mv` it.
- A branch is a **subdirectory** of the thread it came from. The parent is the enclosing directory — no `parent:` field.
- `tree threads/` is the branch view; oil.nvim or yazi are the branch browser; `grep -rlx blocked --include=status threads/` is the needs-you list.
- Moving or pruning a branch is `mv` / `rm -r`, with git as undo.

### 4.2 Thread file format

```markdown
---
agent: coder            # -> agents/coder.md
runtime: headless       # interactive | headless | direct | observed (M1) | native (proposed, M6)
model: null             # overrides the agent's model; change it to switch models (replay mode)
context: replay         # resume | replay
kind: main              # main | fork | subthread
branched_at: null       # forks and sub-threads: the parent turn id they start from, e.g. t7
grounding: [auth-flow, decision-0007]
---

## you · t1
The auth middleware times out under load. Find out why.
END

## agent · t2
Looking at the middleware first.

▸ Read src/auth/middleware.ts (212 lines)
  …full tool output, indented two spaces…
▸ Bash `npm test auth` (exit 1, 48 lines → out/t2-bash-1.txt)

The pool is created per request…
END

## you · t3
/test
Also check the retry logic.
```

The last turn is still a draft: it has no `END` yet, so nothing has been sent.

The frontmatter is **configuration you own**. Runtimes never rewrite it; live state goes in the sidecar files (§4.1).

### 4.3 Turn grammar

A line is a **marker** only at column 0, outside fenced code blocks and outside indented tool output:

| Marker | Written by | Meaning |
|---|---|---|
| `## carry` | whoever creates a branch | Lines chosen from the parent; first section after the frontmatter |
| `## you · tN` | the runtime (as a scaffold after each `END`), or `:AgentsNew` / the creator of a thread for `t1` | Start of your turn |
| `## agent · tN` | the runtime | Start of the agent's turn |
| `## note · <source> · tN` | the runtime, when it consumes `inbox/` | System-written text; never a human turn |
| `END` | you (closing your turn) or the runtime (closing its turn) | End of a turn; doubles as a commit marker |
| `END (interrupted)` / `END (failed)` / `END (conflict)` | the runtime | A turn closed abnormally; parsed like `END` |
| `? PERMISSION pN <tool> <args> [y/n/always]` | the runtime | A pending permission question (tiers 2–3) |
| `> y` / `> n` / `> always` | you, on the line directly below its question | Your answer |

- **Escaping.** The runtime writes tool output indented two spaces (or to `out/`, linked), and prefixes any other output line that would parse as a marker with `\`. Model or tool output can therefore never forge `END`, a header, or a permission answer.
- **Turn ids** (`tN`) are assigned when a turn is created and never renumbered. Deleting or compacting turns leaves gaps; `branched_at` keeps pointing at the same turn.
- **The human region** is the text after the last `## you · tN` header that has no `END` yet. That, plus a permission answer while `blocked`, is all you write. Edits *above* the last `END` are not turns: in replay mode they change what the model sees next; in resume mode they are ignored.
- **A send** is a save after which the last turn is yours and ends with `END`, while status is not `working`. A save without that sends nothing.

### 4.4 Ownership: one writer per file

| File | Machine writer | Human writes |
|---|---|---|
| `thread.md` — agent turns, notes, scaffolds, `END` of agent turns | the thread's runtime (exactly one process owns a thread, chosen by `runtime:`) | — |
| `thread.md` — human region, edits above `END`, frontmatter | — | you (any editor or shell) |
| `status`, `session`, `steps/`, `out/`, `archive/`, `reviews/` (own thread) | the thread's runtime | — |
| `seen` | the editor, on your behalf | `touch seen` |
| `STOP` | — (the runtime deletes it after handling) | you |
| `inbox/<n>.md` | whoever reports (a child's runtime, an extension); one file per note | — |
| `events.jsonl` | append-only; the runtime, and in tier 1 the Claude Code hooks (single-line appends) | — |
| New branch directories | whoever creates the branch (§8) | you, via `:AgentsFork` or `mkdir` |

### 4.5 Rules

1. **Locking.** While `status` is `working`, the editor makes the buffer read-only. During a turn the runtime is the only writer of `thread.md`; if it detects a foreign write (the file changed in a way it didn't), it stops, saves its remaining output to `out/`, closes with `END (conflict)` and sets `interrupted`. If an editor holds unsaved text when the runtime writes, the plugin reloads the file and re-applies your draft below the new last `END` — no "file changed" prompt.
2. **Interrupt.** Create `STOP` in the thread's directory (`touch`, or `:AgentsStop`). The runtime stops the turn (SDK `interrupt()` / native cancel; in tier 1 the bridge sends Escape to the TUI), closes with `END (interrupted)`, sets `interrupted`, and deletes `STOP`.
3. **Crash recovery.** When a runtime starts, any thread it owns whose `status` is `working` with no live owner gets `END (interrupted)` and its `status` becomes `interrupted`. You then **resume** (send a new turn, e.g. "continue") or **discard** (delete the partial agent turn by hand — the buffer is writable once the turn is closed).
4. **Snippets.** In tiers 2–3 a leading `/name args` line is expanded from `snippets/` (or `.claude/commands/`, skills) before sending. In tier 1 your text is forwarded verbatim and Claude Code expands its own commands.
5. **Session actions.** `/fork` creates a branch exactly as `:AgentsFork` does (§8). `/clear` in replay mode starts a fork with an empty `## carry`; in tier 1 it is passed to Claude Code and recorded as a `## note`. `/compact` is compaction (rule 9 below).
6. **Tool calls** are one-line `▸` summaries with output indented beneath (folded by indentation in Neovim) or moved to `out/` and linked. All folds closed = the collapsed natural-language transcript.
7. **Permissions (tiers 2–3).** The runtime writes one `? PERMISSION pN …` line, sets `blocked`, and waits; there is at most one pending question per thread. You answer `> y`, `> n` or `> always` on the line below it and save — the one place you write inside an agent turn, safe because the runtime is waiting, not writing. `always` allows that exact tool call pattern for the rest of the runtime's process (a persistent rules file is proposed; [juggler analysis §3](docs/juggler-analysis.md#3-what-we-borrow--translated-to-files)). Tier-1 permissions are answered in the attached TUI for now (§12).
8. **Status.** Only the thread's runtime writes `status`. "Idle" is not a status: a thread whose `status` file is older than its `seen` file is shown as idle. `closed` is terminal and applies to sub-threads (§8).
9. **Compaction** is the one machine rewrite above `END`: an explicit operation the runtime performs while holding the turn (its `status` is `working`), moving the replaced turns to `archive/` and recording a `## note · compaction`. Turn ids of surviving turns are unchanged.

## 5. Runtimes — three tiers

| Tier (`runtime:`) | Mechanism | Who authors turns | Billing (Claude, as of 2026-10) | Use for |
|---|---|---|---|---|
| **1. Interactive** (`interactive`) | Real `claude` TUI in a detached tmux session, bridged to the thread file by `agent-files-bridge` | **You, only** | Plan limits (interactive use) | Hands-on coding, pairing, anything you drive turn by turn |
| **2. Headless** (`headless`) | Claude Agent SDK / `claude -p`, Codex SDK / `codex exec`, any ACP agent | You or the system | Agent SDK monthly credit, then API rates; other vendors per their terms | Background agents, sub-threads, long autonomous tasks |
| **3. Direct** (`direct`) | Model API calls we make ourselves (multi-provider), or a local model | You (replay threads) or the system | API rates; free for local models | Replay conversation threads (the M1 runner), council, compaction, KB extraction, routing |
| — (`observed`) | Hooks mirror the status of a `claude` session you started by hand | — | Plan limits | M1: attention without a bridge |

### 5.1 Tier 1 — interactive bridge

- `agent-files-bridge` hosts `claude` in a detached tmux session per thread (attach any time to see the real TUI — it is never hidden from you) and is the thread's single writer.
- **Input:** the bridge (via a Claude Code **Channels** MCP server it runs) pushes your newly sent turn into the session. Fallback: `tmux send-keys` / `paste-buffer`.
- **Output:** the bridge writes the agent's reply from the channel's reply tool, and tool calls from the session transcript (`transcript_path`).
- **Status:** hooks append one line each to `events.jsonl`; the bridge applies them. `UserPromptSubmit`, `PreToolUse`, `PostToolUse` → `working`; `Notification` with `permission_prompt` → `blocked`; `idle_prompt` is ignored (it fires ~60 s after a finished turn, not when Claude needs you); `Stop` → `END` + `done`; a failure event (`StopFailure`, if present — verify at build time) → `END (failed)` + `failed`. Interrupts are handled by the bridge itself (§4.5 rule 2), since `Stop` is reported not to fire on a user interrupt (verify at build time).
- **Constraints:** tier 1 is resume-only (`context: resume`); no grounding is injected (use the project's `CLAUDE.md` instead); no snippet expansion (§4.5 rule 4).
- **Policy rule (hard):** the bridge forwards **only text a human wrote and sent** — your human region. It never forwards notes, child reports, council output, scheduled prompts or agent-to-agent messages. Those go through tier 2 or 3, or you copy what you want into your own turn. Agents in tier 1 are denied write access to `threads/` through Claude Code's permission rules, so a tool call can't write a fake human turn. This keeps tier 1 within "ordinary, individual usage" — the file is just a different keyboard.

### 5.2 Tier 2 — headless

- One long-lived client per thread (Claude Agent SDK `ClaudeSDKClient` or equivalent) — streaming input, `interrupt()`, `can_use_tool` callback → `? PERMISSION` line.
- Codex via its SDK / `codex exec --json` with thread resume.
- Prefer **ACP** (Agent Client Protocol) as the uniform boundary where an adapter exists (`claude-agent-acp`, `codex-acp`, Gemini, Copilot): one protocol to implement, many agents.

### 5.3 Tier 3 — direct

- Multi-provider client: `agent-files-run` (a script) in M1; ReqLLM if and when the Elixir supervisor exists.
- No tool loop; structured outputs; caching under our control; exact requests written to `steps/`.
- Proposed: this tier becomes the native loop (`runtime: native`, M6) with no tools and one step — one code path instead of two ([juggler analysis §6](docs/juggler-analysis.md#6-should-we-have-our-own-agent-loop)).

## 6. Context assembly

Every request we assemble (tiers 2–3) is built in a fixed order, most stable first, to maximize prompt-cache hits:

1. **Stable prefix** — the agent's system prompt, tool definitions.
2. **Grounding** — `accepted` KB nodes listed in `grounding:` plus their dependencies (depth-capped; one-line summaries beyond the cap).
3. **Carry** — the thread's `## carry` section, if any.
4. **Thread** — turns and notes in order.

Tier 1 assembles nothing: Claude Code owns its context.

### Resume vs. replay (per thread, `context:`)

- **resume** — the harness owns its session (`session` file); `thread.md` is a faithful mirror. Cheapest; full harness fidelity. Edits above `END` have no effect. The only mode tier 1 supports.
- **replay** — the file *is* the context; it is re-assembled each turn. Editing the file edits what the agent knows: delete a tangent, fix a wrong premise, replace 400 lines of output with a one-line summary. Required for switching models mid-thread.

**Cache economics.** On Anthropic's API a cache read costs ~0.1× base input, a write ~1.25× (5-min TTL) or 2× (1-hour TTL). Editing at position *k* re-writes everything after *k* once (~12.5× that suffix for one turn) plus latency. The default cache lives 5 minutes, so in human-paced threads it has usually expired anyway — replay edits are effectively free there. The cost is felt only in fast autonomous loops over a large prefix, where you are not editing.

### Against the "comprehensiveness assumption"

The habit of carrying an entire thread forward because everything said earlier *might* matter. A tightly scoped request in a clean context often does as well or better. Therefore:

- **Forking with a clean context is the default gesture.** You choose what to carry (yank lines into the child's `## carry` section); nothing is carried implicitly.
- **Settled conclusions are promoted to KB nodes.** New threads ground on nodes, not on old transcripts. Transcripts are scratch; the KB is memory.
- **Token count is visible** in the status line so the cost of carried context is felt.

## 7. Knowledge base (DAG)

`kb/<node id>.md`, one node per file. Node ids are bare slugs, used the same way everywhere (`grounding:`, `depends_on:`):

```markdown
---
type: claim             # fact | claim | ref | decision | question
status: accepted        # proposed | accepted | disputed | retracted
depends_on: [ref-0011, fact-0007]
sources: [https://…]
summary: Pool-per-request causes the auth timeout under load.
---
Body: evidence, reasoning, caveats.
```

- **Edges** are `depends_on`; a lint enforces acyclicity and dangling refs.
- **Agents propose, humans accept.** Agent-written nodes start `status: proposed`. Only `accepted` nodes are ever injected as grounding.
- **Provenance & invalidation.** Retract or dispute a node → walk its dependents → mark claims `disputed` → drop a note in the `inbox/` of every thread whose `grounding` reaches them.
- **Extraction** (tier 3): when a thread is closed or you ask, a cheap model proposes candidate nodes from the transcript for review.

## 8. Orchestration

**Branches — one spec, whoever creates them** (`:AgentsFork`, a `/fork` turn, or an agent spawning a sub-thread):

- A new subdirectory with a `thread.md` whose frontmatter sets `kind` (`fork` or `subthread`) and `branched_at: tN`, copies `agent`, `runtime`, `model`, `context` and `grounding` from the parent unless told otherwise, and has an optional `## carry` section. The parent's `session` is **never** copied.
- **Forks** are yours: they never report back.
- **Sub-threads** are spawned to do a task (an agent spawn defaults to `runtime: headless`). When the task is done — the sub-thread's agent ends a turn declaring it final, or you run `:AgentsClose` — its runtime sets `closed` and writes its final turn as a note into the parent's `inbox/`.
- **Report back:** the parent's runtime consumes `inbox/` at the start of its next turn, writing each note as a `## note · <source>` section before its `## agent` header. In a tier-1 parent, notes are shown to you but never forwarded (§5.1).

**Council** (tier 3, or tier 2 if reviewers need to run the code): the same diff + grounding fans out to N models → `<thread>/reviews/<model>.md`; an aggregator writes `<thread>/reviews/synthesis.md` listing agreements, disagreements, and singletons, and drops a note in the thread's `inbox/`. It surfaces disagreement; it does not vote. Caveats: ~N+1× cost; correlated blind spots across similarly trained models.

## 9. Implementation — scripts first, Elixir/OTP + Jido as the target

**Gate:** the Elixir supervisor is not built in M1. M1 runs on scripts; the supervisor moves to Elixir only after the M1 trial passes *and* one of the triggers in [m1-plan §6](docs/m1-plan.md#6-triggers-for-the-elixir-supervisor) is real — many concurrent agents, crash-recovery pain, multiple machines, or long-lived tier-2 sessions. The file format is the contract, so the swap never touches a thread.

### 9.1 Executables

| Executable | Does | Milestone |
|---|---|---|
| `agent-files-run` | Runtime for `direct` replay threads (and later `native`); single writer of those threads | M1 |
| `agent-files-hook` | Claude Code hook: `observed` status in M1; event lines into `events.jsonl` for the bridge from M2 | M1 |
| `agent-files-stats` | Trial measurement from git history and `threads/` | M1 |
| `agent-files-bridge` | Tier-1 runtime: hosts `claude` in tmux, runs the Channels server, single writer of tier-1 threads | M2 |
| `agent-files-ring` | Rings editors (path + event); always exits 0 by design | M3 |
| `agent-files-notify` | Escalation when no editor answers (OS notification) | M3 |
| supervisor | Owns `headless` threads, spawning, the inbox, the Notifier; scripts first, Elixir when a trigger fires | M3 |

### 9.2 Elixir target

**Target:** Elixir core with Jido 2; harnesses behind a process boundary.

Why: the daemon's job is supervising many long-lived processes, routing messages between them, surviving crashes, and spanning machines — the BEAM's home turf. Agents-as-data (Jido's struct + `cmd/2` → directives) matches "an agent is a declaration". The official SDKs are thin wrappers over CLI JSONL protocols, so the integration surface is subprocess + JSON lines either way.

Tradeoff accepted: official Claude/Codex SDKs are Python/TypeScript-first and track CLI changes fastest. Mitigation: talk **ACP** over a Port where an adapter exists; otherwise run a **tiny TS sidecar** per harness using the official SDK, speaking newline-delimited JSON to the BEAM. Swapping a sidecar never touches the core.

```
AgentFiles.Application
├── FileWatcher            (threads/, kb/, agents/ → signals)
├── ThreadRegistry
├── ThreadSupervisor       (DynamicSupervisor)
│   └── ThreadServer       (Jido AgentServer, one per thread; the thread's single writer; state rebuilt from files on restart)
│       └── Runtime        (Port: bridge | ACP | sidecar | ReqLLM)
├── KB                     (graph index, lint, invalidation)
└── Notifier               (on status changes: rings editors via agent-files-ring; escalates via agent-files-notify)
```

Directives (side effects as data): `AppendToThread`, `SetStatus`, `SpawnChild`, `RunHarness`, `CallModel`, `AskPermission`, `Interrupt`.

Remote machines: a node per machine; distributed Erlang gives one view across them. A looser setup syncs the root via git or Syncthing — then at most one machine may run a runtime for a given thread (see §12 on locks).

## 10. Neovim client — `agents.nvim`

Runs in Ghostty. tmux hosts tier-1 TUI sessions (detached, attachable), not the editor.

- **Watcher:** a `vim.uv.new_fs_event` watch per thread directory (recursive watching is not available on every OS); `autoread`/`checktime` for open buffers.
- **Tabline:** per-thread state from `status` and `seen`, e.g. ` 1 api ⠋   2 docs ●   3 tests ✓ ` (spinner working, red dot blocked, check done-unseen).
- **Attention:** `vim.notify` popup + terminal bell when a thread becomes `blocked` or `failed`.
- **Quickfix:** `:AgentsBlocked` fills the quickfix list with one entry per blocked thread, pointing at its `? PERMISSION` line (or at the thread, for observed sessions).
- **Locking and drafts:** buffer read-only while `working`; on reload, unsaved drafts are re-applied below the new last `END` (§4.5 rule 1).
- **Folds:** by indentation — each `▸` line folds the output beneath it.
- **Acknowledge:** viewing a thread touches its `seen` file.
- **Needs-you jump:** `:AgentsNext` jumps to the next blocked thread's question (the quickfix list's `:cnext`).
- **Commands that write files:** `:AgentsSend` (append `END`, save), `:AgentsStop` (`touch STOP`), `:AgentsNew` (thread directory + `## you · t1`), `:AgentsFork` (branch per §8, selection → `## carry`), `:AgentsClose` (close a sub-thread), `:AgentsPrune` (`rm -r` a branch), `:AgentsGrep` (`rg` across `threads/` into quickfix). Each has a plain-shell equivalent; the full table is in [role-of-neovim §7](docs/role-of-neovim.md#7-the-other-direction-neovims-only-output-is-files).

### 10.1 Neovim's RPC server — a doorbell, not a mailbox

Every Neovim instance runs a msgpack-RPC server (its address is `v:servername`; pin it with `nvim --listen <socket>`), and Neovim exports that address as `$NVIM` into every `:terminal` job.

Its role here is deliberately narrow:

- **Doorbell.** Ringers (the Notifier, a tier-1 hook, an extension) run `agent-files-ring <absolute thread path> <event>`, which calls `ring(path, event)` in each matching editor to say "re-read this thread now". The payload is a path and an event name, never content.
- **Focus control.** Open a thread in a tab, jump to a blocked question, bring forward the agent that just needed you.
- **Identity.** A `claude` started in Neovim's own `:terminal` inherits `$NVIM`, so its hooks know which editor to ring.

What it is not: a store, a message transport, or a requirement. All state goes through files (principles 1, 8, 9). If no Neovim is running or the call fails, nothing is lost — the file watcher catches up. Locally `fs_event` already reacts in milliseconds, so the doorbell's value is *actions* (focus, jump) and shared network mounts where change events are slow or missing — not synced folders, where the ring can arrive before the content does.

Optional: a headless `nvim --headless --listen <addr>` on a remote machine can hold the editor session, and a laptop attaches with `nvim --remote-ui --server <addr>` — the editor's equivalent of `tmux attach`.

Who rings, for whom, when, and what happens if nobody answers: [docs/role-of-neovim.md](docs/role-of-neovim.md). Not built in M1: locally the file watcher is enough.

## 11. Relation to Herdr

| Herdr feature | Here |
|---|---|
| Needs-you status (OSC 7501) | Runtimes and hooks → `status` files; tabline + quickfix |
| `hc run --bg`, `hc send`, reports back | Sub-thread directories inside the parent's; reports via `inbox/` |
| herdr-core persistence | Runtimes outlive the editor; **plus** resumable after reboot (files + `session`) |
| SSH machines in one sidebar | BEAM nodes or a synced root |
| Config as files edited by agents | Config as files (`agents/`, `snippets/`) that *you* own; agents may propose changes as notes |
| GPU terminal (libghostty) | **Not ours** — use Ghostty/tmux |
| Status for arbitrary terminal programs | **Not ours** — only for programs that report |

## 12. Open questions

1. **Channels** is a research preview: protocol stability; whether the reply tool alone suffices or transcript tailing is needed; how permission prompts surface through it — and so how tier-1 permissions could move into the file.
2. Claude Code hook behaviour the bridge relies on — whether `Stop` fires on interrupt, the name of the failure event — to verify against current docs at M2.
3. Default `context:` mode — resume for code threads, replay for discussion threads?
4. Maturity of Elixir clients for Claude/Codex vs. ACP vs. TS sidecars — decide per harness at M3.
5. KB granularity and how much grounding to inline vs. summarize.
6. Codex and other vendors' terms for headless use on consumer plans.
7. A native agent loop for API and local models — recommended in a deliberately small form; see [docs/juggler-analysis.md](docs/juggler-analysis.md#6-should-we-have-our-own-agent-loop).
8. Which Juggler borrowings to adopt beyond branching-as-directories (intra-turn states, an approval rules file, budgets, worktree workspaces) — see the same doc.
9. Locks across machines: with a synced root, how do two machines agree which one runs a thread — an advisory `lock` file naming the host, or "runtimes only on one machine"?
10. How a sub-thread's agent declares its turn final (a structured marker, a tool call, or always one task per sub-thread).

## 13. Milestones

- **M0** — these documents.
- **M1 — thesis trial** ([docs/m1-plan.md](docs/m1-plan.md)): the thread format, `agent-files-run` (direct replay, no tools), minimal `agents.nvim`, `observed` status for ordinary `claude` sessions, measurement; ten working days of use; then a go/no-go decision against criteria fixed in advance.

Everything below happens only if M1 says go, in an order the trial's results suggest:

- **M2** — tier-1 bridge (`agent-files-bridge`): tmux host, Channels input, single-writer output, interrupt via Escape, hook events.
- **M3** — supervisor + tier 2 (Claude, Codex) with `? PERMISSION` lines, `STOP`, sub-threads and the inbox; the doorbell (`agent-files-ring`, registry, `agent-files-notify`). On scripts first; Elixir when an m1-plan §6 trigger fires.
- **M4** — tier 3 + council.
- **M5** — KB: nodes, lint, grounding, proposals, invalidation.
- **M6** *(proposed)* — native loop for API/local models (`runtime: native`), grown from `agent-files-run`, writing every request to `steps/`.
