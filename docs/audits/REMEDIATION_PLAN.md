# Phương án sửa theo PDF — chưa áp dụng

Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.


**Trong nhiệm vụ này chỉ kiểm toán và chuẩn bị phương án. Chưa sửa code/vector A/B, chưa thay PDF/dataset, chưa triển khai C1/C2.** Việc sửa sau này phải theo đúng phạm vi sai lệch đã xác minh; không dùng Top-5 làm hàm mục tiêu.

## 1. Bảo lưu baseline

Giữ nguyên source hiện tại, hai kho vector/stats/mapping và toàn bộ output A-only/B-only/AB. Dùng hash tại `protected_before.json`, `protected_supplement_legacy_previews.json` và `legacy_dependency_register.json` làm mốc; không rename/xóa/ghi đè file cũ. Tạo schema/version/output mới khi được giao triển khai, ví dụ `outputs/A_geometry/features_report_v2/`, `outputs/B_color/color_features_report_v2/`, `outputs/retrieval/ab_report_v2/`; đây là **đường dẫn đề xuất, chưa tạo artifact sửa**.

## 2. A12 — sửa mẫu số Z-score A theo §2.5.2

Thay đúng phép biến đổi, giữ150 chiều, extractor/mapping/raw gallery và Euclid nếu chưa có căn cứ sai lệch khác. Dùng mean/std kho cũ có thể tính lại kiểm chứng từ raw, ddof0 giữ như hiện tại khi PDF chưa buộc đổi. Điều bắt buộc là **mẫu sốraw_sigma+epsilon**, không `where(sigma<threshold,1,sigma)`.

```python
# Pseudocode cho phiên bản mới; KHÔNG phải code đã áp dụng.
mean = raw.astype(float64).mean(axis=0)
raw_sigma = raw.astype(float64).std(axis=0, ddof=0)
epsilon = configured_positive_epsilon  # PDF chưa cho trị số; phải ghi nhận quyết định
divisor = raw_sigma + epsilon
z = (raw - mean) / divisor
```

Lưu riêng `mean`, `raw_sigma`, `epsilon`, `divisor`, fit manifest/hash, schema ID và dtype. Không ghi key `std` mơ hồ mà không mô tả raw hay effective divisor. Nếu giữ float32 để tương thích dung lượng thì cast ở cuối và công khai; query phải dùng đúng effective divisor/schema, không lấy std_safe từ legacy. Không tự loại chiềuσ0, không ép query chiều hằng thành0 và không bỏ sốhạngε cho chiềuσ>0.

PDF không quy định trị sốε nên audit không chọn một “ε chính thức” bằng thứ hạng. Trước implementation phải chốt một giá trị dương/versioned theo thẩm quyền dự án. Các trị1e-12/1e-8/1e-6 trong audit chỉ là độ nhạy; không phải phê duyệt config mới.

Phải cập nhật đồng bộ normalizer, A-only query, worker A và gallery loader theo phiên bản. Kiểm thử normalσ,σ0,σ rất nhỏ và query ngoài kho; expected phải dùng công thức PDF trực tiếp. Không chỉ kiểm training mean0/std1 hoặc Top-5.

## 3. B12 — khôi phục stage mô-men trước ghép, tách khỏi Z-score cuối

PDF trang13/17 buộc có chuẩn hóa mô-men theo kho trước concat; trang13 buộc Z-score từng chiều sau concat. Code mới cần biểu diễn/ghi nhận rõ hai phạm vi này. Tuy nhiên PDF không định nghĩa toán tử chi tiết của stage mô-men; không tự lấy “hai lần Z-score” làm đáp án duy nhất. Chốt mô tả toán tử/stats/fallback theo PDF và các quy ước không xung đột, lưu quyết định mới thay D14 chỉ ở phần thực sự mâu thuẫn thứ tự.

Luồng phiên bản mới đề xuất:

```text
Ảnh + raw masks class1/17
  -> descriptor HS48/Lab12/Hue12 của từng vùng
  -> normalize 24 Lab moments bằng tham số kho đã fit/lưu riêng
  -> concatenate B144, giữ nguyên serialization
  -> final all144 Z-score bằng stats kho của vector sau stage trước
  -> Euclid144
```

Giữ D01–D13/D15–D17 về bins, CIE-Lab, Pearson, ddof, circular std, class/ROI, raw mask, minimum100, serialization, missing, fit scope và metric trừ khi có bằng chứng mới mâu thuẫn yêu cầu rõ. Không đổi Skin+Nose/Clean, không xóa outlier, không tăng/giảm chiều, không thêm sin/cos hay đổi metric. Đặc biệt **không áp dụng `sigma+epsilon` của A sang B một cách máy móc**.

Lưu các stats của stage mô-men và stage cuối tách biệt; query dùng lại cả hai đúng thứ tự. Giữ raw descriptor cũ như baseline; không mặc định cần chạy segmentation lại vì raw masks hiện đã có lineage/hash. Kiểm tra trường hợp nonconstant, constant/tinyσ, new query, fallback và clipping; không nhận hai luồng bằng nhau chỉ vì affine cancel trên kho hiện tại.

## 4. B18 — cách ly helper lịch sử

`moments_only` không đạt bước cuối all144. Runner hiện đã chặn, nên không cần sửa vector v1 chỉ vì helper này tồn tại. Nếu bổ sung entry point mới, enforce schema/profile all144 ngay tại ranh giới production và có test từ chối profile khác. Giữ helper/snapshot nghiên cứu để truy vết; không tự xóa code hoặc đổi nhãn artifact cũ thành compliant.

## 5. Dataset DS05/DS10 và các mục UNVERIFIED

Giữ toàn bộ ảnh hiện tại. Gắn cờ trong audit/catalog phiên bản mới (không sửa catalog cũ), chỉ rõ HF00333/HF00561 mặt phụ, HF00722 che miệng. Chưa tự crop/inpaint/loại ảnh hoặc đổi mask để tạo dataset đẹp hơn. Nếu được giao làm một dataset tuân thủ mới, cần quy trình kiểm duyệt/source thay thế và version riêng; mọi thay đổi phải bám tiêu chí PDF, giữ mapping/lineage tới bản cũ.

Yaw/pitch, IPD/tâm mắt, face-height ratio,1135 người/303 cảm xúc,18–60 tuổi, bicubic/crop/PNG95 và CSDL cần chứng cứ bổ sung/định nghĩa phép đo đã chốt, không suy ra từ tên file, review cũ hay mô hình. Mapping A và14 endpoint cần bảng thẩm quyền; **chưa được tự đổi các điểm A vì chúng đang UNVERIFIED**. Cờ topology mũi cần giải quyết bằng đối chiếu tài liệu/mốc có thể kiểm chứng, không chọn phương án cho Top-5 đẹp.

## 6. Tính lại các phụ thuộc và đánh giá

1. Bảo toàn baseline/hash và giữ danh tính1438/1437 cùng missing policy.
2. Tạo A/B schema/stats/vector mới theo đúng phần sửa; không ghi đường dẫn legacy.
3. Dùng lại **cùng pair IDs** để so sánh phiên bản; tính lại dA/dB và median cho mọi bộ có vector thay đổi, lưu cả median mới và hash nguồn. Nếu tập ID đổi do dataset phiên bản mới, phải tạo pair manifest/calibration mới rõ ràng.
4. Tính lại query transforms, Euclid riêng, median normalization, D và Top-5/CSV/JSON/preview. Đánh dấu rõ version trong A-only/B-only/AB. Không nhận một loader std_safe cũ với một vector mới `sigma+epsilon`.
5. Chạy oracle công thức trước; so sánh số học/ranking để đánh giá tác động, **chấp nhận thứ hạng hoặc chất lượng trực quan kém hơn nếu đó là hệ quả tuân thủ PDF**. Không refit epsilon/weights theo query sau khi xem Top-5.
6. Chất lượng retrieval cần relevance labels/protocol độc lập (tách người/biểu cảm nếu có thẩm quyền nhãn). Kiểm tra công thức và relevance là hai kết luận khác nhau; không báo accuracy/IoU/Dice thiếu GT.

## 7. Điều kiện hoàn tất trước C1/C2

A12 và B12 đã sửa/kiểm chứng ở phiên bản mới; input dataset có giao thức tuân thủ và các vi phạm được giải quyết minh bạch; mapping/endpoint và ε được ghi nhận đủ; artifact/query/calibration nhất quán theo phiên bản. Chỉ sau đó mới có thể kết luận A/B sẵn sàng làm nền tảng phù hợp phạm vi C1/C2. **Chưa triển khai C1/C2 trong nhiệm vụ này.**

## Các sai lệch mà kế hoạch này xử lý

| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |
|---|---|---|---|---|---|---|
| A12 — Z-score A phải có mẫu số σ+ε | 17 §2.5.2 | features/A_geometry/src/normalize_features.py:10::main | std_safe=where(std<1e-8,1,std); Z=(X−mean)/std_safe | 3 oracle normal/zero/tiny sigma; a_zscore_epsilon_sensitivity.csv | DEVIATION | Sửa theo PDF trong phiên bản mới, lưu raw_sigma và epsilon; cập nhật query và mọi phụ thuộc. |
| B12 — Mô-men phải được chuẩn hóa theo kho trước khi ghép | 13 §2.3.3;17 §2.5.2 | features/B_color/src/color_features.py:111::extract_color; features/B_color/src/full_color.py:115::run | Đang raw descriptor → concat144 → fit/transform all144 một lần | test_no_preconcat_moment_standardization_in_current_descriptor; source run(); b_stage_order_illustration.json | DEVIATION | D14 mâu thuẫn thứ tự được PDF nói rõ; chuẩn bị stage riêng trong phiên bản mới, chưa tự thêm ở audit. |
| B18 — Helper lịch sử moments_only không phải chuẩn hóa all144 theo PDF | 13 | features/B_color/src/color_features.py:123::fit_standardizer | profile=moments_only chỉ scale24/144 chiều | run_color_experiment.py từ chối profile này; helper vẫn callable | DEVIATION | Chỉ nhánh nghiên cứu, không được gọi v1 bám báo cáo; giữ lịch sử, không xóa hay thay artifact. |
| DS05 — Một mặt duy nhất, không có mặt phụ | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Detector num_faces5 báo1 trên1438; hình thật có mặt phụ | visual_review_findings.csv: HF00333 và HF00561 | DEVIATION | Không xóa ảnh; gắn cờ lỗi tiêu chí và chuẩn bị dataset phiên bản kiểm duyệt riêng nếu được giao. |
| DS10 — Mắt, mũi, miệng không bị che bởi tay/phụ kiện/tóc | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | HF00722: ngón tay che vùng miệng | dataset_mask_review_page2.png row2 | DEVIATION | Giữ nguyên ảnh và nhãn; lưu bằng chứng, không tối ưu mask/ranking để che vấn đề. |
| AB14 — Calibration/ranking phải thuộc phiên bản A đúng công thức | 17 | retrieval/search_ab.py:126::load_gallery | Hiện fingerprint trỏ A std_safe cũ | legacy_dependency_register.json; A12 confirmed | DEVIATION | Sai lệch kế thừa A12, không đếm là nguyên nhân mới; đánh dấu mọi phụ thuộc trong audit register. |

## Lệnh kiểm chứng thực tế đã chạy thành công

Các lệnh sau chỉ tạo evidence mới trong `docs/audits/`; chúng không phải lệnh áp dụng remediation:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/verify_a.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/measure_dataset.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/verify_b_ab.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/test_a_oracles.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/test_b_ab_oracles.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/write_reports.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/audit_tools/verify_scope.py
```

Tests cũ được chạy qua unittest discovery với log chuyển vào evidence, không gọi các main ghi output chính thức. Worker query đã chạy bằng2 interpreter gốc, truyền raw masks B hiện có và `--output docs/audits/evidence/query_worker_*`; không chạy search main để ghi lại retrieval cũ. Không cài thư viện/tải model.
