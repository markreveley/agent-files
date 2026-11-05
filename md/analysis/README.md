# analysis/

- [`2026-10-31-juggler/`](2026-10-31-juggler/juggler.md): Juggler as a reference.
- [`2026-11-01-multi-subscription/`](2026-11-01-multi-subscription/multi-subscription.md): CLIProxyAPI and T3 Code.
- [`2026-11-03-orchestrator/`](2026-11-03-orchestrator/orchestrator.md): DAG-grounded orchestration; its plan is `plans/2026-11-03-dag-orchestration/`.

The decision records that grew out of analyses (direction, host, Rex) are in `../docs/`.

---

<!-- pinned from repo-template md/analysis/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

Dated findings and recommendations: what was looked at, what was found, what
to do about it. An analysis is a record of a reading at a date; it is not
updated afterwards except to fix an error, and a later reading is a new
analysis that links to it.

**Belongs here:** a comparison of options or tools, a reading of a source
against the repo's own position, the result of an audit or experiment, a
research report.

**Does not:** open questions (they go in `next-operator.md` or a plan),
steps to take (a plan, linked from the analysis's recommendations), a rule
the analysis argues for (once adopted, `governance/POLICY.md`, citing the
analysis).

**Names:** `YYYY-MM-DD-<slug>/<slug>.md`. The folder holds the analysis's
material: data, scripts, excerpts.

**Form:** a header block before the first section, then numbered sections,
the first of them the short answer:

```
# <title>

**Date:** YYYY-MM-DD

**Question.** <what was asked, and why>

**Sources read.** <what was read, by path or link; what was not read and why>

**Method caveat.** <what the reading could not check: fetched through a summariser, figures as of a date, claims taken from the source itself>

---

## 1. The short answer
```
