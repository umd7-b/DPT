<!-- PAGE 1: Bìa -->

# PHÂN TÍCH KỸ THUẬT
## BỘ ĐẶC TRƯNG A & B

**PORTRAIT RETRIEVAL**

Geometry A150 · Color B144

Báo cáo nghiên cứu và kiểm toán triển khai

**Dữ liệu đã kiểm tra:** 1.438 ảnh chân dung, 256×256, CFD và HF.

**Artifact:** A150 — 1.438 vector; B144 — 1.437 vector hợp lệ.

**Phiên bản màu:** B144_raw_v1.0.0, quyết định D01–D17 đã được chấp thuận.

Ngày lập: **22/11/2026**

Nguồn học thuật duy nhất: báo cáo nhóm `csdldpt.pdf`.

Phạm vi: giải thích công thức, dữ liệu và code đang chạy; không sửa A/B, không tạo lại kho và không triển khai C1/C2.

Tài liệu phân biệt rõ yêu cầu trong báo cáo gốc, quy ước hiện thực, quyết định được chấp thuận và những điểm chưa đủ bằng chứng. Kết quả kiểm thử chương trình không được diễn giải thành độ chính xác nhận diện hoặc phân đoạn.

<!-- PAGE 2: Mục lục -->

# MỤC LỤC
| Nội dung | Trang |
|---|---|
| Chương 1. Tổng quan hệ thống và dữ liệu | 3–4 |
| Chương 2. Bộ A: landmarks, chuẩn hóa và A1 | 5–6 |
| Chương 2. 14 đặc trưng A2, phân tích từng thành phần | 7–13 |
| Chương 3. Z-score Bộ A: công thức và dữ liệu | 14–15 |
| Chương 4. Bộ B: parsing, HS, Lab và Hue vòng | 16–19 |
| Chương 4. Bảng index đầy đủ B144 | 20–21 |
| Chương 5. Z-score Bộ B | 22 |
| Chương 6. Euclid, Top-5 và kết quả thật | 23–25 |
| Chương 7. Kết quả, giới hạn và ngoại lệ | 26–27 |
| Nguồn, kiểm chứng và cách tái lập | 28 |

## Quy ước đọc tài liệu

**[PDF]**: nội dung được báo cáo nhóm quy định rõ; dẫn trang là **trang PDF đếm từ 1**, không phải số trang trong mục lục gốc.

**[CODE]**: biểu thức/lựa chọn được đọc trực tiếp từ source hiện tại. Khi PDF chưa chốt landmarks, epsilon hoặc serialization, tài liệu gọi đó là quy ước hiện thực.

**[APPROVED]**: D01–D17 được người dùng chấp thuận cho B v1, không mặc nhiên trở thành công thức nguyên văn của PDF.

**[AUDIT]**: kết quả đo trực tiếp từ artifact, hash hoặc phép kiểm tra độc lập trong lần lập báo cáo này.

**[DEVIATION]**: khác biệt cụ thể giữa code và quy định rõ trong PDF; không tự sửa trong nhiệm vụ viết báo cáo.

**[UNVERIFIED]**: chưa đủ bằng chứng để xác nhận. Không điền số liệu suy đoán.

Các phép tính minh họa được ghi rõ là ví dụ giải tích hoặc được tính từ `cfd_final_00001.png`. Hình chân dung/mask đều lấy từ dataset hoặc artifact thật, không dùng ảnh sinh tạo.

<!-- PAGE 3: Chương 1 — Tổng quan -->

# CHƯƠNG 1. TỔNG QUAN HỆ THỐNG

## 1.1. Từ ảnh đến biểu diễn đặc trưng

Hệ thống biểu diễn mỗi ảnh bằng một dãy số có ý nghĩa và thứ tự cố định — **feature vector**. Thay vì so sánh trực tiếp toàn bộ pixel, truy hồi tính khoảng cách giữa các vector của query và ảnh kho. Mỗi chiều đại diện một tọa độ, tỉ lệ hoặc thống kê màu; một vector chỉ có thể so sánh đúng với vector dùng cùng định nghĩa và cùng tham số chuẩn hóa.

**A150** mô tả hình học: vị trí tương đối của 68 điểm mốc, tỉ lệ và góc. **B144** mô tả phân bố màu của hai ROI da/tóc. Hai ảnh có hình học gần nhau vẫn có thể khác màu; hai ảnh cùng màu chưa chắc giống đường nét. Hai bộ cung cấp thông tin bổ sung chứ không chứng minh danh tính.

![Hình 1. Pipeline khái niệm; nhánh A và B có extractor và thống kê riêng.](figures/pipeline.png)

*Hình 1. Pipeline khái niệm; nhánh A và B có extractor và thống kê riêng.*

## 1.2. Thiết kế 854 chiều và phạm vi hiện có

| Bộ | Biểu diễn | Số chiều | Tình trạng |
|---|---|---|---|
| A | Geometry: 136 tọa độ + 14 tỉ lệ/góc | 150 | Đã có artifact |
| B | Skin72 + Hair72 | 144 | Đã có v1 chính thức |
| C1 | LBP theo 4 vùng | 236 | Chưa triển khai |
| C2 | Root-HOG | 324 | Chưa triển khai |

[PDF: §2.1, tr.7; §2.5.1, tr.16] Tổng thiết kế là 854 chiều. Báo cáo này kiểm tra hai bộ A/B đã có; không coi tổng 854 là một ma trận đã triển khai. Luồng A+B fusion và bốn bộ chưa hoàn thiện.

Khi tính riêng B, khoảng cách Euclid được áp dụng trên B144 đã Z-score. Chuẩn hóa khoảng cách theo median ở §2.5 dành cho kết hợp các bộ; không âm thầm cộng các khoảng cách thô hoặc trộn tham số A và B.

<!-- PAGE 4: Chương 1 — Dữ liệu và tiền xử lý -->

# 1.3. DỮ LIỆU VÀ TIỀN XỬ LÝ

[AUDIT] Đọc trực tiếp 1.438 file PNG trong dataset: tất cả có kích thước `(256,256,3)`. Metadata và prefix có **710 CFD + 728 HF**. README dataset nói ảnh được sao chép giữ nguyên byte và có ảnh HF cần duyệt; đây không phải bằng chứng mọi ảnh đều thỏa điều kiện một người/chính diện.

| Bước được PDF mô tả | Bằng chứng trong repo hiện tại |
|---|---|
| Phát hiện khuôn mặt, loại ảnh có 0 hoặc >1 mặt | A giới hạn num_faces=1; chỉ kiểm tra số output. Không chứng minh đã sàng lọc đủ ảnh nhiều người. |
| 478 → 68 landmarks | Có mapping và code đang dùng; kiểm tra một ảnh thật tái tạo đúng vector đã lưu. |
| Xoay đường mắt nằm ngang, scale/crop về khuôn chuẩn | Không thấy quy trình warp/crop này trong module A/shared/retrieval hiện tại; code đọc ảnh đã chuẩn hóa. |
| Bicubic 256×256 | Toàn bộ kích thước được xác minh; INTER_CUBIC trong map_68_landmarks chỉ phóng hình minh họa, không chứng minh lịch sử crop. |
| Vị trí/scale mắt theo tiêu chí báo cáo | Metadata có eye_distance nhưng không có đầy đủ tọa độ mắt, ma trận biến đổi hoặc log alignment. |

[PDF: §1.2–1.3, tr.5] Báo cáo mô tả khoảng cách mắt trung vị 29,45% chiều rộng và tâm mắt ở 40% chiều cao. [AUDIT] Metadata A có trung vị d=**78,494411 px** (30,6619% của 256), min **72,415794**, max **85,929054**. Đây là khoảng cách hai tâm tính trung bình 6 landmarks/mắt của code; không nhất thiết là cùng thước đo/công đoạn của số liệu alignment trong PDF. Chưa đủ bằng chứng để xác nhận các con số lịch sử hoặc suy ra chính xác pipeline cũ.

Không suy đoán tuổi, giới tính hoặc nguồn gốc sinh trắc từ ảnh. Các mô tả tập dữ liệu trong PDF được ghi là thông tin của báo cáo, không thay cho nhãn đã được kiểm chứng độc lập.

## 1.4. Nguyên tắc kiểm toán

Đọc source và artifact trước khi viết công thức. Đối chiếu tên ảnh/thứ tự, shape, dtype, tính hữu hạn và thống kê thực. Giữ nguyên cả ảnh bất thường, warning và hàng thiếu B. Chỉ tạo tài liệu/hình dẫn xuất dưới `docs/reports/`; không chạy main ghi lại vector A/B hoặc mask nguồn.

<!-- PAGE 5: Chương 2 — Landmarks -->

# CHƯƠNG 2. A150 — GEOMETRY

## 2.1. MediaPipe và ánh xạ 478 → 68

[PDF: §2.2.2, tr.8] Dùng 478 landmarks rồi ánh xạ về 68 điểm. [CODE] `geometry_features.detect_landmarks` đọc BGR, đổi RGB/SRGB, chạy `FaceLandmarker` chế độ IMAGE với model `.task` có sẵn và num_faces=1. Tọa độ x,y chuẩn hóa của model nhân w,h thành pixel float32; z không được đưa vào A150.

![Hình 2. 68 landmarks thật trên cfd_final_00001.png; chỉ số code bắt đầu từ 0.](figures/landmarks_68.png)

*Hình 2. 68 landmarks thật trên cfd_final_00001.png; chỉ số code bắt đầu từ 0.*

Mapping là danh sách INDICES chọn trực tiếp các nút MediaPipe, không phải một lần chạy detector 68 điểm khác. PDF không liệt kê đủ 68 ID; danh sách này là quy ước code. Thứ tự nhóm: hàm → mày trái → mày phải → mũi → mắt trái → mắt phải → miệng. Tên trái/phải theo code; không suy ra mọi quy ước trái/phải giải phẫu đã được tài liệu gốc định nghĩa.

Ảnh đọc lỗi → FileNotFoundError; không có đúng một output → RuntimeError. Batch bắt exception, ghi failed_images và tiếp tục. Artifact hiện có 0 hàng lỗi. Do cap num_faces=1, len(output)==1 không chứng minh ảnh chỉ có một người.

<!-- PAGE 6: Chương 2 — Chuẩn hóa và A1 -->

# 2.2. CHUẨN HÓA TỌA ĐỘ VÀ A1

[PDF: §2.2.2–2.2.3, tr.9] Công thức chuẩn hóa điểm:

$$
p'_i=\frac{p_i-c}{d},\qquad c=\frac{e_L+e_R}{2},\quad d=\|e_L-e_R\|_2
$$

[CODE] eL là mean p36…p41, eR là mean p42…p47. Trừ c đưa tâm mắt về gốc; chia d đặt khoảng cách hai tâm mắt thành 1. Lựa chọn trung bình 6 nút/mắt là quy ước hiện thực của `normalize_landmarks`, không phải danh sách điểm được PDF viết đầy đủ. d<1e-6 gây lỗi thay vì tạo vector giả.

## Ví dụ từ tọa độ thật

| Đại lượng | Giá trị pixel hoặc chuẩn hóa |
|---|---|
| eL | (88.170799, 102.113586) |
| eR | (168.958511, 102.824928) |
| c | (128.564651, 102.469254) |
| d | 80.790840 px |
| p0 | (46.358055, 121.232712) |
| p′0 | (-1.017524, 0.232247) |

`(46.358055−128.564651)/80.790840 ≈ -1.017524`; tọa độ y tính tương tự. Ví dụ là `cfd_final_00001.png`. Tái trích một ảnh bằng model/code hiện tại khớp **đúng từng phần tử A150 đã lưu**. Sai số tính A2 độc lập bằng float64 tối đa 3.345e-07, phù hợp khác biệt độ chính xác float32.

## 2.3. A1 và vector A150

68×2=136 tọa độ: `[x′0,y′0,x′1,y′1,…,x′67,y′67]`. Chỉ số 2i là x′i, 2i+1 là y′i. A150 nối **A1[0:136] và A2[136:150]**, float32. Không đưa eye_distance thành chiều thứ 151; nó được lưu riêng trong metadata.

Bảng mapping đầy đủ theo INDICES (0-based code → ID MediaPipe):

| Nhóm | Index code | ID MediaPipe theo thứ tự |
|---|---|---|
| Hàm | 0–16 | 234, 93, 132, 58, 172, 136, 150, 149, 152, 378, 379, 365, 397, 288, 361, 323, 454 |
| Lông mày trái | 17–21 | 70, 63, 105, 66, 107 |
| Lông mày phải | 22–26 | 336, 296, 334, 293, 300 |
| Mũi | 27–35 | 168, 6, 197, 1, 129, 48, 4, 278, 358 |
| Mắt trái | 36–41 | 33, 160, 158, 133, 153, 144 |
| Mắt phải | 42–47 | 362, 385, 387, 263, 373, 380 |
| Miệng | 48–67 | 61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91, 78, 81, 13, 311, 308, 402, 14, 178 |

Chuẩn hóa này bất biến tịnh tiến và scale dương trong mô hình toán học. Nó không tự loại xoay, phối cảnh, biểu cảm hoặc sai landmarks; d nhỏ khuếch đại nhiễu. Chỉ số (x,y) và mapping phải đồng nhất cho cả kho/query.

<!-- PAGE 7: Chương 2 — A2 1–2 -->

# 2.4. A2 — ĐẶC TRƯNG 1–2

D(a,b)=norm Euclid 2D; h=D((p21+p22)/2,p8); d=norm(eL−eR); ε=1e-8 **trong code tỉ lệ**, đơn vị tương ứng tọa độ pixel. Đây không phải ε của phương trình Z-score trong PDF.

## 1. Rộng gò má / cao mặt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 136.

**Landmarks:** p2,14,21,22,8. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_2,p_{14})}{h+\epsilon}
$$
**Ví dụ thật:** 157.164312/(150.211240+1e-8) → **1.046289**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Tỉ lệ bề ngang so với chiều cao giúp phân biệt mặt rộng với mặt dài.

**Giới hạn:** Code dùng p2–p14 làm đại diện bề ngang; h từ trung điểm mày đến cằm, không phải một phép đo gò má/đỉnh trán được PDF quy định đủ. Góc chụp ảnh hưởng cả hai độ dài.

## 2. Khoảng cách hai mắt / cao mặt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 137.

**Landmarks:** p36…47,21,22,8. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{d}{h+\epsilon}
$$
**Ví dụ thật:** 80.790850/(150.211240+1e-8) → **0.537848**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Mô tả độ tách hai tâm mắt tương đối với trục dọc mặt.

**Giới hạn:** Tâm mắt là trung bình 6 điểm mỗi mắt. Nhắm mắt, nheo mắt hoặc mày/cằm sai làm thay đổi tỉ lệ; không phải khoảng cách đồng tử đo trực tiếp.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 8: Chương 2 — A2 3–4 -->

# 2.4. A2 — ĐẶC TRƯNG 3–4

## 3. Bề ngang mắt trái / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 138.

**Landmarks:** p36,39 và 36…47. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{36},p_{39})}{d+\epsilon}
$$
**Ví dụ thật:** 32.228357/(80.790850+1e-8) → **0.398911**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Chuẩn hóa chiều rộng mắt theo kích thước vùng giữa mặt, hỗ trợ đối sánh hình dạng mắt.

**Giới hạn:** Đầu mút 36/39 do mapping quyết định. Tư thế nghiêng và che khuất làm bề ngang chiếu trên ảnh thay đổi; nhãn trái/phải theo code.

## 4. Bề ngang mắt phải / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 139.

**Landmarks:** p42,45 và 36…47. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{42},p_{45})}{d+\epsilon}
$$
**Ví dụ thật:** 32.753391/(80.790850+1e-8) → **0.405410**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Bổ sung chiều rộng mắt bên còn lại và thông tin bất đối xứng quan sát được.

**Giới hạn:** Chênh hai phía có thể do phối cảnh, che khuất hoặc sai điểm, không tự kết luận là bất đối xứng giải phẫu.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 9: Chương 2 — A2 5–6 -->

# 2.4. A2 — ĐẶC TRƯNG 5–6

## 5. Độ mở mi mắt trái

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 140.

**Landmarks:** p37,41,38,40,36,39. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{37},p_{41})+D(p_{38},p_{40})}{2D(p_{36},p_{39})+\epsilon}
$$
**Ví dụ thật:** (12.924338+13.184732)/(2×32.228357+1e-8) → **0.405064**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Hai khoảng dọc biểu diễn mức mở mi so với bề ngang mắt; phân biệt mắt mở lớn/hẹp.

**Giới hạn:** PDF chỉ gọi tên độ mở mi. Công thức hai cặp dọc/chia bề ngang là quy ước code, nhạy mạnh với chớp mắt và nheo mắt.

## 6. Độ mở mi mắt phải

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 141.

**Landmarks:** p43,47,44,46,42,45. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{43},p_{47})+D(p_{44},p_{46})}{2D(p_{42},p_{45})+\epsilon}
$$
**Ví dụ thật:** (13.589474+13.294606)/(2×32.753391+1e-8) → **0.410401**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Mô tả độ mở mắt còn lại và hỗ trợ so sánh hai bên.

**Giới hạn:** Không thể coi khác biệt chớp mắt là khác danh tính. Bề ngang gần 0 hoặc sai landmark có thể làm tỉ lệ tăng bất thường.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 10: Chương 2 — A2 7–8 -->

# 2.4. A2 — ĐẶC TRƯNG 7–8

## 7. Rộng cánh mũi / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 142.

**Landmarks:** p31,35 và 36…47. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{31},p_{35})}{d+\epsilon}
$$
**Ví dụ thật:** 46.784446/(80.790850+1e-8) → **0.579081**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Biểu diễn bề ngang mũi tương đối với vùng giữa mặt.

**Giới hạn:** Việc gán hai nút MediaPipe cho p31/p35 là xấp xỉ giải phẫu của mapping; phối cảnh hoặc tay che mũi làm sai khoảng cách.

## 8. Rộng miệng / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.9] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 143.

**Landmarks:** p48,54 và 36…47. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{48},p_{54})}{d+\epsilon}
$$
**Ví dụ thật:** 54.961407/(80.790850+1e-8) → **0.680293**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Khoảng hai khóe miệng chuẩn hóa mô tả miệng rộng/nhỏ.

**Giới hạn:** Nụ cười và biểu cảm làm khóe miệng dịch rõ; đây vừa là thông tin hình thái vừa nhạy với trạng thái ảnh.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 11: Chương 2 — A2 9–10 -->

# 2.4. A2 — ĐẶC TRƯNG 9–10

## 9. Độ mở môi / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 144.

**Landmarks:** p62,66 và 36…47. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{62},p_{66})}{d+\epsilon}
$$
**Ví dụ thật:** 1.596677/(80.790850+1e-8) → **0.019763**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Phân biệt môi đóng, hé hoặc mở tương đối với kích thước mặt.

**Giới hạn:** Dùng đúng cặp môi trong 62/66 của code. Biểu cảm và phát âm làm thay đổi lớn; số gần 0 không chứng minh môi đóng tuyệt đối khi landmark có nhiễu.

## 10. Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 145.

**Landmarks:** p36…47 và 30. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(c,p_{30})}{d+\epsilon}
$$
**Ví dụ thật:** 47.144439/(80.790850+1e-8) → **0.583537**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Mô tả vị trí mũi so với tâm hai mắt trong bố cục mặt.

**Giới hạn:** Code dùng Euclid 2D, nên chịu cả lệch ngang lẫn dọc; không phải chỉ lấy chênh tọa độ y. Đầu mũi theo mapping là p30.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 12: Chương 2 — A2 11–12 -->

# 2.4. A2 — ĐẶC TRƯNG 11–12

## 11. Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 146.

**Landmarks:** p36…47,48,54. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(c,(p_{48}+p_{54})/2)}{d+\epsilon}
$$
**Ví dụ thật:** 78.895153/(80.790850+1e-8) → **0.976536**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Mô tả quan hệ bố cục nửa trên và nửa dưới mặt.

**Giới hạn:** Code chọn trung điểm hai khóe miệng. PDF không chỉ rõ cách tổng hợp hai khóe; cười làm điểm giữa dịch chuyển.

## 12. Khoảng cách chóp mũi–đáy cằm / cao mặt

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 147.

**Landmarks:** p30,8,21,22. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_{30},p_8)}{h+\epsilon}
$$
**Ví dụ thật:** 74.196541/(150.211240+1e-8) → **0.493948**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Biểu diễn phần dưới mặt so với chiều cao mặt theo proxy đang dùng.

**Giới hạn:** Cằm bị cắt, râu/phụ kiện hoặc landmark sai có thể làm thay đổi số đo. h là proxy mày–cằm, không phải một chiều cao giải phẫu được xác thực.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 13: Chương 2 — A2 13–14 -->

# 2.4. A2 — ĐẶC TRƯNG 13–14

## 13. Rộng xương hàm / cao mặt

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 148.

**Landmarks:** p4,12,21,22,8. **Đơn vị/miền:** không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].


$$
\frac{D(p_4,p_{12})}{h+\epsilon}
$$
**Ví dụ thật:** 131.203921/(150.211240+1e-8) → **0.873463**.

**Hàm Python:** `geometry_features.calculate_ratios`; dùng distance/midpoint khi cần.

**Thông tin truy hồi:** Bổ sung độ rộng vùng hàm, hỗ trợ phân biệt mặt thuôn với hàm rộng.

**Giới hạn:** Hai nút p4/p12 và phép chiếu 2D là lựa chọn code. Góc quay đầu và đường tóc/che khuất có thể làm landmark trôi.

## 14. Góc xương hàm tại cằm

**Nguồn:** [PDF §2.2.3, tr.10] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** 149.

**Landmarks:** p4,8,12. **Đơn vị/miền:** độ, 0…180 khi hai cạnh không suy biến.


$$
\theta=\frac{180}{\pi}\arccos\left(\operatorname{clip}\left(\frac{u\cdot v}{\|u\|\|v\|},-1,1\right)\right)
$$
**Ví dụ thật:** u=(-63.8098,-32.6512), v=(67.3838,-31.0021); dot=-3287.4900; norm(u)norm(v)=5316.6317; acos(dot/norms)×180/π → **128.195068**°.

**Hàm Python:** `geometry_features.calculate_ratios` gọi `angle_degrees`.

**Thông tin truy hồi:** Góc ở cằm mô tả độ mở của hai cạnh hàm, giúp phân biệt cằm nhọn/tròn theo cấu trúc điểm đang dùng.

**Giới hạn:** angle_degrees từ chối tích norm<1e-8; clip chống lỗi acos do làm tròn. Mapping điểm góc hàm chưa có chứng nhận giải phẫu độc lập.

Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.

<!-- PAGE 14: Chương 3 — Z-score A -->

# CHƯƠNG 3. Z-SCORE BỘ A

## 3.1. Công thức PDF và biểu thức code

[PDF §2.5.2, tr.17] Từng chiều j dùng thống kê kho:

$$
z_j=\frac{x_j-\mu_j}{\sigma_j+\epsilon}
$$

xj là giá trị đặc trưng; μj là trung bình trên các ảnh kho; σj là độ lệch chuẩn cùng chiều; ε ổn định mẫu số. PDF không chốt trị số ε. Fit theo cột của ma trận, không theo hàng từng ảnh: tọa độ và góc có đơn vị/thang đo khác nhau, nên chuẩn hóa riêng mỗi ảnh sẽ trộn các đại lượng không đồng nhất và làm query không còn cùng hệ tham chiếu với kho.

[CODE: normalize_features.main] Chuyển A raw sang float64, tính mean/std axis=0, NumPy ddof=0; **không cộng ε cho mọi chiều**:

$$
s_j=1\ (\sigma_j<10^{-8}),\quad s_j=\sigma_j\ (\sigma_j\geq10^{-8}),\qquad z_j=\frac{x_j-\mu_j}{s_j}
$$

**[DEVIATION] Mẫu số s khác σ+ε.** Ngưỡng 1e-8 của code không được tự coi là ε cộng vào mẫu số. Khi σ>0, hai công thức thường gần nhau nếu ε nhỏ nhưng không bằng nhau; khi σ=0 và query khác mean, tác động có thể rất lớn. Không sửa thuật toán trong báo cáo này.

## 3.2. Ví dụ tính tay và NumPy

Cho cột minh họa x={1,3,5}: μ=3; variance=[4+0+4]/3=8/3; σ=1,632993162; code cho Z={−1,224744871;0;1,224744871}. NumPy std(ddof=0) và phép biến đổi cho cùng kết quả.

Nếu **giả định minh họa** ε=1e-8 trong công thức PDF (không phải giá trị PDF đã chốt), hai đầu là ±1,224744864. Cột {7,7,7}: training Z=0 ở cả hai cách; query x=9 thì code trả 2, còn σ+ε trả 2/ε. Training toàn số 0 không chứng minh hai chính sách giống nhau cho query.

Điều kiện dương của divisor, NaN/Inf và shape phải kiểm tra. Batch A hiện có lỗi thì ghi manifest lỗi; không tự thay vector không hợp lệ bằng zero.

<!-- PAGE 15: Chương 3 — Phân bố A -->

# 3.3. ARTIFACT A VÀ PHÂN BỐ THỰC

![Hình 3. Ba chiều A thật trước/sau Z-score; mỗi cột histogram đếm số ảnh trong kho.](figures/A_distributions.png)

*Hình 3. Ba chiều A thật trước/sau Z-score; mỗi cột histogram đếm số ảnh trong kho.*

| Kiểm tra A | Giá trị đo trực tiếp |
|---|---|
| Raw / normalized shape | (1438,150) / (1438,150) |
| Raw / normalized dtype | float32 / float32 |
| Mean/std lưu | float64, 150 phần tử |
| Ảnh lỗi trong failed_images.csv | 0 |
| Chiều std<1e-8 | 0 |
| Khoảng std raw | 0.004174 … 6.555324 |
| Sai số Z lưu so với phép tính float64 | 2.346e-07 |

Normalized được cast float32 khi lưu. Vì vậy query tính float64 không nhất thiết bằng đúng từng bit với hàng normalized đã lưu, dù raw descriptor khớp. Audit kiểm tra **chính xác** phép tính float64 rồi cast float32 tạo ra artifact hiện có; sai số lượng tử không được coi là nhận diện sai.

`geometry_stats.npz` lưu mean và std_safe; query A dùng lại `(features.astype(float64)−mean)/std`. Không fit lại một ảnh. Mỗi đặc trưng vẫn giữ ngữ nghĩa khác nhau sau chuẩn hóa; Z-score không biến tỉ lệ/góc thành thước đo độc lập về thống kê hoặc loại bỏ biểu cảm.

<!-- PAGE 16: Chương 4 — Parsing và mask -->

# CHƯƠNG 4. B144 — COLOR

## 4.1. Face parsing và ROI

UniFace là thư viện hiện thực; BiSeNet ResNet18 phân lớp ngữ nghĩa pixel (semantic face parsing). [APPROVED D09] lấy class 1 làm Skin và class 17 làm Hair, tạo hai mask uint8 0/255. PDF §2.3 chỉ nêu hai vùng da/tóc, **không chỉ định UniFace/BiSeNet đích danh**.

Mask raw được chọn theo **D10**, giữ nguyên tập pixel dự đoán, không phải vì đã chứng minh tốt hơn erosion. Clean 3×3 và Skin+Nose là thí nghiệm lịch sử, không trộn vào vector chính thức. Skin=1 bỏ nose=10 và lớp tai/cổ theo schema; không tự thêm vào để hình nhìn đầy hơn.

![Hình 4. Dự đoán thật: ảnh gốc, hai mask nhị phân và ROI màu; hàng dưới HF00209 có tóc raw rỗng.](figures/raw_masks.png)

*Hình 4. Dự đoán thật: ảnh gốc, hai mask nhị phân và ROI màu; hàng dưới HF00209 có tóc raw rỗng.*

Trước trích đặc trưng, code đối chiếu image hash, receipt, mask hash, số pixel, shape 256×256 và giá trị 0/255; kiểm tra hai vùng không chồng lấn. Trong kho đã có 2.876 raw mask kỹ thuật hợp lệ. Hash chỉ xác nhận tính toàn vẹn/provenance, không xác nhận pixel đúng ngữ nghĩa.

Model source: UniFace 4.3.0, parsing_resnet18.onnx, provider của lần parsing là CPUExecutionProvider. Nhiệm vụ lập báo cáo không chạy lại parsing hoặc tải model. ROI pixel lấy trực tiếp `image[mask>0]`; ảnh da/tóc nền đen chỉ dùng hiển thị, không làm đầu vào histogram.

<!-- PAGE 17: Chương 4 — B1 -->

# 4.2. B1 — HSV 2D HISTOGRAM

Hue H mô tả hướng sắc màu, Saturation S mô tả độ bão hòa, Value V biểu diễn độ sáng trong HSV. [PDF §2.3.1, tr.12] chọn H và S để mô tả phổ màu/bão hòa, không lấy V trong histogram. Điều này giảm phụ thuộc trực tiếp V nhưng không tạo bất biến hoàn toàn với ánh sáng/cân bằng trắng.

12 Hue ×4 Saturation =48 chiều/vùng, 96 cho hai vùng. [D01] HSV uint8: H=0…179, S=0…255; cạnh H=0,15,…,180 và S=0,64,…,256. Với H,S hợp lệ: `h=floor(H/15)`, `s=floor(S/64)`, index trong HS48 là `4*h+s`. Ví dụ số học H=16,S=70 thuộc h=1,s=1,index=5; đây là ví dụ gán bin, không giả mạo pixel/nhãn thật.


$$
h'_k=\frac{n_k}{\sum_i n_i},\qquad \sum_{k=0}^{47}h'_k=1
$$
![Hình 5. H–S thực của da và tóc cfd_final_00001.png; colorbar là tần suất sau L1.](figures/HS_histograms.png)

*Hình 5. H–S thực của da và tóc cfd_final_00001.png; colorbar là tần suất sau L1.*

Ở ảnh thật, bin da cực đại h=1,s=1 có khối lượng **0.515282**, tóc cực đại h=0,s=1 có khối lượng **0.258604**. Cả hai histogram tổng đúng 1 theo artifact.

Không cộng pixel nền đen ngoài mask; pixel đen thật trong mask vẫn được đếm (H=0,S=0 theo biểu diễn OpenCV). Không loại pixel S thấp theo cảm nhận: D11 chỉ ghi warning. Thay cạnh bin làm đổi phân bố dù tổng số chiều không đổi; biên bin là quy ước được chấp thuận, không phải tất cả đều được PDF ghi nguyên văn.

<!-- PAGE 18: Chương 4 — B2 -->

# 4.3. B2 — CIE-LAB COLOR MOMENTS

L* là độ sáng cảm nhận, a* là trục lục–đỏ, b* là trục lam–vàng. [PDF §2.3.2, tr.12] yêu cầu bốn thống kê trên ba kênh: 12/vùng, 24 cho hai vùng. [D02] BGR float32/255 → Lab float OpenCV, rồi mô-men float64; không dùng Lab uint8 có offset/scale như một phép thay thế ngầm.

[APPROVED D03–D05] Với N pixel có trọng số bằng nhau:

$$
\mu=\frac{1}{N}\sum_i x_i,\quad m_k=\frac{1}{N}\sum_i(x_i-\mu)^k
$$

$$
\sigma=\sqrt{m_2},\quad \operatorname{skew}=\frac{m_3}{\sigma^3},\quad \operatorname{kurt}=\frac{m_4}{\sigma^4}
$$

Mean biểu diễn mức màu trung tâm; std đo độ phân tán; skew mô tả bất đối xứng; kurtosis nhạy với đuôi/phần giá trị cực đoan. Đó không phải phép đo chất lượng ảnh độc lập. Code dùng std quần thể ddof=0, skew không bias và **Pearson kurtosis**, không trừ 3. PDF liệt kê tên thống kê nhưng không chốt các chi tiết này.

**Ví dụ giải tích** x={0,0,0,4}: μ=1; các sai lệch {−1,−1,−1,3}; m2=3, m3=6, m4=21. Vì vậy std=√3=1,732051; skew=2/√3=1,154701; Pearson=7/3=2,333333 (excess sẽ là −0,666667). Đây là oracle số học, không phải nhãn hoặc ảnh giả trong dataset.

| ROI/kênh | Mean | Std | Skew | Pearson |
|---|---|---|---|---|
| skin L* | 70.31785 | 8.98516 | -2.07193 | 10.67935 |
| skin a* | 9.09620 | 2.08260 | 0.91053 | 7.51477 |
| skin b* | 23.47390 | 2.93696 | -2.02431 | 14.42218 |
| hair L* | 21.94723 | 23.20562 | 1.62627 | 4.78546 |
| hair a* | 1.76485 | 2.15065 | 0.19552 | 6.23997 |
| hair b* | 4.43500 | 4.22328 | 1.33926 | 4.99006 |

Bảng 1. Mô-men thật của cfd_final_00001.png. Nếu std<1e-12, code đặt std/skew/kurt=0 và warning; đây là fallback đã chấp thuận vì skew/kurt kênh hằng không xác định. Vùng <100 pixel không được áp fallback để tạo vector giả.

<!-- PAGE 19: Chương 4 — B3 -->

# 4.4. B3 — CIRCULAR HUE STATISTICS

H=179 và H=1 có khoảng cách số học 178 nhưng gần nhau trên vòng Hue. Trung bình số học bằng 90 chỉ về phía đối diện; cần thống kê hướng (directional statistics). [PDF §2.3.3, tr.13] quy định histogram Hue10 L1, góc φ=2πH/180, circular mean/std và miền [0,1].

$$
\varphi_i=\frac{2\pi H_i}{180},\quad C=\operatorname{mean}(\cos\varphi_i),\quad S=\operatorname{mean}(\sin\varphi_i)
$$

$$
R=\operatorname{clip}(\sqrt{C^2+S^2},0,1),\quad \bar H_c=\frac{\operatorname{atan2}(S,C)\bmod 2\pi}{2\pi}
$$

$$
s_c=\min\left(\frac{\sqrt{-2\log(\max(R,10^{-12}))}}{2\pi},1\right)
$$

Sin/cos chiếu hướng thành hai thành phần; mean của chúng là resultant. atan2 dùng cả dấu hai trục để xác định góc; modulo đưa góc về [0,2π), rồi chia 2π. R gần 1 biểu thị hướng tập trung; log tạo độ phân tán trong công thức hiện tại. Floor chống log(0), clip giữ miền. D06–D08 phê duyệt biểu thức cụ thể; PDF không cho đủ công thức scale std để gọi toàn bộ biểu thức là nguyên văn PDF.

![Hình 6. Ví dụ giải tích vòng Hue; không phải một ảnh/nhãn tổng hợp thay dataset.](figures/hue_circle.png)

*Hình 6. Ví dụ giải tích vòng Hue; không phải một ảnh/nhãn tổng hợp thay dataset.*

Với H={179,1}, R=cos(π/90)=**0.999390827**, mean vòng≈0, std vòng=**0.005556120**. Với R<1e-8, mean=0 kèm warning; std tiếp tục theo floor/clip. Mean dạng scalar vẫn có mép vòng khi dùng Euclid; không tự đổi thành sin/cos tăng chiều.

<!-- PAGE 20: Chương 4 — Index Skin -->

# 4.5. B144 — ÁNH XẠ INDEX SKIN

Nguồn trực tiếp: `color_features_full_v1/feature_layout.csv`. B144=[Skin72,Hair72]; index bắt đầu từ 0. Trang này liệt kê đủ 72 chiều Skin, không chỉ mô tả theo khoảng. Tên cùng schema phải dùng thống nhất trong vector, stats và query.

| Index | Tên chính xác | Index | Tên chính xác |
|---|---|---|---|
| 0 | skin_HS_h00_s0 | 36 | skin_HS_h09_s0 |
| 1 | skin_HS_h00_s1 | 37 | skin_HS_h09_s1 |
| 2 | skin_HS_h00_s2 | 38 | skin_HS_h09_s2 |
| 3 | skin_HS_h00_s3 | 39 | skin_HS_h09_s3 |
| 4 | skin_HS_h01_s0 | 40 | skin_HS_h10_s0 |
| 5 | skin_HS_h01_s1 | 41 | skin_HS_h10_s1 |
| 6 | skin_HS_h01_s2 | 42 | skin_HS_h10_s2 |
| 7 | skin_HS_h01_s3 | 43 | skin_HS_h10_s3 |
| 8 | skin_HS_h02_s0 | 44 | skin_HS_h11_s0 |
| 9 | skin_HS_h02_s1 | 45 | skin_HS_h11_s1 |
| 10 | skin_HS_h02_s2 | 46 | skin_HS_h11_s2 |
| 11 | skin_HS_h02_s3 | 47 | skin_HS_h11_s3 |
| 12 | skin_HS_h03_s0 | 48 | skin_Lab_L_mean |
| 13 | skin_HS_h03_s1 | 49 | skin_Lab_L_std |
| 14 | skin_HS_h03_s2 | 50 | skin_Lab_L_skew |
| 15 | skin_HS_h03_s3 | 51 | skin_Lab_L_kurtosis |
| 16 | skin_HS_h04_s0 | 52 | skin_Lab_a_mean |
| 17 | skin_HS_h04_s1 | 53 | skin_Lab_a_std |
| 18 | skin_HS_h04_s2 | 54 | skin_Lab_a_skew |
| 19 | skin_HS_h04_s3 | 55 | skin_Lab_a_kurtosis |
| 20 | skin_HS_h05_s0 | 56 | skin_Lab_b_mean |
| 21 | skin_HS_h05_s1 | 57 | skin_Lab_b_std |
| 22 | skin_HS_h05_s2 | 58 | skin_Lab_b_skew |
| 23 | skin_HS_h05_s3 | 59 | skin_Lab_b_kurtosis |
| 24 | skin_HS_h06_s0 | 60 | skin_Hue_bin00 |
| 25 | skin_HS_h06_s1 | 61 | skin_Hue_bin01 |
| 26 | skin_HS_h06_s2 | 62 | skin_Hue_bin02 |
| 27 | skin_HS_h06_s3 | 63 | skin_Hue_bin03 |
| 28 | skin_HS_h07_s0 | 64 | skin_Hue_bin04 |
| 29 | skin_HS_h07_s1 | 65 | skin_Hue_bin05 |
| 30 | skin_HS_h07_s2 | 66 | skin_Hue_bin06 |
| 31 | skin_HS_h07_s3 | 67 | skin_Hue_bin07 |
| 32 | skin_HS_h08_s0 | 68 | skin_Hue_bin08 |
| 33 | skin_HS_h08_s1 | 69 | skin_Hue_bin09 |
| 34 | skin_HS_h08_s2 | 70 | skin_circular_mean |
| 35 | skin_HS_h08_s3 | 71 | skin_circular_std |

HS48 flatten theo Hue ngoài/S trong. Lab12 theo L,a,b và trong mỗi kênh mean,std,skew,kurtosis. Hue10 tiếp theo, cuối cùng mean vòng và std vòng. Hoán vị đồng bộ toàn bộ vector/stats giữ Euclid; trộn hai serialization khác nhau làm kết quả sai dù shape vẫn 144. D13 chốt thứ tự này, PDF không liệt kê từng index.

<!-- PAGE 21: Chương 4 — Index Hair -->

# 4.5. B144 — ÁNH XẠ INDEX HAIR

Nguồn trực tiếp: `color_features_full_v1/feature_layout.csv`. B144=[Skin72,Hair72]; index bắt đầu từ 0. Trang này liệt kê đủ 72 chiều Hair, không chỉ mô tả theo khoảng. Tên cùng schema phải dùng thống nhất trong vector, stats và query.

| Index | Tên chính xác | Index | Tên chính xác |
|---|---|---|---|
| 72 | hair_HS_h00_s0 | 108 | hair_HS_h09_s0 |
| 73 | hair_HS_h00_s1 | 109 | hair_HS_h09_s1 |
| 74 | hair_HS_h00_s2 | 110 | hair_HS_h09_s2 |
| 75 | hair_HS_h00_s3 | 111 | hair_HS_h09_s3 |
| 76 | hair_HS_h01_s0 | 112 | hair_HS_h10_s0 |
| 77 | hair_HS_h01_s1 | 113 | hair_HS_h10_s1 |
| 78 | hair_HS_h01_s2 | 114 | hair_HS_h10_s2 |
| 79 | hair_HS_h01_s3 | 115 | hair_HS_h10_s3 |
| 80 | hair_HS_h02_s0 | 116 | hair_HS_h11_s0 |
| 81 | hair_HS_h02_s1 | 117 | hair_HS_h11_s1 |
| 82 | hair_HS_h02_s2 | 118 | hair_HS_h11_s2 |
| 83 | hair_HS_h02_s3 | 119 | hair_HS_h11_s3 |
| 84 | hair_HS_h03_s0 | 120 | hair_Lab_L_mean |
| 85 | hair_HS_h03_s1 | 121 | hair_Lab_L_std |
| 86 | hair_HS_h03_s2 | 122 | hair_Lab_L_skew |
| 87 | hair_HS_h03_s3 | 123 | hair_Lab_L_kurtosis |
| 88 | hair_HS_h04_s0 | 124 | hair_Lab_a_mean |
| 89 | hair_HS_h04_s1 | 125 | hair_Lab_a_std |
| 90 | hair_HS_h04_s2 | 126 | hair_Lab_a_skew |
| 91 | hair_HS_h04_s3 | 127 | hair_Lab_a_kurtosis |
| 92 | hair_HS_h05_s0 | 128 | hair_Lab_b_mean |
| 93 | hair_HS_h05_s1 | 129 | hair_Lab_b_std |
| 94 | hair_HS_h05_s2 | 130 | hair_Lab_b_skew |
| 95 | hair_HS_h05_s3 | 131 | hair_Lab_b_kurtosis |
| 96 | hair_HS_h06_s0 | 132 | hair_Hue_bin00 |
| 97 | hair_HS_h06_s1 | 133 | hair_Hue_bin01 |
| 98 | hair_HS_h06_s2 | 134 | hair_Hue_bin02 |
| 99 | hair_HS_h06_s3 | 135 | hair_Hue_bin03 |
| 100 | hair_HS_h07_s0 | 136 | hair_Hue_bin04 |
| 101 | hair_HS_h07_s1 | 137 | hair_Hue_bin05 |
| 102 | hair_HS_h07_s2 | 138 | hair_Hue_bin06 |
| 103 | hair_HS_h07_s3 | 139 | hair_Hue_bin07 |
| 104 | hair_HS_h08_s0 | 140 | hair_Hue_bin08 |
| 105 | hair_HS_h08_s1 | 141 | hair_Hue_bin09 |
| 106 | hair_HS_h08_s2 | 142 | hair_circular_mean |
| 107 | hair_HS_h08_s3 | 143 | hair_circular_std |

HS48 flatten theo Hue ngoài/S trong. Lab12 theo L,a,b và trong mỗi kênh mean,std,skew,kurtosis. Hue10 tiếp theo, cuối cùng mean vòng và std vòng. Hoán vị đồng bộ toàn bộ vector/stats giữ Euclid; trộn hai serialization khác nhau làm kết quả sai dù shape vẫn 144. D13 chốt thứ tự này, PDF không liệt kê từng index.

<!-- PAGE 22: Chương 5 — Z-score B -->

# CHƯƠNG 5. Z-SCORE BỘ B

## 5.1. Các lớp chuẩn hóa và tập fit

Histogram H–S và Hue10 được L1 riêng trong mỗi ROI; circular mean/std đưa về [0,1]; ghép đủ B144 rồi **một lần Z-score all144**. D14 chốt cách hiện thực thống nhất này. §2.3.3 (PDF 13) và §2.5.2 (PDF 17) diễn đạt khác về mô-men trước ghép; không khẳng định PDF chỉ cho duy nhất trình tự trên.

Fit mean/std ddof=0 trên **tất cả 1.437 vector hợp lệ** của kho 1.438 ảnh. `hf_merged_00209.png` không có tóc raw nên không có B144. Không có hàng vector zero/NaN để che thiếu. fit_manifest lưu danh sách ảnh, feature index và hash; warning không tự loại ảnh hợp lệ.


$$
d_j=1\ (\sigma_j<10^{-8}),\quad d_j=\sigma_j\ (\sigma_j\geq10^{-8}),\qquad z_j=\frac{x_j-\mu_j}{d_j}
$$

## 5.2. So sánh chính xác với A

**Code A và B hiện cùng quy tắc divisor dạng std_safe** (ddof=0, ngưỡng 1e-8, thay bằng 1). Không bịa rằng mẫu số hai code khác nhau. Khác biệt quan trọng: A lệch phương trình σ+ε của PDF, còn B được D15 phê duyệt rõ; A lưu normalized float32, B lưu float64; tập fit A=1.438 và B=1.437, số chiều khác nhau.

![Hình 7. Ba chiều B thật trước/sau Z-score; không L1 lại sau bước cuối.](figures/B_distributions.png)

*Hình 7. Ba chiều B thật trước/sau Z-score; không L1 lại sau bước cuối.*

## 5.3. Query và giới hạn

Query dùng đúng mean/divisor đã lưu, không fit theo ảnh hoặc cặp query–candidate. Cột hằng có Z=0 trong training; query khác mean ở cột này vẫn chia 1 chứ không ép 0. Kho B hiện không có cột std<1e-8. Z-score có thể khuếch đại bin hiếm; histogram sau Z-score có thể âm và tổng khác 1. Không điều chỉnh để làm Top-5 đẹp hơn.

<!-- PAGE 23: Chương 6 — Euclid và A Top-5 -->

# CHƯƠNG 6. TÌM KIẾM TƯƠNG ĐỒNG

## 6.1. Euclid và luồng Top-5

$$
d(q,i)=\sqrt{\sum_{j=1}^{D}(z_{qj}-z_{ij})^2},\quad D=150\ (A),\ 144\ (B)
$$

Trích query → dùng stats kho của đúng bộ → tính Euclid → loại self theo quy ước → sắp tăng dần → lấy 5. Khoảng cách A/B chưa cùng thang đo để cộng trực tiếp. L2 ở đây có căn bậc hai; không thay bằng cosine hoặc Chi-square cho B.

**Code A:** query trích lại từ ảnh, Z float64; kho normalized float32 cast float64 trước tính d. Self-match theo `Path(image_path).resolve()`; `np.argsort` mặc định, không có tie-break theo tên được code quy định rõ.

**Code B:** query dùng cùng schema và stats, self theo image_id (có nhận diện hash duy nhất khi gọi API); hòa d theo tên file (`lexsort`). Không tự áp quy ước B hồi tố lên A.

![Hình 8. Top-5 A thật đã lưu cho cfd_final_00144.png; d và tên được kiểm tra lại, không ghi đè artifact.](figures/saved_A_grid.png)

*Hình 8. Top-5 A thật đã lưu cho cfd_final_00144.png; d và tên được kiểm tra lại, không ghi đè artifact.*

| Hạng | Ảnh kết quả | Euclid A |
|---|---|---|
| 1 | cfd_final_00325.png | 6.324556 |
| 2 | hf_merged_00429.png | 6.436708 |
| 3 | cfd_final_00352.png | 6.623885 |
| 4 | cfd_final_00510.png | 6.795212 |
| 5 | cfd_final_00340.png | 6.798524 |

Danh tính ảnh trong 6 ô PNG gốc được xác định bằng khớp pixel với dataset; thứ tự khớp tính lại từ ma trận thật. Hình gốc một hàng giữ ở figures/original_A_top5.png. Khoảng cách bảng dùng độ chính xác tính lại; nhãn PNG lịch sử làm tròn ba chữ số.

<!-- PAGE 24: Chương 6 — B Top-5 -->

# 6.2. TOP-5 B — KẾT QUẢ ĐÃ LƯU

Query `cfd_final_00537.png`, dùng B144_raw_v1.0.0 và stats kho hợp lệ 1.437 ảnh. Dữ liệu tên/thứ tự/d lấy từ `retrieval/top5.csv`, hình gốc từ `retrieval/queries/`; không tự gán các ảnh “trông giống” để thay cho kết quả máy.

![Hình 9. Query và Top-5 B thật; bố cục lại từ ảnh thật, giữ tên, thứ tự và khoảng cách artifact.](figures/saved_B_grid.png)

*Hình 9. Query và Top-5 B thật; bố cục lại từ ảnh thật, giữ tên, thứ tự và khoảng cách artifact.*

| Hạng | Ảnh kết quả | Euclid B |
|---|---|---|
| 1 | cfd_final_00536.png | 1.174659 |
| 2 | cfd_final_00535.png | 1.651839 |
| 3 | cfd_final_00539.png | 2.474773 |
| 4 | cfd_final_00702.png | 3.800347 |
| 5 | cfd_final_00699.png | 3.839057 |

Với query trong kho hợp lệ, sau bỏ self còn 1.436 ứng viên B. Các ảnh khác cùng người/khác biểu cảm vẫn có thể xuất hiện; image_id là ID ảnh, không phải danh tính người. Kho dữ liệu có ảnh cùng người theo mô tả PDF, nhưng việc kết quả gần không chứng minh thuật toán nhận diện đúng người.

Đây là minh họa khả năng vận hành: không có nhãn relevance độc lập để tính accuracy, precision/recall hoặc mAP truy hồi. Các số d chỉ là khoảng cách trong không gian B đã chuẩn hóa; không so sánh trực tiếp d nhỏ của A với d của B để chọn bộ tốt hơn.

Tập 10 query đã lưu của B gồm 5 CFD +5 HF, chọn theo độ phủ mean Lab. Quy tắc chọn query không thay metric; kiểm tra đủ 50 dòng không self-match đã có trong hồ sơ v1. Báo cáo này không sửa công thức dựa trên kết quả nhìn thấy.

<!-- PAGE 25: Chương 6 — So sánh cùng query -->

# 6.3. SO SÁNH ĐÚNG PHẠM VI

Hai hình trước là các ví dụ **đã lưu** nhưng khác query; không dùng chúng để kết luận A/B thắng nhau. Để minh họa cùng đầu vào, bảng dưới giữ kết quả A đã lưu cho CFD00144 và tính kiểm tra B từ hàng B144 normalized thật của đúng ảnh đó. Phần B bổ sung chỉ ghi dưới docs/reports/_build/report_only_B_same_query.csv; không thay kết quả Top-5 hiện có trong outputs.

| Hạng | A: tên ảnh | dA | B: tên ảnh | dB |
|---|---|---|---|---|
| 1 | cfd_final_00325.png | 6.3246 | cfd_final_00346.png | 10.2004 |
| 2 | hf_merged_00429.png | 6.4367 | cfd_final_00146.png | 10.6407 |
| 3 | cfd_final_00352.png | 6.6239 | cfd_final_00145.png | 10.8115 |
| 4 | cfd_final_00510.png | 6.7952 | cfd_final_00334.png | 11.1250 |
| 5 | cfd_final_00340.png | 6.7985 | cfd_final_00347.png | 11.8573 |

![Hình 10. B cho query CFD00144, tính kiểm tra từ artifact thật; không gắn nhãn giả là PNG lịch sử đã lưu.](figures/derived_B_same_query.png)

*Hình 10. B cho query CFD00144, tính kiểm tra từ artifact thật; không gắn nhãn giả là PNG lịch sử đã lưu.*

A đo cấu trúc điểm và tỉ lệ; B đo phân bố màu trong ROI. Hai bộ có thể chọn ảnh khác nhau theo tiêu chí mà mỗi bộ biểu diễn. Không được suy ra chất lượng định danh hoặc “A+B đã hoàn thiện”. Một phân bố màu tương tự có thể thuộc hình học khác và ngược lại.

**Ba loại đánh giá khác nhau:** unit test xác nhận thuật toán số; đánh giá segmentation cần mask thủ công độc lập cùng protocol ROI; đánh giá retrieval cần nhãn/tiêu chí relevance và giao thức query/gallery. Không chuyển một loại kiểm tra thành số đo của loại còn lại.

<!-- PAGE 26: Chương 7 — Kết quả và kiểm chứng -->

# CHƯƠNG 7. KẾT QUẢ VÀ HẠN CHẾ

## 7.1. Tổng hợp đo trực tiếp

| Hạng mục | Bộ A | Bộ B |
|---|---|---|
| Shape raw / normalized | (1438,150) / (1438,150) | (1437,144) / (1437,144) |
| Ảnh không có vector | 0 theo failed_images.csv | 1: hf_merged_00209.png |
| Dtype raw / Z | float32 / float32 | float64 / float64 |
| Fit theo cột | 1.438 hàng hợp lệ | 1.437 hàng hợp lệ |
| Chiều std<1e-8 | 0 | 0 |
| NaN/Inf trong matrices | 0 | 0 |
| Max abs(mean Z) | 2.400e-09 | 2.624e-15 |
| Max abs(std Z−1) | 3.433e-09 | 4.086e-14 |
| Sai số reconstruct so với float64 | 2.346e-07 (cast32) | 0.000e+00 |

Số đo mean/std trên đây được tính lại trong lần audit này, không sao chép summary để giả là kiểm tra độc lập. Sai số giảm tổng/cách bố trí mảng ở mức floating point có thể khác chữ số cuối so với summary lúc trích; ma trận không bị thay đổi. A khớp chính xác khi reconstruct rồi cast32; B reconstruct đúng bằng stats lưu.

## 7.2. Kiểm thử kỹ thuật

40/40 color unit tests chạy lại thành công trong .venv-uniface, log lưu riêng dưới _build. Repo chưa có bộ unit test riêng đầy đủ cho A; báo cáo bổ sung kiểm tra số học độc lập của 14 A2 trên tọa độ thật, sai số tối đa 3,345e-7, tái tạo A150 sample bằng đúng hàng kho, và đối chiếu trực tiếp thống kê toàn ma trận. Không gọi những kiểm tra này là accuracy.

B v1 đã có hồ sơ xác minh 2.876 raw mask, 5.748 histogram L1, đủ 144 chiều và 50 dòng Top-5. Báo cáo đối chiếu lại dtype/shape/finite/statistics và nguồn; không chạy lại segmentation hoặc trích toàn kho. Chỉ chạy landmarks cho một ảnh thật để dựng hình/ví dụ, không ghi vào kho A.

## 7.3. Sai lệch A cần nêu rõ

Mẫu số A std_safe không giống σ+ε của PDF. Face-height và các điểm đại diện gò má/hàm là proxy hiện thực; mapping 68 điểm không được PDF liệt kê đủ để xác nhận từng nút. Bản đồ 2D, pose, ánh sáng tác động detector và biểu cảm đều có thể ảnh hưởng A. Không sửa code hoặc che các giới hạn này bằng tên “đặc trưng nhân trắc”.

<!-- PAGE 27: Chương 7 — ROI và hướng tiếp theo -->

# 7.4. CHẤT LƯỢNG MASK VÀ DỮ LIỆU THIẾU

B có **1.169 ảnh có warning raw/feature**, trong đó **1.168 vector hợp lệ**; warning không tự loại khỏi fit. Có **305 ảnh abs(Z)>5** ở ít nhất một chiều theo hồ sơ v1, không đồng nghĩa 305 lỗi. Pixel tóc ít nhất trong các vector hợp lệ là **106**; ngưỡng 100 không bảo đảm tính đại diện màu tóc.

![Hình 11. Hai dự đoán thật: khăn che tóc HF00694 và tay che mặt HF00722; không phải nhãn chuẩn.](figures/mask_caveats.png)

*Hình 11. Hai dự đoán thật: khăn che tóc HF00694 và tay che mặt HF00722; không phải nhãn chuẩn.*

Ở HF00694, hair raw chỉ 355 pixel sát mép trên, dễ không đại diện cho tóc nhìn thấy. Ở HF00722, raw skin quan sát chứa phần tay; không có nhãn độc lập để định lượng ảnh hưởng. HF00676 có tóc hồng hiếm và kết quả khác màu quan sát; không thay công thức để tối ưu ví dụ này. HF00209 có hair=0; trạng thái thiếu là dữ liệu được công khai, không bịa màu tóc.

## 7.5. Trước khi chuyển sang C

Cần protocol ROI và relevance độc lập nếu muốn đo chất lượng, đặc biệt khi nhiều người, che khuất, nền phức tạp hoặc hue ít bão hòa. Nhãn thủ công lịch sử không tự trở thành bộ GT đầy đủ cho UniFace toàn kho hoặc nhãn truy hồi.

Giữ đúng thiết kế §2.5: khi kết hợp, dùng median normalization từng d rồi tổng trọng số không âm, tổng bằng 1. Ghép theo image_id/a_row_index, không theo số hàng mặc định vì B thiếu một ảnh. Không gán dB=0 hay vector B=0 để che thiếu. C1/C2 và A+B fusion chưa triển khai; tài liệu không tự công bố chúng đã hoàn thiện.

<!-- PAGE 28: Nguồn và tái lập -->

# NGUỒN, KIỂM CHỨNG VÀ TÁI LẬP

## 8.1. Nguồn chính và hồ sơ cục bộ

1. Báo cáo nhóm `csdldpt.pdf`, 18 trang; SHA-256 **8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80**. Các công thức viện dẫn từ tr.9–13 và 17; quy trình dataset tại tr.4–5.
2. A: `geometry_features.py`, `extract_all_features.py`, `normalize_features.py`, `map_68_landmarks.py`; `shared/paths.py`, `shared/detect_landmarks.py`; `retrieval/search_geometry.py`.
3. B: `color_features.py`, `full_color.py`, `search_full_color.py`, `verify_full_color.py`, `batch_uniface.py`; schema/feature_layout/stats/manifest của color_features_full_v1.
4. `docs/report_compliance_audit.md`, `B_implementation_decisions.md`, `B_color_feature_spec.md`, `B_color_final_report.md`; README/metadata dataset và log tests.

Không dùng nguồn web để bổ sung ngầm công thức. Phần giải thích toán học suy ra trực tiếp từ công thức và dữ liệu, được phân biệt với trích dẫn báo cáo. Chi tiết source của 42 module được lưu cùng hash/dòng/hàm trong `_build/source_inventory.json` và bản source_review.txt để truy vết, gồm cả module cũ không thuộc pipeline B v1.

## 8.2. File đi kèm

`A_B_Feature_Analysis.md` là bản nguồn có thể chỉnh sửa; `A_B_Formula_Audit.md` đối chiếu công thức; `A_B_Report_Validation.md` ghi kiểm tra dữ liệu/PDF. Hình, số liệu và script build đặt trong figures/ và _build/. Công thức LaTeX trong Markdown được render SVG vector, không chụp công thức bằng ảnh mờ.

Muốn render lại sau khi chỉnh Markdown: chạy `.venv311\Scripts\python.exe -X utf8 -B docs/reports/_build/render_report.py`, rồi Chrome headless theo lệnh trong file validation. Không cần cài thư viện hoặc tải model. Không chạy main của extractor/normalizer A/B để tạo báo cáo.

## 8.3. Phạm vi bảo toàn

Hash được chụp trước/sau cho source, artifact, dataset, annotations, model và PDF gốc, loại trừ thư mục báo cáo mới và bytecode cache. Mọi sai lệch được ghi, không tự sửa thuật toán. Kiểm tra PDF gồm A4, số trang, font tiếng Việt, cấu trúc bảng/công thức, không tràn vùng nội dung và raster từng trang để review.

Báo cáo mô tả **hệ thống đã quan sát**, nêu rõ phần chưa đủ bằng chứng. Vector hữu hạn, unit tests đạt và Top-5 vận hành không thay thế đánh giá phân đoạn hoặc nhận diện có ground truth.
