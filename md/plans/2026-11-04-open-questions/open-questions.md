# Plan: the open questions

> Status: proposed · 2026-11-04 · gathers the open questions from [ARCHITECTURE §13](../../governance/ARCHITECTURE.md#13-open-questions), [build spec §14](../../docs/m1-build-spec.md#14-open-questions-for-the-build) and [juggler §7](../../analysis/2026-10-31-juggler/juggler.md#7-questions-raised), so no document under `md/` holds one (repo-template guideline 6)

Each question keeps its source number with a prefix: `A` for ARCHITECTURE §13, `S` for the build spec §14, `J` for juggler §7. Other documents cite them as before (`§13 Q6` is `A6`). When a question is answered, delete it here and record the answer where it came from, as a closed item. When the step that waits on one comes up, it moves to `next-operator.md`.

Questions that belong to one plan stay in that plan: [sidebar](../2026-11-04-nvim-sidebar/nvim-sidebar.md#questions), [nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md), [dag-orchestration](../2026-11-03-dag-orchestration/dag-orchestration.md#questions).

## Design (ARCHITECTURE §13)

<a id="a3"></a>**A3.** Default `context:` mode — resume for code threads, replay for discussion threads?

<a id="a5"></a>**A5.** KB granularity and how much grounding to inline vs. summarize.

<a id="a6"></a>**A6.** Codex and other vendors' terms for headless use on consumer plans.

<a id="a8"></a>**A8.** Which Juggler borrowings to adopt beyond branching-as-directories: intra-turn states (now designed from Pi Durable's recovery patterns, juggler-analysis §3), an approval rules file, budgets. Worktree workspaces are not planned.

<a id="a9"></a>**A9.** Locks across machines, for agent-files' own runtimes only (harness sessions on other hosts are Rex's): an advisory `lock` file naming the host, or "runtimes only on one machine"? Default: one machine.

<a id="a10"></a>**A10.** How a sub-thread's agent declares its turn final (a structured marker, a tool call, or always one task per sub-thread).

<a id="a11"></a>**A11.** **Enforcement (§9).** Which of an agent's tests count as protected oracles and which are its own working tests? How fast must ring-0 checks be before they slow the loop more than they save? How do exceptions expire? Which formal tools are worth it for which cores? Can Claude Code's `Stop` hook reliably keep a session working until checks pass, without loops?

<a id="a12"></a>**A12.** **Pi as a harness.** Pi (`pi --mode rpc`, MIT, multi-provider) could serve as a tier-2 harness for non-Claude models, or as the M6 loop instead of growing our own. Open: can its RPC mode or extensions write the exact requests we want in `steps/`? Pi Durable itself is ruled out as a foundation: it owns opaque state and history is immutable, so it cannot replay an edited file ([host-analysis](../../docs/host-analysis.md)).

<a id="a13"></a>**A13.** **Claude Code's own features vs. M3.** Its subagents, `/rewind` and session forking overlap sub-threads for coding work. Grade them against M3 before building it, as TUIOS and Rex were graded against M2.

<a id="a14"></a>**A14.** **Host gaps to watch:** Esc leaves an observed session "working" (a Claude Code gap); whether sessions survive a Rex update.

<a id="a15"></a>**A15.** **T3 Code as a host.** T3 Code runs Claude Code, Codex and others from one GUI, on the operator's own subscriptions. It could replace Rex beside agent-files only if its Claude sessions fire `agent-files-hook` (S9 run in T3 Code). CLIProxyAPI is rejected for Claude: it proxies subscription tokens, which Anthropic forbids. See [md/analysis/2026-11-01-multi-subscription/multi-subscription.md](../../analysis/2026-11-01-multi-subscription/multi-subscription.md).

<a id="a16"></a>**A16.** **Entire for capture.** Grade Entire (and SpecStory) against what the return path in §8.1 needs, before building any capture of coding sessions. The test: capture of observed Claude Code and Codex sessions, a checkpoint id we can cite, local-only use with no account, and transcripts kept out of public remotes. Open: what its memory (entire-brain) does.

<a id="a17"></a>**A17.** **`claude -p` fidelity for the planning harness.** Does a flattened thread read as well as the same thread through the API backend, and do `claude-cli` turns get cache reads? Cache reads can be observed at no cost in `steps/*.response.json`; reading quality, by using both. A synthetic session file with `--resume` would restore real turns, but it depends on Claude Code's internal format.

<a id="a18"></a>**A18.** **How a coding session reads a brief.** Options: by path, with `--add-dir` for the data root; a copy committed into the code repo; or a `CLAUDE.md` import. Decide at M6.

<a id="a19"></a>**A19.** **Acceptance defaults.** Which node types default to `manual`, `auto` or `sample` (§7), and what share `sample` sends for review.

<a id="a20"></a>**A20.** **Product.** Reconsider only when the operator has used the record → accept → ground loop for a month, and two or three other people use it without help ([direction-analysis §7](../../docs/direction-analysis.md#7-built-for-the-operator-first-kept-product-shaped)).

## Build (spec §14)

<a id="s2"></a>**S2.** **Effort per thread.** M1 uses one `effort` from config. If a per-thread knob is wanted, add an optional `effort:` frontmatter field — a format addition, not a change.

<a id="s3"></a>**S3.** **Spinner cost.** A 120 ms timer redrawing the tabline is cheap, but if it flickers in Ghostty, fall back to a static `…`.

## From the Juggler analysis (§7)

<a id="j2"></a>**J2.** Is the `events.jsonl` sidecar worth its weight from M1, or only once the native loop exists?
