# Bộ A — Geometry

Giữ nguyên 150 chiều: A1 gồm 136 tọa độ chuẩn hóa, A2 gồm 14 tỉ lệ/góc. Không đổi ánh xạ 68 điểm, tính toán hoặc kiểu dữ liệu. `extract_all_features` chỉ trích A; `normalize_features` chỉ chuẩn hóa A, chưa phải tiện ích tổng quát.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -m features.A_geometry.src.geometry_features
.\.venv311\Scripts\python.exe -X utf8 -m features.A_geometry.src.map_68_landmarks
# Hai lệnh sau ghi lại toàn bộ ma trận/thống kê A; chỉ chạy khi muốn tái tạo:
.\.venv311\Scripts\python.exe -X utf8 -m features.A_geometry.src.extract_all_features
.\.venv311\Scripts\python.exe -X utf8 -m features.A_geometry.src.normalize_features
```

Vector, ma trận, metadata và lỗi ở `outputs/A_geometry/features/`. Metadata này ánh xạ hàng ma trận A, khác metadata nguồn dataset. Ảnh landmarks ở `outputs/A_geometry/landmarks_68/` và `landmarks_478/`. Tên và nội dung file giữ nguyên.
