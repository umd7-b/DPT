# Kiểm tra dataset cuối trước Bộ C

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. PDF chuẩn duy nhất cho yêu cầu dự án: `C:\Users\USER\Downloads\csdldpt.pdf`, 18 trang, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh lại. Trang ghi dưới đây là trang PDF vật lý. Tài liệu MediaPipe chỉ giải thích topology/API; không thay PDF và không cung cấp bảng chuyển canonical 478→68 cho báo cáo nhóm.

Phạm vi lần này là kiểm toán, không sửa mapping, A2, code chuẩn hóa, nguồn ảnh, mask, vector/stats/calibration/output v1/v2; không tạo CSDL hoặc C1/C2. File mới chỉ nằm trong `docs/audits/`: bốn báo cáo này, `pre_c_tools/` và `pre_c_evidence/`.


## Xem lại đúng ảnh nguồn

Đã mở trực tiếp cả năm PNG tại `D:\TuNam4\dataset_HF_CFD_final\images`, so hash với metadata và xem lại tiêu chí PDF §1.2–1.3 trang 5. Không lấy cảnh báo detector làm ground truth. Các quan sát ảnh dưới đây xác nhận lại hai loại vi phạm trước đây; không suy đoán người, tuổi hay giới từ ngoại hình.

| Ảnh | Phân loại dataset | Quan sát và điều khoản | Tình trạng B v2 | Token nguồn gốc | Person ID nguồn | Khả năng thay thế hiện được chứng minh |
| --- | --- | --- | --- | --- | --- | --- |
| hf_merged_00333.png | DEVIATION | Mặt phụ hiện rõ ở hai mép; vi phạm không có khuôn mặt phụ, PDF trang5. | valid; hair=20630 | parquet_stream_3176 | Trống | Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ |
| hf_merged_00561.png | DEVIATION | Một phần mặt phụ với mắt ở mép trái; vi phạm cùng tiêu chí, PDF trang5. | valid; hair=28778 | parquet_stream_3481 | Trống | Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ |
| hf_merged_00722.png | DEVIATION | Tay/ngón chồng vùng miệng và mặt dưới; vi phạm không che vùng miệng, PDF trang5. | valid; hair=13069 | Female (10).parquet_row_5 | Trống | Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ |
| hf_merged_00209.png | IMPLEMENTATION DETAIL: thiếu B theo D12 | Khăn che tóc; mắt/mũi/miệng quan sát được. Hair=0 làm thiếu B, không tự suy ra sai tiêu chí dataset hoặc lỗi segmentation. | missing_region; hair=0 | hf_hf01044_01044.jpg | Trống | Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ |
| hf_merged_00694.png | UNVERIFIED về che khuất/chất lượng ROI | Khăn và kính nhìn thấy; không tự coi mọi phụ kiện là vi phạm. Hair=355 hợp lệ về ngưỡng, chưa chắc đại diện tóc. Cần đánh giá riêng mức che mắt/mũi/miệng. | valid; hair=355 | parquet_stream_1530 | Trống | Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ |

Ảnh HF00333/HF00561/HF00722 **có B hợp lệ nhưng sai tiêu chí ảnh**; HF00209 **thiếu B nhưng chưa chứng minh sai tiêu chí chỉ từ thiếu tóc**. HF00694 có B hợp lệ theo ngưỡng 100 pixel nhưng độ đại diện tóc và che khuất mắt bởi kính còn cần review. Không gộp ba tình huống này thành một nhãn “ảnh lỗi”. Không suy ra hair=0 là mô hình sai khi không có ground truth.

Chứng cứ trước đây vẫn được giữ nguyên: [contact sheet 1](evidence/dataset_mask_review_page1.png), [contact sheet 2](evidence/dataset_mask_review_page2.png). Nguồn/hash hiện tại và đối chiếu provenance lưu ở [dataset_source_review.json](pre_c_evidence/dataset_source_review.json).

## Có thể lấy ảnh thay thế hợp lệ từ nguồn không?

Đã đọc `metadata.csv` và `hf_provenance.csv`, đối chiếu năm SHA/tên và rà tên ảnh gốc/các alias trong repository, dataset hiện hành và các thư mục nguồn có tên liên quan được xác định trong phạm vi tìm kiếm. Thư mục thực sự có thể đọc: `D:\TuNam4\dataset_HF_CFD_final`, `D:\TuNam4\portrait-retrieval`. Không tìm được file gốc/alias đủ để xác nhận một ảnh thay thế. **Không có ứng viên thay thế nào đã được chứng minh hợp lệ.** Kết luận này không có nghĩa nguồn ngoài máy không tồn tại.

- HF00333/HF00561/HF00694 có token `parquet_stream_3176/3481/1530`: thiếu Hugging Face repository/dataset ID, revision, split, shard và checksum để định vị lại bản ghi.
- HF00722 có `Female (10).parquet_row_5`: chưa thấy file parquet được chỉ ra; không biết revision/split hay quy ước đánh số row 0/1. Không suy ra person_id từ nhãn file.
- HF00209 có `hf_hf01044_01044.jpg`: có tên gốc nhưng chưa xác nhận đường dẫn hoặc checksum ảnh gốc.
- Alias `final_01094.png`, `final_01322.png`, `final_00768.png`, `final_00970.png`, `final_01455.png` thuộc collection lịch sử; cũng chưa tìm thấy trong phạm vi rà soát.
- Cả năm source_person_id đều trống. Ngay cả tìm được ảnh raw cũng chưa chứng minh có ảnh khác cùng người và đạt tiêu chí; không dùng nhận diện ngoại hình để tự bổ sung.

Chi tiết đường dẫn/tên đã thử và kết quả tìm kiếm có trong JSON. Không suy đoán repository nguồn từ token chung hoặc tải/thay ảnh để đủ số lượng.

## Phương án dataset phiên bản mới — chỉ thiết kế

1. Giữ dataset 1438 ảnh, masks, catalog v1/v2 bất biến; lưu membership và cờ review trong manifest phiên bản mới, tách vi phạm ảnh, thiếu feature và UNVERIFIED.
2. Khi có nguồn có thẩm quyền, thu thập locator/revision/checksum/source ID; xác minh identity bằng metadata nguồn nếu cần bảo toàn số người, không đoán bằng ảnh.
3. Review ảnh ứng viên theo cùng tiêu chí: một mặt, không mặt phụ, chính diện, không che mắt/mũi/miệng, kích thước và alignment. Quyết định của người review và ground truth tách khỏi dự đoán của mô hình.
4. Ảnh mới phải có image_id mới gắn với nội dung bất biến, quan hệ `replaces_image_id`, lý do, người review, bằng chứng và dataset_version. Không gán vector/mask cũ của ảnh khác cho ảnh mới; không xóa file cũ.
5. Tính lại số ảnh, số người và ảnh lặp cảm xúc từ nhãn có chứng cứ; không ép số liệu về 1438/1135/303 hoặc ép IPD cho khớp PDF. Nếu catalog thay đổi, các stats/features/calibration/query sau này phải có version mới; không ghi đè v2 đã đóng băng.

Chưa thực hiện các bước tạo/thay ảnh hoặc subset mới trong nhiệm vụ này. Những ảnh bị đánh dấu vẫn có mặt trong input hiện hành.

## Số liệu/điều khoản PDF còn thiếu dữ liệu gốc

| Nội dung PDF | Điều chứng minh được | Điều còn thiếu |
|---|---|---|
| 1438 ảnh, 256×256, PNG RGB | Audit kỹ thuật toàn kho trước đã đạt; hash corpus không đổi | “PNG chất lượng 95”, cùng encoder/mức nén cần log gốc. |
| 1135 người, 303 ảnh cảm xúc lặp | 710 CFD rows có 407 source-scoped IDs và 303 extra rows; 728 HF thiếu person_id | HF có khác nhau/trùng CFD không; nhãn cảm xúc có thẩm quyền. Không suy ra 1135 từ 407+728. |
| Tuổi 18–60, nhãn nữ và tính đa dạng | Catalog ghi nguồn CFD/HF | Chưa đủ tuổi/giới/nhãn phân bố và provenance để kiểm tra; không suy đoán từ mặt. |
| Một mặt, không mặt phụ, không che | Ba ảnh nêu trên có vi phạm quan sát trực tiếp | Review đầy đủ corpus; detector trả một mặt không chứng minh không có mặt phụ. |
| Yaw/pitch <5°, alignment | Có landmark/model proxies được lưu từ audit | Ground truth, quy trình camera/dung sai và source tiền xử lý. |
| IPD median 29.45%, min/max 27.23–32.61%; eye y=40% | Audit centroid/iris cho các số khác nhau | Định nghĩa tâm mắt và phép đo gốc; không rescale để ép thống kê. |
| Face height 70–90%, median 78.6% | Mesh-height proxy ≈78.564% | Định nghĩa bbox/đỉnh đầu–cằm thống nhất; proxy không phải ground truth. |
| Bicubic/crop và metadata/CSDL | Có output ảnh, catalog và feature files | Log/source tiền xử lý, lưu tọa độ mắt và tầng CSDL ứng dụng chưa có bằng chứng triển khai. |

Xem [DATABASE_COMPLIANCE_REVIEW.md](DATABASE_COMPLIANCE_REVIEW.md). Dataset **chưa đạt toàn bộ điều kiện PDF**; không có thay đổi số đo, nhãn hoặc dữ liệu nguồn trong lần review.
