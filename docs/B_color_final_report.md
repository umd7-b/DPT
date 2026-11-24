# Báo cáo hoàn tất Bộ B — B144_raw_v1.0.0

Ngày: **22/11/2026**. Đã triển khai và chạy thực tế trên kho **1.438 ảnh**, tạo **1.437 vector B144 hợp lệ**, ghi rõ **1 ảnh thiếu vùng tóc**. Kết quả phiên bản mới: [color_features_full_v1](../outputs/B_color/color_features_full_v1/). Không chạy lại segmentation, không điền vector thiếu bằng zero, không thay đổi A/C1/C2 hoặc kết quả thí nghiệm cũ.

## 1. Cấu hình và nguồn thẩm quyền

Nguồn báo cáo duy nhất: [csdldpt.pdf](/C:/Users/USER/Downloads/csdldpt.pdf), SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Hash được kiểm tra trực tiếp trước trích xuất và sau xử lý. Số trang dưới đây là trang PDF đếm từ 1.

Schema **`B144_raw_v1.0.0`**, version **1.0.0**, D01–D17 **APPROVED FOR IMPLEMENTATION** theo chỉ định của người dùng ngày 22/11/2026. [Bảng quyết định](B_implementation_decisions.md) và [đặc tả](B_color_feature_spec.md) đã được cập nhật thống nhất.

Các yêu cầu rõ trong PDF và các quy ước được chấp thuận có nguồn thẩm quyền riêng. Phê duyệt Pearson kurtosis, scale/clipping circular std, ROI hoặc trình tự chuẩn hóa không có nghĩa PDF đã viết đầy đủ những công thức đó. [Audit trước phê duyệt](report_compliance_audit.md) giữ nguyên như hồ sơ lịch sử. Không sửa PDF và không tuyên bố toàn bộ hệ thống A/B/C/fusion đã được chứng nhận tuân thủ hoặc có độ chính xác đã xác lập.

| Quy định trong báo cáo | Trang PDF | Thực thi v1 | Chi tiết được chấp thuận bổ sung |
|---|---|---|---|
| Hai vùng da/tóc, mỗi vùng 72, tổng 144 | §2.3, 11–12; §2.5.1, 16 | Skin72 rồi Hair72; mỗi vùng HS48 + Lab12 + Hue12 | D09: class 1 và 17; D13: serialization cố định |
| B1 HSV H–S, 12×4, L1 | §2.3.1, 12 | Đủ 48 chiều/vùng, tổng histogram 1 trước Z-score | D01: HSV uint8, H [0,180), S [0,256), bin đều |
| B2 CIE-Lab, mean/std/skew/kurtosis trên L*, a*, b* | §2.3.2, 12 | 4×3=12 chiều/vùng | D02–D05: Lab từ BGR float32/255, mô-men float64, ddof=0, skew không bias, Pearson kurtosis, fallback có cảnh báo |
| B3 Hue10 L1 + circular mean/std | §2.3.3, 13 | Đúng 12 chiều/vùng | D01/D06–D08: cạnh bin, atan2/modulo, công thức std và suy biến |
| Góc φ=2πH/180; thống kê vòng thuộc [0,1] | §2.3.3, 13 | Dùng đúng phép chiếu; kiểm tra toàn bộ vector | Công thức std=`min(sqrt(-2*log(max(R,1e-12)))/(2π),1)` và R<1e-8 là quy ước được chấp thuận |
| Chỉ tính trên vùng quan tâm hợp lệ | §2.3.1, 12 | Chỉ pixel ảnh gốc trong raw mask; không lấy nền đen ngoài mask | D09–D12: không gộp lớp, không erosion, không lọc S, mỗi vùng ≥100 pixel |
| Chuẩn hóa theo thống kê kho, bước cuối Z-score từng chiều | §2.3.3, 13; §2.5.2, 17 | Descriptor → ghép B144 → một lần all144 | D14 thống nhất cách hiện thực, không khẳng định PDF chỉ định duy nhất trình tự; D15 chốt ddof/divisor |
| Dùng tham số kho cho query | §2.3.3, 13; §2.5.2, 17 | Lưu mean/std và danh sách fit; query chỉ transform | D16: tất cả và chỉ vector hợp lệ trong kho; không refit theo query |
| Euclid cho B, kết quả tăng dần | §2.3.3, 13; §2.5.2–2.5.3, 17–18 | Euclid đủ 144 tọa độ sau Z-score | D17: bỏ self-match theo image_id; hòa khoảng cách theo tên file |

Không thay số bins, không thêm sin/cos vào vector, không dùng cosine/Chi-square cho B, không thêm trọng số block hoặc tối ưu công thức theo Top-5. Vẫn giữ các pixel ít bão hòa; chỉ ghi cảnh báo khi >50% pixel vùng có S<10.

## 2. Dữ liệu, thứ tự và truy vết

Thứ tự chuẩn lấy từ `outputs/A_geometry/features/metadata.csv`, đúng 1.438 ảnh. Tập ảnh và thứ tự khớp manifest UniFace full. Manifest đầy đủ giữ `a_row_index` và `image_id`; metadata hiện không có image_id nên dùng filename stem làm ID ảnh. Đây không phải ID người: các ảnh khác nhau của cùng người vẫn có thể được trả về.

Mỗi ảnh được đối chiếu SHA-256 với UniFace manifest và receipt; hai raw mask được đối chiếu hash với receipt, đúng 256×256, uint8, chỉ 0/255, không chồng lấn, số pixel khớp metrics/receipt. Tổng **1.438 ảnh và 2.876 raw mask đã xác minh kỹ thuật**. Chỉ đọc `uniface_full/masks/skin/` và `masks/hair/` để tạo đặc trưng; không lấy mask clean hoặc skin_masks template làm dữ liệu đánh giá.

| Nguồn | Ảnh đầu vào | Vector hợp lệ | Thiếu B144 | Ảnh có cảnh báo raw/đặc trưng |
|---|---:|---:|---:|---:|
| CFD | 710 | 710 | 0 | 497 |
| HF | 728 | 727 | 1 | 672 |
| Tổng | **1.438** | **1.437** | **1** | **1.169** |

Ảnh thiếu duy nhất: **`hf_merged_00209.png`**, a_row_index **918**, skin **22.231 pixel**, hair **0 pixel**. Trạng thái `missing_region`, lý do `hair:missing_empty(0<100)`; không có feature_row_index và không có hàng giả trong ma trận. Đây là thiếu dữ liệu vùng tóc theo cấu hình, không tự kết luận là một lỗi phân đoạn. Xem [missing_features.csv](../outputs/B_color/color_features_full_v1/missing_features.csv).

Ảnh hợp lệ vẫn có thể có ít tóc hoặc mask kém đại diện: số pixel tóc nhỏ nhất trong tập hợp lệ là **106**, số pixel da nhỏ nhất **15.237**. Ngưỡng 100 là chính sách được chấp thuận, không phải chứng nhận chất lượng vùng. Warning không tự loại ảnh khỏi tập fit: **1.168/1.437 vector hợp lệ có cảnh báo**. Tổng 1.169 cảnh báo theo ảnh ở bảng này dùng raw/feature; không bao gồm các cảnh báo chỉ liên quan clean như báo cáo segmentation cũ.

Ma trận compact giữ thứ tự các ảnh hợp lệ trong metadata. `feature_rows.csv` ánh xạ feature_row_index → a_row_index/image_id; sau hàng metadata 918, chỉ số hàng feature không còn bằng chỉ số metadata. Không ghép với A bằng cách mặc định hai ma trận có cùng số hàng.

Model được tái sử dụng qua mask đã lưu: UniFace **4.3.0**, BiSeNet **parsing_resnet18**, provider của lần segmentation **CPUExecutionProvider**. SHA-256 ONNX đã kiểm tra với file cache hiện có: `0d9bd318e46987c3bdbfacae9e2c0f461cae1c6ac6ea6d43bbe541a91727e33f`. Số inference mới: **0**. Môi trường chạy đặc trưng: Python **3.11.9**, NumPy **2.4.6**, OpenCV **5.1.0**, `.venv-uniface`; không tải/cài thêm gì.

Thời gian trích xuất theo từng ảnh: **22,05 giây**; pipeline gồm kiểm tra/hash và lưu kết quả: **33,86 giây**. Thời gian này chưa tính các bước Top-5, API smoke test và kiểm chứng độc lập sau đó. Số liệu đo của lần chạy, không phải cam kết hiệu năng.

## 3. Ma trận và chuẩn hóa

| Hạng mục | Kết quả thực tế |
|---|---|
| `features_B_raw.npy` | **(1437, 144)**, float64; descriptor dùng raw mask, chưa Z-score |
| `features_B_normalized.npy` | **(1437, 144)**, float64 |
| Tập fit | **1.437 ảnh hợp lệ**, ghi trong `fit_manifest.csv` |
| Thống kê | mean/std ddof=0; divisor=1 nếu std<1e-8; query không fit lại |
| Chiều std bằng/gần 0 theo ngưỡng | **0** trên kho này; logic fallback vẫn có tests độc lập |
| Histogram L1 trước Z-score | **5.748** histogram được kiểm tra độc lập |
| Miền circular mean/std trước Z-score | Toàn bộ thuộc [0,1]; min **0,0009015295**, max **0,9998981031** |
| NaN / Inf | **0 / 0** trong hai ma trận |
| Max trị tuyệt đối mean của Z-score | **1,227e-15** |
| Max sai số std(Z) so với 1 | **4,441e-16** |
| Sai số mean/std với oracle tổng vô hướng độc lập | **7,106e-15 / 8,882e-16** |
| Sai số Z-score với oracle độc lập | **7,106e-15** |
| Tái tạo Z-score bằng đúng stats đã lưu | Sai số **0** |

`normalization_stats.npz` lưu mean, divisor với key `std`, raw_std, constant_dimensions, fit_count, profile, schema_id và hash `fit_manifest.csv`. Không thay divisor bằng raw_std khi truy vấn. Stats của thí nghiệm 100 ảnh giữ nguyên và không được dùng cho kho này.

Z-score có thể âm và không còn tổng histogram bằng 1; không chuẩn hóa L1 lại sau đó. Miền Z trong lần chạy: **[-12,703868; 37,885358]**. Có **305 ảnh** với ít nhất một tọa độ có abs(Z)>5, được ghi trong `feature_outliers.csv`; đây là gợi ý kiểm tra phân bố, không phải 305 lỗi hay một phép đo chất lượng. Không loại các ảnh này hoặc đổi trọng số/công thức.

## 4. Mã và kiểm thử

Các module mới đều ở `features/B_color/src/`:

- `full_color.py`: schema được chấp thuận, kiểm tra raw input, xử lý đủ metadata, lưu trạng thái/ma trận/stats/provenance. Từ chối output đã có dữ liệu.
- `search_full_color.py`: kiểm tra hash/schema kho, chọn 10 query đa dạng, Top-5 theo ID, API/CLI cho query mới với stats đã lưu.
- `verify_full_color.py`: đối chiếu độc lập dữ liệu đã lưu, histogram, số học chuẩn hóa và Top-5. Không gọi extractor, hàm fit hoặc hàm rank đang chạy để làm oracle.

`color_features.py`, `run_color_experiment.py`, `search_color.py` và thuật toán UniFace giữ nguyên trong nhiệm vụ này. Tái sử dụng nguyên descriptor và standardizer đã kiểm thử; schema phê duyệt được lưu riêng ở module mới, không đổi metadata lịch sử của trial.

**40/40 color unit tests đạt**, log ở [unit_tests.log](../outputs/B_color/color_features_full_v1/validation/unit_tests.log). Gồm 32 tests trước đây và 8 tests mới trong `tests/test_color_full.py`. Oracles độc lập gồm khối lượng bin được ấn định, phân bố Lab có nghiệm giải tích, hai góc có resultant giải tích, Z-score trên kho ba hàng/query ngoài kho và khoảng cách nhiều tọa độ 3–4–5. Tests mới kiểm tra raw-only input không cần clean/inference, hash/count sai bị từ chối, schema không làm đổi trial cũ, self-match theo ID, tie theo tên và tính toàn vẹn stats/kho.

Hậu kiểm toàn kho đọc lại 1.438 ảnh và 2.876 mask, tính mean/std bằng `math.fsum`, kiểm tra **50 dòng Top-5** bằng Euclid tính độc lập. Sai số khoảng cách lớn nhất **3,553e-15**, thứ tự khớp. **100/100 descriptor raw của tập thử trước đây bằng đúng từng phần tử với hàng tương ứng trong kho mới**; các Z-score khác trial100 là do tập fit đã được đổi sang toàn bộ 1.437 ảnh hợp lệ, đúng D16.

API query đã được thử bằng bản sao đổi tên của `cfd_final_00239.png`: nhận diện ID bằng hash, loại self-match dù tên file query khác, descriptor/Z-score bằng đúng hàng kho và stats không thay đổi. Đây là smoke test API bằng ảnh có sẵn, không phải đánh giá holdout. Trường hợp `hf_merged_00209.png` trả `missing_region`, không lưu vector hoặc Top-5; query ngoài kho có oracle tính tay trong unit tests. Xem [query_api_checks.json](../outputs/B_color/color_features_full_v1/validation/query_api_checks.json).

## 5. Top-5 và giới hạn chất lượng

Chọn 10 ảnh hợp lệ, **5 CFD + 5 HF**, bằng farthest-point coverage trên mean Lab da/tóc chưa scale. Median/IQR chỉ dùng để chọn query, không dùng làm metric tìm kiếm. Mỗi query tìm trên kho 1.437 vector, sau bỏ self còn 1.436 ứng viên. Không fit lại stats theo query và không tối ưu descriptor sau khi xem kết quả.

| Query | Top-1 | Khoảng cách Euclid |
|---|---|---:|
| cfd_final_00239.png | cfd_final_00240.png | 3,457160 |
| cfd_final_00744.png | cfd_final_00733.png | 9,813132 |
| cfd_final_00537.png | cfd_final_00536.png | 1,174659 |
| cfd_final_00370.png | cfd_final_00362.png | 6,171221 |
| cfd_final_00733.png | cfd_final_00747.png | 4,745943 |
| hf_merged_00694.png | cfd_final_00342.png | 5,413242 |
| hf_merged_00676.png | hf_merged_00381.png | 29,256899 |
| hf_merged_00722.png | hf_merged_00688.png | 16,593418 |
| hf_merged_00683.png | hf_merged_00219.png | 5,246007 |
| hf_merged_00102.png | hf_merged_00612.png | 13,004186 |

Contact sheet đã xem trực quan: [CFD — trang 1](../outputs/B_color/color_features_full_v1/retrieval/contact_sheet/page_01.png), [HF — trang 2](../outputs/B_color/color_features_full_v1/retrieval/contact_sheet/page_02.png). Mỗi trang có 5 query; mỗi hàng gồm query và 5 kết quả, tên ảnh và khoảng cách. [top5.csv](../outputs/B_color/color_features_full_v1/retrieval/top5.csv) chứa đủ 50 kết quả với độ chính xác số được lưu; PNG từng query ở `retrieval/queries/`.

Các quan sát cần xem lại, chưa phải nhãn relevance hoặc nhãn segmentation:

- `hf_merged_00676.png`: query tóc hồng sáng, các kết quả có màu tóc khác quan sát được. Màu hiếm/điều kiện sáng và cách kết hợp 144 tọa độ cần được đánh giá bằng tiêu chí phù hợp; không sửa công thức để làm ví dụ này đẹp hơn. D=29,26 không tự định nghĩa một kết quả đúng/sai hoặc ngưỡng chấp nhận.
- `hf_merged_00694.png`: ảnh có khăn che tóc; raw hair chỉ **355 pixel**, tập trung dải nhỏ sát mép trên. Đạt ngưỡng 100 không bảo đảm vùng màu tóc đại diện tốt.
- `hf_merged_00722.png`: bàn tay che mặt và phần da tay xuất hiện trong raw skin mask quan sát được; màu da mô tả có thể chịu ảnh hưởng vùng che khuất. Không có nhãn độc lập để định lượng mức sai hoặc kết luận quan hệ nhân quả với ranking.
- `hf_merged_00209.png`: tóc bị che trong ảnh quan sát, mask dự đoán không có pixel tóc; giữ trạng thái thiếu B144, không suy diễn một màu tóc.

Xem [raw_mask_examples.png](../outputs/B_color/color_features_full_v1/review/raw_mask_examples.png): ảnh gốc, da raw và tóc raw cùng số pixel. Đây là hiển thị dự đoán thật đã lưu, không phải ground truth.

Các cảnh báo chạm biên, tóc bị cắt, vùng ít pixel, Hue ít bão hòa, phụ kiện, ánh sáng và vùng không đúng đối tượng có thể làm màu không đại diện. Class 1 bỏ mũi là lựa chọn được chấp thuận. Hash/định dạng không xác nhận mask đúng giải phẫu. Kho chứa ảnh khác biểu cảm của cùng người; chúng có thể xuất hiện ở Top-5 và không chứng minh khả năng nhận diện người mới. **Không báo accuracy, IoU, Dice hoặc độ chính xác nhận diện vì chưa có ground truth/relevance labels độc lập cho đánh giá tương ứng.**

## 6. Lệnh chạy và query ảnh mới

Chạy trong PowerShell tại `D:\TuNam4\portrait-retrieval`. Kết quả hiện tại đã có, không chạy lệnh trích xuất mặc định để ghi lại thư mục này. Muốn tái lập, dùng thư mục phiên bản chạy mới/rỗng:

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.full_color --output outputs/B_color/color_features_full_v1_rerun
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.search_full_color --gallery outputs/B_color/color_features_full_v1_rerun
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.verify_full_color --gallery outputs/B_color/color_features_full_v1_rerun
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p "test_color*.py" -v
```

Có thể kiểm tra lại bộ hiện tại bằng `verify_full_color` không truyền `--gallery`; công cụ giữ nguyên bằng chứng đã ghi nếu kết quả vẫn khớp.

Với ảnh mới: cần ảnh đã căn chỉnh 256×256 và **hai raw mask nhị phân cùng ảnh**, tương ứng UniFace class 1 và 17. Dùng pipeline UniFace có sẵn để chuẩn bị mask khi cần; CLI query không suy ra lớp từ tên file, không chạy segmentation hoặc tải mô hình. SHA-256 lưu lại đầu vào; kiểm tra nhị phân không tự chứng minh nguồn lớp/ngữ nghĩa của mask người dùng cung cấp.

Ví dụ dưới đây dùng ảnh đã có để thử cùng đường gọi; thay ba đường dẫn bằng ảnh/mask mới và dùng output mới/rỗng:

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.search_full_color `
  --gallery outputs/B_color/color_features_full_v1 `
  --image D:/TuNam4/dataset_HF_CFD_final/images/cfd_final_00001.png `
  --skin-mask outputs/B_color/uniface_full/masks/skin/cfd_final_00001_skin_mask.png `
  --hair-mask outputs/B_color/uniface_full/masks/hair/cfd_final_00001_hair_mask.png `
  --image-id cfd_final_00001 `
  --output outputs/B_color/color_features_full_v1/query_results/example_00001
```

`--image-id` là ID ảnh để loại self-match nếu query thuộc kho. Khi không truyền, code nhận diện bằng SHA-256 nếu có đúng một ảnh kho trùng; query mới ngoài kho không loại ứng viên nào. Không gán ID người thay cho ID ảnh. Nếu hash trùng nhiều ID, CLI yêu cầu chỉ định ID thay vì tự đoán.

Luồng query: kiểm tra schema/hash kho → tính descriptor theo cùng quy ước → nếu thiếu vùng chỉ lưu trạng thái → nếu hợp lệ dùng `(query_raw−saved_mean)/saved_std` → Euclid/Top-5 → lưu CSV, preview, vector query và hash stats được dùng. Không gọi fit lại mean/std hoặc L1 lại sau Z-score. Query/kho/ảnh/mask đầu vào không bị ghi đè.

## 7. Artifacts, phạm vi và khả năng kết hợp sau này

File chính trong phiên bản mới: `schema.json`, `feature_layout.csv`, `manifest.csv`, `feature_rows.csv`, `missing_features.csv`, `fit_manifest.csv`, hai ma trận `.npy`, `normalization_stats.npz`, `model_info.json`, `summary.json`, `gallery_integrity.json`, `feature_distribution.csv`, `feature_outliers.csv`, `review_candidates.csv`, `retrieval/`, `review/`, `query_checks/`, `validation/`, `source_snapshot/`, `provenance/` và `artifact_manifest.csv` chứa hash artifacts.

Hồ sơ `validation/session_scope.json` đối chiếu hash 14.439 file tồn tại trước nhiệm vụ: chỉ hai tài liệu được yêu cầu cập nhật thay đổi trong tập file cũ. Thuật toán descriptor/standardizer/search trial, UniFace, A/C1/C2, annotations, toàn bộ dataset và mọi kết quả thử nghiệm trước đây giữ nguyên. Mã mới, tests mới, báo cáo cuối và output phiên bản mới được liệt kê riêng; không ghi đè dữ liệu nguồn. Bản PDF giữ nguyên hash.

B144 có thể ghép logic với A150, C1=236 và C2=324 theo **image_id/a_row_index**, tổng thiết kế 854 chiều theo báo cáo. C1/C2 chưa được triển khai trong workspace hiện tại; nhiệm vụ này không tạo chúng hoặc chứng nhận A/C.

Khi triển khai kết hợp, giữ đúng §2.5.2–2.5.3: Euclid cho A/B/C2, Chi-square cho C1, median normalization `d_k/(m_k+ε)` trên tập cặp đại diện, rồi tổng có trọng số không âm và tổng trọng số bằng 1. Cần lưu median/weights và phiên bản thống kê từng bộ; không cộng trực tiếp các khoảng cách thô hoặc dùng stats B100. Với ảnh thiếu B như HF00209, có thể xác định tập giao đủ đặc trưng theo giao thức được chấp thuận; không tự điền B=0, gán dB=0 hoặc đổi trọng số để che dữ liệu thiếu. Chưa thực hiện fusion/A+B trong nhiệm vụ này.
