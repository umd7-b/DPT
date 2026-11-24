# Hợp đồng vùng giải phẫu C1 — đề xuất v0.1, chưa phê duyệt

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` không đổi. Đọc lại §1.3, §2.2 và §2.4 qua bản trích text audit đã đóng băng; PDF gốc được kiểm hash trực tiếp. [Trang PDF liên quan và hash bản trích](eye_c1_evidence/pdf_sections_review.json).

Giữ nguyên CSDL đã nghiệm thu, source/mapping A, dataset, PDF, vector/stats/calibration/query artifacts v1/v2. Lần này thêm bản SQLite có tên mới, metadata đo lại, hợp đồng ROI **đề xuất** và công cụ/bằng chứng audit. Không chạy lại MediaPipe, không viết extractor LBP/HOG, không tạo vector C1/C2.


## Phần PDF quy định rõ

PDF §2.4.2, trang vật lý **13**, quy định bốn vùng độc lập dựa trên landmark: **(1) Trán và vùng lông mày; (2) Má trái; (3) Má phải; (4) Mũi và miệng**. Trang 14–15 quy định LBP8,2, 59 bin uniform không bất biến quay, L1 riêng từng vùng và ghép thành 236 chiều. Lần này chỉ chuẩn bị vùng; không thực hiện các phép trích xuất đó.

PDF **không cho danh sách vertex, polygon, margin, clipping/rasterization, min-area hoặc quy tắc xử lý occlusion/chồng lấn**. Tên “trái/phải” chưa xác định hệ quy chiếu. Không gán các quyết định dưới đây thành quy định nguyên văn của PDF. Trạng thái hợp đồng: **`PROPOSAL_UNVERIFIED_NOT_FOR_FEATURE_EXTRACTION`**.

## Landmark đã kiểm chứng và endpoint còn mở

Mapping A hiện có đủ 68 index duy nhất; từng index và nhóm được đối chiếu source, CSV audit, hình PDF và contour MediaPipe đã lưu. **Membership contour** là bằng chứng cấu trúc, không phải nhãn giải phẫu chuẩn. [A_MAPPING_FINAL_REVIEW.md](A_MAPPING_FINAL_REVIEW.md) giữ kết luận: hai đầu hàm và topology mũi khác hình minh họa trên cùng CFD00001; canonical MP ID thay thế và A2 endpoints chưa được xác minh.

MP1=A30, MP4=A33 giữ nguyên; không dùng một điểm khác để “sửa” hai index này. MP129=A31 và MP358=A35 vẫn là endpoint cánh/bên mũi proxy UNVERIFIED, không có trong sparse NOSE. Chúng vẫn được ghi rõ trong **đề xuất**, không được nâng thành alare canonical. MP1/MP4 được đánh đỏ trên overlay để giữ khả năng đối chiếu.

68 điểm A không có đường trán phía trên. Đề xuất dùng thêm **15 MP478 phụ trợ** trên upper FACE_OVAL: `[127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 356]`. Membership của cả 15 điểm được kiểm với topology đã hash; chúng không được thêm vào A150 hoặc thay một index A nào. PDF chưa quy định rõ C1 có thể truy cập landmark ngoài 68 điểm hay không; việc dùng MP478 phụ trợ phải được chốt trước extractor. FACE_OVAL không tự chứng minh hairline/đỉnh trán; lựa chọn biên trên là IMPLEMENTATION DETAIL cần chốt.

## Hệ tọa độ và đỉnh dẫn xuất

Ảnh 256×256 không crop, align lại, warp hoặc nội suy để cải thiện ROI. P là pixel landmark float32 đã lưu, đưa sang float64 khi dựng polygon. L/R là các tâm float32 mean6 đã mô tả ở [EYE_METADATA_COMPLETION.md](EYE_METADATA_COMPLETION.md), promote sang float64; `D=norm64(R−L)`, `u=(R−L)/D`, `v=(−u_y,u_x)`. Y ảnh hướng xuống; yêu cầu u_x>0 và v_y>0, không tự swap mắt.

Mỗi hàng vertex dùng:

```text
V = P[MP_index] + D * (α*u + β*v)
```

Các hệ số **0.05, 0.08, 0.06** là margin đề xuất theo IPD, không được PDF chỉ định. D của khung ROI là float64; không thay eye_distance float32 của Bộ A. Số A là **index 0-based của 68 điểm hiện hành**; số MP là **index 0-based của 478 điểm**. Không nhầm MP21 với A21, hoặc cộng một rồi coi đó là một mapping PDF đã xác nhận.

## Toàn bộ đỉnh và thứ tự nối

Nối cạnh thẳng theo thứ tự 0→1→…→n−1→0; giữ nguyên thứ tự ghi, không convex-hull, spline hoặc sắp xếp đỉnh tự động. Ý nghĩa giải phẫu của mọi đường biên bên dưới còn UNVERIFIED; membership contour có thể đã xác minh nhưng không chứng nhận polygon.

### Trán và vùng lông mày — `forehead_brow`

| Thứ tự đỉnh | Tham chiếu | MP index | α theo u | β theo v | Ý nghĩa/giới hạn | Phân loại |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | MP127 phụ trợ | 127 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 1 | MP162 phụ trợ | 162 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 2 | MP21 phụ trợ | 21 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 3 | MP54 phụ trợ | 54 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 4 | MP103 phụ trợ | 103 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 5 | MP67 phụ trợ | 67 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 6 | MP109 phụ trợ | 109 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 7 | MP10 phụ trợ | 10 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 8 | MP338 phụ trợ | 338 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 9 | MP297 phụ trợ | 297 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 10 | MP332 phụ trợ | 332 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 11 | MP284 phụ trợ | 284 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 12 | MP251 phụ trợ | 251 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 13 | MP389 phụ trợ | 389 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 14 | MP356 phụ trợ | 356 | 0.0 | 0.0 | Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 15 | A26 | 300 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 16 | A25 | 293 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 17 | A24 | 334 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 18 | A23 | 296 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 19 | A22 | 336 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 20 | A21 | 107 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 21 | A20 | 66 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 22 | A19 | 105 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 23 | A18 | 63 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 24 | A17 | 70 | 0.0 | 0.05 | Đường mày thưa hiện hành; biên dưới có offset đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
### Má trái theo ảnh/người xem — `cheek_left_viewer`

| Thứ tự đỉnh | Tham chiếu | MP index | α theo u | β theo v | Ý nghĩa/giới hạn | Phân loại |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | A36 | 33 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 1 | A41 | 144 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 2 | A40 | 153 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 3 | A39 | 133 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 4 | A31 | 129 | 0.0 | 0.0 | Cánh/bên mũi proxy; MP129/358 không thuộc sparse NOSE | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 5 | A48 | 61 | 0.0 | 0.0 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 6 | A5 | 136 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 7 | A4 | 172 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 8 | A3 | 58 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 9 | A2 | 132 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 10 | A1 | 93 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 11 | A0 | 234 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
### Má phải theo ảnh/người xem — `cheek_right_viewer`

| Thứ tự đỉnh | Tham chiếu | MP index | α theo u | β theo v | Ý nghĩa/giới hạn | Phân loại |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | A45 | 263 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 1 | A46 | 373 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 2 | A47 | 380 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 3 | A42 | 362 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 4 | A35 | 358 | 0.0 | 0.0 | Cánh/bên mũi proxy; MP129/358 không thuộc sparse NOSE | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 5 | A54 | 291 | 0.0 | 0.0 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 6 | A11 | 365 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 7 | A12 | 397 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 8 | A13 | 288 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 9 | A14 | 361 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 10 | A15 | 323 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 11 | A16 | 454 | 0.0 | 0.0 | JAW/FACE_OVAL proxy; biên dưới má được đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
### Mũi và miệng — `nose_mouth`

| Thứ tự đỉnh | Tham chiếu | MP index | α theo u | β theo v | Ý nghĩa/giới hạn | Phân loại |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | A27 | 168 | 0.0 | 0.0 | Đầu nhánh sống mũi theo code; endpoint canonical chưa chốt | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 1 | A42 | 362 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 2 | A35 | 358 | 0.0 | 0.0 | Cánh/bên mũi proxy; MP129/358 không thuộc sparse NOSE | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 3 | A54 | 291 | 0.05 | 0.0 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 4 | A55 | 321 | 0.0 | 0.06 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 5 | A56 | 314 | 0.0 | 0.06 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 6 | A57 | 17 | 0.0 | 0.06 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 7 | A58 | 84 | 0.0 | 0.06 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 8 | A59 | 91 | 0.0 | 0.06 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 9 | A48 | 61 | -0.05 | 0.0 | Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 10 | A31 | 129 | 0.0 | 0.0 | Cánh/bên mũi proxy; MP129/358 không thuộc sparse NOSE | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |
| 11 | A39 | 133 | 0.0 | 0.08 | Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất | IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED |

Định nghĩa máy đọc được: [c1_roi_contract_proposal_v0.json](eye_c1_evidence/c1_roi_contract_proposal_v0.json). Tọa độ thực tế **488 đỉnh =61×8 ảnh** kèm source index và offset: [roi_preview_vertices.csv](eye_c1_evidence/roi_preview_vertices.csv).

## Raster, chồng lấn, vùng thiếu và biên LBP

1. Dựng đỉnh ở float64, kiểm hữu hạn, D≥1e-6 pixel, diện tích contour≥1e-6 pixel², cạnh dài≥1e-9 pixel và không tự giao/chạm cạnh không kề; tolerance kiểm segment là 1e-9 như code audit. Đây là guard số học đề xuất, không phải ngưỡng chất lượng từ PDF. Lỗi thì vùng đó invalid; không sửa đỉnh để tạo một hình đẹp hơn.
2. Preview dùng contour float32, `cv2.pointPolygonTest >=0` tại tâm pixel nguyên (x,y), kể cả boundary. Chỉ đánh giá trong khung ảnh; không clamp từng đỉnh, không extrapolate mô ngoài ảnh. Preview ghi NumPy/OpenCV version để tái lập.
3. Raw polygons có thể chồng nhau. Để tôn trọng bốn vùng độc lập, đề xuất gán pixel theo ưu tiên **trán+mày → mũi+miệng → má trái theo ảnh → má phải theo ảnh**. Vùng sau trừ các pixel đã được gán; output masks không chồng lấn. Đây là lựa chọn cần chốt, không phải thứ tự ghép histogram.
4. Thứ tự ghép tương lai dự kiến giữ danh sách PDF: **trán+mày → má trái → má phải → mũi+miệng**. Quan hệ trái/phải giải phẫu với theo ảnh phải được tác giả chốt trước khi công nhận thứ tự đó.
5. Pixel không thuộc polygon nào để nguyên không gán. Không cố phủ toàn bộ mặt; số pixel “uncovered” trong JSON tính trên cả ảnh 256², gồm nền/tóc và các vùng mặt không chọn.
6. Thiếu landmark, sai frame, polygon tự giao/degenerate, hết pixel sau clipping/overlap là vùng thiếu. Đề xuất cho extractor tương lai: thiếu một trong bốn vùng bắt buộc thì `missing_C1`, không vector 236 và không zero-fill. Chưa đặt ngưỡng min-pixel mang ý nghĩa chất lượng, chưa triển khai extractor.
7. Với R=2, đề xuất tương lai chỉ nhận tâm LBP khi toàn bộ support nằm trong vùng được gán và trong ảnh. PDF chưa chốt cách xử lý support ở biên hoặc nội suy mẫu tròn; quy tắc này **chưa được phê duyệt và chưa được thực thi để tính LBP**. Không suy ra 59 bin hoặc histogram từ preview masks.
8. Polygon không phân biệt da, tóc, kính, vải hoặc tay. Không tự giao với mask skin Bộ B vì PDF C1 chưa quy định thao tác đó và vùng mày/môi có thể bị loại nhầm. Cần protocol occlusion có thẩm quyền, không chọn theo Top-5.

## Overlay và quan sát thực tế

[Contact sheet tám ảnh toàn khung](eye_c1_evidence/overlays/roi_contact_sheet.png). Đã xem CFD00001/CFD00069, HF00001 và năm trường hợp HF cần review. Tất cả **32 polygon trên tám ảnh** qua kiểm tra hình học; mask sau gán ưu tiên không overlap. Đây không phải kết luận về toàn bộ 1438 ROI hoặc chuẩn giải phẫu.

| Ảnh | Pixel sau gán theo vùng | Overlap raw theo cặp | Quan sát/giới hạn |
| --- | --- | --- | --- |
| cfd_final_00001.png | forehead_brow=5059, cheek_left_viewer=3935, cheek_right_viewer=4289, nose_mouth=4588 | 143 | Bốn vùng dựng được; biên dưới vùng trán có thể bỏ một phần thân lông mày. Cần annotation, không tự tăng margin. |
| cfd_final_00069.png | forehead_brow=6084, cheek_left_viewer=3822, cheek_right_viewer=3975, nose_mouth=6649 | 122 | Biểu cảm làm vùng mũi–miệng biến dạng; vẫn dựng được. Chưa chứng minh tính ổn định kết cấu. |
| hf_merged_00001.png | forehead_brow=5002, cheek_left_viewer=4084, cheek_right_viewer=3370, nose_mouth=5522 | 131 | Trán/mày, hai má và mũi–miệng tách được về hình học; coverage giải phẫu chưa có GT. |
| hf_merged_00333.png | forehead_brow=6573, cheek_left_viewer=3022, cheek_right_viewer=5373, nose_mouth=6092 | 135 | Mặt phụ vẫn xuất hiện ở mép ảnh; chọn một bộ landmark không giải quyết vi phạm dataset. |
| hf_merged_00561.png | forehead_brow=5866, cheek_left_viewer=2436, cheek_right_viewer=5343, nose_mouth=6822 | 128 | Có mặt phụ và tóc phủ vùng trán; mask hình học có thể chứa tóc, không tự sửa ảnh hoặc loại pixel. |
| hf_merged_00722.png | forehead_brow=6103, cheek_left_viewer=3517, cheek_right_viewer=6035, nose_mouth=5667 | 147 | Tay/ngón nằm trong polygon mũi–miệng và gần má; geometric-valid không phải unoccluded-valid. |
| hf_merged_00209.png | forehead_brow=5412, cheek_left_viewer=4444, cheek_right_viewer=2958, nose_mouth=5790 | 114 | Có B thiếu tóc nhưng vẫn có landmark và bốn polygon; không suy ra thiếu B đồng nghĩa thiếu C1. |
| hf_merged_00694.png | forehead_brow=4255, cheek_left_viewer=4141, cheek_right_viewer=2797, nose_mouth=6094 | 147 | Vùng trán chứa phần vải che; kính và biên má còn cần đánh giá. Chưa chứng nhận mô giải phẫu. |

Ảnh có nhãn vertex A/MP và dấu `*` cho offset: [CFD00001](eye_c1_evidence/overlays/cfd_final_00001_c1_roi_vertex_labels.png), [HF00001](eye_c1_evidence/overlays/hf_merged_00001_c1_roi_vertex_labels.png). Ảnh kết hợp: [CFD00001](eye_c1_evidence/overlays/cfd_final_00001_c1_roi_proposal.png), [HF00722 có tay](eye_c1_evidence/overlays/hf_merged_00722_c1_roi_proposal.png). Các ảnh khác nằm cùng thư mục. [roi_preview_validation.json](eye_c1_evidence/roi_preview_validation.json) lưu số pixel, version raster và trạng thái; **semantic_anatomy_verified=false**.

## Các quyết định phải chốt trước khi dùng C1

- Tác giả xác nhận hình PDF là ràng buộc endpoint hay minh họa; cung cấp annotation/canonical mapping cho vùng liên quan, đặc biệt trán, góc hàm, cánh mũi và khóe môi.
- Chốt trái/phải, 15 điểm phụ trợ, vertex/margin, coverage cả vùng lông mày, quy tắc overlap và phần mô bị bỏ lại. Không chọn bằng relevance/Top-5.
- Chốt xử lý tóc/tay/kính/vải, vùng thiếu và min-valid-support; review corpus theo protocol định trước. Dataset vi phạm không được tự “sửa” bằng ROI.
- Đóng băng contract đã duyệt với hash và đánh giá annotation độc lập trước khi viết extractor C1. Đề xuất v0.1 này **chưa được chấp nhận làm ROI giải phẫu chính thức**.
