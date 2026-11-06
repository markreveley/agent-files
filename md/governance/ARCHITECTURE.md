# agent-files — Architecture

> Status: draft v0.10 · 2026-11-05 · this document describes the **target** architecture; what gets built next is in [next-agents.md](../../next-agents.md).
> Collapse the agent interface down to **files, processes, and an editor**.
> **Host-neutral (v0.10, 2026-11-05).** What agent-files needs from a host, and which host that is now, are stated once, in §12; everywhere else this document says "the host" or "the next pane". The operator's own layout and config are not part of agent-files ([md/plans/2026-11-05-host-neutral/host-neutral.md](../plans/2026-11-05-host-neutral/host-neutral.md)).
> **Sessions in their own panes (v0.9, 2026-11-05).** The interactive `claude` and `codex` sessions run in panes of their own beside Neovim, grouped per git worktree, not in Neovim's terminals; the host keeps them running and shows their status. Agents reach Neovim in-process, through claudecode.nvim's IDE link, or through its RPC socket (§11.4). The `agents.nvim` sidebar is dropped ([md/plans/2026-11-05-tmux-host/tmux-host.md](../plans/2026-11-05-tmux-host/tmux-host.md); its host choice is superseded by v0.10).
> **Neovim-first (v0.8, 2026-11-04).** agent-files is built around Neovim: it is where threads are read and written. Files stay the source of truth, so other editors could be served later, but nothing is designed for them now.
> **Direction (v0.6).** agent-files is the logbook for human–agent work. It is not a coding harness. Planning happens in its own small loop (the planning harness, M6). Coding is farmed out to Claude Code and Codex, and their sessions come back as records feeding a DAG built on artifact-dag ([md/docs/direction-analysis.md](../docs/direction-analysis.md)).
> **Adopt before building.** Planned work that an existing tool already does is dropped from the plan and the tool is used instead; the tool that covers the most goes first. v0.5 applied this: TUIOS hosts harness sessions and owns attention for them, which removed the tier-1 bridge, the doorbell and the Elixir supervisor ([md/docs/host-analysis.md](../docs/host-analysis.md)). v0.6 applies it to the knowledge base (artifact-dag) and to capturing coding sessions (Entire is graded first). v0.7 moved hosting to Superlogical Rex ([md/docs/rex-host.md](../docs/rex-host.md)). v0.9 moved it to tmux and workmux, which also owned the sessions' status and switching, so the planned sidebar was dropped ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md)). v0.10 states what a host must do and names the current one in §12 only ([host-neutral](../plans/2026-11-05-host-neutral/host-neutral.md)).
> Supplemental: [md/docs/direction-analysis.md](../docs/direction-analysis.md) — what agent-files is for, the planning harness, neighbours to integrate with, the product shape · [md/plans/2026-10-31-m1/m1.md](../plans/2026-10-31-m1/m1.md) — the scope of the first build · [md/docs/m1-build-spec.md](../docs/m1-build-spec.md) — the first M1 build, specified · [md/plans/2026-11-05-host-neutral/host-neutral.md](../plans/2026-11-05-host-neutral/host-neutral.md) — what agent-files needs from a host, and the current host's facts · [md/plans/2026-11-05-tmux-host/tmux-host.md](../plans/2026-11-05-tmux-host/tmux-host.md) — sessions in their own panes beside Neovim, and the three ways agents reach Neovim (its host choice is superseded) · [md/docs/rex-host.md](../docs/rex-host.md) — the 2026-11-04 grading of Rex as the host (reinstated in part by host-neutral) · [md/docs/host-analysis.md](../docs/host-analysis.md) — TUIOS, herdr, cmux, workmux, parrot.nvim and Pi Durable graded against this plan (its host decision is superseded) · [md/docs/related-repos.md](../docs/related-repos.md) — what we take from itsjustshell2, elixir-mind, socrates, manifold and artifact-dag · [md/analysis/2026-10-31-juggler/juggler.md](../analysis/2026-10-31-juggler/juggler.md) — reference comparison, storage format tradeoff, own agent loop · [md/docs/role-of-neovim.md](../docs/role-of-neovim.md) — Neovim's role · [md/docs/view-layer.md](../docs/view-layer.md) — readable text in Neovim, rich HTML view in the browser.

## 1. Thesis

> **The logbook for human–agent work: every exchange a file you can edit as context, every settled conclusion a node that records who or what accepted it, every change linked to the turns and decisions behind it — in Neovim, beside the harnesses.**

The harnesses (Claude Code, Codex) are the engines; Neovim is the cockpit; the logbook outlives both. Others already answer *which conversation wrote this line?* (Entire, Zed's DeltaDB, git-ai). agent-files answers the next question: *which decision is this line serving, and is that decision still true?*

**The logbook loop** (§8.1): **plan** in agent-files' own planning harness → **brief** → **coding session** in a harness → **record** (transcript, commits, checks) → **DAG** (the gate, then acceptance) → **grounding** for the next plan. agent-files builds the planning harness, the record format, the links and the DAG's acceptance and invalidation. It adopts the rest: hosting the sessions and keeping them alive (the host, §12), coding (the harnesses), capture of coding sessions (Entire, if it grades well) and the DAG's schema, lint and viewer (artifact-dag).

Most agent UIs are chat panels bolted onto a harness. Here we flip that:

- A **thread is a file** — `thread.md`, in a directory of its own. The conversation, tool calls and permission questions live in plain markdown on disk; live state (status, session) sits beside it in tiny sidecar files.
- An **agent is a declaration** (a file naming its runtime, model, tools, permissions and grounding). The **process** that runs it is ephemeral — it exists only while there is work to do.
- **Neovim is the workplace.** It sits beside the harness sessions (the next pane), watches files, shows status, and is where you write. Because the state is in files, a shell (`grep`, `cat`) can still read and do everything. The HTML view ([md/docs/view-layer.md](../docs/view-layer.md)) is the client for readers who don't use Neovim, and the first piece of any GUI.
- **Memory is files too:** threads are scratch; durable knowledge is promoted into a DAG (§7, built on artifact-dag) that new threads are grounded in.

Unix analogy: program vs. process. The file is the program and its state; the runner is just a process.

**Built for the operator first, in a shape that could become a product.** The format, the hook, the record links and the viewer are built so they can be pulled out and used by others (principle 13). Whether agent-files becomes a product is decided later, on evidence ([direction-analysis §7](../docs/direction-analysis.md#7-built-for-the-operator-first-kept-product-shaped)).

### Non-goals

- Being a terminal. The host renders. Interactive TUIs (lazygit, an agent's own TUI) stay in a real terminal.
- Being a terminal multiplexer or a session host. Harness sessions run in the **host's** panes beside Neovim; the host keeps them alive when the terminal app quits, groups them per worktree and shows their status (§5.1, §12). A standalone host built with Charm (as TUIOS is) was reconsidered on 2026-11-02 and rejected: the layer is crowded, commoditizing and unmonetized ([direction-analysis §4](../docs/direction-analysis.md#4-the-host-fork-reconsidered)).
- Being a coding harness. Claude Code, Codex, etc. own the coding loop. We do not modify, wrap or proxy them. We sit beside them and own *the planning harness, context assembly for the threads we run, the record, the knowledge base and enforcement*. A general coding harness would compete with Juggler and the vendors on their strengths ([direction-analysis §3](../docs/direction-analysis.md#3-weaknesses-and-the-planning-harness)).
- Being a forge or a capture service for coding sessions. Entire captures sessions and links them to commits; agent-files reads such records and links them to decisions (§9.6, §12.1).

## 2. Principles — the agent you can `cat`

> **State lives in files, formats are plain text, extensions are executables, history is git, and structure is directories.**

1. **State lives in files.** Everything that matters is on disk. Kill every process and nothing is lost; restarting means re-reading files. Processes may cache state, never own it.
2. **Formats are plain text.** Markdown + YAML frontmatter for what humans read and write; one-line files for live state; JSONL for event logs; JSON for single records. No binary format in the source of truth.
3. **Extensions are executables.** A feature is a program on `PATH` named `agent-files-<name>` (like `git` subcommands): arguments and/or JSON on stdin in, JSON (or nothing) on stdout out, meaning in the exit code unless its spec says otherwise. Any language.
4. **History is git.** Undo, audit, blame and multi-machine sync go through git. Runtimes may commit at turn boundaries; nothing rewrites git history.
5. **Structure is directories.** A thread is a directory; a branch is a subdirectory; its id is its path. `ls` and `tree` are the index.
6. **Processes are disposable.** Runners start and stop freely. Control is a file (`touch STOP` in the thread's directory) or a signal. Any long-lived process state must be rebuildable from files.
7. **Indexes are caches.** Any database or index (search, the KB graph) is derived: delete it and rebuild it from files.
8. **Protocols only signal.** RPC, sockets and channels only say "look at this file". Content travels through files. (Streams from harnesses at the edge — ACP, SDK, stream-json — are written to files as they arrive.)
9. **Neovim is the interface; files are the truth.** agent-files is built for Neovim (v0.8). Every operation on a thread can still be done from a shell, because Neovim holds no state that is not on disk.
10. **Humans author, machines append.** You write the human parts of a thread (§4.3); the thread's runtime appends the rest. A file a session reads at your direction, such as a brief (§8.1), is not a turn.
11. **One machine writer per file.** Every file has exactly one process allowed to write it (§4.4). Many readers, one writer, no locks to get wrong.
12. **Review is enforcement.** What a machine can check, a machine checks while the code is written; the guarantee lives in the outermost ring that can enforce it, and humans own the checks (§9).
13. **Extractable.** The parts others could use stand on their own:
    - **The format.** It gets a standalone, versioned spec (`FORMAT.md`), and `md/docs/examples/view-fixture/` grows into conformance fixtures that every parser passes (Python, Lua, and JavaScript for the HTML view). Implementation-only fields go in sidecars, never in the format. Knowledge-base nodes use artifact-dag's schema.
    - **The hook.** `agent-files-hook` has a documented contract (event in, files out) and works without the runner or the editor.
    - **The links.** Every turn is addressable as `<thread path>#tN`. Links to code use shared formats where they exist (§9.6).
    - **The viewer.** It is HTML, built from the files.

    ([direction-analysis §7](../docs/direction-analysis.md#7-built-for-the-operator-first-kept-product-shaped).)

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
| Status | `working \| blocked \| done \| interrupted \| failed \| closed` — written only by the thread's runtime (for `observed` threads, `agent-files-hook`) | `threads/<id>/status` (one line) |
| Seen | Your acknowledgment; a thread whose status is older than `seen` shows as idle | `threads/<id>/seen` (empty file; its mtime) |
| Control file | An out-of-band request to a running turn | `threads/<id>/STOP`, present only until handled |
| Snippet | Reusable prompt text, expanded from `/name` (tiers 2–3) | `snippets/<name>.md` (+ `.claude/commands`, skills) |
| KB node | One definition, claim, resource, decision or question, in artifact-dag's schema (§7) | `kb/<node id>.md` |
| Brief | What a planning thread hands a coding session: the task plus the accepted nodes it rests on (§8.1) | `threads/<id>/briefs/<n>.md`, written by the planning thread's runtime (proposed, M6) |
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
| `events.jsonl` | append-only; the runtime. Tier 1 has none: `agent-files-hook` writes the observed thread's `status` | — |
| `checks/`, `commits` (own thread) | the thread's runtime | — |
| `.agent-files/checks.toml` and other protected paths (in the code repo) | — (agents are denied) | you, by commit (§9.4) |
| New branch directories | whoever creates the branch (§8) | you, via `:AgentsFork` or `mkdir` |

### 4.5 Rules

1. **Locking.** While `status` is `working`, the editor makes the buffer read-only. During a turn the runtime is the only writer of `thread.md`; if it detects a foreign write (the file changed in a way it didn't), it stops, saves its remaining output to `out/`, closes with `END (conflict)` and sets `interrupted`. If an editor holds unsaved text when the runtime writes, the plugin reloads the file and re-applies your draft below the new last `END` — no "file changed" prompt.
2. **Interrupt.** Create `STOP` in the thread's directory (`touch`, or `:AgentsStop`). The runtime stops the turn (SDK `interrupt()` / native cancel), closes with `END (interrupted)`, sets `interrupted`, and deletes `STOP`. Tier 1 has no agent-files runtime: interrupt in the TUI itself (Esc).
3. **Crash recovery.** When a runtime starts, any thread it owns whose `status` is `working` with no live owner gets `END (interrupted)` and its `status` becomes `interrupted`. You then **resume** (send a new turn, e.g. "continue") or **discard** (delete the partial agent turn by hand — the buffer is writable once the turn is closed).
4. **Snippets.** In tiers 2–3 a leading `/name args` line is expanded from `snippets/` (or `.claude/commands/`, skills) before sending. In tier 1 you type into Claude Code itself, which expands its own commands.
5. **Session actions.** `/fork` creates a branch exactly as `:AgentsFork` does (§8). `/clear` in replay mode starts a fork with an empty `## carry`. `/compact` is compaction (rule 9 below). In tier 1 these are Claude Code's own commands.
6. **Tool calls** are one-line `▸` summaries with output indented beneath (folded by indentation in Neovim) or moved to `out/` and linked. All folds closed = the collapsed natural-language transcript.
7. **Permissions (tiers 2–3).** The runtime writes one `? PERMISSION pN …` line, sets `blocked`, and waits; there is at most one pending question per thread. You answer `> y`, `> n` or `> always` on the line below it and save — the one place you write inside an agent turn, safe because the runtime is waiting, not writing. `always` allows that exact tool call pattern for the rest of the runtime's process (a persistent rules file is proposed; [juggler analysis §3](../analysis/2026-10-31-juggler/juggler.md#3-what-we-borrow--translated-to-files)). Tier-1 permissions are answered in the TUI (§5.1).
8. **Status.** Only the thread's runtime writes `status`; for an `observed` thread that is `agent-files-hook`. "Idle" is not a status: a thread whose `status` file is older than its `seen` file is shown as idle. `closed` is terminal and applies to sub-threads (§8).
9. **Compaction** is the one machine rewrite above `END`: an explicit operation the runtime performs while holding the turn (its `status` is `working`), moving the replaced turns to `archive/` and recording a `## note · compaction`. Turn ids of surviving turns are unchanged.

## 5. Runtimes — three tiers

| Tier (`runtime:`) | Mechanism | Who authors turns | Billing (Claude, as of 2026-11) | Use for |
|---|---|---|---|---|
| **1. Interactive** (`observed`) | Real `claude` / `codex` TUI in its own pane beside Neovim, grouped per worktree by the host (§5.1, §12); you type in the TUI. agent-files observes it through hooks and writes no turns | **You**, in the TUI | Plan limits (interactive use) | Hands-on coding, pairing, anything you drive turn by turn |
| **2. Headless** (`headless`) | Claude Agent SDK / `claude -p`, Codex SDK / `codex exec`, any ACP agent | You or the system | Plan limits (`claude -p` and the Agent SDK draw from the subscription; the separate Agent SDK credit announced 2026-05-13 was paused 2026-06-15), or API rates with a key; other vendors per their terms | Background agents, sub-threads, long autonomous tasks; coding farmed out from a plan (§8.1) |
| **3. Direct** (`direct`) | Model API calls we make ourselves (multi-provider), a local model, or the unmodified `claude -p` with every tool and setting removed | You (replay threads) or the system | API rates; plan limits through `claude -p`; free for local models | Replay conversation threads (the M1 runner), council, compaction, KB extraction, routing; grows into the planning harness (M6) |

**Where agent-files touches a harness.** Only at the harness's own published extension points, never by wrapping or driving its UI: Claude Code hooks in `~/.claude/settings.json` (tier 1 status, ring-0 checks, §9.2), SDK or CLI calls we make ourselves (tier 2, and the `claude -p` backend of tier 3), and git hooks in the code repo (§9.6). Hosting, input and screen capture for harness TUIs are the host's (its send and capture, §12), or `agents.term`'s for terminals inside Neovim (§11.2).

### 5.1 Tier 1 — harness TUIs in the host's panes

The tier-1 bridge (`agent-files-bridge`: tmux hosting, Channels input, transcript output) is dropped (2026-11-01). Tier 1 is resume-only by nature — Claude Code owns its context — so editing the file could never change what the agent sees, and a bridge would have bought a second keyboard and a mirror at the cost of the most fragile code in the plan.

- **The host** (v0.9 and v0.10, 2026-11-05, [tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) D2, [host-neutral](../plans/2026-11-05-host-neutral/host-neutral.md) D1). Each worktree has Neovim in one pane and each harness session in a pane of its own beside it, linked to Neovim by claudecode.nvim (`claude --ide`, §11.4). The host keeps them running when its app quits; a closed Claude session resumes with `claude --resume` in its pane. Status, switching and the needs-you list for harness sessions are the host's, beside agent-files' observed threads. Sessions don't run in Neovim's `:terminal`: to the host, Neovim is one pane, so it could not tell the sessions apart or show each one's status, its send would reach Neovim, and quitting Neovim would end them. What a host must do, and which one it is now: §12. Earlier host gradings: [rex-host](../docs/rex-host.md), [host-analysis](../docs/host-analysis.md).
- **agent-files' part: the `observed` thread.** `agent-files-hook` (Claude Code hooks) creates `threads/_observed/<project>-<session>/` and writes its `status`: the record of the session, and the status source for `agents.nvim` (tabline, `:AgentsNext`); whether it keeps writing status beside the host's is [tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) Q2. `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure` → `working`; `PermissionRequest` (the moment the dialog opens) or `Notification` with `permission_prompt` → `blocked`; `idle_prompt` ignored (it fires ~60 s after a finished turn); `Stop` → `done`; `StopFailure` → `failed`; `SessionEnd` → the directory is removed. `Stop` does not fire on Esc (documented), so an interrupted session stays `working` until its next event (TUIOS had the same gap). No turns are written: the transcript stays in the harness (`transcript_path`). Capturing it is part of the record work (§14), and Entire is graded before any capture is built (§12.1); a markdown mirror into the observed thread is the fallback.
- **Coexisting with the host's hooks.** A host may add Claude Code hooks of its own to `~/.claude/settings.json`; `agent-files-hook` entries go beside them, and Claude Code runs both. agent-files needs none of the host's hooks.
- **Adapter rule.** Anything agent-files does with the host goes through the host's CLI from one module, so a switch of host changes one file. Nothing needs it yet.
- **Constraints:** resume-only (`context: resume`); no grounding is injected (use the project's `CLAUDE.md` instead); no snippet expansion (§4.5 rule 4).
- **No send policy** (2026-11-05, [tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) D5). Text typed into a session, by you or by a tool you run (`:AgentsTermSend`, `agent-files-term send`, the host's send, a morla command), is your message relayed. agent-files does not automate interactive sessions or orchestrate agents through them, so nothing is refused by harness.
- **Agents in tier 1 do not write to `threads/`** (principle 11). Not enforced: residue (§9.7), kept by you reading.

### 5.2 Tier 2 — headless

- One long-lived client per thread (Claude Agent SDK `ClaudeSDKClient` or equivalent) — streaming input, `interrupt()`, `can_use_tool` callback → `? PERMISSION` line.
- Codex via its SDK / `codex exec --json` with thread resume.
- Prefer **ACP** (Agent Client Protocol) as the uniform boundary where an adapter exists (`claude-agent-acp`, `codex-acp`, Gemini, Copilot): one protocol to implement, many agents.
- Before building any of this (M3), check what already exists: TUIOS runs headless ACP and Codex protocol panes (`start-agent --protocol acp|codex`), Claude Code has its own subagents, and Pi can run as a harness for non-Claude models (§13 Q12–Q13).

### 5.3 Tier 3 — direct

- Multi-provider client: `agent-files-run` (a script).
- No tool loop; structured outputs; caching under our control; exact requests written to `steps/` (on the API backends; through `claude -p`, only what we sent).
- **Decided (2026-11-02): this tier grows into the planning harness** (`runtime: native`, M6). Direct is the special case with no tools and one step, so there is one code path instead of two ([juggler analysis §6](../analysis/2026-10-31-juggler/juggler.md#6-should-we-have-our-own-agent-loop), [direction-analysis §3](../docs/direction-analysis.md#3-weaknesses-and-the-planning-harness)).
  - **Scope:** planning, research, review, extraction, proposing nodes and writing briefs. It has no code-editing or shell tools: coding goes to a harness (§8.1).
  - **Two modes:**
    - *Full fidelity* on the API backends: exact requests, caching under our control, any provider.
    - *Cheap:* the unmodified `claude -p` on the operator's plan. Tools come over MCP (`--mcp-config --strict-mcp-config`) and structured output through `--json-schema`. Its losses are listed in [direction-analysis §5](../docs/direction-analysis.md#5-claude--p-as-the-planning-harnesss-cheap-mode). The value of the loop does not depend on this mode.

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

**Built on artifact-dag** (adopted 2026-11-02). artifact-dag supplies the node schema (`md/governance/SCHEMA.md`), the parser, the Datalog lint (`dagcheck --lint`, `lint/rules.dl`) and the viewer (`build-viewer`), and `kb/` is a `dag/` folder in its sense. agent-files adds what artifact-dag lacks: acceptance status, supersession, the gate, grounding and the retraction walk. Where an addition is generic, it goes into artifact-dag rather than into a parallel schema. The earlier reasons for not adopting it ([related-repos](../docs/related-repos.md)) were the claude.ai-only viewer, since retired, and Node tooling, which is acceptable for the KB: the standard-library rule covers the parser, the hook, stats and grep.

`kb/<node id>.md`, one node per file. Ids are artifact-dag's `<prefix>:<slug>`, used the same way everywhere (`grounding:`, `depends_on:`); examples elsewhere in this document that use bare slugs (`decision-0007`) are shorthand for the same thing.

```markdown
---
id: claim:pool-per-request-timeout
type: claim             # artifact-dag: definition | claim | resource; added here: decision | question
title: Pool-per-request causes the auth timeout under load
status: accepted        # added: proposed | accepted | disputed | retracted | superseded
accepted_by: mark       # added: a person, or rule:<policy> (Acceptance, below)
depends_on: [res:pg-pool-docs, claim:pool-created-per-request]
supports: []            # artifact-dag edges: uses | depends_on | supports | contradicts | refines | topics
revises: null           # added: the node this one supersedes, if any
sources: [threads/fix-auth-timeout/thread.md#t14, https://…]
---
Body: evidence, reasoning, caveats. [[claim:pool-created-per-request]] in the body is a mention edge.
```

- **Edges.** `depends_on` carries provenance and invalidation. `supports`, `contradicts` and `refines` are typed edges for argument structure; `[[id]]` in a body is a `mentions` edge. artifact-dag's lint reports cycles over `uses`, `depends_on`, `supports`, `refines` and `topics` (`contradicts` and mentions may cycle), and fails on dangling refs. The same Datalog rules express the retraction walk and the §9.7 checks.
- **Sources are records.** A node's `sources:` may cite a turn (`threads/<path>/thread.md#tN`), a commit, an Entire checkpoint id or a DeltaDB delta id, as well as URLs and `res:` nodes. This is how the DAG attaches to agent–operator interactions and to code (§8.1, §9.6).
- **Proposals carry no status — by construction.** The schema the model fills in has no `status` or `accepted_by` field; the runtime writes both, according to the acceptance policy. A node you write yourself is accepted when you write it, with `accepted_by` set to you. Only accepted nodes are ever injected as grounding.
- **The gate is always on.** A proposal is linted (cycles, dangling refs, undefined terms, unresolved sources) *before* it is stored. Errors go back to the model as structured data (through `--json-schema` in the `claude -p` mode, §5.3) for at most two repair rounds. After that the attempt fails loudly, and the rejected candidate is kept in `kb/_rejected/`, which doubles as an eval set. A proposal's `depends_on` may cite only nodes that were in its grounding; anything else is dropped and noted. (From socrates.)
- **Acceptance is a policy, per node type** (2026-11-02). Not everyone wants to approve every node by hand.
  - **The three policies:** `manual` waits for you. `auto` accepts when the node passes the gate. `sample` accepts automatically and queues a share of the accepted nodes for you to review.
  - **Where it is set:** config, for example manual for decisions and auto for definitions and resources.
  - **Attribution survives automation:** `accepted_by` records a person or `rule:<policy>`. Grounding can require nodes a person accepted, per type.
- **Supersession, not editing.** Changing what an accepted node claims means a new node with `revises:`; the old one becomes `superseded`. "What did we believe in August" stays answerable from files.
- **Evidence.** A node stating a fact needs `sources:` that resolve; the lint checks it. (From elixir-mind's `verified_by` rule.)
- **Reading-pace check** (for `manual` and `sample`). Accepting is only meaningful if you read. The KB tooling (M5) warns when the rejection rate falls to about zero or many accepts land within seconds. It catches stopped reading, not shallow reading.
- **Provenance & invalidation.** Retract or dispute a node → walk its dependents → mark claims `disputed` → drop a note in the `inbox/` of every thread whose `grounding` reaches them, and list the commits that cite it (§9.7). Built only after proposals are being accepted at reading pace (M5b, §14).
- **Extraction** (tier 3, then the planning harness). When a thread is closed, when a coding session's record comes back (§8.1), or when you ask, a cheap model proposes candidate nodes. They pass the gate, then follow the acceptance policy.

## 8. Orchestration

**Branches — one spec, whoever creates them** (`:AgentsFork`, a `/fork` turn, or an agent spawning a sub-thread):

- A new subdirectory with a `thread.md` whose frontmatter sets `kind` (`fork` or `subthread`) and `branched_at: tN`, copies `agent`, `runtime`, `model`, `context` and `grounding` from the parent unless told otherwise, and has an optional `## carry` section. The parent's `session` is **never** copied.
- **Forks** are yours: they never report back.
- **Sub-threads** are spawned to do a task (an agent spawn defaults to `runtime: headless`). When the task is done — the sub-thread's agent ends a turn declaring it final, or you run `:AgentsClose` — its runtime sets `closed` and writes its final turn as a note into the parent's `inbox/`.
- **Report back:** the parent's runtime consumes `inbox/` at the start of its next turn, writing each note as a `## note · <source>` section before its `## agent` header. Tier-1 sessions have no `thread.md` turns, so they get no notes; you read the child and type what you want into the TUI (§5.1).
- **Not ours:** sub-agents and fan-out *between harness TUIs* (by hand, through the host's scripting, or with the operator's own worktree tooling), and Claude Code's own subagents. agent-files sub-threads are for headless and direct work whose record should be files.

**Council** (tier 3, or tier 2 if reviewers need to run the code): the same diff + grounding fans out to N models → `<thread>/reviews/<model>.md`; an aggregator writes `<thread>/reviews/synthesis.md` listing agreements, disagreements, and singletons, and drops a note in the thread's `inbox/`. It surfaces disagreement; it does not vote. Caveats: ~N+1× cost; correlated blind spots across similarly trained models.

### 8.1 The logbook loop — briefs out, records back

Planning happens in agent-files (the planning harness, §5.3); coding happens in a harness. The two halves meet at two seams. (Decided 2026-11-02; [direction-analysis §1, §3](../docs/direction-analysis.md#1-what-agent-files-is-for).)

- **Out: the brief.** A plan ends with a brief, `threads/<id>/briefs/<n>.md`. It holds the task and the accepted nodes it rests on, assembled like grounding (§6), including the "no silent caps" line. A brief is a file the coding session reads, not text typed into its TUI:
  - *Interactive:* you start `claude` or `codex` in a worktree's pane and point it at the brief in your first prompt. How a session outside the data root reads the brief is open (§13 Q18).
  - *Headless:* a sub-thread runs `claude -p` with tools, or `codex exec`, with the brief as its prompt (tier 2, M3). Its record is files from the start.
- **Back: the record.** What the coding session leaves behind comes back as evidence:
  - its transcript, captured by Entire if adopted, or mirrored into its observed thread;
  - its commits, linked to the brief, the planning turn and the decisions they implement (§9.6);
  - its check results (§9.5).

  Extraction (§7) proposes nodes from that record: a claim confirmed, a decision implemented (`implemented_by`), a contradiction found. They pass the gate and follow the acceptance policy, and new plans ground on them.
- **What it buys.** From any commit you can reach the decision it serves and the conversation that made the decision. From any decision you can reach the commits that implement it and the threads that relied on it. Retracting a decision reaches all of them (§9.7).
- **Built versus adopted.** agent-files builds the planning harness, the brief, the links and extraction (M6, M7). Hosting is the host's (§12) and coding is the harness's. Capture is Entire's if it grades well (§12.1, §13 Q16).

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
| **1. Interactive** | Claude Code hooks, configured from `checks.toml` by `agent-files-check install`: `PreToolUse` denies writes to protected paths; `PostToolUse` runs `edit` checks on changed files; `Stop` runs `turn` checks and blocks the stop with the failure as its reason, so Claude keeps working (guard against loops with the hook's stop-active flag; verify hook behaviour at build time). The same hooks work under any host or in a bare terminal. The hosts' own hooks only observe and cannot block a turn, so ring 0 stays in Claude Code's hooks. | Feedback goes through Claude Code's own hook channel, set up by you. |
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

  The hook finds the thread from the tier-1 (`observed`) session running in that repo. `git log --format='%(trailers:key=Agent-Files-Thread)'` lists the threads that changed the code; `git blame` → commit → thread → turn explains a line.
- **Addressable turns.** Every turn has the stable address `<thread path>#tN` (turn ids are never renumbered, §4.3). Trailers, `commits` lines and KB `sources:` all point at turns this way.
- **Shared formats, not a private one** (principle 13). When a commit already carries an `Entire-Checkpoint` trailer, its checkpoint id goes on the thread's `commits` line, and the session isn't captured a second time. Agent Trace records (code ranges → conversations) are emitted only once that spec settles; its repo returned 404 on 2026-11-02. The `Agent-Files-*` trailers stay the minimal, tool-neutral form.
- **Thread → commits.** A `commits` sidecar in the thread directory, one line per commit (`<repo> <sha> <subject>`, plus an `entire:<checkpoint id>` field when one exists), written by the thread's runtime (principle 11).
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
| `agent-files-run` | Runtime for `direct` replay threads, growing into the planning harness (`native`, §5.3); single writer of those threads | M1; M6 |
| `agent-files-hook` | Claude Code hook: `status` of `observed` (tier-1) threads | M1 |
| `agent-files-stats` | Threads, turns, spend per day and per thread, live observed sessions | M1 |
| `agent-files-grep` | `rg` across `threads/` | M1 |
| `agent-files-render` | The HTML view: a static page built from the data root. It shows threads first, then the DAG (artifact-dag's viewer) and the chain from decision to turns to commits. Read-only; writes only under `~/.cache/agent-files/view/` | view-layer step 2 (optional during M1); grown in M8 |
| `agent-files-check` | Runs the checks for one trigger and prints JSON results; `install` sets up hooks, git hooks and commit trailers in a code repo (§9) | M7 (a probe earlier) |
| `agent-files-term` | Lists, reads and types into Neovim's terminal buffers through `agents.term` (§11.2) | Operator tooling, 2026-11-03; outside the M1 measurement |
| supervisor | Owns `headless` threads, spawning, the inbox; a script | M3 (deferred) |

**Dropped (2026-11-01):** `agent-files-bridge` (tier 1 runs in a host's terminals: Neovim's until v0.9, the host's own panes since, §5.1), and the doorbell — `agent-files-ring`, the editor registry and `agent-files-notify` (attention for harness sessions is the observed threads, and since v0.9 the host's status; for agent-files' own threads the local file watcher is enough, [role-of-neovim](../docs/role-of-neovim.md)). The 2026-11-05 revisit kept it dropped ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md)).

### 10.2 The Elixir target — dropped

Dropped on 2026-11-01. The case for Elixir/OTP + Jido was a daemon supervising many long-lived processes, routing between them, surviving crashes and spanning machines. For harness sessions all of that is now the host's job (§12): it hosts the processes, keeps them across terminal restarts, routes attention and reaches other machines. What is left for agent-files — `direct` threads, later `headless` sub-threads — is a handful of short-lived processes that scripts handle. Revisit only if headless tier-2 load makes the scripts hurt ([m1-plan §6](../plans/2026-10-31-m1/m1.md#6-triggers-for-a-long-lived-supervisor)); the file format still makes any swap invisible to threads.

**Multi-machine.** Harness sessions on other machines are the host's, where it reaches them (§12). agent-files' own runtimes run on one machine per root; a synced root (git or Syncthing) is read anywhere but run in one place (§13 Q9).

## 11. Neovim client — `agents.nvim`

Runs in a pane of its own, beside the harness sessions (§5.1). Attention: `agents.nvim` is where both kinds of thread ask for you: agent-files' own threads (`direct`) and the `observed` threads that `agent-files-hook` writes for harness sessions. The host's status view is the view of the harness sessions from outside the editor (§12).

- **Watcher:** a `vim.uv.new_fs_event` watch per thread directory (recursive watching is not available on every OS); `autoread`/`checktime` for open buffers.
- **Tabline:** per-thread state from `status` and `seen`, e.g. ` 1 api ⠋   2 docs ●   3 tests ✓ ` (spinner working, red dot blocked, check done-unseen).
- **Attention:** `vim.notify` popup + terminal bell when a thread becomes `blocked` or `failed`.
- **Quickfix:** `:AgentsBlocked` fills the quickfix list with one entry per blocked thread, pointing at its `? PERMISSION` line (or at the thread, for observed sessions).
- **Locking and drafts:** buffer read-only while `working`; on reload, unsaved drafts are re-applied below the new last `END` (§4.5 rule 1).
- **Folds:** by indentation — each `▸` line folds the output beneath it.
- **Display:** highlights for turn markers and a status mark on the last `END`, on top of a generic markdown renderer. A read-only HTML view generated from the same files is optional ([md/docs/view-layer.md](../docs/view-layer.md)); markdown stays the only source.
- **Acknowledge:** viewing a thread touches its `seen` file.
- **Needs-you jump:** `:AgentsNext` jumps to the next blocked thread's question (the quickfix list's `:cnext`).
- **Commands that write files:** `:AgentsSend` (append `END`, save), `:AgentsStop` (`touch STOP`), `:AgentsNew` (thread directory + `## you · t1`), `:AgentsFork` (branch per §8, selection → `## carry`), `:AgentsClose` (close a sub-thread), `:AgentsPrune` (`rm -r` a branch), `:AgentsGrep` (`rg` across `threads/` into quickfix). Each has a plain-shell equivalent; the full table is in [role-of-neovim §7](../docs/role-of-neovim.md#7-the-other-direction-neovims-only-output-is-files).

### 11.1 Neovim's RPC server — a doorbell, not a mailbox

> **Dropped (2026-11-01); kept as a record.** The doorbell's job was reaching you when an agent needed you while no editor was looking. For harness sessions the observed threads and the host's notifications do that; for agent-files' own threads the file watcher does. Do not build what follows.

Every Neovim instance runs a msgpack-RPC server (its address is `v:servername`; pin it with `nvim --listen <socket>`), and Neovim exports that address as `$NVIM` into every `:terminal` job.

Its role here is deliberately narrow:

- **Doorbell.** Ringers (the Notifier, a tier-1 hook, an extension) run `agent-files-ring <absolute thread path> <event>`, which calls `ring(path, event)` in each matching editor to say "re-read this thread now". The payload is a path and an event name, never content.
- **Focus control.** Open a thread in a tab, jump to a blocked question, bring forward the agent that just needed you.
- **Identity.** A `claude` started in Neovim's own `:terminal` inherits `$NVIM`, so its hooks know which editor to ring.

What it is not: a store, a message transport, or a requirement. All state goes through files (principles 1, 8, 9). If no Neovim is running or the call fails, nothing is lost — the file watcher catches up. Locally `fs_event` already reacts in milliseconds, so the doorbell's value is *actions* (focus, jump) and shared network mounts where change events are slow or missing — not synced folders, where the ring can arrive before the content does.

Optional: a headless `nvim --headless --listen <addr>` on a remote machine can hold the editor session, and a laptop attaches with `nvim --remote-ui --server <addr>` — the editor's equivalent of `tmux attach`.

Who rings, for whom, when, and what happens if nobody answers: [md/docs/role-of-neovim.md](../docs/role-of-neovim.md). Not built in M1: locally the file watcher is enough.

### 11.2 Harness terminals in Neovim — `agents.term`

Harness sessions run in the host's panes (v0.9), where the host's send and capture reach them (§12). `agents.term` (`nvim/lua/agents/term.lua`) is for the terminals that run inside Neovim (a shell, or a harness someone starts in `:terminal`): to the host such a terminal is part of Neovim's pane, so the host can't reach it; `agents.term` can, through Neovim's own socket. Whether it grows a backend for the host or is retired: [tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) Q1. It is an operator convenience for harness terminals, outside the thread system: threads still talk only through files (principle 8), and §11.1 stays dropped. It is not the dropped tier-1 bridge either: it writes no thread, mirrors no transcript and hosts nothing.

- **Commands:** `:AgentsTerms` lists the terminal buffers with their harness. `:[range]AgentsTermSend[!] {target}` types the lines in range, or the unnamed register, into a terminal and presses Enter (`!` leaves it out). `:AgentsTermCapture {target} [n]` opens the terminal's screen and scrollback in a scratch buffer.
- **From a shell or an agent:** `agent-files-term ls | capture TARGET [-n N] | send TARGET [TEXT|-] [--no-enter]`, against `$NVIM` (set inside every `:terminal`) or `--server`. An agent in a pane of its own has no `$NVIM` and passes `--server` ([nvim-addressing](../plans/2026-11-03-nvim-addressing/nvim-addressing.md)). It calls `require('agents.term').rpc()` with one JSON request. Exit 0 done; 1 failed (no match, no running job, or Neovim not reachable; the reason on stderr); 2 wrong usage or no `$NVIM`.
- **Targets:** a buffer number, or a harness name, command, directory or title that matches exactly one terminal.
- **Harness detection:** the first process in the terminal job's tree whose name is in `harnesses` (`setup({ term = { harnesses = { "claude", "codex" } } })`, the default), so a `claude` started from a shell in the terminal is found too.
- **Multi-line text** goes to a harness as one bracketed paste and to a shell as one line per command.

### 11.3 The sidebar — dropped

> **Dropped (2026-11-05).** A pane in `agents.nvim` was to start, list, switch and resume the harness sessions in Neovim's terminals ([nvim-sidebar plan](../plans/2026-11-04-nvim-sidebar/nvim-sidebar.md)). With the sessions in their own panes ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) D2), the host lists and switches them and shows their status (§5.1, §12). Kept as a record; do not build it.

### 11.4 How agents reach Neovim

Three ways, none of which depends on where the agent runs ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) D4):

| Way | What the agent gets | Used by |
|---|---|---|
| **In-process.** Lua inside Neovim makes one model call and acts on the reply | Everything Neovim knows at that moment: buffer lines, cursor, selection, buffer list, `:` history. Nothing runs until you say so | morla-neovim (§14 M1.6); inline questions |
| **IDE link.** claudecode.nvim runs a WebSocket server in Neovim and writes `~/.claude/ide/<port>.lock`; `claude --ide` (or `/ide`) started in Neovim's workspace connects | The selection and cursor as they change, files you send (`:ClaudeCodeSend`), open buffers, diagnostics; its edits shown in Neovim as diffs to accept or reject | the `claude` in the next pane |
| **RPC socket.** Neovim's msgpack-RPC server (§11.1; `$NVIM` inside its `:terminal`) | Anything: read and write buffers, run Ex commands, evaluate Lua | `agents.term`, `agent-files-term`; an agent in a pane of its own needs the address ([nvim-addressing](../plans/2026-11-03-nvim-addressing/nvim-addressing.md)) |

In-process suits short requests about the editor's state that you run; the IDE link, a coding session working beside the editor; the socket, tools. Running an agent in Neovim's `:terminal` instead of a pane of its own adds only `$NVIM`, set for free. All three are outside the thread system: threads still talk only through files (principle 8).

## 12. Relation to hosts

**agent-files does not host harness sessions; a host does.** What agent-files requires of one ([host-neutral](../plans/2026-11-05-host-neutral/host-neutral.md) D1):

1. **Panes that keep running when the terminal app quits.**
2. **A pane per harness session beside Neovim, grouped per worktree**, so the host sees each session apart from Neovim (§5.1).
3. **Send and capture from a script:** type into a pane, and read its screen and scrollback, from a shell.
4. **Status for harness sessions**, shown outside the editor.
5. **Remote machines** (optional): sessions on another machine, in the same view.

Anything else a host offers is the operator's to use, outside agent-files. agent-files reaches a host only through the adapter rule (§5.1) and keeps no state in it (principle 1), so a switch of host changes this section, not the design.

**The current host is Superlogical Rex** (2026-11-05, [host-neutral](../plans/2026-11-05-host-neutral/host-neutral.md) D2, with its facts; first graded in [rex-host](../docs/rex-host.md)). A Rex server holds every terminal, and the Mac app is one client of it (1). The operator lays out each worktree with Neovim in one pane and the harness in the next (2). `rex send`, `send-key`, `capture`, `events --json` and `rex api` script it (3). Claude Code and Codex report their state to it natively over OSC 7501, and its Activity view, notifications and Dock badge show it (4). `rex hosts add` and its built-in Tailscale reach other machines (5). It has no worktree command, and no terminal client: outside the Mac app, sessions can be scripted but not watched live. A server restart ends the programs (the layout comes back); a reboot ends them. TUIOS and herdr ([host-analysis](../docs/host-analysis.md)), and tmux with workmux ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md)), were the other hosts tried; none is used.

| Concern | Owner | Notes |
|---|---|---|
| Hosting `claude` / `codex` TUIs, listing and switching them | The host | A pane per session, grouped per worktree; `claude --resume` in the pane restores a session |
| Keeping sessions alive: surviving the terminal app | The host | A reboot ends them |
| Reading and typing into harness terminals | The host's send and capture for its panes; `agents.term` for Neovim's `:terminal` (§11.2) | |
| Needs-you list, alerts, jump to the last finished — for harness sessions | The host's status view | agent-files' observed threads also feed `agents.nvim` (tabline, `:AgentsNext`) while the hook writes status (tmux-host Q2) |
| Answering harness permission prompts | The TUI | |
| Worktree per agent, merge back, one prompt to several agents | The operator's own tooling, outside agent-files | |
| Remote machines | The host (optional) | Replaces the BEAM-nodes plan |
| Per-turn checkpoints of code changes | Claude Code `/rewind` | Never planned here |
| Threads you can edit as context, forks with `## carry`, cross-thread search | **agent-files** | M1 |
| Exact request records (`steps/`), spend cap, the record in git | **agent-files** | |
| Knowledge base, grounding, invalidation | **agent-files**, on artifact-dag | M5 (§7) |
| Capturing coding sessions; commit ↔ session links | Entire, if it grades well (§12.1) | agent-files links those records to threads and decisions (§8.1, §9.6) |
| The planning harness and briefs | **agent-files** | M6 (§5.3, §8.1) |
| Enforcement: checks that can block a turn, protected paths, commit trailers | **agent-files** + Claude Code hooks + CI | The host's hooks, if any, only report; they add nothing to commits |

**Risks we accept, and their bounds.** Rex is a closed-source beta that changes fast (11 preview builds from 2026-10-19 to 2026-11-05) and could change course or stop. Bounds: it holds no source of truth for agent-files (principle 1), so nothing in a thread depends on it; agent-files would reach it only through the adapter rule (§5.1), and nothing does yet; `agent-files-hook` works the same under any host (§9.2). A switch moves the panes and changes this section.

**Corrections to the earlier Herdr comparison.** herdr is now three products: the Herdr TUI (status by reading the screen), herdr-core / `hc` (headless, status from OSC 7501 that Claude Code emits only when the terminal answers its capability query — tmux does not) and a desktop app (telemetry on by default). The herdr TUI resumes Claude and Codex sessions after a restart, so "resumable after reboot" is no longer ours alone.


### 12.1 Relation to record and attribution tools

Entire, Zed's DeltaDB and git-ai answer *which conversation wrote this line?* agent-files answers *which decision is this line serving, and is it still true?* So it integrates at the record level and builds above it ([direction-analysis §6](../docs/direction-analysis.md#6-neighbours-integrate-or-compete)).

| Tool | Stance |
|---|---|
| **Entire** — an MIT CLI that hooks into Claude Code, Codex, Cursor, Pi and others. Each commit with agent work gets a checkpoint under `refs/entire/checkpoints/…` and an `Entire-Checkpoint` trailer. The hosted forge is the paid part | **Integrate** at capture: grade it before building any capture of coding sessions (§13 Q16). **Avoid** the forge. **Watch** its memory: if it grows acceptance and retraction, it competes with §7 |
| **Zed DeltaDB** — every edit is a delta with a stable id, linked to its conversation. Early access, used by Zed's Delta harness; support for other harnesses unclear | Cite delta ids as `sources:` if it opens up |
| **git-ai** (line attribution in git notes), **Agent Trace** (a draft spec), **SpecStory** (sessions as markdown) | Formats to read or emit; grade SpecStory alongside Entire |
| **Juggler** — a coding harness with editable history and step inspection | Not a competitor for the planning harness; possibly one of the engines coding is farmed out to |

## 13. Open questions

Numbers are stable; closed questions keep their number. Open ones are in the [open-questions plan](../plans/2026-11-04-open-questions/open-questions.md), under the same number with an `A` (`A3` is Q3 here); a question closes there and its answer comes back here.

1. *Closed (2026-11-01):* Channels for a tier-1 bridge — no bridge (§5.1).
2. *Closed (2026-11-01):* Claude Code hook behaviour, verified against the hooks reference: `Stop` does not fire on interrupt, the failure event is `StopFailure`, `Notification` carries `notification_type`, and `PermissionRequest` signals a pending prompt at once (build spec §6).
3. *Open:* default `context:` mode → [open-questions A3](../plans/2026-11-04-open-questions/open-questions.md#a3).
4. *Closed (2026-11-01):* Elixir clients for Claude/Codex — no Elixir target (§10.2).
5. *Open:* KB granularity and how much grounding to inline vs. summarize → [open-questions A5](../plans/2026-11-04-open-questions/open-questions.md#a5).
6. *Open:* Codex and other vendors' terms for headless use on consumer plans → [open-questions A6](../plans/2026-11-04-open-questions/open-questions.md#a6).
7. *Closed (2026-11-02):* a native agent loop — yes, as the planning harness (M6, §5.3); not a coding harness ([direction-analysis §3](../docs/direction-analysis.md#3-weaknesses-and-the-planning-harness)). Q12 (Pi) is still graded first.
8. *Open:* Which Juggler borrowings to adopt beyond branching-as-directories → [open-questions A8](../plans/2026-11-04-open-questions/open-questions.md#a8).
9. *Open:* Locks across machines, for agent-files' own runtimes only → [open-questions A9](../plans/2026-11-04-open-questions/open-questions.md#a9).
10. *Open:* How a sub-thread's agent declares its turn final → [open-questions A10](../plans/2026-11-04-open-questions/open-questions.md#a10).
11. *Open:* Enforcement (§9) → [open-questions A11](../plans/2026-11-04-open-questions/open-questions.md#a11).
12. *Open:* Pi as a harness → [open-questions A12](../plans/2026-11-04-open-questions/open-questions.md#a12).
13. *Open:* Claude Code's own features vs. M3 → [open-questions A13](../plans/2026-11-04-open-questions/open-questions.md#a13).
14. *Open:* Host gaps to watch → [open-questions A14](../plans/2026-11-04-open-questions/open-questions.md#a14).
15. *Open:* T3 Code as a host → [open-questions A15](../plans/2026-11-04-open-questions/open-questions.md#a15).
16. *Open:* Entire for capture → [open-questions A16](../plans/2026-11-04-open-questions/open-questions.md#a16).
17. *Open:* `claude -p` fidelity for the planning harness → [open-questions A17](../plans/2026-11-04-open-questions/open-questions.md#a17).
18. *Open:* How a coding session reads a brief → [open-questions A18](../plans/2026-11-04-open-questions/open-questions.md#a18).
19. *Open:* Acceptance defaults → [open-questions A19](../plans/2026-11-04-open-questions/open-questions.md#a19).
20. *Open:* Product → [open-questions A20](../plans/2026-11-04-open-questions/open-questions.md#a20).

## 14. Milestones

- **M0** — these documents.
- **M1** ([md/docs/m1-build-spec.md](../docs/m1-build-spec.md)): the thread format, `agent-files-run` (direct replay, no tools), minimal `agents.nvim`, `observed` status for ordinary `claude` sessions. Built.
- **M2** — *Dropped (2026-11-01):* the tier-1 bridge. Tier 1 runs in the host's panes instead (§5.1, §12).
- **M1.5 — the sidebar** — *Dropped (2026-11-05):* the harness sessions run in their own panes, and the host lists, switches and tracks them (§11.3, §12).
- **M1.6 — the morla command lane** ([plan](../plans/2026-11-05-morla/morla.md)): [morla-neovim](https://github.com/markreveley/morla-neovim) drives `agents.nvim` in plain English, its requests carrying a reference of the `:Agents*` commands and the current terminals and threads. Sessions in the host's panes are reached through the host's send ([tmux-host](../plans/2026-11-05-tmux-host/tmux-host.md) Q3).

The order below follows the logbook loop (§8.1).

- **The record work** — attribution and the DAG on real coding work. It needs four things:
  - capture of coding sessions (Entire graded first, §13 Q16);
  - commit links (the §9.6 part of M7);
  - M5a on artifact-dag;
  - extraction from those records.
- **M3** — supervisor + tier 2 (Claude, Codex) with `? PERMISSION` lines, `STOP`, sub-threads and the inbox, on scripts. This includes headless coding sub-threads that run a brief (§8.1). Only for headless and direct work whose record should be files; grade the host's scripting (`run`, `wait`), workmux (`add -p`, `run`, `wait`), TUIOS `start-agent`, Claude Code subagents and Pi first (§13 Q12–Q13).
- **M4** — tier 3 + council.
- **M5a** — KB on artifact-dag: its schema, lint and viewer, plus what agent-files adds (§7): `status`, `accepted_by`, acceptance policies, the gate, grounding, proposals, extraction and the reading-pace check.
- **M5b** — KB invalidation: the retraction walk, `disputed` marking, inbox notes to affected threads. Only once M5a shows proposals accepted at reading pace. elixir-mind documented this step and never built it; socrates built its gate and ratification but has never run them on real input ([related-repos](../docs/related-repos.md)).
- **M6** — **the planning harness** (`runtime: native`; decided 2026-11-02, §5.3), grown from `agent-files-run`.
  - Tools for reading, search, web fetch, proposing nodes and writing briefs (§8.1); no code-editing or shell tools.
  - The API mode writes every request to `steps/`; the `claude -p` mode uses MCP tools and `--json-schema`.
  - Grade Pi first (§13 Q12).
- **M7** *(proposed)* — enforcement (§9): `checks.toml`, `agent-files-check`, ring-0 hooks per tier, protected paths, exceptions, commit trailers and notes, the KB link. The §9.6 links move forward into the record work.
    - *Probe, any time:* a `Stop` hook on hand-started `claude` sessions that runs the repo's fast checks and blocks finishing until they pass, plus deny rules on test and CI paths. Measure how often the agent's "done" fails the checks, and how often it tries to touch protected files. 
- **M8** *(proposed)* — the record viewer: `agent-files-render` grown into a static HTML page showing threads, the DAG (artifact-dag's viewer) and the chain from decision to turns to commits (principle 13). Editing in a browser only if a product follows.

**Proposed order:** the morla command lane (M1.6) → the record work (capture, links, M5a) → M6 → M8 → M5b → the rest of M7 → M3 and M4 as needed.
