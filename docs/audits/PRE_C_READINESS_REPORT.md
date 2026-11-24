# Kết luận sẵn sàng trước Bộ C

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. PDF chuẩn duy nhất cho yêu cầu dự án: `C:\Users\USER\Downloads\csdldpt.pdf`, 18 trang, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh lại. Trang ghi dưới đây là trang PDF vật lý. Tài liệu MediaPipe chỉ giải thích topology/API; không thay PDF và không cung cấp bảng chuyển canonical 478→68 cho báo cáo nhóm.

Phạm vi lần này là kiểm toán, không sửa mapping, A2, code chuẩn hóa, nguồn ảnh, mask, vector/stats/calibration/output v1/v2; không tạo CSDL hoặc C1/C2. File mới chỉ nằm trong `docs/audits/`: bốn báo cáo này, `pre_c_tools/` và `pre_c_evidence/`.


**Kết luận: A/B v2 là baseline số học có thể tái sử dụng với các giới hạn đã ghi; toàn hệ thống chưa đủ bằng chứng để công nhận 100% tuân thủ PDF.** Nhiệm vụ này không triển khai C1/C2 và không điều chỉnh thuật toán theo Top-5.

## Yêu cầu đã chứng minh và các khoảng trống

| Phạm vi | Trạng thái | Bằng chứng thực tế | Quyết định |
| --- | --- | --- | --- |
| Số lượng 68 điểm, thứ tự, serialization | EXACT trong phạm vi cấu trúc | Hai file mapping giống nhau; 478→68→136+14; ba raw vector thật tái lập; 42 phép kiểm A2. | Có thể đóng câu hỏi số học và cấu trúc này. |
| Membership của contour gốc | EXACT cho 66/68 điểm thuộc contour | 59 điểm ngoài mũi và 7 điểm mũi thuộc contour tương ứng; MP129/358 không có trên sparse NOSE. | Không suy ra canonical mapping hoặc endpoint A2 từ membership. |
| Chuẩn hóa A v2 | EXACT về phương trình; có quy ước đã chốt | ddof=0, raw_sigma+1e-8, giữ 150 chiều; query tái sử dụng stats. | Đóng A12 trên v2 trong phạm vi số học. |
| Chuẩn hóa B v2 | EXACT về trình tự; có IMPLEMENTATION DETAIL đã duyệt | Chuẩn hóa Lab24 trước concat, sau đó chuẩn hóa toàn bộ 144 chiều; giữ hai stage theo D15, class 1/17 và ngưỡng 100 pixel. | Đóng B12 trên v2 trong phạm vi đã chốt. |
| Pipeline số học A+B | EXACT có điều kiện trên vector v2 | Euclid riêng, join ID, cùng 20.000 cặp, median normalization, trọng số 0.5/0.5 và xử lý thiếu B rõ ràng. | Đây là thử nghiệm hai bộ; chưa phải fusion bốn bộ hoặc chứng nhận chất lượng truy hồi. |
| Đối chiếu hình minh họa 68 điểm | DEVIATION so với hình PDF | Trên cùng CFD00001, hai đầu hàm lệch dọc khoảng 34 pixel; thứ tự cao/thấp nhánh sống/đáy mũi ngược hình. | Đã đo sai khác, chưa đủ cơ sở chọn MP index thay thế; giữ nguyên v2. |
| Canonical mapping và endpoint A2 | UNVERIFIED | PDF thiếu bảng MP ID; endpoint giải phẫu, định nghĩa tâm mắt và hệ quy chiếu trái/phải còn mở. | Cần chuẩn hoặc annotation có thẩm quyền và xác nhận vai trò của hình trước khi sửa. |
| Ba ảnh dataset vi phạm | DEVIATION đã xác nhận lại | HF00333/HF00561 có mặt phụ; HF00722 che miệng. | Corpus hiện tại chưa đạt; giữ ảnh và lập phương án review theo phiên bản. |
| Ảnh thay thế từ nguồn | UNVERIFIED | Token provenance chưa định vị được nguồn, identity và ảnh thay thế hợp lệ. | Bổ sung repository/revision/shard/hash và nhãn nguồn trước khi thay. |
| CSDL ứng dụng | NOT IMPLEMENTED trong repository | Rà 74 file Python: không có import driver, DB pattern hay file DB/SQL; hiện lưu bằng file. | Cần tác vụ CSDL riêng với schema và kiểm chứng insert/load/query. |
| Toàn hệ thống tuân thủ 100% PDF | NOT READY | Dataset vi phạm, mapping/metadata còn thiếu bằng chứng, tầng CSDL ứng dụng chưa có. | Chưa đủ cơ sở ký nhận toàn hệ thống. |

**Sai khác mới được xác nhận:** mapping hiện hành không tái hiện vị trí/topology của hình 68 điểm trong PDF trên cùng CFD00001, đặc biệt đầu hàm và nhánh mũi. Phân loại DEVIATION này giới hạn ở việc đối chiếu minh họa; PDF chưa cho MP ID để xác định mapping thay thế. Canonical MP1/MP4, MP129/358 và endpoint A2 vẫn UNVERIFIED. Chưa phát hiện sai lệch mới ở luồng chuẩn hóa v2.

Các vi phạm ảnh đã biết được mở và xác nhận lại từ ảnh nguồn. Việc rà source xác định rõ tầng CSDL ứng dụng và phần lưu tọa độ hai tâm mắt còn thiếu trong repository; không có bằng chứng để kết luận về một CSDL ngoài phạm vi kiểm tra.

## Đóng băng A/B v2

| Hạng mục kiểm tra lại | Kết quả |
| --- | --- |
| Schema A | A150_report_v2.0.0 |
| Schema B | B144_report_v2.0.0 |
| Số file output v2 đóng băng | 54 |
| Shape A chuẩn hóa | [1438, 150] |
| Shape B chuẩn hóa | [1437, 144] |
| Sai số lớn nhất oracle A sigma+epsilon | 7.105427357601002e-15 |
| Sai số lớn nhất oracle B stage Lab | 9.769962616701378e-15 |
| Sai số lớn nhất oracle B đủ hai stage | 7.922551503725117e-13 |
| Số cặp calibration giữ nguyên | 20000 |
| Median A | 16.44198984041917 |
| Median B | 10.81430055226477 |
| Số bảng Top-5 kiểm lại | 9 |
| Query mới qua hai môi trường: đạt | True |
| Unit tests v2 chạy lại, không skip | 19 |
| Thiếu B được xử lý rõ, không zero-fill | True |

[v2_freeze_manifest.json](pre_c_evidence/v2_freeze_manifest.json) ghi hash từng file trong ba thư mục output v2, schema, calibration, hash danh sách cặp ID và kết quả kiểm chứng mới. Đóng băng bằng manifest và hash; không đổi quyền, tên hay nội dung file v2. Source ứng dụng và toàn bộ baseline cũng được so hash lần cuối tại [final_scope.json](pre_c_evidence/final_scope.json).

Oracle dùng phép tính scalar/fsum trên toàn bộ A/B; kiểm riêng stage Lab24 và stage cuối 144 chiều của B. Giữ ID và thứ tự của 20.000 cặp calibration cũ, tính lại độc lập dA, dB và hai median; chín bảng xếp hạng khớp kết quả đã lưu. Query mới chạy worker A trong `.venv311` và worker B trong `.venv-uniface`, kiểm đúng stats/version/hash và hai stage B. Output mới chỉ ghi trong `pre_c_evidence/`. Cả 19 unit tests v2 chạy lại đạt, không skip. Không fit lại stats/median hay ghi lại artifact đã nghiệm thu.

Query fixture là bản PNG mã hóa lại của CFD00001, cùng pixel nhưng khác hash byte. Nó kiểm chứng đường đi dành cho ảnh chưa có hash trong gallery qua hai môi trường; không đại diện cho độ chính xác trên khuôn mặt chưa từng xuất hiện. Thử nghiệm thiếu B kiểm riêng HF00209 và xác nhận không có vector zero-fill.

## Quy ước triển khai được giữ hợp lệ trong phạm vi hiện có

A dùng epsilon=1e-8, ddof=0; B giữ hai stage theo quyết định D15 của v2. Các quy ước HS12×4, Hue10, L1, Lab Pearson, circular moments, class 1/17, raw mask, ngưỡng 100 pixel và xử lý thiếu B giữ theo quyết định v2 đã ghi. Lần kiểm toán này không phát hiện xung đột mới với PDF trong phạm vi đó; không nâng các thông số PDF chưa chốt thành nguyên văn báo cáo.

ID, hash file, row mapping và trọng số 0.5/0.5 thuộc quy trình thử nghiệm đã công khai. Tâm sáu mốc mí, EAR, endpoint A2 và hệ quy chiếu trái/phải vẫn là quy ước hiện hành cần xác minh ý nghĩa giải phẫu.

## Hành động cần thiết trước khi ký nhận toàn hệ thống

1. Chốt canonical mapping, endpoint và hệ quy chiếu trái/phải có thẩm quyền. Đối chiếu mốc và 14 A2 với annotation độc lập, đặc biệt mũi, cao mặt, gò má, gonion và độ mở mí. Không lựa chọn theo Top-5.
2. Giải quyết vi phạm corpus theo quy trình review và version có truy vết, giữ bản cũ. Xác minh nguồn, identity và tiêu chí của ảnh thay thế trước khi lập manifest thay thế.
3. Bổ sung provenance cho thống kê người, cảm xúc, tuổi; quy trình alignment/encoder/crop; camera, dung sai và metadata mắt. Không ép số liệu hoặc suy đoán nhãn từ ảnh.
4. Triển khai CSDL trong nhiệm vụ riêng theo PDF: khóa ảnh/người, tọa độ mắt, version vector và trạng thái thiếu feature. Kiểm thử thực tế insert/load/query, khôi phục dữ liệu và đối chiếu round-trip.
5. Nếu đánh giá chất lượng truy hồi, cần nhãn relevance và quy trình đánh giá độc lập với dự đoán. Test công thức không thay thế nhãn đánh giá.

## Phạm vi có thể dùng để chuẩn bị đầu vào C mà không nhận nhầm chứng nhận

| Có thể tái sử dụng làm baseline kỹ thuật | Điều kiện phải mang theo | Chưa được suy ra |
|---|---|---|
| A150/B144 v2, stats/schema/fingerprints, calibration thử nghiệm, ID mapping | Giữ nguyên hash/version; join bằng ID; giữ trạng thái thiếu B và cờ dataset | Toàn corpus hoặc mapping giải phẫu đã đạt PDF. |
| 1438 ảnh gốc và metadata làm nguồn thực nghiệm đã định danh | Giữ cờ vi phạm/UNVERIFIED riêng; ảnh và version mới phải có lineage | Mọi ảnh đạt một mặt/chính diện/không che hoặc đủ B. |
| Giao 1437 ID đủ A/B cho thử nghiệm fusion sau này | Không zero-fill; tạo calibration version mới nếu đặc trưng/tập ID đổi; phân biệt thử nghiệm với fusion chính thức | Đã có C1/C2, vector 854 chiều hoặc DBMS. |
| Interface và mapping hiện có để thiết kế hợp đồng dữ liệu, đánh giá | Nêu rõ endpoint A chưa được chốt; ROI cho C1 cần review theo PDF trước khi công nhận | Mọi landmark hiện tại đều là canonical hoặc ROI giải phẫu đã được chứng nhận. |

Đây là **khả năng tái sử dụng baseline kỹ thuật có điều kiện**. Nếu cần ký nhận hệ thống tuân thủ trước khi triển khai C chính thức, mapping, dataset và CSDL vẫn còn các điều kiện chưa đạt. Nhiệm vụ hiện tại không tạo feature, code, vector hay calibration cho C.

## Báo cáo và bằng chứng

- [A_MAPPING_FINAL_REVIEW.md](A_MAPPING_FINAL_REVIEW.md)
- [DATASET_FINAL_REVIEW.md](DATASET_FINAL_REVIEW.md)
- [DATABASE_COMPLIANCE_REVIEW.md](DATABASE_COMPLIANCE_REVIEW.md)
- [created_files_manifest.json](pre_c_evidence/created_files_manifest.json) liệt kê hash các file mới, trừ chính manifest này.

Lệnh PowerShell đã chạy thành công từ thư mục gốc repository:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/pre_c_tools/review_mapping.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/pre_c_tools/review_pdf_illustration.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/pre_c_tools/review_storage_dataset.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/pre_c_tools/freeze_v2.py
.\.venv-uniface\Scripts\python.exe -X utf8 -B docs/audits/pre_c_tools/write_reviews.py
```

Worker query đã chạy với `--output docs/audits/pre_c_evidence/new_query_a` và `new_query_b`. Hash PDF và 14267 file baseline được kiểm tra trước/sau. Phạm vi loại trừ môi trường ảo, bytecode và browser profiles được ghi rõ ở [authority.json](pre_c_evidence/authority.json); đây là kiểm tra repository, không phải điều tra CSDL ngoài dự án.
