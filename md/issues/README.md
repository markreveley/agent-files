# issues/

- [`2026-11-02-audit-leftovers.md`](2026-11-02-audit-leftovers.md): what the 2026-11-02 adversarial audit found and was not fixed. No tracker entries.

---

<!-- pinned from repo-template md/issues/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

Dated findings against something: a bug, a place where a document disagrees
with the code, a review's defects, a security advisory draft. An issue file
is the full record; a tracker entry (GitHub Issues) is the pointer to it,
and the file says which tracker entry it was filed as.

**Belongs here:** the finding, where it was seen (path and line at a named
commit), what was expected, the evidence, and what was done or proposed.

**Does not:** the fix's design (a plan), what was learned in general
(`docs/`), a finding about an outside project that is not reported anywhere
(file it or drop it).

**Names:** `YYYY-MM-DD-<slug>.md`. Where several findings share a subject
and a date, one file per subject with a numbered list, and a README in this
folder indexing them with their tracker links.

**Form:** open with a table: what was checked, at which commit, when it was
rechecked, where it was reported. Then the items, each with its location,
expected, observed, and status.
