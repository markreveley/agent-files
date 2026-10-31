# agent-files — Architecture

> Status: draft v0.1 · 2026-10-31
> Collapse the agent interface down to **files, processes, and an editor**.
> Supplemental: [docs/juggler-analysis.md](docs/juggler-analysis.md) — reference comparison, storage format tradeoff, own agent loop.

## 1. Thesis

Most agent UIs are chat panels bolted onto a harness. Here we flip that:

- A **thread is a file.** The conversation, tool calls, permission questions and status all live in plain markdown on disk.
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
2. **Formats are plain text.** Markdown + YAML frontmatter for what humans read and write; JSONL for machine event logs; JSON for single records. No binary format in the source of truth.
3. **Extensions are executables.** A feature is a program on `PATH` named `agent-files-<name>` (like `git` subcommands): JSON on stdin, JSON on stdout, meaning in the exit code. Any language.
4. **History is git.** Undo, audit, blame and multi-machine sync go through git. The supervisor may commit at turn boundaries; it never rewrites history.
5. **Structure is directories.** A thread is a directory; a branch is a subdirectory; a workspace is a worktree path. `ls` and `tree` are the index.
6. **Processes are disposable.** Runners start and stop freely. Control is a line in a file (`STOP`) or a signal. Any long-lived process state must be rebuildable from files.
7. **Indexes are caches.** Any database or index (search, the KB graph) is derived: delete it and rebuild it from files.
8. **Protocols are doorbells.** RPC, sockets and channels only say "look at this file". Content travels through files. (Streams from harnesses at the edge — ACP, SDK, stream-json — are written to files as they arrive.)
9. **The editor is a client.** Neovim is the best viewer, not a dependency. Every operation can be done from a shell.
10. **Humans author, machines append.** You write below the last `END`; runtimes append between `## agent` and `END`. Text a human did not write never enters the interactive tier.

**The cat test.** A feature passes if you can see it with `cat`, find it with `grep`, undo it with `git`, and do it by hand from a shell. A feature that fails the test needs its reason written down.

## 3. Concepts

| Concept | Is | Lives in |
|---|---|---|
| Thread | One conversation, append-mostly markdown | `threads/<id>/thread.md` |
| Branch | A sub-thread or fork of a thread | a subdirectory of that thread's directory |
| Agent | Declaration: runtime, model, tools, permissions, grounding, snippets | `agents/<name>.md` |
| Process | Running instance serving a thread | supervisor (in memory) |
| Snippet | Reusable prompt text, expanded from `/name` | `snippets/<name>.md` (+ `.claude/commands`, skills) |
| KB node | One fact / claim / ref / decision / question | `kb/<id>.md` |
| Status | `idle \| working \| blocked \| done` | thread frontmatter |

## 4. Threads — layout and format

### 4.1 Layout: threads are directories, branches are subdirectories

```
threads/
└── fix-auth-timeout/
    ├── thread.md              # the conversation (main line)
    ├── steps/                 # exact request/response per model call, where we assemble requests
    │   ├── 0001.request.json
    │   └── 0001.response.json
    ├── out/                   # large tool outputs, linked from folds
    │   └── 0003-bash.txt
    ├── archive/               # originals replaced by compaction (nothing is thrown away)
    ├── explore-pool/          # sub-thread: returns only its result to the parent
    │   └── thread.md
    └── retry-logic/           # fork from turn 7
        └── thread.md
```

- A sub-thread or fork is a **subdirectory** of the thread it came from. The parent is the enclosing directory — there is no `parent:` field to drift out of sync.
- `branched_at: 7` in the child's frontmatter names the parent turn it started from. Turns are numbered by the order of their `## you` / `## agent` headers.
- A child carries **nothing** from its parent by default, only an explicit `carry:` block (see the clean-context rule in §6).
- When a sub-thread finishes, only its final turn is appended to the parent, as a quoted block linking the child's path.
- `tree threads/` is the branch view; oil.nvim or yazi are the branch browser; `grep -rl --include=thread.md 'status: blocked' threads/` is the needs-you list.
- Moving or pruning a branch is `mv` / `rm -r`, with git as undo.

### 4.2 Thread file format

```markdown
---
id: fix-auth-timeout
agent: coder            # -> agents/coder.md
runtime: interactive    # interactive | headless | direct
session: 8c1e…          # harness session id (resume mode)
context: resume         # resume | replay
status: done            # idle | working | blocked | done
branched_at: null       # parent turn number, for sub-threads and forks
grounding: [kb/auth-flow, kb/decision-0007]
---

## you
The auth middleware times out under load. Find out why.

## agent
Looking at the middleware first.

▸ Read src/auth/middleware.ts (212 lines)          {{{
… full tool output …
}}}
▸ Bash `npm test auth` (exit 1, 48 lines)            {{{
…
}}}

The pool is created per request…

END

## you
/test
Also check the retry logic.
```

### 4.3 Rules

1. **Single file, turn protocol.** The runtime appends only between an `## agent` header and its `END`. You write only below the last `END`. Saving the file sends your turn.
2. **Locking.** While `status: working`, the Neovim client makes the buffer read-only. The runtime ignores edits above the last `END` (in resume mode).
3. **Interrupt.** A line `STOP` below the last `END` interrupts the running turn (SDK `interrupt()` / channel / signal, per runtime).
4. **Snippets.** A leading `/name args` line is expanded from `snippets/` (or `.claude/commands/`, skills) before sending. Built-ins that act on the session (`/clear`, `/compact`, `/fork`) are handled by the runtime as actions, not text.
5. **Tool calls** are rendered as one-line `▸` summaries with output inside a fold. All folds closed = the collapsed natural-language transcript; no separate view.
6. **Permission requests** are written inline and set `status: blocked`:
   ```markdown
   ? PERMISSION Bash `rm -rf build/`   [y/n/always]
   ```
   You answer below it (`y`, `n`, `always`) and save.

## 5. Runtimes — three tiers

| Tier | Mechanism | Who authors turns | Billing (Claude, as of 2026-10) | Use for |
|---|---|---|---|---|
| **1. Interactive** | Real `claude` TUI in a detached tmux session, bridged to the thread file | **You, only** | Plan limits (interactive use) | Hands-on coding, pairing, anything you drive turn by turn |
| **2. Headless** | Claude Agent SDK / `claude -p`, Codex SDK / `codex exec`, any ACP agent | The system may | Agent SDK monthly credit, then API rates; other vendors per their terms | Background agents, child agents, long autonomous tasks |
| **3. Direct** | Raw model API calls (multi-provider) | The system | API rates | Council review, summarization/compaction, KB claim extraction, routing, classification |

### 5.1 Tier 1 — interactive bridge

- `claude` runs in a detached tmux session per thread (attach any time to see the real TUI — it is never hidden from you).
- **Input:** a custom *file channel* — a Claude Code **Channels** MCP server that watches the thread file and pushes your new turn into the running session. Fallback: `tmux send-keys`/`paste-buffer`.
- **Output:** the channel's reply tool writes the agent's reply into the thread; the session transcript JSONL (`transcript_path` from hooks) supplies tool calls for the folds.
- **Status:** hooks — `UserPromptSubmit`/`PreToolUse` → working, `Notification` (`permission_prompt`, `idle_prompt`) → blocked, `Stop` → done (and write `END`).
- **Policy rule (hard):** the tier-1 bridge forwards **only text a human wrote and saved**. It never forwards text generated by the system (child reports, council output, scheduled prompts, agent-to-agent messages). Those go through tier 2 or 3. This keeps tier 1 within "ordinary, individual usage" — the file is just a different keyboard.

### 5.2 Tier 2 — headless

- One long-lived client per thread (Claude Agent SDK `ClaudeSDKClient` or equivalent) — streaming input, `interrupt()`, `can_use_tool` callback → inline permission block.
- Codex via its SDK / `codex exec --json` with thread resume.
- Prefer **ACP** (Agent Client Protocol) as the uniform boundary where an adapter exists (`claude-agent-acp`, `codex-acp`, Gemini, Copilot): one protocol to implement, many agents.

### 5.3 Tier 3 — direct

- Multi-provider client (ReqLLM in the Elixir implementation).
- No tool loop; structured outputs; caching under our control.

## 6. Context assembly

Every request is assembled in a fixed order, most stable first, to maximize prompt-cache hits:

1. **Stable prefix** — agent role/system prompt, tool definitions.
2. **Grounding** — KB nodes listed in `grounding:` plus their dependencies (depth-capped; one-line summaries beyond the cap).
3. **Thread** — the conversation.

### Resume vs. replay (per thread, `context:`)

- **resume** — the harness owns its session; the file is a faithful mirror. Cheapest; full harness fidelity. Edits above `END` have no effect.
- **replay** — the file *is* the context; it is re-assembled each turn. Editing the file edits what the agent knows: delete a tangent, fix a wrong premise, replace 400 lines of output with a one-line summary. Required for switching models mid-thread.

**Cache economics.** On Anthropic's API a cache read costs ~0.1× base input, a write ~1.25× (5-min TTL) or 2× (1-hour TTL). Editing at position *k* re-writes everything after *k* once (~12.5× that suffix for one turn) plus latency. The default cache lives 5 minutes, so in human-paced threads it has usually expired anyway — replay edits are effectively free there. The cost is felt only in fast autonomous loops over a large prefix, where you are not editing.

### Against the "comprehensiveness assumption"

The habit of carrying an entire thread forward because everything said earlier *might* matter. A tightly scoped request in a clean context often does as well or better. Therefore:

- **`/fork` with clean context is the default gesture.** You explicitly choose what to carry (yank lines into a `carry:` block); nothing is carried implicitly.
- **Settled conclusions are promoted to KB nodes.** New threads ground on nodes, not on old transcripts. Transcripts are scratch; the KB is memory.
- **Token count is visible** in the status line so the cost of carried context is felt.

## 7. Knowledge base (DAG)

`kb/<id>.md`, one node per file:

```markdown
---
id: claim-0042
type: claim             # fact | claim | ref | decision | question
status: accepted        # proposed | accepted | disputed | retracted
depends_on: [ref-0011, fact-0007]
sources: [https://…]
summary: Pool-per-request causes the auth timeout under load.
---
Body: evidence, reasoning, caveats.
```

- **Edges** are `depends_on`; a lint enforces acyclicity and dangling refs.
- **Agents propose, humans accept.** Agent-written nodes start `status: proposed`. Prevents the KB filling with confident hallucinations.
- **Provenance & invalidation.** Retract a ref → walk dependents → mark claims `disputed` → flag threads whose `grounding` reaches them.
- **Extraction** (tier 3): at thread end, a cheap model proposes candidate nodes from the transcript for review.

## 8. Orchestration

- **Spawn:** an agent (or you) creates `<parent dir>/<child>/thread.md`; the supervisor starts it (tier 2). The directory nesting *is* the parent link.
- **Report back:** when a child finishes, the supervisor appends its final turn as a quoted block in the parent thread (in a tier-1 parent, as a pending note *you* forward — see policy rule).
- **Council** (tier 3, or tier 2 if reviewers need to run the code): the same diff + grounding fans out to N models → `reviews/<thread>/<model>.md`; an aggregator writes `synthesis.md` listing agreements, disagreements, and singletons. It surfaces disagreement; it does not vote. Caveats: ~N+1× cost; correlated blind spots across similarly trained models.

## 9. Implementation — Elixir/OTP + Jido

**Decision:** Elixir core with Jido 2; harnesses behind a process boundary.

Why: the daemon's job is supervising many long-lived processes, routing messages between them, surviving crashes, and spanning machines — the BEAM's home turf. Agents-as-data (Jido's struct + `cmd/2` → directives) matches "an agent is a declaration". The official SDKs are thin wrappers over CLI JSONL protocols, so the integration surface is subprocess + JSON lines either way.

Tradeoff accepted: official Claude/Codex SDKs are Python/TypeScript-first and track CLI changes fastest. Mitigation: talk **ACP** over a Port where an adapter exists; otherwise run a **tiny TS sidecar** per harness using the official SDK, speaking newline-delimited JSON to the BEAM. Swapping a sidecar never touches the core.

```
AgentFiles.Application
├── FileWatcher            (threads/, kb/, agents/ → signals)
├── ThreadRegistry
├── ThreadSupervisor       (DynamicSupervisor)
│   └── ThreadServer       (Jido AgentServer, one per thread; state rebuilt from file on restart)
│       └── Runtime        (Port: tmux+channel | ACP | sidecar | ReqLLM)
├── KB                     (graph index, lint, invalidation)
└── Notifier               (status → files; optional $NVIM RPC)
```

Directives (side effects as data): `AppendToThread`, `SetStatus`, `SpawnChild`, `RunHarness`, `CallModel`, `AskPermission`, `Interrupt`.

Remote machines: a node per machine; distributed Erlang gives one view across them (or sync `threads/` via git/Syncthing for a looser setup).

## 10. Neovim client — `agents.nvim`

Runs in Ghostty. tmux is used to host tier-1 TUI sessions (detached, attachable), not required for the editor itself.

- **Watcher:** `vim.uv.new_fs_event` on `threads/`; `autoread`/`checktime` for open buffers.
- **Tabline:** per-thread state, e.g. ` 1 api ⠋   2 docs ●   3 tests ✓ ` (spinner working, red dot blocked, check done-unseen).
- **Attention:** `vim.notify` popup + terminal bell when a thread becomes blocked; `TabEnter`/`BufEnter` turns done → idle.
- **Quickfix:** `:AgentsBlocked` fills the quickfix list with one entry per blocked thread, pointing at the question line.
- **Locking:** buffer read-only while `status: working`.
- **Folds:** `foldmethod=marker` on tool-call blocks.
- **Needs-you jump:** `:AgentsNext` jumps to the next blocked thread's question (the quickfix list's `:cnext`).

### 10.1 Neovim's RPC server — a doorbell, not a mailbox

Every Neovim instance runs a msgpack-RPC server (its address is `v:servername`; pin it with `nvim --listen <socket>`), and Neovim exports that address as `$NVIM` into every `:terminal` job.

Its role here is deliberately narrow:

- **Doorbell.** A hook or the supervisor may call `nvim --server <addr> --remote-expr "v:lua.require'agents'.ring('<thread path>')"` to say "re-read this thread now". The payload is a path, never content.
- **Focus control.** Open a thread in a tab, jump to a blocked question, bring forward the agent that just needed you.
- **Identity.** A `claude` started in Neovim's own `:terminal` inherits `$NVIM`, so its hooks know which editor to ring.

What it is not: a store, a message transport, or a requirement. All state goes through files (principles 1, 8, 9). If no Neovim is running or the call fails, nothing is lost — the file watcher catches up. Locally `fs_event` already reacts in milliseconds, so the doorbell's value is *actions* (focus, jump) and filesystems where change events are slow or missing (network mounts, synced folders), not raw latency.

Optional: a headless `nvim --headless --listen <addr>` on a remote machine can hold the editor session, and a laptop attaches with `nvim --remote-ui --server <addr>` — the editor's equivalent of `tmux attach`.

## 11. Relation to Herdr

| Herdr feature | Here |
|---|---|
| Needs-you status (OSC 7501) | Hooks/runtimes → `status:` in files; tabline + quickfix |
| `hc run --bg`, `hc send`, reports back | Child thread directories inside the parent's; supervisor relays |
| herdr-core persistence | Supervisor outlives the editor; **plus** resumable after reboot (file + session id) |
| SSH machines in one sidebar | BEAM nodes or synced `threads/` |
| Config as files edited by agents | Same pattern (`agents/`, `snippets/`) |
| GPU terminal (libghostty) | **Not ours** — use Ghostty/tmux |
| Status for arbitrary terminal programs | **Not ours** — only for programs that report |

## 12. Open questions

1. **Channels** is a research preview: protocol stability; whether the reply tool alone suffices or transcript tailing is needed; how permission prompts surface through it.
2. Default `context:` mode — resume for code threads, replay for discussion threads?
3. Maturity of Elixir clients for Claude/Codex vs. ACP vs. TS sidecars — decide per harness at M3.
4. KB granularity and how much grounding to inline vs. summarize.
5. Codex and other vendors' terms for headless use on consumer plans.
6. A native agent loop for API and local models — recommended in a deliberately small form; see [docs/juggler-analysis.md](docs/juggler-analysis.md#should-we-have-our-own-agent-loop).
7. Which Juggler borrowings to adopt beyond branching-as-directories (turn states, approval rules file, budgets, worktree workspaces) — see the same doc.

## 13. Milestones

- **M0** — this document.
- **M1** — thread format + `agents.nvim` viewer; tier-1 *observe only* (hooks → status). Usable immediately with ordinary `claude` sessions.
- **M2** — tier-1 bridge: file channel + tmux host; send turns from the file.
- **M3** — Elixir supervisor + tier 2 (Claude, Codex) with inline permissions and `STOP`.
- **M4** — tier 3 + council.
- **M5** — KB: nodes, lint, grounding, proposals, invalidation.
- **M6** *(proposed)* — native loop for API/local models, writing every request to `steps/`.
