# Đặc tả Bộ B — B144_raw_v1.0.0

**APPROVED FOR IMPLEMENTATION — 22/11/2026; schema version 1.0.0.** Nguồn chuẩn duy nhất: [csdldpt.pdf](/C:/Users/USER/Downloads/csdldpt.pdf), SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`.

PDF §2.3 (trang 11–13) quy định cấu trúc, không gian màu, số bin, L1, phép chiếu Hue và Euclid; §2.5 (trang 16–18) quy định chuẩn hóa theo kho và kết hợp. Các chi tiết số học/ROI bên dưới là **quy ước D01–D17 được người dùng chấp thuận**, không phải tất cả đều là công thức nguyên văn PDF. [Bảng quyết định](B_implementation_decisions.md) ghi từng nội dung gốc và quyết định; [audit](report_compliance_audit.md) là hồ sơ trước phê duyệt. PDF giữ nguyên.

## 1. Cấu trúc và thứ tự

| Thành phần | Mỗi vùng | Skin + Hair | Index skin / hair (0-based) |
|---|---:|---:|---|
| B1: HSV H–S 12×4, L1 | 48 | 96 | 0–47 / 72–119 |
| B2: Lab mean/std/skew/kurt, ba kênh | 12 | 24 | 48–59 / 120–131 |
| B3: Hue10 L1 + circular mean/std | 12 | 24 | 60–71 / 132–143 |
| Tổng | 72 | **144** | Skin72 rồi Hair72 |

Mỗi vùng: `[HS48, Lab12, Hue10, circular_mean, circular_std]`. HS flatten C-order, Hue ngoài/Saturation trong. Lab12: `[L.mean,L.std,L.skew,L.kurt,a.mean,a.std,a.skew,a.kurt,b.mean,b.std,b.skew,b.kurt]`. Đây là serialization được chấp thuận, áp dụng chung cho kho, stats và query.

## 2. Đầu vào và ROI

- Ảnh chân dung đã căn chỉnh 256×256, uint8; OpenCV đọc BGR, tương ứng dữ liệu RGB của báo cáo theo đúng thứ tự kênh.
- Chỉ dùng raw mask UniFace: **Skin=1, Hair=17**. Không gộp nose=10, tai, cổ hoặc lớp khác; không erosion.
- Mask nhị phân uint8 cùng kích thước, giá trị 0/255, da/tóc không chồng lấn. Tính trên `image[mask>0]`, không lấy nền đen của preview; pixel đen thật trong mask vẫn được tính.
- Mỗi vùng phải có **ít nhất 100 pixel**. Nếu bất kỳ vùng nào không đạt, trả vector=None; ghi missing_empty hoặc insufficient_pixels, không tạo histogram 0/NaN để giả có dữ liệu.
- Không lọc theo Saturation. Nếu >50% pixel vùng có S<10, chỉ cảnh báo Hue ít tin cậy. Warning không tự loại ảnh khỏi tập fit nếu vẫn có vector hợp lệ.
- Raw mask kiểm chứng bằng receipt, SHA-256, pixel counts, metadata và định dạng; điều này không chứng minh chất lượng ngữ nghĩa/GT. Không dùng skin_masks template làm GT.

## 3. B1 — histogram H–S

HSV uint8 OpenCV: H thuộc 0..179, S thuộc 0..255. 12 bin H đều trên [0,180), cạnh 0,15,…,180; 4 bin S đều trên [0,256), cạnh 0,64,…,256. Chỉ dùng H/S, không V. Với đếm n_ij, `h_ij=n_ij/sum(n_ij)`; mỗi histogram HS48 có tổng 1 trước Z-score.

Số bin, H–S và L1 là yêu cầu rõ của §2.3.1 (PDF 12); cạnh bin/biểu diễn uint8 là D01 được chấp thuận.

## 4. B2 — mô-men CIE-Lab

BGR float32/255 → Lab float bằng OpenCV (L* khoảng 0–100, a*/b* có dấu). Tính mô-men float64, pixel có trọng số bằng nhau. Với N pixel mỗi kênh:

```text
mu = sum(x_i)/N
m_k = sum((x_i-mu)^k)/N
std = sqrt(m_2)                  # ddof=0
skew = m_3 / std^3              # không hiệu chỉnh bias
kurtosis = m_4 / std^4          # Pearson, không trừ 3
```

Nếu std<1e-12: std/skew/kurt=0 kèm warning, vẫn giữ mean. Skew/kurt kênh hằng vốn không xác định; giá trị 0 là fallback đã được chấp thuận. Fallback không được dùng thay cho dữ liệu vùng thiếu.

§2.3.2 (PDF 12) quy định các loại mô-men và CIE-Lab; D02–D05 chốt các chi tiết số học còn thiếu.

## 5. B3 — Hue vòng

Hue10 có cạnh đều 0,18,…,180, L1 riêng. Với pixel H:

```text
phi = 2*pi*H/180
C = mean(cos(phi)); S = mean(sin(phi))
R = clip(sqrt(C*C+S*S),0,1)
circular_mean = (atan2(S,C) modulo 2*pi)/(2*pi)
circular_std = min(sqrt(-2*log(max(R,1e-12)))/(2*pi),1)
```

Khi R<1e-8: circular mean=0, có warning. Sai số góc sát 2π trong dung sai 1e-12 được đưa về 0. Circular mean/std thuộc [0,1]. Không tăng số chiều, không thay bằng sin/cos hoặc metric vòng khác.

§2.3.3 (PDF 13) quy định 10 bin, L1, phép chiếu phi và miền [0,1]. Công thức resultant/atan2, scale std, floor/clip và suy biến là D06–D08 được chấp thuận; không gọi chúng là phương trình đầy đủ do PDF cung cấp.

## 6. Chuẩn hóa kho và query

D14 chốt trình tự: **descriptor chưa scale → ghép B144 → một lần Z-score all144**. Đây là cách hiện thực thống nhất bước chuẩn hóa theo kho; không tuyên bố PDF quy định duy nhất trình tự này. §2.3.3 (PDF 13) và §2.5.2 (PDF 17) có cách diễn đạt khác nhau về mô-men trước ghép; không thực hiện thêm một lần Z-score riêng mô-men trong phiên bản này.

Fit trên **tất cả và chỉ những ảnh có vector B hợp lệ trong kho 1.438 ảnh**. Thứ tự theo metadata A; danh sách đủ ảnh giữ a_row_index và image_id. Ma trận compact chỉ chứa hàng hợp lệ; manifest ánh xạ rõ feature_row_index, ảnh thiếu không có hàng giả.

```text
mean_j = mean(X_valid[:,j])
raw_std_j = std(X_valid[:,j], ddof=0)
divisor_j = 1 if raw_std_j < 1e-8 else raw_std_j
Z_j = (X_j - mean_j)/divisor_j
```

Lưu mean, raw_std, divisor (key `std`), constant_dimensions, fit_count, profile, schema_id và hash fit_manifest. Chiều hằng không bị xóa; training Z=0 tại chiều hằng. Query khác mean tại chiều này vẫn chia 1, không ép về 0. Query dùng đúng mean/divisor đã lưu, **không refit**. Sau Z-score, histogram không còn buộc L1 hoặc không âm; không L1 lại.

Các stats của trial100 giữ riêng và không được dùng cho kho đầy đủ. `moments_only`, clean và skin+nose là thí nghiệm lịch sử, không phải cấu hình chính thức v1.

## 7. Truy hồi và phiên bản output

`d_B(q,i)=sqrt(sum_j=1..144 (z_qj-z_ij)^2)`. Top-5 loại self-match theo image_id; hòa khoảng cách theo tên file. Khi metadata không có image_id, dùng filename stem làm ID ảnh, không phải ID người. Không loại các ảnh khác chỉ vì cùng người. Không thêm trọng số block, không tối ưu công thức theo Top-5.

Kết quả: `outputs/B_color/color_features_full_v1/`; `features_B_raw.npy` là descriptor dùng **raw mask trước Z-score**; `features_B_normalized.npy` là Z-score. `manifest.csv` chứa đủ 1.438 ảnh; `feature_rows.csv`/`fit_manifest.csv` chỉ hàng hợp lệ; `missing_features.csv` ghi ảnh thiếu/lỗi và lý do. Có schema, model_info, input hashes, stats, kiểm tra độc lập, distribution/warnings và contact sheet Top-5.

```powershell
# Lần chạy mới vào thư mục rỗng; không chạy lại segmentation:
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.full_color
# 10 query đa dạng, mỗi nguồn 5; chỉ tạo khi retrieval chưa có kết quả:
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.search_full_color
# Tests màu và oracle độc lập:
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p "test_color*.py" -v
```

Query ảnh mới phải có raw mask da/tóc tương ứng, cùng quy ước/định dạng và ảnh đã căn chỉnh 256×256. CLI `search_full_color --image ... --skin-mask ... --hair-mask ... --output ...` chỉ trích query rồi dùng stats kho; không chạy inference hoặc tải mô hình. `--image-id` dùng để bỏ đúng self-match nếu query thuộc kho; có thể tự nhận diện ID bằng hash duy nhất trùng ảnh kho. Xem [báo cáo cuối](B_color_final_report.md) để biết kết quả thực thi và lệnh đầy đủ.

Phê duyệt cấu hình và kiểm tra định dạng/số học không chứng minh độ chính xác phân đoạn/nhận diện. Bộ A/C1/C2 và công thức median normalization/fusion ở §2.5 giữ nguyên; phiên bản này chỉ truy hồi riêng B.
