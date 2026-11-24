
from pathlib import Path
import cv2
import numpy as np
from uniface.parsing import BiSeNet

# ==========================================
# 1. CẤU HÌNH
# ==========================================

DATASET_DIR = Path(r"D:\TuNam4\dataset_HF_CFD_final")
IMAGE_NAME = "cfd_final_00728.png"

IMAGE_PATH = DATASET_DIR / "images" / IMAGE_NAME

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "B_color" / "uniface_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 2. ĐỌC ẢNH
# ==========================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise FileNotFoundError(f"Không tìm thấy ảnh: {IMAGE_PATH}")

# ==========================================
# 3. FACE PARSING
# ==========================================

print("Đang khởi tạo BiSeNet...")
parser = BiSeNet()

print("Đang phân đoạn ảnh...")
labels = np.asarray(parser.parse(image))

if labels.shape != image.shape[:2]:
    raise ValueError(
        f"Kích thước labels không khớp: {labels.shape}"
    )

# 1 = Skin, 17 = Hair
skin_mask = (labels == 1).astype(np.uint8) * 255
hair_mask = (labels == 17).astype(np.uint8) * 255

# ==========================================
# 4. EROSION - LÀM SẠCH MASK
# ==========================================

kernel = np.ones((3, 3), np.uint8)

skin_mask_clean = cv2.erode(
    skin_mask, kernel, iterations=1
)

hair_mask_clean = cv2.erode(
    hair_mask, kernel, iterations=1
)

# ==========================================
# 5. TRÍCH XUẤT VÙNG DA / TÓC
# ==========================================

skin_image = cv2.bitwise_and(
    image, image, mask=skin_mask_clean
)

hair_image = cv2.bitwise_and(
    image, image, mask=hair_mask_clean
)

# ==========================================
# 6. LƯU MASK GỐC VÀ MASK CLEAN
# ==========================================

stem = Path(IMAGE_NAME).stem

cv2.imwrite(
    str(OUTPUT_DIR / f"{stem}_skin_mask.png"),
    skin_mask
)

cv2.imwrite(
    str(OUTPUT_DIR / f"{stem}_hair_mask.png"),
    hair_mask
)

cv2.imwrite(
    str(OUTPUT_DIR / f"{stem}_skin_mask_clean.png"),
    skin_mask_clean
)

cv2.imwrite(
    str(OUTPUT_DIR / f"{stem}_hair_mask_clean.png"),
    hair_mask_clean
)

# ==========================================
# 7. TẠO PREVIEW TRƯỚC / SAU
# ==========================================

skin_original = cv2.bitwise_and(
    image, image, mask=skin_mask
)

hair_original = cv2.bitwise_and(
    image, image, mask=hair_mask
)

preview = np.hstack([
    image,
    skin_original,
    skin_image,
    hair_original,
    hair_image
])

cv2.imwrite(
    str(OUTPUT_DIR / f"{stem}_preview.png"),
    preview
)

# ==========================================
# 8. THỐNG KÊ
# ==========================================

print("\n===== KẾT QUẢ UNIFACE =====")
print("Ảnh:", IMAGE_NAME)
print("Skin gốc:", np.count_nonzero(skin_mask))
print("Skin clean:", np.count_nonzero(skin_mask_clean))
print("Hair gốc:", np.count_nonzero(hair_mask))
print("Hair clean:", np.count_nonzero(hair_mask_clean))
print("Đã lưu tại:", OUTPUT_DIR)
