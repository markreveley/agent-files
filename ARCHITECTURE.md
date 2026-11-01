# agent-files — Architecture

> Status: draft v0.5 · 2026-11-01 · this document describes the **target** architecture; what gets built is gated by the M1 trial ([docs/m1-plan.md](docs/m1-plan.md)).
> Collapse the agent interface down to **files, processes, and an editor**.
> **Adopt before building.** Planned work that an existing tool already does is dropped from the plan and the tool is used instead; the tool that covers the most goes first. v0.5 applies this: TUIOS hosts harness sessions and owns attention for them, which removes the tier-1 bridge, the doorbell and the Elixir supervisor ([docs/host-analysis.md](docs/host-analysis.md)).
> Supplemental: [docs/m1-plan.md](docs/m1-plan.md) — the M1 trial and go/no-go criteria · [docs/m1-build-spec.md](docs/m1-build-spec.md) — the first M1 build, specified · [docs/host-analysis.md](docs/host-analysis.md) — TUIOS, herdr, cmux, workmux, parrot.nvim and Pi Durable graded against this plan · [docs/related-repos.md](docs/related-repos.md) — what we take from itsjustshell2, elixir-mind, socrates, manifold and artifact-dag · [docs/juggler-analysis.md](docs/juggler-analysis.md) — reference comparison, storage format tradeoff, own agent loop · [docs/role-of-neovim.md](docs/role-of-neovim.md) — Neovim's role · [docs/view-layer.md](docs/view-layer.md) — readable text in Neovim, rich HTML view in the browser.

## 1. Thesis

Most agent UIs are chat panels bolted onto a harness. Here we flip that:

- A **thread is a file** — `thread.md`, in a directory of its own. The conversation, tool calls and permission questions live in plain markdown on disk; live state (status, session) sits beside it in tiny sidecar files.
- An **agent is a declaration** (a file naming its runtime, model, tools, permissions and grounding). The **process** that runs it is ephemeral — it exists only while there is work to do.
- **Neovim is a viewer/editor**, not the host. It watches files, shows status, and is where you write. Anything else that can read files (`grep`, `cat`, a phone reading a synced folder) is also a client.
- **Memory is files too:** threads are scratch; durable knowledge is promoted into a small DAG knowledge base that new threads are grounded in.

Unix analogy: program vs. process. The file is the program and its state; the runner is just a process.

### Non-goals

- Being a terminal. Ghostty renders. Interactive TUIs (lazygit, an agent's own TUI) stay in a real terminal.
- Being a session host or the attention layer for harness TUIs. **TUIOS** hosts `claude` and `codex` sessions (detach, attach, survive the terminal app), tracks their state, holds the needs-you Inbox across sessions and machines, and manages worktrees per agent. herdr is the fallback. See §5.1 and §12.
- Being the main coding harness. Claude Code, Codex, etc. own the heavy coding loop. We do not modify, wrap or proxy them. We sit beside them and own *context assembly for the threads we run, the record, the knowledge base and enforcement*. A small native loop for lighter, transparent work is proposed separately (see the supplemental analysis).

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
12. **Review is enforcement.** What a machine can check, a machine checks while the code is written; the guarantee lives in the outermost ring that can enforce it, and humans own the checks (§9).

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
| Check | An executable every change must pass, run in the agent's loop, at commit, before merge (§9) | listed in the code repo's `.agent-files/checks.toml`; results in `threads/<id>/checks/` |
| Exception | A human decision to let one turn end with a check failing (§9.5) | a `? EXCEPTION` line and its answer, recorded in `checks/` and the commit |

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
        ├── checks/                # check results per agent turn (§9.5)
        │   └── t0007.json
        ├── commits                # commits made from this thread, one per line (§9.6)
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
runtime: headless       # observed (tier 1, M1) | headless | direct | native (proposed, M6)
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
| `? EXCEPTION eN <check> "<reason>" [grant/deny]` | the runtime | The agent asks to end its turn with a check failing (§9.5) |
| `> grant` / `> deny` | you, on the line directly below it | Your answer |

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
| `checks/`, `commits` (own thread) | the thread's runtime | — |
| `.agent-files/checks.toml` and other protected paths (in the code repo) | — (agents are denied) | you, by commit (§9.4) |
| New branch directories | whoever creates the branch (§8) | you, via `:AgentsFork` or `mkdir` |

### 4.5 Rules

1. **Locking.** While `status` is `working`, the editor makes the buffer read-only. During a turn the runtime is the only writer of `thread.md`; if it detects a foreign write (the file changed in a way it didn't), it stops, saves its remaining output to `out/`, closes with `END (conflict)` and sets `interrupted`. If an editor holds unsaved text when the runtime writes, the plugin reloads the file and re-applies your draft below the new last `END` — no "file changed" prompt.
2. **Interrupt.** Create `STOP` in the thread's directory (`touch`, or `:AgentsStop`). The runtime stops the turn (SDK `interrupt()` / native cancel), closes with `END (interrupted)`, sets `interrupted`, and deletes `STOP`. Tier 1 has no agent-files runtime: interrupt in the TUI itself (Esc), through TUIOS.
3. **Crash recovery.** When a runtime starts, any thread it owns whose `status` is `working` with no live owner gets `END (interrupted)` and its `status` becomes `interrupted`. You then **resume** (send a new turn, e.g. "continue") or **discard** (delete the partial agent turn by hand — the buffer is writable once the turn is closed).
4. **Snippets.** In tiers 2–3 a leading `/name args` line is expanded from `snippets/` (or `.claude/commands/`, skills) before sending. In tier 1 you type into Claude Code itself, which expands its own commands.
5. **Session actions.** `/fork` creates a branch exactly as `:AgentsFork` does (§8). `/clear` in replay mode starts a fork with an empty `## carry`. `/compact` is compaction (rule 9 below). In tier 1 these are Claude Code's own commands.
6. **Tool calls** are one-line `▸` summaries with output indented beneath (folded by indentation in Neovim) or moved to `out/` and linked. All folds closed = the collapsed natural-language transcript.
7. **Permissions (tiers 2–3).** The runtime writes one `? PERMISSION pN …` line, sets `blocked`, and waits; there is at most one pending question per thread. You answer `> y`, `> n` or `> always` on the line below it and save — the one place you write inside an agent turn, safe because the runtime is waiting, not writing. `always` allows that exact tool call pattern for the rest of the runtime's process (a persistent rules file is proposed; [juggler analysis §3](docs/juggler-analysis.md#3-what-we-borrow--translated-to-files)). Tier-1 permissions are answered in the TUI, or from the TUIOS Inbox (§5.1).
8. **Status.** Only the thread's runtime writes `status`. "Idle" is not a status: a thread whose `status` file is older than its `seen` file is shown as idle. `closed` is terminal and applies to sub-threads (§8).
9. **Compaction** is the one machine rewrite above `END`: an explicit operation the runtime performs while holding the turn (its `status` is `working`), moving the replaced turns to `archive/` and recording a `## note · compaction`. Turn ids of surviving turns are unchanged.

## 5. Runtimes — three tiers

| Tier (`runtime:`) | Mechanism | Who authors turns | Billing (Claude, as of 2026-10) | Use for |
|---|---|---|---|---|
| **1. Interactive** (`observed`) | Real `claude` / `codex` TUI hosted in **TUIOS**; you type in the TUI. agent-files observes it through hooks and writes no turns | **You, only**, in the TUI | Plan limits (interactive use) | Hands-on coding, pairing, anything you drive turn by turn |
| **2. Headless** (`headless`) | Claude Agent SDK / `claude -p`, Codex SDK / `codex exec`, any ACP agent | You or the system | Agent SDK monthly credit, then API rates; other vendors per their terms | Background agents, sub-threads, long autonomous tasks |
| **3. Direct** (`direct`) | Model API calls we make ourselves (multi-provider), or a local model | You (replay threads) or the system | API rates; free for local models | Replay conversation threads (the M1 runner), council, compaction, KB extraction, routing |

**Where agent-files touches a harness.** Only at the harness's own published extension points, never by wrapping or driving its UI: Claude Code hooks in `~/.claude/settings.json` (tier 1 status, ring-0 checks, §9.2), SDK or CLI calls we make ourselves (tier 2, and the `claude -p` backend of tier 3), and git hooks in the code repo (§9.6). Hosting, input, screen capture and attention for harness TUIs are TUIOS's (§12).

### 5.1 Tier 1 — harness TUIs in TUIOS

The tier-1 bridge (`agent-files-bridge`: tmux hosting, Channels input, transcript output) is dropped (2026-11-01). Tier 1 is resume-only by nature — Claude Code owns its context — so editing the file could never change what the agent sees, and a bridge would have bought a second keyboard and a mirror at the cost of the most fragile code in the plan.

- **Host: TUIOS**, pinned to a known version. It keeps `claude` / `codex` running in daemon sessions you detach from and attach to at will, and owns the Inbox (everything waiting on you, across sessions and machines), alerts, seen marks, per-agent worktrees (`tuios worktree`, `ship`) and remote hosts (`tuios hosts`). herdr (core for hosting, its TUI for attention) is the fallback; plain tmux also works, without attention. Grades and caveats: [host-analysis](docs/host-analysis.md).
- **agent-files' part: the `observed` thread.** `agent-files-hook` (Claude Code hooks) creates `threads/_observed/<project>-<session>/` and writes its `status` — the record, the fallback measure in the M1 trial, and a source for `agents.nvim`. `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure` → `working`; `PermissionRequest` (the moment the dialog opens) or `Notification` with `permission_prompt` → `blocked`; `idle_prompt` ignored (it fires ~60 s after a finished turn); `Stop` → `done`; `StopFailure` → `failed`; `SessionEnd` → the directory is removed. `Stop` does not fire on Esc (documented), so an interrupted session stays `working` until its next event (TUIOS has the same gap). No turns are written: the transcript stays in the harness (`transcript_path`). A markdown mirror of it is deferred until H3 shows it is wanted.
- **Coexisting with TUIOS's integration.** `tuios integration install` adds its own hook entries to `~/.claude/settings.json` and removes only its own (it backs the file up as `settings.json.tuios.bak`); `agent-files-hook` entries are left alone, and Claude Code runs both. `[agents.approvals]` off is simplest. If it is on, TUIOS holds `PermissionRequest` for up to 300 s and the dialog and its `Notification` never appear; the observed status still shows `blocked`, because `agent-files-hook` maps `PermissionRequest` itself.
- **Adapter rule.** Anything agent-files does with TUIOS goes through its JSON CLI from one module, so switching to herdr changes one file. M1 needs none.
- **Constraints:** resume-only (`context: resume`); no grounding is injected (use the project's `CLAUDE.md` instead); no snippet expansion (§4.5 rule 4).
- **Policy rule (hard):** only text a human wrote enters a tier-1 session. Never use the TUIOS (or herdr) features that type agent-written text into a pane: `ask-agent`, `send-agent-message`, agent mail and the delivery queue (herdr: `hc` notes into a parent, so run it with notes off). `fan` and `send-text` carrying your own prompt are fine. Notes, child reports, council output, scheduled prompts and agent-to-agent messages go through tier 2 or 3, or you copy what you want into the TUI yourself. Agents in tier 1 are denied write access to `threads/` through Claude Code's permission rules. This keeps tier 1 within "ordinary, individual usage".

### 5.2 Tier 2 — headless

- One long-lived client per thread (Claude Agent SDK `ClaudeSDKClient` or equivalent) — streaming input, `interrupt()`, `can_use_tool` callback → `? PERMISSION` line.
- Codex via its SDK / `codex exec --json` with thread resume.
- Prefer **ACP** (Agent Client Protocol) as the uniform boundary where an adapter exists (`claude-agent-acp`, `codex-acp`, Gemini, Copilot): one protocol to implement, many agents.
- Before building any of this (M3), check what already exists: TUIOS runs headless ACP and Codex protocol panes (`start-agent --protocol acp|codex`), Claude Code has its own subagents, and Pi can run as a harness for non-Claude models (§13 Q12–Q13).

### 5.3 Tier 3 — direct

- Multi-provider client: `agent-files-run` (a script).
- No tool loop; structured outputs; caching under our control; exact requests written to `steps/`.
- Proposed: this tier becomes the native loop (`runtime: native`, M6) with no tools and one step — one code path instead of two ([juggler analysis §6](docs/juggler-analysis.md#6-should-we-have-our-own-agent-loop)).

## 6. Context assembly

Every request we assemble (tiers 2–3) is built in a fixed order, most stable first, to maximize prompt-cache hits:

1. **Stable prefix** — the agent's system prompt, tool definitions.
2. **Grounding** — `accepted` KB nodes listed in `grounding:` plus their dependencies (depth-capped; one-line summaries beyond the cap).
3. **Carry** — the thread's `## carry` section, if any.
4. **Thread** — turns and notes in order.

Tier 1 assembles nothing: Claude Code owns its context.

**No silent caps.** When assembly drops or summarizes anything — grounding beyond the depth cap, an output replaced by its summary — the request carries one line saying what was left out and how much, and `steps/` records it. A reader of a turn can always tell what the model did not see.

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
status: accepted        # proposed | accepted | disputed | retracted | superseded
depends_on: [ref-0011, fact-0007]
supports: []            # optional typed edges: supports | contradicts | refines
revises: null           # the node this one supersedes, if any
sources: [https://…]
summary: Pool-per-request causes the auth timeout under load.
---
Body: evidence, reasoning, caveats. [[fact-0007]] in the body is a mention edge.
```

- **Edges.** `depends_on` carries provenance and invalidation. `supports`, `contradicts` and `refines` are typed edges for argument structure; `[[id]]` in a body is a `mentions` edge. The lint enforces acyclicity over `depends_on`, `supports` and `refines` (`contradicts` and mentions may cycle) and fails on dangling refs. Lint rules are Datalog in `kb/lint.dl`, run by a small standard-library evaluator; the same rules express the retraction walk and the §9.7 checks. (Edge vocabulary and Datalog lint from artifact-dag; [related-repos](docs/related-repos.md).)
- **Agents propose, humans accept — by construction.** An agent's proposal has no `status` field: the schema the model fills in does not contain one, and the runtime writes `status: proposed`. A node you write yourself is accepted when you write it. Only `accepted` nodes are ever injected as grounding.
- **The gate.** A proposal is linted (cycles, dangling refs, undefined terms) *before* it is stored. Errors go back to the model as structured data for at most two repair rounds; then the attempt fails loudly and the rejected candidate is kept in `kb/_rejected/` (it doubles as an eval set). A proposal's `depends_on` may cite only nodes that were in its grounding; anything else is dropped and noted. (From socrates.)
- **Supersession, not editing.** Changing what an accepted node claims means a new node with `revises:`; the old one becomes `superseded`. "What did we believe in August" stays answerable from files.
- **Evidence.** A `fact` needs `sources:` that resolve (a URL or a `ref` node); the lint checks it. (From elixir-mind's `verified_by` rule.)
- **Reading-pace check.** Accepting is only meaningful if you read. The KB tooling (M5) warns when the rejection rate falls to about zero or many accepts land within seconds. It catches stopped reading, not shallow reading.
- **Provenance & invalidation.** Retract or dispute a node → walk its dependents → mark claims `disputed` → drop a note in the `inbox/` of every thread whose `grounding` reaches them. Built only after proposals are being accepted at reading pace (M5b, §14).
- **Extraction** (tier 3): when a thread is closed or you ask, a cheap model proposes candidate nodes from the transcript; they pass the gate, then wait for you.

## 8. Orchestration

**Branches — one spec, whoever creates them** (`:AgentsFork`, a `/fork` turn, or an agent spawning a sub-thread):

- A new subdirectory with a `thread.md` whose frontmatter sets `kind` (`fork` or `subthread`) and `branched_at: tN`, copies `agent`, `runtime`, `model`, `context` and `grounding` from the parent unless told otherwise, and has an optional `## carry` section. The parent's `session` is **never** copied.
- **Forks** are yours: they never report back.
- **Sub-threads** are spawned to do a task (an agent spawn defaults to `runtime: headless`). When the task is done — the sub-thread's agent ends a turn declaring it final, or you run `:AgentsClose` — its runtime sets `closed` and writes its final turn as a note into the parent's `inbox/`.
- **Report back:** the parent's runtime consumes `inbox/` at the start of its next turn, writing each note as a `## note · <source>` section before its `## agent` header. Tier-1 sessions have no `thread.md` turns, so they get no notes; you read the child and type what you want into the TUI (§5.1).
- **Not ours:** sub-agents and fan-out *between harness TUIs* (TUIOS `start-agent`, `fan`, `compare`), and Claude Code's own subagents. agent-files sub-threads are for headless and direct work whose record should be files.

**Council** (tier 3, or tier 2 if reviewers need to run the code): the same diff + grounding fans out to N models → `<thread>/reviews/<model>.md`; an aggregator writes `<thread>/reviews/synthesis.md` listing agreements, disagreements, and singletons, and drops a note in the thread's `inbox/`. It surfaces disagreement; it does not vote. Caveats: ~N+1× cost; correlated blind spots across similarly trained models.

## 9. Enforcement — review while writing, guarantees at the edges

**Thesis.** The real review steps are the ones a machine can repeat: types, tests, architecture rules, policies, proofs. They run *while* code is written, inside the agent's loop, so a human never sees a turn that fails them. Then they run again at the repository and infrastructure level, where no agent can switch them off. Review by a person shrinks to what only a person can judge: intent, specs, decisions, and exceptions. Every change carries its reasoning (thread, turn, decisions, check results) as plain files and git metadata. No new storage format or external service is involved.

**Placement: a layer, not a tier.** Tiers (§5) say *who runs the agent*. Enforcement says *what every change must satisfy*, whoever made it. So it wraps every tier — and it also applies to commits made with no agent and no agent-files at all.

### 9.1 Rings

Enforcement is arranged in rings, from the agent's loop outward. **Inner rings are for speed; outer rings are for truth.** Every guarantee must be enforced at the outermost ring that can enforce it. Inner rings run the same checks earlier, as feedback, and are never the only enforcement.

| Ring | Where | Runs | Can an agent bypass it? | Purpose |
|---|---|---|---|---|
| **0. Loop** | Inside the thread's runtime, per tier (§9.2) | Fast checks, on each edit and at the end of each agent turn | In principle (same machine, same user) | Instant feedback; the agent fixes failures before you see the turn |
| **1. Repository** | Git hooks in the code repo (`pre-commit`, `commit-msg`) | Fast and medium checks, at each commit | Yes (`--no-verify`) | Cheap gate for every commit, agent or human |
| **2. Infrastructure** | CI required checks, branch protection, merge queue, CODEOWNERS, policy-as-code | The full required set, before merge, on clean machines | **No** — needs credentials the agent doesn't have | The guarantee |
| **3. Runtime** | Deploys and production | Canaries, feature flags, SLO-gated rollout, automatic rollback, runtime monitors from the same specs | No | Enforcement after merge (§9.8) |

Ring 2 never trusts rings 0–1. It re-runs every required check; their records (§9.6) are evidence for the reader, not proof.

### 9.2 Ring 0 in each tier

| Tier | Mechanism | On a failure |
|---|---|---|
| **1. Interactive** | Claude Code hooks, configured from `checks.toml` by `agent-files-check install`: `PreToolUse` denies writes to protected paths; `PostToolUse` runs `edit` checks on changed files; `Stop` runs `turn` checks and blocks the stop with the failure as its reason, so Claude keeps working (guard against loops with the hook's stop-active flag; verify hook behaviour at build time). The same hooks work whether the session runs in TUIOS, herdr, tmux or a bare terminal. TUIOS's own hooks only observe and cannot block a turn, so ring 0 stays in Claude Code's hooks. | Feedback goes through Claude Code's own hook channel, set up by you, so the tier-1 policy rule (§5.1) still holds. |
| **2. Headless** | SDK hooks and `can_use_tool`: protected paths denied, checks run after edits and before the turn ends. | The runtime sends the failure to the agent as a tool result or a follow-up turn; the attempt is logged in `checks/` |
| **3. Direct** | Changes no code, so nothing to enforce. The council (§8) sits here: it is a probabilistic review, useful for raising concerns, never a gate. | — |
| **Native** (M6) | Built in: after each edit tool call, `edit` checks; before writing `END`, `turn` checks. | The loop feeds the failure back as the next step; only a green or excepted turn reaches `END` |

In every tier: a turn may end only when its blocking `turn` checks pass, or with an open exception question (§9.5).

### 9.3 The checks file

One per code repo, **owned by you**: `.agent-files/checks.toml`. It lists checks; it does not implement them. A check is any executable (principle 3): a test runner, a linter, an architecture rule tool, a proof checker.

```toml
protected = ["tests/**", ".github/**", ".agent-files/**", "specs/**"]   # agents may not write these

[[check]]
id       = "types"
run      = "npm run typecheck"
on       = ["edit", "turn", "commit", "merge"]    # edit | turn | commit | merge | deploy
level    = "block"                                 # block | warn
timeout  = "60s"
protects = ["decision-0007"]                        # KB decisions this check enforces (§9.7)

[[check]]
id       = "layers"
run      = "npx depcruise src --config .dependency-cruiser.js"
on       = ["turn", "commit", "merge"]
level    = "block"
protects = ["decision-0003"]                        # "UI never imports from db/"

[[check]]
id       = "mutation"
run      = "npx stryker run --incremental"
on       = ["merge"]
level    = "block"
```

`agent-files-check <trigger> [--paths …]` runs the checks for one trigger and prints one JSON result per check (`id`, `status`: `pass | fail | error | skipped`, `duration_ms`, `summary`, `output` path). It exits non-zero if any blocking check failed. The same executable runs in every ring: from hooks, from git hooks, and in CI. So "what passed on my machine" and "what CI requires" are the same list.

### 9.4 Who checks the checks

If an agent writes both the code and its tests, enforcement is circular. Agents under pressure weaken assertions, delete failing tests, widen types or skip a rule. The answer extends principle 10: **humans own the oracles.**

- **Protected paths.** Tests that act as oracles, specs, policies, CI config and `checks.toml` itself are listed in `protected`. Ring 0 denies agent writes to them. Ring 2 enforces it for real: CODEOWNERS makes your approval required on any change to those paths. A deny rule on the same machine is a convenience; the merge rule is the boundary.
- **Agents propose, humans accept.** An agent that wants a new test or rule writes it as a proposal (a patch under `out/`, or a KB node with `status: proposed`). It enters a protected path only through your commit.
- **Anti-gaming checks**, shipped as ordinary checks:
  - a diff check that fails when a change deletes tests, removes assertions, adds skips, or loosens types (`any`, `# type: ignore`, `@ts-expect-error`) without an exception;
  - mutation testing on the changed code, so tests that pass but test nothing are caught;
  - coverage measured on the diff, not the whole repo.
- **Check the checks.** A property test mutates a known-good input once per rule and asserts that the check responsible for that rule fails. A check that never fires on a mutation protects nothing. (From itsjustshell2.)
- **Checks are versioned with the code.** A check changes only by a commit to a protected path, so `git log .agent-files/` is the audit trail of what the rules were and when.

### 9.5 Results, feedback, exceptions

- **Results are files.** Each ring-0 run writes `threads/<id>/checks/tNNNN.json` (the turn's results) and one fold line in the agent's turn: `▸ check types, layers: pass` or `▸ check layers: fail (2 violations → checks/t0007.json)`.
- **Failures carry their reason.** When a check fails, the runtime gives the agent the failure *and* the text of every decision the check protects (§9.7). The agent fixes the problem knowing why the rule exists, not just that it fired.
- **Exceptions are questions.** When the agent cannot or should not satisfy a check, it asks:

  ```
  ? EXCEPTION e1 layers "SettingsPanel reads db/config directly; the config service doesn't exist yet" [grant/deny]
  > grant
  ```

  The runtime sets `blocked` and waits, exactly like a permission question (§4.5 rule 7). `> grant` lets the turn end with the check failing. Granted exceptions are recorded in the turn's `checks/` file and in the commit's record (§9.6). Ring 2 still fails, so the exception shows up on the PR as the one thing you need to look at. An exception is temporary by default; making it permanent means changing `checks.toml`.

### 9.6 Records: linking commits, threads and checks

The point of a record is that a change can be explained after the fact, from text files and git alone.

- **Commit → thread.** Commits made from a thread carry trailers, added by a `prepare-commit-msg` hook that `agent-files-check install` sets up:

  ```
  Agent-Files-Thread: fix-auth-timeout/retry-logic
  Agent-Files-Turn: t7
  Agent-Files-Decision: decision-0007
  Agent-Files-Exception: layers e1
  ```

  The hook finds the thread from the tier-1 or observed session running in that repo. `git log --format='%(trailers:key=Agent-Files-Thread)'` lists the threads that changed the code; `git blame` → commit → thread → turn explains a line.
- **Thread → commits.** A `commits` sidecar in the thread directory, one line per commit (`<repo> <sha> <subject>`), written by the thread's runtime (principle 11).
- **Commit → checks.** `agent-files-check` attaches its results for each commit as a git note under `refs/notes/agent-files/checks` (JSON: checks, versions, results, exceptions). Notes can be read with `git notes show`, survive rebases with `notes.rewriteRef`, and are pushed explicitly.
- **The PR, read this way:** linked threads (the intent and the conversation), the decisions it touches, the check record, and the list of exceptions. Reading the diff becomes optional; reading the exceptions does not.

### 9.7 Decisions and checks (the KB link)

KB `decision` nodes (§7) and checks point at each other:

```markdown
---
type: decision
status: accepted
summary: The UI layer never imports from db/.
enforced_by: [layers]          # check ids in checks.toml
implemented_by: [api@3f9c2e1]  # commits, filled in from commit trailers
---
```

- A KB lint compares the two sides: a check that protects a missing or retracted decision is a warning; an accepted decision with no `enforced_by` is listed as **soft** — written down, but not enforced.
- **The residue list.** The same applies to rules that are not KB nodes: every rule in a repo's standing instructions (`AGENTS.md`, `CLAUDE.md`) names the check that arms it, or is listed as residue — a rule only a reader enforces. The residue list is the honest size of what review still has to catch. (From itsjustshell2.)
- **Invalidation reaches code.** Retracting or disputing a decision (§7) also lists its checks (drop or change them) and its `implemented_by` commits (review or revert), and drops a note in the threads that relied on it.
- A check failure in any ring links straight to the decision it protects, so the reason for a rule is one hop from its failure.

### 9.8 Formal methods, and after merge

- **Formal proof is for small cores.** Proving a whole application is not realistic. Proving a protocol (TLA+), a state machine, a permission model or a money-handling path (Dafny, Lean, Kani, refinement types) is, and agents make writing specs cheaper. The spec lives in a protected path, so it is the thing you review; the proof checker is an ordinary check. Contracts and property-based tests are the middle ground for everything else.
- **Ring 3, after merge.** The same specs can generate runtime monitors (invariant assertions, contract checks in production builds), and deploys are gated: canary, feature flag, SLO-gated rollout, automatic rollback. An incident closes the loop through the records: the alert names a check or invariant → its decision → a KB dispute → invalidation reaches the commits and threads that depended on it (§9.7).

### 9.9 The cat test

Everything here is a file or git metadata: `checks.toml`, `checks/*.json`, the `commits` sidecar, commit trailers, git notes, KB front matter. Checks are executables. No enforcement depends on agent-files running: ring 2 is ordinary CI calling `agent-files-check merge`, and a repo that drops agent-files keeps its checks.

## 10. Implementation — scripts

Everything agent-files runs is a script: stdlib Python for the core pieces, Lua for the plugin. The file format is the contract, so any script can be replaced without touching a thread.

### 10.1 Executables

| Executable | Does | Milestone |
|---|---|---|
| `agent-files-run` | Runtime for `direct` replay threads (and later `native`); single writer of those threads | M1 |
| `agent-files-hook` | Claude Code hook: `status` of `observed` (tier-1) threads | M1 |
| `agent-files-stats` | Trial measurement from git history and `threads/` | M1 |
| `agent-files-grep` | Logged `rg` across `threads/` | M1 |
| `agent-files-check` | Runs the checks for one trigger and prints JSON results; `install` sets up hooks, git hooks and commit trailers in a code repo (§9) | M7 (a probe earlier) |
| supervisor | Owns `headless` threads, spawning, the inbox; a script | M3 (deferred) |

**Dropped (2026-11-01):** `agent-files-bridge` (tier 1 is hosted by TUIOS, §5.1), and the doorbell — `agent-files-ring`, the editor registry and `agent-files-notify` (attention for harness sessions is the TUIOS Inbox; for agent-files' own threads the local file watcher is enough, [role-of-neovim](docs/role-of-neovim.md)).

### 10.2 The Elixir target — dropped

Dropped on 2026-11-01. The case for Elixir/OTP + Jido was a daemon supervising many long-lived processes, routing between them, surviving crashes and spanning machines. For harness sessions all of that is now TUIOS's job: it hosts the processes, keeps them across terminal restarts, routes attention and spans hosts. What is left for agent-files — `direct` threads, later `headless` sub-threads — is a handful of short-lived processes that scripts handle. Revisit only if headless tier-2 load makes the scripts hurt ([m1-plan §6](docs/m1-plan.md#6-triggers-for-a-long-lived-supervisor)); the file format still makes any swap invisible to threads.

**Multi-machine.** Harness sessions on other machines are TUIOS's (`tuios hosts`). agent-files' own runtimes run on one machine per root; a synced root (git or Syncthing) is read anywhere but run in one place (§13 Q9).

## 11. Neovim client — `agents.nvim`

Runs in Ghostty, or in a TUIOS pane. TUIOS hosts tier-1 TUI sessions (detached, attachable), not the editor. The split of attention: the TUIOS Inbox is where harness sessions ask for you; `agents.nvim` shows agent-files' own threads (`direct`, and `observed` mirrors), which TUIOS cannot see.

- **Watcher:** a `vim.uv.new_fs_event` watch per thread directory (recursive watching is not available on every OS); `autoread`/`checktime` for open buffers.
- **Tabline:** per-thread state from `status` and `seen`, e.g. ` 1 api ⠋   2 docs ●   3 tests ✓ ` (spinner working, red dot blocked, check done-unseen).
- **Attention:** `vim.notify` popup + terminal bell when a thread becomes `blocked` or `failed`.
- **Quickfix:** `:AgentsBlocked` fills the quickfix list with one entry per blocked thread, pointing at its `? PERMISSION` line (or at the thread, for observed sessions).
- **Locking and drafts:** buffer read-only while `working`; on reload, unsaved drafts are re-applied below the new last `END` (§4.5 rule 1).
- **Folds:** by indentation — each `▸` line folds the output beneath it.
- **Display:** highlights for turn markers and a status mark on the last `END`, on top of a generic markdown renderer. A read-only HTML view generated from the same files is optional ([docs/view-layer.md](docs/view-layer.md)); markdown stays the only source.
- **Acknowledge:** viewing a thread touches its `seen` file.
- **Needs-you jump:** `:AgentsNext` jumps to the next blocked thread's question (the quickfix list's `:cnext`).
- **Commands that write files:** `:AgentsSend` (append `END`, save), `:AgentsStop` (`touch STOP`), `:AgentsNew` (thread directory + `## you · t1`), `:AgentsFork` (branch per §8, selection → `## carry`), `:AgentsClose` (close a sub-thread), `:AgentsPrune` (`rm -r` a branch), `:AgentsGrep` (`rg` across `threads/` into quickfix). Each has a plain-shell equivalent; the full table is in [role-of-neovim §7](docs/role-of-neovim.md#7-the-other-direction-neovims-only-output-is-files).

### 11.1 Neovim's RPC server — a doorbell, not a mailbox

> **Dropped (2026-11-01); kept as a record.** The doorbell's job was reaching you when an agent needed you while no editor was looking. For harness sessions the TUIOS Inbox and notifications do that; for agent-files' own threads the file watcher does. Do not build what follows.

Every Neovim instance runs a msgpack-RPC server (its address is `v:servername`; pin it with `nvim --listen <socket>`), and Neovim exports that address as `$NVIM` into every `:terminal` job.

Its role here is deliberately narrow:

- **Doorbell.** Ringers (the Notifier, a tier-1 hook, an extension) run `agent-files-ring <absolute thread path> <event>`, which calls `ring(path, event)` in each matching editor to say "re-read this thread now". The payload is a path and an event name, never content.
- **Focus control.** Open a thread in a tab, jump to a blocked question, bring forward the agent that just needed you.
- **Identity.** A `claude` started in Neovim's own `:terminal` inherits `$NVIM`, so its hooks know which editor to ring.

What it is not: a store, a message transport, or a requirement. All state goes through files (principles 1, 8, 9). If no Neovim is running or the call fails, nothing is lost — the file watcher catches up. Locally `fs_event` already reacts in milliseconds, so the doorbell's value is *actions* (focus, jump) and shared network mounts where change events are slow or missing — not synced folders, where the ring can arrive before the content does.

Optional: a headless `nvim --headless --listen <addr>` on a remote machine can hold the editor session, and a laptop attaches with `nvim --remote-ui --server <addr>` — the editor's equivalent of `tmux attach`.

Who rings, for whom, when, and what happens if nobody answers: [docs/role-of-neovim.md](docs/role-of-neovim.md). Not built in M1: locally the file watcher is enough.

## 12. Relation to TUIOS and herdr

**TUIOS is adopted** as the host and attention layer for harness sessions; **herdr is the fallback.** Graded against 21 host-and-attention items from this plan, TUIOS covered 10 fully, 10 partly and missed 1; herdr (its TUI plus herdr-core) covered 9, 7 and missed 5. Details, sources and risks: [host-analysis](docs/host-analysis.md).

| Concern | Owner | Notes |
|---|---|---|
| Hosting `claude` / `codex` TUIs, detach/attach, surviving the terminal app | TUIOS | Processes still die on reboot or a daemon crash; TUIOS offers `claude --resume <id>` |
| Needs-you Inbox, alerts, seen marks, jump-to-next — for harness sessions | TUIOS | `agents.nvim` keeps these for agent-files' own threads |
| Answering harness permission prompts | The TUI, or the TUIOS Inbox | Keep TUIOS `[agents.approvals]` off (§5.1) |
| Worktree per agent, merge back, fan-out of one prompt to several agents | TUIOS | Replaces the proposed `workspace: worktree` |
| Remote machines in one view | TUIOS | Replaces the BEAM-nodes plan |
| Per-turn checkpoints of code changes | TUIOS, or Claude Code `/rewind` | Never planned here |
| Threads you can edit as context, forks with `## carry`, cross-thread search | **agent-files** | The thesis (M1, H1–H3) |
| Exact request records (`steps/`), spend cap, the record in git | **agent-files** | |
| Knowledge base, grounding, invalidation | **agent-files** | M5 |
| Enforcement: checks that can block a turn, protected paths, commit trailers | **agent-files** + Claude Code hooks + CI | TUIOS hooks only observe; it adds nothing to commits |

**Risks we accept, and their bounds.** TUIOS is pre-1.0, changes daily and is mostly one maintainer's work. Bounds: pin the version; reach it only through its JSON CLI from one adapter module; nothing in a thread depends on it (it holds no source of truth for us); if it misbehaves during the trial, switch to herdr.

**Corrections to the earlier Herdr comparison.** herdr is now three products: the Herdr TUI (status by reading the screen), herdr-core / `hc` (headless, status from OSC 7501 that Claude Code emits only when the terminal answers its capability query — tmux does not) and a desktop app (telemetry on by default). The herdr TUI resumes Claude and Codex sessions after a restart, so "resumable after reboot" is no longer ours alone.

## 13. Open questions

Numbers are stable; closed questions keep their number.

1. *Closed (2026-11-01):* Channels for a tier-1 bridge — no bridge (§5.1).
2. *Closed (2026-11-01):* Claude Code hook behaviour, verified against the hooks reference: `Stop` does not fire on interrupt, the failure event is `StopFailure`, `Notification` carries `notification_type`, and `PermissionRequest` signals a pending prompt at once (build spec §6).
3. Default `context:` mode — resume for code threads, replay for discussion threads?
4. *Closed (2026-11-01):* Elixir clients for Claude/Codex — no Elixir target (§10.2).
5. KB granularity and how much grounding to inline vs. summarize.
6. Codex and other vendors' terms for headless use on consumer plans.
7. A native agent loop for API and local models — recommended in a deliberately small form; see [docs/juggler-analysis.md](docs/juggler-analysis.md#6-should-we-have-our-own-agent-loop). Weigh it against Q12 before M6.
8. Which Juggler borrowings to adopt beyond branching-as-directories: intra-turn states (now designed from Pi Durable's recovery patterns, juggler-analysis §3), an approval rules file, budgets. Worktree workspaces are TUIOS's.
9. Locks across machines, for agent-files' own runtimes only (harness sessions on other hosts are TUIOS's): an advisory `lock` file naming the host, or "runtimes only on one machine"? Default: one machine.
10. How a sub-thread's agent declares its turn final (a structured marker, a tool call, or always one task per sub-thread).
11. **Enforcement (§9).** Which of an agent's tests count as protected oracles and which are its own working tests? How fast must ring-0 checks be before they slow the loop more than they save? How do exceptions expire? Which formal tools are worth it for which cores? Can Claude Code's `Stop` hook reliably keep a session working until checks pass, without loops?
12. **Pi as a harness.** Pi (`pi --mode rpc`, MIT, multi-provider) could serve as a tier-2 harness for non-Claude models, or as the M6 loop instead of growing our own. Open: can its RPC mode or extensions write the exact requests we want in `steps/`? Pi Durable itself is ruled out as a foundation: it owns opaque state and history is immutable, so it cannot replay an edited file ([host-analysis](docs/host-analysis.md)).
13. **Claude Code's own features vs. M3.** Its subagents, `/rewind` and session forking overlap sub-threads for coding work. Grade them against M3 before building it, as TUIOS was graded against M2.
14. **TUIOS gaps to watch in the trial:** Esc leaves a Claude pane "working"; Codex hooks break when the shared app-server was started from another pane (TUIOS issue #1391); verb meanings have changed between releases.

## 14. Milestones

- **M0** — these documents.
- **M1 — thesis trial** ([docs/m1-plan.md](docs/m1-plan.md)): the thread format, `agent-files-run` (direct replay, no tools), minimal `agents.nvim`, `observed` status for ordinary `claude` sessions, measurement; ten working days of use; then a go/no-go decision on H1–H3 against criteria fixed in advance. Harness sessions run in TUIOS during the trial.
- **M2** — *Dropped (2026-11-01):* the tier-1 bridge. Replaced by adopting TUIOS: operator setup, no build (§5.1, §12).

Everything below happens only if M1 says go, in an order the trial's results suggest:

- **M3** — supervisor + tier 2 (Claude, Codex) with `? PERMISSION` lines, `STOP`, sub-threads and the inbox, on scripts. Only for headless and direct work whose record should be files; grade TUIOS `start-agent`, Claude Code subagents and Pi first (§13 Q12–Q13).
- **M4** — tier 3 + council.
- **M5a** — KB: nodes, the gate, lint, grounding, proposals, extraction, the reading-pace check.
- **M5b** — KB invalidation: the retraction walk, `disputed` marking, inbox notes to affected threads. Only once M5a shows proposals accepted at reading pace. elixir-mind documented this step and never built it; socrates built its gate and ratification but has never run them on real input ([related-repos](docs/related-repos.md)).
- **M6** *(proposed)* — native loop for API/local models (`runtime: native`), grown from `agent-files-run`, writing every request to `steps/`.
- **M7** *(proposed)* — enforcement (§9): `checks.toml`, `agent-files-check`, ring-0 hooks per tier, protected paths, exceptions, commit trailers and notes, the KB link. Its own thesis, separate from M1's.
    - *Probe, any time:* a `Stop` hook on hand-started `claude` sessions that runs the repo's fast checks and blocks finishing until they pass, plus deny rules on test and CI paths. Measure how often the agent's "done" fails the checks, and how often it tries to touch protected files. Not part of M1's go/no-go.
