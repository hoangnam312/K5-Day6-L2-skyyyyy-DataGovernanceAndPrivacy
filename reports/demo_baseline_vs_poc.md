Baseline: `baseline` (git 6a75e08, seed 42) · PoC: `poc` (git 6a75e08, seed 42)

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Better | N |
|---|---|---|---|---|---|---|---|
| **Deletion Completeness** (must-delete artefacts deleted / must-delete artefacts) | all | 0.5000 | 1.0000 | 0.5000 | +100.0% | higher | 10 |
| False-delete count (count (target 0): exceptions deleted + deletes outside request scope) | all | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | None |
| Exception handling accuracy (legal-hold/escalate rows handled as expected / such rows) | all | 0.0000 | 1.0000 | 1.0000 | baseline=0 | higher | None |
| Audit trace completeness (actions with an audit entry / actions) | all | 1.0000 | 1.0000 | 0.0000 | +0.0% | higher | None |
| Runtime / 100 items (s) | all | 2.1750 | 0.4000 | | | lower | |
