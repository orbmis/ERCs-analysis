# Pass B — semantic classification of ERC markdown files

You are given a list of ERC markdown file paths. Read each file's raw markdown. For EACH ERC,
produce the fields below. Use ONLY the file contents — no outside knowledge beyond these rules.

## topic — exactly ONE value from this controlled vocabulary (classify on PRIMARY purpose)
- `account-abstraction`: Smart-account mechanics — account abstraction, bundlers, paymasters, EOA delegation, session keys, batched/sponsored execution (4337, 7702, 6900, 7579; "UserOperation","paymaster","modular account").
- `agentic-workflows`: Autonomous-agent coordination, agent identity/authorization, intents, agent-to-agent payments, permissioned delegation to agents (8004; "agent","intent","delegated action","autonomous").
- `reputation-identity`: Attestations, credentials, DIDs, sybil resistance, naming, on-chain reputation/identity (ENS-style naming, attestation registries, "verifiable credential","soulbound").
- `nft`: Non-fungible / semi-fungible token standards & extensions (royalties, rentals, metadata, bound tokens) (721,1155,2981,4907,6551; "non-fungible","tokenURI","token-bound account").
- `rwa`: Real-world-asset tokenization, regulated/compliant transfer, security tokens, asset-backed instruments ("security token","compliance","transfer restriction","real-world asset").
- `defi`: DeFi protocol primitives & integrations — AMMs, lending, vaults, oracles, yield, liquidations (4626 vaults, oracle interfaces, "liquidity","collateral","yield","swap").
- `tokens-fungible`: Core fungible-token standards & extensions (approvals, permits, callbacks) NOT specific to a DeFi protocol (20,777,2612,1363; "fungible","allowance","transferFrom").
- `governance`: On-chain governance, voting, DAOs, proposals, delegation of voting power, treasury control ("proposal","quorum","vote","governor","DAO").
- `security-permissions`: Access control, permission/authorization frameworks, signing/verification schemes, security primitives NOT tied to a single token type (1271, 7710/7715; "authorization","access control").
- `infrastructure-meta`: Process/meta ERCs, registries, addressing, encoding, cross-chain/L2 plumbing, low-level interface conventions with no single domain above (EIP-1-style process, "registry","namespace","cross-chain","calldata encoding").
- `other`: Genuinely fits none above.

Classification rules (apply IN ORDER):
1. Primary purpose wins. An ERC that merely *uses* another domain isn't classified there. A vault issuing ERC-20 shares is `defi`, not `tokens-fungible`.
2. More specific beats more general. Prefer `nft`/`tokens-fungible`/`defi` over `infrastructure-meta` when a clear domain applies.
3. Agent vs AA: smart-account capability (how an account executes) -> `account-abstraction`; autonomous-agent coordination/authorization/identity/intents -> `agentic-workflows`.
4. Permissions vs governance: generic authorization/permission frameworks -> `security-permissions`; voting/proposal/treasury specifically -> `governance`.
5. Use `other` only after rejecting every defined value. Sparingly.

## Other per-ERC fields
- `topic_secondary`: a second vocabulary value if it genuinely straddles two domains, else "".
- `topic_confidence`: "high" | "medium" | "low". Use low/medium for borderline calls.
- `topic_other`: freeform label, ONLY when topic == "other", else "".
- `referenced_ercs`: list of ERC/EIP numbers (ints) mentioned in the BODY beyond the formal `requires` frontmatter list.
- `one_line_summary`: <=25 words, plain description of what the ERC does.
- `notes`: anything analytically useful NOT already deterministic (novel mechanism, supersession/relationship, security caveat, design trade-off). Empty "" rather than padding. Do NOT restate status.

## Output
Write a JSON object to the output path given in your task. Keys = ERC numbers (ints as strings ok).
Every field present (empty string where N/A; referenced_ercs an array). No prose, no markdown fences — just the JSON file.
Schema per ERC: {"topic","topic_secondary","topic_confidence","topic_other","referenced_ercs","one_line_summary","notes"}
