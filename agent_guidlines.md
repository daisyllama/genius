# Development Best Practices

> This document applies to every project. Read it before writing any code or making any architectural decisions.

---

## 1. General Principles

- **Fail loudly and early.** Validate inputs, assumptions, and dependencies before doing any real work.
- **Idempotency by default.** Re-running anything should produce the same result without side effects.
- **Prefer simple and explicit over clever and implicit.** Code is read more than it is written.
- **Document decisions inline.** When a non-obvious choice is made, leave a comment explaining why.
- **Never invent requirements.** If something is ambiguous and consequential, stop and ask.

---

## 2. Workflow: Review → Plan → Implement (RPI)

**Always follow RPI. Never jump straight to implementation.**

### Review
Before touching any code or file:
- Read all relevant existing files, notebooks, and artifacts.
- Identify what already exists and what state it is in.
- Note inconsistencies, gaps, or risks.

### Plan
Before writing a single line of code:
- Write or update `plan.md` with the goal, phases, files to touch, and success criteria.
- Get explicit confirmation from the user if the plan involves significant design decisions.
- Break work into phases small enough that each can be completed and validated independently.

### Implement
- Execute one phase at a time.
- Update `progress.md` at the end of every phase with: what was completed, current state, and the exact next step.
- Do not move to the next phase without confirming the current one is working.

---

## 3. Before Starting Any Project

Before writing code, clarify the following with the user:

- What is the expected input and output?
- What is the expected scale / data volume?
- Is this a one-off script or a repeatable pipeline / service?
- Are there any hard constraints (cost, runtime, platform)?
- For data projects: **always ask whether to use incremental load or full refresh** — never assume.

---

## 4. Context Management

**Long tasks span multiple sessions. Manage context explicitly.**

- Maintain `plan.md` (~200 lines max): goal, phases, files, success criteria.
- Maintain `progress.md` (~100 lines max): what is done, current state, exact next step.
- At the end of every session or phase, update both files before stopping.
- At the start of every session, read both files before doing anything else.
- If context is getting long mid-session, compact completed work into `progress.md` and continue.
- A new session loading only `plan.md` + `progress.md` must have enough context to continue without re-discovery.

---

## 5. Checkpointing & Resume

**Any process that may run for a long time must be resumable.**

- Break long-running work into discrete batches or steps.
- Track progress in a persistent state store (file, table, or database — choose what fits the project).
- On restart, the process must detect where it left off and continue from there — not from the beginning.
- Never design a long-running job as all-or-nothing.
- Batch size should be configurable and documented.

---

## 6. Error Handling

- Wrap external calls (APIs, file I/O, database) in retry logic with exponential backoff.
- Distinguish between **transient failures** (retry) and **permanent failures** (log and skip or halt).
- Always log: what failed, why, and what the state was at the time of failure.
- Never silently swallow exceptions.

---

## 7. Testing

- Write at least one sanity check or assertion for every major output.
- For data outputs: validate row counts, nulls on required fields, and schema shape.
- For API / service outputs: validate response structure before consuming.
- Test with a small sample before running at full scale.

---

## 8. Code Structure

- One clear entry point per script or notebook.
- Separate concerns: data access, transformation logic, and output writing should not be tangled together.
- Avoid hardcoding paths, credentials, or environment-specific values — use config or environment variables.
- Keep notebooks clean: remove scratch cells before considering anything "done."

---

## 9. Security

- **Never hardcode credentials, API keys, or secrets** in any file that could be committed.
- Use `.env` files for local secrets. Confirm `.env` is in `.gitignore` before any credential is written.
- If a secret must be referenced in code, use `os.environ.get(...)` and fail loudly if it is missing.
- If you encounter a credential in an existing file, flag it to the user immediately — do not proceed.

---

## 10. Data & Storage

- Always know the **write mode** (overwrite, append, upsert) before writing — never leave it as a default.
- Staging before production: write to a staging location first, validate, then promote.
- Include an ingestion/processing timestamp on any dataset that is created or modified.
- For the choice of incremental vs full refresh: **always ask the user** — do not decide unilaterally.

---

## 11. When to Stop and Ask vs. Make a Call

**Make a call** when:
- The decision is low-stakes and easily reversible.
- The right choice is obvious from context or best practice.
- Asking would interrupt flow without adding value.

**Stop and ask** when:
- The decision affects data (write modes, schema changes, deletions).
- The decision has cost or performance implications.
- Two reasonable approaches lead to meaningfully different outcomes.
- Something in the existing code or data contradicts the plan.

When in doubt: make your best call, state it explicitly, and flag it for confirmation.

---

## 12. Cost & Performance

- Estimate scale before running. For large inputs, test on a 1% sample first.
- Avoid full scans of large datasets when a filtered read is possible.
- For expensive external calls (LLM APIs, cloud services): batch requests, cache results where safe, and checkpoint progress.
- Flag any approach that could have runaway cost implications before proceeding.

---

## 13. Delivery

- Every deliverable must include a brief summary of: what was built, what decisions were made, and what assumptions were made.
- If the agent made a significant design choice, it must be surfaced to the user for confirmation.
- Leave the project in a state where the user can re-run, extend, or hand it off without asking the agent for context.
- Update `plan.md` and `progress.md` as the final act of every session.
