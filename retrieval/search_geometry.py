
from pathlib import Path
from shared.paths import PROJECT_ROOT
import csv
import cv2
import numpy as np

from features.A_geometry.src.geometry_features import (
    DATASET_DIR,
    extract_geometry
)

FEATURE_DIR = (PROJECT_ROOT / "outputs/A_geometry/features")
OUTPUT_DIR = (PROJECT_ROOT / "outputs/retrieval/search_results")

# Ảnh truy vấn thử nghiệm
QUERY_IMAGE = DATASET_DIR / "cfd_final_00144.png"

TOP_K = 5

# ==============================
# 1. ĐỌC ĐẶC TRƯNG ĐÃ LƯU
# ==============================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    X = np.load(
        FEATURE_DIR / "features_A_normalized.npy"
    )

    stats = np.load(
        FEATURE_DIR / "geometry_stats.npz"
    )

    mean = stats["mean"]
    std = stats["std"]

    with open(
        FEATURE_DIR / "metadata.csv",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        metadata = list(csv.DictReader(f))

    assert len(metadata) == len(X)
    assert X.shape[1] == 150

    # ==============================
    # 2. TRÍCH XUẤT ẢNH TRUY VẤN
    # ==============================

    features, A1, A2, eye_distance = (
        extract_geometry(QUERY_IMAGE)
    )

    # Chuẩn hóa bằng thống kê đã lưu
    query_vector = (
        features.astype(np.float64) - mean
    ) / std

    # ==============================
    # 3. TÍNH KHOẢNG CÁCH EUCLID
    # ==============================

    distances = np.linalg.norm(
        X.astype(np.float64) - query_vector,
        axis=1
    )

    # Nếu ảnh truy vấn nằm trong dataset,
    # loại chính ảnh đó khỏi kết quả
    for i, item in enumerate(metadata):
        if Path(item["image_path"]).resolve() == (
            QUERY_IMAGE.resolve()
        ):
            distances[i] = np.inf

    # ==============================
    # 4. TÌM TOP 5
    # ==============================

    top_indices = np.argsort(distances)[:TOP_K]

    print("\n===== TOP 5 ẢNH TƯƠNG ĐỒNG =====")
    print("Ảnh truy vấn:", QUERY_IMAGE.name)

    results = []

    for rank, idx in enumerate(top_indices, start=1):
        item = metadata[idx]
        distance = float(distances[idx])

        print(
            f"{rank}. {item['image_name']} "
            f"| Euclid = {distance:.6f}"
        )

        results.append({
            "rank": rank,
            "image_name": item["image_name"],
            "distance": distance
        })

    # ==============================
    # 5. TẠO ẢNH MINH HỌA TOP 5
    # ==============================

    query_img = cv2.imread(str(QUERY_IMAGE))

    if query_img is None:
        raise FileNotFoundError(QUERY_IMAGE)

    query_img = cv2.resize(query_img, (256, 256))

    # Ảnh truy vấn + 5 kết quả
    canvas = np.full(
        (310, 256 * 6, 3),
        255,
        dtype=np.uint8
    )

    canvas[0:256, 0:256] = query_img

    cv2.putText(
        canvas,
        "QUERY",
        (80, 280),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 0),
        2
    )

    for rank, idx in enumerate(top_indices, start=1):
        item = metadata[idx]

        image = cv2.imread(item["image_path"])

        if image is None:
            continue

        image = cv2.resize(image, (256, 256))

        x = rank * 256
        canvas[0:256, x:x + 256] = image

        cv2.putText(
            canvas,
            f"TOP {rank}",
            (x + 75, 275),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            2
        )

        cv2.putText(
            canvas,
            f"D={distances[idx]:.3f}",
            (x + 65, 300),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1
        )

    output_path = (
        OUTPUT_DIR /
        f"{QUERY_IMAGE.stem}_top5.png"
    )

    cv2.imwrite(str(output_path), canvas)

    print("\nĐã lưu ảnh kết quả:", output_path)


if __name__ == "__main__":
    main()
