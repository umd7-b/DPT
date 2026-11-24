# Dataset — đối chiếu §1.1–1.3

Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.


**Kết luận:** định dạng/số lượng/catalog được kiểm chứng, nhưng dataset hiện có vi phạm tiêu chí không có mặt phụ và không che miệng. Chưa thể chứng nhận mọi ảnh chính diện,1135 người độc lập, độ tuổi18–60 hoặc lịch sử tiền xử lý. Không thay đổi/xóa bất kỳ ảnh hay nhãn nào.

## Phép đo thực tế toàn bộ1438 ảnh

Đọc trực tiếp PNG IHDR và decodeOpenCV:1438/1438 RGB8,256×256, tỉ lệ1:1;1438 SHA khớp metadata,0 duplicate byte,0 mồ côi;CFD710/HF728. Độ duy nhất byte không phải độ duy nhất danh tính. “PNG chất lượng95” ở PDF không ánh xạ một-một sang tham số nén của PNG; thiếu log encoder nên không bịa trị số nén/chất lượng hoặc đổi định dạng.

Detector audit dùng model FaceLandmarker cục bộ với `num_faces=5`, không dùng cấu hình capped1 của extractor làm phép kiểm một mặt. Kết quả model:1438 ảnh đều trả1 face,478 landmarks; lưu số lượng từng ảnh và toàn bộ landmarks trong `dataset_landmarks478.npz`. **Mô hình vẫn bỏ sót mặt phụ nhìn thấy ở mép**, nên không coi1438×1 là GT hay chứng nhận tiêu chí. Các Euler từ matrix model chưa hiệu chuẩn camera, không dùng làm bằng chứng chính xác yaw/pitch<5°.

| Chỉ số model/proxy | Min | Median | Max |
|---|---:|---:|---:|
| roll_deg | -2.94861194 | -0.02081655 | 2.65115746 |
| ipd_percent_width | 28.28741846 | 30.66187965 | 33.56603044 |
| eye_center_y_percent | 37.01634258 | 39.78226160 | 41.80630222 |
| eye_center_x_percent | 48.42840508 | 50.02143184 | 51.53748865 |
| mesh_height_percent | 69.56522763 | 78.56407389 | 89.49852437 |
| iris_ipd_percent_width | 27.58422078 | 30.74760477 | 33.32609845 |
| iris_eye_center_y_percent | 36.46205366 | 39.25197423 | 41.97834134 |
| iris_roll_deg | -3.18319589 | 0.03512384 | 2.65742968 |

`roll_deg` dùng đường nối centroid6 mí; `iris_*` dùng MP468/473; hai định nghĩa được đo riêng để không tùy tiện đồng nhất tâm mí với tâm đồng tử. Centroid IPD có9 ảnh ngoài khoảng27.23–32.61% của PDF; median30.66188% khác29.45%. Iris median30.74760% cũng khác29.45%. Đây là **chênh lệch quan sát bằng model cần điều tra**, còn UNVERIFIED vì chưa có phép đo mắt chuẩn và provenance alignment để kết luận GT sai đúng. Không tự điều chỉnh scale ảnh cho khớp thống kê PDF.

Mesh-height median78.56407% gần78.6% trong PDF, nhưng mesh extrema không mặc nhiên là face bounding box/đỉnh đầu-cằm. Tâm mắt y và mặt nghiêng có phân bố đã đo; thiếu tolerance của “cố định/40%/giữa ảnh” nên không chứng nhận chính xác mọi ảnh hoặc tự đặt ngưỡng sau khi xem dữ liệu. Ngưỡng sàng lọc2 điểm phần trăm ở CSV chỉ là heuristic công khai để chọn review.

## Các ảnh cần xem xét, có bằng chứng

| Ảnh | Quan sát trực tiếp / bằng chứng | Trạng thái |
|---|---|---|
| hf_merged_00333.png | Partial secondary faces visibly present at left and right borders; dataset_mask_review_page1.png row 2 | DEVIATION |
| hf_merged_00561.png | Partial secondary face with visible eye at left border; dataset_mask_review_page1.png row 3 | DEVIATION |
| hf_merged_00722.png | Hand/fingers overlap the mouth/lower face; some finger skin is selected in raw skin mask; dataset_mask_review_page2.png row 2 | DEVIATION |
| hf_merged_00694.png | Head covering; hair mask only 355 pixels at upper edge, representativeness unverified; dataset_mask_review_page2.png row 1 | UNVERIFIED |
| hf_merged_00209.png | Head covering; raw hair mask empty, missing B retained explicitly; dataset_mask_review_page2.png row 3 | APPROVED IMPLEMENTATION DETAIL |
| hf_merged_00313.png | Historical raw_face_count flag; current detector returns one. Visual review does not settle all historical frame context; dataset_mask_review_page1.png row 1 | UNVERIFIED |
| hf_merged_00610.png | Historical face-count flags and visible hat; fresh detector returns one. No visual proof of a second complete face in this crop; dataset_mask_review_page1.png row 4 | UNVERIFIED |
| hf_merged_00676.png | Rare bright hair color; not a justification for formula changes or deleting image; dataset_mask_review_page2.png row 4 | UNVERIFIED |

- [Contact sheet1](evidence/dataset_mask_review_page1.png): HF00313,00333,00561,00610; ảnh gốc/raw skin/raw hair.
- [Contact sheet2](evidence/dataset_mask_review_page2.png): HF00694,00722,00209,00676.
- [visual_review_findings.csv](evidence/visual_review_findings.csv):8 quan sát thủ công của audit.
- [dataset_model_review_candidates.csv](evidence/dataset_model_review_candidates.csv): toàn bộ ảnh được phép đo model/heuristic gắn cờ, kèm số đo và lý do. Cờ không phải nhãn GT hoặc đề nghị tự xóa ảnh.
- Dataset `review_candidates.csv` lịch sử có9 cờ; audit không tự coi tất cả đúng, vẫn giữ riêng nguồn/lý do. HF00313/HF00610 được báo cờ lịch sử nhưng chưa đủ quan sát để kết luận cùng lỗi DS05 như HF00333/HF00561.

Ảnh HF00722 cho thấy tay/ngón chồng vùng miệng, vi phạm rõ yêu cầu §1.2. Raw skin còn chọn da tay, nhưng “mask chứa da” không đồng nghĩa đã xác minh đúng facial ROI hoặc đo được segmentation accuracy. HF00694/HF00209 có khăn che tóc; PDF yêu cầu không che mắt/mũi/miệng, không cấm riêng mọi khăn trùm tóc, vì thế không tự đánh DEVIATION chỉ từ khăn.

## Danh tính và metadata

710 dòng CFD có person_id,407 ID phân biệt theo nguồn và303 dòng lặp thêm;728 HF không có person_id. Con số407+728=1135 chỉ đúng nếu giả định mỗi HF là người mới khác nhau và không trùng CFD, điều chưa được dữ liệu xác minh. Không có nhãn cảm xúc đủ để chứng nhận303 dòng lặp đều đúng diễn giải cảm xúc của PDF. Không suy đoán tuổi/giới/sắc tộc/danh tính từ ảnh; catalog hiện thiếu trường tuổi và provenance nhãn đủ để xác nhận18–60.

CSV lưu ID/name/path/hash và nguồn; không có vị trí x/y hai mắt đầy đủ, chưa tìm thấy hiện thực CSDL hoặc log alignment gốc chứng minh lưu vị trí hai mắt vào DB. Ảnh PNG cuối không chứng minh đã crop/rotate/resize bằng bicubic. `map_68_landmarks.py` dùng INTER_CUBIC để phóng ảnh minh họa không phải bằng chứng bicubic tiền xử lý dataset.

## Bảng đối chiếu dataset

| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |
|---|---|---|---|---|---|---|
| DS01 — Ít nhất1000 ảnh và đúng1438 ảnh hiện hành | 3–4 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | 1438 PNG, metadata1438 | dataset_verification.json | EXACT | Giữ nguyên toàn bộ ảnh. |
| DS02 — Nguồn CFD và HF, ID/tên file và metadata riêng | 4 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | CFD710 + HF728; unique IDs, hash/name mapping | dataset_verification.json; metadata.csv | EXACT | Xác nhận nguồn được ghi trong catalog, không suy ra toàn bộ lịch sử thu thập. |
| DS03 — 1135 người phân biệt và303 ảnh cảm xúc của cùng người | 4 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | 710 CFD rows có407 source-scoped IDs +303 extra;728 HF không có person_id | dataset_verification.json | UNVERIFIED | Không giả định728 HF đều khác nhau hoặc không trùng CFD; emotion labels không có. |
| DS04 — Quy trình giữ ảnh nhãn nữ và lọc bằng detector | 4–5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Metadata hiện không có nhãn giới/tuổi hoặc log lọc gốc đủ | metadata_fields; source_inventory; dataset source files | UNVERIFIED | Cần provenance nhãn nguồn, không suy đoán từ ngoại hình. |
| DS05 — Một mặt duy nhất, không có mặt phụ | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Detector num_faces5 báo1 trên1438; hình thật có mặt phụ | visual_review_findings.csv: HF00333 và HF00561 | DEVIATION | Không xóa ảnh; gắn cờ lỗi tiêu chí và chuẩn bị dataset phiên bản kiểm duyệt riêng nếu được giao. |
| DS06 — Chính diện, yaw/pitch nhỏ hơn5° | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Model-transform Euler chỉ proxy, chưa hiệu chuẩn | dataset_measurements.csv | UNVERIFIED | Không nhận proxy làm GT; cần pose/annotation protocol độc lập. |
| DS07 — Đường nối hai mắt nằm ngang | 5–6 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Roll centroid median−0.020817°, range−2.948612..2.651157° | dataset_verification.json; iris_roll đo riêng | UNVERIFIED | Ảnh gần ngang theo model; PDF không cho tolerance cho khái niệm nằm ngang cố định. |
| DS08 — Tâm khuôn mặt căn giữa, tỉ lệ tương đồng | 3–5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Eye-center x median50.0214%, range48.4284..51.5375% | dataset_verification.json | UNVERIFIED | Proxy tâm mắt không thay GT tâm mặt; cần tolerance quy định trước. |
| DS09 — Mặt chiếm70–90%, median78.6% chiều cao | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Mesh-height proxy median78.5641%, range69.5652..89.4985% | dataset_verification.json | UNVERIFIED | Mesh bbox không phải face detector bbox/đỉnh đầu-cằm đã hiệu chuẩn; không khẳng định chính xác78.6%. |
| DS10 — Mắt, mũi, miệng không bị che bởi tay/phụ kiện/tóc | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | HF00722: ngón tay che vùng miệng | dataset_mask_review_page2.png row2 | DEVIATION | Giữ nguyên ảnh và nhãn; lưu bằng chứng, không tối ưu mask/ranking để che vấn đề. |
| DS11 — Tất cả cùng256×256,1:1 | 4–6 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | 1438/1438 PNG IHDR width=height=256 | dataset_measurements.csv; đọc trực tiếp IHDR và OpenCV | EXACT | Giữ nguyên. |
| DS12 — PNG, RGB8 | 4–6 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | IHDR bit_depth8, color_type2; decoded uint8 H×W×3 | dataset_verification.json | EXACT | OpenCV đọc BGR là quy ước API, không phải ảnh nguồn sai RGB. |
| DS13 — PNG “chất lượng95”, cùng mức nén | 4,6 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | PNG lossless; số95 không xác định duy nhất mức nén/encoder | Đọc PDF/IHDR; không có encoder logs được xác nhận | UNVERIFIED | Không thay bằng JPEG hoặc bịa thông số95; cần provenance encode. |
| DS14 — Độ tuổi18–60 và đa dạng tuổi/sắc tộc/tóc/ánh sáng | 5–6 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Catalog thiếu tuổi và nhãn phân bố đủ để kiểm tra định lượng | dataset metadata fields | UNVERIFIED | Không suy luận thuộc tính nhân khẩu từ ảnh. |
| DS15 — Tiền xử lý loại0 hoặc nhiều hơn1 mặt | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Pipeline trích A dùng num_faces1, không đủ chứng minh bộ lọc gốc; mặt phụ còn tồn tại | geometry_features.py; visual review; source preprocessing chưa đủ | UNVERIFIED | Tiêu chí ảnh đã vi phạm ở DS05; quy trình lọc gốc riêng chưa xác minh. |
| DS16 — 478→68 trong bước căn chỉnh gốc | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Có extractor hiện tại, thiếu log preprocessing gốc theo từng ảnh | source_listing.txt; dataset files | UNVERIFIED | Không lấy inference mới làm bằng chứng lịch sử. |
| DS17 — IPD median29.45%, min27.23%, max32.61% chiều rộng | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Centroid: median30.66188%, range28.28742..33.56603%; iris:30.74760%,27.58422..33.32610% | dataset_verification.json; 9 centroid IPD ngoài khoảng PDF | UNVERIFIED | Chênh lệch đo cần điều tra định nghĩa tâm mắt/provenance; chưa kết luận từ model estimate là GT. |
| DS18 — Tâm hai mắt ở40% chiều cao | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Centroid y median39.78226%, range37.01634..41.80630%; iris median39.25197% | dataset_verification.json | UNVERIFIED | Chưa có tolerance/định nghĩa chuẩn đủ; không chứng nhận40% mọi ảnh. |
| DS19 — Crop vuông đỉnh đầu→cằm, một phần tóc/vai; bicubic | 5 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | Ảnh output không suy ra chắc interpolation/crop history | Không thấy pipeline warpAffine/resize bicubic preprocessing nguồn được truy vết | UNVERIFIED | Cần source/log gốc, không resize hay crop lại trong audit. |
| DS20 — Metadata trong CSDL gồm ID/path/vị trí hai mắt | 4–5,16 | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | CSV hiện có ID/path nhưng không có eye x/y đầy đủ; không xác minh DB ngoài workspace | metadata.csv fields; repo code/storage search | UNVERIFIED | Nêu thiếu bằng chứng CSDL/eye-coordinate persistence, không tự dựng DB. |
| DS21 — Tính toàn vẹn, không trùng byte/mồ côi | 4 (catalog), yêu cầu audit | D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py | 1438 SHA khớp,0 duplicate byte, tập file=metadata | dataset_verification.json; protected_before.json | EXACT | Không đồng nhất0 duplicate byte với0 duplicate identity. |
