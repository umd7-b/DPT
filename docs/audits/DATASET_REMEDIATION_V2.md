# Dataset — hồ sơ xử lý phiên bản2, chưa thay dữ liệu

Ngày23/11/2026. Giữ nguyên toàn bộ1438 ảnh nguồn, metadata và masks; không xóa/crop/inpaint/tạo ảnh thay thế, không đổi mask để cải thiện retrieval. V2 chỉ tạo vector/stats/calibration/query artifacts mới, không giải quyết một vi phạm ảnh bằng thay đổi công thức.

## Các trường hợp giữ riêng

| Ảnh | Trạng thái | Bằng chứng/quan sát | SHA-256 nguồn bất biến | Ảnh review đã có |
| --- | --- | --- | --- | --- |
| hf_merged_00333.png | DEVIATION | Mặt phụ nhìn thấy ở mép trái/phải, vi phạm §1.2 không có mặt phụ. | f7e88d359d841dfa276944744de9fe582ea75e5423383a5ec5ad49b5c807f9e4 | evidence/dataset_mask_review_page1.png |
| hf_merged_00561.png | DEVIATION | Một phần mặt phụ/eye ở mép trái, vi phạm §1.2. | 8669de66506c72dffde7964fbcc9f0e32d2f3a80142ed55fcabf2f19a5640c8c | evidence/dataset_mask_review_page1.png |
| hf_merged_00722.png | DEVIATION | Ngón tay chồng vùng miệng/mặt dưới, vi phạm yêu cầu không che mắt/mũi/miệng. | e48690069c446a54b27a7b78fa48f11dbee55a4e8788f0df73e381d1d3bd67c2 | evidence/dataset_mask_review_page2.png |
| hf_merged_00209.png | MISSING B; không zero-fill | Hair raw0 pixel, B144 không tồn tại; A vẫn có đủ150 chiều. | 493b24ba810c3f9f4d1a1e26226e3390ba50204da68bd2c63ea9df5f287cec06 | evidence/dataset_mask_review_page2.png |
| hf_merged_00694.png | UNVERIFIED | Khăn che tóc, hair mask355 pixel; chưa chứng minh đại diện màu tóc. | 37fe418c43eaa71551d91a2e3564b409db34ffa2c73b6cf1dea5e013cc49248c | evidence/dataset_mask_review_page2.png |
| hf_merged_00610.png | UNVERIFIED | Mũ/phụ kiện và cờ face-count lịch sử; model mới báo1 chưa phải GT. | 58dfb10857118233d04e41e5aa8700eac4bcba428ae39008ec06dd2d8be8b1fd | evidence/dataset_mask_review_page1.png |

HF00333/HF00561/HF00722 vẫn có mặt trong A v2 và tập B hợp lệ v2. HF00209 vẫn có A; manifest B đủ1438 danh tính, ma trận compact chỉ1437 vector hợp lệ; missing row không có feature_row_index. Không biến cảnh báo/phụ kiện thành quy tắc tự loại ảnh hoặc sửa nhãn. Khăn trùm tóc không tự động vi phạm điều khoản mắt/mũi/miệng không bị che; chất lượng vùng tóc vẫn cần kiểm chứng.

## Chứng cứ cần có để giải quyết các tiêu chí PDF

| Tiêu chí PDF | Chứng cứ hiện có | Thiếu gì để kết luận | Cách giải quyết được đề xuất, chưa thực hiện |
|---|---|---|---|
|1438 ảnh,RGB8 PNG256×256|Audit đọc IHDR/hash toàn kho đạt|Lịch sử encoder “PNG95”/cùng mức nén chưa đủ|Bổ sung log/source encode; không thay ảnh hiện hành hoặc đổi sang JPEG.|
|1135 người,303 ảnh cảm xúc cùng người|CFD710 dòng có407 person_ids và303 dòng lặp thêm;HF728 thiếu person_id|HF có trùng nhau/CFD không, nhãn cảm xúc và provenance identity|Catalog person/expression có thẩm quyền, liên kết nguồn rõ; không suy đoán danh tính từ ảnh hoặc dùng hash byte làm ID người.|
|Một mặt,không có mặt phụ|Detector num_faces5 vẫn báo1 trên mọi ảnh; đã nhìn thấy mặt phụ HF00333/HF00561|Annotation/review đầy đủ; độ bao phủ detector tại mép|Gắn cờ trong hồ sơ riêng, duyệt theo protocol; nếu cần corpus tuân thủ mới thì xin tác vụ riêng và version/provenance riêng, giữ nguyên corpus cũ.|
|Không che mắt/mũi/miệng|HF00722 tay che miệng; raw skin có thể nhận da tay|Vùng occlusion/review độc lập toàn kho|Không inpaint/crop/đổi mask trong v2; thu thập bằng chứng/source phù hợp nếu sau này được giao sửa dataset.|
|Chính diện,yaw/pitch<5°|Pose model chưa hiệu chuẩn; roll có đo|GT/protocol camera/pose định nghĩa rõ|Hiệu chuẩn và annotation hoặc nguồn góc có thẩm quyền; không coi output model là GT.|
|IPD29.45%,min27.23,max32.61;tâm mắt40%|Audit centroid/iris khác số PDF; tâm mắt y có phân bố|Định nghĩa tâm mắt, sai số cho phép, log affine alignment|Truy lại pipeline đầu vào và phép đo chuẩn; không rescale ảnh để ép median.|
|Mặt70–90%,median78.6%,căn giữa|Mesh-height proxy median78.564%|Định nghĩa bbox/đỉnh đầu-cằm/tolerance|Đo theo định nghĩa chốt trước; không coi mesh bbox là ground truth face box.|
|Bicubic/crop vuông đỉnh đầu→cằm|Ảnh cuối cùng và code visualize|Source/log tiền xử lý gốc|Lưu provenance resize/affine/crop; phóng ảnh minh họa bằng bicubic không chứng minh preprocessing.|
|Metadata/CSDL gồmID/path/vị trí hai mắt|CSV ID/path/hash, không đủ eye x/y/DB hiện thực|SchemaDB/log lưu tọa độ/quy trình ingestion|Bổ sung bằng chứng/thiết kế trong tác vụ dữ liệu riêng; không tự dựng DB hoặc thay catalog nguồn.|
|Nhãn nữ,18–60/đa dạng|Metadata hiện thiếu tuổi/nhãn đủ|Nhãn nguồn và quyền/thẩm quyền của annotation|Không suy đoán tuổi/giới/sắc tộc từ ngoại hình; cần nhãn/provenance hợp lệ.|

Liên kết hồ sơ chi tiết: [audit dataset](DATASET_REPORT_COMPLIANCE.md), [số đo toàn kho](evidence/dataset_measurements.csv), [cờ model](evidence/dataset_model_review_candidates.csv), [quan sát thủ công](evidence/visual_review_findings.csv). Các cờ là bằng chứng screening, không phải nhãn GT hoặc accuracy. Không tạo segmentation/retrieval GT từ chính dự đoán.

## Phạm vi nghiệm thu v2

A12/B12 có thể được sửa và kiểm chứng số học trong khi dataset vẫn còn DEVIATION DS05/DS10. Hai kết luận này được giữ riêng. Không tuyên bố toàn hệ thống100% tuân thủ hoặc A/B đã chứng minh chất lượng nhận diện vì có vector/Top-5 hợp lệ. **Không triển khai C1/C2, không thay PDF.**
