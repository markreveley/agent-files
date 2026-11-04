# DAG-grounded orchestration: analysis

> Status: draft · 2026-11-03 · companion to [ARCHITECTURE.md](../../ARCHITECTURE.md) §6, §7, §8.1 and [direction-analysis](../docs/direction-analysis.md) §3, §5 · plan: [dag-orchestration](../plans/dag-orchestration.md)
> Method: the operator's proposal and answers (thread of 2026-11-03), the repo's design docs, the operator's two project DAGs (counted 2026-11-03), `claude --help` on Claude Code 2.1.317, and a web survey (2026-11-03). Claims that rest only on a secondary page are marked *(unverified)*.

**Summary.** The proposal works like this:
- An orchestrator reads a question, picks the DAG nodes it touches, and hands that subgraph, with a plain-English rendering, to an agent.
- The agent explores by walking DAGs first. It has an index of other DAGs it can walk too.
- Answers may claim nothing that the DAG or a cited source doesn't support.

Most of this is already designed: the orchestrator is the planning harness (M6), and the subgraph it hands over is the brief (§8.1). Four parts are new: choosing nodes from the question, a walk tool, a registry of DAGs, and labelling every claim in an answer. The evidence says a graph is cheaper than grep, not more accurate. For a knowledge DAG the gain is knowing what was accepted, not speed. All of it is M6 work; nothing is built before the day-10 decision. The order of work and its open questions are in the [plan](../plans/dag-orchestration.md).

## 1. The proposal, mapped

| Proposal | Already in the design | New |
|---|---|---|
| The orchestrator holds the overall context | Planning harness (M6) | — |
| Hand an agent exactly the right nodes | Brief: the task plus accepted nodes and their dependencies, depth-capped, with a "no silent caps" line (§8.1, §6) | Choosing the nodes from the question; a plain-English rendering of the subgraph |
| The agent starts by walking the DAG | — | A walk tool: a node's neighbours and dependencies, served over MCP (§2) |
| An index of other DAGs | artifact-dag ids are global; a link to an id outside the collection is an external node; the viewer joins several collections | A registry, so an external id resolves (§6) |
| Rebuild the context on each follow-up, or use the cache | `context: replay` or `resume` per thread (§6) | A warning before each send giving what that choice costs (§2) |

**Decided in the thread (2026-11-03):**
- Knowledge graphs first, code graphs possibly as well (§4).
- "Resource DAGs" means both: other projects' DAGs and DAGs built from outside material (§6).

## 2. What `claude -p` lets the orchestrator control

An interactive Claude Code session owns its context. A headless `claude -p` run is different: the orchestrator sets everything it starts with.

| Lever | Flag | Verified |
|---|---|---|
| System prompt | `--system-prompt` replaces Claude Code's; `--append-system-prompt` keeps it and adds ours | Replace, in M1: the whole request was 666 input tokens (spec §14.1) |
| First message | The brief, on stdin | Yes, M1 sends the prompt this way |
| Built-in tools | `--tools "Read,Grep,Glob,Edit,Bash"`, or `""` for none | `""` only |
| Extra tools | `--mcp-config` with `--strict-mcp-config`; the DAG walk tool goes here | No |
| Settings and hooks | `--setting-sources` (`user`, `project`, `local`) | None loaded in M1 |
| `CLAUDE.md` | Not loaded in M1, but that check ran in an empty temp dir. Whether it is found in a repo is unverified. `--bare` skips its discovery, but `--bare` accepts only `ANTHROPIC_API_KEY` | No |
| Follow-up | A fresh run rebuilt from files (replay), `--resume <id>` (resume), or `--resume <id> --fork-session` (branch a resumed session) | No |
| Structured output | `--json-schema` | No |

What it does not control:
- What builds up during the run: tool results and Claude Code's own compaction. The orchestrator sets the start of each run and chooses between runs, not the middle of one.
- The `userEmail` reminder and the `# Environment` block (spec §14.1).
- The exact request. Only the stream is visible.

**Which prompt to use:** replace it for planning, which is verified and gives full control. Append to it for coding, which keeps Claude Code's prompt tuned for its own tools. Grade the trade-off on real briefs.

**Cache or not, as an informed choice:** Juggler's features page describes no switch for this. Instead, a warning before each send says when the next request will miss the prompt cache, and why. The equivalent here is one line before a follow-up: rebuild (about N tokens re-written) or resume. At human pace the 5-minute cache has usually expired anyway (ARCHITECTURE §6), so a rebuild usually costs nothing extra.

## 3. Delegation: evidence and risks

- **Anthropic's research system:** a lead agent with subagents beat a single agent by 90.2% on an internal research eval.
  - It used about 15× the tokens of a chat.
  - Token use alone explained 80% of the variance on BrowseComp, so much of the gain is extra spending.
  - Anthropic calls it a poor fit where agents must share the same context, and says coding has fewer truly parallel tasks than research.
- **Cognition:** "actions carry implicit decisions". Subagents working from part of the context make conflicting choices. A brief therefore has to carry decisions, not just facts, and accepted `decision` nodes do exactly that.
- **Claude Code Projects** (beta, 2026-09-17) is the nearest shipped coordinator:
  - It keeps the goal and sends requests to worker threads: cloud sessions, each on its own branch.
  - Shared Project memory carries decisions forward as plain entries.
  - It is cloud-only for now. The difference here is typed nodes with sources and `accepted_by`.
- **The risk moves to node selection.** If the orchestrator picks the wrong subgraph, the agent never learns what it missed. Two things cover it: the "no silent caps" line, and letting the agent walk beyond the subgraph.
- **The orchestrator's own context degrades as it grows** (Anthropic, context engineering). It should run in replay mode, rebuilt each turn from the DAG and the thread. "Holds the overall context" should mean the context is held in the DAG.

## 4. Code graphs: how they work

**Build:**
1. Parse each file into a syntax tree.
2. Extract entities as nodes: directories, files, classes, functions, methods.
3. Add edges:
   - *contains* (file → class → method)
   - *imports*
   - *calls* (caller → callee)
   - *inherits*
   - *references* (every use of a symbol)

   Security tools add control flow and data flow.
4. Resolve names, the hard part: deciding which `foo` a call to `foo()` means.
5. Store the graph (often SQLite) and re-parse only changed files.

**Two levels of precision:**
- *Syntactic:* tree-sitter plus name matching. It is fast and covers every language, but goes wrong on overloaded names and dynamic dispatch.
- *Precise:* a language server or compiler index (LSP, Sourcegraph's SCIP). It is compiler-accurate and works across repos, but needs per-language setup. Sourcegraph uses precise data where it exists and falls back to search.

**Querying:** the agent gets tools instead of the graph.
- LocAgent: `SearchEntity`, `TraverseGraph`, `RetrieveEntity`.
- Serena (over LSP, as an MCP server): `find_symbol`, `find_referencing_symbols`.
- Codebase-Memory: 14 structural tools over MCP, built on tree-sitter, for 66 languages.

**Selecting context:** Aider's repo map is the clearest example. Tree-sitter finds definitions and references. Files become nodes, with edges where one depends on another. A graph-ranking algorithm picks the most relevant parts, up to a token budget (`--map-tokens`, default 1k).

**How a code graph differs from the knowledge DAG:**

| | Code graph | Knowledge DAG (artifact-dag) |
|---|---|---|
| Made by | A parser, regenerated | People and agents, written |
| Shape | Cyclic (recursion, mutual imports) | Acyclic over `depends_on`, `uses`, `supports`, `refines`, `topics` |
| Encodes | Structure: what calls what | Meaning: what terms mean, what is claimed, what was decided |
| Freshness | As fresh as the last index | As fresh as the last edit |
| Acceptance | None needed | `accepted_by`, supersession |

**How the two join:** a knowledge node cites code entities in `sources:` as path plus symbol at a commit. That gives two things:
1. From a claim, you can jump to the code it is about.
2. When a cited function changes, the claim is flagged for review. This extends the retraction walk (M5b) from beliefs to code.

That is the payoff of having both. Adopt the code graph (§8). Build only the citation and the flag.

## 5. Is walking a graph more efficient than grep?

The published evidence is about code graphs. It says cheaper, not better.

| Study | Result | Caveat |
|---|---|---|
| Codebase-Memory (arXiv, 2026-03) | 10× fewer tokens and 2.1× fewer tool calls than a file-exploring agent | 83% answer quality against the explorer's 92% |
| LocAgent (ACL 2025) | Up to 92.7% file-level localization; about 86% lower cost with a fine-tuned 32B open model | The abstract names no grep baseline |
| RepoGraph (ICLR 2025) | Adding a code graph improved all four SWE-bench methods it was plugged into | — |
| RAG vs GraphRAG (Han et al.) | The graph is better on multi-hop questions; plain retrieval is better on single-hop detail | Graphs built by models |
| Claude Code | Dropped RAG with a vector DB: "agentic search generally works better" | Compared against embeddings, not graphs; secondary *(unverified)* |
| Tool-author benchmarks | A tuned grep beat one graph MCP server by 9 F1 points; agents rarely call graph tools when grep is available | Secondary *(unverified)* |

**For the knowledge DAG, three things matter more than the papers:**
- **Scale.** At today's size the orchestrator can read the whole title index every turn, so choosing nodes needs no search. Efficiency starts to matter only across many DAGs, or at about ten times the size.
  - identikey-dev: 565 node files, 564 with ids (462 definitions, 102 claims), about 255 KB in all; the titles alone are about 18 KB (roughly 4–5k tokens).
  - A second project DAG: 278 nodes (163 claims, 115 definitions).
- **Status, not speed.** Grep finds every place something was said. It can't tell which of three conflicting statements was accepted. A DAG walk returns accepted conclusions and what they rest on, and that is the claim worth testing.
- **Staleness.** Grep reads the files as they are now; a DAG is only as current as its last edit. A stale node handed over as settled is worse than grep. So walk the DAG first, then grep to check the sources its nodes cite. The gate's "sources resolve" check and invalidation (M5b) are what make DAG-first safe.

**The measurement:** take about 20 questions from real threads and run each three ways: grep only, DAG-grounded, and both.
- Tokens and tool calls come from `steps/`.
- Grade answers against accepted nodes.
- Write the hypotheses and thresholds first, as m1-plan §5 did.

When to run it is a question in the [plan](../plans/dag-orchestration.md#questions).

## 6. Resource DAGs

- **Other projects' DAGs:**
  - Ids are already global, and a second project DAG already links to 11 identikey-dev nodes. They show as external nodes unless the viewer joins both collections. The two DAGs define no id in common.
  - A registry is a list of collection paths in config. The walk tool resolves an external id by looking it up there.
  - Grounding from another collection should show where the node came from and who accepted it: a node accepted for one project was accepted for that project's purposes.
- **DAGs built from outside material:**
  - artifact-dag's "claims from a document" procedure (its `dag` skill) already breaks a document into ordered claims with `document:`, `section:` and `order:`.
  - `resource` nodes file outside pages under the definitions they are about.
  - A paper becomes a collection of claims, each citing the paper. Adopt the procedure as it is.
- **No node in either project DAG has `status` or `accepted_by` today** (0 of 842 files, 2026-11-03). Until they do, nothing is "accepted" in the §7 sense. One bridge: count a node on the collection's main branch as accepted by whoever merged its PR, since the `dag` skill sends changes through PRs and git records who merged. Whether to adopt it is a question in the [plan](../plans/dag-orchestration.md#questions).

## 7. Defining "unsupported"

**The unit is an atomic claim:** one checkable statement, the grain the `dag` skill uses for documents and FActScore uses for scoring.

These are not claims:
- questions, plans, proposals and instructions;
- a restatement of the question;
- a statement explicitly framed as a hypothesis ("I suspect X"), which is a candidate `question` node.

Hedging words alone ("probably X") don't make a statement exempt.

**Each claim gets exactly one label:**

| Label | Means | Checked by |
|---|---|---|
| contradicted | Conflicts with an accepted node | Verifier, against the grounding nodes |
| grounded | Cites an accepted node that states it | Script: the id resolves and the node is `accepted`. Verifier: the node entails the claim |
| sourced | Cites a file, commit, turn or URL that states it | Script: the source resolves (the path exists at that commit, the URL loads). Verifier: it entails the claim |
| derived | Follows from cited claims by a step shown in the answer | Premises are grounded or sourced; verifier: the step is valid |
| unsupported | None of the above | — |

**Definition:** *a claim is unsupported when nothing it cites both resolves and states it, and the answer doesn't derive it from claims that do.*

**Rules:**
- **Contradicted comes first.** A claim that conflicts with an accepted node is shown before anything else, whatever it cites. Either the answer is wrong, or the node should be disputed.
- **A citation that fails the check is an error, not a label.** The claim goes back for repair, at most two rounds as with the gate, then fails loudly. A wrong citation is worse than none:
  - In Liu et al. (2023), only 51.5% of sentences from four generative search engines were fully supported by their citations, and 74.5% of citations supported their sentence.
  - Wallat et al. found up to 57% of citations post-rationalized in adversarial tests: the model would have said the same without the source.
- **Citing a `proposed` or `disputed` node doesn't ground a claim.** Label it by that node's own sources, or as unsupported.
- **Common knowledge is unsupported by this definition** ("Python lists are mutable"). The policy decides whether to show the marker; the definition doesn't bend.
- **Claims about code are sourced** when they cite path plus line or symbol at a commit. Grep or a code graph checks them.

**Policy, per thread or per output (`unsupported: label | forbid`):**
- **label:** a marker on each unsupported claim, and a list at the end. The list feeds extraction (§7 of ARCHITECTURE), so the DAG grows where questions hit gaps.
- **forbid:** the output goes back for repair, then fails. FActScore notes that a precision score rises when a model says less. Forbidding has the same effect, so the agent will tend to say less.
- **Recommendation:** `label` for answers, `forbid` for briefs. A coding session shouldn't act on premises nobody checked.

**Who checks:**
- Resolution and status are mechanical: standard library, like the gate.
- Entailment needs a separate verifier call, not the model that wrote the answer, batched over all of an answer's claims.
- The verifier is a model too. Sample its verdicts for review, as the `sample` acceptance policy does.

**Limits:**
- Cross-checking against the DAG tests agreement with what was accepted, not truth.
- The model's training still shapes everything a label can't see: which question it asks, how it frames things, what it leaves out.
- Many nodes were written by models. `accepted_by` and the reading-pace check (§7 of ARCHITECTURE) are what give "grounded" its meaning.

## 8. Adopt before building

| Need | Existing | Coverage | Plan |
|---|---|---|---|
| Orchestrator | Claude Code Projects coordinator | Partial: routing and parallel threads, but memory is plain entries, it runs only in the cloud and it is in beta | The planning harness (M6). Revisit if Projects runs locally and exposes its memory |
| Code graph | Serena (LSP), Codebase-Memory (tree-sitter), LocAgent, Aider's repo map | Full for structure | Adopt one over MCP; grade them at M6 |
| A DAG from a document | artifact-dag's "claims from a document" | Full | Adopt |
| Ids across DAGs | artifact-dag's global ids, external nodes and multi-collection viewer | Most | Add the registry |
| Claim labelling and checking | Methods (FActScore), no tool that fits | None | Build: the script checks plus one verifier call |
| Choosing nodes from a question | — | None | Build. At today's scale, read the title index |

## Sources

- Repo: [ARCHITECTURE.md](../../ARCHITECTURE.md) §6, §7, §8.1; [direction-analysis](../docs/direction-analysis.md); [juggler-analysis](../docs/juggler-analysis.md); [m1-build-spec](../docs/m1-build-spec.md) §5.4.2, §14.1; artifact-dag `SCHEMA.md`, `README.md`, `.claude/skills/dag/SKILL.md`; node counts from the operator's identikey-dev `dag/` folder and a second, private project DAG (2026-11-03)
- Claude Code Projects: [VentureBeat, 2026-09](https://venturebeat.com/orchestration/anthropic-launches-claude-code-projects-an-always-on-conversation-that-remembers-and-delegates-your-long-running-dev-work)
- Juggler: [juggler.studio/features.html](https://juggler.studio/features.html) (read 2026-11-03)
- Anthropic: [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), [effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Cognition: [Don't build multi-agents](https://cognition.com/blog/dont-build-multi-agents)
- Code graphs: [Codebase-Memory, arXiv 2603.27277](https://arxiv.org/abs/2603.27277); [LocAgent, arXiv 2503.09089](https://arxiv.org/abs/2503.09089); [RepoGraph, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/4a4a3c197deac042461c677219efd36c-Abstract-Conference.html); [Aider repo map](https://aider.chat/docs/repomap.html) and [its tree-sitter post](https://aider.chat/2023/10/22/repomap.html); [Serena](https://www.greptile.com/grepository/serena) *(secondary)*; [Sourcegraph precise navigation](https://sourcegraph.com/docs/code-search/code-navigation/precise_code_navigation), [SCIP](https://sourcegraph.com/blog/announcing-scip)
- Graph vs retrieval: [RAG vs GraphRAG, arXiv 2502.11371](https://arxiv.org/abs/2502.11371v3); [Claude Code and RAG](https://www.besthub.dev/articles/why-top-ai-coding-agents-dropped-vector-databases-for-grep-based-retrieval-e16a7a8ee9f5) *(secondary)*; [graph-tool benchmarks](https://dev.to/nike-17/i-benchmarked-code-retrieval-for-ai-coding-agents-on-60-tasks-f9h) *(secondary)*
- Claims and citations: [FActScore, arXiv 2305.14251](https://arxiv.org/abs/2305.14251); [Liu et al. 2023, arXiv 2304.09848](https://arxiv.org/abs/2304.09848); [Wallat et al., arXiv 2412.18004](https://arxiv.org/abs/2412.18004)
