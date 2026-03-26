# Development Best Practices

> This document applies to every project. Read it before writing any code or making any architectural decisions.

---

## 1. General Principles

- **Fail loudly and early.** Validate inputs, assumptions, and dependencies before doing any real work.
- **Idempotency by default.** Re-running anything should produce the same result without side effects.
- **Prefer simple and explicit over clever and implicit.** Code is read more than it is written.
- **Document decisions inline.** When a non-obvious choice is made, leave a comment explaining why.

---

## 2. Before Starting Any Project

Before writing code, the agent must clarify the following with the user:

- What is the expected input and output?
- What is the expected scale / data volume?
- Is this a one-off script or a repeatable pipeline / service?
- Are there any hard constraints (cost, runtime, platform)?
- For data projects: **always ask whether to use incremental load or full refresh** — never assume.

---

## 3. Checkpointing & Resume

**Any process that may run for a long time must be resumable.**

- Break long-running work into discrete batches or steps.
- Track progress in a persistent state store (file, table, or database — choose what fits the project).
- On restart, the process must detect where it left off and continue from there — not from the beginning.
- Never design a long-running job as all-or-nothing.
- Batch size should be configurable and documented.

---

## 4. Error Handling

- Wrap external calls (APIs, file I/O, database) in retry logic with exponential backoff.
- Distinguish between **transient failures** (retry) and **permanent failures** (log and skip or halt).
- Always log: what failed, why, and what the state was at the time of failure.
- Never silently swallow exceptions.

---

## 5. Testing

- Write at least one sanity check or assertion for every major output.
- For data outputs: validate row counts, nulls on required fields, and schema shape.
- For API / service outputs: validate response structure before consuming.
- Test with a small sample before running at full scale.

---

## 6. Code Structure

- One clear entry point per script or notebook.
- Separate concerns: data access, transformation logic, and output writing should not be tangled together.
- Avoid hardcoding paths, credentials, or environment-specific values — use config or environment variables.
- Keep notebooks clean: remove scratch cells before considering anything "done."

---

## 7. Data & Storage

- Always know the **write mode** (overwrite, append, upsert) before writing — never leave it as a default.
- Staging before production: write to a staging location first, validate, then promote.
- Include an ingestion/processing timestamp on any dataset that is created or modified.
- For the choice of incremental vs full refresh: **always ask the user** — do not decide unilaterally.

---

## 8. Cost & Performance

- Estimate scale before running. For large inputs, test on a 1% sample first.
- Avoid full scans of large datasets when a filtered read is possible.
- For expensive external calls (LLM APIs, cloud services): batch requests, cache results where safe, and checkpoint progress.
- Flag any approach that could have runaway cost implications before proceeding.

---

## 9. Delivery

- Every deliverable must include a brief summary of: what was built, what decisions were made, and what assumptions were made.
- If the agent made a significant design choice, it must be surfaced to the user for confirmation.
- Leave the project in a state where the user can re-run, extend, or hand it off without asking the agent for context.
