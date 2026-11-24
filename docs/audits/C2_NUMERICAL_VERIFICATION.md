# C2 Root-HOG324 — kiểm chứng số học độc lập

Ngày thực hiện: **24/11/2026**, Asia/Saigon. **TECHNICAL_PROTOTYPE_FIXED_CONVENTIONS**.
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc trực tiếp §2.4.1–2.4.3 và§2.5.2.
Spec content SHA `a568f2eaec4d54cbc72c2a80d49c371362248367ff88224c158f8c5aaa10f169`; spec file SHA `e16394a661adba43088af4e8106eb14949b9fdf9c7ac155bc9796f097ae5967a`;
kernel SHA `9e8f596945fd29501afccdf76a122d9c5a92c7460da5e72bd6569a4c1cf846b4`; preprocessing `BGR_GRAY_INT16384_CENTER160x192_BORDER_SKIP_v1`.
Spec/kernel được pin trước synthetic tests/trial/retrieval; không thay crop/parameter để cải thiện Top-5.
Không cài thư viện,không chạy alignment hoặc detector,không refit A/B hoặc chạy lại C1 full batch.

## Gating và phạm vi kiểm tra

Preflight15 tests trước trial. Trial100 giữ đúng C1 manifest đã chạy,100 valid/0 missing.
Oracle independent toàn100 ảnh,30020 tâm/ảnh =3.002.000. Chỉ sau trial verification PASS cùng spec/kernel
mới chạy1438 ảnh,1438 valid/0 missing,710CFD+728HF. Full oracle12 case cố định,360.240 tâm.
Các stage đều lưu status cho từng input và rows chỉ cho valid,không ép success hoặc zero-fill.

| Intermediate | Shape mỗi ảnh | Verification |
|---|---|---|
| ROI BGR/gray |192×160×3 /192×160 |Crop đúng pixels,integer gray giống convention C1 |
| Gx,Gy,magnitude,theta |192×160 |Công thức PDF,border skip cố định,unsigned mod180 |
| Cells |4×4×9 |Hard bins20°,vote magnitude,row-major |
| Raw/Root blocks |9×36 |Sliding3×3,local2×2,row-major;sum denominator riêng block |
| Final |324 float64 |Exact global L2,norm min/max0.9999999999999998/1.0000000000000002 |

Oracle không import/call production để tạo expected. Python int gray,loops/math gradient,
histogram accumulation vàmath.fsum total/Root/L2. Gradient vàhist raw maxabs error0.0;
Root block=5.551115123125783e-17,final=4.163336342344337e-17.
Tolerances đã khóa trước trial:gray/Gx/Gy exact,magnitude/angle1e-12,cells1e-8abs/1e-13rel,
Root/vector5e-14abs,L2 norm1e-12abs,Euclid1e-13abs. Không thay convention/tolerance theo results.
100 trial vectors trong full khớp bitwise bằng image_id,không metadata positional zip.
Mọi full stored raw/Root/final arrays được reconstruct và kiểm kiểu/finite/nonnegative/dimension.

## Tests và distance

118 tests PASS,0 failure/error/skip:23 C2+95 regression A/B/C1. Kiểm9 bins/20°boundaries,
180wrap,horizontal/vertical/diagonal,difference not Sobel,16 cells40×48,9 blocks36,epsilon,
Root khácL2/Hys,zero block vàzero final→missing,NaN/shape bad,magnitude votes,source ID permutation,
query lock mismatch,self exclusion,stableties vàEuclid số học.
Euclid scalar=math.sqrt(math.fsum((float(a)-float(b))**2)),không cosine/squared-only/Chi-square.
12×1438=17256 distances full,maxabs error5.551115123125783e-17,self0,12 Top-5 khớp scalar order.
[Full verification](../../outputs/C2_hog/full_v1/verification.json),
[trial verification](../../outputs/C2_hog/trial100/verification.json),
[full118 tests log](../../outputs/C2_hog/full_v1/tests.log).

## Tính tay trên CFD00001

ROI(80,96)→source(128,128).Gray left/right/up/down=201/205/199/201;
Gx4,Gy2,m=sqrt20=4.47213595499958,angle26.56505117707799°,bin1.
Cell(y2,x2) nhận magnitude của pixel này;hist tổng cell-bin=2161.574536126979.
Block4 origin(1,1),component28,S=119310.09760327979;
Root=sqrt(h/(S+1e-8))=0.13460044859840956;global L2 component=0.04486681619947182.
[JSON trung gian](../../outputs/C2_hog/full_v1/hand_calculation.json),
[hình pipeline](../../outputs/C2_hog/evidence/cfd_final_00001_pipeline.png).

## Quy ước và phần chưa chứng minh

Các công thức/parameters rõ trongPDF được đối chiếu tại [spec](../C2_ROOT_HOG_324_SPEC.md).
Center crop(48,32,208,224),gray integer,border exclusion,hard bins,half-open180→0,layout vàepsilon1e-8
là IMPLEMENTATION_DETAIL. PDF ghi unsigned[0°,180°],không chốt cách biểu diễn endpoint vote;
wrapping0 là convention được user cho phép chọn,không thêm bin10.
Crop anatomy/occlusion vàrelevance/accuracy không có ground truth đầy đủ,nênUNVERIFIED.
Không có DEVIATION với yêu cầu rõ được xác nhận;không tự coi mọi convention làPDF_EXACT.
Không thay HOG thànhLBP,RootSIFT,L2-Hys,Sobel hoặcL2 từng block. Không sửa luật sau khi nhìn Top-5.

## Tính toàn vẹn

| Artifact | SHA-256 |
|---|---|
| trial100/features_C2.npy | `ef2c4e9327407bae455f5e91eb03b03a3bddf6401b64cb3769d5ef7049fc8b07` |
| trial100/verification.json | `10a2a292f49c9a8ee9da316391d95fda7bd381662671c54880b4818a4cf050f2` |
| full_v1/features_C2.npy | `fb732b4c8bba3a95d8f2281f05dc2eb8c7d9b02d750521b327c6077190272419` |
| full_v1/raw_cells.npy | `23fddb12f56275ee6ea0c0efbd1419b7aa2404740f7b127620688babd2640f10` |
| full_v1/raw_blocks.npy | `9b09fe9fe94e605ef6a389c738ad07a26ce57db67b31c7c08afca912f46a45b9` |
| full_v1/root_blocks.npy | `3c963871e6a922bb91a46ff1f009455e95e6a4dee184d828aaf17f398d7f117d` |
| full_v1/feature_rows.csv | `5701ee670d8ce3f4e163691845b6f13d42f837d17a2355df0fe6f2fe00179729` |
| full_v1/extraction_status.csv | `0f3b31cfed4ad86d70cf64f67ad5629c02d04f0adbd1b317ec4a04bb670a0e48` |
| full_v1/feature_schema.json | `79232590330d536ee6159f72fd1be3ceedab465c542f49e352ae997dbfba638e` |
| full_v1/manifest.json | `6889623bc4da2182440b7515fe8a5f5ac1bc0e55d88d56ed4983d5c02d8d5022` |
| full_v1/verification.json | `fcbbf98d2ab7693a22a1143462360f68eaa849395842d856582265b0ac6470fe` |

6 query CLI CSV/JSON/PNG đã kiểm round-trip và36 tile pixel nguồn,không thay gallery.
Baseline17813 file cũ SHA-256 trước/sau0 đổi/thiếu,gồmA/B/C1/PDF/dataset/SQLite/eye metadata,
stats/calibration vàkết quả cũ. Regressions chỉ fit fixture/temp,không refit gallery stats hoặc rerun C1 full.
[Baseline](../../outputs/C2_hog/evidence/baseline_before.json),
[final scope](../../outputs/C2_hog/evidence/final_scope.json),
[new files manifest](../../outputs/C2_hog/evidence/created_files_manifest.json).
Không update SQLite,không fusion. [Lệnh thực tế vàTop-5](../C2_FULL_IMPLEMENTATION_REPORT.md).
