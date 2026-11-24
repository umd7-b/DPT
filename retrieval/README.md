# Retrieval

`search_geometry.py` giữ truy vấn mẫu `cfd_final_00144.png`, Euclidean float64, loại chính ảnh truy vấn theo đường dẫn, và np.argsort lấy Top-5. Không thêm fusion hoặc đổi ranking. Đọc dữ liệu A ở `outputs/A_geometry/features/`, ghi ảnh vào `outputs/retrieval/search_results/`.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -m retrieval.search_geometry
```

Chuẩn hóa riêng A nằm ở `features/A_geometry/src/normalize_features.py`. Lệnh A-only cũ trên giữ nguyên hành vi; thử nghiệm A+B bên dưới là module mới.

## Truy vấn thử A150 + B144

`search_ab.py` triển khai **cấu hình thử nghiệm hai bộ A+B, không phải fusion chính thức bốn bộ A/B/C1/C2**. Mặc định A=0.5, B=0.5. Không sửa code, vector hoặc tham số chuẩn hóa A/B; không fit lại Z-score.

Đã đọc trực tiếp §2.5, trang PDF 16–18 của `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Theo §2.5.2–2.5.3:

```text
dA = ||zA(query) - zA(candidate)||₂
dB = ||zB(query) - zB(candidate)||₂
mA = median{dA(i,j)}; mB = median{dB(i,j)} trên cùng tập cặp
normalized_A = dA / (mA + epsilon)
normalized_B = dB / (mB + epsilon)
D_AB = weight_a * normalized_A + weight_b * normalized_B
weight_a >= 0, weight_b >= 0, weight_a + weight_b = 1
```

`epsilon=1e-8` là quy ước số học của triển khai này; PDF có ε nhưng không chốt giá trị. Không dùng trung vị khoảng cách của riêng từng truy vấn. A chuẩn hóa hiện có float32, B float64; tính khoảng cách bằng float64 từ chính các vector đã lưu. Quy tắc Z-score A hiện có khác cách viết `sigma+epsilon` trong PDF; giữ nguyên theo yêu cầu tái sử dụng A và không thay pipeline.

### Ghép danh tính và tập so sánh

- A: `outputs/A_geometry/features/features_A_normalized.npy` + `metadata.csv` (1.438 × 150).
- B: `outputs/B_color/color_features_full_v1/features_B_normalized.npy` + `feature_rows.csv` (1.437 × 144), kiểm tra SHA-256 theo `gallery_integrity.json` và schema B144 v1.
- Ghép bằng `image_id` (A hiện dùng stem tên ảnh), đối chiếu `a_row_index`; lấy hàng vector B bằng `feature_row_index`. Không ghép A/B theo vị trí hàng. Kiểm tra ID trùng, chỉ số sai, tên ảnh mâu thuẫn và NaN/Inf.
- Cả A+B, A-only và B-only dùng **cùng 1.437 ảnh đủ A/B**, loại self-match theo danh tính; hòa khoảng cách theo tên ảnh. A-only xếp bằng `normalized_A`, B-only bằng `normalized_B`; cùng thứ tự với Euclid thô của từng bộ.
- `hf_merged_00209.png` thiếu B do `hair:missing_empty(0<100)`: loại khỏi tập ứng viên của cả ba cách. Nếu truy vấn ảnh thiếu B, trả A-only; A+B/B-only rỗng, `status=missing_B`, khoảng cách B/tổng là `null` trong JSON, ô trống trong CSV. Không zero-fill hoặc tự đổi trọng số. Đây là trạng thái dữ liệu được xử lý, CLI kết thúc mã 0; đầu vào/tham số lỗi kết thúc mã 2.

### Median tái lập

Sắp 1.437 ID chung, lấy mẫu đều không hoàn lại **20.000 cặp không thứ tự, không tự ghép**, `random.Random(42)`, từ 1.031.766 cặp có thể có. Cặp được chọn độc lập với truy vấn, trọng số và kết quả Top-5. Lựa chọn mẫu đều và seed là quy ước triển khai, PDF không chỉ định thuật toán chọn mẫu.

Lưu tại `outputs/retrieval/ab_experiment/calibration/`:

- `representative_pairs.csv`: hai ID và hai khoảng cách Euclid cho từng cặp, có thể tính lại trung vị độc lập.
- `median_params.json`: hai median, ε, seed, số cặp, danh sách ID, số cặp theo nguồn CFD/HF, hash bảng cặp và hash vector/metadata/stats nguồn.

Lần sau đọc lại tham số, kiểm tra hash nguồn và bảng cặp, đối chiếu median với khoảng cách đã lưu. Nếu kho hoặc tham số thay đổi, báo calibration cũ; dùng một `--calibration-dir` mới trong `outputs/retrieval/` để tạo phiên bản mới. Không âm thầm fit lại khi truy vấn.

### CLI và kết quả

Chạy từ `D:\TuNam4\portrait-retrieval` trong PowerShell:

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
```

`--image` nhận tên ảnh có sẵn hoặc đường dẫn ảnh. Có thể gọi trực tiếp `retrieval/search_ab.py`; truy vấn vector đã lưu cũng chạy được bằng `.venv311`, không import MediaPipe/UniFace. Trọng số phải không âm, hữu hạn, tổng bằng 1; không tự sửa trọng số người dùng nhập.

Kết quả ở `outputs/retrieval/ab_experiment/queries/<query_stem>/`:

- `ab_top5.csv`, `a_only_top5.csv`, `b_only_top5.csv`: tên/ID ảnh, dA/dB thô, hai khoảng cách chuẩn hóa, D_AB và `score` dùng xếp hạng của từng chế độ. Số trong tên file theo `--top-k`.
- `comparison_top5.png`: ba hàng ảnh truy vấn và Top-5, có tên ảnh, khoảng cách và điểm xếp hạng.
- `results.json`: toàn bộ kết quả, trọng số, trạng thái, lý do thiếu B, danh tính self-match đã loại, hash kho và đường dẫn tham số. Chạy lại cùng stem ghi lại kết quả truy vấn; calibration dùng lại.

`--output` và `--calibration-dir` chỉ được trỏ vào thư mục con của `outputs/retrieval/`, bảo vệ code/vector A/B hiện có.

### Ảnh mới và hai môi trường

Ảnh truy vấn khớp SHA-256 với ảnh kho dùng vector đã lưu, kể cả bản sao đổi tên; không chỉ dựa vào tên file. Với ảnh mới, `ab_query_worker.py` gọi đúng hàm hiện có bằng subprocess riêng:

1. `.venv311\Scripts\python.exe`: `extract_geometry`, rồi dùng `geometry_stats.npz` hiện có để chuẩn hóa A150.
2. `.venv-uniface\Scripts\python.exe`: UniFace với model cục bộ đã kiểm hash (cấm tải model), mask **raw** class 1/17, `extract_color(min_pixels=100)`, rồi `transform` với `normalization_stats.npz` B hiện có. Không dùng mask erosion để tính B.

Ảnh mới phải là chân dung đã căn chỉnh 256×256, BGR uint8 như đầu vào B hiện có. Không cài thư viện, không trộn site-packages, không sửa pipeline. Trung gian truyền qua file `.npy` trong thư mục tạm; vector truy vấn mới được lưu ở thư mục kết quả retrieval. Nếu thiếu vùng da/tóc, B trả trạng thái thiếu và A-only vẫn có thể chạy.

Tùy chọn `--python-a`/`--python-b` chỉ định interpreter có sẵn. Nếu có mask raw phù hợp, truyền đồng thời `--skin-mask` và `--hair-mask` để bỏ bước parsing; người gọi chịu trách nhiệm cung cấp mask đúng ảnh và ngữ nghĩa. Ảnh mã hóa lại có byte khác được xem là ảnh mới; không phát hiện trùng theo nội dung pixel.

## Kiểm thử và lần chạy thực tế 23/11/2026

Các lệnh sau đã chạy thành công trong PowerShell tại repository root (mã thoát 0):

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_search_ab.py -v
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_search_ab.py -v
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_ab.py --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab --image hf_merged_00209.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m retrieval.search_ab --image outputs/retrieval/ab_validation/new_query.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_color_search.py -v
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_color_full.py -v
.\.venv-uniface\Scripts\python.exe -X utf8 -B outputs/retrieval/ab_validation/validate_run.py
```

17 unit tests đạt trên cả hai môi trường: ghép ID khi thiếu hàng giữa và đảo thứ tự metadata B, median bằng nghiệm tay trên cùng tập cặp, mẫu tái lập/không trùng/không tự ghép, cache cũ/bị sửa, Euclid và công thức có ε, trọng số, self-match, tie-break, top-k, thiếu B và đúng interpreter.

`new_query.png` là fixture mã hóa PNG lại từ `cfd_final_00001.png`: pixel giải mã giữ nguyên nhưng hash byte khác, buộc chạy cả hai extractor thật. Nhánh này đã dùng `.venv311` cho A và `.venv-uniface` cho B, không cài thêm gì; metadata `query_info.source=separate_environment_workers`. Do khác byte, fixture được xem là ảnh mới và ảnh gốc có thể xuất hiện trong kết quả; truy vấn chính tên ảnh kho đã loại self-match đúng.

Median thực tế: **mA=16.441995193**, **mB=10.814300552**, lần đầu `calibration_reused=false`, các lần sau `true`.

Top-5 A+B cho `cfd_final_00001.png`:

| Hạng | Ảnh | dA Euclid | dB Euclid | D_AB |
|---:|---|---:|---:|---:|
| 1 | cfd_final_00038.png | 11.311273 | 6.985327 | 0.666942 |
| 2 | cfd_final_00029.png | 11.740421 | 7.282025 | 0.693710 |
| 3 | cfd_final_00036.png | 13.375915 | 7.631354 | 0.759597 |
| 4 | cfd_final_00044.png | 12.408391 | 8.268706 | 0.759643 |
| 5 | cfd_final_00031.png | 13.513434 | 7.854466 | 0.774094 |

A-only: `hf_merged_00136`, `cfd_final_00336`, `cfd_final_00382`, `cfd_final_00312`, `cfd_final_00502`. B-only: `cfd_final_00439`, `cfd_final_00038`, `cfd_final_00029`, `cfd_final_00440`, `cfd_final_00036`. Bảng CSV/JSON có đầy đủ khoảng cách; ảnh so sánh có cả ba hàng.

Hồ sơ kiểm chứng ở `outputs/retrieval/ab_validation/`: hash 97 file code/artifact A/B chụp trước triển khai, log và `validation_summary.json`. Đối chiếu SHA-256 sau chạy xác nhận **0 file A/B thay đổi**. Script `validate_run.py` tính lại độc lập từ vector gốc: hai median và toàn bộ khoảng cách/thứ hạng của ba bảng khớp chính xác; cache được tái sử dụng. Sai số tối đa của A trích xuất lại so với vector float32 đã lưu là `1.1765232e-7`; B bằng `0`. Regression B hiện có: `test_color_search.py` 2 tests và `test_color_full.py` 8 tests đều đạt. Các thứ hạng này là kết quả thử nghiệm số học; chưa có nhãn relevance để kết luận chất lượng truy hồi.
