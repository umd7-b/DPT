# C1 v0.4 — trạng thái sẵn sàng cho nghiệm thu có bằng chứng

Ngày24/11/2026, Asia/Saigon. **REVIEW_PACKAGE_READY — HUMAN_REVIEW_PENDING**.
Candidate vẫn **GEOMETRY_VALIDATED / ANATOMY_PROVISIONAL**, `active=false`.
Đã tạo công cụ/hình review; chưa có con người đánh giá hoặc bằng chứng chấp thuận trong hồ sơ này.

| Hạng mục | Điều đã chứng minh / trạng thái hiện tại |
|---|---|
| Hash contract | v0.2 `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c`; v0.4 `c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39`; canonical hash khớp |
| Geometry toàn kho từ audit trước | v0.2 5748/5752 valid,4 tự giao; v0.4 5752/5752 valid,0 self-cross/support<64/out-of-image |
| Tính bất biến vùng | Ba vùng má/mũi-miệng không đổi mask; forehead đổi trên1438 ảnh; chưa tạo vector với ROI mới |
| Proxy mày | v0.4 1436/1438 đủ integer proxy; HF198 thiếu3px,HF267 thiếu1px;4 native points ngoài polygon |
| Anatomy | Bốn vùng ở cả1438 ảnh chưa có đủ anatomical annotation/clearance có thẩm quyền |
| Bộ review mới | 100 ảnh50CFD/50HF,18 mandatory+82 random fill;100 source copies,800 raw masks và binary diffs |
| Phiếu | 800 NOT_REVIEWED,0 ACCEPT/REJECT/UNCERTAIN;400 rows candidate và400 comparison |
| Quyết định PDF chưa chốt | D01–D08 đều PENDING_AUTHORITY_REVIEW; không có người/nguồn xác nhận thực tế |
| Bảo toàn | Baseline14714 file trước đợt này; các hash cũ phải giữ nguyên |
| Triển khai | Không kích hoạt v0.4,không tính lại96 vector trial cũ,không chạy C1 toàn kho,C2 hoặc fusion |

Geometry/proxy coverage không đủ chứng minh anatomy. Các vấn đề dataset HF333/HF561 mặt phụ,
HF722 tay che vẫn giữ; HF209 thiếu tóc B không tự là lỗi dataset hoặc thiếu C1,HF694 phụ kiện vẫn cần review.
Không suy đoán person_id/tuổi/giới, không sửa/crop/inpaint nguồn ảnh.

## Điều kiện đề xuất để xem xét kích hoạt contract mới

Các điều kiện này là **đề xuất protocol chờ project owner chốt**, không phải Agent cấp approval:

1. Xác minh reviewer/tác giả/đại diện nhóm có thẩm quyền và phạm vi; lưu ủy quyền/biên bản có hash.
   Người có thẩm quyền chốt D01–D08 đúng yêu cầu rõ của PDF, có evidence; quyết định không được trái công thức PDF.
2. Hoàn thành review400 ROI candidate trên100 ảnh, trả lời sáu prompts, ghi occlusion và đối chiếu ảnh/PDF.
   Mọi REJECT/UNCERTAIN phải được adjudicate hoặc có policy missing/exclusion được phê duyệt và version hóa;
   không xóa ca khó khỏi manifest hoặc ép mọi ảnh thành ACCEPT. Lưu độc lập review v0.2 nếu có.
3. Xác minh annotation anatomy: extent trán/mày,temple/glabella bridges,má/mũi-miệng,frame trái/phải,
   bốn continuous-node cases và tiêu chí tóc/nền/tay/kính/vải. Nếu cần sửa ROI,tạo version khác rồi audit lại;
   không sửa trực tiếp v0.4 hoặc mapping A.
4. Đánh giá độ đủ của review100 theo protocol do người có thẩm quyền xác nhận.100 ảnh không tự đủ để
   chứng nhận cả1438 anatomy-valid;1338 ảnh ngoài bộ này chưa được reviewer của bộ này xem xét.
   Các quan sát Agent ở audit trước không thay annotation/ủy quyền cho bộ mới.
5. Biên bản activation phải bind đúng content/file/geometry hashes,schema,dataset version,policy và phạm vi,
   nêu giới hạn và bên chịu trách nhiệm. Lưu activation record/registry mới bên ngoài candidate đã đóng băng,
   không sửa cờ active trong snapshot hoặc thay PDF theo implementation. Thao tác activation cần nhiệm vụ
   được giao riêng sau khi có evidence; công cụ ở đây không có chức năng activation.

Các bản form và register ban đầu giữ nguyên; review con người phải được lưu trong round/namespace mới.
Validator PASS chỉ chứng minh cấu trúc/hash/reference, không xác thực chữ ký,identity hay cấp chấp thuận.

## Điều kiện tính C1 lại trên100 ảnh — chỉ cho nhiệm vụ tương lai

Cần ủy quyền chạy technical trial mới cùng contract/hash đã được quyết định cho phạm vi thử nghiệm,
policy missing/occlusion và namespace mới; đây là quyết định riêng với activation production.
Giữ exact seed/manifest review hoặc manifest100 được chốt trước,không chọn theo Top-5.
Adapter/context cho hash ROI mới phải được version hóa riêng,giữ nguyên kernel số học đã kiểm:
P8,R2,>=,NRI59,L1 riêng,Chi-square0.5 và gray/bilinear/bit/codebook/support21 hiện hành.
Chỉ reuse landmarks có provenance; nếu thiếu nguồn,dừng rõ thay vì tự align/detect theo giả định.
Kiểm counts/dtype/dimension,L1 và scalar oracle độc lập,query/gallery hashes,negative/missing cases,
đối chiếu baseline trước/sau. Không sửa expectation về số vector để che rejection/occlusion;
trial100 v0.2 và96 vector cũ vẫn nguyên hash,không đưa vector thử nghiệm vào SQLite production.
Chưa thực hiện bất kỳ bước trích xuất nào trong nhiệm vụ hồ sơ này.

## Điều kiện tính C1 toàn bộ1438 ảnh — chỉ cho nhiệm vụ tương lai

Ngoài các điều kiện kỹ thuật100 ảnh,phải có quyết định triển khai cho phạm vi1438 và protocol anatomical/
occlusion đủ phạm vi,quyết định dataset có truy vết,adjudication các exception và biên bản nghiệm thu
contract/version phù hợp. Nếu chỉ có sampled review,ghi giới hạn coverage,không dán nhãn100% anatomy compliant.
Audit lại toàn5752 ROI cho version được chọn nếu khác hash hiện hành; khóa nguồn/hash dữ liệu,stats/calibration
A/B không refit; tạo output/version mới,mapping image_id và missing_reason,không zero-fill hoặc ghi đè DB/vector.
Chốt phương án rollback/activation registry và bài kiểm numeric/provenance trước khi giao thực thi riêng.
Không triển khai C2 hoặc fusion dưới phạm vi chấp thuận C1.

## Hồ sơ giao người review

- [Trang bắt đầu100 ảnh](c1_v04_review/index.html) · [Manifest](c1_v04_review/review_manifest.json).
- [Phiếu800 dòng](c1_v04_review/review_annotations.csv) · [Registry reviewer trống](c1_v04_review/reviewer_authorities.csv).
- [Protocol và18 ID bắt buộc](C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md) · [8 quyết định chưa duyệt](C1_V04_DECISION_REGISTER.md).
- [Kiểm chứng](c1_v04_review/verification.json) · [baseline](c1_v04_review/baseline_before.json) · [final scope](c1_v04_review/final_scope.json).

Lệnh thực tế tạo và kiểm hồ sơ tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/build_review.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/verify_bundle.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/write_review_docs.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/finalize_review.py
```

Tất cả là thao tác hồ sơ/geometry display. Không có ACCEPT do Agent điền vào CSV,không có chấp thuận
toàn hệ thống hoặc activation được cấp từ việc hồ sơ đã tạo xong.
