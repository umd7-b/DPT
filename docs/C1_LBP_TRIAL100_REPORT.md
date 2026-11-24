# C1 LBP236 — kết quả technical trial100

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

## Kết quả thực tế và phạm vi

Đúng manifest đã khóa: **100 ảnh =50 CFD+50 HF**, **96 vector** (50 CFD+46 HF), **4 missing_C1**.
Không chọn lại ảnh. Gallery chỉ có shape **(96,236)** float64; counts **(96,4,59)** uint64;
histograms **(96,4,59)** float64. Manifest100 ghi image_id, nguồn, feature_row_index hoặc NULL,
hash contract/spec, provenance và các trạng thái tách riêng. Nối archive/DB/catalog bằng image_id hoặc filename,
không giả định thứ tự hàng giống nhau. SQLite chỉ mở URI `mode=ro&immutable=1` để đọc catalog.

| image_id | Kết quả | Nguyên nhân |
|---|---|---|
| hf_merged_00069 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00198 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00267 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |
| hf_merged_00463 | missing_C1; feature_row_index=NULL | forehead_brow:self_intersection |

Mask/support của bốn ảnh lỗi chỉ được đo để chẩn đoán. Không chạy LBP cho bất kỳ vùng nào của ảnh đó;
counts/histograms/vector đều JSON null, không tạo dòng gallery và không zero-fill.
**396/400 ROI valid hình học**, bốn ROI forehead_brow invalid. Cả400 raw masks/hash/pixel-count/support-count
khớp census ROI đã đóng băng. Đây là xác minh tái lập hình học, chưa phải giải phẫu.

## Công thức và các quy ước được giữ nguyên

PDF quy định P8,R2, `gp>=gc`, non-rotation-invariant uniform59 (58 mẫu riêng+198 mã vào bin58),
bốn vùng theo thứ tự và L1 từng vùng; vector236; khoảng cách Chi-square hệ số0.5.
Triển khai dùng đúng các lựa chọn kỹ thuật đã khóa: gray uint32 `(1868B+9617G+4899R+8192)//16384`,
gray uint8 rồi float64; p0 Đông, ngược kim đồng hồ trên ảnh; bán kính2 và ±sqrt(2) float64;
bilinear horizontal lerp rồi vertical lerp, không làm tròn gp/offset. Không epsilon ở bit test,
không padding/reflect. Support đủ21 điểm nguyên trong cùng raw ROI/ảnh. Shared pixels giữ trong từng ROI;
không priority subtraction, không giao mask với skin/hair B. Guard64 tâm là quy ước kỹ thuật, không yêu cầu PDF.
Counts uint64; h=count/N float64, không epsilon L1, không global-L1/L2/Z-score hoặc refit.
Chi-square =`0.5*sum((a-b)^2/(a+b+1e-8))`; epsilon1e-8 là quy ước version của spec, PDF không chốt số này.

`Extractor.extract` và `TrialGallery.extract_query` dùng cùng Context/contract/codebook/support,
hash lệch thì reject. Query adapter nhận BGR256² đã aligned và478 pixel landmarks có provenance do caller cung cấp;
không tự chạy detector hoặc tuyên bố tái tạo alignment gốc. Đã tái trích xuất96 ảnh valid theo query adapter,
khớp bitwise với vector gallery đọc lại; self-distance0. Không tính Top-5 hoặc fusion.

## Số học, histogram và oracle

**26 tests đạt**, không skip/failure/error. Codebook đủ256→0..58,
58 uniform riêng/198 nonuniform; test constant255→57, equality bit1, threshold không epsilon,
định hướng không gộp, tất cả256 stencil bit fixtures, grayscale màu, sqrt(2), support21,
ngoài ROI, overlap, missing/invalid, query/gallery lock và hệ số0.5.
Oracle không import/call extractor để tạo expected: Python integer gray, enumerate right rotations cho codebook,
đọc đỉnh float64 từ CSV audit, quét raster riêng, duyệt21 support scalar và nội suy scalar.
Đối chiếu10 ảnh gồm năm case HF bắt buộc, CFD00001 và bốn ảnh chọn seed6112026 trước khi so kết quả:
**164144 tâm /40 histogram**. Sai khác raw_code/counts=0;
max absolute interpolation/histogram error đều **0.0** trên môi trường ghi trong contract_lock.json.
Không suy rộng bitwise equivalence sang mọi backend khác hoặc mặc định skimage.

| Vùng (96 vector) | Raw pixels min–max | Eligible min–max | Tổng tâm | Bin có count>0 |
|---|---:|---:|---:|---:|
| forehead_brow | 3451–7206 | 2492–6150 | 442986 | 58–59 |
| cheek_left_viewer | 2500–6367 | 1946–5630 | 357696 | 58–59 |
| cheek_right_viewer | 2490–6687 | 1972–5898 | 359623 | 59–59 |
| nose_mouth | 3887–7243 | 3326–6386 | 469949 | 59–59 |

Mọi counts sum đúng eligible N; mỗi histogram sum nằm trong
`[0.9999999999999998,1.0000000000000002]`; tổng236 trong `[3.999999999999999,4.0]`.
Tất cả hữu hạn, không âm, đúng dimension/dtype. Đã đối chiếu NumPy↔JSON↔gallery và identity mapping.

## Ví dụ tính tay trên ảnh thật

Ảnh `cfd_final_00001.png`, vùng forehead_brow, tâm `(106,61)` là phần tử giữa danh sách tâm row-major,
không chọn bằng retrieval. BGR=(148,190,223):
`floor((1868*148+9617*190+4899*223+8192)/16384)=195`.

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

Bits theo p0→p7 là `10111111`; code=`1+4+8+16+32+64+128=253`.
Chuỗi có7 bit1, run_start=2; label=`1+8*(7-1)+((-2)%8)=55`.
Ví dụ p1: stencil `(189,194;196,193)`, tx=0.41421356237309226,ty=0.5857864376269077;
upper=191.07106781186548,lower=194.75735931288074,
gp=193.23044737829954<195→bit0. Không round gp thành uint8.

## Trạng thái giải phẫu và dataset

- Số học: PASS trong phạm vi thử nghiệm và oracle đã nêu.
- Hình học:396 valid/4 invalid trong400 ROI, không sửa polygon.
- Giải phẫu: cả100 vẫn UNVERIFIED/PROVISIONAL, kể cả96 có vector.
- Dataset: HF00333/HF00561 có mặt phụ, HF00722 có tay che miệng, vẫn giữ và tạo vector kỹ thuật;
  không coi thành công C1 là đã giải quyết vi phạm PDF. HF00209 thiếu B tóc nhưng có C1 kỹ thuật;
  thiếu B không tự làm thiếu C1. HF00694 khăn/kính vẫn cần review, không tự gắn nhãn vi phạm.
- Vector:96 valid_C1,4 missing_C1, không đưa C1 vào SQLite production.

Trước khi chạy1438 chính thức: cần xác nhận có thẩm quyền endpoint/frame trái–phải và mô giải phẫu;
xử lý undercoverage proxy lông mày (audit toàn kho44.29–67.14%, chưa phải skin ground truth);
chốt quy trình giải quyết bốn forehead tự giao, occlusion tóc/tay/kính/vải và dataset vi phạm;
review candidate contract bằng annotation độc lập rồi version/hash mới nếu được chấp nhận.
Proposal v0.3 chưa active và vẫn có case HF00198 tự giao. Không chọn ROI bằng Top-5.
Mapping canonical478→68 chưa có trong PDF; lệch topology mũi MP1/MP4 đã báo cáo vẫn giữ nguyên.

## Artifact và tính toàn vẹn

Output riêng: [trial100_spec_v0_1](../outputs/C1_lbp/trial100_spec_v0_1/).
[Manifest100](../outputs/C1_lbp/trial100_spec_v0_1/manifest.json),
[gallery96](../outputs/C1_lbp/trial100_spec_v0_1/gallery_vectors.npy),
[counts](../outputs/C1_lbp/trial100_spec_v0_1/counts.npy),
[histograms](../outputs/C1_lbp/trial100_spec_v0_1/histograms.npy),
[missing](../outputs/C1_lbp/trial100_spec_v0_1/missing_C1.json).
Mỗi ảnh có JSON riêng trong images/ với vector/counts/histograms hoặc null,
mask pixels/support, hash ảnh/landmark row, included_for và status.
Nguồn landmarks478 đã được xác thực theo hash archive/audit; không chạy lại MediaPipe.
Model asset hash được ghi, phiên bản distribution MediaPipe lịch sử không có log nên để null.

**14533 file đã có được so SHA-256 trước/sau:0 thay đổi/thiếu**. Bao gồm PDF,1438 ảnh nguồn,
metadata, A/B source/mapping/vectors/stats/calibration/query v1/v2, ROI outputs và các SQLite cũ/backup/restore.
[Baseline đầy đủ](../outputs/C1_lbp/trial100_spec_v0_1/evidence/baseline_before.json),
[kết quả integrity](../outputs/C1_lbp/trial100_spec_v0_1/evidence/final_scope.json),
[manifest file mới](../outputs/C1_lbp/trial100_spec_v0_1/evidence/created_files_manifest.json).
Giữ nguyên cả README/spec cũ như hồ sơ lần trước; báo cáo này ghi nhận bước technical trial mới.

Lệnh PowerShell thực tế đã chạy thành công từ repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C1_lbp.src.trial100
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/test_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c1_trial100.py
```

Runner, verifier và test logger từ chối ghi đè output đã hoàn tất. Các lệnh là hồ sơ thực thi;
không xóa artifact để chạy lại. Thử nghiệm tương lai cần version/output mới hoặc checkout độc lập.
Lần wrapper PowerShell `2>&1|Tee-Object` báo exit1 vì unittest dùng stderr mặc dù26 tests OK;
đã dùng runner stdout riêng, chạy26 tests thành công exit0. Không đổi công thức để làm test pass.
Không triển khai C2/fusion, không ghi CSDL, không sửa kết quả A+B; hash của chúng bất biến.
