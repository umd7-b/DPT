
from pathlib import Path
from shared.paths import PROJECT_ROOT
import cv2
import numpy as np

DATASET_DIR = Path(
    r"D:\TuNam4\dataset_HF_CFD_final"
)

IMAGE_DIR = DATASET_DIR / "images"
MASK_DIR = DATASET_DIR / "skin_masks"

OUTPUT_DIR = (PROJECT_ROOT / "outputs/B_color/mask_check")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images = sorted(IMAGE_DIR.glob("*.png"))

    missing = []

    for image_path in images:
        mask_name = image_path.stem + "_skin.png"
        mask_path = MASK_DIR / mask_name

        if not mask_path.exists():
            missing.append(image_path.name)

    print("Tổng ảnh:", len(images))
    print("Số mặt nạ:", len(list(MASK_DIR.glob("*.png"))))
    print("Ảnh thiếu mặt nạ:", len(missing))

    for name in missing:
        print("THIẾU:", name)

    # Kiểm tra trực quan ảnh 00088
    image_name = "cfd_final_00088.png"

    image = cv2.imread(
        str(IMAGE_DIR / image_name)
    )

    mask = cv2.imread(
        str(MASK_DIR / "cfd_final_00088_skin.png"),
        cv2.IMREAD_GRAYSCALE
    )

    if image is None or mask is None:
        raise FileNotFoundError(
            "Không tìm thấy ảnh hoặc mặt nạ 00088"
        )

    if mask.shape != image.shape[:2]:
        raise ValueError("Kích thước mặt nạ không khớp ảnh")

    # Vùng trắng được xem là da
    skin_mask = np.where(
        mask > 127, 255, 0
    ).astype(np.uint8)

    skin_image = cv2.bitwise_and(
        image, image, mask=skin_mask
    )

    preview = np.hstack([
        image,
        cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR),
        skin_image
    ])

    output_path = (
        OUTPUT_DIR / "cfd_final_00088_check.png"
    )

    cv2.imwrite(str(output_path), preview)

    print("Pixel da:", np.count_nonzero(skin_mask))
    print("Đã lưu:", output_path)


if __name__ == "__main__":
    main()
