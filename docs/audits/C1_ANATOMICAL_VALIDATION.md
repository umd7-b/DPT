# C1 anatomical validation — chứng cứ và phần chưa xác minh

Ngày kiểm tra: **24/11/2026**, Asia/Saigon. Trạng thái ứng viên:
**GEOMETRY_VALIDATED — ANATOMY_PROVISIONAL**. `active=false`; chưa sẵn sàng trích xuất C1 chính thức.

Nguồn chuẩn cao nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã kiểm lại trực tiếp.
Đã đọc toàn bộ §2.2/§2.4 bằng pypdf có sẵn ở Python hệ thống và xem hình minh họa68 điểm PDF trang8;
bản trích mới tại [pdf_sections_2_2_2_4.txt](../../outputs/C1_lbp/roi_remediation_v0_4/pdf_sections_2_2_2_4.txt).
Các script geometry dùng `.venv311`, không cài thư viện, không chạy lại MediaPipe.
Đã đọc các contract/spec, audit mapping/full-dataset và hai báo cáo trial100; chúng nằm trong baseline bất biến.

Contract active v0.2 content SHA `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c` và LBP spec `7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851` khớp canonical JSON;
proposal v0.3 file SHA `3a09e0a312005645e7af9d8d6635132c406b87803e235b763f0d1e246d3c37a6`.
Ứng viên mới **C1_ROI_ANATOMICAL_CANDIDATE_v0.4.0** content SHA
`c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39`, file SHA `7535c7ce88ae54f5564f8f9da6bfcad212d7049703afbd9ced850ac285db1f68`.
Source links/hash, thứ tự25/12/12/12 đỉnh và offsets nằm trong JSON; không sửa/đổi contract active.

## Phân loại chứng cứ

| Vùng | PDF quy định | Quan sát/endpoint basis | Quy ước triển khai | Chưa đủ chứng cứ |
|---|---|---|---|---|
| Trán+lông mày | Tên vùng, dựa landmarks | Upper FACE_OVAL15 và native brow lower10; proxy coverage đo toàn kho | Upper oval không phải hairline; bridge/closure, zero margin, pixel rule | Toàn mô trán/mày; bốn continuous-node exceptions; tóc/khăn; canonical auxiliary478 |
| Má trái | Tên vùng, dựa landmarks | Lower-eye, nose-side, mouth-corner và FACE_OVAL endpoints trên mẫu CFD/HF | Viewer-left; offsets0.08D; straight polygon12 đỉnh | Ranh má thật/zygion/gonion, MP129, cơ sở cắt giữa má và mũi-miệng |
| Má phải | Tên vùng, dựa landmarks | Nhóm đối xứng phía phải ảnh, không tự chứng minh đối xứng giải phẫu | Viewer-right; cùng offsets,12 đỉnh | Ranh má thật, MP358, annotation hai bên và khi biểu cảm |
| Mũi+miệng | Tên vùng, dựa landmarks | Bridge nose, eye-inner, nose-side và LIPS;12 đỉnh | u±0.05D,v0.06/0.08D; giữ overlap | Full anatomical boundary; canonical nose-side; tay/răng/môi khi biểu cảm |

Tên bốn vùng là EXACT theo văn bản PDF trong phạm vi hẹp. Membership một điểm trong native contour được
đối chiếu đúng tập cạnh; **endpoint anatomical canonical của mọi vertex vẫn UNVERIFIED** khi chưa có chuẩn.
Số đỉnh/offset và những cạnh nối giữa contour không được PDF quy định. Không tự dùng nhãn EXACT cho toàn polygon.

[MediaPipe FaceLandmarksConnections](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py)
được xem24/11/2026 chỉ xác nhận danh sách contour. Snapshot local hash có trong source_proof/candidate JSON;
không dùng master như canonical mapping478→68 của nhóm. PDF là thẩm quyền cao nhất cho yêu cầu dự án.

## Mọi endpoint và thứ tự polygon ứng viên

A và thứ tự vertex0-based. MP native là0…477; không thêm điểm phụ vào vector A.
L/R mean6 float32 hiện hành, promote float64; D=norm(R−L),u=(R−L)/D,v=(-u_y,u_x).
P'=P_MP+D(αu+βv), nối0→1→…→n−1→0. Upper forehead và lower candidate không offset;
các offset của3 vùng còn lại đúng v0.2. Frame là theo người xem/code; quan hệ trái/phải của PDF cần tác giả chốt.
Overlap raw độc lập, uncovered không được lấp, missing/support guards giữ nguyên, không skin intersection.
CSV có endpoint status từng dòng cho cả3 phiên bản:
[endpoint_contract_review.csv](../../outputs/C1_lbp/roi_remediation_v0_4/endpoint_contract_review.csv).


### forehead_brow

Upper arc15 FACE_OVAL; lower native brow5+5; bridge giữa hai mày và nối thái dương là IMPLEMENTATION DETAIL. Không phải hairline/skin annotation.

| Thứ tự | Index68 (0-based) | MP index | α·D·u | β·D·v | Membership mô hình |
|---:|---|---:|---:|---:|---|
| 0 | Không có trong A68 | 127 | 0.0 | 0.0 | FACE_OVAL |
| 1 | Không có trong A68 | 162 | 0.0 | 0.0 | FACE_OVAL |
| 2 | Không có trong A68 | 21 | 0.0 | 0.0 | FACE_OVAL |
| 3 | Không có trong A68 | 54 | 0.0 | 0.0 | FACE_OVAL |
| 4 | Không có trong A68 | 103 | 0.0 | 0.0 | FACE_OVAL |
| 5 | Không có trong A68 | 67 | 0.0 | 0.0 | FACE_OVAL |
| 6 | Không có trong A68 | 109 | 0.0 | 0.0 | FACE_OVAL |
| 7 | Không có trong A68 | 10 | 0.0 | 0.0 | FACE_OVAL |
| 8 | Không có trong A68 | 338 | 0.0 | 0.0 | FACE_OVAL |
| 9 | Không có trong A68 | 297 | 0.0 | 0.0 | FACE_OVAL |
| 10 | Không có trong A68 | 332 | 0.0 | 0.0 | FACE_OVAL |
| 11 | Không có trong A68 | 284 | 0.0 | 0.0 | FACE_OVAL |
| 12 | Không có trong A68 | 251 | 0.0 | 0.0 | FACE_OVAL |
| 13 | Không có trong A68 | 389 | 0.0 | 0.0 | FACE_OVAL |
| 14 | Không có trong A68 | 356 | 0.0 | 0.0 | FACE_OVAL |
| 15 | Không có trong A68 | 276 | 0.0 | 0.0 | LEFT_EYEBROW |
| 16 | Không có trong A68 | 283 | 0.0 | 0.0 | LEFT_EYEBROW |
| 17 | Không có trong A68 | 282 | 0.0 | 0.0 | LEFT_EYEBROW |
| 18 | Không có trong A68 | 295 | 0.0 | 0.0 | LEFT_EYEBROW |
| 19 | Không có trong A68 | 285 | 0.0 | 0.0 | LEFT_EYEBROW |
| 20 | Không có trong A68 | 55 | 0.0 | 0.0 | RIGHT_EYEBROW |
| 21 | Không có trong A68 | 65 | 0.0 | 0.0 | RIGHT_EYEBROW |
| 22 | Không có trong A68 | 52 | 0.0 | 0.0 | RIGHT_EYEBROW |
| 23 | Không có trong A68 | 53 | 0.0 | 0.0 | RIGHT_EYEBROW |
| 24 | Không có trong A68 | 46 | 0.0 | 0.0 | RIGHT_EYEBROW |

### cheek_left_viewer

A36/41/40/39 thuộc EYE, offset0.08D đẩy xuống dưới mắt; A31/MP129 là nose-side proxy chưa canonical, A48/MP61 thuộc LIPS; A5…A0 thuộc FACE_OVAL. Các cạnh nối không phải contour má được PDF định nghĩa.

| Thứ tự | Index68 (0-based) | MP index | α·D·u | β·D·v | Membership mô hình |
|---:|---|---:|---:|---:|---|
| 0 | 36 | 33 | 0.0 | 0.08 | RIGHT_EYE |
| 1 | 41 | 144 | 0.0 | 0.08 | RIGHT_EYE |
| 2 | 40 | 153 | 0.0 | 0.08 | RIGHT_EYE |
| 3 | 39 | 133 | 0.0 | 0.08 | RIGHT_EYE |
| 4 | 31 | 129 | 0.0 | 0.0 | Không thuộc sparse contours đã xuất |
| 5 | 48 | 61 | 0.0 | 0.0 | LIPS |
| 6 | 5 | 136 | 0.0 | 0.0 | FACE_OVAL |
| 7 | 4 | 172 | 0.0 | 0.0 | FACE_OVAL |
| 8 | 3 | 58 | 0.0 | 0.0 | FACE_OVAL |
| 9 | 2 | 132 | 0.0 | 0.0 | FACE_OVAL |
| 10 | 1 | 93 | 0.0 | 0.0 | FACE_OVAL |
| 11 | 0 | 234 | 0.0 | 0.0 | FACE_OVAL |

### cheek_right_viewer

A45/46/47/42 thuộc EYE, offset0.08D; A35/MP358 nose-side proxy chưa canonical, A54/MP291 thuộc LIPS; A11…A16 thuộc FACE_OVAL. Viewer-right chưa đồng nghĩa anatomical-right.

| Thứ tự | Index68 (0-based) | MP index | α·D·u | β·D·v | Membership mô hình |
|---:|---|---:|---:|---:|---|
| 0 | 45 | 263 | 0.0 | 0.08 | LEFT_EYE |
| 1 | 46 | 373 | 0.0 | 0.08 | LEFT_EYE |
| 2 | 47 | 380 | 0.0 | 0.08 | LEFT_EYE |
| 3 | 42 | 362 | 0.0 | 0.08 | LEFT_EYE |
| 4 | 35 | 358 | 0.0 | 0.0 | Không thuộc sparse contours đã xuất |
| 5 | 54 | 291 | 0.0 | 0.0 | LIPS |
| 6 | 11 | 365 | 0.0 | 0.0 | FACE_OVAL |
| 7 | 12 | 397 | 0.0 | 0.0 | FACE_OVAL |
| 8 | 13 | 288 | 0.0 | 0.0 | FACE_OVAL |
| 9 | 14 | 361 | 0.0 | 0.0 | FACE_OVAL |
| 10 | 15 | 323 | 0.0 | 0.0 | FACE_OVAL |
| 11 | 16 | 454 | 0.0 | 0.0 | FACE_OVAL |

### nose_mouth

A27/MP168 trên sparse NOSE; A42/A39 là mắt với offset0.08D; A35/31 nose-side proxies; A54/48 khóe môi và A55…59 LIPS với offsets u±0.05,v0.06. Không dùng MP1/4 để tự sửa A; đường bao mũi-miệng chưa annotation.

| Thứ tự | Index68 (0-based) | MP index | α·D·u | β·D·v | Membership mô hình |
|---:|---|---:|---:|---:|---|
| 0 | 27 | 168 | 0.0 | 0.0 | NOSE |
| 1 | 42 | 362 | 0.0 | 0.08 | LEFT_EYE |
| 2 | 35 | 358 | 0.0 | 0.0 | Không thuộc sparse contours đã xuất |
| 3 | 54 | 291 | 0.05 | 0.0 | LIPS |
| 4 | 55 | 321 | 0.0 | 0.06 | LIPS |
| 5 | 56 | 314 | 0.0 | 0.06 | LIPS |
| 6 | 57 | 17 | 0.0 | 0.06 | LIPS |
| 7 | 58 | 84 | 0.0 | 0.06 | LIPS |
| 8 | 59 | 91 | 0.0 | 0.06 | LIPS |
| 9 | 48 | 61 | -0.05 | 0.0 | LIPS |
| 10 | 31 | 129 | 0.0 | 0.0 | Không thuộc sparse contours đã xuất |
| 11 | 39 | 133 | 0.0 | 0.08 | RIGHT_EYE |


## Hình minh họa PDF và giải phẫu thật phải tách riêng

Hình68 của PDF trang8 cho thấy layout nhóm hàm/mày/mắt/mũi/miệng trên CFD00001. Theo audit A,
đầu hàm trong implementation thấp hơn vị trí minh họa, MP1=A30 và MP4=A33 khác thứ tự cao-thấp so với hình.
Đây là **khác biệt so với hình minh họa**, không có đủ canonical MP-ID table để kết luận/tự đổi mọi endpoint.
MP129/358 không thuộc sparse NOSE không tự chứng minh sai vùng mũi; sparse contour không phải toàn mô mũi.
Không phát hiện chứng cứ mới đủ để sửa mapping A. C1 candidate giữ nguyên hàm, má và mũi-miệng.

Sai lệch đã chứng minh:4 proper self-intersections v0.2; undercoverage proxy mày toàn kho;
offset v0.3 gây crossing HF00198; các vi phạm dataset mặt phụ/tay có ảnh chứng cứ.
Những điều này khác với khẳng định mọi polygon sai giải phẫu hoặc mọi phụ kiện là vi phạm.
Không có anatomical segmentation annotation nên coverage mô thật cho toàn kho vẫn UNVERIFIED.

## Đo proxy, điểm liên tục và occlusion

| Phiên bản | ROI valid/5752 | Tự giao | Support<64 | Proxy mày min/median/max | Proxy pixel đủ |
|---|---:|---:|---:|---|---:|
| v0_2 | 5748 | 4 | 0 | 44.294606% / 55.547956% / 67.137809% | 0/1438 |
| v0_3 | 5751 | 1 | 0 | 99.635922% / 100.000000% / 100.000000% | 1436/1438 |
| candidate_v0_4 | 5752 | 0 | 0 | 99.635922% / 100.000000% / 100.000000% | 1436/1438 |

HF00198 thiếu3/824 proxy pixels, HF00267 thiếu1/738; mày trái/phải tương ứng còn99.006623%/99.638989%.
V0.4 không tự giao vẫn có4 native point ngoài region; đã kiểm28.760 native brow points:

| Ảnh | Native point ngoài candidate | Signed distance px | Pixel proxy thiếu |
|---|---|---:|---:|
| hf_merged_00055 | MP300 | -0.403582088 | 0 |
| hf_merged_00198 | MP70 | -1.048695317 | 3 |
| hf_merged_00267 | MP300 | -0.618782860 | 1 |
| hf_merged_00463 | MP300 | -0.099358703 | 0 |

Pixel coverage100% của HF00055/HF00463 không bao hàm continuous point membership100%.
Không âm thầm tăng margin hoặc dịch contour để làm bảng đạt100%. Những điểm mày proxy này cũng không phải
annotation đường biên lông thật. Upper FACE_OVAL không phải chân tóc; trên CFD/HF có phần trán nhìn thấy
nằm trên arc; PDF chưa chốt có bắt buộc toàn bộ mô trán hay một vùng ổn định. Cần tác giả/annotation chốt.

| Ảnh đã xem | Quan sát có giới hạn |
|---|---|
| cfd_final_00001 | Đường dưới ứng viên bao quanh proxy mày rõ hơn v0.2. Upper FACE_OVAL nằm dưới đường chân tóc quan sát được, không phải annotation toàn trán. Hai má và mũi-miệng có vẻ hợp vùng trên mẫu này; endpoint vẫn chưa canonical. |
| cfd_final_00069 | Biểu cảm miệng mở làm polygon mũi-miệng bao cả phần răng/miệng mở. Không đổi polygon để làm retrieval đẹp hơn; đây không chứng minh ổn định giải phẫu khi biểu cảm. |
| cfd_final_00112 | Tóc đi vào vùng trên trán; đường bao hình học không tự phân biệt tóc và da. Không gắn nhãn anatomical-valid từ geometry. |
| cfd_final_00268 | Ví dụ v0.2 thiếu coverage proxy nhiều nhất; native lower contour bao trọn proxy pixel trong ứng viên. Mô thật, độ đủ của trán và endpoint má vẫn chưa annotation. |
| hf_merged_00001 | Mày nhìn thấy, đường dưới native phù hợp tổng thể vùng mày trên ảnh mẫu. Các cạnh má/mũi-miệng dựng được; chưa xác minh tất cả endpoint theo PDF. |
| hf_merged_00055 | Tóc mái che một phần trán/mắt theo phía người xem trái. MP300 nằm ngoài candidate 0.403582px dù proxy raster pixel phủ100%; minh họa khác biệt continuous point với integer raster. |
| hf_merged_00069 | V0.2 có cạnh mày cắt upper FACE_OVAL phía phải ảnh; ứng viên không còn cắt trên cùng landmarks. Quan sát này xác nhận hình học, không tạo ground truth giải phẫu. |
| hf_merged_00198 | Kính nằm ngang vùng mắt và một phần biên gần má/thái dương. V0.3 còn giao ở phía trái ảnh. Ứng viên không giao nhưng MP70 ngoài đường oval proxy; không kết luận mô mày/trán đã đủ. |
| hf_merged_00209 | Khăn che tóc và sát biên trán. B thiếu tóc không tự làm thiếu ROI C1; B hair=0 cũng không chứng minh mọi pixel forehead là da. Khăn/occlusion vẫn cần annotation riêng. |
| hf_merged_00267 | V0.2 tự giao phía phải ảnh. Ứng viên hết giao nhưng còn1 pixel proxy mày và MP300 ngoài boundary; không coi gần100% là đủ chứng cứ giải phẫu. |
| hf_merged_00311 | Tóc mái che hầu hết vùng trán và lông mày. Hair mask đã lưu phủ93.364% forehead ứng viên là proxy mô hình, phù hợp cảnh báo nhìn thấy tóc nhưng không phải nhãn ground truth. |
| hf_merged_00333 | Mặt phụ nhìn thấy tại mép ảnh. Thay forehead không giải quyết vi phạm dataset; giữ nguyên ảnh và cờ review. |
| hf_merged_00463 | V0.2 tự giao phía phải ảnh. Ứng viên đơn giản nhưng MP300 vẫn ngoài0.099359px, pixel proxy có thể vẫn phủ100%; không điều chỉnh tiếp để ép số liệu. |
| hf_merged_00561 | Mặt phụ nhìn thấy ở mép trái, tóc phủ phần trán. Giữ nguyên hai vấn đề dataset/occlusion dù polygon mới không tự giao. |
| hf_merged_00694 | Khăn và kính nhìn thấy, ở gần các biên ROI. Hair proxy0 không phải bằng chứng không vải/kính. Chưa đủ cơ sở gắn nhãn sai tiêu chí dataset chỉ từ phụ kiện. |
| hf_merged_00722 | Tay/ngón chồng vùng miệng và phần má. Polygon hình học vẫn chứa vùng bị che; không crop/inpaint, giao skin mask hoặc loại ảnh để hợp thức hóa. |


15 before/after cases và HF00055 supplementary đã xem trực tiếp; **1422 ảnh còn lại chưa được review giải phẫu
bằng mắt trong nhiệm vụ này**. Đủ1438 ảnh được audit hình học/hair proxy/coverage tự động không làm thay đổi
sự thiếu ground truth. Cả16 mẫu cũng chỉ có observations, không được cấp anatomy clearance.
Ảnh A/MP toàn bộ4 vùng:
[CFD00001](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/cfd_final_00001_all_regions_A_MP.png),
[HF00001](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/hf_merged_00001_all_regions_A_MP.png).

## Kết luận sử dụng và các bước còn thiếu

- Có thể dùng v0.4 như **ứng viên hình học để review**, kèm đúng hash/schema và các exception, không tự chuyển
  thành input extractor/gallery hiện hành. Hiện geometry5752/5752; active contract/trial100 vẫn v0.2/96 valid4 missing.
- Cần annotation hoặc quyết định có thẩm quyền cho upper trán/hairline, lower mày, closure thái dương/glabella,
  viewer/anatomical left-right, endpoint má/mũi-miệng, overlap/occlusion, liên hệ sơ đồ68 với478 phụ trợ.
- Cần xem4 continuous-node cases, adjudication các vi phạm dataset và review mô thật độc lập trước nghiệm thu.
  Nếu chốt thay đổi, tạo version mới và kiểm toàn kho; không sửa PDF, A/B, SQL hoặc trial100 đã đóng băng.
- Không có cơ sở công nhận C1 chính thức/toàn hệ thống chỉ từ geometry. Không tạo vector trong nhiệm vụ này,
  không có Top-5 để chọn ROI, không triển khai C2 hoặc fusion.

14664 protected files đã so SHA-256 trước/sau,0 thiếu/đổi;8 geometry tests đạt.
[Kiểm chứng](../../outputs/C1_lbp/roi_remediation_v0_4/verification.json),
[baseline](../../outputs/C1_lbp/roi_remediation_v0_4/baseline_before.json),
[final scope](../../outputs/C1_lbp/roi_remediation_v0_4/final_scope.json).
[Báo cáo remediation đầy đủ và lệnh thực thi](C1_ROI_REMEDIATION_REPORT.md).
