"""Render a self-contained offline dashboard; counters come from actual run data."""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from ..common.decision import Decision


def render_dashboard(summary: dict, final: pd.DataFrame, decision: Decision,
                     path: Path, n_reviewed: int = 0) -> None:
    template = (Path(__file__).parent / "templates" / "dashboard.html").read_text(encoding="utf-8")
    execution = summary.get("execution_counts", {})
    actions = summary.get("action_counts", {})
    deleted = int(execution.get("deleted", 0)) + int(execution.get("already_deleted", 0))
    pending = int(execution.get("pending_approval", 0))
    planned = int(execution.get("planned_delete", 0))
    esc = int(actions.get("escalate", 0))
    hold = int(actions.get("retain_legal_hold", 0))
    action_n = int(summary.get("n_actions", 0))
    dry = summary.get("mode") == "dry_run"
    # Escape HTML fields, then insert JSON last so data cannot act as template code.
    values = {
        "owner": summary.get("owner", ""),
        "mode": "Dry-run · Lập kế hoạch" if dry else "Thực hiện mô phỏng",
        "decision": decision.status,
        "decision_reason": {
            "DRY_RUN_ONLY": "Đang lập kế hoạch. Chưa thực hiện xóa mô phỏng.",
            "PENDING_APPROVAL_OR_CONFLICT": "Còn quyết định chờ duyệt hoặc xung đột cần xử lý.",
            "EXCEPTIONS_REQUIRE_FOLLOW_UP": "Còn ngoại lệ cần người phụ trách theo dõi.",
            "REQUEST_SCOPE_NOT_FOUND": "Có yêu cầu chưa xác định được dữ liệu liên quan.",
            "MOCK_ACTIONS_COMPLETE": "Các hành động mô phỏng đã hoàn tất.",
        }.get(decision.reason_code, decision.reason),
        "n_requests": int(summary.get("n_requests", 0)),
        "n_actions": action_n,
        "n_unique": int(summary.get("n_unique_artefacts", 0)),
        "n_delete": int(actions.get("delete", 0)),
        "n_exceptions": esc + hold,
        "n_escalate": esc,
        "n_hold": hold,
        "n_deleted": deleted,
        "n_pending": pending,
        "n_planned": planned,
        "n_reviewed": int(n_reviewed),
        "review_progress": min(100, round(100 * n_reviewed / action_n)) if action_n else 0,
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", html.escape(str(value), quote=True))
    data = {"summary": summary, "n_reviewed": int(n_reviewed), "rows": json.loads(final.to_json(orient="records", force_ascii=False)),
            "decision": {"status": decision.status, "reason_code": decision.reason_code}}
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    path.write_text(template.replace("{{payload}}", payload), encoding="utf-8")
