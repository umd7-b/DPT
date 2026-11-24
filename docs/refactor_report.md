# Báo cáo refactor Portrait Retrieval

Ngày 22/11/2026. Snapshot: `.refactor_backup/20261122_155715/snapshot.zip`. Git có sẵn, HEAD `78a9d30`; có thay đổi chưa commit từ công việc gán nhãn. Đã lưu toàn bộ trong snapshot, không reset/stash/commit.

## Trước và sau

Trước: 14 file Python ngang hàng trong src, outputs trộn A/B/retrieval. Sau: package theo bộ đặc trưng, shared và retrieval; xem project_structure.md. C1/C2 chỉ tạo README/package marker. Model, annotations và dataset giữ nguyên vị trí, requirements giữ nguyên nội dung.

## Mapping và backup

`refactor_mapping.csv` liệt kê đường dẫn cũ → mới → chức năng của 475 file snapshot. `refactor_inventory.json` bổ sung hành động và định dạng npy/npz/csv/ảnh. Backup tạo trước mọi di chuyển; có manifest SHA-256, git_status.txt và git_diff.patch. Không đổi tên/định dạng dữ liệu, không xóa kết quả cũ.

Bốn log editor đang mở bị Windows khóa nên chỉ sao chép và giữ bản cũ tại outputs/mask_validation. Không ép đóng cửa sổ để tránh mất thao tác chưa lưu. Các output còn lại đã chuyển. Dataset ngoài repository không bị di chuyển hoặc chỉnh sửa.

## Import và đường dẫn

Implementation dùng import package tuyệt đối và shared.paths.PROJECT_ROOT. Dataset vẫn D:\TuNam4\dataset_HF_CFD_final. Hằng output/model dựa trên root; 14 wrapper src hỗ trợ CLI và import cũ. Tests cập nhật import. Thân script top-level được bọc main() để import không chạy batch; thứ tự/công thức giữ nguyên.

Không hợp nhất detector hoặc chuyển chuẩn hóa A thành module tổng quát. Không sửa chuỗi provenance trong CSV/JSON hoặc tài liệu lịch sử trong outputs; các artifact này giữ checksum. Hướng dẫn hiện hành nằm tại các README mới. Đường dẫn cũ trong code thực thi đã được rà soát; wrapper cũ vẫn dùng được.

## Kết quả kiểm chứng

- 447 artifact gốc thuộc outputs/annotations/models giữ nguyên SHA-256, không mismatch.
- 42 module package/implementation/wrapper/script import thành công.
- 21/21 unit tests hiện có đạt; log tại refactor_tests.log.
- Hai ma trận A vẫn (1438,150), float32; hai vector A riêng (150,); mean/std (150,). Các file dữ liệu giữ nguyên byte.
- AST toàn bộ hàm geometry_features và hàm segment_hair giống trước refactor.
- Truy vấn cfd_final_00144.png: vector A, query chuẩn hóa, toàn bộ 1438 khoảng cách và top_indices bằng chính xác bản trước refactor.
- Top-5: cfd_final_00325, hf_merged_00429, cfd_final_00352, cfd_final_00510, cfd_final_00340; khoảng cách tương ứng 6.324556196924805, 6.436707653655997, 6.623884901655206, 6.795211785284631, 6.798523737887016. Chi tiết: refactor_regression_results.json.
- Mask tóc 00001/00069/00088 có SHA-256 bằng baseline chạy trước refactor; số pixel 13148/4749/18814. Output thử mới tại outputs/B_color/refactor_validation.
- Truy vấn thử dùng main() mới, chỉ chuyển OUTPUT_DIR sang outputs/retrieval/refactor_validation để tránh ghi đè ảnh cũ; đã kiểm tra đường dẫn mặc định là outputs/retrieval/search_results.
- Đánh giá nhãn ba ảnh cho TP/FP/FN và IoU/Dice/precision/recall bằng chính xác báo cáo trước; output thử trong refactor_validation/label_evaluation.
- Đã kiểm tra root/model/output khi cwd là thư mục tạm; wrapper CLI cũ --help chạy thành công.
- Không tái trích cả dataset hoặc chạy lại chuẩn hóa vào file cũ để tránh ghi đè; không tuyên bố đã chạy batch này. Không chạy hair --all, không cài dependencies hoặc tải model.

## Tồn tại

Giới hạn chất lượng segmentation và mask da template giữ nguyên. Requirements.txt vốn trống, không tự thêm dependency. C1/C2 chưa triển khai. Bốn log khóa giữ tại đường dẫn cũ; đóng/mở lại editor trước khi gán nhãn tiếp để nhận code mới. Bản backup chứa cả thay đổi chưa commit, không thay thế bằng git reset --hard.

## Rollback

```powershell
# Dry-run trước, kiểm tra xung đột:
.\.venv311\Scripts\python.exe -X utf8 -m scripts.rollback_refactor
# Chỉ khi muốn phục hồi đường dẫn và byte trước refactor:
.\.venv311\Scripts\python.exe -X utf8 -m scripts.rollback_refactor --restore
```

Rollback phục hồi snapshot về đường dẫn gốc, không xóa cây mới/kết quả mới. Từ chối ghi đè file đã thay đổi sau refactor, đặc biệt nhãn vừa chỉnh. Nếu cần cây cũ tuyệt đối, sau khôi phục hãy rà soát thủ công các thư mục mới; script không xóa dữ liệu người dùng. Đã kiểm tra dry-run; chưa chạy restore trên workspace thật.

Lệnh chạy A/B/Top-5 ở README gốc và README từng nhóm. Thay đổi Git chưa được commit để người dùng review. Chi tiết kiểm tra cuối ở refactor_final_checks.json.
