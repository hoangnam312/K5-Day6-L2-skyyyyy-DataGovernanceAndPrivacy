"""Vinh: quy tắc local rõ ràng, giữ nguyên trước khi xem GT."""
ACTIONS = {"delete", "retain_legal_hold", "escalate"}
POLICY_VERSION = "t08-local-v1"


def propose_action(request: dict, artefact: dict, actor: str) -> dict:
    row = {
        "item_id": request["request_id"] + "::" + artefact["artefact_id"],
        "request_id": request["request_id"], "artefact_id": artefact["artefact_id"],
        "subject_id": request["subject_id"], "artefact_type": artefact["type"],
        "deadline": request["deadline"], "uri": artefact["uri"],
        "evidence_path": " -> ".join(artefact.get("_evidence_path", [artefact["artefact_id"]])),
        "policy_version": POLICY_VERSION,
    }
    # Các hold ID không có thời hạn trong fixture được xem đang hiệu lực.
    # Không tự truyền hold từ raw sang mọi bản dẫn xuất: đây là giả định local,
    # được ghi rõ trong hướng dẫn và phải hỏi domain owner trước triển khai thật.
    if artefact.get("legal_hold"):
        action, code, score = "retain_legal_hold", "LEGAL_HOLD", 100
    elif not request["identity_verified"]:
        action, code, score = "escalate", "IDENTITY_UNVERIFIED", 99
    elif actor not in artefact["acl"]:
        action, code, score = "escalate", "NO_PERMISSION", 98
    elif not artefact["origin_known"]:
        action, code, score = "escalate", "UNKNOWN_ORIGIN", 97
    elif artefact.get("_missing_parents"):
        action, code, score = "escalate", "MISSING_PARENT", 96
    elif artefact.get("_scope_inferred") or request["subject_id"] not in artefact["subject_ids"]:
        action, code, score = "escalate", "SUBJECT_UNCONFIRMED", 95
    elif len(set(artefact["subject_ids"])) > 1:
        action, code, score = "escalate", "MULTI_SUBJECT", 94
    else:
        action, code, score = "delete", "SINGLE_SUBJECT_AUTHORIZED", 10
    row.update(action=action, proposed_action=action, reason_code=code, reason=code,
               score=float(score), needs_review=True, execution_approved=False,
               reviewer="", review_status="pending")
    return row
