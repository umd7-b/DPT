
from pathlib import Path
from shared.paths import PROJECT_ROOT
import cv2
import mediapipe as mp
import numpy as np

# ==============================
# 1. CẤU HÌNH
# ==============================

DATASET_DIR = Path(
    r"D:\TuNam4\dataset_HF_CFD_final\images"
)

MODEL_PATH = (PROJECT_ROOT / "models/face_landmarker.task")
OUTPUT_DIR = (PROJECT_ROOT / "outputs/A_geometry/features")

IMAGE_NAME = "cfd_final_00001.png"

# Giữ đúng bảng ánh xạ đã dùng ở bước trước
JAW = [
    234, 93, 132, 58, 172, 136, 150, 149,
    152, 378, 379, 365, 397, 288, 361, 323, 454
]

LEFT_EYEBROW = [70, 63, 105, 66, 107]
RIGHT_EYEBROW = [336, 296, 334, 293, 300]

NOSE = [
    168, 6, 197, 1,
    129, 48, 4, 278, 358
]

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

MOUTH = [
    61, 40, 37, 0, 267, 270,
    291, 321, 314, 17, 84, 91,
    78, 81, 13, 311, 308, 402, 14, 178
]

INDICES = (
    JAW + LEFT_EYEBROW + RIGHT_EYEBROW +
    NOSE + LEFT_EYE + RIGHT_EYE + MOUTH
)

assert len(INDICES) == 68
assert len(set(INDICES)) == 68


# ==============================
# 2. HÀM TÍNH TOÁN
# ==============================

def distance(a, b):
    return float(np.linalg.norm(a - b))


def midpoint(a, b):
    return (a + b) / 2.0


def angle_degrees(a, vertex, b):
    u = a - vertex
    v = b - vertex

    denominator = (
        np.linalg.norm(u) * np.linalg.norm(v)
    )

    if denominator < 1e-8:
        raise ValueError("Không tính được góc hàm")

    cosine = np.dot(u, v) / denominator
    cosine = np.clip(cosine, -1.0, 1.0)

    return float(np.degrees(np.arccos(cosine)))


# ==============================
# 3. CHUẨN HÓA 68 LANDMARKS
# ==============================

def normalize_landmarks(points):
    left_eye_center = np.mean(points[36:42], axis=0)
    right_eye_center = np.mean(points[42:48], axis=0)

    center = midpoint(
        left_eye_center,
        right_eye_center
    )

    eye_distance = distance(
        left_eye_center,
        right_eye_center
    )

    if eye_distance < 1e-6:
        raise ValueError("Khoảng cách hai mắt không hợp lệ")

    normalized = (points - center) / eye_distance

    return normalized, eye_distance


# ==============================
# 4. TÍNH 14 ĐẶC TRƯNG
# ==============================

FEATURE_NAMES = [
    "face_width_height",
    "eye_distance_face_height",
    "left_eye_width",
    "right_eye_width",
    "left_eye_open",
    "right_eye_open",
    "nose_width",
    "mouth_width",
    "mouth_open",
    "eye_to_nose",
    "eye_to_mouth",
    "nose_to_chin",
    "jaw_width",
    "chin_angle"
]


def calculate_ratios(p):
    eps = 1e-8

    # Tâm mắt
    eye_l = np.mean(p[36:42], axis=0)
    eye_r = np.mean(p[42:48], axis=0)
    eye_mid = midpoint(eye_l, eye_r)

    inter_eye = distance(eye_l, eye_r)

    # Chiều cao mặt xấp xỉ:
    # từ điểm giữa hai lông mày đến cằm
    brow_mid = midpoint(p[21], p[22])
    face_height = distance(brow_mid, p[8])

    # Chiều rộng mặt và hàm
    face_width = distance(p[2], p[14])
    jaw_width = distance(p[4], p[12])

    # Chiều rộng mắt
    left_width = distance(p[36], p[39])
    right_width = distance(p[42], p[45])

    # Độ mở mắt / chiều rộng mắt
    left_open = (
        distance(p[37], p[41]) +
        distance(p[38], p[40])
    ) / (2 * left_width + eps)

    right_open = (
        distance(p[43], p[47]) +
        distance(p[44], p[46])
    ) / (2 * right_width + eps)

    # Mũi
    nose_width = distance(p[31], p[35])
    nose_tip = p[30]

    # Miệng
    mouth_width = distance(p[48], p[54])
    mouth_open = distance(p[62], p[66])

    mouth_mid = midpoint(p[48], p[54])

    # Góc hàm tại cằm
    chin_angle = angle_degrees(
        p[4], p[8], p[12]
    )

    ratios = np.array([
        face_width / (face_height + eps),
        inter_eye / (face_height + eps),
        left_width / (inter_eye + eps),
        right_width / (inter_eye + eps),
        left_open,
        right_open,
        nose_width / (inter_eye + eps),
        mouth_width / (inter_eye + eps),
        mouth_open / (inter_eye + eps),
        distance(eye_mid, nose_tip) / (inter_eye + eps),
        distance(eye_mid, mouth_mid) / (inter_eye + eps),
        distance(nose_tip, p[8]) / (face_height + eps),
        jaw_width / (face_height + eps),
        chin_angle
    ], dtype=np.float32)

    return ratios


# ==============================
# 5. PHÁT HIỆN LANDMARKS
# ==============================

def detect_landmarks(image_path):
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

    if len(result.face_landmarks) != 1:
        raise RuntimeError("Không phát hiện khuôn mặt")

    h, w = image.shape[:2]

    points_478 = np.array([
        [lm.x * w, lm.y * h]
        for lm in result.face_landmarks[0]
    ], dtype=np.float32)

    return points_478[INDICES]


# ==============================
# 6. TẠO VECTOR 150 CHIỀU
# ==============================

def extract_geometry(image_path):
    points = detect_landmarks(image_path)

    normalized, eye_distance = normalize_landmarks(
        points
    )

    # A1: 136 tọa độ
    A1 = normalized.flatten().astype(np.float32)

    # A2: 14 tỉ lệ và góc
    A2 = calculate_ratios(points)

    # Vector A: 150 chiều
    features = np.concatenate([A1, A2])

    assert A1.shape == (136,)
    assert A2.shape == (14,)
    assert features.shape == (150,)
    assert np.all(np.isfinite(features))

    return features, A1, A2, eye_distance


# ==============================
# 7. CHẠY THỬ
# ==============================

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = DATASET_DIR / IMAGE_NAME

    features, A1, A2, eye_distance = (
        extract_geometry(image_path)
    )

    print("\n===== KẾT QUẢ BỘ A =====")
    print("Ảnh:", IMAGE_NAME)
    print("Khoảng cách hai mắt:", eye_distance)

    print("\nA1:", A1.shape)
    print("A2:", A2.shape)
    print("Vector A:", features.shape)

    print("\n14 đặc trưng hình học:")

    for name, value in zip(FEATURE_NAMES, A2):
        print(f"{name:30s}: {value:.6f}")

    output_path = (
        OUTPUT_DIR / f"{Path(IMAGE_NAME).stem}_A.npy"
    )

    np.save(output_path, features)

    print("\nĐã lưu:", output_path)
