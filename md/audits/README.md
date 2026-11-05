# audits/

None kept yet. The 2026-11-02 adversarial audit's fixes are in PR #24's commits, and what it left open is in `../issues/2026-11-02-audit-leftovers.md`.

---

<!-- pinned from repo-template md/audits/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

A dated reading of the repo, or of one piece of it, against what it claims
to be: the code against its documents, the documents against each other, a
build against its spec. An audit lists what was checked, what held, and what
did not. What did not hold becomes issues (`../issues/`), one per finding,
and the audit links to them.

**Belongs here:** the scope, the method, the commit checked, every item
checked with its result, and the fixes that followed with their commits.

**Does not:** the fix itself (a PR), a finding on its own (`../issues/`), a
recommendation about direction (`../analysis/`).

**Names:** `YYYY-MM-DD-<slug>.md`. A second audit of the same scope is a new
file that says what changed since the first.

**Form:** a header table (scope, commit, date, who or what ran it), then one
section per area with a table of items and results, then "Not checked".
