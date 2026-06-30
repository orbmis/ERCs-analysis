# ERC Dataset Builder

A Claude Code workflow that turns the locally-cloned Ethereum ERCs repository into a single,
validated, analysis-ready CSV — one row per ERC, with structured metadata, a consistent
semantic taxonomy, and dependency-graph fields suitable for repo-wide and time-series analysis.

The work is packaged as a skill (`erc-dataset`) and driven autonomously with Claude Code's
`/goal` command, which keeps the agent working across turns until a verifiable completion
condition is met.

> ## 📊 Read the analysis
>
> The dataset has been built **and analyzed**. The full write-up is:
>
> ### → **[`analysis/ERC_REPORT.md`](analysis/ERC_REPORT.md)** — the consolidated report
>
> A single, coherent read of nine analyses of all 600 ERCs. Headline findings:
>
> - **A tiny core carries the whole ecosystem** — four standards (ERC-165/721/20/1155, plus EIP-712) anchor the entire dependency graph, and the same handful dominate authorship, discussion, *and* on-chain adoption (millions of deployments) while ~596 ERCs have no measurable mainnet footprint.
> - **Only ~23% of ERCs ever reach Final** — survival analysis says fewer than a third ever will; ~70% of the 2018–2021 boom cohorts went Stagnant; 78% of authors write exactly one ERC.
> - **The frontier rotated to agents & accounts** — account-abstraction and agentic standards are the newest, slowest, longest, most-debated, and *least-tested* work; ERC-4337 on-chain usage grew ~240× from 2023→2025, **adoption lagging standardization by 2–4 years**.
> - **Discussion confers legitimacy, not delay** — engagement rises monotonically toward Final and silence is near-fatal (10% finalization), but debate *volume* has no bearing on finalization speed.
>
> Seven standalone sub-reports under [`analysis/`](analysis/) carry the detail:
> [foundation](analysis/ERC_ANALYSIS.md) ·
> [network / survival / predictor deep dives](analysis/FURTHER_ANALYSIS.md) ·
> [external-EIP graph](analysis/EXTERNAL_EIP_GRAPH.md) ·
> [time-series eras](analysis/TIMESERIES_ANALYSIS.md) ·
> [discussion engagement](analysis/DISCUSSION_ANALYSIS.md) ·
> [on-chain adoption](analysis/ONCHAIN_ADOPTION.md) ·
> [build report](_run_report.md).
> 38 figures live in [`analysis/figures/`](analysis/figures/); every statistic is reproducible from the scripts (see [Reproducing the analysis](#reproducing-the-analysis)).

---

## What it produces

Two files in the working directory:

- **`erc_dataset.csv`** — one row per `ERCs/ERCS/erc-<N>.md` file, ~29 columns spanning
  frontmatter metadata, semantic classification, body-structure signals, and dependency-graph
  metrics. See [Output schema](#output-schema).
- **`_run_report.md`** — a run summary: files processed, frontmatter failures, subagent count,
  the `topic` distribution, and the list of rows flagged for manual review.

The CSV is the substrate for the analysis the dataset is designed to support — topic composition,
dependency centrality, standard maturity, author networks, and (with the optional git pass)
lifecycle timing. See [Analysis the dataset supports](#analysis-the-dataset-supports).

---

## Prerequisites

- The **ERCs repo cloned locally** so that `ERCs/ERCS/erc-*.md` files exist on disk.
- **Claude Code v2.1.139 or later** (the version that introduced `/goal`).
- The workspace **trust dialog accepted** — `/goal` runs as part of the hooks system and is
  unavailable in untrusted workspaces or where hooks are disabled.
- A plan with enough headroom. A few-hundred-file run sits comfortably inside a **Max 5x**
  session given the cost discipline below; for zero subscription impact you can run it under
  API billing instead. See [Cost & safety model](#cost--safety-model).
- Optional: **`networkx`** (only if you want the `pagerank` centrality column in Pass D) and
  **`git`** (only for the optional temporal pass).

---

## Installation

Place the skill folder in your repository so the final path is:

```
.claude/skills/erc-dataset/SKILL.md
```

Project-scoped skills are available only inside that repository, which is what you want here.
If the skill doesn't appear when you type `/` in Claude Code, restart the session or run `/init`.

---

## Usage

### Recommended: drive it with `/goal`

`/goal` takes a *completion condition*, not a prompt — Claude starts working immediately and a
separate evaluator model checks the transcript after every turn until the condition holds. The
detailed instructions live in the skill; the `/goal` line just names the skill and states the
finish line:

```
Use the erc-dataset skill to build erc_dataset.csv from ERCs/ERCS/. Done when: erc_dataset.csv exists in the working directory and the matched erc-<int>.md file count equals the CSV row count (both printed to the transcript); columns erc, title, status, created are non-null for every row or each exception is listed in _run_report.md; every created value parses as ISO YYYY-MM-DD; and _run_report.md exists summarising files processed, frontmatter failures, subagent count, topic distribution, and rows flagged for review. Prove it by printing to the transcript the matched file count, the CSV row count, the CSV column header, a null check on the four required columns, and a date-parse check. No file under ERCs/ has been modified.
```

The `prove it by printing…` clause is load-bearing: the evaluator only reads what Claude
surfaces in the conversation, so the condition must be demonstrable from printed output rather
than from Claude merely asserting success.

### Alternative: run it interactively

Invoke `/erc-dataset` directly to load and run the skill with normal turn-by-turn control. Use
this when you want to watch each pass and intervene — at the cost of re-prompting "continue"
between turns. `/goal` exists precisely to remove that re-prompting for a job with a verifiable
end state.

### Watch the cost while it runs

Use `/usage` or `/status` inside Claude Code (or Settings → Usage on claude.ai) to see burn and
your reset window. Starting at the top of a fresh 5-hour window gives the run a full session
budget.

---

## Methodology

### Core principle: deterministic first, LLM only where judgment is required

The naive approach treats the whole task as one big language-model extraction job. That is the
expensive, non-reproducible, and partly hallucination-prone way to do it — because most of what
you want is already structured data.

Every ERC opens with standardized YAML frontmatter (`title`, `author`, `status`, `type`,
`category`, `created`, `requires`, `discussions-to`). Roughly two-thirds of the target fields —
including the name, authors, creation date, status, and the *formal dependency list* — can be
parsed deterministically with a script: exactly, for free, and identically on every rerun. The
language model is reserved for the genuinely fuzzy minority: a semantic topic that the
frontmatter doesn't capture, references that appear only in prose, and short judgment notes.

This split is the spine of the whole design. It drives the cost profile (the LLM touches only
one pass), the reproducibility (the structured fields are deterministic), and the quality (exact
values rather than model approximations of data that was sitting in plain text).

### The passes

| Pass | Method | Produces | Cost |
|---|---|---|---|
| **A** | Script — parse YAML frontmatter | Core metadata + formal `requires` dependencies; normalized author identities | Negligible |
| **A2** | Script — regex over bodies | Structure flags (security considerations, test cases, reference impl) + complexity proxies | Negligible |
| **B** | Haiku subagents, batched | Semantic `topic`, body-referenced ERCs, one-line summary, judgment notes | The only real LLM cost |
| **D** | Script — graph over `requires` | Reverse edges, in/out degree, centrality, dependency depth | Negligible |

Passes A, A2, and D are plain scripts. Pass B is the only stage that consumes a language model,
and it runs on **Haiku** in batches (~15 ERCs per subagent, ~6 concurrent), each subagent seeing
only its instruction block and its assigned markdown — nothing else.

### Why a controlled vocabulary for `topic`

If each subagent invented its own category labels, the resulting column would be free-text soup:
ungroupable, and useless for time-series. So Pass B classifies into a **fixed eleven-value enum**
with a written gloss and example signals for each value, plus ordered tie-break rules for the
genuine boundary cases (smart-account capability vs. agent authorization; generic permissions vs.
governance; specific domain vs. cross-cutting infrastructure). A defined vocabulary also improves
a small model's consistency far more than it would a large one's — which is what makes Haiku the
right tool here.

To avoid discarding the cases that legitimately span two domains, `topic` stays single-valued
(clean for grouping) while a separate `topic_secondary` preserves the straddle signal, and
`topic_confidence` marks borderline calls so they surface in the run report for audit.

### Formal vs. informal dependency edges

Two different relationships are captured separately and never conflated:

- **`requires`** — the formal dependency declared in frontmatter. These are the authoritative
  edges of the dependency graph (Pass D builds from these only).
- **`referenced_ercs`** — ERCs merely *mentioned* in the body. A looser "related-to" signal,
  kept distinct so it can be analyzed without polluting the graph.

Pass D inverts the formal edges into `required_by` (which ERCs depend on this one — the
load-bearing / influence signal), and derives degree, centrality, and dependency depth to
separate foundational standards from leaf ones.

---

## Output schema

Columns grouped by origin. List-valued fields are semicolon-separated; `created` is ISO
`YYYY-MM-DD` for clean time-series handling.

**Identity & frontmatter (Pass A)**
`erc`, `title`, `description`, `status`, `type`, `category`, `created`, `last_call_deadline`,
`withdrawal_reason`, `author`, `authors_normalized`, `requires`, `discussions_to`

**Semantic classification (Pass B)**
`topic`, `topic_secondary`, `topic_confidence`, `topic_other`, `referenced_ercs`,
`one_line_summary`, `notes`

**Body-structure signals (Pass A2)**
`has_security_considerations`, `has_test_cases`, `has_reference_impl`, `spec_word_count`,
`section_count`

**Dependency graph (Pass D)**
`required_by`, `in_degree`, `out_degree`, `pagerank`, `dependency_depth`

> Note: `category` (Pass A) is the formal EIP type subfield — Core / Networking / Interface /
> ERC — and is distinct from `topic` (Pass B), which is the analytical subject-matter taxonomy.

---

## Cost & safety model

The job is bounded by design. The factors that actually drive token usage, and the guards
against each:

- **Orchestrator turns.** The biggest lever is keeping the main coordination loop on **Sonnet,
  not Opus** — this is dispatch-and-merge work, not deep reasoning. The skill states this
  explicitly.
- **Context bloat.** The orchestrator must never read ERC markdown *bodies* into its own context;
  only the scripts and the Haiku subagents touch file contents, and subagents return compact JSON.
  This is the single biggest way the run could balloon, and the skill forbids it.
- **Subagent fan-out.** A cost guard stops the run before Pass B if `ceil(files / batch_size)`
  exceeds 60 subagents. If the folder is larger than expected, raise `batch_size` rather than the
  ceiling, so the agent count stays bounded.
- **Source safety.** Everything under `ERCs/` is read-only; all writes go to the working directory.
- **Resumability.** Output is written incrementally and reruns skip already-processed ERCs, so a
  crash or limit-reset never forces a restart from scratch.

For a few-hundred-file repo with those guards in place, this stays comfortably within a Max 5x
session. If you'd rather not touch subscription quota at all, run it under API billing — a
Haiku-dominated batch like this is cheap per token.

---

## Extending the dataset

**Pass C — git-derived temporal fields. ✓ Done** (`erc_temporal.csv`). Status-transition dates,
`time_to_final` (days from `created` to Final), `last_modified`, `commit_count`, and
`distinct_committers`, mined from `git log --follow` over the source repo's history. This turns the
snapshot into a genuine time-series and underpins the lifecycle/survival analysis.

**External enrichment (joined on `erc`). ✓ Done** — the fields that separate *proposed* from
*adopted*: **on-chain adoption** (`erc_adoption.csv`, deployments/usage via Dune —
see [`ONCHAIN_ADOPTION.md`](analysis/ONCHAIN_ADOPTION.md)) and **discussion-thread volume**
(`erc_discussions.csv`, ethereum-magicians + GitHub via the `discussions-to` link —
see [`DISCUSSION_ANALYSIS.md`](analysis/DISCUSSION_ANALYSIS.md)).

---

## Analysis the dataset supports

*All of the following were carried out — see **[`analysis/ERC_REPORT.md`](analysis/ERC_REPORT.md)** for the consolidated write-up and the linked sub-reports for detail.*

- **Topic composition over time** — `topic` × `created` (year/quarter): how the standards body's
  focus has shifted (e.g. the rise of account-abstraction and agentic-workflow ERCs).
- **Dependency centrality** — `required_by`, `in_degree`, `pagerank`: which standards are
  load-bearing vs. peripheral; the spine of the composition stack.
- **Standard maturity** — `has_security_considerations` / `has_test_cases` against `status`:
  where Final-track ERCs are missing the rigor EIP-1 expects.
- **Author networks** — `authors_normalized`: co-authorship structure and the most prolific
  contributors.
- **Lifecycle timing** — with Pass C, `time_to_final` and status-velocity distributions across
  topics and cohorts.
- **Straddle / boundary standards** — non-empty `topic_secondary`: ERCs that bridge two domains,
  often the most architecturally interesting.

---

## Reproducing the analysis

The analysis layer is plain Python (stdlib + `matplotlib`, `networkx`, `scikit-learn`, `scipy`).
Each script reads the CSVs and writes figures/metrics under `analysis/`:

| Script | Produces |
|---|---|
| `pass_ad.py`, `pass_c.py`, `merge.py` | the dataset (`erc_dataset.csv`, `erc_temporal.csv`) |
| `compute.py` | foundation analysis ([`ERC_ANALYSIS.md`](analysis/ERC_ANALYSIS.md)) |
| `further.py` | networks, survival, predictor, retention ([`FURTHER_ANALYSIS.md`](analysis/FURTHER_ANALYSIS.md)) |
| `timeseries.py` | topic eras over time ([`TIMESERIES_ANALYSIS.md`](analysis/TIMESERIES_ANALYSIS.md)) |
| `build_ext_graph.py` | external-EIP graph completion ([`EXTERNAL_EIP_GRAPH.md`](analysis/EXTERNAL_EIP_GRAPH.md)) |
| `fetch_discussions.py`, `analyze_discussions.py` | discussion engagement ([`DISCUSSION_ANALYSIS.md`](analysis/DISCUSSION_ANALYSIS.md)) |
| `run_dune.py`, `build_adoption.py` | on-chain adoption ([`ONCHAIN_ADOPTION.md`](analysis/ONCHAIN_ADOPTION.md)) |

The on-chain pass needs a Dune API key, read from a **gitignored** `.dune_key` (or `DUNE_API_KEY`
env var) — never committed. The discussion pass is resumable (per-thread cache, gitignored).

---

## Caveats & limitations

- **The evaluator is transcript-only.** `/goal`'s completion check reads what Claude prints, not
  the filesystem independently — hence the explicit "print the checks" requirement in the
  condition. Without it, the goal could pass on an assertion rather than a demonstration.
- **`notes` is the one soft field.** It's the single open-ended judgment field, and a small model
  reads it more shallowly than a large one. Spot-check ~20 rows; if it's thin, drop it or re-run
  only `notes` (and any `topic_confidence: low` rows) through a small Sonnet pass.
- **Classification is probabilistic.** Boundary ERCs may be debatable. The vocabulary, tie-break
  rules, `topic_confidence`, and the run-report review list exist to make those calls auditable
  rather than invisible — they don't eliminate them.
- **`pagerank` needs a graph library.** If you'd rather keep the run dependency-free, omit it;
  `in_degree` / `out_degree` already carry most of the foundational-vs-leaf signal.
- **Snapshot, not history, by default.** Without Pass C the dataset reflects the repo at the
  moment you run it — current status only, no transition history.
