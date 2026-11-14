# T08 integration check

Base fetched from GitHub: origin/main at 6a75e08. Existing lineage, policy and
executor were retained. Review implementation from fba74cc was relocated from
src/human_review.py to src/t08/human_review.py to fix package-relative imports.

Integration additions: complete input validation/input hash, baseline, pipeline
wiring, review-to-executor handoff, decision/output generation and execute config.
Latest shared owner/group preserved: Dương Quốc Anh / skyyyy.

## Checks actually performed

- Full pytest run: **70 passed, 39 skipped** (13.52 s). Skips require instructor GT.
- Class fixture PoC: exit 0, 10 requests, 212 input artefacts, 158 request-artefact
  decisions: 128 delete proposals, 28 escalate, 2 retain_legal_hold.
- Default mode dry-run: no class-fixture human approvals or mock deletions claimed.
- Baseline: exit 0, 10 raw-only proposals.
- Development self-check: exit 0, 2 requests / 9 artefacts / 10 hand-authored
  expected pairs; completeness 0.5 baseline versus 1.0 PoC; false-delete 0 for both.
- Generated review JavaScript/export: passes DOM test-double check, including
  CSV encoding/quotes/newlines. This is not visual browser QA or real human review.

Commands:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -o addopts= -q -ra
.\.venv\Scripts\python.exe -m src.main --offline --seed 42
.\.venv\Scripts\python.exe -m src.main --pipeline src.t08_baseline --output out/baseline --run-name baseline --offline --seed 42
.\.venv\Scripts\python.exe -X utf8 tools/run_t08_selfcheck.py
node tools/check_review_ui.cjs out/poc/review.html
~~~

Windows fixture text bytes were normalized to LF only after checking that the
normalized hash exactly matched the existing manifest. Manifests and evaluator
definitions were not changed. Git attributes preserve those bytes on later clones.

Official class-fixture scores remain unavailable until instructor GT is supplied.
Human review and the demo presentation still need to be performed by the team.
