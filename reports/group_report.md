# Group Report — Day 06 Data Lab (Field-to-Release PoC)

## 00 · Header

| Mục | Giá trị |
|---|---|
| Group ID | skyyyyy |
| Challenge | T08 · Retention & Delete Request Simulator |
| Thành viên (5) + vai trò | 1. Lê Văn Khởi (Lead / Pipeline Integration / Loader / Baseline)<br>2. Núi (Lineage Traversal BFS Algorithm)<br>3. Vinh (Policy Precedence & Legal Exception Engine)<br>4. Anh (Human Review Portal UI & Overrides Verification)<br>5. Nam (Mock Executor / State Management / Idempotency / Audit Log) |
| Git URL | https://github.com/hoangnam312/K5-Day6-L2-skyyyyy |
| Tag `demo-180m` (commit) | demo-180m |
| Tag `final-24h` (commit) | final-24h |
| Deadline (giờ VN) | 2026-11-15 17:00 |

---

## 01 · Problem statement

- **Ai bị ảnh hưởng / ai chịu hậu quả khi hệ thống sai?**:
  - *Chủ thể dữ liệu (Data Subjects / Khách hàng)*: Nếu hệ thống không xóa sạch, dữ liệu cá nhân (khuôn mặt, hành trình xe, vector embedding) vẫn bị lưu trữ trái phép, vi phạm quyền riêng tư nghiêm trọng theo GDPR (Điều 17) và Nghị định 13/2023/NĐ-CP của Việt Nam.
  - *Doanh nghiệp vận hành AI*: Chịu mức phạt tài chính khổng lồ (lên tới 4% doanh thu toàn cầu theo GDPR) nếu vi phạm quyền xóa. Ngược lại, nếu doanh nghiệp cắm đầu xóa nhầm dữ liệu đang bị phong tỏa pháp lý (`legal_hold`), doanh nghiệp và kỹ sư sẽ chịu trách nhiệm hình sự về tội tiêu hủy chứng cứ tư pháp.
- **Điểm nghẽn cụ thể**: 
  - Video gốc (`raw_video`) đã bị phân rã và lan truyền sâu vào hệ sinh thái dữ liệu: sinh ra khung ảnh (`frames`), ảnh cắt mặt (`face_crop`), vector số AI (`embeddings`), bản lưu trữ lạnh (`backup`), và các tệp xuất huấn luyện mô hình (`training_export`).
  - Xóa thủ công ở mức tệp đơn lẻ (file-level) chắc chắn bỏ sót dữ liệu phái sinh (Data Lineage Leakage).
- **Đầu vào → Đầu ra**:
  - *Đầu vào*: `requests.json` (10 yêu cầu xóa kèm danh tính, deadline) + `data_graph.json` (212 món dữ liệu thô với liên kết cha-con, quyền ACL, cờ legal hold).
  - *Đầu ra*: `actions.csv` (danh sách hành động cho từng cặp request-artefact), `execution_evidence.csv` (bằng chứng thực thi có kiểm toán), `audit_log.jsonl` (nhật ký append-only), và `decision.json` (quyết định GO/HOLD của Lead).
- **Tiêu chí GO / HOLD / REWORK (chốt trước khi chạy eval)**:
  - `HOLD: DRY_RUN_ONLY`: Khi hệ thống chạy ở chế độ lập kế hoạch thử nghiệm, chưa có phê duyệt từ con người.
  - `HOLD: EXCEPTIONS_REQUIRE_FOLLOW_UP`: Khi đã thực thi xong các ca xóa an toàn, nhưng vẫn còn các ngoại lệ pháp lý (`retain_legal_hold`, `escalate`) cần chuyên viên theo dõi tiếp.
  - `HOLD: REQUEST_SCOPE_NOT_FOUND`: Khi có yêu cầu xóa nhưng không tìm thấy dữ liệu liên quan.
  - `GO: MOCK_ACTIONS_COMPLETE`: Chỉ khi 100% dữ liệu yêu cầu xóa đã được xử lý triệt để và không còn ngoại lệ tồn đọng.
- **Giả định của nhóm**:
  - Lệnh phong tỏa `legal_hold` tại một node cục bộ có hiệu lực tuyệt đối và không tự động xóa nhầm.
  - Dữ liệu có nhiều hơn một chủ thể (`len(subject_ids) > 1`) hoặc không rõ xuất xứ (`origin_known == False`) bắt buộc phải gán `escalate` để xin chỉ đạo, không được tự ý xóa bỏ làm mất dữ liệu của bên thứ ba.

---

## 02 · Data & provenance

| Split / File | N | Nguồn / link | License | Synthetic / Mock? |
|---|---|---|---|---|
| `requests.json` | 10 requests | Fixture ban tổ chức (`DR-001` .. `DR-010`) | Proprietary Lab | Mock |
| `data_graph.json` | 212 artefacts | Fixture ban tổ chức (212 nodes) | Proprietary Lab | Mock |
| `manifest.csv` | 2 records | Fixture ban tổ chức (SHA-256 hashes) | Proprietary Lab | Verification |

- **Schema & class mapping**: 
  - 7 loại artefact trong đồ thị: `raw_video` (10), `backup` (10), `frame` (33), `annotation` (33), `face_crop` (30), `embedding` (30), `training_export` (12).
  - 3 hành động chính thức: `delete` (xóa an toàn), `retain_legal_hold` (giữ lại do án tòa niêm phong), `escalate` (chuyển cấp trên giải quyết rủi ro).
- **Seed: 42** · Giao thức kiểm tra SHA-256 qua `verify_manifest()`.
- **`manifest.csv` verified**: Đã kiểm tra tính toàn vẹn 100% bằng lệnh chuẩn; nghiêm cấm chỉnh sửa fixtures để qua mặt hệ thống kiểm tra hash.
- **Dữ liệu thật**: Theo quy định đề bài T08, dữ liệu thực tế không bị xóa trong bài lab để bảo toàn hệ thống.

---

## 03 · Research & design

- **Tài liệu tham khảo & Căn cứ kỹ thuật**:
  1. *GDPR Article 17 ("Right to be Forgotten")* & *Nghị định 13/2023/NĐ-CP*: Căn cứ pháp lý về quyền yêu cầu xóa dữ liệu và các trường hợp miễn trừ nghĩa vụ xóa (Điều 17(3) GDPR - Legal obligations/Legal claims).
  2. *Data Lineage Graph & Provenance Architecture (IEEE/ACM Data Governance Standards)*: Duyệt quan hệ cha-con bảo đảm tính toàn vẹn phả hệ dữ liệu.
  3. *Idempotency in Distributed Storage Systems*: Thiết kế mock state bảo đảm chạy nhiều lần không gây lỗi trùng lặp.
- **Sơ đồ Data Flow**:
  ```
  [1. LOAD] ──(requests.json + data_graph.json + verify manifest)
     │
     ▼
  [2. LINEAGE BFS] ──(Duyệt đồ thị cha-con tìm 100% con cháu liên quan subject_id)
     │
     ▼
  [3. POLICY PRECEDENCE] ──(Bộ lọc 8 tầng: Legal Hold > ACL/Origin > Multi-Subject > Delete)
     │
     ▼
  [4. HUMAN REVIEW] ──(Cổng review.html cho chuyên viên DPO duyệt bằng mắt + xuất CSV)
     │
     ▼
  [5. MOCK EXECUTOR] ──(Thực thi xóa mô phỏng vào mock_state.json + chống chạy lặp)
     │
     ▼
  [6. DECIDE & AUDIT] ──(Xuất actions.csv, audit_log.jsonl, decision.json)
  ```
- **Thành phần offline**: Thuần Python standard library + Pandas. Không gọi mạng ngoài (offline 100%).
- **Trade-offs đã cân nhắc**:
  - *Trade-off 1 (Tốc độ vs Toàn vẹn)*: Duyệt BFS toàn đồ thị tốn thời gian hơn tìm kiếm theo tên, nhưng đảm bảo Deletion Completeness đạt 100% thay vì 50% như Baseline.
  - *Trade-off 2 (Tự động hóa vs Pháp lý an toàn)*: Tự động hóa xóa 100% sẽ gây tai họa khi gặp Legal Hold; nhóm chấp nhận giữ lại cổng Human Review trên Web để con người ký duyệt các ca rủi ro.

---

## 04 · Baseline vs PoC

- **Baseline**: Script `src/t08_baseline.py` — mô phỏng cách làm ngây thơ của kỹ sư mới: chỉ tìm một file video gốc thô (`raw_video`) theo tên file rồi xóa, hoàn toàn bỏ qua các bản sao lưu, khung hình, vector embedding và không kiểm tra lệnh niêm phong Legal Hold.
- **PoC của nhóm**: Dây chuyền tự động hóa 5 bước kết hợp thuật toán BFS duyệt phả hệ đầy đủ + bộ lọc luật ưu tiên 8 tầng + cổng thẩm định người thật và sổ cái ghi vết kiểm toán.
- **Cùng điều kiện kiểm thử**: Cùng bộ dữ liệu, cùng seed 42, cùng protocol đánh giá khách quan.

### Bảng 1 · Baseline vs PoC (Đo lường định lượng trên bộ mẫu kiểm chuẩn T08)

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Đánh giá |
|---|---|---|---|---|---|---|
| **Deletion Completeness** [PRIMARY] | all | 0.5000 | **1.0000** | +0.5000 | **+100.0%** | PoC vượt trội hoàn toàn |
| **False-delete count** (target 0) | all | 0.0000 | **0.0000** | 0.0000 | baseline=0 | Tuyệt đối an toàn (0 lỗi) |
| **Exception handling accuracy** | all | 0.0000 | **1.0000** | +1.0000 | **+100.0%** | Bắt đúng 100% ngoại lệ |
| **Audit trace completeness** | all | 1.0000 | **1.0000** | 0.0000 | +0.0% | Ghi log 100% minh bạch |
| **Runtime / 100 items (giây)** | all | 0.9650s | **0.6800s** | -0.2850s | -29.5% | PoC tối ưu tốc độ hơn |

---

## 05 · Evaluation protocol

- **Công thức Primary Metric**:
  $$\text{Deletion Completeness} = \frac{\text{Số artefact bắt buộc xóa đã được xóa}}{\text{Tổng số artefact bắt buộc phải xóa trong phạm vi}}$$
- **False-delete count**: Tổng số lần xóa nhầm dữ liệu đang bị Legal Hold + số lần xóa dữ liệu không thuộc phạm vi yêu cầu (Mục tiêu = 0).
- **Exception handling accuracy**: Tỷ lệ các dòng chứa ngoại lệ pháp lý (`retain_legal_hold`, `escalate`) được xử lý chuẩn xác theo kỳ vọng.
- **Lệnh đánh giá chính thức**:
  ```bash
  python -m src.evaluate --track t08 --pred out/poc/actions.csv
  ```

---

## 06 · Result slices & Phân tích Failure Cases

### Thống kê thực tế trên 10 yêu cầu lớp học:
- Tổng số quyết định xử lý: **158 hành động** trên 144 artefact riêng biệt.
- Phân loại hành động:
  - `delete`: **128 món** (Đã xóa mô phỏng an toàn sau khi được người thẩm định phê duyệt).
  - `escalate`: **28 món** (Chuyển xử lý cấp trên).
  - `retain_legal_hold`: **2 món** (Niêm phong làm chứng cứ).

### Phân tích 3 Failure Cases điển hình bắt buộc:
1. **Failure Case 1 — Lineage Leak (Rò rỉ phả hệ ở Baseline)**:
   - *Hiện tượng*: Baseline chỉ xóa file gốc `a0015` (`raw_video`).
   - *Hậu quả*: Toàn bộ khung hình `a0017`, khuôn mặt cắt `a0018`, vector embedding AI `a0019` và bản backup `a0016` vẫn còn nguyên vẹn trong hệ thống. Doanh nghiệp vi phạm quyền riêng tư nghiêm trọng.
   - *Khắc phục trong PoC*: Dùng BFS truy vết triệt để qua quan hệ `parent_ids`, xóa sạch toàn bộ cây con cháu.
2. **Failure Case 2 — Vi phạm lệnh phong tỏa tư pháp (Legal Hold Breach)**:
   - *Hiện tượng*: Request `DR-002` yêu cầu xóa dữ liệu của `subj_03`, nhưng file video gốc `a0043` đang mang mã `legal_hold: LH-2026-03` do tòa án yêu cầu điều tra tai nạn.
   - *Khắc phục trong PoC*: Quy tắc Precedence đặt `legal_hold` lên vị trí số 1 (tối thượng). Dữ liệu này bị chặn xóa ngay lập tức và gán nhãn `retain_legal_hold`.
3. **Failure Case 3 — Xóa nhầm dữ liệu đa chủ thể (Multi-Subject Collateral Damage)**:
   - *Hiện tượng*: Tệp xuất huấn luyện `a0212` (`training_export`) chứa dữ liệu của 9 chủ thể khác nhau (`subj_00` đến `subj_13`). Khi ông `subj_01` yêu cầu xóa, nếu xóa sổ file `a0212` sẽ phá hủy tập train của 8 người vô can khác.
   - *Khắc phục trong PoC*: Phát hiện `len(subject_ids) > 1` ➔ tự động chuyển sang diện `escalate` để chuyên viên tách dữ liệu hoặc ẩn danh hóa.

---

## 07 · Human & decision

- **Review Queue & Giao diện Web (`review.html`)**:
  - Tự động sinh cổng thẩm định người thật với 3 thẻ tổng quan phân màu: Đỏ (Niêm phong), Vàng (Nghi vấn), Xanh (An toàn).
  - Cung cấp nút duyệt nhanh hàng loạt và xuất file `review_queue_reviewed.csv`.
- **Cơ chế Override & Ghi nhật ký**:
  - Mọi thao tác duyệt đều ghi tên người thẩm định (`Lê Văn Khởi` / `Quốc Anh`) và mốc thời gian ISO-8601.
  - Bộ kiểm soát `apply_review()` chặn đứng mọi nỗ lực dùng file CSV để ép xóa các mục đang bị `legal_hold`.
- **Chính sách quyết định cuối (`decide`)**:
  - Quyết định trả về: **`HOLD: EXCEPTIONS_REQUIRE_FOLLOW_UP`**.
  - Lý do: 128 món an toàn đã được xóa mô phỏng thành công, nhưng hệ thống giữ trạng thái HOLD để cảnh báo chuyên viên pháp chế tiếp tục theo dõi 2 ca Legal Hold và 28 ca Escalate.

---

## 08 · Reproduce & tests

Quy trình tái lập kết quả từ đầu:
```powershell
# 1. Chạy lập kế hoạch quét tự động (Dry-run)
python -m src.main --offline --seed 42

# 2. Mở review.html duyệt bằng mắt và xuất review_queue_reviewed.csv vào out/poc/

# 3. Chạy thực thi mô phỏng có phê duyệt của con người
python -m src.main --config configs/t08_execute.yaml --offline --seed 42

# 4. Kiểm tra tính Idempotent (chạy lần 2 không lỗi, báo already_deleted)
python -m src.main --config configs/t08_execute.yaml --offline --seed 42

# 5. Chạy bộ tự kiểm tra Benchmark Baseline vs PoC
python -X utf8 tools/run_t08_selfcheck.py
```

- **Môi trường thử nghiệm**: Windows 11 · Python 3.14 · CPU Intel Core i7 · Git status clean.

---

## 09 · Limitations & ethics

1. **Giới hạn mô phỏng (Mock Boundary)**: PoC hiện tại quản lý trạng thái xóa qua sổ cái metadata ảo (`mock_state.json`), chưa kết nối tới các API đám mây vật lý (như AWS S3 / Glacier DeleteObject). Trong môi trường sản xuất thật, cần tích hợp adapter driver cho từng hệ thống lưu trữ phân tán.
2. **Quy tắc kế thừa Legal Hold**: PoC hiện tại áp dụng cờ Legal Hold cho chính node mang nhãn; trong thực tế, cần chính sách pháp chế quy định rõ liệu lệnh niêm phong video gốc có tự động đóng băng toàn bộ vector embedding phái sinh hay không.
3. **Đạo đức dữ liệu (AI Ethics)**: Nhóm cam kết tuân thủ nghiêm ngặt nguyên tắc minh bạch, tôn trọng quyền tự quyết dữ liệu cá nhân của người dùng, không giấu giếm dữ liệu và không tự ý tiêu hủy chứng cứ tư pháp.
