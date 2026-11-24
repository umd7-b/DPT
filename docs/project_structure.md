# Cấu trúc dự án

```text
features/
  A_geometry/src/    geometry_features, extract_all_features, normalize_features, map_68_landmarks
  B_color/src/       refine_hair_mask, mask_labels, annotate_masks, evaluate_masks,
                     prepare_mask_validation, hair_color_core, check_existing_masks, visualize_color_regions
  C1_lbp/src/        placeholder
  C2_hog/src/        placeholder
shared/              paths, detect_landmarks
retrieval/           search_geometry
models/              face_landmarker.task
annotations/manual_masks/   nhãn người dùng, giữ nguyên
outputs/
  A_geometry/        features, landmarks_68, landmarks_478
  B_color/           hair_masks, hair_evaluation, color_regions, mask_check, mask_validation
  C1_lbp/            dành cho tương lai
  C2_hog/            dành cho tương lai
  retrieval/         search_results, refactor_validation
  evaluation/        dành cho đánh giá liên bộ tương lai
  mask_validation/   ngoại lệ: bốn log editor cũ đang khóa
src/                 wrapper tương thích
scripts/             rollback_refactor
 tests/              tests hiện có với import mới
 docs/               mapping, inventory, báo cáo
.refactor_backup/    snapshot và bằng chứng hồi quy, không commit
```

Báo cáo QA mask chỉ phục vụ B vẫn ở `outputs/B_color/mask_validation/`. Metadata A ở cạnh ma trận; metadata nguồn vẫn trong dataset ngoài repository. Không sửa chuỗi đường dẫn provenance trong CSV/JSON lịch sử, vì đó là nội dung cần bảo toàn; code thực thi dùng đường dẫn mới. Xem `refactor_mapping.csv` cho từng file và `refactor_inventory.json` cho shape/dtype/header/chức năng.

Script có thân tính toán top-level nay được bọc main guard để import không chạy batch. Thứ tự/công thức tính toán giữ nguyên. Lệnh -m chạy từ root; wrapper gọi bằng đường dẫn tuyệt đối cũng xác định đúng root.
