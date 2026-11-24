# C1 ROI anatomical remediation — kết quả có giới hạn

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

## Kết quả toàn kho

Kiểm **1438×4=5752 ROI cho từng phiên bản**, tổng17.256 hàng đo.
Không chỉ lấy bốn ảnh lỗi hoặc contact sheet để kết luận toàn kho.

| Phiên bản | ROI valid/5752 | Tự giao | Support<64 | Proxy mày min/median/max | Proxy pixel đủ |
|---|---:|---:|---:|---|---:|
| v0_2 | 5748 | 4 | 0 | 44.294606% / 55.547956% / 67.137809% | 0/1438 |
| v0_3 | 5751 | 1 | 0 | 99.635922% / 100.000000% / 100.000000% | 1436/1438 |
| candidate_v0_4 | 5752 | 0 | 0 | 99.635922% / 100.000000% / 100.000000% | 1436/1438 |

Candidate hết tự giao, không có out-of-image vertex hoặc ROI thiếu support, nhưng **1438/1438 ảnh vẫn thiếu
annotation giải phẫu độc lập**. Coverage bảng là polygon proxy của mô hình, không phải độ phủ mô mày thật.
Full-dataset CSV/JSON và contact sheets nằm riêng tại `outputs/C1_lbp/roi_remediation_v0_4/`.

## Nguyên nhân chính xác bốn lỗi v0.2

| Ảnh | Cạnh upper FACE_OVAL | Cạnh mày v0.2 (offset+0.05D·v) | Giao điểm (x,y) |
|---|---|---|---|
| hf_merged_00069 | MP389 → MP356 (vertex[13, 14]) | A26/MP300 → A25/MP293 (vertex[15, 16]) | 195.127496637, 87.973927046 |
| hf_merged_00198 | MP162 → MP21 (vertex[1, 2]) | A18/MP63 → A17/MP70 (vertex[23, 24]) | 61.708473538, 76.788782588 |
| hf_merged_00267 | MP251 → MP389 (vertex[12, 13]) | A26/MP300 → A25/MP293 (vertex[15, 16]) | 192.748555820, 84.605495113 |
| hf_merged_00463 | MP389 → MP356 (vertex[13, 14]) | A26/MP300 → A25/MP293 (vertex[15, 16]) | 193.941318970, 86.410776275 |

Index vertex/A68 dùng0-based. Đã xác minh giao bên trong hai segment bằng determinant và linear solve độc lập,
residual<1e-10. Tọa độ các endpoint, parameters t/u, frame mắt và source landmark row hash nằm trong
[four_cases_intersections.json](../../outputs/C1_lbp/roi_remediation_v0_4/four_cases_intersections.json).
Hash ảnh gốc được nối theo image_id từ catalog đã xác thực, ghi trong diagnostic,
contact_sheet_selection.json và baseline; không suy đoán tọa độ hoặc nguồn ảnh.

Cả bốn giao đều là **cạnh nội bộ upper FACE_OVAL với cạnh nội bộ mày**; không giao nào dùng cạnh đóng24→0.
Vì vậy không quy hết lỗi cho cạnh đóng polygon. Upper arc15 điểm có14 cạnh native
đúng thứ tự, hai đường mày có thứ tự vùng hợp lý, nhưng kết hợp endpoint thưa + offset chung không bảo đảm
hai contour không cắt ở thái dương. Không có bằng chứng để sửa detector hoặc mapping A.

### Tách endpoint/offset/đường nối

| Ảnh | v0.2 | Upper-brow v0.2 bỏ offset: chỉ test4 case | v0.3 | v0.4 |
|---|---:|---:|---:|---:|
| hf_merged_00069 | 1 | 0 | 0 | 0 |
| hf_merged_00198 | 1 | 1 | 1 | 0 |
| hf_merged_00267 | 1 | 2 | 0 | 0 |
| hf_merged_00463 | 1 | 2 | 0 | 0 |

Các số là số proper intersections, không phải điểm chất lượng retrieval. Counterfactual bỏ offset của đường
upper-brow cũ chỉ phân tích bốn ảnh: HF00069 hết giao, HF00198 vẫn giao, HF00267/HF00463 tăng hai giao.
Do đó chỉ xóa offset0.05 trên contour A cũ không phải cách sửa chung và không khắc phục proxy undercoverage.
Không kích hoạt counterfactual, không dùng hull/xóa đỉnh/reorder/clip vào oval để che giao.

V0.3 dùng lower-brow native +0.02D·v: hết ba lỗi nhưng HF00198 còn giao
**MP127→MP162 (0→1) với MP53+offset→MP46+offset (23→24)** tại
**(62.568903833,81.214931423)**. Native MP46=(62.339294434,79.981666565), sau shift thành
(62.312974548,81.522940826); displacement=(-0.026319885,+1.541274261)px.
Signed cross với MP127→162 đổi **+0.807109411→−5.660792207**: downshift theo frame mắt không phải
inward normal của cạnh oval nghiêng. Đây là bằng chứng số học cho crossing do quy tắc offset v0.3 ở case này,
không khẳng định mọi landmark là ground truth hoặc coi kính là nguyên nhân detector khi thiếu nhãn chuẩn.

## Ứng viên và căn cứ thay đổi

V0.4 giữ nguyên15 upper FACE_OVAL và25 vertex count; dùng lower chain
`MP276,283,282,295,285,55,65,52,53,46` **không offset**, thay đường mày A26…A17+0.05D của v0.2.
Không xóa đỉnh tùy ý, không đổi toàn bộ thứ tự để làm polygon hợp lệ. Bốn cạnh mỗi nửa lower chain có
membership EYEBROW native; bridge285→55 và hai đường nối thái dương vẫn là quy ước polygon chưa được
PDF/annotation chốt. Zero offset loại padding chưa có căn cứ giải phẫu; không phải giá trị được tìm bằng
quét tham số để đạt geometry hoặc Top-5. [Decision trước census](../../outputs/C1_lbp/roi_remediation_v0_4/decision_before_census.json)
đóng băng lựa chọn trước khi xem các metric ứng viên toàn kho.

Ba vùng má trái/má phải/mũi-miệng giữ nguyên cả definitions, coordinates, mask bytes, area và support;
mapping A và vector không đổi. Giữ frame viewer/code left-right, mean6 float32 mắt rồi float64 D/u/v,
pixel rule pointPolygonTest>=0 với contour float32, clipping chỉ khung ảnh; raw overlap độc lập.
Không đưa candidate vào Context/extractor/gallery trial100. Các rule LBP P8,R2,59 bins,L1,Chi-square0.5 và
epsilon/gray/bilinear/support21 trong spec cũ giữ nguyên; nhiệm vụ này không gọi extractor.

Tài liệu chính thức [FaceLandmarksConnections](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py)
xác nhận các cạnh mày/oval; [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
mô tả output478 landmarks. Chỉ dùng để xác nhận topology mô hình, không thay PDF hoặc chứng nhận mô thật.
Đối chiếu chính xác khi tính toán dùng native_mediapipe_topology.json đã hash, không lệ thuộc master thay đổi.

## Coverage lông mày và giới hạn giải phẫu

Proxy mỗi mày là polygon đóng từ5 điểm upper+5 điểm lower; cạnh đóng hai đầu do audit quy ước, không phải
annotation pixel lông mày. V0.2 min/median/max44.294606%/55.547956%/67.137809%.
V0.3/v0.4 min99.635922%, median/max100%; cả hai phủ đủ integer proxy ở1436 ảnh.
HF00198 phủ821/824 pixel (thiếu3 phía trái theo ảnh; riêng mày trái99.006623%), HF00267 phủ737/738
(thiếu1 phía phải; riêng mày phải99.638989%). Giữ nguyên số liệu, không chỉnh contract để ép100%.

| Ảnh | Native point ngoài candidate | Signed distance px | Pixel proxy thiếu |
|---|---|---:|---:|
| hf_merged_00055 | MP300 | -0.403582088 | 0 |
| hf_merged_00198 | MP70 | -1.048695317 | 3 |
| hf_merged_00267 | MP300 | -0.618782860 | 1 |
| hf_merged_00463 | MP300 | -0.099358703 | 0 |

Ngoài2 pixel-mask exceptions còn có4 ảnh với một native landmark ngoài candidate (28.760 điểm đã kiểm).
HF00055/HF00463 vẫn có proxy integer coverage100% vì phần thiếu là nhỏ ở tọa độ phân số, không chứa tâm pixel
nguyên bị loại. [CSV](../../outputs/C1_lbp/roi_remediation_v0_4/native_brow_outside_points.csv) và
[ảnh exceptions](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/native_brow_fractional_exceptions.png).
Geometry-valid, integer proxy coverage và continuous point membership là ba phép đo khác nhau;
không phép nào xác nhận anatomical-valid. Native upper oval cũng không phải đường chân tóc/trán có annotation.

## Diện tích, pixels, support và thay đổi từng ảnh

| Variant / vùng | Area px² min/median/max | Raw pixels min/median/max | Support min/median/max |
|---|---|---|---|
| v0_2 / forehead_brow | 3455.476 / 5809.521 / 7751.131 | 3451.000 / 5812.000 / 7757.000 | 2492.000 / 4762.500 / 6719.000 |
| v0_2 / cheek_left_viewer | 2153.525 / 4343.234 / 7416.949 | 2155.000 / 4347.500 / 7418.000 | 1645.000 / 3704.500 / 6610.000 |
| v0_2 / cheek_right_viewer | 2090.893 / 4343.246 / 7432.262 | 2095.000 / 4343.000 / 7429.000 | 1571.000 / 3698.500 / 6628.000 |
| v0_2 / nose_mouth | 3893.343 / 5453.834 / 7685.283 | 3887.000 / 5455.000 / 7686.000 | 3326.000 / 4741.000 / 6835.000 |
| v0_3 / forehead_brow | 4179.103 / 6693.665 / 8668.103 | 4179.000 / 6694.500 / 8655.000 | 3202.000 / 5630.500 / 7599.000 |
| v0_3 / cheek_left_viewer | 2153.525 / 4343.234 / 7416.949 | 2155.000 / 4347.500 / 7418.000 | 1645.000 / 3704.500 / 6610.000 |
| v0_3 / cheek_right_viewer | 2090.893 / 4343.246 / 7432.262 | 2095.000 / 4343.000 / 7429.000 | 1571.000 / 3698.500 / 6628.000 |
| v0_3 / nose_mouth | 3893.343 / 5453.834 / 7685.283 | 3887.000 / 5455.000 / 7686.000 | 3326.000 / 4741.000 / 6835.000 |
| candidate_v0_4 / forehead_brow | 3939.327 / 6449.616 / 8406.987 | 3932.000 / 6453.000 / 8392.000 | 2955.000 / 5385.500 / 7337.000 |
| candidate_v0_4 / cheek_left_viewer | 2153.525 / 4343.234 / 7416.949 | 2155.000 / 4347.500 / 7418.000 | 1645.000 / 3704.500 / 6610.000 |
| candidate_v0_4 / cheek_right_viewer | 2090.893 / 4343.246 / 7432.262 | 2095.000 / 4343.000 / 7429.000 | 1571.000 / 3698.500 / 6628.000 |
| candidate_v0_4 / nose_mouth | 3893.343 / 5453.834 / 7685.283 | 3887.000 / 5455.000 / 7686.000 | 3326.000 / 4741.000 / 6835.000 |

Stat v0.2/v0.3 gồm cả mask invalid với vai trò chẩn đoán; không dùng area tự giao làm feature.
Tất cả1438 ảnh thay pixel **chỉ ở forehead_brow**. Added pixels min/median/max=405.000 / 619.000 / 992.000;
removed=0.000 / 0.000 / 13.000. Diện tích/pixel từng ROI, thay đổi từng ảnh, hair proxy và
reason nằm trong [roi_metrics.csv](../../outputs/C1_lbp/roi_remediation_v0_4/roi_metrics.csv),
[image_metrics.csv](../../outputs/C1_lbp/roi_remediation_v0_4/image_metrics.csv),
[175436 vertex rows cho v0.3/v0.4](../../outputs/C1_lbp/roi_remediation_v0_4/candidate_vertices.csv).

| Cặp vùng (candidate; bằng v0.2 từng ảnh) | Pixel min/median/max |
|---|---|
| forehead_brow / cheek_left_viewer | 0.000 / 0.000 / 0.000 |
| forehead_brow / cheek_right_viewer | 0.000 / 0.000 / 0.000 |
| forehead_brow / nose_mouth | 0.000 / 0.000 / 0.000 |
| cheek_left_viewer / cheek_right_viewer | 0.000 / 0.000 / 0.000 |
| cheek_left_viewer / nose_mouth | 44.000 / 70.000 / 107.000 |
| cheek_right_viewer / nose_mouth | 43.000 / 70.000 / 104.000 |

Không cặp nào thay số overlap so với v0.2 trên bất kỳ ảnh nào; unique overlap91…208px, max memberships2.
Independent inclusion-exclusion xác minh raw sum−pair sum=union. Không ownership subtraction.

## Occlusion và dataset

Đã xem trực tiếp **16 ảnh khác nhau**:15 case sheets gồm CFD/HF, bốn lỗi và các extrema định trước,
cộng HF00055 từ continuous-node exceptions; hai overlay lớn có A68/MP labels cho đủ4 vùng.
Đây là review mẫu, không phải manual ground truth cho1438 ảnh.
[Quan sát từng ảnh](../../outputs/C1_lbp/roi_remediation_v0_4/visual_observations.json),
[bốn trang trước/sau](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/overview_01.png).
HF00311 tóc mái phủ trán, saved B hair proxy93.364070% forehead candidate; HF00055/CFD00112 cũng có tóc
đi vào ROI trên hình. HF00198/HF00694 có kính, HF00209/HF00694 có khăn.
B hair mask=0 ở hai ảnh khăn không phải clearance vải/kính/skin; không tự dùng proxy hair như nhãn mô thật.
HF00333/HF00561 vẫn có mặt phụ; HF00722 tay che miệng/má vẫn nằm trong ROI không sửa.
Các vi phạm dataset đã xác nhận giữ nguyên và tách khỏi geometric validity; không suy nhãn danh tính/tuổi/giới.

## Đối chiếu PDF và điều cần chốt

PDF §2.4 cho bốn tên vùng và landmark-based partition, không liệt kê MP endpoints, upper hairline,
margin, polygon graph, frame trái/phải, overlap hoặc occlusion masks. Vì vậy chứng minh rõ **undercoverage
proxy của v0.2**, nhưng chưa đủ tuyên bố mức undercoverage mô thật theo một ground truth không tồn tại.
Các khác biệt vị trí hàm/mũi của A với hình minh họa PDF trang8 (đặc biệt MP1/MP4) vẫn là findings từ
A_MAPPING_FINAL_REVIEW, không tự coi chúng là canonical mapping thay thế hoặc tự sửa A.
Endpoint vùng má/mũi-miệng và độ đầy đủ vùng trán cần annotation/xác nhận có thẩm quyền.
Chi tiết endpoint/phân loại ở [C1_ANATOMICAL_VALIDATION.md](C1_ANATOMICAL_VALIDATION.md).

Có thể xử lý bằng quy ước triển khai có version: raster/support/overlap, dùng lower native chain và loại
downshift không được chứng minh, identity join/provenance và guard missing. Các quy ước không cấp chứng nhận
giải phẫu. Trước C1 chính thức cần: tác giả chốt frame và ý nghĩa4 vùng; annotation upper/lower forehead/mày,
hai má/mũi-miệng và occlusion; adjudicate4 continuous-node exceptions; review dataset vi phạm; thẩm định lại
contract và toàn kho độc lập, rồi nghiệm thu version mới nếu đủ chứng cứ. Không tự thực hiện bước kích hoạt.

## Kiểm chứng và bảo toàn

8 tests geometry đạt, census độc lập kiểm2876 forehead polygons v0.3/v0.4 bằng determinant CSV,
đủ17.256 ROI metric rows,25.884 overlap rows. [verification.json](../../outputs/C1_lbp/roi_remediation_v0_4/verification.json),
[tests.log](../../outputs/C1_lbp/roi_remediation_v0_4/tests.log).
Baseline **14664 file** (gồm PDF,dataset,A/B source/vector/stats/calibration,SQLite cũ và toàn bộ trial100)
được kiểm trước/sau **0 thay đổi/thiếu**. Không tính lại96 vector trial, không tạo C1/C2 mới, không fit hoặc
calibration/Top-5/fusion, không chạy lại MediaPipe và không ghi SQLite.
[Baseline](../../outputs/C1_lbp/roi_remediation_v0_4/baseline_before.json),
[final scope](../../outputs/C1_lbp/roi_remediation_v0_4/final_scope.json),
[manifest mới](../../outputs/C1_lbp/roi_remediation_v0_4/created_files_manifest.json).

Lệnh PowerShell thực tế tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/audit_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/audit_remediation.py --check-completed
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/render_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/verify_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/review_native_brows.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/write_reports.py
```

Census đầu ghi đủ toàn bộ CSV/JSON rồi gặp lỗi **in summary ra stdout** do NumPy int64 JSON serializer,
exit1; đã sửa serialization log, kiểm completed CSV/JSON qua `--check-completed` exit0 và verifier exit0.
Không đổi geometry/rule/parameter hoặc chạy lại census để cải thiện số liệu; giữ nguyên artifacts đã ghi.
Các renderer/verifier/finalizer từ chối ghi đè bộ đã hoàn tất. Kết luận giới hạn vẫn
**GEOMETRY_VALIDATED / ANATOMY_PROVISIONAL**, không kích hoạt candidate và chưa triển khai C1 chính thức.
