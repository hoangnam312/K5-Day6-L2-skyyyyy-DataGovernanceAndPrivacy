"""Anh: CSV/HTML offline, quyết định người thật và kiểm override."""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd
from ..common.context import RunContext
from ..common.review import make_review_queue, write_review_queue, load_review_decisions
from .policy import ACTIONS


def build_queue(ctx: RunContext, proposed: pd.DataFrame) -> pd.DataFrame:
    queue = make_review_queue(proposed, id_col="item_id", score_col="score",
                              budget=len(proposed), reason_col="reason_code",
                              action_col="action", evidence_col="evidence_path")
    queue["plan_hash"] = ctx.stats["plan_hash"]
    write_review_queue(queue, ctx.out("review_queue.csv"))
    render_review_html(queue, ctx.out("review.html"))
    return queue


def render_review_html(queue: pd.DataFrame, path: Path) -> None:
    payload = queue.fillna("").to_json(orient="records", force_ascii=False).replace("<", "\\u003c")
    headers = json.dumps(list(queue.columns))
    template = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>T08 — Cổng Duyệt Kế Hoạch Xóa Dữ Liệu (Human Review Portal)</title>
<style>
:root {
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #64748b;
  --danger: #ef4444;
  --danger-bg: #fef2f2;
  --danger-border: #fecaca;
  --warning: #f59e0b;
  --warning-bg: #fffbeb;
  --warning-border: #fde68a;
  --success: #10b981;
  --success-bg: #ecfdf5;
  --success-border: #a7f3d0;
  --radius: 10px;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  margin: 0;
  padding: 24px 32px;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid var(--border);
  padding-bottom: 16px;
  margin-bottom: 24px;
}
.header h1 {
  margin: 0;
  font-size: 24px;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header .badge-tag {
  font-size: 13px;
  background: #e0e7ff;
  color: #3730a3;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 600;
}
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.card.card-hold { border-left: 5px solid var(--danger); }
.card.card-escalate { border-left: 5px solid var(--warning); }
.card.card-delete { border-left: 5px solid var(--success); }
.card .title { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; }
.card .num { font-size: 28px; font-weight: 700; margin: 4px 0; color: var(--text); }
.card .desc { font-size: 12px; color: var(--muted); }

.control-panel {
  position: sticky;
  top: 12px;
  z-index: 100;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.control-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.reviewer-box {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 14px;
}
.reviewer-box input {
  padding: 8px 14px;
  border: 2px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  min-width: 220px;
}
.reviewer-box input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
}
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn {
  font-weight: 600;
  font-size: 13px;
  padding: 9px 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
}
.btn-primary { background: var(--primary); color: #fff; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-danger { background: var(--danger-bg); color: var(--danger); border-color: var(--danger-border); }
.btn-danger:hover { background: #fee2e2; }
.btn-warning { background: var(--warning-bg); color: #b45309; border-color: var(--warning-border); }
.btn-warning:hover { background: #fef3c7; }
.btn-success { background: var(--success-bg); color: #065f46; border-color: var(--success-border); }
.btn-success:hover { background: #d1fae5; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid var(--border);
  padding-bottom: 8px;
  overflow-x: auto;
}
.tab {
  background: transparent;
  border: none;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  border-radius: 6px;
  cursor: pointer;
}
.tab.active {
  background: #e2e8f0;
  color: var(--text);
}
.search-box {
  width: 100%;
  max-width: 350px;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
}

.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: auto;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 1000px;
}
th {
  background: #f1f5f9;
  color: #475569;
  font-weight: 700;
  padding: 12px 14px;
  text-align: left;
  border-bottom: 2px solid var(--border);
  font-size: 12px;
  letter-spacing: 0.5px;
}
td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
tr:hover { background: #f8fafc; }

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.badge-hold { background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger-border); }
.badge-escalate { background: var(--warning-bg); color: #b45309; border: 1px solid var(--warning-border); }
.badge-delete { background: var(--success-bg); color: #047857; border: 1px solid var(--success-border); }

.reason-detail {
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
}
.item-code {
  font-family: ui-monospace, Consolas, monospace;
  font-weight: 700;
  color: #3b82f6;
}
select.action-select {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1.5px solid #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  background: #fff;
  cursor: pointer;
}
select.action-select:focus { border-color: var(--primary); outline: none; }
input.note-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 12px;
}
.status-bar {
  font-size: 13px;
  font-weight: 600;
  color: #059669;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🛡️ Cổng Thẩm Định Xóa Dữ Liệu T08 <span class="badge-tag">Human-In-The-Loop</span></h1>
    <p style="margin: 4px 0 0; color: var(--muted); font-size: 13px;">
      Quy trình kiểm soát theo luật GDPR & Nghị định Bảo vệ dữ liệu. AI gợi ý, con người phê duyệt trước khi thực thi.
    </p>
  </div>
  <a href="dashboard.html" style="font-size: 13px; font-weight: 600; color: var(--primary); text-decoration: none;">← Về Dashboard</a>
</div>

<!-- 3 THẺ TỔNG QUAN -->
<div class="stats-cards">
  <div class="card card-hold" onclick="setTab('hold')">
    <div class="title">Niêm phong chứng cứ (Legal Hold)</div>
    <div class="num" id="count-hold">0</div>
    <div class="desc">Bắt buộc giữ lại phục vụ cơ quan pháp luật</div>
  </div>
  <div class="card card-escalate" onclick="setTab('escalate')">
    <div class="title">Chuyển xử lý (Escalate)</div>
    <div class="num" id="count-escalate">0</div>
    <div class="desc">Nhiều chủ thể, nguồn gốc mờ ám hoặc thiếu quyền</div>
  </div>
  <div class="card card-delete" onclick="setTab('delete')">
    <div class="title">Đề xuất xóa an toàn</div>
    <div class="num" id="count-delete">0</div>
    <div class="desc">Một chủ thể duy nhất, đủ quyền xóa</div>
  </div>
</div>

<!-- THANH ĐIỀU KHIỂN & BỘ LỌC -->
<div class="control-panel">
  <div class="control-row">
    <div class="reviewer-box">
      <span>👤 Người duyệt:</span>
      <input type="text" id="who" value="Lê Văn Khởi" placeholder="Nhập tên người thẩm định...">
    </div>
    <div class="action-buttons">
      <button class="btn btn-danger" onclick="approveCategory('retain_legal_hold')">🛡️ Xác nhận giữ 2 ca Legal Hold</button>
      <button class="btn btn-warning" onclick="approveCategory('escalate')">⚠️ Duyệt chuyển 28 ca Escalate</button>
      <button class="btn btn-success" onclick="approveCategory('delete')">⚡ Duyệt 128 ca Xóa an toàn</button>
      <button class="btn btn-primary" id="export" style="font-size: 14px; padding: 10px 20px;">💾 Xuất file CSV nộp</button>
    </div>
  </div>

  <div class="control-row">
    <div class="tabs">
      <button class="tab active" data-tab="all" onclick="setTab('all')">Tất cả (158)</button>
      <button class="tab" data-tab="hold" onclick="setTab('hold')">🔴 Niêm phong (2)</button>
      <button class="tab" data-tab="escalate" onclick="setTab('escalate')">🟡 Chuyển xử lý (28)</button>
      <button class="tab" data-tab="delete" onclick="setTab('delete')">🟢 Xóa an toàn (128)</button>
      <button class="tab" data-tab="pending" onclick="setTab('pending')">⏳ Chưa chọn quyết định</button>
      <button class="tab" data-tab="approved" onclick="setTab('approved')">✅ Đã duyệt</button>
    </div>
    <input type="search" class="search-box" id="search" placeholder="🔍 Tìm theo mã request, artefact hoặc lý do...">
  </div>

  <div class="control-row" style="margin-top: 4px;">
    <div class="status-bar" id="statusBar">
      Đang hiển thị: 158 / 158 dòng | Đã duyệt: 0 dòng
    </div>
  </div>
</div>

<!-- BẢNG DANH SÁCH -->
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th style="width: 140px;">Mã yêu cầu & File</th>
        <th style="width: 250px;">Đề xuất AI & Lý do pháp lý</th>
        <th style="width: 180px;">Bằng chứng Lineage</th>
        <th style="width: 180px;">Quyết định của bạn</th>
        <th style="width: 160px;">Override (Nếu sửa)</th>
        <th>Ghi chú thẩm định</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
</div>

<script>
const data = __DATA__;
const headers = __HEADERS__;

const reasonExplanations = {
  LEGAL_HOLD: "Lệnh công an/tòa án niêm phong chứng cứ vụ án (Bắt buộc giữ lại)",
  NO_PERMISSION: "Hệ thống không có quyền tác vụ trên file này (Chuyển quản trị)",
  UNKNOWN_ORIGIN: "Nguồn gốc file không xác định, có nguy cơ tranh chấp (Chuyển pháp chế)",
  MULTI_SUBJECT: "File chứa mặt của nhiều người, không được tự xóa (Chuyển xử lý)",
  SUBJECT_UNCONFIRMED: "Chưa xác minh chắc chắn danh tính chủ thể trong file",
  MISSING_PARENT: "File bị đứt gãy phả hệ cha-con (Cần kỹ sư rà soát)",
  IDENTITY_UNVERIFIED: "Yêu cầu xóa từ app chưa qua xác thực CCCD/Passport",
  SINGLE_SUBJECT_AUTHORIZED: "Một chủ thể duy nhất, hợp pháp 100% để xóa"
};

let currentTab = 'all';

// Cập nhật số liệu thẻ
document.getElementById('count-hold').textContent = data.filter(r => r.suggested_action === 'retain_legal_hold').length;
document.getElementById('count-escalate').textContent = data.filter(r => r.suggested_action === 'escalate').length;
document.getElementById('count-delete').textContent = data.filter(r => r.suggested_action === 'delete').length;

function setTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tabs .tab').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  renderRows();
}

function matches(r) {
  const q = document.getElementById('search').value.trim().toLowerCase();
  const searchMatch = !q || [r.item_id, r.evidence_path, r.reason, r.suggested_action, reasonExplanations[r.reason]||''].join(' ').toLowerCase().includes(q);
  if (!searchMatch) return false;

  if (currentTab === 'all') return true;
  if (currentTab === 'hold') return r.suggested_action === 'retain_legal_hold';
  if (currentTab === 'escalate') return r.suggested_action === 'escalate';
  if (currentTab === 'delete') return r.suggested_action === 'delete';
  if (currentTab === 'pending') return !r.reviewer_decision;
  if (currentTab === 'approved') return Boolean(r.reviewer_decision);
  return true;
}

function renderRows() {
  const tbody = document.getElementById('rows');
  tbody.innerHTML = '';
  let visible = 0;
  let approvedCount = data.filter(r => r.reviewer_decision).length;

  for (const r of data) {
    if (!matches(r)) continue;
    visible++;

    const tr = document.createElement('tr');

    // Cột 1: ID
    const tdId = document.createElement('td');
    tdId.innerHTML = `<span class="item-code">${r.item_id}</span>`;
    tr.append(tdId);

    // Cột 2: Đề xuất & Lý do
    const tdReason = document.createElement('td');
    let badgeClass = 'badge-delete';
    let badgeText = '🟢 Xóa an toàn';
    if (r.suggested_action === 'retain_legal_hold') {
      badgeClass = 'badge-hold';
      badgeText = '🔴 Niêm phong (Hold)';
    } else if (r.suggested_action === 'escalate') {
      badgeClass = 'badge-escalate';
      badgeText = '🟡 Chuyển xử lý';
    }
    const explanation = reasonExplanations[r.reason] || r.reason;
    tdReason.innerHTML = `
      <span class="badge ${badgeClass}">${badgeText}</span>
      <strong style="display:block; margin-top:4px; font-size:12px;">${r.reason}</strong>
      <div class="reason-detail">${explanation}</div>
    `;
    tr.append(tdReason);

    // Cột 3: Evidence
    const tdEvidence = document.createElement('td');
    tdEvidence.innerHTML = `<code style="font-size:11px; color:#475569;">${r.evidence_path}</code>`;
    tr.append(tdEvidence);

    // Cột 4: Quyết định
    const tdDec = document.createElement('td');
    const select = document.createElement('select');
    select.className = 'action-select';
    const opts = [
      ['', '(Chưa chọn quyết định)'],
      ['approve', '✅ Approve (Đồng ý với AI)'],
      ['reject', '❌ Reject (Từ chối)'],
      ['edit', '✏️ Edit (Đổi quyết định)'],
      ['escalate', '⚠️ Escalate (Chuyển tiếp)'],
      ['skip', '⏭️ Skip (Bỏ qua)']
    ];
    for (const [val, text] of opts) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = text;
      select.append(opt);
    }
    select.value = r.reviewer_decision || '';
    select.onchange = () => {
      r.reviewer_decision = select.value;
      updateStatusBar();
    };
    tdDec.append(select);
    tr.append(tdDec);

    // Cột 5: Override
    const tdOver = document.createElement('td');
    const overSelect = document.createElement('select');
    overSelect.className = 'action-select';
    const overOpts = [
      ['', '(Không override)'],
      ['delete', 'delete'],
      ['retain_legal_hold', 'retain_legal_hold'],
      ['escalate', 'escalate']
    ];
    for (const [val, text] of overOpts) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = text;
      overSelect.append(opt);
    }
    overSelect.value = r.override_value || '';
    overSelect.onchange = () => { r.override_value = overSelect.value; };
    tdOver.append(overSelect);
    tr.append(tdOver);

    // Cột 6: Ghi chú
    const tdNote = document.createElement('td');
    const noteInput = document.createElement('input');
    noteInput.className = 'note-input';
    noteInput.placeholder = 'Ghi chú lý do...';
    noteInput.value = r.review_note || '';
    noteInput.oninput = () => { r.review_note = noteInput.value; };
    tdNote.append(noteInput);
    tr.append(tdNote);

    tbody.append(tr);
  }

  document.getElementById('statusBar').textContent = 
    `Đang hiển thị: ${visible} / ${data.length} dòng | Đã duyệt: ${approvedCount} / ${data.length} dòng`;
}

function updateStatusBar() {
  const approvedCount = data.filter(r => r.reviewer_decision).length;
  document.getElementById('statusBar').textContent = 
    `Tổng: ${data.length} dòng | Đã duyệt: ${approvedCount} / ${data.length} dòng`;
}

function approveCategory(category) {
  let count = 0;
  for (const r of data) {
    if (r.suggested_action === category) {
      r.reviewer_decision = 'approve';
      count++;
    }
  }
  renderRows();
  alert(`Đã tự động Approve cho toàn bộ ${count} ca thuộc diện [${category}]!`);
}

document.getElementById('search').addEventListener('input', renderRows);
renderRows();

// XUẤT CSV
const quote = v => '"' + String(v ?? '').replaceAll('"', '""') + '"';
document.getElementById('export').onclick = () => {
  const who = document.getElementById('who').value.trim();
  if (!who) {
    alert('Vui lòng nhập tên người duyệt ở ô "Người duyệt"!');
    return;
  }
  const decided = data.filter(r => r.reviewer_decision);
  if (decided.length === 0) {
    alert('Bạn chưa chọn quyết định cho dòng nào cả! Hãy bấm các nút duyệt nhanh hoặc chọn quyết định.');
    return;
  }
  for (const r of data) {
    if (r.reviewer_decision) {
      r.reviewer = who;
      r.reviewed_at = new Date().toISOString();
    }
  }
  const csv = headers.map(quote).join(',') + '\\r\\n' +
              data.map(r => headers.map(h => quote(r[h])).join(',')).join('\\r\\n');
  const url = URL.createObjectURL(new Blob(['\\ufeff' + csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'review_queue_reviewed.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
  alert(`Xuất file review_queue_reviewed.csv thành công! Hãy copy file này vào thư mục out/poc/`);
};
</script>
</body>
</html>"""
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
