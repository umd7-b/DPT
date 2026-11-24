# Kiểm tra CSDL ứng dụng theo PDF

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. PDF chuẩn duy nhất cho yêu cầu dự án: `C:\Users\USER\Downloads\csdldpt.pdf`, 18 trang, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh lại. Trang ghi dưới đây là trang PDF vật lý. Tài liệu MediaPipe chỉ giải thích topology/API; không thay PDF và không cung cấp bảng chuyển canonical 478→68 cho báo cáo nhóm.

Phạm vi lần này là kiểm toán, không sửa mapping, A2, code chuẩn hóa, nguồn ảnh, mask, vector/stats/calibration/output v1/v2; không tạo CSDL hoặc C1/C2. File mới chỉ nằm trong `docs/audits/`: bốn báo cáo này, `pre_c_tools/` và `pre_c_evidence/`.


## Kết luận trong phạm vi repository

**Tầng HQT/CSDL ứng dụng chưa được triển khai trong repository đã kiểm tra.** Hiện lưu artifact bằng CSV/NPY/NPZ/JSON; không có bằng chứng bảng/schema, kết nối, insert hoặc query bằng DBMS cho ảnh, metadata và vector. Việc NumPy load file không chứng minh đã query CSDL. Không suy ra rằng một CSDL chưa biết ở máy chủ khác không tồn tại.

PDF §1.3 trang 5 nêu lưu metadata gồm mã ảnh, đường dẫn, vị trí hai mắt vào CSDL; §2.5.1 trang 16 mô tả lưu vector riêng để so sánh/kết hợp. PDF không chốt SQLite/PostgreSQL/MySQL hoặc kiểu dữ liệu SQL. Cách diễn đạt “bốn vector” nhưng “ba cột” cần tác giả làm rõ trước khi công nhận schema vật lý là tuân thủ hoàn toàn. Khoảng trống triển khai CSDL và điểm chưa rõ của đặc tả cần được giải quyết riêng; không tạo DB mới trong audit.

## Bằng chứng rà source và file thực tế

- Scan AST/import và các pattern connection/DDL/insert/SQL trên **74 file Python đang hoạt động** ở features/src/shared/retrieval/scripts/tests: **0 import driver/ORM, 0 match DB pattern**.
- File DB/SQL thuộc phạm vi dự án, ngoài môi trường ảo, Git, backup và browser profiles: **0**. Không dùng SQLite cache của trình duyệt như bằng chứng DB dự án.
- Không dò dịch vụ/credential hoặc kết nối DB ngoài dự án; không tạo file DB, DDL, migration hoặc insert thử. Việc máy có công cụ DB cài sẵn không chứng minh ứng dụng đã có CSDL.
- Source hàm/dòng/hash, configs và danh mục lưu trữ: [database_inventory.json](pre_c_evidence/database_inventory.json). Scan chỉ nêu vị trí match nếu có, không in connection secrets.

| Hạng mục | Hiện thực quan sát | Trạng thái |
|---|---|---|
| DBMS/connection/transaction | Không tìm thấy driver/ORM/config kết nối hoặc connection code ứng dụng | NOT IMPLEMENTED trong repository; hệ thống ngoài phạm vi là UNVERIFIED. |
| Bảng metadata | Catalog `metadata.csv`; A/B có CSV riêng | Có file catalog; chưa có bảng DB, FK hoặc transaction chứng minh đáp ứng phần CSDL. |
| Khóa ảnh | image_id từ mã ảnh/stem filename; SHA-256 là bằng chứng nội dung | Dùng được để join artifact; chưa có primary/unique key DB. |
| Khóa người | source_person_id trên 710 CFD rows, 407 source-scoped IDs; 728 HF trống | Chưa có bảng persons hoặc FK; không coi image_id là person_id. |
| Đường dẫn ảnh | image_path tuyệt đối trong metadata A/B; filename/path/hash ở catalog nguồn | Có giá trị file path thực; chưa lưu/query được qua DBMS. |
| Tọa độ tâm hai mắt | Catalog có các cột eyeXY=[]; A metadata có eyeXY=[]; A có eye_distance | Khoảng cách không phải hai tọa độ. Mảng landmark ở audit không phải bảng tâm mắt của ứng dụng. |
| Vector A/B | `.npy`: A1438×150, B1437×144; stats `.npz`; schema/hash `.json` | File đúng version có kiểm chứng số học; chưa có cột/vector row DB theo image_id. |
| image_id/a_row_index/feature_row_index | CSV mapping và join Python | Liên kết đúng artifact; row index không phải khóa danh tính bền vững hoặc FK DB. |
| Load/query | `np.load`, `csv.DictReader`, norm và sort trong RAM | Retrieval trên file; chưa có DB select/load hoặc transaction round-trip. |
| Bằng chứng thực nghiệm | V2 query files, CSV, PNG và hash đã kiểm tra | Chứng minh file persistence và số học; chưa chứng minh insert/SELECT hoặc phục hồi DB. |

## Theo dõi code kết nối/insert/load/query

`shared/report_v2.py::read_csv/load_stats` đọc file. `features/A_geometry/src/report_v2.py::build/load_gallery` ghi/đọc metadata CSV, raw reference JSON, NPY/NPZ. Bộ B tương tự với hai stage stats. `retrieval/search_ab_v2.py::load_gallery` gọi các loader file; `retrieval/search_ab.py::join_galleries/rankings` join bằng dict và tính Euclid/lexsort NumPy. Main lưu CSV/JSON/PNG. Không có đường đi connection/insert để kiểm transaction hoặc query DB.

Một ví dụ quan hệ hiện hành: HF00209 có a_row_index=918 nhưng không có B feature_row_index; các ảnh hợp lệ sau nó lệch một chỉ số giữa A/B. Vì vậy schema sau này phải liên kết bằng image_id và feature version; row index chỉ làm provenance của manifest/matrix cụ thể.

## Thiết kế đề xuất — chưa tạo CSDL

| Thực thể đề xuất | Nội dung/khóa cần lưu | Ràng buộc cần chứng minh |
|---|---|---|
| Images | image_id, sha256, source locator/revision, image_path, width/height | image_id ổn định, hash nội dung; ảnh mới có ID và lineage mới. |
| Persons | person_key, source_namespace, source_person_id, evidence | FK ảnh→người có thể NULL; không gán theo ngoại hình; source IDs không mặc nhiên toàn cục. |
| DatasetVersions/Membership | dataset_version, image_id, review_flags, status, replaces_image_id | Bảo toàn corpus cũ; lịch sử review và tổng số người có chứng cứ. |
| EyeCoordinates | image_id, detector/model/mapping version, left_x/y, right_x/y, frame/method | Không nhầm centroid sáu mí với pupil/iris; lưu đơn vị, kích thước và định nghĩa. |
| FeatureVersions | kind=A/B, schema_id, fit manifest, stats/source hashes, dtype, dimension | A150/B144 giữ version và hai stage B rõ; không dùng stats v1 cho v2. |
| FeatureVectors | image_id, feature_version, vector, status/reason | Unique(image_id,feature_version); B thiếu có NULL/status, không vector zero-fill; row index chỉ là provenance. |
| Calibrations | version, pair IDs/hash, epsilon, median A/B, vector fingerprints | Tính lại khi vector/tập ID đổi; không tính median riêng theo query. |
| RetrievalRuns/Results | query ID/inputs, feature/calibration versions, weights, dA/dB/normalized/D, rank | Đối chiếu round-trip với oracle file; không lẫn image_id và person_id. |

Đây là mô hình khái niệm để phân tích trách nhiệm lưu trữ, chưa phải schema vật lý đã được chứng nhận. Nhóm cần chọn HQT, kiểu lưu vector và làm rõ “ba cột/bốn vector” với tác giả; ưu tiên giữ A/B tách riêng đúng mục đích so sánh từng bộ. Tham chiếu file có checksum chỉ là phương án storage cần được chấp nhận riêng, không tự coi là đã đáp ứng yêu cầu lưu vector trong CSDL.

Kiểm nghiệm tối thiểu khi triển khai: migration/version; insert/load/select bằng transaction; unique/FK; round-trip 150/144 giá trị và dtype/hash; query dùng đúng stats/calibration; thiếu B có trạng thái; không đổi ranking do lỗi lưu/khôi phục; backup/restore và truy vết. **Không có DDL/DB/table/row nào được tạo trong lần audit.** Không thêm C1/C2.
