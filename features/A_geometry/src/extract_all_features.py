
from pathlib import Path
from shared.paths import PROJECT_ROOT
import csv
import cv2
import mediapipe as mp
import numpy as np

from features.A_geometry.src.geometry_features import (
    DATASET_DIR,
    MODEL_PATH,
    OUTPUT_DIR,
    INDICES,
    normalize_landmarks,
    calculate_ratios
)

# Các định dạng ảnh được hỗ trợ
EXTENSIONS = {".png", ".jpg", ".jpeg"}

# ==============================
# 1. CHUẨN BỊ DANH SÁCH ẢNH
# ==============================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_paths = sorted([
        p for p in DATASET_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONS
    ])

    print("Tổng số ảnh:", len(image_paths))

    if not image_paths:
        raise RuntimeError("Không tìm thấy ảnh trong dataset")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)

    # ==============================
    # 2. KHỞI TẠO MEDIAPIPE
    # ==============================

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1
    )

    features_list = []
    metadata = []
    failed_images = []

    # ==============================
    # 3. TRÍCH XUẤT HÀNG LOẠT
    # ==============================

    with mp.tasks.vision.FaceLandmarker.create_from_options(
        options
    ) as detector:

        for i, image_path in enumerate(image_paths, start=1):

            try:
                image = cv2.imread(str(image_path))

                if image is None:
                    raise ValueError("Không đọc được ảnh")

                h, w = image.shape[:2]

                if (h, w) != (256, 256):
                    raise ValueError(
                        f"Kích thước không hợp lệ: {w}x{h}"
                    )

                rgb = cv2.cvtColor(
                    image, cv2.COLOR_BGR2RGB
                )

                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(rgb)
                )

                result = detector.detect(mp_image)

                if len(result.face_landmarks) != 1:
                    raise ValueError(
                        "Không phát hiện đúng 1 khuôn mặt"
                    )

                points_478 = np.array([
                    [lm.x * w, lm.y * h]
                    for lm in result.face_landmarks[0]
                ], dtype=np.float32)

                points_68 = points_478[INDICES]

                normalized, eye_distance = (
                    normalize_landmarks(points_68)
                )

                A1 = normalized.flatten().astype(np.float32)
                A2 = calculate_ratios(points_68)

                feature_vector = np.concatenate([A1, A2])

                if feature_vector.shape != (150,):
                    raise ValueError("Vector không đủ 150 chiều")

                if not np.all(np.isfinite(feature_vector)):
                    raise ValueError("Vector chứa NaN hoặc Inf")

                features_list.append(feature_vector)

                metadata.append({
                    "image_name": image_path.name,
                    "image_path": str(image_path),
                    "eye_distance": float(eye_distance)
                })

                status = "OK"

            except Exception as e:
                failed_images.append({
                    "image_name": image_path.name,
                    "reason": str(e)
                })

                status = f"FAILED: {e}"

            print(
                f"[{i}/{len(image_paths)}] "
                f"{image_path.name}: {status}",
                flush=True
            )

    # ==============================
    # 4. LƯU MA TRẬN ĐẶC TRƯNG
    # ==============================

    if not features_list:
        raise RuntimeError(
            "Không trích xuất được đặc trưng của ảnh nào"
        )

    X = np.stack(features_list).astype(np.float32)

    assert X.shape[1] == 150
    assert X.shape[0] == len(metadata)

    np.save(
        OUTPUT_DIR / "features_A_raw.npy",
        X
    )

    # Lưu metadata
    with open(
        OUTPUT_DIR / "metadata.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_name",
                "image_path",
                "eye_distance"
            ]
        )

        writer.writeheader()
        writer.writerows(metadata)

    # Lưu ảnh lỗi
    with open(
        OUTPUT_DIR / "failed_images.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=["image_name", "reason"]
        )

        writer.writeheader()
        writer.writerows(failed_images)

    # ==============================
    # 5. THỐNG KÊ
    # ==============================

    print("\n===== TỔNG KẾT =====")
    print("Tổng số ảnh:", len(image_paths))
    print("Thành công:", len(features_list))
    print("Thất bại:", len(failed_images))
    print("Ma trận đặc trưng:", X.shape)

    print(
        "Đã lưu:",
        OUTPUT_DIR / "features_A_raw.npy"
    )


if __name__ == "__main__":
    main()
