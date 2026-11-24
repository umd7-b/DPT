# Xác minh số học C1 LBP236 — technical trial100

Ngày thực hiện: **24/11/2026**, Asia/Saigon.

**EXPERIMENTAL_TECHNICAL_TRIAL** — **ROI_ANATOMY_STATUS=PROVISIONAL**.
Thành công số học không chứng nhận ROI giải phẫu hoặc toàn hệ thống.

PDF chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`.
Đã đọc trực tiếp §2.4 từ PDF vật lý trang13–16 bằng `pypdf` có sẵn trong Python hệ thống;
extractor/tests chạy `.venv311`, không cài thêm thư viện. Bản trích và nguồn nằm trong evidence của trial.

Khóa `C1_ROI_RAW_CONTRACT_v0.2.0`: `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c`;
`C1_LBP_236_IMPLEMENTATION_SPEC_v0.1.0`: `7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851`;
codebook file SHA-256 `7eb6a7a12b7374efb50d487f2e399b3475ef0e03594da35971bf083b0188ac94`.
Cả hai content hash được tính lại từ JSON canonical (bỏ trường content_sha256), so với giá trị yêu cầu;
sai schema/hash thì dừng. Không sửa spec, mapping A hoặc áp dụng proposal forehead v0.3.

## Bằng chứng kiểm thử độc lập

**26 tests đạt**,0 failure/error/skip;
[unit/integration log](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/unit_integration_tests.log),
[JSON trạng thái](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/unit_integration_tests.json).
Tests nằm ở tests/test_c1_lbp236.py và tests/test_c1_trial100_integration.py.
Oracle features/C1_lbp/verification/scalar_oracle.py không import target;
expected codebook được dựng bằng run bit1 và phép quay phải, không gọi LUT builder production.
Expected gray dùng Python int từng pixel; stencil/support duyệt scalar thay cv2.erode;
mask quét full256² với contour float32 của vertex CSV frozen thay dùng polygon builder target.
OpenCV pointPolygonTest là primitive chung bắt buộc theo contract; không tuyên bố oracle raster hoàn toàn khác backend.
Expected bilinear là phép lerp scalar có cùng thứ tự quy định, không dùng phép nội suy NumPy production.

Codebook kiểm đủ256 mã,58 uniform riêng và198 mã vào bin58; test stencil dựng riêng đủ256 bit words;
orientation khác nhau có nhãn khác, không dùng10-bin rotation invariant.
Gray fixtures blue29,green150,red76,white255,black0 và fixture ngẫu nhiên xác nhận tránh overflow.
Constant73 cho raw255/bin57; equality bit1; chênh thấp1e-12 phải bit0.
Bilinear ở sqrt(2) kiểm analytic affine plane và fixture scalar; không round5 decimal/intensity.
Support21 gồm5+4+3+4+5 điểm; bỏ bất kỳ điểm nào làm tâm không eligible, bỏ điểm(1,0) không làm mất tâm.
Ngoài raw ROI không ảnh hưởng counts; hai polygon trùng vẫn giữ đủ histogram cả hai.
Self-cross/missing/<64/nonfinite input đi missing cả ảnh; unit test chặn mọi lời gọi LBP ở self-cross.
Chi-square symmetric/nonnegative/self0, fixture bốn nhóm one-hot khác bin cho `4/(1+1e-8)`, xác minh hệ số0.5.
Reject vector global-L1 sai schema. Query/gallery hash mismatch phải reject, không fit tham số.

## Kết quả dữ liệu thật

100 bản ghi serialized được kiểm;96 vector236 float64 và counts uint64 round-trip chính xác.
Cả96 query adapter tái trích đúng bitwise gallery; không xếp hạng.
Cả400 raw masks/pixels/support khớp census đóng băng; bốn negative không có dòng vector.
Oracle10 ảnh cố định: cfd_final_00001, hf_merged_00209, hf_merged_00333, hf_merged_00561, hf_merged_00694, hf_merged_00722, cfd_final_00347, cfd_final_00344, hf_merged_00049, hf_merged_00112.
Seed6112026 chỉ chọn bốn ảnh bổ sung từ manifest, không dùng output retrieval hoặc tối ưu ROI.
Đã tính scalar toàn bộ tâm eligible trên10 ảnh: **164144 tâm,40 histogram**,
so đủ raw words và8 giá trị gp mỗi tâm. Raw code/count mismatch=0;
max |gp_production−gp_scalar|=0.0, max |hist_production−hist_scalar|=0.0.
[JSON đầy đủ](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/numerical_verification.json).
Đây là equivalence trên môi trường NumPy/OpenCV/Python ghi trong lock; không khẳng định bitwise trên mọi platform.

| Vùng (96 vector) | Raw pixels min–max | Eligible min–max | Tổng tâm | Bin có count>0 |
|---|---:|---:|---:|---:|
| forehead_brow | 3451–7206 | 2492–6150 | 442986 | 58–59 |
| cheek_left_viewer | 2500–6367 | 1946–5630 | 357696 | 58–59 |
| cheek_right_viewer | 2490–6687 | 1972–5898 | 359623 | 59–59 |
| nose_mouth | 3887–7243 | 3326–6386 | 469949 | 59–59 |

Mỗi count sum=N; mỗi nhóm L1 nằm `[0.9999999999999998,1.0000000000000002]`,
vector sum `[3.999999999999999,4.0]`; hữu hạn, nonnegative, C1 đúng236 chiều,
không sử dụng stats150/144 hoặc global normalization của A/B.

## Ví dụ truy vết phép tính

`cfd_final_00001.png`, forehead_brow, tâm(106,61), BGR148/190/223→gray195.

| p | (x,y) láng giềng | gp float64 | gp>=195 |
|---:|---|---:|---:|
| 0 | (108, 61) | 200 | 1 |
| 1 | (107.414213562373, 59.5857864376269) | 193.2304473783 | 0 |
| 2 | (106, 59) | 197 | 1 |
| 3 | (104.585786437627, 59.5857864376269) | 195.213203435596 | 1 |
| 4 | (104, 61) | 198 | 1 |
| 5 | (104.585786437627, 62.4142135623731) | 198.414213562373 | 1 |
| 6 | (106, 63) | 201 | 1 |
| 7 | (107.414213562373, 62.4142135623731) | 198.071067811865 | 1 |

Bits p0→7=`10111111`, code253, run_start2, ones7→bin55.
Ở p1: gray stencil(189,194;196,193), tx0.41421356237309226,ty0.5857864376269077,
lerp ngang191.07106781186548/194.75735931288074, lerp dọc193.23044737829954<195→0.
Tất cả tọa độ, stencil và kết quả trung gian nằm ở
[hand_calculation.json](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/hand_calculation.json).

## Giới hạn và bảo toàn

| image_id | Kết quả | Nguyên nhân |
|---|---|---|
| hf_merged_00069 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00198 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00267 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00463 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |

396 ROI valid hình học không xác nhận anatomy; cả100 giữ PROVISIONAL.
HF333/HF561 mặt phụ và HF722 tay che vẫn là vi phạm dataset đã biết; HF209 thiếu B tóc nhưng C1 kỹ thuật valid;
HF694 kính/khăn còn UNVERIFIED. Không sửa mapping A, ROI, ảnh hoặc loại ảnh khó.
Contract raw v0.2 ưu tiên cao hơn proposal v0.1 cũ về overlap: không priority subtraction.
Proxy lông mày undercoverage và endpoint canonical478→68/topology mũi MP1/MP4 chưa giải quyết.
Trước chạy1438 chính thức cần review giải phẫu, occlusion và contract có quyết định được ghi nhận;
không dùng numerical PASS làm chứng nhận toàn hệ thống.

14533 protected file SHA-256 giữ nguyên,0 thiếu/đổi.
[final_scope.json](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/final_scope.json),
[baseline](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/baseline_before.json),
[nguồn/phiên bản implementation](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/implementation_provenance.json).
Không có sửa số học sau khi oracle chạy; chỉ thay import hashlib tĩnh và sửa logger PowerShell.
Không cài thư viện, không rerun MediaPipe, không ghi SQLite hoặc tạo C2/calibration/fusion/ranking.
Ảnh chưa aligned hoặc thiếu landmarks có provenance nằm ngoài phạm vi adapter; không suy đoán alignment lịch sử.

Lệnh thành công (repository root):

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C1_lbp.src.trial100
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/test_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c1_trial100.py
```

Xem [báo cáo trial](../C1_LBP_TRIAL100_REPORT.md) về cấu trúc output và giới hạn giải phẫu/dataset.
