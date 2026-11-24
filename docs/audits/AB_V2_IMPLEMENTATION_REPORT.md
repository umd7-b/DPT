# Nghiệm thu A150/B144 report v2

Ngày **23/11/2026**. **Đã triển khai, chạy và kiểm chứng A12/B12 ở phiên bản 2; chưa thể tuyên bố toàn hệ thống tuân thủ 100%.** PDF giữ nguyên SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Quy ước epsilon/ddof A và Lab24 B được người dùng chốt trong yêu cầu v2: [v2_authority.json](v2_evidence/v2_authority.json). Đã đọc và giữ nguyên sáu báo cáo audit; hash ở [phase1_review.json](v2_evidence/phase1_review.json).

## Trả lời tám câu nghiệm thu

| Câu | Yêu cầu | Kết luận có giới hạn | Bằng chứng |
| --- | --- | --- | --- |
| 1 | A12 đã đúng sigma+epsilon? | Đã khắc phục ở v2: epsilon1e-8,ddof0; lưu raw_sigma/effective_divisor riêng, không thay std nhỏ bằng1,không bỏ chiều0 variance. | A1501438×150;19 tests mới + oracle toàn kho. |
| 2 | B12 đã chuẩn hóa mô-men trước ghép thật sự? | Đã khắc phục: fit24 Lab moments; thay12 Lab trong mỗi region72 còn tách riêng; sau đó concatenate144 và fit/transform final144 riêng. | features_B_after_moments.npy;stats moments24/final144;oracle độc lập cả2 stage. |
| 3 | Query dùng đúng stats/version? | Đã kiểm chứng: A dùng mean/raw_sigma/epsilon v2; B dùng2 stats v2 theo thứ tự; worker trả schemaID/hash từngstats. Loader từ chối sai stage/v1/A-vs-B. | Real new_query trong2 venv, q vector bằng đúng hànggallery khi pixel gốc không đổi. |
| 4 | Legacy có thay đổi? | Không: hash 14057 file baseline đều giữ nguyên; không sửa API/file hiện có,không ghi đè vectors/stats/outputs/audit/PDF/dataset/C1/C2. | baseline_before.json;final_scope.json;new_source_inventory.json. |
| 5 | Oracle độc lập đạt? | Đạt:19 tests mới;114 testcases trong tests/đã được phủ qua2 venv;39 oracle audit cũ đạt. Oracle fsums toàn kho/query/pairs không gọi fit/transform/rank mục tiêu làm expected. | verification_summary.json và logs/test_coverage.json. |
| 6 | Khoảng cách/ranking thay đổi gì? | Khoảng cáchA vàmedianA đổi;B thay đổi mức làm tròn dùthứtự thực thi đã sửa;9/9 bảng Top5của3 query giữ nguyên,50 hàng B-only cũ giữ thứtự. | distance_comparison.csv,top5_comparison.csv,ranking_comparison.json,b_only_10_queries_comparison.csv. |
| 7 | Còn DEVIATION trong code A/B v2 đang dùng? | Không còn sai lệch đã xác nhận A12/B12 trong luồng chuẩn hóa v2 được kiểm tra;AB14được giải quyết bằng calibration v2. B18 chỉ helperlegacy,không được chuẩn hóa v2 gọi. Chưa chứng nhận toàn bộ geometry/A2do các mục UNVERIFIED. | Schema/step artifacts/independent tests;no full-system compliance claim. |
| 8 | Còn điều kiện chưa chứng minh/vi phạm? | Mapping478→68,tâm mắt,A2endpoints/guards,self-match định nghĩa;dataset mặtphụ/chemiệng;identity/age/pose/alignment/encoder/CSDL;mask semanticquality vàrelevance. | A_GEOMETRY_DECISIONS_V2.md;DATASET_REMEDIATION_V2.md;6 auditbaseline. |

## Module và entry point mới

Không sửa hàm hoặc API legacy. Tám file mới:

- `shared/report_v2.py`: I/O, stats, hash, integrity và bảo vệ output.
- `features/A_geometry/src/report_v2.py`: fit/transform/build/load A150_report_v2.0.0.
- `features/B_color/src/report_v2.py`: descriptor từng vùng, Lab24 trước ghép và final144.
- `retrieval/search_ab_v2.py`: load đúng gallery v2, join danh tính, calibration và query.
- `retrieval/ab_query_worker_v2.py`: extractor trong hai môi trường gốc, schema/stats hashes v2.
- `tests/test_report_v2.py`: 19 tests mới về công thức, query và version.
- `scripts/verify_ab_report_v2.py`: oracle độc lập toàn kho/query/pairs/ranking/hash.
- `scripts/report_ab_v2.py`: ba hồ sơ v2 và xác minh phạm vi cuối.

Phạm vi dự kiến trước sửa: [implementation_scope.json](v2_evidence/implementation_scope.json). Danh sách file/hàm/dòng/hash thực tế: [new_source_inventory.json](v2_evidence/new_source_inventory.json).

## A12 — công thức và dtype

```text
mean = mean(raw_A, axis=0)
raw_sigma = std(raw_A, axis=0, ddof=0)
effective_divisor = raw_sigma + 1e-8
normalized = (raw_A - mean) / effective_divisor
```

Raw A1438×150 float32 giữ nguyên. `raw_reference.json` lưu đường dẫn/hash raw bất biến; metadata có image_id/a_row_index. Stats lưu riêng mean, raw_sigma, epsilon, effective_divisor, ddof, fit_count, schema và hash raw/fit manifest. Không std_safe, không bỏ chiều, không ép query chiều hằng thành 0. Query dùng lại mean/raw_sigma/epsilon đúng phiên bản, không fit lại.

Normalized A v2 lưu float64, thống nhất phép tính gallery/query với B. V1 normalized float32; raw A không đổi. So sánh tách phần thay công thức trước cast khỏi sai số cast float32 v1 (max `2.34564010881e-07`). Không quy toàn bộ chênh lệch file v1/v2 cho epsilon hoặc chọn dtype bằng Top-5.

## B12 — chuẩn hóa mô-men trước ghép

Tính lại descriptor từ **1438 ảnh và 2876 raw mask** đã kiểm hash/receipt, không chạy segmentation lại. 1437 raw B144 khớp từng phần tử v1. Giữ HS48/Lab12/Hue12, class1/17, raw mask, min100, Pearson/circular đã duyệt; không erosion/gộp nose.

```text
skin72 và hair72 riêng, chứa Lab12 chưa chuẩn hóa
 -> fit 24 Lab moments: ddof0, divisor1 nếu sigma<1e-8
 -> chuẩn hóa 12 Lab trong mỗi vùng72 còn tách riêng
 -> ghép Skin72 + Hair72 thành B144
 -> fit bộ mean/raw_sigma/divisor D15 riêng trên 144 chiều SAU bước Lab
 -> final Z-score144 -> Euclid144
```

`normalize_moments_before_concat` trả hai vùng72; `assemble_after_moments` mới ghép B144. Raw serialization chỉ để lưu/đối chiếu, không đưa thẳng vào final fit. D14 cũ được thay bằng quy ước hai bước người dùng chốt. **B giữ D15 ở cả hai bước, không cộng epsilon của A.**

Lưu raw, `features_B_after_moments.npy`, normalized, stats24 và stats144 riêng, manifest/mapping/schema/source/integrity. Chỉ24 Lab đổi tại bước đầu; HS/Hue/circular giữ nguyên tại bước đó. Query dùng cả hai stats theo đúng thứ tự, không refit. Giá trị final gần v1 không phải lý do bỏ bước được PDF quy định.

Stats v1 chỉ đọc để kiểm tra/so sánh baseline. Loader v2 kiểm schema, stage24/144, fit manifest/hash và quan hệ giữa các vector. Calibration pin hash vectors/stats/schema v2, từ chối v1 hoặc cache stale/tamper.

## So sánh trước/sau

| Hạng mục | V1 | V2 | Ảnh hưởng đã đo |
| --- | --- | --- | --- |
| A normalized | 1438×150 float32 | 1438×150 float64 | max∣Δ∣=1.03581216058e-05 |
| A divisor | std_safe | raw_sigma+1e-8 | max formula-only∣Δz∣=1.02480673698e-05 |
| B raw | 1437×144 float64 | 1437×144 float64 | Tính lại từrawmasks,đúng từng phần tửV1 |
| B Lab stage | Không có stage riêng | 24 mean/raw_sigma/divisors;post-stage1437×144 | Chỉ24Lab thay đổi;HS/Hue/circular giữ nguyên ở stage này |
| B final | Fit trên raw144 | Fit trên post-moment144 | max∣Δz∣=7.92255150373e-13 |
| MedianA | 16.441995192935675 | 16.441989840419168 | Δ=-5.35251650646e-06 |
| MedianB | 10.814300552264744 | 10.814300552264770 | Δ=2.6645352591e-14 |

Toàn bộ 150+24+144 bộ mean/raw_sigma/divisor ở [normalization_stats_comparison.csv](v2_evidence/normalization_stats_comparison.csv). Stats final B cho24 Lab dùng đơn vị sau biến đổi, không so trực tiếp với raw Lab rồi gọi là sai số fit.

## A+B và ranking

Join bằng image_id/a_row_index; B lấy theo feature_row_index. Giữ nguyên **20000 cặp ID và thứ tự** từ v1; dA/dB và median được tính lại trên vectors v2. Lưu hash source pair CSV và hash danh sách ID. Median normalization `d/(m+1e-8)`, trọng số cố định thử nghiệm0.5/0.5; chưa phải fusion chính thức bốn bộ.

Ba query00001/00088/00144 có chín bảng A-only/B-only/A+B trên cùng1437 ứng viên. **0/9 Top-5 đổi thứ tự**, không có vị trí toàn ranking đổi trong các phép thử này; không suy ra kết quả cho mọi query. Đối chiếu thêm mười query B-only v1/50 hàng: thứ hạng giữ nguyên. Khoảng cách và median vẫn đổi. Không dùng Top-5 trùng để kết luận công thức cũ đúng.

Baseline được tính lại bằng vector/median v1 trên cùng tập ứng viên; không giả đã có CSV A+B v1 cho00088/00144. [distance_comparison.csv](v2_evidence/distance_comparison.csv) có **4311 dòng**, [top5_comparison.csv](v2_evidence/top5_comparison.csv)45 dòng; [ranking_comparison.json](v2_evidence/ranking_comparison.json) ghi đầy đủ thay đổi.

Top-5 A+B của `cfd_final_00001.png`:

| Hạng | Ảnh | dA v2 | dB v2 | D_AB v1 | D_AB v2 |
| --- | --- | --- | --- | --- | --- |
| 1 | cfd_final_00038.png | 11.311268707635 | 6.985326867075 | 0.666942199396 | 0.666942167604 |
| 2 | cfd_final_00029.png | 11.740416532629 | 7.282024837326 | 0.693710389889 | 0.693710382149 |
| 3 | cfd_final_00036.png | 13.375908897467 | 7.631354089981 | 0.759596918992 | 0.759596878586 |
| 4 | cfd_final_00044.png | 12.408384717186 | 8.268705637096 | 0.759642580210 | 0.759642518617 |
| 5 | cfd_final_00031.png | 13.513428773540 | 7.854466010267 | 0.774094456909 | 0.774094446813 |

[Ảnh so sánh ba hàng](../../outputs/retrieval/ab_report_v2/queries/cfd_final_00001/comparison_top5.png), [JSON kết quả](../../outputs/retrieval/ab_report_v2/queries/cfd_final_00001/results.json). CSV/JSON lưu dA/dB, normalizedA/B, D_AB và score chế độ. Chưa có relevance labels để kết luận chất lượng nhận diện.

## Query mới, thiếu B và môi trường

Fixture `new_query.png` đã có từ baseline, pixel giống00001 nhưng encoding/hash khác, buộc qua nhánh query mới. V2 không tạo/sửa ảnh nguồn. Worker A chạy `.venv311`, B chạy `.venv-uniface` với model cục bộ đã kiểm hash, rồi đúng hai bước chuẩn hóa v2. Raw query/bước Lab/normalized được lưu để oracle; vectors query bằng đúng hàng gallery00001 của cả A/B. Đây là smoke test bằng ảnh có sẵn, không phải holdout.

HF00209 vẫn có A, B thiếu tóc: A-only có kết quả, A+B/B-only rỗng, dB/D null. Worker B chạy riêng với raw masks của ảnh này trả missing_B và không tạo.npy. Không zero-fill hoặc đổi trọng số. Self-match byte→ID giữ nguyên; PNG khác encoding có thể trả ảnh gốc, như hồ sơ quyết định đã ghi.

## Oracles và tests

| Phép đối chiếu độc lập | Max sai số tuyệt đối |
| --- | --- |
| A gallery sigma+epsilon | 7.1054273576e-15 |
| B Lab24 stage | 9.7699626167e-15 |
| B full2-stage final | 7.92255150373e-13 |
| A query | 3.99680288865e-15 |
| B queryLab24 | 8.65973959208e-15 |
| B queryfinal144 | 4.52970994047e-14 |
| Pair EuclidA | 7.1054273576e-15 |
| Pair EuclidB | 1.42108547152e-14 |

Expected toàn kho dùng math.fsum và phương trình scalar cho mean/std/Euclid, không gọi fit/transform/rank/calibrate mục tiêu làm expected. Raw descriptors và pair IDs kiểm đúng từng phần tử; sai số cộng float tách khỏi sai công thức.

`tests/` có **95 tests cũ +19 tests v2 =114**. `.venv311`:112 đạt, hai test skip vì thiếu UniFace. `.venv-uniface`:tám batch tests đều đạt, gồm đúng hai test đã skip; đối chiếu ID test xác nhận đủ114 testcase.19 tests v2 cũng đạt ở UniFace. Chạy thêm23+16 oracle audit cũ qua unittest loader với log mới, không ghi lại log baseline. Không cài thư viện hoặc trộn site-packages. Xem [test_coverage.json](v2_evidence/test_coverage.json), [verification_summary.json](v2_evidence/verification_summary.json).

## Thời gian thực tế và phạm vi đo

Builder ghi thời gian đến mốc comparison: A `0.038103` giây; B `37.838119` giây. B gồm đọc/hash/receipt, tính descriptor, fit/lưu hai bước; chưa gồm verify_sources/integrity cuối hoặc khởi động interpreter. Oracle validation `11.845047` giây; query00001 `0.482775` giây đến trước ghi results.json. Không coi đây là cam kết hiệu năng hoặc so trực tiếp với thời gian segmentation v1.

## Output và bảo toàn

- `outputs/A_geometry/features_report_v2/`:raw reference, metadata, normalized A, stats/schema/source/integrity/comparison.
- `outputs/B_color/color_features_report_v2/`:raw/post-Lab/final B, stats24/144, manifest1438/rows1437/missing1.
- `outputs/retrieval/ab_report_v2/`:calibration và query CSV/JSON/PNG v2, kiểm worker thiếu B.
- `docs/audits/v2_evidence/`:baseline, phạm vi, logs, oracles, bảng so sánh và manifest mới.
- [A_GEOMETRY_DECISIONS_V2.md](A_GEOMETRY_DECISIONS_V2.md), [DATASET_REMEDIATION_V2.md](DATASET_REMEDIATION_V2.md).

**14057 file baseline không đổi byte.** Dataset/masks/metadata, sáu audit cũ, PDF và C1/C2 giữ nguyên. Không xóa/crop/inpaint/tạo ảnh thay thế; không triển khai C1/C2. [final_scope.json](v2_evidence/final_scope.json) và [created_files_manifest.json](v2_evidence/created_files_manifest.json) ghi phạm vi/hash.

## Lệnh PowerShell đã chạy thành công

Chạy tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.A_geometry.src.report_v2
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.report_v2
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image hf_merged_00209.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00088.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00144.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image outputs/retrieval/ab_validation/new_query.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv-uniface\Scripts\python.exe -X utf8 -B scripts/verify_ab_report_v2.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B scripts/report_ab_v2.py
```

Output tồn tại được từ chối ghi đè. Query lại dùng `--output outputs/retrieval/ab_report_v2/queries/<new_run_name>`; calibration v2 dùng lại nếu mọi hash khớp. Build lại dùng thư mục mới đúng prefix `features_report_v2*` hoặc `color_features_report_v2*`, rồi chọn gallery/calibration v2 mới. Không ghi vào đường dẫn v1.
