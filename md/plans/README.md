# plans/

- [`2026-10-31-m1/`](2026-10-31-m1/m1.md): M1, the first build. Done.
- [`2026-11-03-dag-orchestration/`](2026-11-03-dag-orchestration/dag-orchestration.md): DAG-grounded orchestration, part of M6. Proposed.
- [`2026-11-03-nvim-addressing/`](2026-11-03-nvim-addressing/nvim-addressing.md): Neovim instances addressable by name. Proposed; waits on the doorbell revisit.
- [`2026-11-04-open-questions/`](2026-11-04-open-questions/open-questions.md): every open design and build question not owned by one plan (ARCHITECTURE §13, build spec §14, juggler §7). Proposed.
- [`2026-11-04-inline-ask/`](2026-11-04-inline-ask/inline-ask.md): questions written inline in any Markdown file, answered on save by `agents.nvim`. Proposed.
- [`2026-11-04-nvim-sidebar/`](2026-11-04-nvim-sidebar/nvim-sidebar.md): the agent sidebar in `agents.nvim`. Proposed.
- [`2026-11-05-provenance/`](2026-11-05-provenance/provenance.md): provenance for direct turns: provider ids, hashed and committed step records, operator authorship, `verify`. Proposed; from the investigations repo's Agent Habitat analysis.
- [`2026-11-05-morla/`](2026-11-05-morla/morla.md): morla-neovim as the plain-English command lane for `agents.nvim`; intent decides whether a send is human (ARCHITECTURE §5.1). Accepted; milestone M1.6, after the sidebar.

---

<!-- pinned from repo-template md/plans/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

What will be done, in what order, and what it waits on. A plan is the
bridge from an analysis's recommendations to the steps in `next-agents.md`.

**Belongs here:** a plan of work with its steps in order, the decisions it
rests on, and the questions it waits on; the reference material a plan
needs beside it.

**Does not:** findings (those are the analysis the plan links to), finished
work (delete the steps; git history holds them), the current next step
(that is `next-agents.md`, which links back to the plan it comes from).

**Names:** `YYYY-MM-DD-<slug>/<slug>.md`, the date being the day the plan
was written. The folder holds anything the plan carries with it.

**Form:** the first line after the title is a status line, updated when the
plan changes:

```
> Status: proposed · YYYY-MM-DD · from [<analysis>](../../analysis/...)
```

Status words: `proposed`, `accepted`, `in progress`, `done`, `dropped`.
Decisions are numbered (`D1`) so steps and other documents cite them;
outside the plan, cite them with its slug (`<plan-slug> D1`). A decision
adopted as design moves to `governance/ARCHITECTURE.md` under its next
number, and the plan links to it. A
question in a plan moves to `next-operator.md` when the step that waits on
it comes up.
