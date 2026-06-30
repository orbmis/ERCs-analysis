# Addendum — External-EIP graph completion (#12)

*The dependency analyses so far were computed on `requires`/`referenced_ercs` edges that stay inside the 600-ERC corpus. But ERCs also depend on **Core (and other) EIPs** that live outside the ERC set. This addendum fetches those 36 referenced EIPs from `ethereum/EIPs`, adds them as real graph nodes, and recomputes influence so the picture is no longer truncated at the ERC boundary. Reproducible from `build_ext_graph.py`; data in `analysis/external_eip_metrics.json` and `analysis/tables/combined_influence.csv`.*

## What was added
- **36 external EIP nodes** referenced by ERCs but outside the corpus: **27 resolved** (live frontmatter fetched from GitHub) and **9 unresolved** — references to EIPs that no longer exist as standards (672, 677, 735, 780, 827, 1643, 1644, 2158, 7939).
- The graph grew from 778 to **897 edges** across 636 nodes.

![ERC + external-EIP dependency graph](figures/dependency_graph_full.png)

*(Squares = external Core/other EIPs; circles = ERCs colored by topic; triangles = unresolved references.)*

## Headline: EIP-712 is a top-5 load-bearing standard

With external EIPs included, the true influence ranking (by in-degree = how many ERCs depend on it) is:

| Rank | Node | Title | Depended on by | Status |
|---|---|---|---|---|
| 1 | ERC-165 | Standard Interface Detection | 177 | Final |
| 2 | ERC-721 | Non-Fungible Token Standard | 145 | Final |
| 3 | ERC-20 | Token Standard | 104 | Final |
| 4 | ERC-1155 | Multi Token Standard | 60 | Final |
| **5** | **EIP-712** | **Typed structured data hashing and signing** | **43** | Final |
| **6** | **EIP-155** | **Simple replay attack protection** | **27** | Final |
| 7 | ERC-1271 | Signature Validation for Contracts | 27 | Final |
| 8 | ERC-137 | ENS Specification | 19 | Final |
| 9 | ERC-4337 | Account Abstraction (Alt Mempool) | 14 | Final |

**EIP-712 (typed-data signing) is the 5th most-depended-upon standard in the entire ecosystem** — more load-bearing than ERC-1271 — yet it was completely invisible in the ERC-only graph. It is the connective tissue beneath nearly every signature-based standard (permits, meta-transactions, account abstraction, intents). **EIP-155** (replay protection) is similarly foundational at #6.

## The rising Core-EIP frontier
Below the bedrock, the external EIPs that ERCs increasingly build on are exactly the new account/wallet primitives:

| EIP | Title | In-degree | Overall rank |
|---|---|---|---|
| 7702 | Set Code for EOAs | 7 | #16 |
| 5792 | Wallet Call API | 7 | #17 |
| 4844 | Shard Blob Transactions | 5 | #21 |
| 1193 | Ethereum Provider JS API | 5 | #23 |

These confirm the earlier finding that the frontier is **accounts + wallets**: ERC authors are now anchoring on EIP-7702 (EOA delegation) and EIP-5792 (wallet calls) the way an earlier generation anchored on ERC-20/721.

## Two incidental findings
1. **Dangling references.** 9 ERCs cite EIPs that no longer exist (e.g., EIP-677 `transferAndCall`, EIP-735 claim-holder, EIP-1643/1644 ENS records) — a minor data-hygiene signal: standards referencing withdrawn/never-merged predecessors.
2. **Methodology note.** With external EIPs entering as dependency *sinks* (they rarely `require` anything back inside the corpus), **in-degree is the reliable influence metric here**; PageRank becomes distorted by the dangling-sink structure, so the ranking above uses in-degree.

## Artifacts
| File | Contents |
|---|---|
| `analysis/external_eip_metrics.json` | combined ranking + external-EIP ranking + unresolved list |
| `analysis/tables/combined_influence.csv` | top-25 combined influence table |
| `analysis/figures/dependency_graph_full.png` | the completed graph |
| `ext_eips/eip-*.md` | the 27 fetched external EIP source files |
| `build_ext_graph.py` | regenerates everything above |
