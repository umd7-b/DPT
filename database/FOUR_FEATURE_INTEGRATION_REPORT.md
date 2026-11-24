# SQLite — tích hợp fusion A150/B144/C1_236/C2_324

Ngày **24/11/2026**, Asia/Saigon. **Đã tích hợp và kiểm chứng SQLite cho bốn vector; EXPERIMENTAL_EQUAL_WEIGHTS.**
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`, đã đọc trực tiếp §1.3 và§2.5.1–2.5.3.
Đã đọc schema, toàn bộ module database cũ, nguồn retrieval và các báo cáo C1/C2/fusion yêu cầu.
Không tuyên bố anatomy-approved, accuracy tăng hoặc 100% toàn hệ thống tuân thủ.

## CSDL bàn giao và số liệu thực tế

Nguồn được giữ nguyên `database/data/portrait_ab_v2_eye_metadata_v1.sqlite3`; SQLite backup API tạo bản mới
`database/four_feature_v1/data/portrait_four_features_v1.sqlite3`, rồi migration additive trong một transaction.
Import từ chối đích đã tồn tại; không ghi đè source hoặc artifact nào có trước nhiệm vụ.

1438 Images, 407 Persons; 1441 EyeCoordinates (1438 phép đo audit mới + 3 phép đo audit lịch sử),
1438 EyeCoordinateSources giữ nguyên; không gọi các tọa độ audit là alignment gốc.
5752 FeatureVectors gồm 5751 valid và 1 missing, 4 FeatureVersions.

| Bộ | Phiên bản | Dimension/dtype | Valid | Missing |
|---|---|---|---:|---:|
| A | `A150_report_v2.0.0` | 150/`<f8` | 1438 | 0 |
| B | `B144_report_v2.0.0` | 144/`<f8` | 1437 | 1 |
| C1 | `C1_LBP236_FULL_ROI_V04_v1` | 236/`<f8` | 1438 | 0 |
| C2 | `C2_ROOT_HOG324_FULL_v1` | 324/`<f8` | 1438 | 0 |

Missing duy nhất `hf_merged_00209` ở B với `hair:missing_empty(0<100)`, BLOB và feature_row_index NULL.
A/C1/C2 của ảnh đó giữ nguyên, hợp lệ. Không zero-fill hoặc chia trọng số sang ba bộ.
1437 ảnh đủ bốn vector = 710 CFD + 727 HF; dataset vẫn gồm 1438 = 710 CFD + 728 HF.

## Thiết kế additive và phiên bản

Giữ nguyên `database/schema.sql`, base `PRAGMA user_version=1` để loader AB cũ tương thích.
Extension `FOUR_FEATURE_SQLITE_v1` có version riêng ở FourFeatureMigrations; migration SHA:
`f48ee1916f66aebc7f91b8d3ce4a479d2d08091173f0306bcf6fa62eeff3fba2`.
Không ALTER cột bảng cũ; tận dụng FeatureVersions/FeatureVectors/Calibrations/CalibrationComponents/
Candidates/Pairs/PairDistances bằng INSERT append-only. 19 bảng nguồn giữ nguyên toàn bộ dòng đã có;
các bảng khác chỉ đọc. Thống kê scope và schema thực nghiệm trong evidence.

| Bảng mới | Các cột |
|---|---|
| FourFeatureArtifacts | feature_version, artifact_name, artifact_data, artifact_sha256, source_path |
| FourFeatureCalibrations | calibration_id, policy_sha256, epsilon_c1, params_sha256, pairs_sha256, feature_versions_json, configuration |
| FourFeatureMigrations | extension_version, migration_sha256, source_database_sha256, authority_data, authority_sha256, policy_data, policy_sha256, created_at |
| FourFeatureResults | run_id, mode, rank, image_id, dA, dB, dC1, dC2, normalized_a, normalized_b, normalized_c1, normalized_c2, D, score |
| FourFeatureRunComponents | run_id, calibration_id, kind, feature_version, weight, median |
| FourFeatureRuns | run_id, created_at, query_image_id, query_path, query_sha256, calibration_id, weight_a, weight_b, weight_c1, weight_c2, top_k, status, missing_reason, gallery_intersection_count, candidate_count, self_exclusion_count, ranked_candidate_count, provenance_json |
| FourFeatureVectorBindings | image_id, feature_version, source_row_index, source_vector_sha256, source_image_sha256 |
| FourFeatureVersionLocks | kind, feature_version, version_record_sha256, vector_artifact_sha256 |

Explicit indexes mới: FourFeatureResults_image, FourFeatureRuns_query, FourFeatureVectors_lookup. Các PK/UNIQUE cũng sinh autoindex SQLite.
View mới FourFeatureCoverage; trigger mới FourFeatureResult_contract.
PK/FK/UNIQUE bảo vệ image_id + feature_version, row index, calibration/version và run/mode/rank.
Trigger chặn self, candidate ngoài intersection, rank vượt TopK, run unavailable và thiếu bốn component version.
SQL CHECK bảo vệ payload length, dtype/dimension, status/null, finite bounds và weights; ứng dụng kiểm hữu hạn.

PDF nói ba nhóm A/B/C nhưng bốn vector A/B/C1/C2. Schema lưu logical_group=C và feature_name=C1/C2 riêng,
không vector giả hoặc ép ba cột vật lý. SQLite, schema dạng hàng, kiểu BLOB, index, UUID, tên bảng/cột và migration
là IMPLEMENTATION DETAIL; PDF không quy định chính xác thiết kế SQL hay DBMS.

## Serialization, provenance và chuẩn hóa

Tái sử dụng database.store.encode_vector/decode_vector: IEEE754 C-order bytes, <f8, không cast làm mất số.
Mỗi FeatureVectors có image_id, feature_version, dimension, dtype, status, missing_reason, vector_sha256,
a_row_index, feature_row_index và provenance_json. BLOB khớp chính xác artifact nguồn ở cả 5751 vector hợp lệ.
FourFeatureVectorBindings lưu source row/hash ảnh/hash vector độc lập; query kiểm cả binding và payload,
phát hiện sửa byte kể cả khi sửa lại hash tự khai báo của FeatureVectors.
Join image_id, không ROWID hay vị trí hàng SELECT; row index chỉ tham chiếu trong đúng bộ/version.

A/B stats và ba NPZ normalization stage giữ nguyên byte từ CSDL nguồn, không fit lại.
C1/C2 đã có chuẩn hóa nội bộ, không có fitted gallery stats mới. Trường stats_hash của hai version này là
hash định nghĩa chuẩn hóa và schema đã có (ghi rõ trong provenance), không tạo NPZ stats giả.
FourFeatureArtifacts lưu nguyên byte schema/manifest/feature_rows/extraction_status C1/C2 cùng hash;
schema/provenance giữ ROI/spec/codebook/kernel/preprocessing hashes.
VersionLocks ghi hash toàn bản ghi FeatureVersions và vector artifact; schema/source mismatch bị từ chối.

## Calibration bốn bộ và cách ly lịch sử

ID mới `FUSION_AB_C1_C2_v1:frozen_AB_v2_pairs`; calibration AB `AB_report_v2:frozen_pairs_v1` giữ nguyên.
Tổng 2 calibrations, 40.000 pair rows, 120.000 component distance rows: AB cũ 20k/40k và four-way 20k/80k.
Nhập đúng 20.000 cặp ID/thứ tự và 80.000 scalar distance đã nghiệm thu; không sampling hoặc tính lại median.
Calibrations giữ nguyên byte params JSON/pairs CSV và hash; bảng quan hệ lưu pair IDs, 4 distance, 4 median,
candidate IDs/index. FourFeatureCalibrations lưu policy hash, epsilon_C1 và feature version mapping.

| Bộ | Median giữ nguyên |
|---|---:|
| A | 16.441989840419168 |
| B | 10.81430055226477 |
| C1 | 0.30520587913351654 |
| C2 | 0.21819130381743668 |

Pair IDs SHA `eb93d6da4ac56fcdc79a1fe66a12cacf754bd1b428acecaf302f2f3525926072`; policy SHA `18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798`.
Authority SHA `ea0b144ac265b33a130b16ecf7ac3ef110283616bcfcac8a7da621049261dfea` khóa source DB, source/schema và calibration hashes trước import.
Query đọc calibration từ SQL, kiểm nguyên BLOB so với source hash đã khóa, rồi đối chiếu đủ 20k pair IDs,
80k distance, 4 version/median, epsilon và fingerprint. Không dùng AB calibration cho four-way hoặc ngược lại.

## Query từ SQLite và lịch sử

Module `database/four_feature.py`: CLI import, search, info, backup.
SqlFourGallery đọc metadata, vectors, stats, calibration từ SQLite; không đọc NPY/CSV gallery hoặc file calibration.
Kiểm source module số học/serialization bằng hash; tái sử dụng fusion_four.component_distances/combine/
rank_indices và resolve. Chỉ bổ sung luồng điều phối và lưu lịch sử, không viết lại công thức.

```text
dA,dB,dC2 = sqrt(sum((q-i)^2)) trên từng vector riêng
dC1 = 0.5*sum((q-i)^2/(q+i+epsilon_C1))
normalized_k = d_k/(median_k+epsilon)
D = wA*normalized_A + wB*normalized_B + wC1*normalized_C1 + wC2*normalized_C2
```

Epsilon median và epsilon_C1 đều 1e-8. Weights (.25,.25,.25,.25) giữ nguyên;
hữu hạn, không âm, tổng 1 với atol1e-12/rtol0; không tự normalize weights hoặc optimize theo Top5.
Trọng số đều là EXPERIMENTAL_EQUAL_WEIGHTS, không phải trọng số PDF chỉ định.
Tolerance parity được khóa trước import: atol1e-12/rtol1e-12; quan sát thực tế exact, max error 0.
Không ghép854 chiều để tính Euclid; không refit/re-extract hay chuẩn hóa lại vector.


Hỗ trợ gallery ID/exact filename/path có hash nguồn; không adapter ảnh mới hoặc giả ảnh đã aligned.
Candidate pool chung gồm giao 1437 cho A-only/B-only/C1-only/C2-only/fusion; loại self ID, sort(distance,image_id).
Query đầy đủ: 1436 candidate, 1 self; missing B: pool 1437, 0 self, 0 ranked và fusion_unavailable.
Chế độ only dùng raw metric tương ứng; D vẫn lưu để giải thích fusion cùng bốn raw/normalized components.

Một FourFeatureRuns lưu một request, năm mode trong FourFeatureResults; FourFeatureRunComponents lưu
bốn feature versions/weights/medians. INSERT run/components/results commit atomically; unavailable
vẫn có run và bốn version refs nhưng 0 results. Demo 6 requests có 6 runs, 24 component refs, 125 Top5 results.
Giữ nguyên 18 RetrievalRuns/80 RetrievalResults AB lịch sử; không sửa QueryVectors cũ.
--no-save chỉ đọc; --output JSON có sẵn bị từ chối trước khi ghi lịch sử. CSDL mới là bản làm việc có thể
thay hash khi người dùng lưu thêm run; backup/restored là snapshot nghiệm thu, không ghi đè chúng.

| Query | Trạng thái | Candidate | Loại self | Đã xếp hạng | Rows Top5 đã lưu |
|---|---|---:|---:|---:|---:|
| cfd_final_00001 | ok | 1436 | 1 | 1436 | 25 |
| cfd_final_00069 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00001 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00198 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00722 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00209 | fusion_unavailable | 1437 | 0 | 0 | 0 |

## Top-5 file và SQLite: khớp chính xác ở mọi chế độ

### cfd_final_00001.png

| Chế độ | Top5: filename (distance) |
|---|---|
| A | hf_merged_00136.png (8.837416381528); cfd_final_00336.png (8.885966327716); cfd_final_00382.png (9.392805515224); cfd_final_00312.png (10.575001074429); cfd_final_00502.png (10.709277159797) |
| B | cfd_final_00439.png (6.959676513697); cfd_final_00038.png (6.985326867075); cfd_final_00029.png (7.282024837326); cfd_final_00440.png (7.463745705506); cfd_final_00036.png (7.631354089981) |
| C1 | cfd_final_00429.png (0.050103653496); cfd_final_00757.png (0.052864582413); cfd_final_00686.png (0.054052967661); cfd_final_00439.png (0.055542644036); cfd_final_00462.png (0.056340935589) |
| C2 | cfd_final_00724.png (0.108779552421); cfd_final_00453.png (0.110432430634); cfd_final_00426.png (0.114284882695); cfd_final_00445.png (0.116672192870); cfd_final_00443.png (0.116819001244) |
| FUSION | cfd_final_00038.png (0.538296454408); cfd_final_00031.png (0.581634447663); cfd_final_00034.png (0.606283457224); cfd_final_00443.png (0.608694041697); cfd_final_00029.png (0.610621929810) |

[JSON query](four_feature_v1/queries/cfd_final_00001.json).

### cfd_final_00069.png

| Chế độ | Top5: filename (distance) |
|---|---|
| A | hf_merged_00443.png (5.802768782401); cfd_final_00592.png (6.731731747160); hf_merged_00494.png (7.061874926637); cfd_final_00213.png (7.307968450465); cfd_final_00278.png (7.352300096209) |
| B | cfd_final_00072.png (4.698668360785); cfd_final_00086.png (9.058056090274); cfd_final_00126.png (9.621999737723); cfd_final_00124.png (10.059857377336); cfd_final_00085.png (10.198264678849) |
| C1 | cfd_final_00072.png (0.057946145836); cfd_final_00258.png (0.065849660620); cfd_final_00205.png (0.068737062742); cfd_final_00184.png (0.072334255579); cfd_final_00283.png (0.072488134115) |
| C2 | cfd_final_00294.png (0.115955581536); cfd_final_00150.png (0.124052266249); cfd_final_00163.png (0.125964975273); cfd_final_00666.png (0.129891106137); cfd_final_00278.png (0.130184669210) |
| FUSION | cfd_final_00072.png (0.514484575774); cfd_final_00124.png (0.661486017940); cfd_final_00079.png (0.677560160494); cfd_final_00154.png (0.707019113962); cfd_final_00205.png (0.737890108135) |

[JSON query](four_feature_v1/queries/cfd_final_00069.json).

### hf_merged_00001.png

| Chế độ | Top5: filename (distance) |
|---|---|
| A | hf_merged_00030.png (4.794145871799); hf_merged_00577.png (5.718433125788); hf_merged_00719.png (5.875493490954); hf_merged_00524.png (5.913185115047); hf_merged_00067.png (6.463303842859) |
| B | hf_merged_00565.png (2.895577742443); hf_merged_00002.png (3.157583670499); hf_merged_00330.png (3.249534582683); hf_merged_00033.png (3.263802046551); cfd_final_00719.png (3.783165518617) |
| C1 | hf_merged_00408.png (0.090548391171); hf_merged_00152.png (0.095828466696); hf_merged_00243.png (0.105497220974); hf_merged_00485.png (0.115777382728); hf_merged_00169.png (0.115878986777) |
| C2 | hf_merged_00524.png (0.130121423722); hf_merged_00319.png (0.137304874064); hf_merged_00486.png (0.142581400445); hf_merged_00500.png (0.144808546988); hf_merged_00621.png (0.145113277741) |
| FUSION | hf_merged_00152.png (0.540332830369); hf_merged_00030.png (0.541817390925); hf_merged_00319.png (0.547570327944); hf_merged_00511.png (0.574386871815); hf_merged_00017.png (0.586003006240) |

[JSON query](four_feature_v1/queries/hf_merged_00001.json).

### hf_merged_00198.png

| Chế độ | Top5: filename (distance) |
|---|---|
| A | hf_merged_00333.png (14.454630240536); hf_merged_00708.png (14.658781243593); hf_merged_00485.png (14.746536938292); hf_merged_00358.png (15.153763562385); hf_merged_00315.png (15.216349985527) |
| B | hf_merged_00079.png (5.894313737030); hf_merged_00012.png (6.040612459501); hf_merged_00455.png (6.059764097815); hf_merged_00041.png (6.133008876236); hf_merged_00310.png (6.669284340139) |
| C1 | hf_merged_00459.png (0.124144203608); hf_merged_00126.png (0.125887306239); hf_merged_00624.png (0.134828645572); hf_merged_00275.png (0.138625657639); hf_merged_00093.png (0.145551264441) |
| C2 | hf_merged_00530.png (0.186408266253); hf_merged_00297.png (0.193236418035); cfd_final_00637.png (0.198475057098); hf_merged_00496.png (0.199872561140); hf_merged_00197.png (0.200168746326) |
| FUSION | hf_merged_00275.png (0.853847093002); hf_merged_00135.png (0.886857881821); hf_merged_00298.png (0.895247880163); hf_merged_00496.png (0.903500680530); hf_merged_00259.png (0.910781323410) |

[JSON query](four_feature_v1/queries/hf_merged_00198.json).

### hf_merged_00722.png

| Chế độ | Top5: filename (distance) |
|---|---|
| A | hf_merged_00208.png (10.846602851010); hf_merged_00304.png (11.647818132911); cfd_final_00046.png (12.396058697184); hf_merged_00190.png (12.492702709612); hf_merged_00389.png (12.636934390671) |
| B | hf_merged_00688.png (16.593418012030); hf_merged_00678.png (18.996367554990); hf_merged_00547.png (18.996849962847); hf_merged_00643.png (19.239233405601); hf_merged_00546.png (19.700046289228) |
| C1 | hf_merged_00248.png (0.142214408448); hf_merged_00272.png (0.143747323080); hf_merged_00245.png (0.151181556676); hf_merged_00474.png (0.158408917841); hf_merged_00226.png (0.159234913227) |
| C2 | hf_merged_00062.png (0.181915367125); hf_merged_00557.png (0.189896634648); hf_merged_00458.png (0.190323116752); cfd_final_00584.png (0.191114608101); cfd_final_00216.png (0.195680349516) |
| FUSION | hf_merged_00474.png (1.101994556175); hf_merged_00208.png (1.103368316866); hf_merged_00227.png (1.122969730172); hf_merged_00304.png (1.168378158196); hf_merged_00505.png (1.179334535004) |

[JSON query](four_feature_v1/queries/hf_merged_00722.json).

## Kiểm chứng và bảo toàn

176 tests PASS, 0 fail/error/skip: 17 tests SQLite mới, 19 CSDL cũ, 140 regression A/B/C1/C2/fusion.
Năm query đầy đủ × 1436 candidate × 5 mode = **35.900 ranking rows**: thứ tự ID và mọi trường số học khớp chính xác,
max absolute error quan sát = 0.0; 125 Top5 rows và cả 6 trạng thái query khớp file. Weights/median không đổi.
[Full ranking CSV](four_feature_v1/evidence/full_ranking_comparison.csv),
[Top5 trước/sau](four_feature_v1/evidence/top5_before_after.csv),
[5751 vector round-trip](four_feature_v1/evidence/vector_roundtrip.csv),
[tests log](four_feature_v1/evidence/tests.log).

Tests kiểm INSERT/SELECT, FK/UNIQUE, missing, version/hash/schema, dtype/dimension, corrupted bytes,
serialization exact, đảo thứ tự physical bindings và reverse_unordered_selects, calibration isolation,
query không đọc file vectors/calibration, backup/restore và từ chối ghi đè. Fault injection chỉ trên
bản sao trong RAM/temp từ dữ liệu thật; không commit dữ liệu giả hoặc sửa artifact nghiệm thu.
Regressions fit thống kê trên fixture/temp; không refit gallery hoặc chạy extractor.

Toàn bộ 19 bảng nguồn giữ mọi dòng cũ exact; 7 bảng cho phép append version/vector/calibration.
[Đối chiếu từng bảng](four_feature_v1/evidence/original_table_preservation.json).
Baseline 17915 file SHA trước/sau: 0 changed, 0 missing; PDF, dataset, A/B/C1/C2 vectors,
stats, calibration, source, SQLite cũ, queries/trial/review cũ không đổi.
[Verification JSON](four_feature_v1/evidence/verification.json),
[schema inventory](four_feature_v1/evidence/schema_inventory.json),
[SQL đã thực thi](four_feature_v1/evidence/sql_examples_results.json).

## Backup/restore

| File | SHA-256 | Integrity/full ranking |
|---|---|---|
| database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3 | `0d40f0fc248813e52590620d52bfe0a68efe8df5a2088c12714f38dae8050949` | ok/exact |
| database/four_feature_v1/restored/portrait_four_features_v1.sqlite3 | `0d40f0fc248813e52590620d52bfe0a68efe8df5a2088c12714f38dae8050949` | ok/exact |

SQLite backup API, đích mới. Integrity ok, FK empty, counts và toàn bộ SQL dump khớp;
logical dump SHA `91a1d3b23116345551843257ce03f9b368c0edee45813406e6ca4f679dae0f1b`.
Sau phục hồi, cả 6 query và toàn bộ 35.900 ranking rows khớp database chính, không chỉ Top5.

## Hash nguồn và artifact mới

| File | SHA-256 |
|---|---|
| database/data/portrait_ab_v2_eye_metadata_v1.sqlite3 | `6fc6213286c715edf997ed9484ca1da8da0d07dff59e2c486375fd53e34f4396` |
| database/four_feature_v1/data/portrait_four_features_v1.sqlite3 | `4d9b5436ac40209fe24b23c46657d00b3befafdbf2e40e37e4ce4f755ce9e2c7` |
| database/migrations/001_four_features_v1.sql | `f48ee1916f66aebc7f91b8d3ce4a479d2d08091173f0306bcf6fa62eeff3fba2` |
| database/four_feature_v1/evidence/authority.json | `ea0b144ac265b33a130b16ecf7ac3ef110283616bcfcac8a7da621049261dfea` |
| database/four_feature.py | `8a88de840ef8dd7206d4d29cd3c1aa112c50bc134e92f124553cf43d383f9463` |
| database/verify_four_feature.py | `c40b3c3ff7c085a37c987161ab1afb097eab22733cd98c85c3ec3856e4a23fa1` |
| database/four_feature_v1/evidence/verification.json | `73bbf9542aa4198f6480eb33f14ae95c7ebcbeb38c8f841c15659da55a776684` |
| database/four_feature_v1/evidence/full_ranking_comparison.csv | `160e58b371f5f55f7f2e38a420c20107a59b48a66d20cd47d15fdf850488b9b0` |
| database/four_feature_v1/evidence/vector_roundtrip.csv | `ea0184dc8c39428a75946bf75c521c14a83c5d7af6afc5d553b3835fe5549fe8` |
| database/four_feature_v1/evidence/baseline_before.json | `8c48fb41a7dc6488672ab2ffaeb1ef52f708c01638bb1e1b20d217a90ee56d15` |

Các file khác ở evidence/created_files_manifest.json; manifest không tự chứa chính nó.
SQLite vẫn được ignore theo yêu cầu Git trước đó; file thực tế lưu ở namespace trên.

## Giới hạn còn giữ nguyên

C1 ROI v0.4 là project-selected/provisional, không anatomy-approved; không ghi ACCEPT hoặc APPROVED vào hồ sơ review.
Mapping A478→68/nose endpoints và alignment lịch sử còn UNVERIFIED; metadata mắt là audit_remeasurement.
Anatomy của C2 fixed center crop chưa xác minh. Dataset HF333/HF561 có mặt phụ, HF722 có tay che miệng vẫn tồn tại;
HF209 thiếu B là vấn đề feature khác. Giữ nguyên person labels NULL của HF, không suy người/tuổi/giới từ ngoại hình.
Chưa có relevance ground truth để kết luận fusion nâng accuracy.
Không sửa PDF, dataset, extractor, normalization/calibration/weights hoặc Top5; không GUI hoặc xử lý ảnh mới.

## Lệnh PowerShell đã chạy thành công

Chạy tại repository root với .venv311 đã có, không cài thêm thư viện. Import/backup/JSON output chỉ dùng đích mới;
không rerun ghi đè những đích này. demo.ps1 dùng --no-save, có thể chạy lại mà không đổi snapshot.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature import
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s database/tests -p test_four_feature.py -v
foreach ($sqlFusionQuery in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00722.png','hf_merged_00209.png')) {
    $sqlFusionId = [System.IO.Path]::GetFileNameWithoutExtension($sqlFusionQuery)
    $sqlFusionOutput = "database/four_feature_v1/queries/$sqlFusionId.json"
    $sqlFusionResult = .\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature search --image $sqlFusionQuery --top-k 5 --weight-a 0.25 --weight-b 0.25 --weight-c1 0.25 --weight-c2 0.25 --output $sqlFusionOutput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $sqlFusionResult | ConvertFrom-Json | Select-Object status, run_id, candidate_count, self_exclusion_count, ranked_candidate_count
}
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature backup --destination database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature backup --db database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3 --destination database/four_feature_v1/restored/portrait_four_features_v1.sqlite3
.\.venv311\Scripts\python.exe -X utf8 -B -m database.verify_four_feature
& .\database\four_feature_v1\demo.ps1 -Image cfd_final_00001.png -TopK 5 | ConvertFrom-Json | Select-Object status, candidate_count, self_exclusion_count, ranked_candidate_count
.\.venv311\Scripts\python.exe -X utf8 -B -m database.report_four_feature
```
