# C1 ROI contract v0.2.0 — PROVISIONAL

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu cao nhất: `csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh. Đã đọc toàn bộ §2.2/§2.4 qua bản trích PDF đóng băng, đối chiếu hình PDF và source/hash hiện hành. Không chỉnh PDF, dataset, mapping A, vector A/B, stats/calibration, CSDL hoặc kết quả A+B đã nghiệm thu.

Đợt này chỉ kiểm toán ROI và chốt đặc tả kỹ thuật có nguồn gốc rõ. Không chạy lại MediaPipe, không gọi LBP/HOG trên ảnh, không viết extractor hoặc tạo vector C1/C2. Tên file “final” là hồ sơ kết luận của lần rà soát; trạng thái giải phẫu vẫn **PROVISIONAL**.


## Nhận dạng và phạm vi

- Schema ID: `C1_ROI_RAW_CONTRACT_v0.2.0`; version `0.2.0`; status **PROVISIONAL**.
- [Contract JSON](../outputs/C1_lbp/roi_validation/contract_v0_2.json); file SHA-256 `6d014ac00707bc158e8970a971548ed847331df19faebd4078bfca62347720a6`.
- Canonical content SHA-256 `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c`: JSON canonical sort-key, UTF-8, không gồm trường content_sha256. [Sidecar hash file](../outputs/C1_lbp/roi_validation/contract_v0_2.sha256).
- Geometry SHA-256 `edba1f488fbc4733889d257c7e25053357e64f6085815442a1be3c7f2729bc54`; 61 vertex definition được giữ **đúng v0.1**, gồm 25/12/12/12 đỉnh. Proposal v0.1 và mọi output trước giữ nguyên.
- Thay đổi có chủ đích của đợt kiểm tra: dùng **bốn mask raw độc lập**, không áp dụng ownership hoặc trừ overlap theo ưu tiên của proposal cũ.

PDF §2.4.2 quy định bốn vùng: trán và lông mày, má trái, má phải, mũi và miệng. PDF không cho vertex, margin, hệ quy chiếu trái/phải, raster rule hoặc cách chia overlap. Tên vùng là EXACT theo văn bản; các lựa chọn hình học bên dưới là quy ước triển khai có giới hạn, không phải endpoint canonical được PDF xác nhận.

## Mapping, topology và hệ quy chiếu

A0…A67 là mapping 68 điểm hiện hành, MP0…MP477 là landmark gốc. Dữ liệu đến từ archive 1438×478×2 float32 có hash xác thực. Không dùng vị trí hàng làm danh tính; nối qua tên ảnh/image_id. [Source proof](../outputs/C1_lbp/roi_validation/source_proof.json).

Trái/phải chọn **theo người xem/code**; không tự swap sang giải phẫu. Tâm L/R là mean6 float32 của các nhóm `[33,160,158,133,153,144]` và `[362,385,387,263,373,380]`, rồi promote sang float64 để dựng frame: `D=norm64(R−L)`, `u=(R−L)/D`, `v=(−u_y,u_x)`. Mỗi vertex là `P[MP]+D*(αu+βv)`. Các offset 0.05/0.08/0.06 là quy ước, không nằm trong PDF.

Vùng trán dùng 15 MP phụ trợ upper FACE_OVAL `[127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 356]`. Đã kiểm membership và **14 cạnh liên tiếp** trong topology đã hash. Dùng 478 phụ trợ cho C1 chưa được PDF mô tả rõ và cần xác nhận trước chứng nhận giải phẫu; không thêm chúng vào vector A.

MP1=A30, MP4=A33 giữ nguyên. Khác biệt topology với hình PDF trước đây chưa được giải quyết bằng cách đổi index. MP129=A31 và MP358=A35 vẫn là endpoint cánh/bên mũi proxy UNVERIFIED, không thuộc sparse NOSE. Membership mắt/mày/môi/FACE_OVAL đã kiểm không đồng nghĩa canonical anatomical endpoint. Xem [A_MAPPING_FINAL_REVIEW.md](audits/A_MAPPING_FINAL_REVIEW.md).

## Toàn bộ vertex và thứ tự

Nối cạnh thẳng theo thứ tự 0→1→…→n−1→0; không tự sắp xếp, convex-hull, spline hoặc sửa mapping để làm hình đơn giản/đẹp hơn. Các hệ số dùng theo đúng công thức frame ở trên.

### Trán và vùng lông mày

| Thứ tự | Nguồn | MP index | α·D·u | β·D·v |
| --- | --- | --- | --- | --- |
| 0 | MP127 phụ trợ | 127 | 0.0 | 0.0 |
| 1 | MP162 phụ trợ | 162 | 0.0 | 0.0 |
| 2 | MP21 phụ trợ | 21 | 0.0 | 0.0 |
| 3 | MP54 phụ trợ | 54 | 0.0 | 0.0 |
| 4 | MP103 phụ trợ | 103 | 0.0 | 0.0 |
| 5 | MP67 phụ trợ | 67 | 0.0 | 0.0 |
| 6 | MP109 phụ trợ | 109 | 0.0 | 0.0 |
| 7 | MP10 phụ trợ | 10 | 0.0 | 0.0 |
| 8 | MP338 phụ trợ | 338 | 0.0 | 0.0 |
| 9 | MP297 phụ trợ | 297 | 0.0 | 0.0 |
| 10 | MP332 phụ trợ | 332 | 0.0 | 0.0 |
| 11 | MP284 phụ trợ | 284 | 0.0 | 0.0 |
| 12 | MP251 phụ trợ | 251 | 0.0 | 0.0 |
| 13 | MP389 phụ trợ | 389 | 0.0 | 0.0 |
| 14 | MP356 phụ trợ | 356 | 0.0 | 0.0 |
| 15 | A26 | 300 | 0.0 | 0.05 |
| 16 | A25 | 293 | 0.0 | 0.05 |
| 17 | A24 | 334 | 0.0 | 0.05 |
| 18 | A23 | 296 | 0.0 | 0.05 |
| 19 | A22 | 336 | 0.0 | 0.05 |
| 20 | A21 | 107 | 0.0 | 0.05 |
| 21 | A20 | 66 | 0.0 | 0.05 |
| 22 | A19 | 105 | 0.0 | 0.05 |
| 23 | A18 | 63 | 0.0 | 0.05 |
| 24 | A17 | 70 | 0.0 | 0.05 |
### Má trái theo người xem

| Thứ tự | Nguồn | MP index | α·D·u | β·D·v |
| --- | --- | --- | --- | --- |
| 0 | A36 | 33 | 0.0 | 0.08 |
| 1 | A41 | 144 | 0.0 | 0.08 |
| 2 | A40 | 153 | 0.0 | 0.08 |
| 3 | A39 | 133 | 0.0 | 0.08 |
| 4 | A31 | 129 | 0.0 | 0.0 |
| 5 | A48 | 61 | 0.0 | 0.0 |
| 6 | A5 | 136 | 0.0 | 0.0 |
| 7 | A4 | 172 | 0.0 | 0.0 |
| 8 | A3 | 58 | 0.0 | 0.0 |
| 9 | A2 | 132 | 0.0 | 0.0 |
| 10 | A1 | 93 | 0.0 | 0.0 |
| 11 | A0 | 234 | 0.0 | 0.0 |
### Má phải theo người xem

| Thứ tự | Nguồn | MP index | α·D·u | β·D·v |
| --- | --- | --- | --- | --- |
| 0 | A45 | 263 | 0.0 | 0.08 |
| 1 | A46 | 373 | 0.0 | 0.08 |
| 2 | A47 | 380 | 0.0 | 0.08 |
| 3 | A42 | 362 | 0.0 | 0.08 |
| 4 | A35 | 358 | 0.0 | 0.0 |
| 5 | A54 | 291 | 0.0 | 0.0 |
| 6 | A11 | 365 | 0.0 | 0.0 |
| 7 | A12 | 397 | 0.0 | 0.0 |
| 8 | A13 | 288 | 0.0 | 0.0 |
| 9 | A14 | 361 | 0.0 | 0.0 |
| 10 | A15 | 323 | 0.0 | 0.0 |
| 11 | A16 | 454 | 0.0 | 0.0 |
### Mũi và miệng

| Thứ tự | Nguồn | MP index | α·D·u | β·D·v |
| --- | --- | --- | --- | --- |
| 0 | A27 | 168 | 0.0 | 0.0 |
| 1 | A42 | 362 | 0.0 | 0.08 |
| 2 | A35 | 358 | 0.0 | 0.0 |
| 3 | A54 | 291 | 0.05 | 0.0 |
| 4 | A55 | 321 | 0.0 | 0.06 |
| 5 | A56 | 314 | 0.0 | 0.06 |
| 6 | A57 | 17 | 0.0 | 0.06 |
| 7 | A58 | 84 | 0.0 | 0.06 |
| 8 | A59 | 91 | 0.0 | 0.06 |
| 9 | A48 | 61 | -0.05 | 0.0 |
| 10 | A31 | 129 | 0.0 | 0.0 |
| 11 | A39 | 133 | 0.0 | 0.08 |

[roi_vertices.csv](../outputs/C1_lbp/roi_validation/roi_vertices.csv) lưu **87.718 vertex thực tế** của cả 1438 ảnh. Index nguồn, thứ tự và offset đều được ghi lại, không chỉ mô tả tên vùng.

## Raster, overlap, gaps và vùng không hợp lệ

Vertex tính float64, contour raster cast float32; điểm lấy mẫu là tâm pixel nguyên x/y, `pointPolygonTest>=0` kể cả boundary. Đánh giá trong khung 0…255; không clamp từng vertex, không warp ảnh. Guard số học: D≥1e-6, diện tích≥1e-6 pixel², cạnh≥1e-9; kiểm giao/chạm cạnh không kề với tolerance 1e-9 theo công cụ audit.

**Không áp dụng priority subtraction.** Mỗi ROI giữ membership riêng, pixel overlap được lưu ở cả hai mask. Quy ước pooling tương lai của bản đặc tả kỹ thuật cũng giữ shared pixels độc lập; đây là lựa chọn triển khai, không phải câu nguyên văn PDF. Việc hiểu “bốn vùng độc lập” thành disjoint hay independent pooling chưa có đặc tả pixel trong PDF; không gọi điều đó là đã chứng minh tuân thủ hoàn toàn.

Pixel ngoài union giữ unassigned; không ép bốn ROI phủ toàn bộ mặt. Báo cáo phân biệt unassigned trên toàn ảnh với unassigned **trong FACE_OVAL proxy**; cả hai có thể gồm mắt/cằm cố ý không chọn. “Enclosed gap” là component không chạm biên proxy, không tự coi là lỗi giải phẫu.

Mask của polygon tự giao vẫn được raster để đo/hiển thị **chẩn đoán**; nó không hợp lệ cho extractor tương lai. Thiếu/invalid một vùng hoặc <64 tâm có support hợp lệ thì future C1 phải trả `missing_C1`, không zero-fill. Ngưỡng 64 và cờ review mask<256 pixel là quy ước kỹ thuật công khai, không phải mức chất lượng do PDF quy định.

## Kết quả toàn kho và mức cho phép sử dụng

**5752 ROI đã kiểm: 5748 hợp lệ về hình học, 4 trán tự giao.** Không có out-of-bounds hoặc cờ quá nhỏ theo ngưỡng đã đặt. Bốn ảnh lỗi: HF00069, HF00198, HF00267, HF00463. [Báo cáo toàn kho](audits/C1_ROI_FULL_DATASET_VALIDATION.md).

Mọi 1438 ảnh có overlap, unique shared pixels min/median/max=91/140/208; chỉ hai cặp má–mũi/miệng có overlap. Proxy lông mày native chỉ được phủ khoảng **44.29–67.14%**, median **55.55%**; không ảnh nào phủ đủ proxy. Đây là bằng chứng undercoverage của proxy, không phải annotation mô lông mày thật.

**Chưa cho phép coi bản này là ROI giải phẫu chính thức hoặc sinh 100 vector hợp lệ.** Có thể dùng cho thử nghiệm kỹ thuật có kiểm soát sau khi được giao triển khai extractor: manifest 100 ảnh đã chuẩn bị, 96 đi nhánh tính toán và 4 bắt buộc trả missing vì hình học. Không chạy thử trong nhiệm vụ này. [trial100_manifest.json](../outputs/C1_lbp/roi_validation/trial100_manifest.json).

## Điều chỉnh được đề xuất, chưa áp dụng

1. Thay biên dưới trán bằng lower-eyebrow native chain `[276,283,282,295,285,55,65,52,53,46]` cộng 0.02D·v; giữ upper FACE_OVAL và toàn bộ A indices. Lý do: proxy undercoverage toàn kho. [Proposal v0.3](../outputs/C1_lbp/roi_validation/forehead_amendment_proposal_v0_3.json) **không phải contract active**.
2. Preview trên 18 case cho coverage proxy mới min `0.996359`, nhưng chỉ **17/18** có hình học đơn giản; **hf_merged_00198 vẫn tự giao**. Không chọn/triển khai proposal chỉ vì coverage tốt hơn. [So sánh HF00198](../outputs/C1_lbp/roi_validation/proposal_comparisons/hf_merged_00198_forehead.png), [toàn bộ kết quả proposal](../outputs/C1_lbp/roi_validation/forehead_amendment_comparisons.json).
3. Cần xác định đường nối ở thái dương có thẩm quyền để tránh cắt upper FACE_OVAL, rồi kiểm lại toàn bộ 5752 ROI của candidate mới; không tự convex-hull hoặc cắt đỉnh vì mục tiêu đẹp/hợp lệ giả.
4. Giữ occlusion flags và giải quyết bằng protocol riêng. Không tự giao ROI với skin/hair mask Bộ B, không inpaint/crop/xóa ảnh. Đổi ROI không giải quyết dataset có mặt phụ hoặc tay che.

Không lựa chọn ROI bằng kết quả retrieval/Top-5. Trạng thái sau rà soát: **PROVISIONAL, không APPROVED**.
