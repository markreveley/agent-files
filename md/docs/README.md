# docs/

- [`m1-build-spec.md`](m1-build-spec.md): the M1 build; wins over the M1 plan.
- [`direction-analysis.md`](direction-analysis.md): decision record on what agent-files is for, the planning harness, and what to adopt.
- [`host-analysis.md`](host-analysis.md): decision record grading existing hosts against M2; the model for "adopt before building".
- [`rex-host.md`](rex-host.md): decision record on Rex as the host.
- [`related-repos.md`](related-repos.md): decision record on the repos agent-files relates to.
- [`role-of-neovim.md`](role-of-neovim.md), [`view-layer.md`](view-layer.md): the Neovim client and the read-only view.
- [`operator-neovim.md`](operator-neovim.md): the operator's own Neovim and Rex layout; not part of agent-files, but its §3 is how to use `agents.term`.
- `examples/view-fixture/`: the shared parser and plugin test fixture, read by the tests.

---

<!-- pinned from repo-template md/docs/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

How to use and work on what the repo holds: user guides, setup, reference
for a tool or format the repo ships, decision records that a reader needs
in order to work here.

**Belongs here:** a guide (`USAGE.md`), a setup walkthrough, the reference
for a config file, a record of a decision and its reasons, notes on an
outside system the repo depends on.

**Does not:** a rule the repo enforces (`governance/POLICY.md`), a data format
(`governance/SCHEMA.md`), findings from looking into something (`analysis/`),
steps still to be done (`plans/`).

**Names:** `<topic>.md`, lower case, hyphens. A topic that needs more than
one file gets a folder with a README.

**Form:** no fixed header. Open with one paragraph saying what the document
is for and who reads it. Keep a decision record's reasons; delete steps that
are done.
