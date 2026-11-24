# C1 toàn kho v0.4 — kiểm chứng số học

Ngày thực hiện: **24/11/2026**, Asia/Saigon. **PROJECT_SELECTED_ROI_V04; ANATOMY_PROVISIONAL**.
Chủ dự án đã lựa chọn ROI v0.4 cho nhiệm vụ triển khai này. Lựa chọn triển khai khác với chứng nhận
đúng giải phẫu: không sửa candidate contract, `active=false` trong snapshot vẫn nguyên, không ghi ACCEPT/
approval vào CSV hoặc decision register review cũ. Không thay PDF/dataset/A/B/calibration/SQLite/kết quả A+B.

Nguồn chuẩn cao nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, §2.4, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc và xác minh trực tiếp bằng
pypdf có sẵn ở Python hệ thống; phần trích nằm trong full_v04/evidence/pdf_section_2_4.txt.
Extractor/tests dùng `.venv311`, không cài thư viện hoặc chạy lại MediaPipe.

ROI v0.4 content SHA `c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39`; original LBP spec content SHA `7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851`;
codebook file SHA `7eb6a7a12b7374efb50d487f2e399b3475ef0e03594da35971bf083b0188ac94`;
kernel source SHA `c8793bbff26e871d3461c165a7e9d5168ebed7277905ff425edec2e8f2a888ff`. Mismatch schema/content/source hash thì dừng.

## Phạm vi thực tế

1438 ảnh:710 CFD/728 HF.1438 valid vectors float64(236),0 missing;1438 status rows đầy đủ.
Counts uint64(1438,4,59),eligible uint64(1438,4). Đủ5752 nhóm histogram finite/nonnegative,
counts.sum=N≥64,feature.reshape(4,59)=counts/N bitwise, mỗi nhómL1 trong sai sốfloat64.
Kernel cũ không sửa; ROI v0.4 bind riêng bởi feature schema mới, dependency v0.2 của spec gốc vẫn giữ.

| Vùng | Min | Median | Max | Tổng tâm theo ROI |
|---|---:|---:|---:|---:|
| forehead_brow | 2955 | 5385.5 | 7337 | 7734700 |
| cheek_left_viewer | 1645 | 3704.5 | 6610 | 5347242 |
| cheek_right_viewer | 1571 | 3698.5 | 6628 | 5313302 |
| nose_mouth | 3326 | 4741.0 | 6835 | 6906243 |

Vector sum min/max=3.999999999999999/4.000000000000001; không chuẩn hóa global.
Mỗi row metadata gắn image_id/feature_row_index/hash,archive join theo tên/ID, không source-position zip.
Diagnostics full1438 ghi raw mask hash/pixels/support từng vùng,khớp census v0.4.

## Oracle độc lập

12 ảnh cố định: cfd_final_00001, cfd_final_00069, hf_merged_00001, hf_merged_00069, hf_merged_00198, hf_merged_00267, hf_merged_00463, hf_merged_00209, hf_merged_00333, hf_merged_00561, hf_merged_00694, hf_merged_00722.
Scalar oracle cũ không import target để tạo expected: Python integer grayscale, codebook bằng quay run1,
frozen CSV vertex,full raster scan,21-point scalar support,ordered scalar bilinear.
OpenCV pointPolygonTest là primitive raster chung do contract quy định, không khẳng định độc lập backend này.
48 histogram /211534 tâm đối chiếu counts và L1 chính xác.3122 tâm lấy stride row-major trước khi so
raw codes và8 neighbours;0 mismatch, max interpolation/histogram error0.0. Gray cả12 ảnh khớp từng pixel.

Chi-square independent=`0.5*math.fsum((float(a)-float(b))**2/(float(a)+float(b)+1e-8))`.
Đối chiếu17256 distances với vectorized implementation,max error=2.220446049250313e-16.
Self-distance0 vàTop-5 của cả12 ảnh khớp scalar; không dùng Euclid.
Fixture hai candidate có Euclid order ngược Chi-square xác minh production dùng đúng metric.
Tie fixture có duplicate zero-distance: chỉ bỏ query_id,giữ candidate0,sort distance rồiimage_id,
không thay thứ tự khi hoán vị row metadata. Đây là convention tie-break,PDF không chốt.

## Regression và provenance

95 tests đạt,0 error/failure/skip.19 report_v2 tests(A sigma+epsilon,B2-stage,Euclid/median AB),
17 A/B identity/fusion tests,12 color features,10 color report conventions,26 trial C1 và11 full_v04.
Synthetic fit/calibration fixtures trong regression không refit artifact kho. C1 query ảnh gallery reuse vectors,
và3 vùng không đổi khớp bitwise96 old trial vectors. Các ảnh v0.2 thiếu C1 do forehead tự giao nay có numerical
C1 v0.4; trial100 cũ vẫn96 vector/4 missing nguyên trạng/hash, không sửa lịch sử để thành100.
[regression log](../../outputs/C1_lbp/full_v04/evidence/regression_tests.log),
[regression JSON](../../outputs/C1_lbp/full_v04/evidence/regression_tests.json),
[verification đầy đủ](../../outputs/C1_lbp/full_v04/verification.json).

Đã chạy6 query CLI gallery:CFD00001/CFD00069/HF00001/HF00198/HF00209/HF00722.
CSV↔JSON rankings/distances khớp;36 source image tiles trong comparison PNG khớp pixel nguồn.
[Query CFD00001](../../outputs/C1_lbp/full_v04/queries/cfd_final_00001/results.json),
[HF00209](../../outputs/C1_lbp/full_v04/queries/hf_merged_00209/results.json).
CLI chưa hỗ trợ arbitrary new image; không giả định alignment. Query không refit/histogram biến đổi.

## Hash và bất biến

| Artifact | SHA-256 |
|---|---|
| features_C1.npy | `34d26e5b862e012ca537a03fa313eb087b8e58495e37e1da817485276f109f97` |
| counts.npy | `51ce90756651bd8a6e13eef8b34354a81a75310f448c8f65f3e5668c62d0acc0` |
| eligible_centres.npy | `05435fc1569f2aeb3d1430fac38ff42cd62535f8877950a1133854d32b247265` |
| feature_rows.csv | `3ec0f9ff624fa0d15fcf3073bab985bbdc080ba3d68aa11eae2ce0706bbfa5f1` |
| extraction_status.csv | `94f7fe22596b112d7e8b2108a4c73e5cc6f898716362f6e7bb03b7395d7857b8` |
| feature_schema.json | `2b706f20f560d5fa4dfb4f68cb3f97ee46871523b85d9a45919402c6b8b36909` |
| image_diagnostics.jsonl | `17b97594db82d11da7f652da2689d5579eeadb973c006f0b973ce49783f26427` |
| manifest.json | `7bab10b39d4a4435659ca1db4d618132fcf914384dbaf7b184827448cf493084` |
| verification.json | `b0d87098dfd2980cb949ce6bb4ba88dab3108f00439db6abe8b15a3191e34336` |

17772 file cũ so SHA-256 trước/sau,0 thiếu/đổi, gồm PDF,dataset,A/B,SQLite,A+B,trial100 và review.
[Baseline](../../outputs/C1_lbp/full_v04/evidence/baseline_before.json),
[final scope](../../outputs/C1_lbp/full_v04/evidence/final_scope.json),
[manifest file mới](../../outputs/C1_lbp/full_v04/evidence/created_files_manifest.json).
Không ghi SQLite,rerun MediaPipe,thay codebook/gray/bilinear/P/R/threshold,L1,Chi0.5 hoặc stats/calibration.
Mọi missing phải có reason,không zero-fill; run này0 missing là số đo thực tế,không ép expectation.

## Giới hạn đánh giá

PASS là kết quả số học/serialization/identity/ranking trong môi trường schema đã ghi; không anatomy certification.
ROI phụ trợ478/upper FACE_OVAL/lower brow/bridge/frame/overlap/margins là convention chưa có annotation đầy đủ.
2 ảnh thiếu proxy pixels,4 native-point exceptions,tóc/tay/kính/vải và3 dataset violations vẫn giữ.
Chủ dự án chọn v0.4 cho triển khai nhưng không đổi các dòng NOT_REVIEWED thành ACCEPT hoặc ghi quyết định
chấp thuận giả. Không tuyên bố100% anatomical compliance,không triển khai C2/fusion.
Xem [báo cáo triển khai và lệnh PowerShell thực tế](../C1_FULL_IMPLEMENTATION_REPORT.md).
