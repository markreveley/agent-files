# Juggler as a reference — supplemental analysis

> Status: draft · 2026-10-31 · companion to [ARCHITECTURE.md](../ARCHITECTURE.md)
> Sources: [juggler.studio](https://juggler.studio) and [its features page](https://juggler.studio/features.html), read 2026-10-31. Source code (not yet read): [github.com/juggler-ai/juggler](https://github.com/juggler-ai/juggler).

**Summary.** Juggler is the closest reference so far. It already ships most of our context ideas — editable history, branching, sub-threads that return only results, approvals as persistent state, model switching mid-conversation. The difference is where those ideas live: Juggler builds its own agent loop and stores conversations as live-synced CRDT documents behind a native app. agent-files keeps them in plain files and borrows existing harnesses. That difference is our angle:

> Juggler is "the coding agent you can see inside". agent-files is the agent you can `cat`.

## 1. What Juggler is

- A coding agent with a desktop app (Go backend, JavaScript UI, not Electron), by Julian Storer (JUCE, Tracktion, Cmajor). Also runs as a headless server; browser and phone clients attach to the same live session.
- **Step inspection:** every model call can be opened to show the exact request (system prompt, messages, tool definitions) and response (output, tokens, cache, timing, stop reason).
- **Conversation as a tree:** branch anywhere; sub-threads return only their result to the parent; rewind, delete, fork, `/handoff`, undo/redo of structural changes.
- **Approvals:** shell commands are parsed so only parts that can change something ask; "don't ask again" saves a narrow, editable rule. Approvals are stored as a state, so a turn waiting on you survives quitting.
- **Attention:** ⌘J jumps to the next conversation waiting on you; tabs highlight or chime.
- **Providers:** Claude Code (Pro/Max via the unmodified `claude` CLI), Codex (ChatGPT plans), Copilot; API keys for Anthropic, OpenAI, Gemini, Mistral, DeepSeek, OpenRouter and others; local models (Ollama, LM Studio, llama.cpp); ACP agents; MCP servers.
- **Storage:** files in the project's `.juggler` folder and `~/.juggler`; conversations are **Yjs documents** synced live to every client.
- **Extensions:** a typed SDK — tools, loop strategies, slash commands, workspace providers (git worktree, scratch copy, monorepo folder), viewers, sidebar cards.
- **License:** application AGPLv3; extension SDK Apache-2.0. *We borrow ideas, not code.*

## 2. Overlaps

| Juggler | agent-files |
|---|---|
| Rewind, delete, fork from any message, undo | Replay mode: editing the file edits the context |
| `/handoff` into a fresh conversation | `/fork` with an explicit `## carry` section |
| Sub-threads return only their result | A closed sub-thread sends only its final turn to the parent, as a note via `inbox/` |
| Approval stored as a state, survives quit | A `? PERMISSION` line + `blocked` status; surviving a runtime restart needs intra-turn states (proposed, §3) — today a restart closes the turn as interrupted |
| ⌘J to next waiting conversation | `:AgentsNext` / quickfix `:cnext` |
| Switch model mid-conversation | Replay mode (context is the file, not a vendor session) |
| Reads `CLAUDE.md`, `AGENTS.md`, skills, Claude Code slash commands | Snippets expand from `snippets/` and `.claude/commands/` |
| ACP agents + MCP servers | ACP as the preferred harness boundary |
| Sessions survive restarts | Runtimes rebuild every thread from its files; a turn cut off by a crash is closed as interrupted and resumed with a new turn |

## 3. What we borrow — translated to files

| Juggler feature | File-native translation | Status |
|---|---|---|
| Conversation tree (Miller columns) | Threads are directories; branches are subdirectories; `tree threads/` is the branch view | **Adopted** (ARCHITECTURE §4.1) |
| Non-destructive compaction | An explicit rewrite the runtime performs while holding the turn; originals moved to `archive/`, a `## note` records it | **Adopted** (ARCHITECTURE §4.5 rule 9) |
| Step inspection | `steps/NNNN.request.json` + `.response.json`; inspect with `jq`, compare turns with `diff` | **Adopted** in layout — only where we call the model API ourselves (direct, native loop); inside Claude Code or Codex we only have transcripts |
| Turn as named states (model → tools → approval → next call) | Stable turn ids are **adopted** (`## agent · tN`); intra-turn states go in a sidecar (not the frontmatter, which is yours), so a restarted runtime knows where to resume | Proposed |
| Narrow, editable approval rules | One text rules file per project, in Claude Code's allow/deny syntax | Proposed |
| Token budget per sub-agent, spend ceiling per conversation | `budget:` in frontmatter, enforced by the supervisor | Proposed — matters once SDK credit / API billing is in play |
| Workspace per conversation | `workspace: worktree` in frontmatter → the runtime runs `git worktree add` in the code repo | Proposed |
| Read-only explore/research sub-agents in parallel | Sub-thread template with read-only tools; many may run at once | Proposed |
| Extension SDK | Executables on `PATH`: `agent-files-<name>`, arguments/JSON in, JSON out | **Adopted** as principle 3 |
| Export to Markdown/HTML | Not needed — the thread already is markdown | — |

## 4. Where we deliberately differ

| | Juggler | agent-files | Why |
|---|---|---|---|
| Conversation storage | Yjs CRDT documents | Markdown + YAML, one-line and JSON/JSONL sidecars | Must pass the cat test (§5) |
| Agent loop | Its own, for all providers | Borrowed harnesses; small native loop only for light work | Harness quality for coding (§6) |
| UI | Native app, Miller columns | Neovim + the directory tree | The editor is a client (principle 9) |
| Extensions | Typed in-process SDK | Executables, JSON over stdio | Any language, no SDK to version |
| Undo | ⌘Z over structural edits | git | History is git (principle 4) |
| Multi-device | Live sync to browser/phone | git or Syncthing; clients watch files | Trades live co-editing for plain files |

## 5. Storage format tradeoff

The question: what is the source of truth for a conversation on disk?

| Criterion | Markdown + YAML | JSONL event log | CRDT (Yjs) | SQLite |
|---|---|---|---|---|
| Read with `cat`, search with `grep` | ✅ | ✅ (noisy) | ❌ binary updates | ❌ needs a client |
| Meaningful `git diff` / merge | ✅ | ✅ append-only diffs | ❌ | ❌ |
| Edit in any editor | ✅ | ⚠️ escaped strings | ❌ | ❌ |
| Concurrent writers | ⚠️ needs a protocol | ✅ append-only | ✅ automatic merge | ✅ transactions |
| Live sync to many clients | ⚠️ via file watching | ⚠️ via `tail -f` | ✅ designed for it | ❌ |
| Structured queries | ⚠️ frontmatter + grep | ✅ `jq` | ⚠️ via the library | ✅ SQL |
| Fidelity for structured data (tool args, usage) | ⚠️ lossy if inlined | ✅ | ✅ | ✅ |
| Crash safety | ✅ with an END marker | ✅ | ✅ | ✅ |
| Tooling a reader needs | none | `jq` | Yjs runtime | SQLite client |

**Decision: a layered plain-text format.**

1. **`thread.md` is the human surface and the replay source.** Markdown + YAML frontmatter (your configuration), append-mostly. It holds what a person reads and edits: turns, folded one-line tool summaries, permission questions, notes.
2. **Sidecars hold live state and machine fidelity.** One-line `status` and `session` files (current state, one writer each), `steps/*.json` for exact requests and responses, an optional `events.jsonl` history of transitions and raw tool calls (the `status` file is authoritative), `out/` for large tool outputs. Plain text, readable with `cat` and `jq`.
3. **Indexes are caches.** If we need SQL or full-text search, it is a derived SQLite index rebuilt from files (principle 7) — like `locate`'s database, never a source of truth.

**What we give up, and how we cope:**

- **Live co-editing.** Yjs merges simultaneous edits character by character; we don't. One machine writer per file instead (ARCHITECTURE §4.4): during a turn only the runtime writes `thread.md`, the buffer is locked, and a foreign write closes the turn as a conflict. Running the same thread from two machines needs a lock (proposed: an advisory `lock` file naming the host; §7).
- **Live multi-client sync.** Clients watch the file (`fs_event`, or literally `tail -f`). Across machines, git (explicit, conflicts visible) or Syncthing (continuous; conflicts become `.sync-conflict` files we can detect and surface).
- **Fine-grained undo.** Editor undo within a session; git across sessions (optional auto-commit at each `END`).
- **Crash safety.** Writes to `thread.md` are appends, except explicit compaction; sidecars are replaced atomically. `END` doubles as a commit marker: a turn without `END` after a crash is closed as `END (interrupted)` with status `interrupted`, to resume or discard.

The one place a CRDT would clearly win is real-time collaboration between people on one thread. That is not the primary use case; if it becomes one, a CRDT can be a sync layer *over* the files rather than the storage format.

## 6. Should we have our own agent loop?

**Recommendation: yes, but deliberately small — and not as the main coding harness.**

**For a native loop:**

- **Complete step inspection.** Only a loop we run lets us write every exact request to `steps/`. Inside Claude Code or Codex we see transcripts, not requests.
- **Any model, including local.** One OpenAI-compatible client reaches Ollama, LM Studio and llama.cpp, plus API-key providers (ReqLLM covers many).
- **File-native from the inside.** Turn states, permission rules, budgets and steps are ours by construction, not reconstructed from someone else's events.
- **Model switching is free.** The context is the file (replay mode), so changing models mid-thread is a frontmatter edit.
- **Less exposure to vendor billing and terms changes** for work that doesn't need a vendor harness.

**Against making it the main coding agent:**

- **Harness quality.** Claude Code and Codex are tuned hard for their models — tool design, edit formats, prompts, context management. A new loop will be worse at heavy coding for a long time.
- **Safety work.** A shell tool needs sandboxing and careful permission handling to be trustworthy.
- **Maintenance.** Every provider quirk becomes ours.
- **An alternative exists for local models:** a multi-provider agent that speaks ACP (OpenCode is one) can sit in tier 2 without a loop of our own. Verify local-model support per agent.

**Scope of the native loop:** work where transparency matters more than coding horsepower — research, review, KB curation and extraction, summarization, triage, glue between threads. Default tools: read / grep / glob, web fetch, write only to the thread and to `kb/` as `status: proposed`; shell gated by the approval rules file. Coding-heavy threads go to Claude Code or Codex.

**Shape:** it grows from M1's `agent-files-run` replay runner (a script) by adding tools and a `steps/` view; every request written to `steps/`. If and when the supervisor moves to Elixir ([m1-plan §6](m1-plan.md#6-triggers-for-the-elixir-supervisor)), the loop moves with it: ReqLLM for providers, Jido actions as tools, an MCP client for external tools. Tier 3 ("direct") is then the special case of this loop with no tools and one step — one code path instead of two.

**Milestone:** M6, only if the M1 trial says go; the trial's results set its priority relative to M2–M5.

## 7. Open questions

1. **How does Juggler drive `claude` on Pro/Max?** Its site says the unmodified CLI, but not whether interactively or with `-p` (which now draws from the Agent SDK credit). Read its source before building the M2 interactive bridge.
2. Is the `events.jsonl` sidecar worth its weight from M1, or only once the native loop exists?
3. Locks across machines — an advisory `lock` file naming the host, or simply "runtimes only on one machine"? (ARCHITECTURE §12.)
