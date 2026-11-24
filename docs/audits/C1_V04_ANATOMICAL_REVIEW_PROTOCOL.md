# C1 v0.4 — protocol review giải phẫu và ghi nhận chứng cứ

Ngày tạo: **24/11/2026**, Asia/Saigon. Hồ sơ chờ đánh giá của con người.
**800/800 dòng NOT_REVIEWED**, reviewer/date trống,0 quyết định có thẩm quyền, không kích hoạt v0.4.

## Nguồn và phạm vi

Thẩm quyền yêu cầu cao nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã kiểm trực tiếp.
Đã đọc các audit remediation/anatomical validation/mapping/full-corpus và hai spec hiện hành.
PDF §2.2/§2.4 được đọc trực tiếp bằng pypdf có sẵn; bản trích và hai hình trang8 trong
[reference/](c1_v04_review/reference/). Snapshot hình PDF chỉ là tham chiếu, không phải canonical MP-ID table.

Contract v0.2 content SHA: `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c`.
Candidate v0.4 content SHA: `c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39`. Cả hai được tính lại canonical JSON, loại field content_sha256.
V0.4 giữ `active=false`. Không sửa vertex, offsets, frame, PDF, A/B, calibration, SQLite hoặc trial100 cũ.
P8,R2,threshold>=,NRI59,L1 riêng,Chi-square0.5,gray/bilinear/bit-order/codebook đã khóa giữ nguyên.
Không gọi LBP/HOG hay tạo vector; chỉ raster lại ROI cho100 ảnh và đối chiếu hash census đã đóng băng.

## Tập review100 ảnh

**50 CFD+50 HF**, gồm **18 ID bắt buộc** và82 ảnh lấy mẫu phần còn lại.
Seed `24042026`; `random.Random(seed).sample` trên pool ID đã sort, lần lượt CFD rồi HF,
bù đủ50 mỗi nguồn sau khi chọn mandatory. Không dùng ranking, distance hoặc kết quả tìm kiếm để chọn.
Danh sách đầy đủ, lý do, extrema values và source hashes:
[review_manifest.json](c1_v04_review/review_manifest.json).
Đây là mẫu pha mandatory/risk/extrema với lấy mẫu ngẫu nhiên bổ sung, không phải100 ảnh random thuần
hay mẫu đủ để chứng nhận1438 ảnh về giải phẫu.

| ID bắt buộc | Lý do chọn |
|---|---|
| cfd_final_00001 | fixed_CFD_HF_reference |
| cfd_final_00069 | required_visible_expression_geometry_case_no_emotion_label |
| cfd_final_00112 | candidate_v0_4:continuous_area_px2:minimum; candidate_v0_4:raw_mask_pixels:minimum; required_prior_visible_forehead_hair_case; v0_2:continuous_area_px2:minimum; v0_2:raw_mask_pixels:minimum |
| cfd_final_00268 | required_visible_expression_geometry_case_no_emotion_label |
| cfd_final_00529 | v0_2:continuous_area_px2:maximum; v0_2:raw_mask_pixels:maximum |
| hf_merged_00001 | fixed_CFD_HF_reference |
| hf_merged_00055 | required_native_brow_point_outside_v04; required_prior_visible_forehead_hair_case |
| hf_merged_00069 | required_v02_self_intersection |
| hf_merged_00082 | candidate_v0_4:continuous_area_px2:maximum; candidate_v0_4:raw_mask_pixels:maximum |
| hf_merged_00198 | required_native_brow_point_outside_v04; required_prior_visible_glasses_case; required_v02_self_intersection |
| hf_merged_00209 | required_prior_visible_head_covering_case |
| hf_merged_00267 | required_native_brow_point_outside_v04; required_v02_self_intersection |
| hf_merged_00311 | required_prior_visible_forehead_hair_case |
| hf_merged_00333 | required_confirmed_dataset_violation |
| hf_merged_00463 | required_native_brow_point_outside_v04; required_v02_self_intersection |
| hf_merged_00561 | required_confirmed_dataset_violation; required_prior_visible_forehead_hair_case |
| hf_merged_00694 | required_prior_visible_glasses_case; required_prior_visible_head_covering_case |
| hf_merged_00722 | required_confirmed_dataset_violation |

Extrema đã lấy cả diện tích liên tục lẫn số raw pixels, cho cảv0.2/v0.4:
forehead nhỏ nhất CFD00112; lớn nhất v0.2 CFD00529; lớn nhất v0.4 HF00082.
Bốn lỗi v0.2 và bốn native-node exceptions có phần trùng ID; không hiểu đây là8 ảnh khác nhau.

## Xem bằng chứng

Mở [index.html](c1_v04_review/index.html) trong trình duyệt cục bộ; lọc ID/lý do rồi nhấn từng ảnh.
Mỗi trang có ảnh gốc sao chép nguyên bytes, overlay hai contract, overlay toàn bộ68 điểm với bảng A68→MP,
các MP phụ trợ,8 raw mask PNG (4 mỗi contract),4 ảnh đổi pixel và binary added/removed masks.
Contact sheet tổng quan có4 raw masks v0.4; trang chi tiết có cả mask v0.2.
Màu mask độc lập, không trừ overlap. Chấm đỏ/cross ở native brow ngoài v0.4 chỉ là model-proxy finding.
V0.2 self-cross được vẽ đỏ và mask chỉ dùng chẩn đoán; không coi đó là một vùng valid để trích LBP.
Added=green,removed=red; ba vùng còn lại không thay pixel. Nhấn ảnh để xem đúng độ phân giải.

`evidence.json` từng ảnh ghi measurements, hash ảnh/landmark row, source index, điểm liên quan ngoài polygon,
pixel changes và các quan sát trước đây. [landmark_membership.csv](c1_v04_review/landmark_membership.csv)
ghi containment cho A68 và MP liên quan: điểm A68 ngoài một vùng khác không tự là lỗi;
điểm source chưa offset có thể nằm ngoài vì offset eye/cheek có chủ đích. Không đánh đồng với vertex sai.
Quan sát tóc/kính/khăn/tay lấy từ hồ sơ trước được ghi rõ **prior agent observation**, không phải annotation
hoặc quyết định của reviewer. Các ảnh chưa có quan sát ghi NO_PRIOR_OBSERVATION_RECORDED,
không phải clearance không che khuất. Reviewer phải tự điền occlusion_observation.

## Phiếu đánh giá

[review_annotations.csv](c1_v04_review/review_annotations.csv): **100×4×2=800 dòng**,400 dòng cho mỗi contract.
Khóa duy nhất `(image_id,roi_name,contract_version)`; không gộp accept v0.2 và v0.4 dù ba mask giống nhau.
`geometry_status` và hash/evidence metadata là dữ liệu frozen, độc lập với anatomy_review_status.
Tất cả reviewer/date/reason/decision_notes/occlusion observation/bằng chứng quyết định ban đầu trống.

| Nội dung cần người review trả lời | Cột | Giá trị |
|---|---|---|
| Có bao phủ đúng phần được mô tả? | covers_described_anatomy | YES/NO/UNCERTAIN/NOT_ANSWERED |
| Có cắt mất phần quan trọng? | cuts_important_part | như trên |
| Có quá nhiều tóc/nền/vải/kính/tay? | excess_non_target_material | như trên; mô tả vật thể và vị trí ở notes |
| Ranh giới hợp lý với biểu cảm đang thấy? | expression_boundary_reasonable | như trên; không chứng nhận temporal stability từ ảnh đơn |
| Có landmark cần đối chiếu hình PDF? | pdf_landmark_verification_needed | như trên; ghi A/MP ID ở notes |
| Trái/phải hiểu theo ai? | left_right_reference | VIEWER/IMAGE_SUBJECT/UNCERTAIN/NOT_ANSWERED |

Contract dùng **VIEWER**; người review hiểu theo người trong ảnh phải ghi IMAGE_SUBJECT và giải thích quan hệ,
không tự đổi tên cột, thứ tự vùng hoặc vector. Geometry không quyết định anatomy status tự động.

`anatomy_review_status` chỉ nhận **ACCEPT,REJECT,UNCERTAIN,NOT_REVIEWED**; mặc định NOT_REVIEWED.
ACCEPT là kết luận con người trên **một ảnh/một ROI/một hash contract**, không chấp nhận toàn hệ thống.
REJECT phải có lý do/vị trí; UNCERTAIN dùng khi thiếu chứng cứ hoặc cần tác giả/annotation;
NOT_REVIEWED nghĩa chưa có đánh giá, không thay bằng dự đoán detector hoặc nhận xét Agent.
Không có ngưỡng proxy coverage tự động chuyển thành ACCEPT. Cả người review cũng không được dùng Top-5 để chọn ROI.

## Ghi nhận thẩm quyền và quyết định

1. Chủ dự án/tác giả chỉ định người review, vai trò và phạm vi; lưu tài liệu chỉ định/ký xác nhận có thể kiểm tra.
   [reviewer_authorities.csv](c1_v04_review/reviewer_authorities.csv) ban đầu chỉ có header, không bịa tên người.
2. Giữ template bất biến; sao chép CSV và register sang **namespace round mới** (ví dụ `review_submissions/round_01/`).
   Ghi `reviewer`, ngàyISO YYYY-MM-DD, sáu câu trả lời, quan sát che khuất, reason/decision_notes.
   Nếu có nhiều reviewer, lưu file riêng theo reviewer/round, giữ cả disagreement thay vì ghi đè nhau.
3. `reviewer_authority_evidence` phải trỏ văn bản chỉ định khớp register; register ghi role, hash tài liệu và
   authority_confirmation_status do chủ dự án xác nhận. Không dùng tên Agent hoặc output model làm thẩm quyền.
4. `decision_evidence_path`/SHA phải trỏ biên bản/ghi chú ký nhận hoặc bằng chứng quyết định có nguồn gốc.
   `evidence_path` chỉ là hình review; không dùng trang polygon làm bằng chứng đã chấp thuận.
   Ghi rõ contract content hash, ID ảnh/ROI, người, ngày, phạm vi, lý do và nguồn viện dẫn trong biên bản.
5. Với các quyết định convention ở D01–D08, ghi kết luận được ủy quyền vào **bản register round mới**,
   authority person/source, ngày, đường dẫn/hash evidence và phạm vi/điều kiện. Không lấy nhận xét Agent làm quyết định.
   Tranh chấp/REJECT/UNCERTAIN cần adjudication có người chịu trách nhiệm; không xóa ảnh khó khỏi manifest.

Validator chỉ đọc file; kiểm đủ800 khóa, metadata/hash, enum, tên/ngày, câu trả lời và evidence refs đối với
các dòng đã review. Nó **không xác thực danh tính, chữ ký, tính thật của văn bản ủy quyền hoặc tự cấp approval**.
Project owner vẫn phải kiểm nguồn văn bản và xác nhận thẩm quyền. Các proposed gate trong readiness cũng
phải được chủ dự án chấp nhận; báo cáo này không tự thay người nghiệm thu.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py
# Với một round do con người thực hiện, dùng đường dẫn CSV/register của round đó:
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py --annotations <round.csv> --authority-register <authorities.csv> --evidence-base <thu_muc_chua_evidence>
```

Lệnh đầu đã chạy PASS với800 NOT_REVIEWED,0 human reviews. Lệnh có placeholder chỉ là hướng dẫn tương lai,
không được ghi là một human review đã thực hiện. Case evidence_path phải còn resolve trong evidence-base;
nếu dùng round ở nơi khác, mirror/link cấu trúc contact_sheets và lưu nguồn gốc, không sửa immutable evidence fields.

## Bảo toàn và bước tiếp theo

Kiểm800 raw mask round-trips,800 binary diff,100 source image hashes và8 tests về enum/provenance/selection.
[verification.json](c1_v04_review/verification.json), [tests.log](c1_v04_review/tests.log).
Baseline trước đợt này **14714 file**, gồm toàn bộ trial100, hai contract, A/B,
dataset/PDF/SQLite và remediation cũ. Các hash phải không đổi trước/sau; evidence tại
[baseline_before.json](c1_v04_review/baseline_before.json), [final_scope.json](c1_v04_review/final_scope.json).

[Decision register](C1_V04_DECISION_REGISTER.md) và [approval readiness](C1_V04_APPROVAL_READINESS.md)
ghi rõ phần còn thiếu và điều kiện tương lai. Việc tạo hồ sơ không kích hoạt contract, không tính C1,
không chỉnh thuật toán, không chứng nhận anatomy100% từ100 ảnh.
