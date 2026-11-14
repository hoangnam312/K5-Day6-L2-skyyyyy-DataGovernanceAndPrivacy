"""Anh: CSV/HTML offline, quyết định người thật và kiểm override."""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd
from ..common.context import RunContext
from ..common.review import make_review_queue, write_review_queue, load_review_decisions
from .policy import ACTIONS


def build_queue(ctx: RunContext, proposed: pd.DataFrame) -> pd.DataFrame:
    # T08 không áp budget top-B bắt buộc như T02: đưa toàn bộ action vào queue.
    # Do đó không có delete bị bỏ khỏi luồng phê duyệt vì hết budget.
    queue = make_review_queue(proposed, id_col="item_id", score_col="score",
                              budget=len(proposed), reason_col="reason_code",
                              action_col="action", evidence_col="evidence_path")
    queue["plan_hash"] = ctx.stats["plan_hash"]
    write_review_queue(queue, ctx.out("review_queue.csv"))
    render_review_html(queue, ctx.out("review.html"))
    return queue


def render_review_html(queue: pd.DataFrame, path: Path) -> None:
    # Escape < để dữ liệu không thể đóng thẻ script; UI dùng textContent.
    payload = queue.fillna("").to_json(orient="records", force_ascii=False).replace("<", "\\u003c")
    headers = json.dumps(list(queue.columns))
    template = """<!doctype html><html lang="vi"><meta charset="utf-8">
<title>T08 — Human review</title><style>
body{font:15px system-ui;margin:24px;background:#f5f7fa;color:#182231}
table{border-collapse:collapse;background:white;width:100%}td,th{border:1px solid #ccd4df;padding:8px;text-align:left}
thead{position:sticky;top:0;background:#e0eafa}input,select,button{padding:7px;margin:4px}
.top{position:sticky;top:0;background:#f5f7fa;padding:10px;border-bottom:2px solid #667}
</style><h1>T08 — Duyệt kế hoạch xóa mô phỏng</h1>
<p>Chưa có dữ liệu thật bị xóa. Chọn quyết định, nhập tên và xuất CSV.
Approve giữ hành động đề xuất; edit/reject cần override và ghi chú.
Policy chặn xóa không được vượt qua bằng CSV.</p>
<div class="top"><label>Người duyệt <input id="who" placeholder="Tên người thực sự duyệt"></label>
<button id="approve">Approve tất cả delete an toàn</button>
<button id="export">Xuất review_queue_reviewed.csv</button>
<span id="status"></span></div><table><thead><tr>
<th>ID</th><th>Đề xuất / lý do</th><th>Evidence</th><th>Quyết định</th><th>Override</th><th>Ghi chú</th>
</tr></thead><tbody id="rows"></tbody></table><script>
const data=__DATA__, headers=__HEADERS__;
function select(options,value){let s=document.createElement('select');for(let v of options){
let o=document.createElement('option');o.value=v;o.textContent=v||'(chưa chọn)';s.append(o)}s.value=value||'';return s}
for(const r of data){const tr=document.createElement('tr');
for(const value of [r.item_id,r.suggested_action+' / '+r.reason,r.evidence_path]){
let td=document.createElement('td');td.textContent=value;tr.append(td)}
let d=select(['','approve','reject','edit','escalate','skip'],r.reviewer_decision);
d.onchange=()=>r.reviewer_decision=d.value;r.control=d;
let o=select(['','delete','retain_legal_hold','escalate'],r.override_value);
o.onchange=()=>r.override_value=o.value;
let n=document.createElement('input');n.value=r.review_note;n.oninput=()=>r.review_note=n.value;
for(const x of [d,o,n]){let td=document.createElement('td');td.append(x);tr.append(td)}
document.getElementById('rows').append(tr)}
document.getElementById('approve').onclick=()=>{let n=0;
for(const r of data)if(r.suggested_action==='delete'&&!r.reviewer_decision){
r.reviewer_decision='approve';r.control.value='approve';n++}
document.getElementById('status').textContent='Đã chọn approve cho '+n+' dòng. Kiểm tra trước khi xuất.'};
const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
document.getElementById('export').onclick=()=>{
const who=document.getElementById('who').value.trim();if(!who){alert('Cần tên người duyệt');return}
if(!data.some(r=>r.reviewer_decision)){alert('Chưa có quyết định');return}
for(const r of data){if(r.reviewer_decision){r.reviewer=who;r.reviewed_at=new Date().toISOString()}}
const csv=headers.map(quote).join(',')+'\\r\\n'+data.map(r=>headers.map(h=>quote(r[h])).join(',')).join('\\r\\n');
const url=URL.createObjectURL(new Blob(['\\ufeff'+csv],{type:'text/csv;charset=utf-8'}));
const a=document.createElement('a');a.href=url;a.download='review_queue_reviewed.csv';a.click();
setTimeout(()=>URL.revokeObjectURL(url),2000)};
</script></html>"""
    path.write_text(template.replace("__DATA__", payload).replace("__HEADERS__", headers), encoding="utf-8")


def apply_review(ctx: RunContext, proposed: pd.DataFrame) -> pd.DataFrame:
    final = proposed.copy()
    path = ctx.output_dir / "review_queue_reviewed.csv"
    if not path.exists():
        ctx.stats["n_reviewed"] = 0
        return final
    raw = pd.read_csv(path, dtype=str).fillna("")
    if "item_id" not in raw or "plan_hash" not in raw:
        raise ValueError("Review CSV needs item_id and plan_hash; export from current review.html")
    if raw.item_id.duplicated().any():
        raise ValueError("Duplicate item_id in review CSV")
    if not set(raw.item_id).issubset(set(final.item_id)):
        raise ValueError("Review CSV contains unknown item_id")
    if len(raw) and not (raw.plan_hash == ctx.stats["plan_hash"]).all():
        raise ValueError("Stale review CSV: input/policy/actor changed, review the current plan")
    reviewed = load_review_decisions(path)
    pending_logs = []
    for review in reviewed.itertuples(index=False):
        idx = final.index[final.item_id == review.item_id][0]
        before = final.at[idx, "action"]
        decision = review.reviewer_decision
        value = str(review.override_value).strip().lower()
        if value and value not in ACTIONS:
            raise ValueError(f"Invalid override action: {value}")
        if decision in {"edit", "reject"}:
            if not value or not review.review_note.strip():
                raise ValueError("edit/reject needs override_value and review_note")
            target = value
        elif decision == "escalate":
            target = "escalate"
        else:
            if value:
                raise ValueError("approve/skip must not contain an override_value")
            target = before
        # Bất kỳ người duyệt nào cũng không thể biến hard blocker thành delete.
        if before != "delete" and target == "delete":
            raise ValueError(f"Policy blocks deletion for {review.item_id}; fix evidence through a new plan")
        if before == "retain_legal_hold" and target != before:
            raise ValueError("Cannot override an active legal hold")
        final.at[idx, "action"] = target
        final.at[idx, "reviewer"] = review.reviewer.strip()
        final.at[idx, "review_status"] = decision
        final.at[idx, "execution_approved"] = bool(target == "delete" and decision in {"approve", "edit", "reject"})
        pending_logs.append((review, before, target))
    # Validate toàn bộ CSV trước khi ghi log, tránh log nửa file khi gặp lỗi.
    for review, before, target in pending_logs:
        row = final.loc[final.item_id == review.item_id].iloc[0]
        ctx.audit.log(actor=review.reviewer, action="human_review", item_id=row.artefact_id,
                      before=before, after=target, reason=review.review_note or review.reviewer_decision,
                      request_id=row.request_id, composite_id=row.item_id, plan_hash=ctx.stats["plan_hash"])
    ctx.stats["n_reviewed"] = len(reviewed)
    return final

