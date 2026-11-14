"""Self-contained rendering and escaping regression checks for T08 dashboard."""
import json
import re

import pandas as pd

from src.common.decision import Decision
from src.t08.dashboard import render_dashboard


def test_dashboard_embeds_css_and_escapes_data(tmp_path):
    summary = {"mode": "dry_run", "owner": '<script>alert("owner")</script>',
               "n_requests": 1, "n_actions": 128, "n_unique_artefacts": 128,
               "action_counts": {"delete": 128}, "execution_counts": {"pending_approval": 128},
               "requests": []}
    final = pd.DataFrame([{"request_id": "DR-001", "reason": "</script><img src=x>"}])
    path = tmp_path / "dashboard.html"
    render_dashboard(summary, final, Decision("HOLD", "DRY_RUN_ONLY", "dry", "test"), path)
    text = path.read_text(encoding="utf-8")
    assert "<style>" in text and 'name="viewport"' in text
    assert "ĐÃ XÓA MÔ PHỎNG" in text
    assert '<div class="number">0</div>' in text
    assert '<div class="number">128</div>' in text
    assert "<script>alert" not in text and "</script><img" not in text
    assert "&lt;script&gt;" in text
    assert "{{payload}}" not in text and "{{owner}}" not in text
    assert not re.search(r'(?:href|src)=["\']https?://', text)
    payload = re.search(r'<script id="run-data" type="application/json">(.*?)</script>', text, re.S).group(1)
    assert json.loads(payload)["rows"][0]["reason"] == "</script><img src=x>"


def test_dashboard_zero_actions(tmp_path):
    path = tmp_path / "dashboard.html"
    render_dashboard({"requests": [], "action_counts": {}, "execution_counts": {}},
                     pd.DataFrame(), Decision("HOLD", "REQUEST_SCOPE_NOT_FOUND", "empty", "test"), path)
    text = path.read_text(encoding="utf-8")
    assert 'aria-valuenow="0"' in text
    assert "Có yêu cầu chưa xác định" in text
    assert "{{" not in text
