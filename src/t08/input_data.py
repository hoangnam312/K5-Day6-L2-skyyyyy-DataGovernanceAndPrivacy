"""Đọc và kiểm tra cấu trúc input; không bao giờ đọc GT."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def load_input(input_dir: Path) -> dict:
    requests = json.loads((input_dir / "requests.json").read_text(encoding="utf-8"))
    graph = json.loads((input_dir / "data_graph.json").read_text(encoding="utf-8"))
    if not isinstance(graph, dict) or not isinstance(graph.get("artefacts"), list):
        raise ValueError("data_graph.json needs an artefacts list")
    artefacts = graph["artefacts"]
    for name, rows, key in (("requests", requests, "request_id"), ("artefacts", artefacts, "artefact_id")):
        if not isinstance(rows, list):
            raise ValueError(f"{name} must be a list")
        ids = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{name}: missing {key}")
            if "::" in row[key]:
                raise ValueError(f"{key} must not contain the composite ID separator ::")
            ids.append(row[key])
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {key}")
    for req in requests:
        if not isinstance(req.get("subject_id"), str) or not req["subject_id"]:
            raise ValueError("Request needs subject_id")
        if not isinstance(req.get("identity_verified"), bool):
            raise ValueError("identity_verified must be boolean")
        dates = []
        for key in ("received_at", "deadline"):
            try:
                dt = datetime.fromisoformat(req[key])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid {key} for {req['request_id']}") from exc
            if dt.tzinfo is None:
                raise ValueError(f"{key} must include timezone")
            dates.append(dt)
        if dates[1] < dates[0]:
            raise ValueError("deadline cannot precede received_at")
    ids = {a["artefact_id"] for a in artefacts}
    for art in artefacts:
        for key in ("subject_ids", "parent_ids", "acl"):
            values = art.get(key)
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise ValueError(f"{art['artefact_id']}: {key} must be a list of nonempty strings")
        if not isinstance(art.get("origin_known"), bool):
            raise ValueError("origin_known must be boolean")
        if not isinstance(art.get("type"), str) or not isinstance(art.get("owner"), str):
            raise ValueError("Artefact needs type and owner")
        if not isinstance(art.get("uri"), str) or not art["uri"].startswith("mock://"):
            raise ValueError("This simulator accepts mock:// URIs only")
        hold = art.get("legal_hold")
        if hold is not None and not isinstance(hold, (str, bool)):
            raise ValueError("legal_hold must be null, boolean or a hold reference")
        # Không bịa parent bị thiếu. Ghi vấn đề để policy chuyển người xử lý.
        art["_missing_parents"] = sorted(set(art["parent_ids"]) - ids)
    # Tách hash dữ liệu khỏi các trường dẫn xuất dùng cho thuật toán.
    clean = [{k: v for k, v in a.items() if not k.startswith("_")} for a in artefacts]
    return {"requests": requests, "artefacts": artefacts,
            "input_hash": fingerprint({"requests": requests, "artefacts": clean})}
