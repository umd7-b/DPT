# SQLite bốn bộ — kiểm chứng tích hợp

Ngày **24/11/2026**, Asia/Saigon. **Đã tích hợp và kiểm chứng SQLite cho bốn vector; EXPERIMENTAL_EQUAL_WEIGHTS.**
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`, đã đọc trực tiếp §1.3 và§2.5.1–2.5.3.
Đã đọc schema, toàn bộ module database cũ, nguồn retrieval và các báo cáo C1/C2/fusion yêu cầu.
Không tuyên bố anatomy-approved, accuracy tăng hoặc 100% toàn hệ thống tuân thủ.

| Bộ | Phiên bản | Dimension/dtype | Valid | Missing |
|---|---|---|---:|---:|
| A | `A150_report_v2.0.0` | 150/`<f8` | 1438 | 0 |
| B | `B144_report_v2.0.0` | 144/`<f8` | 1437 | 1 |
| C1 | `C1_LBP236_FULL_ROI_V04_v1` | 236/`<f8` | 1438 | 0 |
| C2 | `C2_ROOT_HOG324_FULL_v1` | 324/`<f8` | 1438 | 0 |

| Bộ | Median giữ nguyên |
|---|---:|
| A | 16.441989840419168 |
| B | 10.81430055226477 |
| C1 | 0.30520587913351654 |
| C2 | 0.21819130381743668 |

## Kết quả thực nghiệm

- Exact IEEE byte round-trip: 5751 valid vectors; 5752 status records gồm 1 missing B.
- C1/C2 mỗi bộ có 1438 float64 vectors 236/324 chiều; A/B v2 giữ nguyên.
- Nhập 20.000 pairs và 80.000 component distances mới exact; không sampling/refit median.
- Giữ calibration AB v2 và mọi phiên bản lịch sử; median 4 bộ và epsilon 1e-8 không đổi.
- Full ranking parity: 5 query × 1436 candidate × 5 mode = 35.900 rows; ordered IDs và mọi distance exact, max error 0.
- Declared parity tolerance atol1e-12/rtol1e-12 đã khóa trước import tại authority.json.
- 125 Top5 rows và 6 query histories INSERT/SELECT khớp; HF209 fusion_unavailable, 0 result, không zero-fill.
- 176 tests PASS, 0 skip/failure/error: 140 regression + 19 database cũ + 17 SQL mới.
- Backup/restore integrity ok, FK empty, SQL dump và mọi query/full ranking khớp.
- 17915 file baseline trước/sau không đổi; 19 bảng nguồn giữ mọi dòng đã có exact.

| Query | Trạng thái | Candidate | Loại self | Đã xếp hạng | Rows Top5 đã lưu |
|---|---|---:|---:|---:|---:|
| cfd_final_00001 | ok | 1436 | 1 | 1436 | 25 |
| cfd_final_00069 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00001 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00198 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00722 | ok | 1436 | 1 | 1436 | 25 |
| hf_merged_00209 | fusion_unavailable | 1437 | 0 | 0 | 0 |

## Nguồn expected và tính độc lập

Parity expected dùng gallery/calibration file đã nghiệm thu và retrieval.search_fusion; actual dùng SQL adapter
đọc BLOBs và calibration quan hệ. Hai luồng dùng cùng hàm số học đã kiểm chứng, đúng yêu cầu tái sử dụng.
Nhiệm vụ này kiểm serialization/identity/calibration/persistence, không viết lại numerical oracle.
Oracle math.fsum độc lập của 20.000 pairs và 5 full rankings đã được đóng băng ở
outputs/retrieval/fusion_ab_c1_c2_v1/evidence/verification.json; các tests cũ được chạy regression.
Không gọi SQL query để tự tạo expected, không dùng Top5 để chọn trọng số.

DB nguồn SHA-256: `6fc6213286c715edf997ed9484ca1da8da0d07dff59e2c486375fd53e34f4396`.
1438 Images, 1441 audit EyeCoordinates và 1438 sources được backup trước additive migration.
Nguồn/user_version=1 và schema.sql giữ nguyên; extension có version độc lập FOUR_FEATURE_SQLITE_v1.
Thêm 8 bảng, 3 explicit indexes, 1 trigger, 1 view; không ALTER cột cũ.

## Bằng chứng

- [Verification JSON](../../database/four_feature_v1/evidence/verification.json)
- [Toàn bộ 35900 ranking rows](../../database/four_feature_v1/evidence/full_ranking_comparison.csv)
- [5751 vector bytes](../../database/four_feature_v1/evidence/vector_roundtrip.csv)
- [125 Top5 rows](../../database/four_feature_v1/evidence/top5_before_after.csv)
- [Bảo toàn 19 bảng](../../database/four_feature_v1/evidence/original_table_preservation.json)
- [Schema/columns/constraints](../../database/four_feature_v1/evidence/schema_inventory.json)
- [Tests log](../../database/four_feature_v1/evidence/tests.log)

| File | SHA-256 | Integrity/full ranking |
|---|---|---|
| database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3 | `0d40f0fc248813e52590620d52bfe0a68efe8df5a2088c12714f38dae8050949` | ok/exact |
| database/four_feature_v1/restored/portrait_four_features_v1.sqlite3 | `0d40f0fc248813e52590620d52bfe0a68efe8df5a2088c12714f38dae8050949` | ok/exact |

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

## Phạm vi kết luận

Đã triển khai lưu 4 vector riêng và truy vấn SQL đúng công thức PDF §1.3/§2.5 trên snapshot hiện có;
SQL/BLOB/version/schema là quy ước triển khai, không phải số bảng/cột do PDF chỉ định.
Không chứng nhận anatomy ROI/C2 crop, mapping A, alignment lịch sử, tiêu chí dataset hoặc retrieval accuracy.
Không GUI/ảnh mới và không sửa PDF/vectors/weights/calibration để thay Top5.
[Báo cáo đầy đủ và PowerShell demo](../../database/FOUR_FEATURE_INTEGRATION_REPORT.md).
