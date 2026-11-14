"""Baseline cố ý yếu: một raw theo filename, bỏ derived/backup và ngoại lệ."""
import pandas as pd
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .pipeline import load


def run(ctx: RunContext) -> None:
    data = load(ctx)
    rows = []
    for req in data["requests"]:
        matches = sorted((a for a in data["artefacts"]
                          if a["type"] == "raw_video"
                          and req["subject_id"] in str(a.get("filename", ""))),
                         key=lambda a: a["artefact_id"])
        if matches:
            art = matches[0]
            rows.append({"request_id": req["request_id"], "artefact_id": art["artefact_id"], "action": "delete"})
            ctx.audit.log(actor="baseline", action="baseline_proposal", item_id=art["artefact_id"],
                          after="delete", request_id=req["request_id"], reason="RAW_FILENAME_ONLY")
    pd.DataFrame(rows, columns=["request_id", "artefact_id", "action"]).to_csv(ctx.out("actions.csv"), index=False)
    ctx.stats["n_items"] = len(rows)
    ctx.stats["mode"] = "prediction_only_no_execution"
    write_decision(Decision(status="HOLD", reason_code="BASELINE_PREDICTION_ONLY",
                           reason="Naive comparison baseline, no mock execution or approval",
                           owner=ctx.config["owner"], scope="t08", evidence=["actions.csv"]),
                   ctx.out("decision.json"), ctx.out("decision_log.csv"))
    print(f"[baseline] {len(rows)} raw-only proposals; no deletion executed")
