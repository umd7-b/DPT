# SQLite cho Portrait Retrieval A/B v2

SQLite là **quyết định triển khai thử nghiệm cục bộ**, không phải DBMS do PDF quy định. Tầng này lưu metadata, vector, stats, calibration và kết quả truy vấn trong CSDL quan hệ thật. Nó không thay công thức trích xuất hoặc thứ hạng của hệ thống file v2.

Nguồn yêu cầu: `csdldpt.pdf`, §1.3 và §2.5, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Các báo cáo audit trước triển khai được giữ nguyên như hồ sơ lịch sử. Xem [báo cáo triển khai](implementation_report.md) và [kết quả kiểm chứng](evidence/verification_summary.json).

## File và môi trường

| File | Vai trò |
| --- | --- |
| [schema.sql](schema.sql) | Schema version 1; PK, NOT NULL, FK, UNIQUE, CHECK, trigger và view |
| [store.py](store.py) | Import có transaction, codec vector, SELECT/load/search, lưu run và backup |
| [__main__.py](__main__.py) | CLI `python -m database` |
| [data/portrait_ab_v2.sqlite3](data/portrait_ab_v2.sqlite3) | CSDL thử nghiệm có dữ liệu thật |
| [backups/portrait_ab_v2.backup.sqlite3](backups/portrait_ab_v2.backup.sqlite3) | Snapshot bằng SQLite backup API |
| [restored/portrait_ab_v2.sqlite3](restored/portrait_ab_v2.sqlite3) | File phục hồi từ snapshot, đã SELECT và truy vấn lại |
| [examples.sql](examples.sql) | Ví dụ SQL đã thực thi bằng Python sqlite3 |
| [tests/test_database.py](tests/test_database.py) | Unit và integration tests với corpus thật |
| [verify.py](verify.py) | Bằng chứng toàn kho, Top-5, backup/restore và hash baseline |

Không thêm dependency. Import, query ảnh đã có và tests chạy trong `.venv311` hoặc `.venv-uniface` với NumPy có sẵn. SQLite dùng module chuẩn `sqlite3`. Không cần server hoặc chương trình `sqlite3.exe`.

## Cấu trúc logic

PDF mô tả ba **nhóm** A/B/C và bốn **vector** A/B/C1/C2; PDF không quy định chính xác số bảng/cột SQL. Schema chọn một bản ghi vector cho mỗi `(image_id, feature_version)`, dùng `logical_group` và `feature_name` để phân biệt nhóm và vector. C1/C2 có thể được đăng ký sau với version/stats riêng, nhưng **không có bản ghi version, vector hay calibration giả cho C** trong CSDL hiện tại.

| Thực thể | Nội dung và quan hệ |
| --- | --- |
| DatasetVersions | Nhãn corpus cục bộ bất biến và hash metadata nguồn |
| Images | 1438 mã ảnh, tên/path, hash, kích thước, nguồn, dataset version; cả thứ tự catalog và `a_row_index` |
| Persons | 407 ID có namespace từ metadata CFD; FK `Images.person_id` cho phép NULL |
| EyeCoordinates | Ba phép đo audit có provenance; vai trò `audit_remeasurement`, không phải tiền xử lý gốc |
| FeatureVersions | Hai version A150/B144, schema, dimension/dtype, normalization version, hash stats và trạng thái có giới hạn |
| NormalizationStages | Một stage A và hai stage B; NPZ lưu nguyên byte trong BLOB, theo thứ tự stage |
| FeatureVectors | 2876 bản ghi: 1438 A hợp lệ, 1437 B hợp lệ và một B thiếu với payload NULL |
| Calibrations/Components | Tham số median/epsilon đã có, version từng vector và fingerprint nguồn |
| CalibrationCandidates/Pairs/PairDistances | 1437 ứng viên theo đúng thứ tự; 20.000 cặp có thứ tự và 40.000 khoảng cách đã lưu |
| RetrievalRuns/QueryVectors | Query/hash, mode A/B/AB, trọng số, version, calibration, self-exclusion, query vector và provenance |
| RetrievalResults | Mã ảnh, rank, dA/dB, khoảng cách chuẩn hóa, D_AB và score; FK đến run và ảnh |

Khóa ngoại bật trên **mọi connection do module tạo**. Các client SQL khác cũng phải dùng `PRAGMA foreign_keys=ON`. Các khóa chính kiểu TEXT có NOT NULL tường minh. Vector có composite FK đến dtype/dimension của version; chỉ số hàng A có composite FK đến đúng ảnh. Các row index dùng để truy vết matrix cụ thể, không thay `image_id` hoặc `person_id`.

## Bảo toàn vector và tham số

`vector_data` chứa byte IEEE liên tiếp theo C-order, không chuyển qua JSON số hoặc làm tròn decimal. `dtype` lưu cả endian (`<f8` cho các vector chuẩn hóa v2 đang import), `dimension` là 150/144, kèm SHA-256 từng payload. Loader kiểm độ dài, hash và giá trị hữu hạn. Kiểm chứng đối chiếu **toàn bộ 2875 vector hợp lệ theo byte**, không chỉ dùng tolerance.

`NormalizationStages.stats_data` giữ nguyên byte NPZ gốc, gồm mean, raw_sigma, effective_divisor, epsilon/ddof và fit provenance. `FeatureVersions.stats_hash` là SHA-256 của JSON canonical danh sách `(stage_name, stats_sha256)` theo thứ tự stage; `schema_hash` là hash file schema artifact nguồn. A giữ sigma+epsilon; B giữ stage Lab24 rồi final144. Không fit lại stats.

Calibration giữ nguyên JSON và CSV nguồn dưới dạng BLOB có hash, cùng biểu diễn quan hệ của ứng viên, cặp và khoảng cách. Median A=`16.44198984041917`, B=`10.81430055226477`, epsilon=`1e-8`; không calibration riêng theo ảnh query. Việc tính lại khoảng cách trong verifier chỉ kiểm chứng dữ liệu, không thay tham số đã lưu.

HF00209 có B `status='missing'`, `vector_data=NULL`, `feature_row_index=NULL`, `missing_reason='hair:missing_empty(0<100)'`. Không zero-fill, không đổi trọng số để bù. HF00210 có `a_row_index=919` và B `feature_row_index=918`; import lấy vector qua ID và chỉ số tường minh.

## Tâm mắt và người

Không có tọa độ hai mắt từ tiền xử lý gốc trong metadata hiện hành. Ba phép đo đã lưu từ lần audit trước được nhập cho CFD00001, CFD00069 và HF00001, đối chiếu lại landmark/evidence/model hash. Method là `audit_mean6_eyelid_scalar_f64`: trung bình scalar float64 của sáu điểm mí có tọa độ pixel float32. Hệ quy chiếu trái/phải theo code/người xem được ghi rõ. Không gán chúng thành tọa độ đồng tử hoặc phép đo gốc đã mất.

1435 ảnh khác không có dòng EyeCoordinates; LEFT JOIN trả NULL. Cả 1438 ảnh chưa có bằng chứng tọa độ tiền xử lý gốc. `model_version` chứa phiên bản package và hash model; provenance lưu hash ảnh, landmark, evidence và script. Không chạy detector để bịa metadata còn thiếu.

407 người là **ID trong namespace nguồn CFD**, không phải bằng chứng xác nhận 1135 người toàn corpus. 728 ảnh HF giữ `person_id=NULL`. Không suy đoán tuổi/giới/danh tính từ ảnh.

## Import và truy vấn

Chạy tại `D:\TuNam4\portrait-retrieval` bằng PowerShell. CSDL bàn giao đã tồn tại; import vào đường dẫn có sẵn bị từ chối. Muốn dựng một bản riêng:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m database import-v2 --db database/data/portrait_ab_v2_new.sqlite3
```

Importer kiểm hash/gallery/version, ID/order và ảnh nguồn trước/khi INSERT. DDL và dữ liệu nằm trong một transaction. Lỗi import rollback, chỉ loại file mới do chính lần import đó tạo. Không ghi vào các thư mục A/B v2.

Các lệnh dùng CSDL bàn giao:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m database info
.\.venv311\Scripts\python.exe -X utf8 -B -m database image --image-id hf_merged_00209
.\.venv311\Scripts\python.exe -X utf8 -B -m database search --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B -m database search --image hf_merged_00209 --mode all --no-save
```

`--mode all` lưu ba run riêng A/B/AB trong cùng transaction. `--no-save` mở connection chỉ đọc và không lưu run. Top-5 mặc định dùng **cùng giao 1437 ứng viên đủ A/B**, đúng hệ thống thử nghiệm file hiện tại; A-only không tự mở rộng ứng viên lên 1438. Query thiếu B có kết quả A-only, mode B/AB rỗng và trạng thái thiếu B được lưu rõ.

Gallery, vector, stats và calibration của query ảnh đã có được SELECT từ SQLite. Euclid, median normalization và tie-break tên ảnh vẫn dùng hàm đã có của v2; không thêm SQL extension/ANN hoặc thay thuật toán. Self-match giữ nhận dạng bằng hash byte, loại mọi ID có cùng hash. Đây là **thử nghiệm hai bộ**, không phải fusion chính thức bốn vector.

Ảnh mới 256×256 RGB dùng worker A trong `.venv311` và B trong `.venv-uniface`, giữ pipeline hiện hành. Worker còn đọc gallery/stats v2 nguồn để xác minh và trích xuất theo code cũ; kết quả chỉ được dùng nếu hash stats trùng BLOB trong CSDL. Sau đó ứng viên và vector để xếp hạng được đọc từ SQLite. Vì vậy nhánh ảnh mới còn cần các model, hai môi trường và artifact worker gốc; không tuyên bố nó độc lập hoàn toàn với file. Không tải model hay cài thư viện.

API tối thiểu:

```python
from contextlib import closing
from database import store

with closing(store.connect()) as connection:
    image = store.get_image(connection, 'cfd_final_00001')
    vector = store.get_vector(connection, image['image_id'], store.a_v2.SCHEMA_ID)
    result = store.search(connection, image['image_id'], persist=False)
```

## Backup và phục hồi

Dùng SQLite backup API, không copy file đang có transaction. Đích phải mới:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m database backup --destination database/backups/manual_snapshot_01.sqlite3
.\.venv311\Scripts\python.exe -X utf8 -B -m database backup --db database/backups/manual_snapshot_01.sqlite3 --destination database/restored/manual_restore_01.sqlite3
```

Verifier đã kiểm `integrity_check`, `foreign_key_check`, hash SQL dump toàn bộ bảng và Top-5 sau phục hồi. Backup hiện tại là snapshot của thời điểm kiểm chứng; query có lưu sau đó sẽ thay file primary và cần snapshot mới.

## Tests và giới hạn chứng nhận

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s database/tests -v
```

`python -m database.verify` là quy trình bằng chứng một lần: lưu thêm run vào CSDL rồi tạo các đường dẫn backup/restore cố định và từ chối ghi đè chúng. Không chạy lại trên snapshot đã bàn giao; tests dùng CSDL tạm riêng và không sửa CSDL bàn giao.

Dataset vẫn có ảnh mặt phụ/che miệng; mapping vẫn khác hình minh họa PDF và endpoint canonical chưa được xác minh. Việc có CSDL không giải quyết các vấn đề này, số người/nhãn nguồn hoặc tọa độ mắt gốc còn thiếu. **Không tuyên bố toàn hệ thống tuân thủ 100%, không triển khai C1/C2.**
