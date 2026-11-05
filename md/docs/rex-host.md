# Rex as the host — how Superlogical Rex works with agent-files

> Status: decision record · 2026-11-04 · companion to [ARCHITECTURE.md](../governance/ARCHITECTURE.md) §5.1, §12
> **Supersedes the host decision in [host-analysis.md](host-analysis.md)** (TUIOS hosts, herdr fallback) and the "keep TUIOS" line in [direction-analysis §4](direction-analysis.md#4-the-host-fork-reconsidered). Those documents stay as they are, as the record of the earlier decision; where they name TUIOS as the host, read Rex.
> Method: the installed Rex Beta 0.1.0 (1758), whose CLI is `rex 0.0.1793645657-gd018d2`: its `--help` for every command, the guide it gives agents (`rex skill show`), the server and app actions (`rex actions`, `rex -C <app> actions`), and one look at a live server (`rex whoami`, `rex ls`, `rex block call … program_status`). Nothing was run inside Rex beyond that. *(cli)* marks a claim read from the CLI's help or guide but not exercised.
> **Narrowed (2026-11-04):** agent-files is now Neovim-first. `agents.nvim` starts and shows the `claude` and `codex` sessions in Neovim terminal buffers ([sidebar plan](../plans/2026-11-04-nvim-sidebar/nvim-sidebar.md)); Rex hosts Neovim, not the sessions directly. A harness in its own Rex block still works but is not the path agent-files is built for.

**Decision.** Rex hosts harness sessions and the operator's editor. TUIOS (installed, pinned at 0.12.1) is the fallback, then herdr. agent-files stays what it was: the logbook beside the host, reached by the host only through Claude Code's hooks, and reaching the host only through one adapter module (none is needed for M1). Attention for harness sessions moves from the TUIOS Inbox to agent-files' own observed threads in `agents.nvim`, plus Rex's Activity sidebar.

## 1. Why, against the tool that grades higher

By the count in [host-analysis §1](host-analysis.md#1-session-host-and-attention--21-items), TUIOS covers more of the plan than Rex (§2 below: TUIOS 10 F, Rex 4 F). The rule "the tool that covers the most goes first" would keep TUIOS. It is set aside here for one reason that the grading did not weigh: **how the operator actually works**.

- The operator runs harness TUIs inside Neovim's `:terminal` splits, beside the files, and moves between them with `ctrl-w`. A host sees that whole Neovim as one pane.
- Most of what TUIOS scored on works per pane: the Inbox, `peek-prompt` / `respond`, `fan`, per-agent worktrees, checkpoints. With agents inside Neovim, TUIOS would see one pane running `nvim` and none of those items apply. Its hook-reported status would still arrive, but filed under the one Neovim pane.
- What the operator was missing is what both hosts give: **persistence** (close the terminal app, keep every session) and **remote machines**. Rex gives them as the terminal itself, built on libghostty, with no terminal-inside-a-terminal layer. TUIOS is a TUI that would run inside Ghostty.
- The attention TUIOS would have provided already exists in agent-files: `agent-files-hook` writes an observed thread per Claude Code session, and `:AgentsNext` / `:AgentsBlocked` list the ones that need you ([role-of-neovim](role-of-neovim.md)). With Rex, the observed threads carry it.

What is given up: answering a permission prompt without opening the pane (C5), worktrees per agent with merge-back (C10), fan-out (C20) and per-turn checkpoints (C15). None of these is in M1. Claude Code's own `/rewind` covers checkpoints; worktrees and fan-out are done by hand or by a later milestone graded on its own.

## 2. Rex against the 21 host items

F = does it as specified or better, P = partly, N = not at all, ? = not found.

| # | Planned capability | Rex |
|---|---|---|
| C1 | Host unmodified TUIs, detached; attach any time | F — a server holds every terminal; the app is one client of it (`rex server start`, `rex client ls`) |
| C2 | Send input, capture output from a script | F — `rex send`, `send-key`, `capture` (screen and scrollback, ~64 MiB), `--json` on every command |
| C3 | Status per harness session | P — `program_status` per block reads OSC 7501, which Superlogical wrote *(cli)*; no hook-reported status. agent-files' observed threads cover Claude Code |
| C4 | Needs-you list across sessions, jump, notify | P — the app's Activity sidebar, by session or by priority (`client.sidebar.activity.*`) *(cli)*. Inside Neovim, `:AgentsNext` over observed threads |
| C5 | Answer permission prompts without opening the pane | N — blind `send-key` only |
| C6 | Seen vs unseen-done | ? |
| C7 | Interrupt from outside | P — `send-key esc` / `ctrl+c` |
| C8 | State machine-readable to other tools | F — `rex events --json` streams session and block events; `rex api` |
| C9 | Agent spawns an agent and gets its result | P — `rex run --wait` returns the exit status; `capture` reads the output |
| C10 | Worktree per agent, merge back | N |
| C11 | Remote machines in one view | F — `rex hosts add LABEL ENDPOINT`, `-S host`; `rex server tailscale`; ssh-forwarded sockets *(cli)* |
| C12 | Survive terminal quit / server restart / reboot | P — the app quits and the server keeps every process; reboot not checked |
| C13 | Neovim integration | P — none of its own; it hosts Neovim whole. Inside Neovim, `agents.term` (ARCHITECTURE §11.2) |
| C14 | Greppable transcript | P — `capture` of the scrollback; the harness's own JSONL is still the transcript |
| C15 | Per-turn checkpoints of code | N |
| C16 | Hooks that can block a turn | N — its Claude Code hook only reports the Rex session and pane at `SessionStart` |
| C17 | Commits linked to the session | N |
| C18 | Usage / cost / budgets | N |
| C19 | Headless agents | N — runs any command; no protocol panes |
| C20 | Fan one prompt to several agents | N — scriptable with `rex run` |
| C21 | Platform, license, maturity | P — public beta since 2026-10-05, macOS app, CLI version 0.0.x; Superlogical (Mitchell Hashimoto's company); free, no account |
| | **Total** | **4 F · 9 P · 7 N · 1 ?** |

## 3. How Rex and agent-files fit

```
 Rex server (this Mac, or a remote host)
 └─ session per repo ── window (tab) ── block (pane)
                                         └─ nvim ── :terminal claude ─┐  hooks   ┌─ agent-files-hook
                                                    :terminal codex   ├────────▶ │  threads/_observed/…/status
                                                    :terminal zsh     │          └─ agents.nvim marks, :AgentsNext
                                                                       │
                                         └─ (or) claude in its own block ┘
```

- **Rex owns the processes; agent-files owns the record.** Nothing in a thread depends on Rex. Kill the Rex server and every thread is intact; only the running harness processes are lost (principle 1).
- **The hook path is unchanged.** `agent-files-hook` is configured in Claude Code, not in the host ([m1-plan §3](../plans/2026-10-31-m1/m1.md)), so the observed thread appears the same under Rex, TUIOS or a bare terminal. S9 is run inside Rex.
- **Rex's own Claude Code integration coexists.** `rex skill setup` added one `SessionStart` entry to `~/.claude/settings.json` (`rex __internal session-start …`, which tells the agent its `REX_SESSION` and `REX_BLOCK`), and a skill at `~/.claude/skills/rex`. The `agent-files-hook` entries go beside it, and Claude Code runs both. That hook calls `rex` by name, so `rex` must be on `PATH`. It is a link in `~/.local/bin` to the CLI inside `Rex Beta.app` (2026-11-03).
- **A harness inside Neovim inherits Neovim's `REX_BLOCK`.** To Rex, it is the Neovim pane. A `rex send` to that block types into Neovim, not into the harness. Reach a harness inside Neovim through `agents.term` (ARCHITECTURE §11.2), and a harness in its own Rex block through `rex send`.
- **Adapter rule.** Anything agent-files does with Rex goes through its JSON CLI from one module, so a switch back to TUIOS or to herdr changes one file. M1 needs none.
- **Multi-machine.** A Rex host on another machine (`rex hosts add`) runs the harness sessions there, which keep going while the laptop sleeps. The hook writes observed threads into *that* machine's data root; agent-files' own runtimes still run on one machine per root (ARCHITECTURE §13 Q9). A Rex host gives you a box, not a sandbox: isolation, network policy and per-task cleanup are whatever the machine provides, unlike cloud Claude Code sessions.

## 4. The policy rule under Rex

ARCHITECTURE §5.1 keeps its hard rule, now stated per harness: **a harness whose terms allow only human-written input in interactive sessions gets only text a human wrote.** Claude Code on a subscription is one, and Codex is treated as one until its terms are read (§13 Q6). A harness on an API key, or one whose terms allow it, may take text from another agent.

Under Rex this rules out:

- `rex send` / `send-key` carrying agent-written text into a block that runs `claude` or `codex`. The Rex skill teaches agents these commands for any pane, so the rule is the agent's to keep. Nothing enforces it; it is residue (ARCHITECTURE §9.7).
- `agent-files-term send` into a Neovim terminal running such a harness. This one is enforced: `agents.term` refuses agent sends to a terminal whose harness policy is `human` (§11.2).

Still allowed: your own text through either path (`:AgentsTermSend` on a selection, `rex send` from your own shell), reading any pane (`rex capture`, `agent-files-term capture`), and agent text into shells, dev servers and API-keyed harnesses.

## 5. What changes elsewhere

- ARCHITECTURE v0.7: §1, §5, §5.1, §8, §10, §11 (new §11.2), §12, §13 Q8, Q9, Q13–Q15, §14.
- README, AGENTS.md, next-agents.md, next-operator.md (step 2a is now "Host in Rex"; S9 runs inside Rex), role-of-neovim §1.
- The operator's own Neovim layout, outside agent-files: [md/operator-neovim.md](../operator-neovim.md).
- Not edited, read with this record: [host-analysis](host-analysis.md), [direction-analysis](direction-analysis.md), [juggler-analysis](../analysis/2026-10-31-juggler/juggler.md) (worktrees "adopted from TUIOS" are now unowned), [multi-subscription-analysis](../analysis/2026-11-01-multi-subscription/multi-subscription.md) ("replace TUIOS" now means "replace Rex"), [m1-plan](../plans/2026-10-31-m1/m1.md) (the needs-you list for harness sessions is the observed threads), and the session logs (now in thread-archive, `threads/agent-files/`).

## 6. Sources

- Rex: the installed app and CLI (versions above). The beta date, "free" and program status come from the sources of [direction-analysis](direction-analysis.md#sources): [mitchellh.com/writing/superlogical](https://mitchellh.com/writing/superlogical), [public testing](https://superlogical.com/updates/public-testing-beginning), [program status](https://www.superlogical.com/rex/docs/build/program-status).
- The TUIOS grades this is compared against: [host-analysis §1](host-analysis.md#1-session-host-and-attention--21-items).
