# A/B — Đối chiếu công thức với báo cáo và source hiện tại

Ngày 22/11/2026. PDF chuẩn SHA-256 8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80. Số trang PDF từ 1. Không sửa thuật toán hoặc artifact.

## Bộ A

`geometry_features.py` là nguồn extractor; `map_68_landmarks.py` là công cụ vẽ. A1 interleaved x,y theo INDICES; A2 nối đúng thứ tự 14 mục. Các ID landmarks/epsilon trong A2 là quy ước code khi PDF chưa quy định đủ, không đánh EXACT cho toàn bộ biểu thức chỉ vì tên trùng báo cáo.

| Mục | PDF | Code/công thức đang dùng | Trạng thái/ảnh hưởng |
|---|---|---|---|
| 478 → 68 | §2.2.2, tr.8 | INDICES chọn 68 nút từ model 478; num_faces=1 | IMPLEMENTATION DETAIL: PDF không cho đủ mapping; cap output không chứng minh ảnh chỉ có một người |
| Chuẩn hóa điểm | §2.2.2, tr.9 | p′=(p−c)/d; c=mid(mean(p36:42),mean(p42:48)) | EXACT về công thức; IMPLEMENTATION DETAIL về định nghĩa tâm bằng 6 nút |
| A1/A2 | §2.2.3, tr.9–10 | 136 tọa độ +14 ratio/angle; float32 | EXACT về kích thước; serialization là quy ước |
| Z-score A | §2.5.2, tr.17 | where(std<1e-8,1,std), không phải std+epsilon | DEVIATION: không được nói hai cách giống nhau; ε PDF chưa cho trị số |
| Query A | §2.5.2, tr.17 | Dùng stats kho, gallery float32/query float64 | EXACT reuse; precision và self-match theo đường dẫn là implementation detail |

## Đủ 14 thành phần A2

Ký hiệu D(a,b)=Euclid2D; eL/eR là mean 6 điểm mắt; c=(eL+eR)/2; d=D(eL,eR); h=D((p21+p22)/2,p8); epsilon ratio=1e-8. Nguồn hàm `geometry_features.calculate_ratios`, với `angle_degrees` cho mục 14. PDF §2.2.3 tr.9–10 nêu tên, tỉ lệ và ý nghĩa; công thức điểm cụ thể bên dưới là hiện thực code.

### A2-01: Rộng gò má / cao mặt

- Index A150: 136; landmarks p2,14,21,22,8.
- Công thức code: `\frac{D(p_2,p_{14})}{h+\epsilon}`.
- Ví dụ ảnh thật: `157.164312/(150.211240+1e-8)` → 1.046288610.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Code dùng p2–p14 làm đại diện bề ngang; h từ trung điểm mày đến cằm, không phải một phép đo gò má/đỉnh trán được PDF quy định đủ. Góc chụp ảnh hưởng cả hai độ dài.

### A2-02: Khoảng cách hai mắt / cao mặt

- Index A150: 137; landmarks p36…47,21,22,8.
- Công thức code: `\frac{d}{h+\epsilon}`.
- Ví dụ ảnh thật: `80.790850/(150.211240+1e-8)` → 0.537848175.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Tâm mắt là trung bình 6 điểm mỗi mắt. Nhắm mắt, nheo mắt hoặc mày/cằm sai làm thay đổi tỉ lệ; không phải khoảng cách đồng tử đo trực tiếp.

### A2-03: Bề ngang mắt trái / khoảng cách hai mắt

- Index A150: 138; landmarks p36,39 và 36…47.
- Công thức code: `\frac{D(p_{36},p_{39})}{d+\epsilon}`.
- Ví dụ ảnh thật: `32.228357/(80.790850+1e-8)` → 0.398910999.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Đầu mút 36/39 do mapping quyết định. Tư thế nghiêng và che khuất làm bề ngang chiếu trên ảnh thay đổi; nhãn trái/phải theo code.

### A2-04: Bề ngang mắt phải / khoảng cách hai mắt

- Index A150: 139; landmarks p42,45 và 36…47.
- Công thức code: `\frac{D(p_{42},p_{45})}{d+\epsilon}`.
- Ví dụ ảnh thật: `32.753391/(80.790850+1e-8)` → 0.405409724.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Chênh hai phía có thể do phối cảnh, che khuất hoặc sai điểm, không tự kết luận là bất đối xứng giải phẫu.

### A2-05: Độ mở mi mắt trái

- Index A150: 140; landmarks p37,41,38,40,36,39.
- Công thức code: `\frac{D(p_{37},p_{41})+D(p_{38},p_{40})}{2D(p_{36},p_{39})+\epsilon}`.
- Ví dụ ảnh thật: `(12.924338+13.184732)/(2×32.228357+1e-8)` → 0.405063659.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: PDF chỉ gọi tên độ mở mi. Công thức hai cặp dọc/chia bề ngang là quy ước code, nhạy mạnh với chớp mắt và nheo mắt.

### A2-06: Độ mở mi mắt phải

- Index A150: 141; landmarks p43,47,44,46,42,45.
- Công thức code: `\frac{D(p_{43},p_{47})+D(p_{44},p_{46})}{2D(p_{42},p_{45})+\epsilon}`.
- Ví dụ ảnh thật: `(13.589474+13.294606)/(2×32.753391+1e-8)` → 0.410401464.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Không thể coi khác biệt chớp mắt là khác danh tính. Bề ngang gần 0 hoặc sai landmark có thể làm tỉ lệ tăng bất thường.

### A2-07: Rộng cánh mũi / khoảng cách hai mắt

- Index A150: 142; landmarks p31,35 và 36…47.
- Công thức code: `\frac{D(p_{31},p_{35})}{d+\epsilon}`.
- Ví dụ ảnh thật: `46.784446/(80.790850+1e-8)` → 0.579081059.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Việc gán hai nút MediaPipe cho p31/p35 là xấp xỉ giải phẫu của mapping; phối cảnh hoặc tay che mũi làm sai khoảng cách.

### A2-08: Rộng miệng / khoảng cách hai mắt

- Index A150: 143; landmarks p48,54 và 36…47.
- Công thức code: `\frac{D(p_{48},p_{54})}{d+\epsilon}`.
- Ví dụ ảnh thật: `54.961407/(80.790850+1e-8)` → 0.680292547.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Nụ cười và biểu cảm làm khóe miệng dịch rõ; đây vừa là thông tin hình thái vừa nhạy với trạng thái ảnh.

### A2-09: Độ mở môi / khoảng cách hai mắt

- Index A150: 144; landmarks p62,66 và 36…47.
- Công thức code: `\frac{D(p_{62},p_{66})}{d+\epsilon}`.
- Ví dụ ảnh thật: `1.596677/(80.790850+1e-8)` → 0.019763097.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Dùng đúng cặp môi trong 62/66 của code. Biểu cảm và phát âm làm thay đổi lớn; số gần 0 không chứng minh môi đóng tuyệt đối khi landmark có nhiễu.

### A2-10: Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt

- Index A150: 145; landmarks p36…47 và 30.
- Công thức code: `\frac{D(c,p_{30})}{d+\epsilon}`.
- Ví dụ ảnh thật: `47.144439/(80.790850+1e-8)` → 0.583537042.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Code dùng Euclid 2D, nên chịu cả lệch ngang lẫn dọc; không phải chỉ lấy chênh tọa độ y. Đầu mũi theo mapping là p30.

### A2-11: Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt

- Index A150: 146; landmarks p36…47,48,54.
- Công thức code: `\frac{D(c,(p_{48}+p_{54})/2)}{d+\epsilon}`.
- Ví dụ ảnh thật: `78.895153/(80.790850+1e-8)` → 0.976535797.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Code chọn trung điểm hai khóe miệng. PDF không chỉ rõ cách tổng hợp hai khóe; cười làm điểm giữa dịch chuyển.

### A2-12: Khoảng cách chóp mũi–đáy cằm / cao mặt

- Index A150: 147; landmarks p30,8,21,22.
- Công thức code: `\frac{D(p_{30},p_8)}{h+\epsilon}`.
- Ví dụ ảnh thật: `74.196541/(150.211240+1e-8)` → 0.493947983.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Cằm bị cắt, râu/phụ kiện hoặc landmark sai có thể làm thay đổi số đo. h là proxy mày–cằm, không phải một chiều cao giải phẫu được xác thực.

### A2-13: Rộng xương hàm / cao mặt

- Index A150: 148; landmarks p4,12,21,22,8.
- Công thức code: `\frac{D(p_4,p_{12})}{h+\epsilon}`.
- Ví dụ ảnh thật: `131.203921/(150.211240+1e-8)` → 0.873462677.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: Hai nút p4/p12 và phép chiếu 2D là lựa chọn code. Góc quay đầu và đường tóc/che khuất có thể làm landmark trôi.

### A2-14: Góc xương hàm tại cằm

- Index A150: 149; landmarks p4,8,12.
- Công thức code: `\theta=\frac{180}{\pi}\arccos\left(\operatorname{clip}\left(\frac{u\cdot v}{\|u\|\|v\|},-1,1\right)\right)`.
- Ví dụ ảnh thật: `u=(-63.8098,-32.6512), v=(67.3838,-31.0021); dot=-3287.4900; norm(u)norm(v)=5316.6317; acos(dot/norms)×180/π` → 128.195068359.
- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.
- Hạn chế: angle_degrees từ chối tích norm<1e-8; clip chống lỗi acos do làm tròn. Mapping điểm góc hàm chưa có chứng nhận giải phẫu độc lập.

## Bộ B — yêu cầu PDF và quy ước đã được phê duyệt

| Thành phần | Nguồn PDF | Code/schema thực tế | Phân loại |
|---|---|---|---|
| HS12×4, L1 | §2.3.1, tr.12 | region_descriptor; bins (12,4), H [0,180), S [0,256) | EXACT số bins/L1; cạnh bin D01 APPROVED |
| CIE-Lab 4×3 | §2.3.2, tr.12 | BGR float32/255 → Lab, mô-men float64 | EXACT tên/chiều; D02 APPROVED đơn vị/precision |
| Std/skew/Pearson | §2.3.2, tr.12 | sqrt(m2), m3/std³, m4/std⁴; không trừ 3 | D03–D05 APPROVED; không gán công thức chi tiết cho PDF |
| Hue10 L1 | §2.3.3, tr.13 | np.histogram 10 bin, [0,180), L1 | EXACT số bin/miền/L1; cạnh D01 APPROVED |
| Phi | §2.3.3, tr.13 | 2*pi*H/180 | EXACT biểu thức |
| Mean/std vòng | §2.3.3, tr.13 | atan2(S,C) modulo 2π /2π; min(sqrt(-2log(max(R,1e-12)))/2π,1) | D06–D08 APPROVED; PDF chỉ nêu góc/tên/[0,1] |
| ROI raw skin1/hair17 | §2.3, tr.11–13 | class1/class17; không erosion, không gộp nose | D09–D12 APPROVED, không phải UniFace được PDF chỉ định |
| B144 order | §2.3, tr.11–13 | Skin72,Hair72; HS48/Lab12/Hue10/mean/std | D13 APPROVED; đủ144, index đầy đủ trong báo cáo chính |
| Z-score B | §2.3.3, tr.13; §2.5.2, tr.17 | descriptor→concat→all144; ddof0, std<1e-8 divisor1 | D14–D16 APPROVED; không tuyên bố PDF chỉ cho một trình tự |
| Euclid/self/tie | §2.3.3, tr.13; §2.5, tr.17–18 | L2 đủ144; self ID; tie filename | EXACT Euclid; D17 APPROVED giao thức |

## Kết luận kiểm toán có giới hạn

A và B code hiện dùng cùng dạng std_safe, nhưng nguồn thẩm quyền khác: A đang khác mẫu số σ+ε của PDF; B được D15 phê duyệt. A lưu Z float32, B float64. Không sửa A để làm báo cáo đẹp hơn; không đổi công thức B theo ví dụ Top-5. A2 có đủ 14 tên theo PDF nhưng proxy mốc/chiều cao và các guard chưa được PDF liệt kê đủ. Chất lượng landmarks/ROI và relevance không được chứng nhận bởi kiểm tra số học.

Nguồn code đầy đủ và vị trí hàm: _build/source_inventory.json (42 module), _build/source_review.txt. Số liệu: _build/facts.json. Không triển khai hoặc kiểm toán công thức C1/C2 như thể đã có code.
