# governance/

- [`ARCHITECTURE.md`](ARCHITECTURE.md): the design of agent-files. Its §13 numbers the design questions (the open ones are in `../plans/2026-11-04-open-questions/`), and its §14 lists the milestones.

agent-files has no POLICY, SCHEMA, PROCEDURE or DOCTRINE yet. The thread format is in ARCHITECTURE §4 and the build spec.

---

<!-- pinned from repo-template md/governance/README.md @ 868468a; refresh from the template, do not edit by hand -->
## About this folder (repo-template `868468a`)

The documents that govern the repo. Five fixed names, each present only when
it has content; a repo deletes the stubs it has no use for and lists the
rest in its README.

| file | says | changed by |
|---|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | how the thing is built: the parts, the flow between them, the boundaries, and the decisions with their reasons | a design decision |
| [`POLICY.md`](POLICY.md) | the rules in force: each one numbered, with why it holds and what checks it | a ruling by the operator |
| [`SCHEMA.md`](SCHEMA.md) | the formats and contracts of the data the repo holds or emits | a breaking change, announced to whatever reads the data |
| [`PROCEDURE.md`](PROCEDURE.md) | the step-by-step methods the repo runs, each numbered, saying which steps a person does | a method being tried and adopted |
| [`DOCTRINE.md`](DOCTRINE.md) | what the repo holds to be true and what it values: the principles the policies derive from and the architecture serves | an argument, recorded in an analysis |

How they relate: doctrine says why, policy says what is required, procedure
says how it is done, schema says what the data looks like, architecture
says how the parts fit. A rule nobody checks and nothing enforces is
doctrine, not policy. A policy cites the doctrine it serves; a procedure
cites the policies it satisfies; an architecture decision cites both.

**Does not belong here:** a guide (`docs/`), a plan, an analysis, a
document about one piece of the repo only (`docs/`).
