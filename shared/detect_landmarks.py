
from pathlib import Path
from shared.paths import PROJECT_ROOT
import cv2
import mediapipe as mp
import numpy as np

# Đường dẫn dataset
DATASET_DIR = Path(
    r"D:\TuNam4\dataset_HF_CFD_final\images"
)

# Đường dẫn model
MODEL_PATH = (PROJECT_ROOT / "models/face_landmarker.task")

# Thư mục kết quả
OUTPUT_DIR = (PROJECT_ROOT / "outputs/A_geometry/landmarks_478")

# Ảnh thử nghiệm
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = DATASET_DIR / "cfd_final_00069.png"

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Chưa có model: {MODEL_PATH}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(f"Không đọc được ảnh: {image_path}")

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(rgb)
    )

    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1
    )

    with mp.tasks.vision.FaceLandmarker.create_from_options(
        options
    ) as detector:
        result = detector.detect(mp_image)

    if len(result.face_landmarks) != 1:
        raise RuntimeError("Không phát hiện được khuôn mặt")

    landmarks = result.face_landmarks[0]
    h, w = image.shape[:2]

    points = np.array([
        [lm.x * w, lm.y * h]
        for lm in landmarks
    ], dtype=np.float32)

    print("Số landmarks:", len(points))
    print("Kích thước vector:", points.shape)
    print("5 điểm đầu tiên:")
    print(points[:5])

    # Vẽ landmarks
    visualization = image.copy()

    for x, y in points:
        cv2.circle(
            visualization,
            (int(round(x)), int(round(y))),
            1,
            (0, 255, 0),
            -1
        )

    output_path = OUTPUT_DIR / "cfd_final_00069_478.png"

    cv2.imwrite(str(output_path), visualization)

    print("Đã lưu kết quả:", output_path)


if __name__ == "__main__":
    main()
