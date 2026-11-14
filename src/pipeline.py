"""LeVanKhoi: nối 5 bước T08; phần riêng nằm trong src/t08/."""
from __future__ import annotations
import html
import json

import pandas as pd
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.io import write_json
from .common.manifest import verify_manifest
from .t08.input_data import load_input, fingerprint
from .t08.lineage import find_related
from .t08.policy import POLICY_VERSION, propose_action
from .t08.human_review import build_queue, apply_review
from .t08.executor import execute_mock

ACTION_COLUMNS = ["item_id", "request_id", "artefact_id", "subject_id", "artefact_type",
                  "deadline", "uri", "evidence_path", "policy_version", "action",
                  "proposed_action", "reason_code", "reason", "score", "needs_review",
                  "execution_approved", "reviewer", "review_status"]


def load(ctx: RunContext) -> dict:
    if ctx.track != "t08":
        raise NotImplementedError("This reference pipeline implements T08 only")
    # Bản tham khảo luôn kiểm toàn vẹn, kể cả nếu cấu hình cố tắt guard.
    problems = verify_manifest(ctx.input_dir / "manifest.csv")
    if problems:
        raise ValueError(f"provenance check failed: {problems[:3]}")
    data = load_input(ctx.input_dir)
    actor = ctx.param("actor", "data-platform")
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("params.actor must name the execution principal")
    ctx.stats.update(n_requests=len(data["requests"]), n_artefacts=len(data["artefacts"]),
                     input_hash=data["input_hash"],
                     plan_hash=fingerprint({"input": data["input_hash"], "actor": actor,
                                            "policy": POLICY_VERSION}))
    print(f"[load] T08: {len(data['requests'])} requests, {len(data['artefacts'])} artefacts")
    return data


def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    records = []
    counts = {}
    for request in data["requests"]:
        related = find_related(request, data["artefacts"])
        counts[request["request_id"]] = len(related)
        for art in related:
            row = propose_action(request, art, ctx.param("actor", "data-platform"))
            records.append(row)
            # Evaluator chuẩn tra item_id bằng artefact ID; audit thêm composite_id
            # để truy chính xác cặp request-artifact mà không sửa evaluator.
            ctx.audit.log(actor="policy", action="action_proposed", item_id=row["artefact_id"],
                          after=row["action"], reason=row["reason_code"],
                          request_id=row["request_id"], composite_id=row["item_id"],
                          plan_hash=ctx.stats["plan_hash"], evidence_path=row["evidence_path"])
    ctx.stats["scope_counts"] = counts
    ctx.stats["requests_without_scope"] = sorted(key for key, n in counts.items() if n == 0)
    scored = pd.DataFrame(records, columns=ACTION_COLUMNS)
    scored.to_csv(ctx.out("proposed_actions.csv"), index=False)
    return scored


def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    return build_queue(ctx, scored)


def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    return apply_review(ctx, scored)


def decide(ctx: RunContext, final: pd.DataFrame) -> Decision:
    counts = final.action.value_counts().to_dict()
    execution = ctx.stats.get("execution_counts", {})
    if ctx.stats["requests_without_scope"]:
        status, code = "HOLD", "REQUEST_SCOPE_NOT_FOUND"
    elif ctx.param("dry_run", True):
        status, code = "HOLD", "DRY_RUN_ONLY"
    elif execution.get("pending_approval", 0) or execution.get("blocked_conflicting_request", 0):
        status, code = "HOLD", "PENDING_APPROVAL_OR_CONFLICT"
    elif counts.get("escalate", 0) or counts.get("retain_legal_hold", 0):
        status, code = "HOLD", "EXCEPTIONS_REQUIRE_FOLLOW_UP"
    else:
        status, code = "GO", "MOCK_ACTIONS_COMPLETE"
    return Decision(status=status, reason_code=code,
                    reason="Mock-only run; see action decisions and execution evidence. " + code,
                    owner=ctx.config["owner"], scope="t08",
                    evidence=["actions.csv", "execution_evidence.csv", "audit_log.jsonl", "summary.json"],
                    metrics={"action_counts": counts, "execution_counts": execution})


def run(ctx: RunContext) -> None:
    owner = str(ctx.config.get("owner", "")).strip()
    if not owner or owner.startswith("TODO"):
        raise ValueError("Fill config owner with the responsible person")
    data = load(ctx)
    proposed = process(ctx, data)
    ctx.stats["n_items"] = len(proposed)
    queue = rank(ctx, proposed)
    reviewed = review(ctx, proposed, queue)
    final = execute_mock(ctx, reviewed)
    # Đây là quyết định cuối, không có nghĩa tất cả delete đã được thực hiện.
    final.to_csv(ctx.out("actions.csv"), index=False)
    summaries = []
    for request in data["requests"]:
        rows = final.loc[final.request_id == request["request_id"]]
        summaries.append({"request_id": request["request_id"], "subject_id": request["subject_id"],
                          "deadline": request["deadline"], "n_artefacts": len(rows),
                          "action_counts": rows.action.value_counts().to_dict(),
                          "execution_counts": rows.execution_status.value_counts().to_dict()})
    summary = {"mode": "dry_run" if ctx.param("dry_run", True) else "mock_execute",
               "policy_version": POLICY_VERSION, "owner": owner,
               "input_hash": data["input_hash"], "plan_hash": ctx.stats["plan_hash"],
               "n_requests": len(data["requests"]), "n_actions": len(final),
               "n_unique_artefacts": int(final.artefact_id.nunique()),
               "action_counts": final.action.value_counts().to_dict(),
               "execution_counts": ctx.stats["execution_counts"],
               "official_metrics": None, "note": "No instructor GT: these are operational counts, not official scores",
               "requests": summaries}
    write_json(ctx.out("summary.json"), summary)
    pd.DataFrame([{**r, "action_counts": json.dumps(r["action_counts"]),
                   "execution_counts": json.dumps(r["execution_counts"])} for r in summaries]).to_csv(
                       ctx.out("request_summary.csv"), index=False)
    decision = decide(ctx, final)
    write_decision(decision, ctx.out("decision.json"), ctx.out("decision_log.csv"))
    ctx.out("dashboard.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>T08 summary</title>'
        '<h1>T08 — Mock deletion run</h1><p>Operational counts, not official scores.</p>'
        '<p><a href="review.html">Open human review</a></p><pre>' +
        html.escape(json.dumps(summary, ensure_ascii=False, indent=2)) + '</pre>', encoding="utf-8")
    print(f"[poc] actions={len(final)} counts={summary['action_counts']}")
    print(f"[decision] {decision.status}: {decision.reason_code}; mock data only")
