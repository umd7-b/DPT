# A150 — kiểm chứng công thức và artifact

Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.


**Kết luận A:** tọa độ chuẩn hóa và số học14 A2 được kiểm chứng; Z-score **DEVIATION**. Không chứng nhận trọn14 đặc trưng EXACT khi endpoint/định nghĩa giải phẫu còn thiếu. Toàn bộ code/vector A giữ nguyên.

## A1 —478→68, tâm mắt và136 tọa độ

`geometry_features.py::INDICES` có68 phần tử duy nhất theo nhóm jaw17, mày5+5, nose9, mắt6+6, môi20. Bảng đầy đủ từng index68→MP478 và tọa độ thật nằm ở [landmark_mapping.csv](evidence/landmark_mapping.csv); bản code có dòng tại [source_listing.txt](evidence/source_listing.txt). `map_68_landmarks.py` có bảng cùng cấu trúc, nhưng chú thích của chính file gọi là ánh xạ thử nghiệm; không lấy tên file làm chứng nhận.

Code dùng `L=mean(p36..41)`, `R=mean(p42..47)`, `E=(L+R)/2`, `d=||L−R||₂`, `p′=(p−E)/d`. PDF viết trung điểm hai tọa độ mắt và phép chia d; **không chỉ định phải lấy mean của6 điểm mí**. Vì thế phép biến đổi tọa độ là EXACT có điều kiện, còn lựa chọn tâm mỗi mắt là UNVERIFIED về phê duyệt học thuật. Thứ tự A1 là x0,y0,…,x67,y67; không đưa z của MediaPipe vào vector.

Đã xem hai hình PDF trang8 (`pdf_page8_X31.png`, `pdf_page8_X33.png`) và ảnh audit có đánh số mốc. Có dấu hiệu topology mũi khác hình minh họa: code p30=MP1 có y≈149.59, p33=MP4 có y≈142.02 trên CFD00001, nên “đáy mũi” p33 nằm trên p30 trong cách gán code. Hình PDF không cho bảng ID MediaPipe hoặc nhãn index rõ từng nút để chốt mapping thay thế. **Ghi UNVERIFIED, không tự sửa mũi hoặc giả chứng minh đúng giải phẫu.** Tương tự, cách lấy rộng gò má p2/p14 và cao mặt từ midpoint hai đầu mày tới cằm cần thẩm quyền chốt endpoint.

`detect_landmarks` đặt `num_faces=1`, kiểm `len(result.face_landmarks)==1`; cấu hình này chỉ cho tối đa1 mặt trả về, không chứng minh ảnh không có mặt phụ. d<1e-6 bị từ chối; norm góc<1e-8 bị từ chối; vector cuối phải hữu hạn. PDF chưa quy định các ngưỡng đó. Không chạy main extractor/batch để ghi lại kho.

## A2 —14 đặc trưng, từng tử số/mẫu số/đơn vị

Mọi hàng dùng `features/A_geometry/src/geometry_features.py::calculate_ratios`; góc gọi `angle_degrees`. Ký hiệu `D(i,j)=||p_i−p_j||₂`, `H=D((p21+p22)/2,p8)`, `d=||L−R||₂`, `E=(L+R)/2`, `e=1e-8`. Mốc ghi 0-based; tên “trái/phải” là nhãn code, chưa xác nhận quy ước trái giải phẫu hay trái ảnh.

Ảnh thật minh họa **cfd_final_00001.png**. Số học oracle dùng `math.hypot/fsum/acos`, không lấy output hàm code làm expected. Tử số và mẫu số trong bảng tính scalar float64 từ cùng landmarks; code có phép toán/cast float32 nên có sai số làm tròn được đo riêng.

| STT / Nội dung PDF | Mốc code (0-based) | Tử số | Mẫu số thực tế | Đơn vị | Code / oracle ảnh thật | Trạng thái |
|---|---|---:|---:|---|---|---|
| 1. Rộng gò má / cao mặt | p2=MP132,p14=MP361;H dùng p21=MP107,p22=MP336,p8=MP152 | 157.164311525254 | 150.211239656817 +1e-8 | dimensionless | 1.046288609505 / 1.046288625764 | UNVERIFIED |
| 2. Khoảng cách hai mắt / cao mặt | mean p36..41/MP33,160,158,133,153,144 và p42..47/MP362,385,387,263,373,380; H như trên | 80.790850069643 | 150.211239656817 +1e-8 | dimensionless | 0.537848174572 / 0.537848234585 | UNVERIFIED |
| 3. Bề ngang mắt trái / khoảng cách hai mắt | p36=MP33,p39=MP133;d hai tâm mí | 32.228357157026 | 80.790850069643 +1e-8 | dimensionless | 0.398910999298 / 0.398910979712 | UNVERIFIED |
| 4. Bề ngang mắt phải / khoảng cách hai mắt | p42=MP362,p45=MP263;d hai tâm mí | 32.753390643459 | 80.790850069643 +1e-8 | dimensionless | 0.405409723520 / 0.405409654821 | UNVERIFIED |
| 5. Độ mở mi mắt trái | p37=MP160,p41=MP144,p38=MP158,p40=MP153; p36/p39 | 26.109070544663 | 64.456714314051 +1e-8 | dimensionless | 0.405063658953 / 0.405063627870 | UNVERIFIED |
| 6. Độ mở mi mắt phải | p43=MP385,p47=MP380,p44=MP387,p46=MP373; p42/p45 | 26.884079950610 | 65.506781286918 +1e-8 | dimensionless | 0.410401463509 / 0.410401479333 | UNVERIFIED |
| 7. Rộng cánh mũi / khoảng cách hai mắt | p31=MP129,p35=MP358 | 46.784445818403 | 80.790850069643 +1e-8 | dimensionless | 0.579081058502 / 0.579080994596 | UNVERIFIED |
| 8. Rộng miệng / khoảng cách hai mắt | p48=MP61,p54=MP291 | 54.961406725543 | 80.790850069643 +1e-8 | dimensionless | 0.680292546749 / 0.680292467171 | UNVERIFIED |
| 9. Độ mở môi / khoảng cách hai mắt | p62=MP13,p66=MP14 | 1.596677107182 | 80.790850069643 +1e-8 | dimensionless | 0.019763097167 / 0.019763093291 | UNVERIFIED |
| 10. Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt | E trung điểm hai tâm mí; p30=MP1 | 47.144439313003 | 80.790850069643 +1e-8 | dimensionless | 0.583537042141 / 0.583536864218 | UNVERIFIED |
| 11. Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt | E và midpoint(p48=MP61,p54=MP291) | 78.895153263479 | 80.790850069643 +1e-8 | dimensionless | 0.976535797119 / 0.976535748611 | UNVERIFIED |
| 12. Khoảng cách chóp mũi–đáy cằm / cao mặt | p30=MP1,p8=MP152;H như trên | 74.196540862746 | 150.211239656817 +1e-8 | dimensionless | 0.493947982788 / 0.493947996350 | UNVERIFIED |
| 13. Rộng xương hàm / cao mặt | p4=MP172,p12=MP397;H như trên | 131.203921440732 | 150.211239656817 +1e-8 | dimensionless | 0.873462677002 / 0.873462743079 | UNVERIFIED |
| 14. Góc xương hàm tại cằm | p4=MP172,p8=MP152,p12=MP397 | 128.195068024916 | tích hai norm trong arccos; xem công thức | degrees | 128.195068359375 / 128.195068024916 | UNVERIFIED |

Góc STT14: θ=degrees(acos(clip((p4−p8)·(p12−p8)/(||p4−p8||||p12−p8||),−1,1))). Tử số hiển thị ở hàng14 là góc kết quả scalar để tiện đối chiếu, không phải dot product; mẫu số thật của arccos được viết ở công thức này. Góc ở miền[0°,180°], đúng đơn vị độ PDF; góc quan sát vẫn phụ thuộc endpoint.

Với từng hàng: biểu thức code đầy đủ có trong bảng yêu cầu dưới đây; [a2_real_image_oracles.csv](evidence/a2_real_image_oracles.csv) lưu **56 dòng=14×4 ảnh**, numerator, denominator trước cộng ε, ε, code value, scalar value, tỷ lệ không guard và sai số. **UNVERIFIED không có nghĩa sai số học**:14 tests giải tích đều đạt, nhưng PDF chỉ nêu tên tỉ lệ, không đủ định nghĩa từng điểm/độ mở mắt và không có hồ sơ phê duyệt A tương đương D01–D17 của B.

| Ảnh thật | Max sai số raw so với kho | Max sai số tọa độ oracle | Max sai số14 A2 |
|---|---:|---:|---:|
| cfd_final_00001.png | 0 | 3e-07 | 3.34e-07 |
| cfd_final_00069.png | 0 | 2.33e-07 | 4.99e-06 |
| cfd_final_00088.png | 0 | 1.38e-07 | 7.64e-06 |
| cfd_final_00144.png | 0 | 1.74e-07 | 4.61e-06 |

Các regularizer A2 `+1e-8` làm biểu thức không bằng đúng phép chia không guard trên số thực; CSV lưu cả hai. Bảng PDF chưa cho công thức/biện pháp số học chi tiết cho từng tỉ lệ, nên ghi **quy ước chưa phê duyệt/UNVERIFIED**, không tự gộp nó thành EXACT hoặc âm thầm bỏ guard trong lần kiểm toán này. Riêng Z-score có phương trình mẫu số rõ ràng, xử lý ở mục tiếp theo.

## A3 — Z-score, ưu tiên cao nhất

PDF §2.5.2 trang17: `z_j=(x_j−mu_j)/(sigma_j+epsilon)`; query dùng lại tham số kho. Code thực tế:

```python
X = np.load(...).astype(np.float64)
mean = np.mean(X, axis=0)
std = np.std(X, axis=0)  # ddof=0
std_safe = np.where(std < 1e-8, 1.0, std)
X_normalized = (X - mean) / std_safe
np.save(..., X_normalized.astype(np.float32))
np.savez(..., mean=mean, std=std_safe)
```

Vị trí chính xác: `features/A_geometry/src/normalize_features.py` dòng24 tính mean, dòng25 tính std, **dòng28 thay std bằng1 theo ngưỡng**, **dòng31 chia cho std_safe**, dòng36 cast float32; từng dòng nằm trong source_listing. **DEVIATION** ở mẫu số so với PDF §2.5.2 trang17; `1e-8` trong `where` là ngưỡng, không phải ε được cộng. Saved key `std` là divisor hiệu dụng, không luôn là raw_sigma. Trên kho hiện tại0 chiều raw_sigma<1e-8; mọi divisor bằng raw_sigma, vẫn không bằng raw_sigma+ε với ε>0.

| Trường hợp độc lập | Code hiện tại | Công thức PDF với ε minh họa1e-8 |
|---|---|---|
| x=1,3,5; μ=3,σ=√(8/3) | z=(x−3)/σ | z=(x−3)/(σ+1e-8), khác dù rất nhỏ |
| Training7,7,7; query9 | divisor1 → qz=2 | divisor1e-8 → qz=200000000 |
| x=1e-10,3e-10,5e-10 | σ≈1.63299e-10<1e-8 → divisor1 | divisor≈1.01633e-8, khác xa divisor1 |

Không nhận hai công thức là tương đương chỉ vì training cột hằng cùng bằng0 hoặc thứ hạng ít thay đổi. PDF không chốt trị số ε; ba giá trị dưới đây chỉ là phép đo độ nhạy, không tạo output sửa chính thức:

| ε giả định | Chiều / ảnh / giá trị float64 khác | Giá trị float32 đổi | Max ∣Δ∣ float64 |
|---:|---|---:|---:|
| 1e-12 | 150 / 1438 / 215700 | 92 | 1.02480957054e-09 |
| 1e-08 | 150 / 1438 / 215700 | 214046 | 1.02480673698e-05 |
| 1e-06 | 150 / 1438 / 215700 | 215700 | 0.00102456371524 |

Chi tiết từng chiều tại [a_zscore_dimensions.csv](evidence/a_zscore_dimensions.csv). So sánh float64 ở đây dùng cùng μ, cùng raw_sigma của kho, tách khỏi sai số cast; cột float32 so sau cast giống dtype artifact. `mean_oracle_max_error=0.0`, `std_oracle_max_error=8.88e-16`, normalized cũ được tái tạo **đúng từng phần tử**. Nhất quán artifact cũ không loại bỏ DEVIATION.

## A4 —query và Top-5

Legacy search gọi đúng extractor và `(query_raw−saved_mean)/saved_std`, norm đủ150 chiều float64, loại chính query theo đường dẫn, argsort tăng dần. Worker A cũng dùng cùng stats cũ, đã thực thi thật trong `.venv311`. Bộ test kiểm lại3 ảnh legacy có PNG:00001,00088,00144, dựng ảnh mới trong audit và so pixel giải mã: **3/3 khớp**. Không ghi lại file legacy. CSV audit chứa15 dòng kết quả tính lại; file PNG lịch sử chỉ in khoảng cách3 chữ số, không có CSV gốc để đối chiếu float64 lịch sử đến mọi chữ số.

Phép thử giả định σ+ε cho2 query×2 chế độ A-only/A+B×3 epsilon tạo12 trường hợp. Top-5 không đổi trong12 trường hợp này, nhưng giá trị khoảng cách/median thay đổi; **không dùng việc thứ hạng trùng để chấp nhận code cũ hoặc chọn ε**. Xem `a_hypothetical_pdf_ranking_sensitivity.json`. Không phải benchmark chất lượng truy hồi.

## Bảng đối chiếu đầy đủ A

| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |
|---|---|---|---|---|---|---|
| A01 — 478 landmarks từ MediaPipe, sau đó chọn 68 | 5,8 | features/A_geometry/src/geometry_features.py:203::detect_landmarks | pixel=(lm.x*w,lm.y*h); points_478[INDICES] | dataset_verification.json: 1438×478; a_verification.json | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| A02 — Số điểm và thứ tự nhóm: hàm, mày, mũi, mắt, miệng | 8–9 | features/A_geometry/src/geometry_features.py:1 | 17+5+5+9+6+6+20=68; 68 ID duy nhất | landmark_mapping.csv; test_flatten_order_x_y_and_136_plus_14 | EXACT | EXACT về số lượng/nhóm, không chứng nhận từng mốc giải phẫu. |
| A03 — Ánh xạ từng ID 478→68 và đúng vị trí giải phẫu | 8 (hình),9 | features/A_geometry/src/geometry_features.py:1 | Danh sách INDICES hiện có; đặc biệt NOSE=[168,6,197,1,129,48,4,278,358] | landmark_mapping.csv; pdf_page8_X31.png; cfd_final_00001_68_annotated.png | UNVERIFIED | Cần bảng ID chuẩn/canonical có thẩm quyền; hình mũi có dấu hiệu khác, không tự thay ID. |
| A04 — Tâm hai mắt là trung điểm hai mắt | 5,9 | features/A_geometry/src/geometry_features.py:86::normalize_landmarks | C=(eye_l+eye_r)/2 | test_normalization_known_centers_and_ipd; oracle trên 4 ảnh thật | EXACT | Kết luận điều kiện trên hai tâm mắt đã chọn; lựa chọn tâm xem A05. |
| A05 — Định nghĩa tọa độ tâm mỗi mắt | 5,9 | features/A_geometry/src/geometry_features.py:86::normalize_landmarks | eye_l=mean(p36:p42); eye_r=mean(p42:p48) | Ảnh mốc và tọa độ thực; PDF không cho công thức trung bình 6 mí | UNVERIFIED | Chốt quy ước tâm mí hay tâm mống mắt; không coi mặc nhiên đã được phê duyệt. |
| A06 — Chuẩn hóa tọa độ P′=(P−C)/d | 9 | features/A_geometry/src/geometry_features.py:86::normalize_landmarks | (points-center)/∣∣eye_l-eye_r∣∣₂ | test_normalization_known_centers_and_ipd; a_verification.json | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| A07 — A1 136 tọa độ, thứ tự x,y theo từng mốc | 9 | features/A_geometry/src/geometry_features.py:246::extract_geometry | normalized.flatten() → x0,y0,…,x67,y67 | test_flatten_order_x_y_and_136_plus_14; raw shape 1438×150 | EXACT | Thứ tự x,y được kiểm chứng; PDF không liệt kê serialization chi tiết. |
| A08 — Xử lý thiếu landmark/không hợp lệ | 8–9; PDF không chốt fallback | features/A_geometry/src/geometry_features.py:203::detect_landmarks | num_faces=1; reject len!=1; d<1e-6 → ValueError; finite assert | test_zero_eye_distance_rejected; code caps num_faces at 1 | UNVERIFIED | Không dùng num_faces=1 làm bằng chứng không có mặt phụ; chốt chính sách lỗi. |
| A09 — Ghép A1 và đủ 14 thành phần A2 thành A150 | 9–10,16 | features/A_geometry/src/geometry_features.py:246::extract_geometry | concatenate(A1[136],A2[14]) | test_flatten_order_x_y_and_136_plus_14; 4 vector thật tái lập | EXACT | Chỉ chứng nhận cấu trúc, không thay cho kiểm toán từng tỉ lệ. |
| A2-01 — Rộng gò má / cao mặt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(2,14)/(H+e) | test_A2_01_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 1 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-02 — Khoảng cách hai mắt / cao mặt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | d/(H+e) | test_A2_02_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 2 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-03 — Bề ngang mắt trái / khoảng cách hai mắt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(36,39)/(d+e) | test_A2_03_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 3 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-04 — Bề ngang mắt phải / khoảng cách hai mắt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(42,45)/(d+e) | test_A2_04_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 4 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-05 — Độ mở mi mắt trái | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | (D(37,41)+D(38,40))/(2D(36,39)+e) | test_A2_05_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 5 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-06 — Độ mở mi mắt phải | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | (D(43,47)+D(44,46))/(2D(42,45)+e) | test_A2_06_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 6 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-07 — Rộng cánh mũi / khoảng cách hai mắt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(31,35)/(d+e) | test_A2_07_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 7 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-08 — Rộng miệng / khoảng cách hai mắt | 9 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(48,54)/(d+e) | test_A2_08_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 8 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-09 — Độ mở môi / khoảng cách hai mắt | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(62,66)/(d+e) | test_A2_09_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 9 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-10 — Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(E,p30)/(d+e) | test_A2_10_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 10 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-11 — Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(E,(p48+p54)/2)/(d+e) | test_A2_11_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 11 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-12 — Khoảng cách chóp mũi–đáy cằm / cao mặt | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(30,8)/(H+e) | test_A2_12_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 12 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-13 — Rộng xương hàm / cao mặt | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | D(4,12)/(H+e) | test_A2_13_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 13 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A2-14 — Góc xương hàm tại cằm | 10 | features/A_geometry/src/geometry_features.py:130::calculate_ratios | degrees(acos(clip((p4−p8)·(p12−p8)/(D(4,8)D(12,8)),−1,1))) | test_A2_14_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng 14 | UNVERIFIED | Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt. |
| A10 — Công thức Euclid giữa hai mốc và góc arccos tính bằng độ | 9–10 | features/A_geometry/src/geometry_features.py:65::angle_degrees | D=√(dx²+dy²); θ=degrees(acos(u·v/(∣∣u∣∣∣∣v∣∣))) | test_angle_right_straight_and_degenerate; 14 oracle A2 | EXACT | EXACT về phép toán/đơn vị, tách riêng câu hỏi endpoint ở A2-14. |
| A11 — ε và các ngưỡng bổ sung trong tỉ lệ/landmark | 9–10 (không chốt) | features/A_geometry/src/geometry_features.py:130::calculate_ratios | e=1e-8; d guard=1e-6; angle norm guard=1e-8 | source_listing.txt; a2_real_image_oracles.csv có giá trị không cộng e | UNVERIFIED | Công khai quy ước chưa phê duyệt; không gán epsilon A2 cho Z-score A. |
| A12 — Z-score A phải có mẫu số σ+ε | 17 §2.5.2 | features/A_geometry/src/normalize_features.py:10::main | std_safe=where(std<1e-8,1,std); Z=(X−mean)/std_safe | 3 oracle normal/zero/tiny sigma; a_zscore_epsilon_sensitivity.csv | DEVIATION | Sửa theo PDF trong phiên bản mới, lưu raw_sigma và epsilon; cập nhật query và mọi phụ thuộc. |
| A13 — Cách fit mean/std và ddof | 11,17 | features/A_geometry/src/normalize_features.py:10::main | mean(X,axis=0), std(X,axis=0,ddof=0) | a_verification.json: mean error=0, sigma error≤8.89e-16 | UNVERIFIED | ddof=0 đã đo đúng code, nhưng PDF không chốt ddof; giữ nguyên khi sửa mẫu số nếu không có căn cứ đổi. |
| A14 — Giá trị ε Z-score A | 17 | features/A_geometry/src/normalize_features.py:10::main | Không có epsilon cộng mẫu số; 1e-8 chỉ là ngưỡng std | source_listing.txt; sensitivity ε=1e-12/1e-8/1e-6 | UNVERIFIED | PDF không cho trị số; phải lưu rõ một ε dương, không nhận ngưỡng std là ε. |
| A15 — Raw, stats và normalized A nhất quán với phiên bản code hiện tại | 11,17 | features/A_geometry/src/normalize_features.py:10::main | 1438×150; raw float32→float64 fit→normalized float32 | a_verification.json: tái tạo normalized đúng từng phần tử | EXACT | EXACT về tính toàn vẹn phiên bản cũ; A12 vẫn DEVIATION. |
| A16 — Query A dùng lại đúng stats kho | 17 | retrieval/search_geometry.py:25::main; retrieval/ab_query_worker.py:13::normalize_a | (query_raw.astype(float64)−mean)/saved_std | query_worker_verification.json; tái lập 4 raw vector thật | EXACT | Dùng lại đúng stats cũ không làm mẫu số cũ tuân thủ PDF. |
| A17 — Euclid đủ 150 chiều, sắp tăng dần | 11,17–18 | retrieval/search_geometry.py:25::main | norm(X.astype(float64)−q,axis=1); argsort | 3 PNG A-only tái tạo đúng pixel; 15 khoảng cách lưu trong evidence | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| A18 — Self-match A-only và tie-break | 18; PDF không chốt danh tính | retrieval/search_geometry.py:25::main | Loại theo Path.resolve; argsort không có filename tie-break | source_listing.txt; A-only 3 query loại đúng path; AB khác legacy | UNVERIFIED | Công khai quy ước; bản sao đổi tên/đổi encoding chưa được legacy loại theo ID. |
| A19 — Top-5 A-only đã lưu có tái lập được | 11,18 | retrieval/search_geometry.py:25::main | 3 query 00001/00088/00144, render lại layout hiện hành | a_verification.json::legacy_all_previews: 3/3 exact pixel reproduction | EXACT | Không có CSV lịch sử; đối chiếu PNG xác nhận tên/thứ tự/nhãn khoảng cách đến 3 chữ số. |
| A20 — Giá trị thông tin: phương sai giữa người lớn, trong người nhỏ; ổn định màu/sáng/scale | 7–8,10–11 | features/A_geometry/src/geometry_features.py:246::extract_geometry; features/A_geometry/src/normalize_features.py:10::main | Có sigma theo kho và invariance tọa độ; chưa có đánh giá giữa/trong người đầy đủ | a_zscore_dimensions.csv; translation/scale oracle; metadata HF thiếu person_id | UNVERIFIED | Không đồng nhất độ phân tán kho với discriminability hoặc ổn định thực nghiệm; cần nhãn/protocol độc lập. |
