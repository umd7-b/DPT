# Kiểm toán tuân thủ báo cáo — Portrait Retrieval

Ngày kiểm toán: **22/11/2026**. Phạm vi sửa mã: **Bộ B**. Đã đọc toàn bộ 18 trang PDF, gồm mục 2.2, 2.3, 2.4 và 2.5; không cấp chứng nhận tuân thủ cho A/C1/C2 chỉ từ lần kiểm toán B này.

**Kết luận: chưa thể xác nhận toàn bộ pipeline tuân thủ 100%.** Các yêu cầu rõ về kích thước B144, histogram H–S 12×4, histogram Hue 10 bin, L1, phép chiếu góc và Euclid được đáp ứng. Các công thức Pearson kurtosis, circular std có scale/clipping, ánh xạ vùng da, erosion và một số chi tiết chuẩn hóa vẫn cần nhóm xác nhận. Tests đạt chỉ xác nhận tính đúng của phần được kiểm tra, không biến lựa chọn của Agent thành định nghĩa của báo cáo.

## 1. Tài liệu chuẩn và bằng chứng

Chỉ sử dụng bản người dùng đã chỉ định: [csdldpt.pdf](/C:/Users/USER/Downloads/csdldpt.pdf), 5.324.823 byte, 18 trang. Trang bìa ghi báo cáo môn Hệ cơ sở dữ liệu đa phương tiện, lớp 03, nhóm 06, Hà Nội 2026. SHA-256:

```text
8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80
```

Hash khớp `SCHEMA`, `summary.json` và bản báo cáo đã dùng khi trích tập thử. Không tìm thấy PDF khác trong workspace; không ghép nội dung nhiều phiên bản. Đây là xác nhận **đúng file người dùng chỉ định**, không phải suy đoán phiên bản chính thức từ tên file hoặc ngày sửa.

Đã trích lại nội dung trực tiếp từ file PDF hiện tại bằng parser ToUnicode có sẵn, kiểm tra thứ tự trang với cây `/Pages`: đủ 18 trang, thứ tự khớp bản trích. Tất cả số trang dưới đây là **trang PDF đếm từ 1**, không dùng số trang trong mục lục vì phân trang mục lục không trùng vị trí trang PDF.

Bằng chứng được lưu riêng tại [outputs/B_color/report_compliance_audit](../outputs/B_color/report_compliance_audit/): `source_provenance.json`, `report_text.txt`, `report_pages.json`, `protected_before.json`, `artifact_checks/artifact_validation.json`, `unit_tests.log`, `scope_validation.json` và `configuration_status.json`. Bản trích là bằng chứng đọc tài liệu, không thay thế hoặc sửa PDF gốc.

Tài liệu `B_color_feature_spec.md`, `SCHEMA`, README và các REPORT cũ là **mô tả triển khai**, không có quyền bổ sung công thức vào báo cáo nhóm. Nguồn kiểm chứng code là file hiện tại và snapshot/hash của trial; không dùng kiến thức bên ngoài để thay định nghĩa.

## 2. Cách phân loại

| Trạng thái | Ý nghĩa trong kiểm toán này |
|---|---|
| EXACT | Yêu cầu được báo cáo nêu rõ và phần code tương ứng khớp. Không mở rộng kết luận sang chi tiết chưa được báo cáo quy định. |
| IMPLEMENTATION DETAIL | Lựa chọn hiện thực đang có, nhưng báo cáo không định nghĩa đủ để gọi công thức đó là EXACT. Cần nhóm xác nhận trước khi chốt cấu hình chính thức. |
| DEVIATION | Có khác biệt cụ thể so với yêu cầu được nêu rõ. Ghi cả phạm vi ảnh hưởng và việc đã chặn/sửa hay còn tồn tại trong nhánh nghiên cứu. |
| UNVERIFIED | Chưa đủ bằng chứng, còn mâu thuẫn/cách hiểu chưa chốt hoặc ngoài phạm vi kiểm toán chi tiết. Không suy ra là đúng hay sai. |

Mỗi hàng chỉ chứng nhận phạm vi ghi trong hàng đó. Ví dụ, đúng tên bốn mô-men không đồng nghĩa công thức Pearson kurtosis đã được báo cáo quy định.

## 3. Bảng đối chiếu

Tên file dưới đây nằm trong `features/B_color/src/`, trừ nơi ghi khác. Các trích dẫn ngắn được đối chiếu với đúng PDF ở mục 1.

| Mục báo cáo | Trích dẫn trang | File/hàm code | Trạng thái | Sai lệch | Hướng xử lý |
|---|---|---|---|---|---|
| B01 — hai vùng, ba nhóm, 72/vùng, 144 tổng | §2.3, PDF 11–12: “72 × 2 = 144”; §2.5.1, PDF 16 | `color_features.py::region_descriptor`, `extract_color` | EXACT | Không thấy sai kích thước; 48+12+12 cho mỗi vùng. | Giữ nguyên; kiểm tra shape bằng fixture độc lập và cả 300 vector đã lưu. |
| B02 — B1 dùng HSV, H và S, không dùng V trong histogram | §2.3.1, PDF 12: “hai kênh H và S” | `color_features.py::region_descriptor` | EXACT | Chọn đúng H/S sau chuyển màu. | Giữ nguyên; test màu đỏ/xanh phát hiện đảo RGB/BGR. |
| B03 — 12 Hue × 4 Saturation, 48 bin/vùng | §2.3.1, PDF 12: “12 × 4 = 48 chiều” | `color_features.py::region_descriptor` | EXACT | Không phát hiện sai số bins. | Giữ nguyên; test 48 ô với khối lượng khác nhau. |
| B04 — L1 histogram H–S | §2.3.1, PDF 12: `h'_k = h_k / ∑ h_i` | `color_features.py::region_descriptor` | EXACT | Code chia tổng đếm của chính histogram. | Giữ nguyên; tổng bằng 1 trước Z-score. |
| B05 — biên bin và lượng tử hóa B1 | §2.3.1, PDF 12: không liệt kê biên bin | `color_features.py::SCHEMA`, `region_descriptor` | IMPLEMENTATION DETAIL | Đang dùng H `[0,180)`, S `[0,256)`, các bin đều, OpenCV uint8 HSV. Không phải toàn bộ tham số đều được PDF chốt. | Công khai lựa chọn; nhóm xác nhận. Không tự đổi `[0,256)` sang miền khác. |
| B06 — thứ tự flatten HS | §2.3, PDF 11–13: không định nghĩa serialization | `color_features.py::feature_names`, `region_descriptor` | IMPLEMENTATION DETAIL | Hue ngoài, Saturation trong, C-order là quy ước code. | Giữ thứ tự đã dùng để không làm sai vector/query; nhóm xác nhận. |
| B07 — B2 CIE-Lab, bốn loại thống kê trên ba kênh, 12/vùng | §2.3.2, PDF 12: “Mean, Std, Skewness, Kurtosis”, L*, a*, b* | `color_features.py::region_descriptor` | EXACT | Đúng không gian màu, loại thống kê và số thành phần. Không chứng nhận công thức mô-men ở hàng này. | Giữ cấu trúc; xem B08–B12 cho công thức số học. |
| B08 — biểu diễn số CIE-Lab | §2.3.2, PDF 12: không chỉ định thư viện/kiểu số/white point | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | OpenCV float32 BGR/255 → Lab; L* khoảng 0–100, a*/b* có dấu; thống kê float64. | Ghi rõ phiên bản thư viện và quy ước, cần nhóm xác nhận; không chuyển ngầm sang Lab uint8. |
| B09 — mean | §2.3.2, PDF 12: nêu trung bình μ, không có phương trình hoặc trọng số | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | Đang dùng trung bình số học không trọng số trên pixel mask. | Test giá trị giải tích; không nói PDF đã cung cấp phương trình này. |
| B10 — std và skewness | §2.3.2, PDF 12: không ghi mẫu/quần thể, bias hoặc ddof | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | `sqrt(m2)` với ddof=0; skew=`m3/m2^(3/2)`, không hiệu chỉnh bias. | Giữ nguyên lựa chọn hiện tại, chờ nhóm chốt; không thay bằng thư viện có mặc định khác. |
| B11 — kurtosis | §2.3.2, PDF 12: chỉ nêu “kurtosis” | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | Đang dùng Pearson `m4/m2²`, không trừ 3. Không có căn cứ gọi Pearson hoặc excess là lựa chọn chính thức của PDF. | Cần nhóm xác nhận Pearson/excess và bias; tests chỉ xác nhận công thức đang dùng. |
| B12 — mô-men khi kênh hằng | §2.3.2, PDF 12: không quy định trường hợp suy biến | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | std<1e-12 → std/skew/kurt=0 kèm warning; skew/kurt kênh hằng vốn không xác định. | Giữ cờ chẩn đoán; cần nhóm chốt fallback. Không gọi số 0 này là mô-men được PDF định nghĩa. |
| B13 — B3 10-bin Hue + hai thống kê vòng, 12/vùng | §2.3.3, PDF 13: “histogram 10 bin” và Circular Mean/Std | `color_features.py::region_descriptor` | EXACT | Đúng 10+1+1; không tăng số bin. | Giữ nguyên 10; không sửa theo câu mô tả “chi tiết hơn” 12-bin của B1. |
| B14 — miền Hue và L1 B3 | §2.3.3, PDF 13: “miền OpenCV từ 0 đến 180, chuẩn hóa L1” | `color_features.py::region_descriptor` | EXACT | Đúng miền quy ước OpenCV và chia tổng đếm. H uint8 thực tế 0–179 được bao phủ. | Giữ nguyên, test H=0 và H=179. |
| B15 — biên đều của 10 bin Hue | §2.3.3, PDF 13: không liệt kê cạnh bin | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | Code dùng cạnh 0,18,…,180. | Nhóm xác nhận biên; không tự thay đổi. |
| B16 — phép chiếu Hue sang góc | §2.3.3, PDF 13: `φ_i = 2π·h_i / 180` | `color_features.py::hue_statistics` | EXACT | Code nhân H với `2*pi/180`. | Test nghiệm giải tích hai góc và trường hợp qua mép vòng. |
| B17 — hai thống kê vòng thuộc [0,1] | §2.3.3, PDF 13: “chuẩn hóa về miền [0, 1]” | `color_features.py::hue_statistics` | EXACT | Miền giá trị được đáp ứng. Đây chỉ là chứng nhận miền, không chứng nhận công thức scale. | Kiểm tra miền trên 300 vector; xem B18–B20. |
| B18 — công thức circular mean cụ thể | §2.3.3, PDF 13: không ghi atan2/modulo/cách scale | `color_features.py::hue_statistics` | IMPLEMENTATION DETAIL | Mean hướng resultant, modulo 2π rồi chia 2π; có xử lý sai số tại mép vòng. | Công khai công thức; nhóm xác nhận. Không thay thành mean số học hay thêm sin/cos vào vector. |
| B19 — circular standard deviation cụ thể | §2.3.3, PDF 13: không ghi công thức hoặc mẫu số scale | `color_features.py::hue_statistics` | IMPLEMENTATION DETAIL | `min(sqrt(-2*log(max(R,1e-12)))/(2*pi),1)`. Phép chia 2π, log-floor và clip không được PDF quy định. | Cần nhóm chốt; tuyệt đối không đánh EXACT chỉ vì tên “circular std” và miền khớp. |
| B20 — resultant gần 0 | §2.3.3, PDF 13: không quy định suy biến | `color_features.py::hue_statistics` | IMPLEMENTATION DETAIL | R<1e-8 → mean=0 cùng warning; std chịu log-floor/clip. | Giữ cảnh báo; chờ nhóm xác nhận ngưỡng/fallback. |
| B21 — pixel ít bão hòa | §2.3.1/2.3.3, PDF 12–13: không chỉ định loại pixel theo S | `color_features.py::region_descriptor` | IMPLEMENTATION DETAIL | Vẫn tính toàn bộ pixel trong mask; chỉ cảnh báo nếu >50% có S<10. Không đổi histogram hoặc trọng số vì cờ này. | Giữ cờ phụ trợ; không coi là tiêu chí học thuật đã được hiệu chuẩn. |
| B22 — chỉ tính trên vùng da/tóc, không cộng nền ngoài mask | §2.3, PDF 11; §2.3.1, PDF 12: vùng quan tâm hợp lệ | `color_features.py::region_descriptor`, `extract_color` | EXACT | `image[mask>0]`; không tính nền đen của preview. Pixel đen thật trong mask vẫn được đếm. | Giữ; kiểm tra thay pixel ngoài mask và tính bất biến đầu vào. |
| B23 — skin=1, hair=17 | §2.3, PDF 11–13: không nêu UniFace hoặc class ID | `batch_uniface.py::make_masks` | IMPLEMENTATION DETAIL | Ánh xạ đúng nhãn cài sẵn UniFace, nhưng không phải định nghĩa vùng da do báo cáo cung cấp. Skin=1 không gồm nose=10, ear, neck. | Giữ nguyên raw đã lưu; nhóm xác nhận ROI giải phẫu chính thức. |
| B24 — Skin + Nose | §2.3, PDF 11–13: không nêu phép gộp lớp | `run_color_experiment.py::build_nose_masks` | IMPLEMENTATION DETAIL | Union lớp 1 và 10 thay đổi tập pixel so với raw. C dùng class map thật đã lưu, không suy từ mask nhị phân. | Giữ thí nghiệm C riêng; không tự chọn làm cấu hình chính thức. |
| B25 — erosion | §2.3, PDF 11–13: không có erosion trong mô tả | `batch_uniface.py::make_masks` | IMPLEMENTATION DETAIL | Clean là erosion 3×3 một lần, làm đổi ROI và phân bố màu. Không có quy định rõ bắt buộc/cấm erosion để kết luận đây là công thức EXACT hay một DEVIATION đã chứng minh. | Giữ raw/clean riêng; chưa phê duyệt clean, không gọi mặc nhiên tốt hơn. |
| B26 — ROI dự đoán có đúng vùng giải phẫu hay không | §2.3, PDF 11: hai vùng giải phẫu tách biệt | `make_masks`, mask/class map và dữ liệu đầu vào | UNVERIFIED | Đúng class ID, nhị phân, không chồng lấn hoặc hash không chứng minh mask đúng về ngữ nghĩa; chưa có GT độc lập đủ cho 100 ảnh. | Nhóm chốt ROI và duyệt/đánh giá nhãn độc lập; không dùng skin_masks template làm GT. |
| B27 — thiếu vùng, ngưỡng 100 pixel | §2.3.1, PDF 12: “vùng quan tâm hợp lệ”, không cho ngưỡng | `color_features.py::region_descriptor`, `extract_color` | IMPLEMENTATION DETAIL | 0 → missing_empty; 1–99 → insufficient_pixels; trả vector=None, không zero-fill. Nhị phân uint8 0/255 và cấm overlap là kiểm tra kỹ thuật. | Nhóm xác nhận ngưỡng/chính sách; ghi trạng thái riêng, không thêm chiều mới vào B144. |
| B28 — thứ tự ghép B144 | §2.3, PDF 11–13: có nhóm thành phần nhưng không chốt index serialization | `color_features.py::feature_names`, `extract_color` | IMPLEMENTATION DETAIL | Skin72 rồi Hair72; mỗi vùng HS48/Lab12/Hue10/mean/std. Lab theo từng kênh, mỗi kênh mean/std/skew/kurt. | Giữ đồng bộ kho/query; thứ tự được đóng băng bằng tests, vẫn cần nhóm xác nhận. |
| B29 — Z-score cuối trên toàn bộ 144 chiều | §2.3.3, PDF 13: “Z-score theo từng chiều … trên 144 chiều” | `color_features.py::fit_standardizer`, `transform`; `run_color_experiment.py::run` | EXACT | Profile all144 đáp ứng phạm vi chuẩn hóa cuối; người dùng đã xác nhận lựa chọn này. Hàng này không chứng nhận ddof/epsilon hoặc trình tự bước mô-men trước ghép. | Giữ all144; runner hiện từ chối profile khác trước mọi ghi file/inference. |
| B30 — trình tự chuẩn hóa mô-men trước ghép và Z-score sau ghép | §2.3.3, PDF 13; §2.5.2, PDF 17: mô-men chuẩn hóa theo kho trước ghép | `region_descriptor`, `fit_standardizer`, `run` | UNVERIFIED | Code lưu mô-men chưa scale trong descriptor, thực hiện một lần Z-score sau ghép. PDF diễn đạt thêm bước mô-men trước ghép nhưng không cho công thức chi tiết; xác nhận all144 chưa giải quyết duy nhất trình tự này. | Ghi rõ, không tự thêm lần scale thứ hai hoặc tuyên bố hai cách luôn tương đương; nhóm chốt cách hiểu và xử lý suy biến. |
| B31 — công thức số học Z-score | §2.3.3, PDF 13; §2.5.2, PDF 17: phương trình có ε viết riêng cho A, không chốt ε/ddof cho B | `color_features.py::fit_standardizer`, `transform` | IMPLEMENTATION DETAIL | B đang dùng ddof=0, std<1e-8 → divisor=1; còn lại chia std, không cộng ε cho mọi chiều. Không được lấy phương trình A rồi tự coi đó là B đã được chốt. | Kiểm chứng số học độc lập; nhóm xác nhận chính sách B. Không đổi mặc định trong audit. |
| B32 — reuse thống kê kho cho query | §2.3.3, PDF 13: tham số kho; §2.5.2, PDF 17: query dùng lại tham số kho | `color_features.py::transform`; `evaluate_color_retrieval.py::run` | EXACT | Query all144 dùng đúng mean/std của phương án tương ứng, không fit theo từng query/cặp. | Test query ngoài kho bằng nghiệm tính tay và kiểm tra stats bất biến. |
| B33 — phạm vi thống kê hiện có | §2.1, PDF 7; §2.3.3, PDF 13: thống kê kho | `run_color_experiment.py::run`, trial summary | IMPLEMENTATION DETAIL | Hiện fit trên kho thử 100 ảnh, tách riêng ba phương án; không phải mean/std của 1.438 ảnh. | Giữ dữ liệu là thí nghiệm 100 ảnh; không tái dùng stats100 để tuyên bố đã chuẩn hóa toàn kho. |
| B34 — tùy chọn moments_only | So với §2.3.3, PDF 13: yêu cầu cuối trên cả 144 chiều | `color_features.py::fit_standardizer(profile='moments_only')`; CLI/hàm `run_color_experiment.py` trước sửa | DEVIATION | Chỉ scale 24 mô-men, bỏ Z-score histogram/thống kê vòng. Đây là sai khác so với bước cuối được §2.3.3 nêu rõ, dù §2.5.2 có cách diễn đạt khác. Không có kết quả hiện tại dùng profile này. | **Đã chặn ở CLI và hàm run**. Helper nghiên cứu cũ giữ riêng, không được dùng như cấu hình báo cáo; không xóa/đổi kết quả lịch sử. |
| B35 — Euclid trên B144 | §2.3.3, PDF 13; §2.5.2, PDF 17: Euclid cho B | `search_color.py::top5` | EXACT | L2 đủ 144 tọa độ, có căn bậc hai; không thay bằng cosine/Chi-square hoặc thêm trọng số block. | Test tam giác 3–4–5 và nhiều tọa độ; kiểm tra độc lập 150 khoảng cách/thứ hạng đã lưu. |
| B36 — tự khớp và hòa khoảng cách | §2.5.3, PDF 17–18: tăng dần; không quy định self-match/tie-break | `search_color.py::top5` | IMPLEMENTATION DETAIL | Loại query theo tên; hòa khoảng cách xử lý theo tên file. | Giữ quy ước hiện tại và thứ hạng cũ, công khai chi tiết. |
| X01 — A150 | §2.2, PDF 8–11: 68×2 + 14; `p'_i=(p_i-c)/d`; §2.5.2 PDF 17 | `features/A_geometry/src/geometry_features.py`, `normalize_features.py`; `retrieval/search_geometry.py` | UNVERIFIED | Đã đọc để hiểu giao diện và quy định chuẩn; chưa kiểm toán đầy đủ từng tỉ lệ, mốc và epsilon của A trong nhiệm vụ B này. | Không sửa/chạy lại A; không suy ra A tuân thủ 100% từ shape hoặc kiểm tra B. |
| X02 — C1/C2 | §2.4, PDF 13–16: C1=236, C2=324; tổng 560 | `features/C1_lbp/README.md`, `features/C2_hog/README.md`, các package marker | UNVERIFIED | Workspace hiện chưa có thuật toán C1/C2 để đối chiếu. Không thể chứng nhận bằng tên thư mục. | Ghi tình trạng chưa triển khai, không thêm hay sửa C1/C2 trong audit B. |
| X03 — median normalization và fusion | §2.5.2–2.5.3, PDF 17–18: `d_k/(m_k+ε)`, tổng có trọng số, tổng w=1 | `search_color.py` là B-only; `retrieval/` hiện là A-only | UNVERIFIED | Chưa có fusion bốn bộ để đối chiếu công thức. B-only dùng dB không đồng nghĩa đã thực hiện D tổng hợp. | Không cài thêm fusion, không tự chọn median/weights; cần nhiệm vụ riêng. |
| X04 — điều kiện một người và không che khuất | §1.2–1.3, PDF 5; điều kiện nền tảng cho §2.1–2.4 | metadata, source images và các ghi chú review đã có | UNVERIFIED | Chưa xác nhận toàn bộ tiêu chí dữ liệu bằng kiểm toán này; mask hợp lệ về định dạng không chứng minh ảnh đáp ứng điều kiện báo cáo. | Giữ ghi chú review; không tự loại ảnh hoặc làm lại dataset/ranking. |

## 4. Công thức đang dùng và giới hạn của kết luận

### B1, B3 và thứ tự hiện tại

Các yêu cầu rõ được giữ nguyên:

```text
B1(region) = L1(histogram2d(H,S; 12×4))              : 48
B2(region) = 4 loại mô-men trên L*, a*, b*           : 12
B3(region) = L1(histogram(H; 10)) + mean/std vòng    : 12
B(region)                                               72
B(skin) + B(hair)                                      144
phi_i = 2*pi*H_i/180
d_B(q,i) = sqrt(sum_j=1..144 (z_qj-z_ij)^2)
```

Code chỉ dùng pixel ảnh gốc trong mask. Các histogram có tổng 1 **ở descriptor trước Z-score**; sau Z-score all144, histogram có thể có phần tử âm và tổng không còn bằng 1. Không được “sửa” bằng cách L1 lại sau Z-score vì sẽ thay phép biến đổi đã chọn.

Thứ tự **đang dùng**, không phải thứ tự được PDF định nghĩa đầy đủ:

| Index 0-based | Nội dung |
|---|---|
| 0–47 / 72–119 | skin/hair HS48, Hue ngoài và Saturation trong |
| 48–59 / 120–131 | skin/hair Lab12: L rồi a rồi b; mỗi kênh mean/std/skew/kurt |
| 60–69 / 132–141 | skin/hair Hue10 |
| 70–71 / 142–143 | skin/hair circular mean và circular std |

### Mô-men và thống kê vòng

Với `m_k = mean((x-mean(x))^k)`, lựa chọn hiện tại là std=`sqrt(m2)`, skew=`m3/m2^(3/2)`, Pearson kurtosis=`m4/m2²`. PDF không cho đủ công thức để xác nhận các lựa chọn ddof, bias, Pearson/excess. Tests với phân bố `{0,0,0,4}` có oracle giải tích: mean=1, variance=3, skew=2/√3, Pearson=7/3, excess=−2/3. Phép test này phân biệt hai loại kurtosis nhưng không quyết định thay nhóm loại nào là chính thức.

Circular mean hiện tại dùng hướng của resultant; `R=hypot(mean(cos(phi)),mean(sin(phi)))`; circular std dùng `min(sqrt(-2*log(max(R,1e-12)))/(2*pi),1)`. PDF quy định góc và miền [0,1], **không quy định đủ biểu thức std**. Không suy ra phép chia 2π, epsilon hoặc clipping là yêu cầu của nhóm.

Ảnh hưởng cần lưu ý: Pearson/excess khác một hằng số ở các kênh không suy biến; Z-score nhất quán có thể triệt tiêu dịch hằng đó. Tương tự, một hệ số scale dương có thể bị Z-score triệt tiêu khi không có clipping/floor. Vì vậy không được khẳng định những lựa chọn này luôn làm ranking đổi; fallback, clipping hoặc xử lý kênh suy biến có thể phá tính tương đương. Dù ranking trùng, vấn đề xác nhận công thức học thuật vẫn còn.

Circular mean được lưu như một số trên [0,1]; Euclid trên scalar vẫn có mép vòng. Báo cáo yêu cầu biểu diễn này và Euclid, nên audit không tự thay bằng metric vòng, sin/cos hoặc tăng số chiều.

### Mask và cấu hình chính thức

Nguồn class ID được kiểm tra từ **gói UniFace đang cài**: `.venv-uniface/Lib/site-packages/uniface/draw.py::FACE_PARSING_LABELS` ghi skin=1, nose=10, hair=17. Đây là bằng chứng về ngữ nghĩa nhãn của thư viện, không phải bằng chứng báo cáo nhóm yêu cầu nhãn đó. Không tải mô hình hoặc chạy inference để kiểm toán.

Raw, clean và skin+nose là ba tập pixel khác nhau. Tên thí nghiệm C trên đĩa là `C_skin1or10_hair17_raw`; không liên quan Bộ C1/C2. Erosion không làm đổi số chiều hoặc số bin nhưng có thể làm đổi phân bố màu và gây thiếu vùng. Chưa có cơ sở gọi raw, clean hay union là ROI chính thức của báo cáo; cũng chưa có căn cứ từ PDF để gọi mọi thao tác không được nhắc đến là một công thức bị cấm. Do đó các lựa chọn này là IMPLEMENTATION DETAIL, độ đúng ngữ nghĩa ROI là UNVERIFIED.

Tất cả kết quả hiện tại vẫn là **thí nghiệm** trong `outputs/B_color/color_features_100/` và `color_evaluation_10/`, không được di chuyển hoặc gắn lại nhãn “official”. `configuration_status.json` ghi `official_configuration=null` và danh sách quyết định còn mở. Không tạo cấu hình chính thức mới khi còn thiếu xác nhận.

### Z-score và phạm vi quyết định đã có

Người dùng đã xác nhận all144 trong hội thoại. Quyết định đó chọn bước chuẩn hóa cuối theo §2.3.3, không xác nhận thay nhóm Pearson kurtosis, circular std, erosion hoặc ROI.

Code hiện chỉ scale một lần sau ghép. §2.3.3 còn diễn đạt mô-men chuẩn hóa theo kho trước ghép, trong khi §2.5.2 không nhắc lại rõ bước cuối trên histogram/thống kê vòng. Với hai phép chuẩn hóa affine đồng nhất, std dương và không có epsilon/fallback, một bước scale mô-men trước có thể bị Z-score cuối triệt tiêu. Nhưng PDF chưa quy định các trường hợp biên, nên audit **không khẳng định hai trình tự luôn tương đương** và không tự thêm/bỏ lần chuẩn hóa nào. Điểm này vẫn UNVERIFIED, cần nhóm chốt.

Không áp dụng máy móc `σ+ε` từ phương trình viết riêng cho A sang B. Hiện B dùng std quần thể ddof=0; divisor=1 nếu std<1e-8, còn lại divisor=std. Cột hằng có Z-score bằng 0 trên kho. Với query ngoài kho có giá trị khác ở cột hằng, chính sách hiện tại trả `(query-mean)/1`, không ép query về 0 hoặc tự loại chiều. Tests kiểm tra cả trường hợp này; chính sách vẫn cần nhóm xác nhận.

## 5. Kiểm thử và kiểm tra artifacts

Lệnh trong PowerShell từ project root:

```powershell
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p "test_color*.py" -v
.\.venv-uniface\Scripts\python.exe -X utf8 -B -m features.B_color.src.audit_report_artifacts --output outputs/B_color/report_compliance_audit_rerun
```

Thư mục audit artifacts phải mới/rỗng và nằm ngoài các thư mục đầu vào. Lệnh thứ hai chỉ đọc vector, mask, class map và ranking đã có; không gọi extractor, parser hoặc hàm ghi ranking.

**32/32 color tests đạt**, gồm 10 tests mới trong `tests/test_color_report_compliance.py`. Oracles độc lập gồm: 48 ô histogram có khối lượng định trước, phân bố Lab bất đối xứng có nghiệm giải tích, màu đỏ/xanh để xác nhận thứ tự kênh và region, nghiệm resultant của hai góc, Z-score tính tay trên kho ba hàng và query ngoài kho, khoảng cách nhiều tọa độ 3–4–5, giao thủ công lân cận 3×3, và từ chối `moments_only` trước tạo output/inference. Không tạo GT từ dự đoán.

`audit_report_artifacts.py` dùng `math.fsum` để tính lại mean/std và Euclid, không gọi `fit_standardizer`, `transform` hoặc `top5`. Erosion được đối chiếu bằng giao chín cửa sổ dịch, không lấy `cv2.erode` làm oracle của chính nó.

| Kiểm tra đọc artifacts hiện có | Kết quả |
|---|---|
| Manifest trial / evaluation giữ nguyên hash | 557 / 75 file được xác minh |
| Ma trận chưa scale và đã scale | 3 phương án, mỗi ma trận 100×144, hữu hạn |
| Histogram L1 trước Z-score | 1.200 histogram đạt |
| Nguồn ảnh khớp SHA-256 và thứ tự A | 100 ảnh; đủ đúng tập thử, đúng a_row_index |
| Mask đúng 256×256, uint8, chỉ 0/255 | 600 mask đạt trên tập thử |
| Class map hiện có, đối chiếu raw và union 1/10 | 100 class map đạt kiểm tra nhãn kỹ thuật |
| Erosion độc lập | 200 mask clean khớp quy ước hiện tại |
| Cột phương sai 0: Raw/Clean/Skin + Nose | 1 / 8 / 0; không xóa chiều |
| Sai số mean/std so với tổng vô hướng độc lập | ≤1.422e-14 / ≤1.777e-15 |
| Sai số Z-score với oracle vô hướng độc lập | ≤5.330e-15; tái tạo bằng stats lưu: đúng tuyệt đối |
| Khoảng cách và thứ tự Top-5 đã lưu | 150 dòng khớp; sai số d ≤3.553e-15 |
| Inference / vector mới được lưu / ranking mới được ghi | 0 / 0 / 0 |

Việc xác minh lại Top-5 chỉ kiểm tra file đã lưu; không thay thứ hạng hoặc tái xuất contact sheet. Đúng định dạng, hash và số học không chứng minh mask đúng hoặc kết quả tìm kiếm phù hợp. Không báo accuracy/IoU/Dice vì chưa có nhãn độc lập tương ứng.

## 6. Những thay đổi và kiểm soát phạm vi

Thay đổi hành vi duy nhất trong mã đang chạy: `run_color_experiment.py::run` từ chối mọi profile khác all144 **trước khi ghi file, đọc dữ liệu trial hay khởi tạo parser**; CLI chỉ chấp nhận `--normalization all144`. Mặc định all144 vốn đã có, không đặt một mặc định chuẩn hóa mới.

`color_features.py::fit_standardizer(..., 'moments_only')` vẫn tồn tại để giữ khả năng tái hiện nghiên cứu cũ; đây là helper **không tuân thủ bước cuối §2.3.3**, đã bị loại khỏi đường chạy trial bám báo cáo. Chưa xóa helper hoặc viết lại công thức thay thế theo suy đoán từ §2.5.2. Các output hiện tại đều ghi all144 nên bản sửa này không áp dụng thay đổi hồi tố lên vector/ranking.

Các file mới: tài liệu audit này, `features/B_color/src/audit_report_artifacts.py`, `tests/test_color_report_compliance.py` và bằng chứng dưới `outputs/B_color/report_compliance_audit/`.

Đã chụp hash 14.419 file tồn tại trước audit (không tính `__pycache__`), gồm source, tài liệu, output cũ, annotations, models, toàn bộ file dataset và PDF gốc. `scope_validation.json` liệt kê thay đổi được cho phép. Chỉ file runner B nêu trên thay đổi trong tập file cũ; `color_features.py`, `search_color.py`, các kết quả trích xuất/ranking/mask cũ, A/C1/C2 và dữ liệu nguồn giữ nguyên. Không chạy lại toàn dataset, không kết hợp A+B, không tải/cài gì và không sửa nội dung báo cáo nhóm.

## 7. Tổng kết bắt buộc

1. **Phần khớp 100% với yêu cầu được nêu rõ, trong phạm vi từng yêu cầu:** hai vùng ×72=144; B1 H–S 12×4 và L1; B2 gồm đúng bốn loại thống kê trên ba kênh CIE-Lab và đủ 12 chiều; B3 10-bin Hue L1 cộng hai thống kê vòng, phép chiếu `2πH/180` và miền [0,1]; lấy pixel trong ROI; bước cuối all144 đã chọn; dùng tham số kho và Euclid đủ 144 tọa độ. Không mở rộng chữ EXACT từ tên mô-men sang công thức chưa được PDF quy định.
2. **Phần code chưa khớp:** helper nghiên cứu `moments_only` bỏ Z-score trên 120 chiều, khác §2.3.3. Đã chặn khả năng chọn nó qua CLI/hàm runner bám báo cáo; helper vẫn mang trạng thái DEVIATION đối với yêu cầu đó và không được coi là cấu hình chính thức. Không phát hiện sai số bins/L1/dimension/Euclid trong cấu hình all144 đang kiểm tra. Trình tự chuẩn hóa mô-men chưa được xác minh đầy đủ, không tuyên bố đã khớp.
3. **Chỗ PDF chưa đủ chi tiết:** công thức/bias/ddof của mô-men, Pearson/excess, scale/clipping/suy biến circular std/mean, ROI da/tóc và nose/ear/neck, erosion, biên bins/serialization, ngưỡng thiếu pixel, chính sách zero variance/epsilon B và cách hiện thực trình tự chuẩn hóa. A/C1/C2/fusion chưa được chứng nhận trong kiểm toán B này.
4. **Sửa đổi đã thực hiện:** chặn profile không phù hợp tại runner/CLI mà không thay công thức all144; bổ sung 10 tests độc lập; thêm công cụ kiểm tra artifacts chỉ đọc; tạo bảng audit và hồ sơ hash/truy vết. Không sửa extractor, mask, vector cũ hoặc ranking.
5. **Các quyết định cần nhóm xác nhận:** (a) Pearson hay excess, ddof và bias; (b) công thức circular std, phép scale, epsilon/clip và giá trị suy biến; (c) ROI da chính thức gồm lớp nào, có nose/ear/neck hay không, có erosion không; (d) trình tự scale mô-men trước ghép và all144 cuối, epsilon/zero-variance của B; (e) biên bin, thứ tự serialization và tiêu chí vùng hợp lệ. Trước khi có xác nhận, không chọn raw/clean/union làm cấu hình chính thức và không tuyên bố toàn bộ pipeline tuân thủ 100%.
