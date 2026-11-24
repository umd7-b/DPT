
from pathlib import Path
from shared.paths import PROJECT_ROOT
import cv2
import numpy as np
import mediapipe as mp

from features.A_geometry.src.geometry_features import DATASET_DIR, MODEL_PATH

IMAGE_NAME = "cfd_final_00088.png"
OUTPUT_DIR = (PROJECT_ROOT / "outputs/B_color/color_regions")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = DATASET_DIR / IMAGE_NAME
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(image_path)

    h, w = image.shape[:2]

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1
    )

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(rgb)
    )

    with mp.tasks.vision.FaceLandmarker.create_from_options(
        options
    ) as detector:
        result = detector.detect(mp_image)

    if not result.face_landmarks:
        raise RuntimeError("Không phát hiện khuôn mặt")

    points = np.array([
        [lm.x * w, lm.y * h]
        for lm in result.face_landmarks[0]
    ], dtype=np.float32)

    # Đường viền mặt MediaPipe
    FACE_OVAL = [
        10, 338, 297, 332, 284, 251, 389, 356,
        454, 323, 361, 288, 397, 365, 379,
        378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234,
        127, 162, 21, 54, 103, 67, 109
    ]

    # ==============================
    # 1. TẠO MASK DA SƠ BỘ
    # ==============================

    face_mask = np.zeros((h, w), dtype=np.uint8)

    polygon = np.round(
        points[FACE_OVAL]
    ).astype(np.int32)

    cv2.fillPoly(face_mask, [polygon], 255)

    # Thu nhỏ vùng để tránh viền mặt và tóc
    kernel = np.ones((11, 11), np.uint8)
    skin_mask = cv2.erode(face_mask, kernel)

    # ==============================
    # 2. TẠO MASK TÓC SƠ BỘ
    # ==============================

    # Giới hạn vùng phía trên và quanh đầu
    x_left = max(0, int(points[234, 0]) - 25)
    x_right = min(w, int(points[454, 0]) + 25)
    y_bottom = min(h, int(points[152, 1]))

    candidate = np.zeros((h, w), dtype=np.uint8)
    candidate[:y_bottom, x_left:x_right] = 255

    # Loại vùng mặt
    candidate[face_mask > 0] = 0

    # Loại các điểm gần màu nền ở góc ảnh
    corners = np.array([
        image[0, 0],
        image[0, w - 1],
        image[h - 1, 0],
        image[h - 1, w - 1]
    ], dtype=np.float32)

    background = np.median(corners, axis=0)

    difference = np.linalg.norm(
        image.astype(np.float32) - background,
        axis=2
    )

    # Đây chỉ là ngưỡng thử nghiệm

    corners = np.array([
        image[0, 0],
        image[0, w - 1],
        image[h - 1, 0],
        image[h - 1, w - 1]
    ], dtype=np.float32)

    background = np.median(corners, axis=0)

    difference = np.linalg.norm(
        image.astype(np.float32) - background,
        axis=2
    )

    # Loại các pixel giống nền
    hair_mask = np.where(
        (candidate > 0) & (difference > 35),
        255,
        0
    ).astype(np.uint8)

    # Làm sạch nhiễu nhỏ
    kernel = np.ones((3, 3), np.uint8)

    hair_mask = cv2.morphologyEx(
        hair_mask,
        cv2.MORPH_OPEN,
        kernel
    )
    # ==============================
    # 3. HIỂN THỊ KẾT QUẢ
    # ==============================

    skin_image = cv2.bitwise_and(
        image, image, mask=skin_mask
    )

    hair_image = cv2.bitwise_and(
        image, image, mask=hair_mask
    )

    preview = np.hstack([
        image,
        skin_image,
        hair_image
    ])

    cv2.putText(
        preview, "ORIGINAL", (55, 245),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (0, 255, 0), 2
    )

    cv2.putText(
        preview, "SKIN", (256 + 85, 245),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (0, 255, 0), 2
    )

    cv2.putText(
        preview, "HAIR", (512 + 85, 245),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (0, 255, 0), 2
    )

    output_path = OUTPUT_DIR / (
        Path(IMAGE_NAME).stem + "_regions.png"
    )

    cv2.imwrite(str(output_path), preview)

    print("Ảnh:", IMAGE_NAME)
    print("Số pixel da:", np.count_nonzero(skin_mask))
    print("Số pixel tóc:", np.count_nonzero(hair_mask))
    print("Đã lưu:", output_path)


if __name__ == "__main__":
    main()
