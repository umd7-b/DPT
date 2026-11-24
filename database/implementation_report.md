# Triển khai CSDL cho Portrait Retrieval A/B v2

Ngày nghiệm thu: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `csdldpt.pdf`, §1.3 và §2.5, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đối chiếu. Đã đọc năm báo cáo được yêu cầu; giữ nguyên chúng như hồ sơ trước khi có tầng CSDL.

**Đã triển khai và kiểm chứng tầng SQLite thực sự. Chưa chứng nhận toàn hệ thống tuân thủ 100% PDF.** Chỉ thêm thư mục `database/`; không sửa pipeline, mapping, dataset, PDF, vector, stats, calibration hay kết quả query v1/v2. Không triển khai C1/C2.

## Phạm vi yêu cầu và lựa chọn triển khai

| Yêu cầu | Hiện thực và bằng chứng | Kết luận có giới hạn |
| --- | --- | --- |
| §1.3: mã ảnh, đường dẫn và metadata vào CSDL | Images có PK, hash, kích thước, source, dataset version; INSERT/SELECT thực tế 1438 ảnh | Đã có lưu trữ quan hệ và truy xuất metadata; không chứng nhận tiêu chí nội dung từng ảnh. |
| §1.3: vị trí hai mắt | EyeCoordinates có method/model/frame/role/provenance và ba phép đo audit | Chưa có tọa độ tiền xử lý gốc; 1435 ảnh chưa có phép đo audit. Không khai báo hoàn tất phần metadata mắt. |
| §2.5.1: giữ vector riêng để so sánh từng bộ/kết hợp | FeatureVectors chứa BLOB A150/B144 tách theo image_id và feature_version | Đã thực hiện cho A/B; không tự coi số bảng/cột SQL là nguyên văn PDF. |
| §2.5.2: tham số chuẩn hóa đã lưu | Một NPZ A và hai NPZ B được lưu nguyên byte và có hash/version/thứ tự stage | Giữ đúng v2 đã nghiệm thu; không fit lại, không đổi công thức. |
| §2.5.2: median normalization | Calibration relational lưu 20.000 cặp, 40.000 dA/dB, median/epsilon, candidate order và fingerprint | Dùng lại calibration v2, không tính median theo query. |
| §2.5.3: tổng có trọng số | SQL SELECT vector rồi hàm Euclid/median/rank hiện hành; RetrievalRuns/Results lưu version, trọng số và mọi khoảng cách | Chỉ thử nghiệm A+B 0.5/0.5; chưa phải fusion A/B/C1/C2 chính thức. |
| Khóa người | Persons có source_namespace + source_person_id; Images FK có thể NULL | 407 ID CFD; 728 ảnh HF không suy đoán identity. |

SQLite **3.45.1** qua module chuẩn `sqlite3` là IMPLEMENTATION DETAIL cho prototype cục bộ. PDF không chọn DBMS, kiểu BLOB, dtype/endian serialization, UUID run ID, schema migration/version hay số bảng. Schema version 1 có **16 bảng**, các PK/FK/UNIQUE/CHECK và view/trigger; đây là thiết kế triển khai, không phải số bảng do PDF quy định.

PDF nói ba nhóm A/B/C nhưng bốn vector A/B/C1/C2. Schema thể hiện `logical_group` riêng với `feature_name`; mỗi vector/version là bản ghi độc lập, tránh ghép số chiều hoặc tạo vector giả. CalibrationComponents và các bảng cặp cho phép thêm version sau này. Loader/retrieval hiện chỉ phục vụ A/B; bổ sung C cần nhiệm vụ riêng, không có bản ghi C trong file bàn giao.

## Dữ liệu bàn giao

| Hạng mục | Số lượng |
| --- | --- |
| Images | 1438 |
| Persons | 407 |
| EyeCoordinates | 3 |
| FeatureVersions | 2 |
| FeatureVectors | 2876 |
| NormalizationStages | 3 |
| CalibrationPairs | 20000 |
| CalibrationPairDistances | 40000 |
| RetrievalRuns | 18 |
| RetrievalResults | 80 |
| valid_A | 1438 |
| valid_B | 1437 |

- [CSDL chính](data/portrait_ab_v2.sqlite3), SHA-256 `a74617294f5d60af432ff781cdd50b11f636d9a3ba43ba19a51d03a86eb535c1`.
- [Schema SQL](schema.sql), [module import/load/query](store.py), [CLI](__main__.py), [ví dụ SQL](examples.sql).
- [Snapshot backup](backups/portrait_ab_v2.backup.sqlite3) và [file phục hồi](restored/portrait_ab_v2.sqlite3).
- [README và hướng dẫn API](README.md).

Nhãn `dataset_HF_CFD_final:immutable_v1` là nhãn truy vết cục bộ, không tự gán nó là một release upstream. Catalog gốc có thứ tự khác A; Images giữ cả `catalog_row_index` lẫn `a_row_index`. Import A kiểm chỉ số hàng tường minh, B tra image_id rồi lấy đúng feature_row_index. HF00209 có a_row_index=918 nhưng thiếu B; HF00210 có a_row_index=919, B row=918. Không zip hai matrix.

## Vector, chuẩn hóa và calibration

**2875 vector hợp lệ** đọc từ SQLite khớp dtype, shape và byte với artifact v2: 1438 A150 và 1437 B144 float64. SHA payload từng hàng lưu trong CSDL và [vector_roundtrip.csv](evidence/vector_roundtrip.csv). Không serialize qua decimal/JSON số. Length CHECK cùng composite FK version/dtype/dimension ngăn mất chiều hoặc metadata dtype sai.

Ba NPZ normalization giữ nguyên byte, gồm scalar metadata và mảng tham số; [normalization_roundtrip.json](evidence/normalization_roundtrip.json). A dùng `(raw−mean)/(raw_sigma+1e-8)`, ddof=0. B giữ Lab24 trước concat và final144 riêng theo D15. Loader có thể đọc các tham số từ BLOB, không cần NPZ nguồn cho query ảnh đã có.

Median A=`16.44198984041917`, B=`10.81430055226477`, epsilon=`1e-8`. BLOB JSON/CSV calibration, danh sách ứng viên, thứ tự cặp và khoảng cách đều được bảo toàn. Tính lại Euclid từ vector SELECT cho toàn bộ 20.000 cặp cho max sai số A=0.0, B=0.0; phép kiểm này không thay median/stats đã lưu.

HF00209: B `status='missing'`, payload và feature_row_index đều NULL, reason `hair:missing_empty(0<100)`. Các thử INSERT/UPDATE sai bị từ chối bằng ràng buộc; [missing_b.json](evidence/missing_b.json), [constraints.json](evidence/constraints.json). Không zero-fill, không đổi trọng số hay lọc thêm ảnh để cải thiện Top-5.

## Metadata mắt có giới hạn

| image_id | left_x | left_y | right_x | right_y | Vai trò |
| --- | --- | --- | --- | --- | --- |
| cfd_final_00001 | 88.17080307006836 | 102.11359151204427 | 168.9585215250651 | 102.82492955525716 | audit_remeasurement |
| cfd_final_00069 | 87.96431223551433 | 102.16291681925456 | 166.66907246907553 | 102.46160507202148 | audit_remeasurement |
| hf_merged_00001 | 88.83979161580403 | 102.66320673624675 | 167.23843892415366 | 102.58268356323242 | audit_remeasurement |

Ba dòng dùng dữ liệu đã lưu ở audit trước: scalar float64 mean của sáu điểm mí pixel float32. Import xác minh hash model tại thời điểm audit, ảnh, landmark, evidence và script. `model_version` gồm MediaPipe package version và hash `face_landmarker.task`; `provenance_json` ghi rõ không phải tọa độ tiền xử lý gốc. Trái/phải theo code/người xem, không ngầm đổi sang hệ quy chiếu giải phẫu.

1435 ảnh khác không có dòng đo; LEFT JOIN trả NULL. Cả 1438 ảnh vẫn thiếu bằng chứng về tọa độ mắt được dùng ở bước tiền xử lý gốc. Không suy ngược tọa độ tuyệt đối từ vector A1 đã chuẩn hóa, không gán eye_distance thành hai tâm mắt và không dùng vị trí trong hình PDF làm metadata.

## Đối chiếu truy vấn trước/sau import

Đã INSERT run, query vector và result thực tế, rồi SELECT lại để đối chiếu. **15 chế độ trên năm trường hợp, 65 hàng kết quả**, giữ chính xác rank, ID/tên, dA, dB, normalized A/B, D_AB và score. Các trường hợp: CFD00001, CFD00088, CFD00144, HF00209 và new_query. CLI mẫu trước đó tạo thêm ba run/15 result; file bàn giao tổng cộng 18 run và 80 result.

| Rank | Ảnh A+B CFD00001 | dA từ DB | dB từ DB | D_AB từ DB | Mọi trường bằng file |
| --- | --- | --- | --- | --- | --- |
| 1 | cfd_final_00038.png | 11.311268707634891 | 6.985326867075205 | 0.6669421676040852 | True |
| 2 | cfd_final_00029.png | 11.740416532628645 | 7.282024837325859 | 0.6937103821488055 | True |
| 3 | cfd_final_00036.png | 13.375908897467028 | 7.631354089981295 | 0.7595968785857593 | True |
| 4 | cfd_final_00044.png | 12.408384717186053 | 8.268705637096096 | 0.7596425186171186 | True |
| 5 | cfd_final_00031.png | 13.513428773539635 | 7.854466010267181 | 0.7740944468126063 | True |

[top5_before_after.csv](evidence/top5_before_after.csv) lưu cột trước/sau ở đầy đủ độ chính xác; [ranking_comparison.json](evidence/ranking_comparison.json) lưu từng run/version tham chiếu. [sql_examples_results.json](evidence/sql_examples_results.json) chứa kết quả SQL thực thi, không chỉ ví dụ văn bản.

Tập ứng viên cho cả ba mode giữ giao A/B 1437 ảnh, đúng thử nghiệm file. Query thiếu B có A-only 5 kết quả; B/AB rỗng, dB/D_AB NULL. Self-match theo hash byte và tie-break tên ảnh giữ nguyên. Euclid/rank chạy bằng hàm NumPy hiện hành sau SELECT; không tuyên bố SQLite có ANN hoặc vector extension.

Query mới dùng đúng hai worker và môi trường gốc, hash stats được đối chiếu với CSDL; [new_query_provenance.json](evidence/new_query_provenance.json). Worker vẫn cần gallery/model file v2 để xác minh và trích xuất; gallery dùng xếp hạng được đọc từ SQLite. Fixture là PNG mã hóa lại cùng pixel CFD00001, khác hash byte; đây là smoke test đường đi ảnh mới, không phải đánh giá khuôn mặt holdout hoặc chất lượng nhận diện.

## Kiểm chứng, transaction và backup/restore

**19 unit/integration tests CSDL +19 regression tests v2 đạt, không skip.** Tests kiểm byte/endian/signed-zero, ID/order sau ảnh thiếu B, NPZ hai stage B, calibration, constraints, corruption detection, persistence, rollback và backup/restore; không sửa tests hay code A/B hiện có. Query ảnh đã có được kiểm khi file gallery loaders bị vô hiệu hóa. Logs: [tests.log](evidence/tests.log), [v2_regression_tests.log](evidence/v2_regression_tests.log).

Import dùng transaction DDL+dữ liệu; file có sẵn bị từ chối. Lỗi import rollback và loại đúng file mới vừa tạo, có test riêng. Mỗi connection bật FK. Retrieval lưu các mode trong một transaction. Backup/restore dùng SQLite backup API, đích mới; kiểm integrity, FK, toàn bộ SQL dump và Top-5 sau phục hồi.

Hash SQL dump nguồn/khôi phục: `84ae026dccf0f6d32408deeaa5629d19d0c56326538a5e64487a61c68f1bfb37`. [backup_restore.json](evidence/backup_restore.json) có hash từng file và kết quả. Backup phản ánh snapshot lúc nghiệm thu; query mới có lưu sẽ thay DB chính nhưng không thay artifact A/B v2.

**14313 file có sẵn kiểm hash trước/sau: không có thay đổi**, gồm PDF, dataset/masks, source, vector/stats/calibration/output v1/v2 và các audit trước. [baseline_before.json](evidence/baseline_before.json), [verification_summary.json](evidence/verification_summary.json), [final_scope.json](evidence/final_scope.json). Chỉ các file mới trong `database/` thuộc thay đổi lần này.

## Lệnh PowerShell thực tế đã chạy thành công

Từ `D:\TuNam4\portrait-retrieval`; stdout/log được lưu trong `database/evidence/`:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s database/tests -v
.\.venv311\Scripts\python.exe -X utf8 -B -m database import-v2
.\.venv311\Scripts\python.exe -X utf8 -B -m database search --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B -m database image --image-id hf_merged_00209
.\.venv311\Scripts\python.exe -X utf8 -B -m database.verify
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\.venv311\Scripts\python.exe -X utf8 -B -m database.report
```

`database.verify` đã chạy một lần và tạo snapshot; chạy lại sẽ từ chối trước khi ghi thêm run nếu snapshot tồn tại. Import/backup không ghi đè file có sẵn. Các lệnh dựng bản khác và backup thủ công ở README là ví dụ cho đích mới, không phải khẳng định đã chạy trên đường dẫn ví dụ đó.

## Những phần chưa được chứng minh hoặc chưa giải quyết

- Sai khác mapping với hình PDF ở đầu hàm/topology mũi đã được audit xác nhận; canonical MP ID thay thế, endpoint 14 A2, định nghĩa tâm mắt và frame trái/phải vẫn cần thẩm quyền. Không sửa mapping.
- HF00333/HF00561 có mặt phụ; HF00722 che miệng. CSDL nhập nguyên corpus, không xóa/crop/thay ảnh. HF00209 thiếu B không tự chứng minh vi phạm dataset; HF00694 còn vấn đề đại diện vùng tóc/che khuất cần review.
- Provenance chưa định vị được ảnh thay thế hợp lệ; nhãn người HF, tuổi/giới/cảm xúc, số 1135 người/303 ảnh cảm xúc và quy trình preprocessing/alignment còn thiếu bằng chứng.
- Tọa độ mắt audit không thay bằng chứng tiền xử lý gốc. Chưa có relevance labels để chứng nhận chất lượng truy hồi.
- Chỉ đóng khoảng trống **tầng CSDL A/B prototype đã triển khai và kiểm chứng**. Không nâng trạng thái toàn hệ thống lên 100% tuân thủ, không tạo C1/C2 hoặc fusion bốn vector.
