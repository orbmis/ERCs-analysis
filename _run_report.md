# ERC dataset run report

- Files processed (matched `erc-<int>.md`): **600**
- CSV rows written: **600**
- Frontmatter failures: **0**
- Pass B subagents: **40** (batch size 15; loaded 40 batch files)
- ERCs missing a Pass B classification: **0**
- Out-of-vocabulary topics: **0**
- Required-column nulls (erc/title/status/created): **0**
- Non-ISO created values: **0**

## Frontmatter failures
None.

## Topic distribution

- `infrastructure-meta`: 175
- `nft`: 136
- `tokens-fungible`: 71
- `security-permissions`: 57
- `account-abstraction`: 44
- `reputation-identity`: 39
- `defi`: 37
- `rwa`: 13
- `governance`: 10
- `other`: 9
- `agentic-workflows`: 9

## Rows flagged for review (196)
Criteria: `topic = other`, `topic_confidence = low`, or non-empty `topic_secondary`.

| erc | topic | secondary | confidence | topic_other |
|---|---|---|---|---|
| 137 | reputation-identity | infrastructure-meta | high |  |
| 162 | reputation-identity | infrastructure-meta | high |  |
| 181 | reputation-identity | infrastructure-meta | high |  |
| 634 | infrastructure-meta | reputation-identity | high |  |
| 725 | infrastructure-meta | account-abstraction | medium |  |
| 801 | other |  | medium | canary contracts |
| 823 | defi | tokens-fungible | medium |  |
| 884 | rwa | tokens-fungible | high |  |
| 902 | security-permissions | tokens-fungible | high |  |
| 918 | tokens-fungible | defi | high |  |
| 998 | nft | tokens-fungible | high |  |
| 1046 | tokens-fungible | nft | high |  |
| 1078 | account-abstraction | reputation-identity | high |  |
| 1155 | nft | tokens-fungible | high |  |
| 1175 | tokens-fungible | infrastructure-meta | medium |  |
| 1261 | reputation-identity | governance | high |  |
| 1337 | defi | tokens-fungible | medium |  |
| 1438 | other |  | low | dApp component registry (avatar/badge store) and universal wallet |
| 1450 | rwa | security-permissions | high |  |
| 1491 | other |  | low | human capital accounting tokens based on BDI model |
| 1523 | nft | rwa | high |  |
| 1592 | tokens-fungible | security-permissions | medium |  |
| 1633 | nft | tokens-fungible | high |  |
| 1753 | other |  | medium | license-permits |
| 1761 | security-permissions | nft | high |  |
| 1775 | security-permissions | account-abstraction | high |  |
| 1922 | infrastructure-meta | security-permissions | medium |  |
| 1973 | defi | tokens-fungible | high |  |
| 1996 | tokens-fungible | defi | high |  |
| 2009 | security-permissions | tokens-fungible | high |  |
| 2018 | tokens-fungible | defi | high |  |
| 2019 | tokens-fungible | defi | high |  |
| 2020 | tokens-fungible | defi | high |  |
| 2021 | tokens-fungible | defi | high |  |
| 2193 | infrastructure-meta | reputation-identity | high |  |
| 2390 | reputation-identity | infrastructure-meta | high |  |
| 2525 | reputation-identity | security-permissions | medium |  |
| 2569 | infrastructure-meta | nft | medium |  |
| 2767 | governance | security-permissions | high |  |
| 2770 | account-abstraction | security-permissions | high |  |
| 2980 | rwa | tokens-fungible | medium |  |
| 3000 | governance | infrastructure-meta | medium |  |
| 3135 | tokens-fungible | defi | medium |  |
| 3386 | nft | tokens-fungible | medium |  |
| 3450 | infrastructure-meta | security-permissions | medium |  |
| 3475 | defi | nft | medium |  |
| 3525 | nft | tokens-fungible | medium |  |
| 3643 | rwa | security-permissions | high |  |
| 3722 | other |  | high | social media, content posting |
| 4353 | nft | tokens-fungible | high |  |
| 4361 | security-permissions | reputation-identity | high |  |
| 4393 | nft | tokens-fungible | high |  |
| 4494 | tokens-fungible | nft | high |  |
| 4521 | nft | tokens-fungible | high |  |
| 4546 | tokens-fungible | nft | medium |  |
| 4671 | reputation-identity | nft | high |  |
| 4885 | nft | defi | high |  |
| 4886 | security-permissions | infrastructure-meta | medium |  |
| 4910 | nft | defi | high |  |
| 4972 | reputation-identity | account-abstraction | medium |  |
| 4973 | nft | reputation-identity | high |  |
| 5050 | nft | infrastructure-meta | medium |  |
| 5114 | reputation-identity | nft | high |  |
| 5131 | security-permissions | reputation-identity | high |  |
| 5173 | nft | defi | high |  |
| 5192 | nft | reputation-identity | high |  |
| 5216 | tokens-fungible | nft | high |  |
| 5252 | account-abstraction | governance | medium |  |
| 5289 | security-permissions | reputation-identity | high |  |
| 5298 | reputation-identity | nft | high |  |
| 5375 | nft | reputation-identity | high |  |
| 5484 | reputation-identity | nft | high |  |
| 5505 | nft | defi | medium |  |
| 5507 | tokens-fungible | nft | high |  |
| 5516 | reputation-identity | nft | high |  |
| 5539 | security-permissions | infrastructure-meta | high |  |
| 5553 | nft | tokens-fungible | high |  |
| 5573 | security-permissions | reputation-identity | high |  |
| 5615 | tokens-fungible | nft | high |  |
| 5639 | security-permissions | governance | high |  |
| 5679 | tokens-fungible | nft | high |  |
| 5725 | defi | nft | high |  |
| 5727 | reputation-identity | nft | high |  |
| 5732 | infrastructure-meta | security-permissions | high |  |
| 5791 | nft | security-permissions | high |  |
| 5805 | governance | tokens-fungible | high |  |
| 6065 | rwa | nft | high |  |
| 6066 | security-permissions | nft | high |  |
| 6105 | nft | defi | high |  |
| 6120 | tokens-fungible | infrastructure-meta | high |  |
| 6147 | nft | security-permissions | high |  |
| 6239 | reputation-identity | nft | high |  |
| 6315 | account-abstraction | security-permissions | high |  |
| 6327 | security-permissions | account-abstraction | high |  |
| 6358 | infrastructure-meta | tokens-fungible | medium |  |
| 6464 | nft | security-permissions | high |  |
| 6492 | account-abstraction | security-permissions | high |  |
| 6538 | infrastructure-meta | security-permissions | medium |  |
| 6551 | nft | account-abstraction | high |  |
| 6604 | tokens-fungible | nft | medium |  |
| 6786 | nft | defi | medium |  |
| 6808 | tokens-fungible | security-permissions | high |  |
| 6809 | nft | security-permissions | high |  |
| 6909 | tokens-fungible | nft | high |  |
| 6932 | tokens-fungible | defi | medium |  |
| 6956 | nft | rwa | high |  |
| 6960 | tokens-fungible | nft | medium |  |
| 6981 | infrastructure-meta | account-abstraction | medium |  |
| 6997 | nft | security-permissions | high |  |
| 7092 | rwa | tokens-fungible | high |  |
| 7093 | security-permissions | account-abstraction | high |  |
| 7144 | tokens-fungible | security-permissions | high |  |
| 7204 | account-abstraction | tokens-fungible | high |  |
| 7231 | reputation-identity | nft | high |  |
| 7254 | defi | tokens-fungible | high |  |
| 7291 | defi | tokens-fungible | high |  |
| 7506 | reputation-identity | security-permissions | high |  |
| 7508 | nft | infrastructure-meta | high |  |
| 7512 | security-permissions | infrastructure-meta | high |  |
| 7513 | nft | account-abstraction | medium |  |
| 7518 | rwa | tokens-fungible | high |  |
| 7522 | account-abstraction | security-permissions | high |  |
| 7527 | nft | defi | high |  |
| 7528 | infrastructure-meta | tokens-fungible | high |  |
| 7529 | reputation-identity | infrastructure-meta | high |  |
| 7531 | nft | security-permissions | high |  |
| 7535 | defi | tokens-fungible | high |  |
| 7538 | tokens-fungible | nft | medium |  |
| 7540 | defi | security-permissions | high |  |
| 7546 | infrastructure-meta | security-permissions | high |  |
| 7555 | account-abstraction | reputation-identity | high |  |
| 7562 | account-abstraction | security-permissions | high |  |
| 7564 | account-abstraction | nft | high |  |
| 7565 | defi | nft | high |  |
| 7566 | other |  | high | On-chain multiplayer game communication |
| 7578 | nft | rwa | high |  |
| 7590 | nft | tokens-fungible | high |  |
| 7595 | nft | rwa | high |  |
| 7597 | security-permissions | tokens-fungible | high |  |
| 7598 | tokens-fungible | security-permissions | medium |  |
| 7604 | nft | tokens-fungible | high |  |
| 7613 | infrastructure-meta | account-abstraction | high |  |
| 7615 | infrastructure-meta | defi | medium |  |
| 7621 | defi | tokens-fungible | high |  |
| 7627 | infrastructure-meta | reputation-identity | medium |  |
| 7629 | tokens-fungible | nft | medium |  |
| 7631 | nft | tokens-fungible | high |  |
| 7638 | account-abstraction | infrastructure-meta | high |  |
| 7641 | tokens-fungible | defi | high |  |
| 7649 | nft | defi | high |  |
| 7681 | tokens-fungible | nft | high |  |
| 7683 | agentic-workflows | infrastructure-meta | high |  |
| 7695 | nft | security-permissions | high |  |
| 7710 | security-permissions | account-abstraction | high |  |
| 7715 | account-abstraction | security-permissions | high |  |
| 7726 | defi | infrastructure-meta | high |  |
| 7730 | infrastructure-meta | security-permissions | high |  |
| 7750 | other |  | medium | decentralized-employment-system |
| 7758 | tokens-fungible | security-permissions | high |  |
| 7765 | rwa | nft | high |  |
| 7770 | tokens-fungible | defi | high |  |
| 7776 | other |  | medium | transparent-financial-reporting |
| 7777 | agentic-workflows | reputation-identity | medium |  |
| 7780 | account-abstraction | security-permissions | high |  |
| 7787 | governance | reputation-identity | high |  |
| 7802 | tokens-fungible | defi | high |  |
| 7803 | security-permissions | account-abstraction | high |  |
| 7806 | account-abstraction | agentic-workflows | high |  |
| 7828 | infrastructure-meta | reputation-identity | high |  |
| 7829 | nft | defi | high |  |
| 7832 | nft | governance | high |  |
| 7836 | infrastructure-meta | account-abstraction | high |  |
| 7846 | infrastructure-meta | security-permissions | high |  |
| 7847 | nft | reputation-identity | high |  |
| 7857 | nft | reputation-identity | high |  |
| 7861 | reputation-identity | nft | high |  |
| 7878 | tokens-fungible | nft | medium |  |
| 7884 | infrastructure-meta | defi | high |  |
| 7920 | security-permissions | tokens-fungible | medium |  |
| 7945 | tokens-fungible | security-permissions | high |  |
| 7946 | account-abstraction | security-permissions | high |  |
| 7947 | account-abstraction | security-permissions | high |  |
| 7962 | tokens-fungible | security-permissions | high |  |
| 7968 | security-permissions | tokens-fungible | high |  |
| 7992 | other |  | high | verifiable-ml-inference |
| 8041 | agentic-workflows | nft | medium |  |
| 8047 | tokens-fungible | infrastructure-meta | high |  |
| 8092 | security-permissions | reputation-identity | high |  |
| 8107 | reputation-identity | agentic-workflows | high |  |
| 8122 | infrastructure-meta | agentic-workflows | high |  |
| 8126 | reputation-identity | agentic-workflows | high |  |
| 8161 | defi | tokens-fungible | high |  |
| 8196 | agentic-workflows | security-permissions | high |  |
| 8199 | account-abstraction | agentic-workflows | high |  |
| 8226 | rwa | agentic-workflows | high |  |
| 8273 | agentic-workflows | security-permissions | high |  |

