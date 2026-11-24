
from pathlib import Path
import cv2
import numpy as np
import mediapipe as mp

# ==========================================
# 1. CẤU HÌNH
# ==========================================

DATASET_DIR = Path(r"D:\TuNam4\dataset_HF_CFD_final")
IMAGE_NAME = "cfd_final_00088.png"

IMAGE_PATH = DATASET_DIR / "images" / IMAGE_NAME
SKIN_PATH = DATASET_DIR / "skin_masks" / (
    Path(IMAGE_NAME).stem + "_skin.png"
)

MODEL_PATH = Path("models/face_landmarker.task")

OUTPUT_DIR = Path("outputs/hair_masks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. ĐỌC ẢNH
# ==========================================

image = cv2.imread(str(IMAGE_PATH))
skin = cv2.imread(str(SKIN_PATH), cv2.IMREAD_GRAYSCALE)

if image is None:
    raise FileNotFoundError(IMAGE_PATH)

if skin is None:
    raise FileNotFoundError(SKIN_PATH)

h, w = image.shape[:2]

if skin.shape != (h, w):
    raise ValueError("Kích thước mặt nạ da không khớp")


# ==========================================
# 3. PHÁT HIỆN LANDMARKS
# ==========================================

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
    raise RuntimeError("Không phát hiện được khuôn mặt")

points = np.array([
    [lm.x * w, lm.y * h]
    for lm in result.face_landmarks[0]
], dtype=np.float32)


# ==========================================
# 4. TẠO MẶT NẠ KHUÔN MẶT
# ==========================================

FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356,
    454, 323, 361, 288, 397, 365, 379,
    378, 400, 377, 152, 148, 176, 149,
    150, 136, 172, 58, 132, 93, 234,
    127, 162, 21, 54, 103, 67, 109
]

face_mask = np.zeros((h, w), dtype=np.uint8)

face_polygon = np.round(
    points[FACE_OVAL]
).astype(np.int32)

cv2.fillPoly(face_mask, [face_polygon], 255)

expanded_face = cv2.dilate(
    face_mask,
    np.ones((5, 5), np.uint8)
)


# ==========================================
# 5. XÁC ĐỊNH VÙNG TÓC
# ==========================================

left = int(points[234, 0])
right = int(points[454, 0])
chin = int(points[152, 1])
forehead = int(points[10, 1])

# Giới hạn tọa độ
left = np.clip(left, 0, w - 1)
right = np.clip(right, 0, w - 1)
chin = np.clip(chin, 0, h - 1)
forehead = np.clip(forehead, 0, h - 1)

if left > right:
    left, right = right, left

face_width = max(1, right - left)

# Khởi tạo GrabCut
mask = np.full(
    (h, w),
    cv2.GC_PR_BGD,
    dtype=np.uint8
)

border = 5

mask[:border, :] = cv2.GC_BGD
mask[-border:, :] = cv2.GC_BGD
mask[:, :border] = cv2.GC_BGD
mask[:, -border:] = cv2.GC_BGD

# Vùng ứng viên tóc
margin = int(face_width * 0.35)

x1 = max(border, left - margin)
x2 = min(w - border, right + margin)

mask[border:h-border, x1:x2] = cv2.GC_PR_FGD

# Hạt giống tóc trên đỉnh đầu
seed_top = max(border, forehead - 45)
seed_bottom = max(seed_top + 1, forehead - 10)

seed_left = max(border, left + 15)
seed_right = min(w - border, right - 15)

if seed_right > seed_left:
    mask[
        seed_top:seed_bottom,
        seed_left:seed_right
    ] = cv2.GC_FGD

# Loại vùng mặt
mask[expanded_face > 0] = cv2.GC_BGD

if not np.any(mask == cv2.GC_FGD):
    raise RuntimeError("Không có hạt giống tóc hợp lệ")


# ==========================================
# 6. CHẠY GRABCUT
# ==========================================

bg_model = np.zeros((1, 65), np.float64)
fg_model = np.zeros((1, 65), np.float64)

cv2.grabCut(
    image,
    mask,
    None,
    bg_model,
    fg_model,
    7,
    cv2.GC_INIT_WITH_MASK
)

hair_mask = np.where(
    (mask == cv2.GC_FGD) |
    (mask == cv2.GC_PR_FGD),
    255,
    0
).astype(np.uint8)

# Loại mặt và da
hair_mask[expanded_face > 0] = 0
hair_mask[skin > 127] = 0

# Làm sạch nhiễu nhỏ
kernel = np.ones((3, 3), np.uint8)

hair_mask = cv2.morphologyEx(
    hair_mask,
    cv2.MORPH_OPEN,
    kernel
)


# ==========================================
# 7. LỌC VÙNG TÓC THEO VỊ TRÍ
# ==========================================

num_labels, labels, stats, _ = (
    cv2.connectedComponentsWithStats(
        hair_mask,
        connectivity=8
    )
)

filtered_mask = np.zeros_like(hair_mask)

# Vùng tóc có thể kéo dài tới đáy ảnh,
# nhưng phải nằm gần hai bên khuôn mặt.
side_margin = int(face_width * 0.18)

left_side_limit = left + side_margin
right_side_limit = right - side_margin

# Vùng đỉnh đầu
top_limit = max(1, forehead)

# Hạn chế các vùng quần áo thấp hơn cằm
lower_limit = min(h, chin + int(face_width * 0.35))

for i in range(1, num_labels):
    x, y, cw, ch, area = stats[i]

    if area < 100:
        continue

    component = labels == i

    # Tóc phía trên đầu
    touches_top = np.any(
        component[:top_limit, :]
    )

    # Tóc bên trái mặt
    left_region = np.any(
        component[:lower_limit, :left_side_limit]
    )

    # Tóc bên phải mặt
    right_region = np.any(
        component[:lower_limit, right_side_limit:]
    )

    # Chỉ giữ thành phần phù hợp vị trí
    if touches_top or left_region or right_region:
        filtered_mask[component] = 255

hair_mask = filtered_mask

# Loại mặt và da một lần nữa
hair_mask[expanded_face > 0] = 0
hair_mask[skin > 127] = 0


# ==========================================
# 8. HIỂN THỊ
# ==========================================

hair_image = cv2.bitwise_and(
    image,
    image,
    mask=hair_mask
)

mask_bgr = cv2.cvtColor(
    hair_mask,
    cv2.COLOR_GRAY2BGR
)

preview = np.hstack([
    image,
    mask_bgr,
    hair_image
])


# ==========================================
# 9. LƯU KẾT QUẢ
# ==========================================

stem = Path(IMAGE_NAME).stem

mask_output = OUTPUT_DIR / f"{stem}_hair_mask.png"
preview_output = OUTPUT_DIR / f"{stem}_hair.png"

cv2.imwrite(str(mask_output), hair_mask)
cv2.imwrite(str(preview_output), preview)

print("\n===== KẾT QUẢ TÁCH TÓC =====")
print("Ảnh:", IMAGE_NAME)
print("Kích thước:", image.shape)
print("Số pixel tóc:", np.count_nonzero(hair_mask))
print("Đã lưu mask:", mask_output)
print("Đã lưu preview:", preview_output)
