# T08 — Chạy bản đã tích hợp

Code nguồn các bạn đã lên origin/main; phần tích hợp được thực hiện trên
branch integration/t08-demo. Owner/group giữ theo config mới nhất của nhóm:
Dương Quốc Anh / skyyyy. Các module có hỗ trợ AI; mỗi bạn cần giải thích được
phần mình nhận và chỉ ghi bằng chứng đóng góp thực tế.

## Môi trường

Terminal tại thư mục gốc repo. Mỗi máy tự tạo .venv và cài requirements.txt
một lần; demo chạy offline sau khi cài. Starter khuyến nghị Python 3.11–3.13.

~~~powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

## Baseline → PoC → người duyệt → mock execute

~~~powershell
.\.venv\Scripts\python.exe -m src.main --pipeline src.t08_baseline --output out/baseline --run-name baseline --offline --seed 42
.\.venv\Scripts\python.exe -m src.main --offline --seed 42
~~~

Mở out/poc/dashboard.html và out/poc/review.html. Nhập tên người thực sự duyệt,
xem các đề xuất, chọn quyết định và xuất review_queue_reviewed.csv. Chép đúng
tên file vào out/poc/review_queue_reviewed.csv. edit/reject cần override và note.
Hold/thiếu quyền/ngoại lệ khác không được chuyển thành delete chỉ bằng override.

~~~powershell
# Áp review nhưng vẫn dry-run:
.\.venv\Scripts\python.exe -m src.main --offline --seed 42
# Thực hiện mock sau khi đã duyệt:
.\.venv\Scripts\python.exe -m src.main --config configs/t08_execute.yaml --offline --seed 42
# Chạy lại để đối chiếu already_deleted / không tăng tác động:
.\.venv\Scripts\python.exe -m src.main --config configs/t08_execute.yaml --offline --seed 42
~~~

status=0 nghĩa là chương trình chạy xong; HOLD vì dry-run, chờ duyệt hoặc
ngoại lệ là kết quả hợp lệ. Xem execution_evidence.csv thay vì suy ra đã xóa
từ cột action. Chỉ mock_state.json thay đổi; không có file dữ liệu thật bị xóa.

CSV duyệt có plan_hash để phát hiện input/actor/policy cũ. Khi thay rule phải
tăng POLICY_VERSION rồi duyệt lại. Dùng đúng cùng output cho vòng review/execute.

## Test và đánh giá

~~~powershell
.\.venv\Scripts\python.exe -m pytest -o addopts= -q -ra
.\.venv\Scripts\python.exe -X utf8 tools/run_t08_selfcheck.py
~~~

Self-check dùng ví dụ phát triển viết tay: 2 request, 9 artefact, 10 expected
action pairs. Kết quả nằm reports/demo_metrics_*.json và demo_baseline_vs_poc.md.
Không phải điểm trên fixture lớp hay hidden eval. Chính thức cần overlay GT
giảng viên và các lệnh src.evaluate / src.compare trong README starter.

## Theo dõi module đã ghép

- Núi: src/t08/lineage.py từ ba8345d.
- Vinh: src/t08/policy.py từ 3232046.
- Anh: review từ fba74cc, sửa vị trí file trong lượt tích hợp.
- Nam: executor và development tests từ 9157ef2 (đã merge vào main).
- Phần tích hợp: loader/input hash, nối pipeline, baseline và execute config.

Giả định: legal_hold áp local, ID không rỗng xem đang hiệu lực; không tự kế thừa
hold sang mọi descendant. Dữ liệu nhiều subject/nguồn chưa rõ/thiếu quyền hoặc
scope suy diễn cần escalate. Actor=data-platform khác owner người ký duyệt.
