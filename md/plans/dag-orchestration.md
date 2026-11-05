# Plan: DAG-grounded orchestration

> Status: proposed · 2026-11-04 · from [orchestrator-analysis](../analysis/orchestrator-analysis.md); part of M6 ([ARCHITECTURE §14](../../ARCHITECTURE.md#14-milestones))

**Goal.** The planning harness reads a question, picks the DAG nodes it bears on, and briefs an agent with that subgraph. The agent walks DAGs first, and every claim in its answer carries a label. What was adopted and why is in the analysis. This file holds the order of work and the questions it waits on.

## Steps

Each step names the question it waits on. When a step comes up, its question moves to [next-operator.md](../../next-operator.md) as blocking.

1. **Measure graph against grep** (analysis §5). Run about 20 real questions three ways: grep only, DAG-grounded, and both. Record tokens and tool calls from `steps/`, and grade answers against accepted nodes. Decide in advance what result would change the plan. *Waits on Q3.*
2. **Acceptance for existing DAGs** (analysis §6). No node in identikey-dev or the second project DAG has `status` or `accepted_by` (0 of 842 files, 2026-11-03), so nothing counts as `grounded` yet. *Waits on Q2.*
3. **Registry and walk tool.** A config list of collection paths. A walk tool (neighbours and dependencies of an id, resolved across collections) built on artifact-dag's parser and served over MCP (`--mcp-config --strict-mcp-config`).
4. **Choosing nodes from a question.** At today's scale, read the whole title index, about 4–5k tokens for identikey-dev. Briefs keep the "no silent caps" line (ARCHITECTURE §6).
5. **Claim labels** (analysis §7):
   - script checks: ids resolve, nodes are `accepted`, sources resolve;
   - one verifier call per answer, a different model from the writer, with its verdicts sampled for review;
   - the per-output policy `unsupported: label | forbid`.

   *Waits on Q1.*
6. **Grounding across projects.** Show the source collection and `accepted_by` for every node from another DAG. *Waits on Q4.*
7. **Code graph** (analysis §4):
   - grade Serena and Codebase-Memory, and adopt one over MCP;
   - add path-plus-symbol-at-a-commit citations to `sources:`;
   - flag a claim when a symbol it cites changes.

   *Waits on Q5.*
8. **`claude -p` checks** (analysis §2), on the installed Claude Code before step 3 relies on them:
   - is `CLAUDE.md` loaded when the run happens inside a repo?
   - does `--mcp-config` work with a real server?
   - for coding briefs, should we replace Claude Code's system prompt or append to it?

## Questions

Answer when convenient; none blocks M1.

1. **`unsupported` policy:** `label` for answers and `forbid` for briefs (recommended), or one policy everywhere? *(step 5)*
2. **Does a node merged to its collection's main branch count as accepted by whoever merged it?** The `dag` skill sends changes through PRs, and git records the merger. *(step 2)*
3. **When to measure graph against grep:** during the record work, or in the adopt-first check before M6? *(step 1)*
4. **Can a node accepted in another project ground an answer here,** or only with a flag? *(step 6)*
5. **Which code graph to grade first:** Serena (precise, needs language servers) or Codebase-Memory (syntactic, every language)? *(step 7)*
