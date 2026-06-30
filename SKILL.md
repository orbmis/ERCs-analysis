---
name: erc-dataset
description: Build an analysis-ready CSV dataset from locally-cloned Ethereum ERC markdown files (ERCs/ERCS/erc-*.md), extracting frontmatter metadata, semantic topics, and dependency-graph fields. Use this skill whenever the user wants to catalog, extract, structure, or analyze Ethereum ERCs (or EIPs) into a dataset or CSV, build an ERC dependency graph, or run repo-wide / time-series analysis over the ERCs repo — even if they don't say the word "skill" or "dataset". Do NOT use it to analyze or summarize a single ERC's contents in prose.
---

# ERC dataset builder

Build a validated, analysis-ready CSV describing every Ethereum ERC in the local
`ERCs/ERCS/` folder. The ERCs repo has already been cloned into `ERCs`.

## How to run this (model routing & context discipline)

These choices keep cost bounded — follow them unless told otherwise.

- **Run the main/orchestrator loop on Sonnet, not Opus.** This task is coordination —
  dispatch, merge, validate — not deep reasoning. Sonnet pulls far less from usage limits
  for equivalent work here.
- **The orchestrator must NOT read ERC markdown *bodies* into its own context.** Only the
  Pass A/A2/D scripts and the Pass B subagents touch file contents. The orchestrator works
  from script outputs and merged JSON/CSV. Do not `cat` ERC files into the main thread "to
  check" — that is the single biggest way this job balloons.
- **Subagents run on Haiku** (see Pass B). They return only compact JSON to the main thread.
- The deterministic passes (A, A2, D) are plain scripts and cost almost nothing — do as much
  as possible there and reserve the LLM for Pass B only.

## Scope (read-only source)
- Process only files matching `ERCs/ERCS/erc-<N>.md` where `<N>` is an integer. Ignore everything else.
- Treat everything under `ERCs/` as read-only: never modify, move, or delete a source file.
- First, count the matching files and print the count. This is the expected final row count.

## Two-pass extraction — deterministic first, LLM only where needed

### Pass A — structured fields (no LLM, one script)
Every ERC begins with YAML frontmatter. Parse it directly for all files into a base
table keyed by ERC number:
- `erc` (int), `title`, `description`, `author`, `discussions-to`, `status`, `type`,
  `category`, `created` (ISO date), `requires` (list of EIP/ERC numbers = the **formal dependencies**).
- `last-call-deadline` and `withdrawal-reason` — present only on Last Call / Withdrawn ERCs; capture when present.
- `author` may be multi-author / multi-line; `requires` is comma-separated; `created` is `YYYY-MM-DD`.
- **Author normalization:** also split `author` into a list of discrete identities
  (name + GitHub handle and/or email where given) in an `authors_normalized` field, for
  later co-authorship / prolific-author analysis. Keep the raw `author` string too.
- Log any file with missing or malformed frontmatter to the run report and continue — do not fail the run.

### Pass A2 — body-structure flags (no LLM, cheap regex over the same files)
While the files are open, record structural signals:
- `has_security_considerations` (bool), `has_test_cases` (bool), `has_reference_impl` (bool).
- `spec_word_count` (int) and `section_count` (int) as complexity proxies.
EIP-1 requires a Security Considerations section for Final, so the absence-vs-status
combination is a genuine maturity signal worth having explicitly.

### Pass B — semantic fields (Haiku subagents, batched)
Only for fields that need judgment, dispatch subagents:
- **Batch ~15 ERCs per subagent** (do NOT spawn one subagent per ERC). Lower the batch if the markdown is long.
- **Cap concurrency at ~6 subagents.**
- Each subagent receives ONLY: this instruction block + the raw markdown of its assigned ERCs. No other context.

Each subagent returns strict JSON keyed by ERC number. For each ERC produce:

**`topic`** — exactly one value from the controlled vocabulary below. Read the gloss, not just the label; classify on the ERC's *primary purpose*, not an incidental mention.

| value | covers | typical signals / examples |
|---|---|---|
| `account-abstraction` | Smart-account mechanics: account abstraction, bundlers, paymasters, EOA delegation, session keys, batched/sponsored execution | 4337, 7702, 6900, 7579; "UserOperation", "paymaster", "modular account" |
| `agentic-workflows` | Autonomous-agent coordination, agent identity/authorization, intents, agent-to-agent payments, permissioned delegation to agents | 8004 and the agent-layer stack; "agent", "intent", "delegated action", "autonomous" |
| `reputation-identity` | Attestations, credentials, DIDs, sybil resistance, naming, on-chain reputation/identity | ENS-style naming, attestation registries, "verifiable credential", "soulbound" identity use |
| `nft` | Non-fungible and semi-fungible token standards and their extensions (royalties, rentals, metadata, bound tokens) | 721, 1155, 2981, 4907, 6551; "non-fungible", "tokenURI", "token-bound account" |
| `rwa` | Real-world-asset tokenization, regulated/compliant transfer, security tokens, asset-backed instruments | "security token", "compliance", "transfer restriction", "real-world asset" |
| `defi` | DeFi protocol primitives and integrations: AMMs, lending, vaults, oracles, yield, liquidations | 4626 vaults, oracle interfaces, "liquidity", "collateral", "yield", "swap" |
| `tokens-fungible` | Core fungible-token standards and their extensions (approvals, permits, callbacks) NOT specific to a DeFi protocol | 20, 777, 2612 permit, 1363; "fungible", "allowance", "transferFrom" |
| `governance` | On-chain governance, voting, DAOs, proposals, delegation of voting power, treasury control | "proposal", "quorum", "vote", "governor", "DAO" |
| `security-permissions` | Access control, permission/authorization frameworks, signing/verification schemes, security primitives NOT tied to a single token type | 1271 signature validation, permission grammars (7710/7715), "authorization", "access control" |
| `infrastructure-meta` | Process/meta ERCs, registries, addressing, encoding, cross-chain/L2 plumbing, and low-level interface conventions with no single domain above | EIP-1-style process, "registry", "namespace", "cross-chain", "calldata encoding" |
| `other` | Genuinely does not fit any value above | — |

Classification rules (apply in order):
1. **Primary purpose wins.** An ERC that merely *uses* another domain isn't classified there. A vault that issues ERC-20 shares is `defi`, not `tokens-fungible`.
2. **More specific beats more general.** Prefer `nft`/`tokens-fungible`/`defi` over `infrastructure-meta` when a clear domain applies; reserve `infrastructure-meta` for genuinely cross-cutting plumbing.
3. **Agent vs. AA boundary.** Smart-account *capability* (how an account executes) → `account-abstraction`. *Autonomous-agent coordination/authorization* (what an agent is allowed to do, agent identity, intents) → `agentic-workflows`.
4. **Permissions vs. governance.** Generic authorization/permission frameworks → `security-permissions`; voting/proposal/treasury control specifically → `governance`.
5. Only use `other` after rejecting every defined value. Use it sparingly.

Also produce, per ERC:
- **`topic_secondary`** — a second value from the same vocabulary if the ERC genuinely straddles two domains, else empty. (Keeps `topic` single-valued for clean grouping while preserving the straddle signal you'd otherwise lose.)
- **`topic_confidence`** — `high` | `medium` | `low`; use `low`/`medium` for borderline calls so they're auditable later.
- **`topic_other`** — freeform label, only when `topic == other`.
- **`referenced_ercs`** — ERC/EIP numbers mentioned in the body **beyond** the formal `requires` list.
- **`one_line_summary`** — ≤25 words, plain description of what the ERC does.
- **`notes`** — anything analytically useful that is NOT already deterministic: novel mechanism, supersession/relationship to another ERC, security caveat, notable design trade-off. Leave empty rather than padding with generic restatement. (Status-based facts like Withdrawn/Stagnant come from frontmatter in Pass A — don't duplicate them here.)

Output contract: strict JSON, keys are ERC numbers (ints), every field present (empty string where N/A), no prose outside the JSON, no markdown fences.

The fixed `topic` enum and the classification rules are mandatory so categories stay consistent across subagents and remain groupable.

> Model note: Haiku is well-suited to the closed-set fields above (`topic`, numbers, summary) given the defined vocabulary. `notes` is the one open-ended field — if a spot-check of ~20 rows shows it reading thin, either drop it from this pass or re-run only `notes` (and any `topic_confidence: low` rows) through a small Sonnet pass, keeping the mechanical fields on Haiku.

### Pass D — dependency-graph fields (no LLM, post-processing on `requires`)
Once Pass A's `requires` edges exist, build the dependency DAG and derive per-ERC:
- `required_by` — the reverse edges (which ERCs depend on this one); the influence / load-bearing signal.
- `in_degree`, `out_degree`, and `pagerank` (or betweenness) over the DAG to surface foundational vs. leaf standards. If you'd rather avoid a graph dependency (`networkx`), `in_degree`/`out_degree` alone already give most of the foundational-vs-leaf signal — drop the centrality column in that case.
- `dependency_depth` — longest upstream `requires` chain; proxy for how deep in the stack a standard sits.
Build the graph from `requires` only (the formal edges); keep `referenced_ercs` separate as the looser, body-mention signal.

## Merge & output
- Join Pass A + A2 + B + D on ERC number into `erc_dataset.csv`.
- Columns, in order:
  `erc, title, description, topic, topic_secondary, topic_confidence, topic_other, status, type, category, created, last_call_deadline, withdrawal_reason, author, authors_normalized, requires, required_by, referenced_ercs, in_degree, out_degree, pagerank, dependency_depth, has_security_considerations, has_test_cases, has_reference_impl, spec_word_count, section_count, discussions_to, one_line_summary, notes`
- `created` as ISO `YYYY-MM-DD` (for time-series). List fields (`requires`, `required_by`, `referenced_ercs`, `authors_normalized`) as semicolon-separated.

## Bounded execution (cost & safety)
- **Resumable / idempotent:** write incrementally; on rerun, skip ERCs already present in the output. Never restart from scratch if partial output exists.
- **Cost guard:** before Pass B, compute `subagent_count = ceil(matching_files / batch_size)`. If it exceeds 60, STOP and report the number instead of proceeding. (If the folder is larger than expected, raise `batch_size` rather than the ceiling.)
- **Confinement:** all writes go to the working directory only.

## Definition of done — stop when ALL are true
1. `erc_dataset.csv` exists with one row per matching file (row count == the count printed in Scope).
2. Required columns (`erc`, `title`, `status`, `created`) are non-null for every row, OR each exception is listed in the run report.
3. Every `created` value parses as an ISO date.
4. `_run_report.md` summarizes: files processed, frontmatter failures, subagent count, the `topic` distribution, and the ERCs flagged for review — those with `topic = other`, `topic_confidence = low`, or a non-empty `topic_secondary` — so borderline classifications are auditable in one place.

Report these results and stop. Do not begin analysis unless explicitly asked.

## Optional Pass C — git-derived temporal fields (only if requested)
The source files carry only *current* status; the lifecycle lives in git history. If asked,
derive per ERC from `git log --follow`:
- status-transition dates parsed from diffs to the `status:` line (Draft → Review → Last Call → Final),
  and from those compute `time_to_final` (days from `created` to Final).
- `last_modified` date, `commit_count` (churn / staleness), and `distinct_committers`.
Skip unless asked; it materially increases run time. This is what turns the snapshot into a true time-series.

## Deferred — external enrichment (NOT part of this local run)
Keyed on `erc` as a later join, not pulled in this pass:
- on-chain adoption (deployments / usage via Dune, BundleBear) — separates *proposed* from *adopted*.
- discussion-thread volume (ethereum-magicians / the `discussions-to` link) as a contention/interest signal.
