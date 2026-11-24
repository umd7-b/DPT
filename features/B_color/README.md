# Bộ B — Color và kiểm chứng mask

Chứa pipeline segmentation, kiểm chứng mask và trích đặc trưng B144 đã thử trên 100 ảnh; chưa trích vector toàn kho 1.438 ảnh. Output B ở `outputs/B_color/`: `hair_masks`, `hair_evaluation`, `color_regions`, `mask_check`, `mask_validation`. Nhãn thủ công giữ ở `annotations/manual_masks/`, độc lập với prediction.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.refine_hair_mask --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.prepare_mask_validation
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.annotate_masks --annotator "USER"
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.evaluate_masks
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.hair_color_core --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.check_existing_masks
.\.venv311\Scripts\python.exe -X utf8 -m features.B_color.src.visualize_color_regions
```

Giữ nguyên phím, thuật toán và xác nhận nhãn. Quy ước vẽ ở `outputs/B_color/mask_validation/README.txt` là tài liệu lịch sử; dùng lệnh mới ở trên hoặc wrapper `src/...` cũ. Đường dẫn output trong tài liệu lịch sử cần đối chiếu mapping. Chạy lại chuẩn bị panel/đánh giá sẽ cập nhật báo cáo như trước.

Đóng/mở lại editor đang chạy để nạp code mới. Bốn log cửa sổ cũ vẫn ở `outputs/mask_validation/` vì Windows khóa; bản sao đã có trong cây B. Không xóa nhãn hoặc đổi pixel. Chưa chạy `--all`.

## UniFace batch và full dataset

Pipeline dùng chung: `features/B_color/src/batch_uniface.py`; giữ nhãn skin=1, hair=17 và erosion 3x3 một lần. Không trích vector B ở bước này.

```powershell
# Toàn bộ CFD/HF vào outputs/B_color/uniface_full (chỉ chạy mới khi thư mục rỗng):
.\.venv-uniface\Scripts\python.exe -X utf8 -m features.B_color.src.batch_uniface --all
# Xác minh/bỏ qua mask đã hoàn tất, chỉ thử lại ảnh lỗi hoặc thiếu receipt:
.\.venv-uniface\Scripts\python.exe -X utf8 -m features.B_color.src.batch_uniface --all --retry-failed
```

Mẫu 100 ảnh vẫn là mặc định khi không có `--all`. Dữ liệu batch100 không được ghi đè. Xem `outputs/B_color/uniface_full/USAGE.txt` về receipt, điều kiện retry và giới hạn heuristic; xem `REPORT.txt` và `summary.json` trong cùng thư mục cho kết quả. Receipt chỉ xác nhận định dạng/hash, không chứng nhận mask là nhãn chuẩn hoặc clean tốt hơn raw.

## Trích đặc trưng màu B144 — thử 100 ảnh

Định nghĩa từ `csdldpt.pdf`: mỗi vùng 48 HS + 12 mô-men Lab + 12 Hue vòng; da/tóc tổng 144 chiều. Xem `docs/B_color_feature_spec.md` về công thức, thứ tự block và các quy ước số học còn cần nhóm xác nhận.

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -m features.B_color.src.run_color_experiment --report C:/Users/USER/Downloads/csdldpt.pdf --include-nose-experiment --normalization all144 --output outputs/B_color/color_features_100_rerun
.\.venv-uniface\Scripts\python.exe -X utf8 -m features.B_color.src.search_color --trial outputs/B_color/color_features_100_rerun
.\.venv-uniface\Scripts\python.exe -X utf8 -m unittest discover -s tests -p "test_color*.py" -v
```

Thư mục trial phải mới/rỗng. Raw, clean và skin1+10 là ba phương án riêng trong cùng Bộ B; không phải Bộ A/C1/C2. Không zero-fill vùng thiếu; không trích vector toàn dataset trong CLI thử này. Nhãn lớp 10 của thí nghiệm C đến từ inference thật, không sửa mask full. Kết quả và giới hạn ở `outputs/B_color/color_features_100/REPORT.txt`.
