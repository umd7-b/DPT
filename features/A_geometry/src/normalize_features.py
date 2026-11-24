
from pathlib import Path
from shared.paths import PROJECT_ROOT
import numpy as np

# Thư mục chứa đặc trưng
FEATURE_DIR = (PROJECT_ROOT / "outputs/A_geometry/features")

# Đọc ma trận đặc trưng
def main():
    X = np.load(
        FEATURE_DIR / "features_A_raw.npy"
    ).astype(np.float64)

    print("Kích thước dữ liệu:", X.shape)

    if X.ndim != 2 or X.shape[1] != 150:
        raise ValueError("Ma trận phải có 150 cột")

    if not np.all(np.isfinite(X)):
        raise ValueError("Dữ liệu chứa NaN hoặc Inf")

    # Tính trung bình và độ lệch chuẩn theo cột
    mean = np.mean(X, axis=0)
    std = np.std(X, axis=0)

    # Tránh chia cho 0
    std_safe = np.where(std < 1e-8, 1.0, std)

    # Chuẩn hóa Z-score
    X_normalized = (X - mean) / std_safe

    # Lưu ma trận chuẩn hóa
    np.save(
        FEATURE_DIR / "features_A_normalized.npy",
        X_normalized.astype(np.float32)
    )

    # Lưu tham số để chuẩn hóa ảnh truy vấn mới
    np.savez(
        FEATURE_DIR / "geometry_stats.npz",
        mean=mean,
        std=std_safe
    )

    # Kiểm tra kết quả
    print("\n===== KẾT QUẢ CHUẨN HÓA =====")
    print("Kích thước:", X_normalized.shape)
    print("Giá trị nhỏ nhất:", X_normalized.min())
    print("Giá trị lớn nhất:", X_normalized.max())

    print("\n5 đặc trưng đầu:")
    for i in range(5):
        print(
            f"Feature {i}: "
            f"mean={X_normalized[:, i].mean():.6f}, "
            f"std={X_normalized[:, i].std():.6f}"
        )

    print("\nĐã lưu features_A_normalized.npy")
    print("Đã lưu geometry_stats.npz")


if __name__ == "__main__":
    main()
