# Direction — the logbook, a planning harness, and what to adopt

> Status: decision record · 2026-11-02 · companion to [ARCHITECTURE.md](../ARCHITECTURE.md) §1, §7, §8.1, §9.6, §14
> Method: the git history before and after the TUIOS decision (`6e60896`, `e194b0a`), the installed TUIOS binary, the operator's related repos, and a web survey of hosts, harnesses and attribution tools (2026-11-02). Where only a secondary page says so, it is marked *(unverified)*.

**Decision.** agent-files is the **logbook for human–agent work**. It is not a host and not a coding harness. It keeps TUIOS as the host. It builds a small **planning harness**, grown from `agent-files-run`. Coding is farmed out to Claude Code and Codex, and their sessions come back as records. The knowledge base is built on **artifact-dag**. Capture tools for coding sessions (Entire first) are graded before any capture is built. M1 runs unchanged; attribution and the DAG are the next trial. agent-files is built for the operator first, in a shape that could become a product (§7).

## 1. What agent-files is for

> **The logbook for human–agent work: every exchange a file you can edit as context, every settled conclusion a node that records who or what accepted it, every change linked to the turns and decisions behind it — beside any harness, under any host.**

The harnesses are the engines; TUIOS (or herdr, or Rex) is the cockpit; the logbook outlives both.

**The logbook loop:**

```
plan ──► brief ──► coding session ──► record ──► DAG ──► grounding ─┐
 ▲   (planning      (Claude Code /     (transcript,   (gate, then    │
 │    harness)       Codex, in TUIOS)   commits,       acceptance)    │
 │                                      checks)                      │
 └───────────────────────────────────────────────────────────────────┘
```

The planning harness is where the loop starts and closes. Coding harnesses, and the capture of their sessions, are the other half; those are adopted, not built. Each part exists somewhere: Entire for the record, Juggler for editable context, artifact-dag for knowledge. No one joins the three.

## 2. Strengths, checked

| Claimed strength | Verdict |
|---|---|
| **Clear attribution** | There are two kinds. **Within a thread** (the human region vs escaped machine text, exact requests in `steps/`), the strength is real, built and distinctive, but it covers only threads agent-files runs. **Commit ↔ conversation** links are real but already taken: Entire has an `Entire-Checkpoint` trailer and `refs/entire/checkpoints/…`, git-ai has line attribution in git notes, and Zed's DeltaDB records every edit (§6). Adopt their formats; don't build. Today, observed Claude Code sessions get no attribution at all: the hook writes only `status` and the transcript path. |
| **Modular context engineering** | The strongest strength and the least contested. Nobody combines a markdown source of truth, edit-and-replay across models, and git. The nearest are Juggler (its own harness), gptel and codecompanion (editor buffers), and md-ai (13★). The limit: it works only where agent-files owns the loop. Never inside Claude Code, which owns its own context. |
| **A DAG on agent–operator interactions** | The most distinctive strength. Seven of the operator's repos share this core: socrates, itsjustshell2, manifold, elixir-mind, composable-beliefs, artifact-dag and agent-files. artifact-dag is the one in real use: identikey-dev alone has 564 nodes. The acceptance and invalidation machinery elsewhere was built or designed but has not been run on real input ([related-repos](related-repos.md)). |
| **Subscription pricing, existing harnesses** | Real for the operator. Signing in to the unmodified CLI with your own subscription is allowed. `claude -p` and the Agent SDK draw from plan limits; the separate Agent SDK credit announced 2026-05-13 was paused 2026-06-15. As a moat it is weak: every host already lets you bring your own subscription, and the terms changed several times in 2026. It cuts costs; it doesn't set agent-files apart. |

## 3. Weaknesses, and the planning harness

- **GUI.** The interaction model itself (type `END` to send, edit above `END`) is unfamiliar to most people. It doesn't matter for the operator's own use; it is the main barrier for a product. The HTML view is the cheap test of it. Reaching GUI users takes the web, not a terminal toolkit.
- **A custom harness.**
  - *A general coding harness was considered and rejected.* It would compete with Juggler, which already has editable history (rewind, fork, delete), full step inspection with cache-miss warnings, Claude through the unmodified CLI on Pro/Max, desktop, browser and phone clients, and headless mode. Behind Juggler are Claude Code, Codex, OpenCode, Pi and Crush. The cost would be coding quality, sandboxing, upkeep for every provider, and the operator's time, all taken from the parts only agent-files has.
  - *A planning harness is the decision.* Planning, research, review, extraction and proposing nodes happen in agent-files' own loop. Coding is farmed out. This was mostly the original plan: v0.4 listed "being the main coding harness" as a non-goal, and [juggler-analysis §6](juggler-analysis.md#6-should-we-have-our-own-agent-loop) scoped a small loop to that work. What it left vague was the handoff in both directions. Now it is first-class: briefs out, records back ([ARCHITECTURE §8.1](../ARCHITECTURE.md#81-the-logbook-loop--briefs-out-records-back)).
  - *Differentiation from Juggler:* a DAG whose nodes record who accepted them, with invalidation that reaches threads and commits (Juggler has a `MEMORY.md` and no knowledge base or decision record). Also a record of *other* harnesses' sessions, and markdown as the source of truth. Juggler could even be one of the engines coding is farmed out to.

## 4. The host fork, reconsidered

- **The plan before TUIOS never aimed at a multiplexer.** ARCHITECTURE v0.4 (`6e60896`) listed "Being a terminal. Ghostty renders; tmux hosts" as a non-goal. It built the tier-1 bridge (the file as a second keyboard into the `claude` TUI), the Neovim doorbell and an Elixir supervisor. TUIOS replaced hosting and attention ([host-analysis](host-analysis.md)). The bridge went because tier 1 is resume-only: editing the file could never change what Claude saw.
- **TUIOS is built on Charm throughout.** The installed v0.12.1 binary contains Bubble Tea v2, Lip Gloss v2, Ultraviolet, Wish v2, `charm.land/ssh` and `x/xpty`. Following its lead would mean building a host. The host layer is the worst place for agent-files to build:
  - **Crowded.** TUIOS has one developer and 55 releases in 14 months; herdr has a $6M seed and 47.6k★; Superlogical Rex (Mitchell Hashimoto's company, on libghostty, public beta since 2026-10-05); cmux, Conductor, T3 Code and Paradev; and the vendors' own Codex app and Claude Desktop Code tab.
  - **Commoditizing.** Agent status is a shared protocol (OSC 7501, written by Superlogical, used by TUIOS, herdr and libghostty).
  - **Unmonetized.** Rex "will always be free"; herdr charges for a Cloud relay, not for the host; Vibe Kanban shut down at 28.6k★ because it "couldn't find a business model."
- **Keep TUIOS.** The adapter rule (§5.1) lets Rex or herdr replace it. Rex has not been graded; add it if hosts are re-graded.
- **Where Charm could fit later:** a terminal viewer for the record (threads, DAG, provenance), possibly served over SSH with Wish. It would be a client over the files, not a host.

## 5. `claude -p` as the planning harness's cheap mode

`claude -p` with the verified M1 flags strips all of Claude Code's tools, settings and prompt (666 input tokens for a whole request; [build spec §14.1](m1-build-spec.md#14-open-questions-for-the-build)). With `--mcp-config` and `--strict-mcp-config` it runs only the tools we supply. `--json-schema` gives structured output, which suits proposals that must pass the gate. So the planning harness can be agent-files' context assembly plus its own tools over MCP, with `claude -p` making the model call on the operator's plan.

| Limit | What it touches | Effect on the value |
|---|---|---|
| The exact request isn't observable, only what we sent | Attribution | Small. The gap is Claude Code's known `userEmail`/Environment block. For tracing decisions, what was assembled plus the reply is the evidence. The full-fidelity claim ("exact requests") needs the API backend. |
| History is flattened into one prompt (`[you]`/`[agent]` labels); no real assistant turns, no prefill | Editable context | Editing still works: what you edit is what gets sent. The model reads the thread as a document. This is a quality question to measure, not a design flaw. A synthetic Claude Code session file with `--resume` would restore turns, but it depends on an internal format. |
| Probably no cache reuse between turns (the thread is one block that changes every turn) *(unverified)* | Plan limits | Measurable at no cost: `steps/*.response.json` records `cache_read_input_tokens` for `claude-cli` turns. |
| Replay resends the whole thread | Plan limits | The design already pulls against it: forks with a small `## carry`, grounding on nodes instead of old transcripts (§6). |
| Policy durability | A product, not personal use | The real risk. Personal use of the unmodified CLI is explicitly allowed. For a product used by others, anything built on the Agent SDK must use API keys. The subscription stays a cost option, never the pitch. |

**Conclusion:** `claude -p` is the cheap mode, with its caveats in `backend_caveats`; the API backend is the full-fidelity mode. The value of the loop does not depend on `claude -p`.

## 6. Neighbours: integrate or compete

They all answer *which conversation wrote this line?* agent-files answers the next question: *which decision is this line serving, and is that decision still true?*

| Tool | What it is | Stance |
|---|---|---|
| **Entire** (entire.com; Thomas Dohmke, ex-GitHub CEO; $60M seed 2026-02) | "A Git forge built for agent–human collaboration." Its MIT CLI (`entire enable`) installs hooks in Claude Code, Codex, Cursor, Copilot CLI, OpenCode, Pi and others (more through `entire-agent-<name>` binaries). Each commit with agent work gets a checkpoint (prompts, transcript, files touched) under `refs/entire/checkpoints/…`, linked by an `Entire-Checkpoint` trailer. Capture works locally with no account; hosting, "Trails" and search are the paid forge. It doesn't edit context or accept knowledge. Transcripts are pushed with the code, and redaction is "best effort". | **Integrate** at capture: grade it first for the return path of §8.1. **Avoid** the forge. **Watch** its memory, which pairs sessions with a code graph to retrieve "files, symbols and decisions" *(unverified)*. If that grows acceptance and retraction, it competes with the DAG. |
| **Zed DeltaDB** (announced 2026-06-11; early access) | Version control by fine-grained deltas, each with a stable id. From any line you can find the conversation that produced it and every later conversation that touched it. CRDT worktrees; git stays for CI and the outside world. It powers Zed's own Delta harness; support for other harnesses is unclear *(reports conflict)*. | **Integrate** if it opens up: a delta id is a source a node can cite. Not a target to beat. |
| **git-ai** | Line attribution in git notes, `git ai blame`; the founders joined OpenAI's Codex team. | A format to read, not a dependency. |
| **Agent Trace** (Cursor, RFC 2026-01) | A JSON spec linking code ranges to conversations; storage left open. Its GitHub repo returned 404 on 2026-11-02. | Emit it only once it settles. |
| **SpecStory** | Saves sessions as markdown under `.specstory/history/`; "Lore" mines history into skills. | Overlaps the transcript mirror. Grade it with Entire. |
| **Juggler** | Its own coding harness with editable history and step inspection (§3). | Not a competitor for a planning harness; possibly one of the engines. |

## 7. Built for the operator first, kept product-shaped

- **The operator's own use comes first.** The itch is proven: seven repos keep returning to the same core. What's unproven is daily use of the acceptance and invalidation machinery. An open gap isn't proof of demand (md-ai 13★, Juggler 848★).
- **Where the money is in this category:** hosted record-keeping (Entire's forge) and per-seat GUIs (Conductor). For tools where the user owns the files, the model that works is a free local tool plus paid sync, publishing or team features (Obsidian, herdr Cloud, SpecStory's cloud). For agent-files that would be teams reviewing agent PRs through the record (§9.6). A solo trial can't test that.
- **Product-shaped means four rules,** written into ARCHITECTURE §2 (principle 13):
  1. **The format can be pulled out.** It gets a standalone, versioned spec (`FORMAT.md`), separate from ARCHITECTURE, which mixes format and plans. `docs/examples/view-fixture/` grows into a conformance suite that every parser passes; a JavaScript viewer would be the third, after Python and Lua. Implementation-only fields go in sidecars. Knowledge-base nodes use artifact-dag's schema, not a parallel one.
  2. **The hook can be pulled out.** It stays standard-library-only and silent, and gets a documented contract (event in, files out), so it installs and works without the runner or Neovim. Codex is added the same way.
  3. **Links use shared formats.** Every turn is addressable as `<thread path>#tN`; turn ids are never renumbered, so the address is stable. Commit trailers follow §9.6. When an `Entire-Checkpoint` trailer is present, its id goes in the thread's `commits` sidecar instead of capturing the session twice. Agent Trace JSON is emitted only once that spec settles. Nodes cite turns, commits, checkpoints and delta ids in `sources:`.
  4. **The viewer is HTML.** It is a static page built from the data root, like artifact-dag's `build-viewer`. It shows threads with their status, the DAG (reusing artifact-dag's viewer) and the chain from decision to turns to commits. It is read-only; markdown stays the only source. Editing in a browser comes only with a product, through a local server that obeys the same one-writer rule.
- **Acceptance is a choice.** Not everyone will want to approve every node by hand. The gate (no cycles, no dangling references, sources resolve) is always on. Acceptance is a policy per node type: `manual`, `auto` or `sample`. Every node records `accepted_by`, so attribution survives automation (ARCHITECTURE §7).
- **Reconsider "product" only when** the trial passes, the operator has used the record → accept → ground loop for a month, and two or three other people use it without help.

## 8. The trials

- **M1 runs unchanged.** Its build spec, hypotheses and thresholds ([m1-plan §5](m1-plan.md#5-decision-criteria)) stay as they are. M1 tests modular context engineering only (H1–H3).
- **Free measurements during M1** (no new building): for `claude-cli` turns, the `cache_read_input_tokens` in `steps/*.response.json`; and whether a thread sent through `claude-cli` reads as well as the same thread sent through the API backend. The journal can note both.
- **The record trial comes next.** It tests attribution and the DAG on real coding work:
  - capture of coding sessions (Entire graded first, else a transcript mirror of observed sessions);
  - commit links (§9.6);
  - M5a on artifact-dag;
  - extraction proposing nodes from those records.

  Its hypotheses and thresholds are written before it starts, as M1's were. It tests a different thesis from M1: if H1–H3 fail, editable context fails, not the record. Whether the record trial still runs is decided at day 10.

## Sources

- agent-files history: ARCHITECTURE v0.4 at `6e60896`; the TUIOS decision `e194b0a`; [host-analysis](host-analysis.md); [related-repos](related-repos.md); [multi-subscription-analysis](multi-subscription-analysis.md)
- TUIOS: the installed binary (`tuios version 0.12.1`), [github.com/Gaurav-Gosain/tuios](https://github.com/Gaurav-Gosain/tuios)
- herdr: [herdr.dev](https://herdr.dev), [seed announcement](https://herdr.dev/blog/herdr-raised-a-seed/)
- Superlogical Rex: [mitchellh.com/writing/superlogical](https://mitchellh.com/writing/superlogical), [public testing](https://superlogical.com/updates/public-testing-beginning), [program status](https://www.superlogical.com/rex/docs/build/program-status)
- Vibe Kanban shutdown: [vibekanban.com/blog/shutdown](https://www.vibekanban.com/blog/shutdown) · Conductor: [conductor.build/pricing](https://conductor.build/pricing)
- Juggler: [juggler.studio/features.html](https://juggler.studio/features.html) (read 2026-11-02)
- Entire: [github.com/entireio/cli](https://github.com/entireio/cli), [TechCrunch 2026-02-10](https://techcrunch.com/2026/02/10/former-github-ceo-raises-record-60m-dev-tool-seed-round-at-300m-valuation/), [everydev](https://www.everydev.ai/tools/entire) *(memory, unverified)*
- Zed DeltaDB: [zed.dev/blog/introducing-deltadb](https://zed.dev/blog/introducing-deltadb), [alphasignal](https://alphasignal.ai/news/zed-s-deltadb-rebuilds-version-control-around-ai-agent-conversations), [mindstudio](https://www.mindstudio.ai/blog/zed-delta-ai-coding-agent)
- git-ai: [github.com/git-ai-project/git-ai](https://github.com/git-ai-project/git-ai), [The New Stack](https://thenewstack.io/openai-hires-git-ai/) · Agent Trace: [agent-trace.dev](https://agent-trace.dev) · SpecStory: [specstory.com](https://specstory.com) · md-ai: [github.com/carlassmann/md-ai](https://github.com/carlassmann/md-ai)
- Anthropic terms and billing: [code.claude.com/docs/en/legal-and-compliance](https://code.claude.com/docs/en/legal-and-compliance), [Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
