
from pathlib import Path
from shared.paths import PROJECT_ROOT
import cv2
import mediapipe as mp
import numpy as np

DATASET_DIR = Path(
    r"D:\TuNam4\dataset_HF_CFD_final\images"
)
MODEL_PATH = (PROJECT_ROOT / "models/face_landmarker.task")
OUTPUT_DIR = (PROJECT_ROOT / "outputs/A_geometry/landmarks_68")

# Ánh xạ thử nghiệm: 68 điểm từ MediaPipe
# Thứ tự: hàm, lông mày, mũi, mắt, miệng

JAW = [
    234, 93, 132, 58, 172, 136, 150, 149,
    152, 378, 379, 365, 397, 288, 361, 323, 454
]

LEFT_EYEBROW = [70, 63, 105, 66, 107]
RIGHT_EYEBROW = [336, 296, 334, 293, 300]

NOSE = [
    # Sống mũi: 27–30
    168, 6, 197, 1,

    # Đáy mũi: 31–35
    129, 48, 4, 278, 358
]

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

MOUTH = [
    # Viền môi ngoài: 48–59
    61, 40, 37, 0, 267, 270,
    291, 321, 314, 17, 84, 91,

    # Viền môi trong: 60–67
    78, 81, 13, 311,
    308, 402, 14, 178
]

LANDMARK_INDICES = (
    JAW + LEFT_EYEBROW + RIGHT_EYEBROW +
    NOSE + LEFT_EYE + RIGHT_EYE + MOUTH
)

assert len(LANDMARK_INDICES) == 68

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = DATASET_DIR / "cfd_final_00069.png"
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(image_path)

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

    if not result.face_landmarks:
        raise RuntimeError("Không phát hiện khuôn mặt")

    h, w = image.shape[:2]

    points_478 = np.array([
        [lm.x * w, lm.y * h]
        for lm in result.face_landmarks[0]
    ], dtype=np.float32)

    points_68 = points_478[LANDMARK_INDICES]

    print("Kích thước 478:", points_478.shape)
    print("Kích thước 68:", points_68.shape)

    # Vẽ 68 landmarks và đánh số
    # Vẽ 68 landmarks và đánh số
    # Phóng to ảnh 3 lần để dễ quan sát
    scale = 3

    visualization = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    for i, (x, y) in enumerate(points_68):
        px = int(round(x * scale))
        py = int(round(y * scale))

        # Vẽ điểm landmark
        cv2.circle(
            visualization,
            (px, py),
            4,
            (0, 0, 255),
            -1
        )

        # Hiển thị số thứ tự
        cv2.putText(
            visualization,
            str(i),
            (px + 5, py - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

    output_path = OUTPUT_DIR / "cfd_final_00069_68.png"

    cv2.imwrite(str(output_path), visualization)

    print("Đã lưu:", output_path)


if __name__ == "__main__":
    main()
