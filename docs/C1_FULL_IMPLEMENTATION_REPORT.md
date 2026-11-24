# C1 LBP236 — triển khai toàn bộ dataset với ROI v0.4

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

## Kết quả thực tế

**1438 ảnh đã xử lý,1438 vector hợp lệ,0 missing**:710 CFD+728 HF.
Đây là valid theo geometry/support/numerical guards đã khóa, không phải1438 ảnh đã được chứng nhận anatomy.
`features_C1.npy` shape **(1438,236)** dtype **float64**, hữu hạn,không âm.
`counts.npy` uint64(1438,4,59); `eligible_centres.npy` uint64(1438,4).
Mọi count sum=N và histogram chính xác count/N; đủ5752 histogram L1 riêng.
Tổng mỗi nhóm nằm `[0.9999999999999998,1.0000000000000002]`, tổng vector trong
`[3.999999999999999,4.000000000000001]`. Không global-L1/L2/Z-score/refit.

Tất cả image_id có một dòng extraction_status.csv. Missing nếu xuất hiện sẽ không có feature row/vector,
kèm reason rõ; không zero-fill. Lần chạy này không có exception/missing, không ép số thành công.
Thứ tự vector là image_id tăng dần, có feature_row_index tường minh trong feature_rows.csv.
Archive↔catalog↔image nối bằng image_id/filename, không zip catalog với hàng landmarks.
Mỗi vector mang đúng ROI/spec hash trong row metadata và feature version `C1_LBP236_FULL_ROI_V04_v1`.

| Vùng | Min | Median | Max | Tổng tâm theo ROI |
|---|---:|---:|---:|---:|
| forehead_brow | 2955 | 5385.5 | 7337 | 7734700 |
| cheek_left_viewer | 1645 | 3704.5 | 6610 | 5347242 |
| cheek_right_viewer | 1571 | 3698.5 | 6628 | 5313302 |
| nose_mouth | 3326 | 4741.0 | 6835 | 6906243 |

Các tổng tâm là count theo từng raw ROI, không phải union các tâm; overlap vẫn pool độc lập.
Cả5752 raw mask hash,raw pixel count và support đều khớp census v0.4 đã đóng băng.

## Binding phiên bản và kernel tái sử dụng

Không sửa features/C1_lbp/src/lbp236.py. Tầng mới `V04Context` authenticate spec gốc/codebook/v0.2 dependency,
authenticate candidate v0.4 rồi bind ROI mới để dùng **nguyên** Extractor,polygons,gray,bilinear,raw code,
histogram và missing rules đã kiểm. Ba polygon má/mũi-miệng phải trùng definition v0.2.

Spec gốc v0.1.0 **có dependency ROI v0.2**. Không tự xóa hoặc tuyên bố dependency đó vốn là v0.4.
Feature schema mới ghi `PROJECT_SELECTED_V04_SAME_LBP_SPEC_ARITHMETIC_v1`: original_spec_ROI_dependency,
implementation_ROI, lý do lựa chọn của chủ dự án và original spec hash; không sửa JSON gốc.
Đây là binding triển khai mới, giữ arithmetic đúng spec, không tuyên bố mọi nội dung metadata của spec cũ
đã biến thành spec v0.4. Danh tính/hash nguồn và lựa chọn triển khai được ghi riêng trong feature_schema.json.

Giữ P8,R2,threshold>=,58 mẫu uniform riêng+198 nonuniform vào bin58,59 bins mỗi vùng.
Gray=(1868B+9617G+4899R+8192)//16384 với uint32,gray uint8 rồi float64; offsets p0 Đông ngược kim đồng hồ,
±sqrt(2) chính xác float64; horizontal lerp rồi vertical lerp,không round5 decimal/intensity.
Support21 trong cùng raw ROI/ảnh,overlap độc lập,min64; counts uint64,h=count/N float64 không epsilon L1.
Chi-square=0.5*sum((a-b)^2/(a+b+1e-8)), không dùng Euclid cho C1.

## Kiểm thử và oracle

**95 tests đạt,0 failure/error/skip**: A/B report v2 và A+B identity/calibration numeric fixtures,
color features/report rules,20 C1 numeric tests+6 trial integration và11 full_v04 tests.
Đã kiểm kernel pin,modified candidate rejection,missing không zero-fill,shape/dtype/hash,
Chi-square independent scalar/0.5/epsilon/self0/symmetry,tie-break và metadata permutation.
Một fixture chứng minh Chi-square và Euclid xếp hạng khác nhau; production phải cho thứ tự Chi-square.
Các hàm fit trong regression A/B chỉ chạy trên fixtures trong bộ nhớ/temp, không refit hoặc ghi stats artifact.
Trial100 cũ không chạy lại batch hoặc ghi đè: regression dùng kernels/query checks và dữ liệu trial đã lưu.

Oracle độc lập trên12 ảnh cố định (2 CFD,10 HF,bao gồm4 negative v0.2 và các case occlusion/dataset),
không chọn bằng Top-5. Oracle dùng Python integer gray,rotation-enumeration codebook,vertex CSV frozen,
raster quét toàn ảnh,support scalar và bilinear scalar; không gọi extractor để tạo expected.
**48 histogram /211534 tâm scalar** khớp counts/histogram chính xác;3122 raw-code centres và8 neighbour
values mỗi tâm khớp chính xác. Max histogram/interpolation error=0.0.
Independent Chi-square qua math.fsum đối chiếu **17256 khoảng cách (12×1438)**,
max absolute error=2.220446049250313e-16; cả12 Top-5 trùng scalar oracle, self-distance0.
Ba histogram vùng không đổi khớp bitwise toàn bộ96 vector trial v0.2; không tái fit theo query.
Các khẳng định bitwise chỉ áp dụng môi trường đã ghi, không tự suy ra tương đương default skimage/platform khác.

## Truy vấn riêng C1

Module [search_c1.py](../retrieval/search_c1.py) đọc gallery qua explicit image_id/feature_row_index,
kiểm hash artifact/schema/ROI/spec và histogram. Query hiện chỉ nhận ảnh trong gallery: image_id,
filename hoặc file path có hash trùng. Ảnh mới **chưa hỗ trợ**, không tự coi ảnh mới đã aligned.
Query reuse vector lưu, không gọi detector/extractor,không đổi histogram/fit tham số.
Bỏ đúng image_id truy vấn, giữ các ảnh khác dù distance0; sort `(distance_C1,image_id)` tăng dần.
CSV,JSON vàcomparison.png tách từng run,không ghi đè output có sẵn.

Lệnh PowerShell thực tế đã chạy thành công:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C1_lbp.src.full_v04
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c1_full.py
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image cfd_final_00001.png --top-k 5
foreach ($c1Query in @('cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00209.png','hf_merged_00722.png')) {
    .\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image $c1Query --top-k 5
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c1_full.py
```

Lần chạy tiếp theo dùng `--output <thư_mục_mới>`; batch vàverification từ chối ghi đè artifacts đã hoàn tất.


### cfd_final_00001.png

| Rank | Ảnh | Chi-square |
|---:|---|---:|
| 1 | cfd_final_00429.png | 0.050103653496 |
| 2 | cfd_final_00757.png | 0.052864582413 |
| 3 | cfd_final_00686.png | 0.054052967661 |
| 4 | cfd_final_00439.png | 0.055542644036 |
| 5 | cfd_final_00462.png | 0.056340935589 |

[Ảnh so sánh](../outputs/C1_lbp/full_v04/queries/cfd_final_00001/comparison.png) · [CSV](../outputs/C1_lbp/full_v04/queries/cfd_final_00001/results.csv) · [JSON](../outputs/C1_lbp/full_v04/queries/cfd_final_00001/results.json).

### hf_merged_00209.png

| Rank | Ảnh | Chi-square |
|---:|---|---:|
| 1 | hf_merged_00116.png | 0.115896867298 |
| 2 | hf_merged_00166.png | 0.126961354133 |
| 3 | hf_merged_00487.png | 0.128810815232 |
| 4 | hf_merged_00158.png | 0.129792288948 |
| 5 | hf_merged_00181.png | 0.130080823646 |

[Ảnh so sánh](../outputs/C1_lbp/full_v04/queries/hf_merged_00209/comparison.png) · [CSV](../outputs/C1_lbp/full_v04/queries/hf_merged_00209/results.csv) · [JSON](../outputs/C1_lbp/full_v04/queries/hf_merged_00209/results.json).

Ngoài hai ví dụ còn có4 run CFD00069,HF00001,HF00198,HF00722 trong queries/.
Đã round-trip cả6 CSV↔JSON và so36 ô ảnh trong PNG chính xác với pixel nguồn, không chỉ ghi tên output.
Các Top-5 là kết quả thử chức năng, không dùng chọn ROI hoặc điều chỉnh công thức; không phải đánh giá độ đúng identity.

## Artifact và hash

Namespace: [outputs/C1_lbp/full_v04](../outputs/C1_lbp/full_v04/).
Các file yêu cầu features_C1.npy,feature_rows.csv,extraction_status.csv,feature_schema.json,manifest.json,
verification.json đầy đủ. Bổ sung counts.npy,eligible_centres.npy,image_diagnostics.jsonl và evidence/ để đối chiếu.

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

Manifest pin byte hashes8 artifact nền; verification lưu kết quả numerical. Manifest file mới ở evidence/
pin thêm scripts/reports/query outputs và verification, tự loại chính nó để tránh hash vòng.

## Những điều PDF không chốt và giới hạn còn lại

PDF §2.4 quy định P/R,>=,nri59,bốn vùng,L1 riêng,236 chiều,Chi-square0.5. PDF chưa cho MP endpoint/margin,
upper hairline,left/right frame,raw overlap,grayscale integer convention,interpolation ordering/bit direction,
bin numbering,min64,epsilon cụ thể hoặc tie-break. Các chi tiết này là quy ước version đã công khai,
không trình bày là nguyên văn PDF. Raster/support/bilinear/epsilon vẫn đúng bản đã khóa.

V0.4 vẫn **ANATOMY_PROVISIONAL**: upper FACE_OVAL không phải annotation hairline; native brow proxy không phải
mô thật. HF00198 còn3 pixel proxy ngoài,HF00267 còn1; HF00055/00198/00267/00463 có native point ngoài.
Các endpoint má/mũi-miệng và mâu thuẫn topology minh họa A/MP1/MP4 chưa được giải quyết bằng cách sửa A.
HF00333/HF00561 mặt phụ,HF00722 tay che vẫn là vi phạm dataset đã biết; tóc/kính/khăn vẫn có thể trong ROI.
Mọi ảnh được giữ,không skin-intersect/crop/inpaint/xóa hoặc dự đoán person_id/tuổi/giới.
HF00209 B missing tóc nhưng C1 numerical valid không xóa vấn đề B hoặc tự chứng nhận ảnh đúng giải phẫu.
Hồ sơ review800 NOT_REVIEWED/decision register trước được giữ nguyên; lựa chọn triển khai trong task này
không được ghi thành phê duyệt anatomy thay cho người có thẩm quyền.

## Bảo toàn

**17772 file đã có giữ nguyên SHA-256 trước/sau**, gồm PDF,1438 ảnh và metadata,source/mapping A/B,
vectors/stats/calibration/query outputs v1/v2,các SQLite và backup,ROI v0.2/v0.4,trial100 v0.2/96 vectors,
hồ sơ review và các file UI đang có khi nhiệm vụ này bắt đầu. SQLite catalog chỉ được mở `mode=ro&immutable=1`.
Không thay kết quả A+B,không nhập vector C1 vào SQLite,không triển khai C2 hoặc fusion.
[Baseline](../outputs/C1_lbp/full_v04/evidence/baseline_before.json),
[final scope](../outputs/C1_lbp/full_v04/evidence/final_scope.json),
[created files manifest](../outputs/C1_lbp/full_v04/evidence/created_files_manifest.json).
