# Plan: provenance for direct turns

> Status: proposed · 2026-11-05 · from [agent-files-analysis.md](https://github.com/markreveley/investigations/blob/main/in-progress/agent-habitat-architecture/agent-files-analysis.md) in the investigations repo (private; locally `~/dev/repos/investigations/in-progress/agent-habitat-architecture/agent-files-analysis.md`)

**Goal.** Make the record of a direct turn (tier 3, `agent-files-run`) checkable evidence rather than a convention. Afterwards, for any agent turn, the record should show four things:

- what the model was given, rebuilt from git and compared with `steps/`;
- that the step records were not changed after the turn;
- that the human turn and the model's turn are attributed to different parties in git;
- the provider's own identifier for the call.

**Why.** The investigations repo read Replit's white paper Agent Habitat Architecture against agent-files' direct tier ([the analysis](https://github.com/markreveley/investigations/blob/main/in-progress/agent-habitat-architecture/agent-files-analysis.md)). Its findings are summarised here; the analysis has the evidence and the paper's passage ids.

- **The strength.** In replay mode the file is the context (ARCHITECTURE §6), so a direct turn can record what the model saw, not only what it said. The paper's provenance is about authority: which workload acted, under which trigger. Entire, git-ai and DeltaDB record conversations. None records the exact model input.
- **The gaps:**
  - Both the `send` and `reply` commits are authored `agent-files` (`lib/agent_files/git.py`), so git credits the operator's words to the machine.
  - The turn commit holds `thread.md`, `steps/` and `out/`, not the agent declaration or the config that shape the request. So the request can't be rebuilt from git alone.
  - `request.json` is written after the `send` commit, so the journal entry before the call isn't committed until the reply.
  - No provider message id or request id is recorded.
  - Every step record can be rewritten by any process running as the operator.
  - Every call uses the operator's one API key.

None of this has been run. Experiment G in the investigation (`reproduction.md`) is the test of the rebuild claim, and step 5 below makes it a command.

**Adopt before building.** Capture tools (Entire, git-ai, SpecStory) record harness sessions, not the requests this runner assembles, so they don't cover it. Git already provides what D2–D3 need: trailers, author and committer identities, and SSH commit signing. For D8, existing LLM logging proxies (LiteLLM's proxy, mitmproxy) are graded before anything is built.

## Decisions

- **D1. Record the provider's identifiers.** `steps/tNNNN.response.json` gains `provider_message_id` and `provider_request_id` wherever the backend returns them: the Anthropic and OpenAI-compatible backends. The accessor for the request id on a streamed response is confirmed against the SDK at build time. A missing id is recorded as `null` and never fails a turn.
- **D2. Commit the request with the send, and hash both records.**
  - Assembly (build spec §5.2 step 4) moves before the `send` commit (step 2), and `request.json` is committed with it. The journal entry for the call is then in git before the call is made.
  - The `send` commit gains the trailer `Agent-Files-Request-Sha256`. The `reply` commit gains `Agent-Files-Response-Sha256`, and `Agent-Files-Error-Sha256` when a turn fails.
  - Hashes are of the files' bytes as written.
  - A turn that fails before assembly (spend cap, unknown backend) has no request and no request trailer. That is the current behaviour, made explicit.
- **D3. Separate the two parties in git.**
  - The `send` commit is authored by the operator and committed by `agent-files`.
  - The `reply` and `recover` commits stay `agent-files` for both author and committer.
  - The operator identity is the data root's own `user.name` and `user.email`. If those are unset, it is `operator <operator@localhost>`.
  - This is a claim, not a proof: the runner can't know who saved the file. D3 makes the existing convention visible in `git log`; signing (Q2, Q4) is what would make it evidence.
- **D4. Every input to assembly is recoverable at the `send` commit.**
  - The `send` commit stages `agents/<agent>.md` for the thread's agent.
  - It records the SHA-256 of the `config.toml` in use as `Agent-Files-Config-Sha256`.
  - Whether `config.toml` itself is committed is Q1.
  - Grounding is not built (M5). When it is, the accepted nodes injected into a request are committed or hashed the same way.
- **D5. `agent-files-run verify <thread> [tN]`.** For each agent turn, or just one:
  - read the thread, agent declaration and config at the turn's `send` commit (with `git show`, never a checkout of the data root);
  - rebuild the body with the same code as `check`;
  - compare it with the `request` field of `request.json`;
  - compare both step records with their trailer hashes.

  It prints one JSON line per turn (`turn`, `request: match | differ | missing`, `hashes: ok | differ | missing`, `differ_fields`) and exits non-zero on any difference. Turns made before D2 and D4 report `missing`, not `differ`. This is Experiment G as a command, following principle 3.
- **D6. Per-agent API key.** An agent declaration may name `api_key_env`, overriding the backend's. Provider usage records then attribute calls per agent. The variable's name goes into `response.json` (`api_key_env`), never its value.
- **D7. The data root's remote refuses rewrites.** This is operator configuration, not code: branch protection on the data root's private remote, with force-push and deletion blocked. It is the cheapest step toward a store a local agent can't rewrite.
- **D8. No broker yet.** A local proxy running as another Unix user would hold the API key, log every request and response where the runner can't write, and confirm `request.json` against what was sent. It is the strongest witness, and it has the most upkeep. Decided after D1–D5 are in use (Q3). It applies only to API backends: `claude -p` opens its own connection.
- **D9. Tools are pinned when the planning harness gets them.** When M6 adds MCP tools, each server is pinned by hash in the agent declaration, and each piece of assembled context carries a source label in `request.json`: a person-accepted node, a rule-accepted node, or tool output. Recorded here so the M6 design picks it up ([dag-orchestration plan](../2026-11-03-dag-orchestration/dag-orchestration.md)). Not built in this plan.

Once built, D2–D5 change ARCHITECTURE §4.1 (what `steps/` holds), §9.6 (trailers), and build spec §5.2 (step order). Those sections are updated in the same change.

## Steps

1. D1: provider ids in `response.json`, with backend tests using the fakes in `tests/fakes/`.
2. D2: move assembly before the `send` commit and add the hash trailers. Update build spec §5.2 and the runner tests (`tests/test_run.py`, `tests/test_git.py`), plus smoke S1–S5.
3. D3: operator authorship on `send` commits, with a test that reads `%an` and `%cn` from both commits of a turn.
4. D4: stage the agent declaration and add the config-hash trailer. Waits on Q1 for whether to commit `config.toml`.
5. D5: `verify`, with tests covering a matching thread, an edited `request.json`, a changed agent file, and a pre-D2 thread.
6. D6: `api_key_env` in agent declarations.
7. D7: the operator sets branch protection on the data root's remote.
8. Run Experiment G against a temporary root on the `anthropic` backend (about three calls; operator approval), and record the result in the investigation.
9. Q2–Q4, then D8 if chosen.

## Questions

- **Q1.** Should `config.toml` be committed with each `send`, or only hashed? It holds backend settings and prices, not keys, but it is the operator's file (AGENTS.md: don't edit it).
- **Q2.** Should the runner sign its commits with its own SSH key? Creating the key and setting `gpg.format ssh` in the data root's config changes the local environment, so it needs the operator's approval.
- **Q3.** Is the broker of D8 worth building for one operator, or is D7 plus provider ids enough until there is a second user?
- **Q4.** Should human `send` turns be signed by the operator? That would mean `agents.nvim` committing the send under the operator's key instead of the runner, which changes who commits a send.
