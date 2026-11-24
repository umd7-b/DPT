# C2 Root-HOG324 — triển khai và truy vấn toàn kho

Ngày thực hiện: **24/11/2026**, Asia/Saigon. **TECHNICAL_PROTOTYPE_FIXED_CONVENTIONS**.
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc trực tiếp §2.4.1–2.4.3 và§2.5.2.
Spec content SHA `a568f2eaec4d54cbc72c2a80d49c371362248367ff88224c158f8c5aaa10f169`; spec file SHA `e16394a661adba43088af4e8106eb14949b9fdf9c7ac155bc9796f097ae5967a`;
kernel SHA `9e8f596945fd29501afccdf76a122d9c5a92c7460da5e72bd6569a4c1cf846b4`; preprocessing `BGR_GRAY_INT16384_CENTER160x192_BORDER_SKIP_v1`.
Spec/kernel được pin trước synthetic tests/trial/retrieval; không thay crop/parameter để cải thiện Top-5.
Không cài thư viện,không chạy alignment hoặc detector,không refit A/B hoặc chạy lại C1 full batch.

## Kết quả thực tế và gate

| Giai đoạn | Input | Valid | Missing | Scalar oracle | Tests |
|---|---:|---:|---:|---|---:|
| Synthetic trước trial | Fixtures | — | — | Random fixture đối chiếu đủ intermediate |15 PASS |
| Trial100 |100=50CFD+50HF |100 |0 |Toàn100 ảnh,3.002.000 tâm gradient |15 PASS |
| Full_v1 |1438=710CFD+728HF |1438 |0 |12 case cố định,360.240 tâm;mọi intermediate full được kiểm |118 PASS |

Trial dùng đúng manifest C1 trial đã thực thi `outputs/C1_lbp/trial100_spec_v0_1/input_trial100_manifest.json`,
giữ đủ ID/thứ tự và4 ảnh C1 v0.2 từng thiếu; không thay bằng bộ anatomical-review100.
Việc C2 valid trên4 ảnh đó không sửa lịch sử/ROI C1 hoặc chứng nhận ảnh không lỗi dataset.
Full batch chỉ chạy sau trial verification PASS và spec/kernel locks khớp.0 missing là kết quả thực tế,
không áp expectation hoặc zero-fill. Mỗi input có extraction_status.csv kể cả nếu không có vector.

## Đối chiếu PDF và các lựa chọn prototype

[Đặc tả và bảng PDF_EXACT/IMPLEMENTATION_DETAIL/DEVIATION/UNVERIFIED](C2_ROOT_HOG_324_SPEC.md)
ghi đủ từng yêu cầu. Đã xác minh ROI160×192,cells4×4 kích thước40×48,sai phân trung tâm PDF,
magnitude sqrt,hướng unsigned,vote magnitude/9 bins,2×2 block stride1,9×36=324,Root theo tổng block,
global L2 và Euclid324. Không có sai lệch yêu cầu rõ được xác nhận trong các kiểm tra này.
Không gọi convention chưa có trong PDF là PDF_EXACT hoặc dùng PASS làm chứng nhận anatomy/relevance.

Repository trước nhiệm vụ chỉ có placeholder C2 và hồ sơ nói chưa triển khai; không tìm được pipeline/provenance
crop160×192 thực sự. Dùng fallback được user chỉ định: **bgr[32:224,48:208]**, x48…207,y32…223 inclusive,
không resize input hoặc chạy face alignment mới. Center crop là IMPLEMENTATION_DETAIL,không phải tọa độ PDF
hay anatomical segmentation. Reviewer chưa chứng nhận extent/occlusion crop trên1438 ảnh.

Giữ gray nguyên C1: uint32 `(1868B+9617G+4899R+8192)//16384`,cast uint8 rồi float64;
không import C1 vector/kernel vào production C2. Standard-library SQLite catalog chỉ đọc
`mode=ro&immutable=1`; C2 không dùng landmarks478 hoặc môi trường Uniface/MediaPipe vì crop fixed không cần chúng.
I/O/hash/image_id patterns tái sử dụng theo cách đã kiểm của C1 nhưng không dùng công thức LBP cho HOG.

## Các bước số học thực tế

| Bước | Shape cho một ảnh | Công thức/ordering |
|---|---|---|
| Input |256×256×3 uint8 BGR |Ảnh source đã aligned trong dataset |
| Crop |192×160×3 uint8 |x[48,208),y[32,224) |
| Gray |192×160 float64 |Integer rounding đã khóa |
| Gx,Gy |192×160 mỗi mảng |I(x+1,y)−I(x−1,y);I(x,y+1)−I(x,y−1) |
| Magnitude,orientation |192×160 mỗi mảng |sqrt(Gx²+Gy²);degrees(atan2(Gy,Gx))%180 |
| Raw cells |4×4×9 float64 |Hard20° bin;pixel chỉ vote vào cell(y//48,x//40) |
| Raw blocks |9×36 float64 |block_y,x row-major;local2×2 cell row-major;bin innermost |
| Root blocks |9×36 float64 |sqrt(h/(sum(block)+1e-8)) |
| Final |324 float64 |Ghép9 block,row-major rồi chia exact global L2 |

Boundary convention: chỉ1≤x≤158,1≤y≤190 góp vote;toàn perimeter1px có Gx=Gy=magnitude0.
30020 tâm/ảnh,không padding/reflect/lấy pixel ngoài ROI. Cell vẫn40×48,không thay shape vì bỏ vote biên.
Unsigned [0,180),180/−180→0;PDF in[0°,180°],half-open wrapping là convention để không sinh bin10.
Hard bins[0,20),…,[160,180),không orientation/spatial interpolation. Tích lũy float64 theo y,x.
Block epsilon1e-8 là quy ước chứ PDF không chốt số. Không L2-Hys,cell L1,block L2,Sobel,RootSIFT hoặc clip0.2.
Final L2 không cộng epsilon. Zero block→root0 đúng công thức,nhưng zero final norm→missing_C2 có reason,
không vector giả. Invalid shape/dtype/nonfinite không impute,nan_to_num hoặc repair.

## Kiểm thử và oracle độc lập

Scalar oracle không import production: Python integer gray,crop indices cố định,loops sai phân,
math.sqrt/math.atan2,hard-bin vote,math.fsum tổng block và L2. Tolerance chốt trong spec trước trial,
không điều chỉnh để làm pass. Trial100 so toàn3.002.000 tâm;full12 case so360.240 tâm.
Max abs error gray,Gx,Gy,magnitude,orientation,cell histogram và raw block=0.0 trên môi trường hiện tại;
Root block tối đa=5.551115123125783e-17,finalvector=4.163336342344337e-17.
Mọi full saved cells→raw blocks→Root→L2 reconstruction khớp bitwise production,
và100 trial vectors khớp bitwise full theo image_id dù thứ tự metadata khác.
Full L2 norm min/max **0.9999999999999998/1.0000000000000002**;tất cả finite,float64,nonnegative,324 chiều.

118 tests cuối:23 C2(15 math+8 pipeline),95 regression A/B/C1 hiện có,0 failures/errors/skips.
Kiểm crop/16 cells,Gx/Gy khác Sobel,ngang/dọc/chéo,9 bins/wrap,unsigned,block layout36,
Root khác block-L2/Hys,epsilon/zero/nan,Euclid/self0/symmetry,ID permutation,ties và output source lock.
Ảnh ngoài gallery bị từ chối; ảnh trùng tên nhưng khác hash không được giả là ảnh aligned cũ.
Trên12 query cố định×1438 vectors,Euclid scalar đối chiếu17256 distances,max error **5.551115123125783e-17**,
Top-5 khớp independent ranking. Không dùng cosine hoặc Chi-square.
Regressions có fit/calibration fixtures trong memory/temp,không refit artifact A/B và không ghi C1 full output.

## Ví dụ tính tay trên ảnh thật

CFD00001,tâm ROI(x80,y96) tương ứng source(x128,y128),chọn cố định không dựa query results.
Gray trái/phải/trên/dưới=201/205/199/201. **Gx=205−201=4,Gy=201−199=2**;
magnitude=sqrt(20)=**4.47213595499958**;
orientation=atan2(2,4)=**26.56505117707799°**,hard bin floor(theta/20)=**1**.
Pixel góp4.47213595499958 vào cell(row2,col2),bin1;hist tổng cell-bin từ mọi pixel=2161.574536126979.
Block index4 có origin cell(1,1),component28 ứng với cell(2,2),bin1.
S_block=119310.09760327979;Root=sqrt(2161.574536126979/(S+1e-8))=
**0.13460044859840956**;sau global L2,component cùng vị trí=
**0.04486681619947182**. Không lấy riêng magnitude pixel làm histogram cả cell.
[Hand calculation JSON](../outputs/C2_hog/full_v1/hand_calculation.json),
[pipeline PNG](../outputs/C2_hog/evidence/cfd_final_00001_pipeline.png).
Magnitudes/Gx/Gy trong PNG được scale chỉ để hiển thị,không đưa ảnh display đó vào extractor.

## Artifact và truy vấn

Trial: [outputs/C2_hog/trial100](../outputs/C2_hog/trial100/).Full: [full_v1](../outputs/C2_hog/full_v1/).
Đủfeatures_C2.npy,feature_rows.csv,extraction_status.csv,feature_schema.json,manifest.json,verification.json.
Bổ sung raw_cells.npy,raw_blocks.npy,root_blocks.npy,ROI coords trong từng row và source/spec/kernel/preprocess hashes.
ID joins tường minh;full orderimage_id tăng dần,trial theo manifest gốc,không dựa vị trí hàng catalog.
Missing nếu có phải có reason và không có feature row;không zero-fill.

`retrieval/search_c2.py --image <gallery ID/filename/path> --top-k 5` reuse vector lưu,
check schema/hash/preprocessing match,loại self theo image_id,sort(distance,image_id) tăng dần.
Không loại tất cả zero-distance duplicates. CLI chỉ hỗ trợ gallery,không giả preprocessing/alignment ảnh mới.
Mỗi run CSV/JSON/PNG trong namespace riêng,thư mục có sẵn sẽ bị từ chối ghi đè.


### cfd_final_00001.png

| Rank | Ảnh | Euclid324 |
|---:|---|---:|
| 1 | cfd_final_00724.png | 0.108779552421 |
| 2 | cfd_final_00453.png | 0.110432430634 |
| 3 | cfd_final_00426.png | 0.114284882695 |
| 4 | cfd_final_00445.png | 0.116672192870 |
| 5 | cfd_final_00443.png | 0.116819001244 |

[PNG](../outputs/C2_hog/full_v1/queries/cfd_final_00001/comparison.png) · [CSV](../outputs/C2_hog/full_v1/queries/cfd_final_00001/results.csv) · [JSON](../outputs/C2_hog/full_v1/queries/cfd_final_00001/results.json).

### hf_merged_00209.png

| Rank | Ảnh | Euclid324 |
|---:|---|---:|
| 1 | hf_merged_00186.png | 0.160972420165 |
| 2 | hf_merged_00027.png | 0.163234327695 |
| 3 | hf_merged_00421.png | 0.164933094150 |
| 4 | hf_merged_00118.png | 0.166479410400 |
| 5 | hf_merged_00339.png | 0.174905694960 |

[PNG](../outputs/C2_hog/full_v1/queries/hf_merged_00209/comparison.png) · [CSV](../outputs/C2_hog/full_v1/queries/hf_merged_00209/results.csv) · [JSON](../outputs/C2_hog/full_v1/queries/hf_merged_00209/results.json).

Đã chạy thêmCFD00069,HF00001,HF00198,HF00722,tổng6 runs. CSV/JSON round-trip và36 source image tiles
trong PNG khớp pixel gốc. Top-5 này chỉ kiểm chức năng,khoảng cách là cấu trúc gradient trong crop,
không phải bằng chứng identity/relevance cao;không điều chỉnh thuật toán sau khi xem.

## Hash và bằng chứng bảo toàn

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

Spec JSON/lock,full/trial manifests pin version/source bytes và array artifacts;manifest file mới cuối
pin thêm reports/tests/query figures và tự loại chính nó để tránh vòng hash.
**17813 file cũ giữ nguyên SHA-256 trước/sau**:PDF,dataset,A/B v2,stats/calibration,A+B outputs,
C1 full_v04/trial vectors/queries,SQLite/eye metadata và các hồ sơ review/ROI đã có.
[Baseline](../outputs/C2_hog/evidence/baseline_before.json),[final scope](../outputs/C2_hog/evidence/final_scope.json),
[created manifest](../outputs/C2_hog/evidence/created_files_manifest.json).
Không cập nhật production DB,không chạy lại C1 full batch,không triển khai fusion bốn bộ.

## Lệnh PowerShell thực tế và giới hạn

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C2_hog.src.batch --stage trial
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c2.py --stage trial
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C2_hog.src.batch --stage full
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c2.py --stage full
foreach ($c2Query in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00209.png','hf_merged_00722.png')) {
    .\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c2.py --image $c2Query --top-k 5
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c2.py
```

Preflight15 tests được chạy và ghi evidence/preflight_tests.log trước trial;trial oracle PASS trước full.
Các lệnh trên đã chạy thành công;rerun query phải dùng `--output <thư_mục_mới>`,không xóa output cũ để overwrite.
Kernel/spec pin giữ nguyên qua toàn bộ run. Giới hạn còn UNVERIFIED:crop anatomy/occlusion,alignment lịch sử,
endpoint dữ liệu và relevance labels. Các vi phạm dataset đã biết vẫn tồn tại;không crop/inpaint/xóa nguồn
để che chúng(center crop là input C2 versioned,không sửa file dataset). Không tuyên bố fully compliant
theo mọi diễn giải hoặc độ chính xác truy hồi cao chỉ từ numeric PASS.
