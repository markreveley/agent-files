# M1 plan — a cheap test of the thesis

> Status: draft · 2026-10-31 · companion to [ARCHITECTURE.md](../ARCHITECTURE.md) §13
> Build spec: [m1-build-spec.md](m1-build-spec.md)
> Goal: build the smallest agent-files that can prove or disprove the core thesis in two weeks of real use, and decide with evidence whether anything bigger gets built.

**Summary.** M1 is a trial, not a foundation. It ships a replay runner script, a minimal Neovim plugin, observe-only hooks for ordinary Claude Code sessions, and a way to measure use. After ten working days, fixed go/no-go criteria decide whether the rest of the architecture (supervisor, interactive bridge, knowledge base) is worth building. Nothing in M1 uses Elixir; the file format is the contract, so scripts can be replaced later without touching a single thread.

## 1. Hypotheses

The thesis is that context you can edit as a file beats an append-only chat. M1 tests it as four hypotheses:

| # | Hypothesis | Core or side benefit |
|---|---|---|
| H1 | **Context editing** — you will edit context above `END` when it helps: delete a tangent, fix a premise, compress an output | Core |
| H2 | **Clean forks** — you will start forks with a small `## carry` section instead of continuing long threads, and those forks will be at least as good | Core |
| H3 | **Cross-thread search** — plain-text threads will be searched and reused (`rg` / `grep` across `threads/`) | Core |
| H4 | **Attention from files** — `status` files (tabline, `:AgentsNext`) will help you juggle several Claude Code sessions | Side benefit |

If H1–H3 fail, the thesis fails, whatever H4 shows.

## 2. Scope

**In M1**

- The thread format (ARCHITECTURE §4): the root at `~/agent-files/` (its own git repo), thread directories, `thread.md` with the turn grammar (§4.3), the `status` and `seen` sidecars, `## carry`, `steps/`.
- `agent-files-run` — the runtime for `direct` replay threads (§3.1).
- `agents.nvim` — a minimal plugin (§3.2).
- `agent-files-hook` — `observed` status for ordinary Claude Code sessions (§3.3).
- Measurement: auto-commit at each `END`, `agent-files-stats`, a daily journal (§3.4).

**Deferred until after the M1 decision**

- The supervisor, sub-threads and the inbox (M3); the Elixir version of it (§6).
- The tier-1 interactive bridge (M2).
- Tier-2 headless harnesses (Agent SDK, Codex, ACP).
- Tools in the runner — M1 threads are conversation only, so there are no tool folds and no permission questions.
- Grounding, the knowledge base, council, compaction.
- The doorbell (`agent-files-ring`, editor registry, `agent-files-notify`). Locally the file watcher is enough; see [role-of-neovim.md](role-of-neovim.md).
- Multi-machine use.

## 3. Deliverables

### 3.1 `agent-files-run` — the replay runtime

A single executable script (Python, a few hundred lines). Per principle 3 it is just a program on `PATH`; the later supervisor can replace it without changing any file. It is the **single writer** of every thread whose `runtime:` is `direct` (ARCHITECTURE §4.4).

- **Modes:** `agent-files-run watch` (long-running, watches `~/agent-files/threads/`) and `agent-files-run once <thread dir>`.
- **Send detection:** after a save, the last turn is yours, ends with `END`, and `status` is not `working` (ARCHITECTURE §4.3). A draft without `END` sends nothing.
- **Assembly (replay):** the agent's system prompt (`agents/<agent>.md`, or a default) → the `## carry` section, if any → every turn in order. The file *is* the context, so whatever you edited above `END` is what the model sees.
- **On a send:** write `working` to `status`; append `## agent · tN`; stream the reply, escaping any line that would parse as a marker; append `END`; append the scaffold `## you · tN+1`; write `done` to `status`; write `steps/tN.request.json` and `.response.json`; `git commit` in the root repo.
- **Interrupt:** if `STOP` appears in the thread directory, stop streaming, append `END (interrupted)`, write `interrupted`, delete `STOP`.
- **Conflicts and crashes:** a foreign write to `thread.md` mid-turn closes the turn with `END (conflict)`; on start-up, any `direct` thread left `working` is closed with `END (interrupted)` (ARCHITECTURE §4.5 rules 1, 3).
- **Model switching:** change `model:` in the frontmatter; the next turn uses it.
- **Backends** (chosen by `model:`):

| Backend | Cost (as of 2026-10) | Exact request in `steps/`? | Notes |
|---|---|---|---|
| Anthropic Messages API (API key) | API rates; cache writes 1.25×, reads 0.1× | Yes | Cleanest replay |
| OpenAI-compatible endpoint (Ollama, LM Studio, llama.cpp) | Free locally | Yes | Good for cheap iteration |
| `claude -p` | Draws from the monthly Agent SDK credit on Pro/Max (billed as tier 2, headless) | No — Claude Code adds its own prompt and tools | Verify flags at build time |

### 3.2 `agents.nvim` — minimal plugin

A few hundred lines of Lua.

- Detect `threads/**/thread.md`; `autoread` plus one `vim.uv.new_fs_event` watch per thread directory.
- Buffer read-only while `status` is `working`; on reload, re-apply an unsaved draft below the new last `END`.
- Tabline / statusline mark per thread from `status` and `seen`; a `working` status older than 10 minutes is marked stale (an interrupted observed session, §3.3); a rough token count of the thread (characters ÷ 4) so carried context has a visible cost.
- Commands:
    - `:AgentsSend` — append `END` to your turn and save.
    - `:AgentsStop` — `touch <thread dir>/STOP`.
    - `:AgentsNew <name>` — create `threads/<name>/thread.md` with frontmatter (`runtime: direct`, `context: replay`, `kind: main`) and `## you · t1`.
    - `:AgentsFork` — from a visual selection: create `<thread>/<child>/thread.md` with `kind: fork`, `branched_at: tN`, the parent's settings except `session`, a `## carry` section holding the selection, and `## you · t1`.
    - `:AgentsNext` / `:AgentsBlocked` — needs-you list in quickfix.
    - `:AgentsGrep <pattern>` — `rg` across `threads/` into quickfix; logs one line per search (for H3).
- Viewing a thread touches its `seen` file (your acknowledgment; ARCHITECTURE §4.5 rule 8).

### 3.3 `agent-files-hook` — observed status

Configured in `~/.claude/settings.json` for ordinary interactive `claude` sessions. It sends nothing to Claude; it only mirrors status, and it is the single writer of its observed threads.

- On a session's first event it creates `threads/_observed/<project>-<session short id>/` with a frontmatter-only `thread.md` (`runtime: observed`, the transcript path).
- Writes `status`: `UserPromptSubmit`, `PreToolUse`, `PostToolUse` → `working`; `Notification` with `permission_prompt` → `blocked`; `idle_prompt` ignored (it fires ~60 s after a finished turn); `Stop` → `done`; a failure event → `failed` (event name to verify at build time); `SessionEnd` → deletes the directory.
- Known gap: `Stop` is reported not to fire when you interrupt with Esc, so an interrupted session stays `working` until its next event; the plugin marks it stale after 10 minutes.

### 3.4 Measurement

- **Git history.** The runner commits at every `END` in the root repo. An edit above `END` shows up as a commit that changes or deletes lines above the last `END` instead of only appending.
- **`agent-files-stats`** reads `git log` and `threads/` and prints: threads, turns per thread, edits above `END` (count, and share of threads with 6+ turns that had one), forks and their `## carry` sizes, model switches, `:AgentsGrep` searches.
- **Journal** — `trial/journal.md`, one entry a day: what you used it for, what you used *instead* (the Claude app or plain TUI) and why, the worst friction, and for each fork whether it helped or hurt.

## 4. Trial protocol

- **Start:** when all deliverables pass a smoke test (one thread, one fork, one interrupt, one observed session).
- **Length:** ten working days of real use.
- **Use it for:** discussion, research and design threads — where context editing should matter. Heavy coding stays in the Claude Code TUI, observed through hooks.
- **Habits to try:** start each new question as a thread; when a thread drifts, try a fork with a `## carry` section before continuing; once a day, try answering something by searching old threads.
- **Midpoint check (day 5):** if you are defaulting to the Claude app or plain TUI for this kind of work more than half the time, stop and diagnose before continuing.
- **Allowed mid-trial:** fixing the worst friction. **Not allowed:** changing the thresholds.

## 5. Decision criteria

Set before the trial starts; revise them now if they look wrong, never after.

| Signal | Go | Kill |
|---|---|---|
| H1 — context edits | An edit above `END` in ≥ 20% of threads with 6+ turns | < 5% |
| H2 — clean forks | ≥ 5 forks, and the journal shows at least as many "helped" as "hurt" | < 2 forks |
| H3 — search | ≥ 5 cross-thread searches whose result you used | 0–1 |
| Fallback | < 30% of comparable sessions went to the Claude app or plain TUI | > 50% |

**Outcomes**

- **H1–H3 mostly go** → the thesis holds. Next, in an order the trial suggests: grow `agent-files-run` into the native loop (tools, `steps/` view — M6), add the supervisor and tier-2 headless agents (M3), then the interactive bridge (M2). Elixir only when a trigger in §6 fires.
- **Only H4 holds** → the value is attention, not context. Consider adopting an existing tool (Herdr, Juggler) for that, and stop building.
- **Nothing holds** → stop, and write down why in this doc.

## 6. Triggers for the Elixir supervisor

Move from scripts to the Elixir/Jido supervisor (ARCHITECTURE §9.2) only when one of these is *real*, not anticipated:

- Routinely more than ~5 agents running at once, and the scripts' process handling hurts.
- Crash-recovery or restart bugs are costing real time.
- Threads need to run across more than one machine.
- Tier-2 harness sessions must stay alive across many turns (long-lived SDK clients).

Until then the file format is the contract: replacing scripts never touches a thread.

## 7. Risks to the trial itself

| Risk | Mitigation |
|---|---|
| Builder bias — you built it and want it to work | Thresholds fixed in advance; the journal records fallbacks honestly |
| A clunky prototype fails for UX reasons, not the thesis | Friction journaled separately; fixing the worst friction mid-trial is allowed |
| Replay re-sends the whole thread every turn | Local models or the `claude -p` credit for cheap iteration; a daily spend cap in config |
| Frequent `:w` while composing sends half a turn | Sending needs an `END` line; saving alone sends nothing |

## 8. Effort

Under a week: runner about a day, plugin one to two days, hooks and stats half a day, smoke test half a day.

## 9. Open questions

1. `claude -p` as a replay backend: which flags minimize Claude Code's own system prompt and tools, and is the exact request observable at all?
2. One global root (`~/agent-files/`) is the M1 default. Do per-project roots pay off later?
3. Is characters ÷ 4 a good enough token estimate for the status line, or should the runner record exact counts from API usage (in `steps/`)?
