# Notebook rollout checkpoint — 15 November 2026

Work is paused at the user's request. The rollout ledger records **115 worker
repositories and 214 notebooks published**. The existing Units current-release
coverage gap remains documented separately; this count is not a claim that every
current worker API is covered.

Completed notebook changes are committed and pushed. The latest completed worker,
[FHIR](https://github.com/Query-farm/vgi-fhir/tree/main/notebooks), is on main at
`0c3abe02a26c14f0d941fe3a3e97230d69e46d10`.

The following public working branches preserve unfinished work. They have not been
merged into main and should not be described as completed examples.

| Worker | Checkpoint branch | Commit | Remaining work |
| --- | --- | --- | --- |
| [NFL](https://github.com/Query-farm/vgi-nfl/tree/notebooks/fleet-standard-nfl/notebooks) | `notebooks/fleet-standard-nfl` | `590749817e8507a10e47872ee0a92601b56f1fc8` | Four defaults and experiments passed; output comparisons, final chart review, preloaded setup, live checks, guards and publication remain. |
| [SNMP](https://github.com/Query-farm/vgi-snmp/tree/notebook-standard-snmp/notebooks) | `notebook-standard-snmp` | `5d4db2ffb1cedeeca2ee5737c4ec023d1c2c650e` | Draft default and simulator controls passed; companion registration, experiments, charts, fresh setup, final coverage and publication remain. |
| [Tennis](https://github.com/Query-farm/vgi-tennis/tree/notebooks/fleet-standard-tennis/notebooks) | `notebooks/fleet-standard-tennis` | `76577298ba201470f5f4577dffeaf99aa9272e08` | Two drafts remain unexecuted; third story, lint configuration, execution, coverage, chart review and portable setup remain. |

Shared tooling **v0.3.55** is pushed at
`cbfcd39eac4538dd14353124e8614f83da670d32`, including the frozen FHIR and Tennis
companions. NFL companions are in v0.3.54. The SNMP companion branch exists, but
its registry entry has not yet been released.

Original user checkouts and unrelated edits were preserved. The local coordinator
ledger retains the complete inventory, per-worker evidence, private-repository
holds and authoring scratch checkpoints. No background notebook work continues.
