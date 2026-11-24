# Shared

`paths.py` xác định root, dataset và model bằng pathlib. `detect_landmarks.py` là công cụ chẩn đoán/vẽ 478 landmarks đã có, dùng tham khảo cho A/B. Trước đây đây là script độc lập, không phải hàm A/B cùng import. Không hợp nhất các detector hiện tại để tránh đổi hành vi.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -m shared.detect_landmarks
```

Ảnh ở `outputs/A_geometry/landmarks_478/`. `mask_labels.py` giữ trong B vì chứa protocol nhãn da/tóc.
