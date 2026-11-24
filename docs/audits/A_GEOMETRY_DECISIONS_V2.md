# Hồ sơ quyết định hình học A — phiên bản2

Ngày23/11/2026. PDF chuẩn SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đối chiếu đủ6 báo cáo audit; giữ chúng như baseline lịch sử. Source geometry SHA-256 hiện tại: `d784c626ee1b468183f16a1f9ad6cfdfe063c8acc612f211c7c84665e540112f`; byte không đổi so baseline.

## Phần PDF rõ và phạm vi v2 đã sửa

PDF §2.2 yêu cầu478→68,136 tọa độ chuẩn hóa theo `(p−C)/d`,14 đặc trưng như bảng trang9–10; Euclid150. §2.5.2 quy định Z-score `(x−mu)/(sigma+epsilon)`. Yêu cầu v2 đã chốt **epsilon1e-8,ddof0**; `report_v2.py` thực hiện đúng và giữ raw A150 bất biến. Việc chốt normalizer **không đồng thời phê duyệt** mọi MP index, tâm mắt, endpoint A2 hoặc ε guard A2 cũ.

API extractor cũ, `geometry_features.py`, `map_68_landmarks.py`, batch extractor và normalizer/query legacy không bị sửa. V2 chỉ dùng extractor hiện có cho raw query rồi áp dụng stats v2. Không đưa478 điểm hoặc thêm chiều mới vào A150.

## Mapping và thứ tự hiện hành

Các index68 dưới đây **0-based**. PDF minh họa hình68 nhưng không cung cấp đầy đủ bảng478→68 có thể dùng như canonical labels.

| Nhóm | Index68 | Index MediaPipe478 đang dùng | Kết luận |
| --- | --- | --- | --- |
| JAW | 0–16 | 234, 93, 132, 58, 172, 136, 150, 149, 152, 378, 379, 365, 397, 288, 361, 323, 454 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| LEFT_EYEBROW | 17–21 | 70, 63, 105, 66, 107 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| RIGHT_EYEBROW | 22–26 | 336, 296, 334, 293, 300 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| NOSE | 27–35 | 168, 6, 197, 1, 129, 48, 4, 278, 358 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| LEFT_EYE | 36–41 | 33, 160, 158, 133, 153, 144 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| RIGHT_EYE | 42–47 | 362, 385, 387, 263, 373, 380 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |
| MOUTH | 48–67 | 61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91, 78, 81, 13, 311, 308, 402, 14, 178 | UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên |

Chứng cứ: [mapping đủ68 điểm](evidence/landmark_mapping.csv), [hình PDF trang8](evidence/pdf_page8_X31.png), [ảnh mốc audit](evidence/cfd_final_00001_68_annotated.png). Số lượng68/nhóm/thứ tự x0,y0,… có kiểm chứng; đúng vị trí giải phẫu từng mốc vẫn cần canonical/annotation.

## Tâm mắt và phép biến đổi tọa độ

`L=mean(p36..41)`, `R=mean(p42..47)`, `C=(L+R)/2`, `d=||L−R||₂`, `p′=(p−C)/d`; A1 flatten136. Phép tịnh tiến/chia d được PDF quy định và oracle kiểm chứng. Cách lấy tâm mỗi mắt bằng6 mí chưa được PDF chốt; không tự chuyển sang MP468/473 dù audit đã đo iris riêng. Ngưỡng d<1e-6, norm góc<1e-8 và regularizer A2 `+1e-8` giữ nguyên, là quy ước hiện hành chưa được nâng thành nguyên văn PDF.

## Từng đặc trưng A2

Ký hiệu `D(i,j)=||p_i−p_j||₂`, `E=(L+R)/2`, `H=D((p21+p22)/2,p8)`, `e=1e-8`. File/hàm hiện hành cho cả14 hàng: `features/A_geometry/src/geometry_features.py::calculate_ratios`; STT14 gọi `angle_degrees`. Tất cả được giữ nguyên.

| STT | Phần PDF rõ | Mốc/định nghĩa code | Công thức hiện hành | Đơn vị | Trạng thái v2 | Thiếu chứng cứ/dấu hiệu | Phép thử cần có |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Rộng gò má / cao mặt (PDF 9) | p2=MP132,p14=MP361; H=D((p21=MP107+p22=MP336)/2,p8=MP152) | D(2,14)/(H+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Chưa chốt điểm zygion và định nghĩa chiều cao mặt: code dùng giữa đầu mày→cằm, không có bảng endpoint chuẩn PDF. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 2 | Khoảng cách hai mắt / cao mặt (PDF 9) | L=mean(p36..41), R=mean(p42..47); H như trên | d/(H+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Chưa chốt tâm mắt6 mí hay tâm đồng tử/iris, và endpoint cao mặt. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 3 | Bề ngang mắt trái / khoảng cách hai mắt (PDF 9) | p36=MP33,p39=MP133; d=∣∣L−R∣∣ | D(36,39)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Cần xác minh khóe mắt và quy ước trái theo giải phẫu hay theo ảnh. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 4 | Bề ngang mắt phải / khoảng cách hai mắt (PDF 9) | p42=MP362,p45=MP263; d=∣∣L−R∣∣ | D(42,45)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Cần xác minh khóe mắt và quy ước phải theo giải phẫu hay theo ảnh. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 5 | Độ mở mi mắt trái (PDF 9) | p37=MP160,p41=MP144,p38=MP158,p40=MP153; p36/p39 | (D(37,41)+D(38,40))/(2D(36,39)+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | PDF chỉ nêu độ mở mí, chưa quy định EAR trung bình2 đoạn/chiều ngang mắt. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 6 | Độ mở mi mắt phải (PDF 9) | p43=MP385,p47=MP380,p44=MP387,p46=MP373; p42/p45 | (D(43,47)+D(44,46))/(2D(42,45)+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | PDF chỉ nêu độ mở mí, chưa quy định EAR trung bình2 đoạn/chiều ngang mắt. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 7 | Rộng cánh mũi / khoảng cách hai mắt (PDF 9) | p31=MP129,p35=MP358 | D(31,35)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Chưa đủ bằng chứng MP129/358 đúng hai cánh mũi trong mọi ảnh. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 8 | Rộng miệng / khoảng cách hai mắt (PDF 9) | p48=MP61,p54=MP291 | D(48,54)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Cần canonical endpoints hai khóe môi; không đổi theo visual retrieval. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 9 | Độ mở môi / khoảng cách hai mắt (PDF 10) | p62=MP13,p66=MP14 | D(62,66)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Cần xác minh p62/p66 chính là cặp biên trong phù hợp độ mở môi. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 10 | Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt (PDF 10) | E=(L+R)/2; p30=MP1 | D(E,p30)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | p30=MP1 cần xác minh vai trò chóp mũi; topology mũi có dấu hiệu cần xem lại. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 11 | Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt (PDF 10) | E và midpoint(p48=MP61,p54=MP291) | D(E,(p48+p54)/2)/(d+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | PDF không nói rõ “khóe miệng” dùng một khóe hay trung điểm hai khóe. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 12 | Khoảng cách chóp mũi–đáy cằm / cao mặt (PDF 10) | p30=MP1,p8=MP152; H như trên | D(30,8)/(H+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Cần xác minh chóp mũi/đáy cằm và endpoint chiều cao mặt. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 13 | Rộng xương hàm / cao mặt (PDF 10) | p4=MP172,p12=MP397; H như trên | D(4,12)/(H+e) | dimensionless | UNVERIFIED; số học oracle đạt, không đổi công thức | Chưa có canonical gonion/xương hàm cho lựa chọn p4/p12. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |
| 14 | Góc xương hàm tại cằm (PDF 10) | p4=MP172,p8=MP152,p12=MP397 | degrees(acos(clip((p4−p8)·(p12−p8)/(D(4,8)D(12,8)),−1,1))) | degrees | UNVERIFIED; số học oracle đạt, không đổi công thức | Phép acos/độ khớp PDF; endpoint hai góc hàm tại p4/p12 chưa đủ thẩm quyền xác nhận. | Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước |

[56 phép đối chiếu ảnh thật](evidence/a2_real_image_oracles.csv) chứng minh số học hiện hành trên14×4 ảnh; không chứng minh mọi endpoint đúng giải phẫu. Đặc biệt p30=MP1 có y≈149.59 và p33=MP4 có y≈142.02 trên CFD00001, nên topology “đáy mũi” cần xem lại với hình PDF. Đây là **dấu hiệu cần xác minh**, chưa có bảng ID chuẩn đủ để tự sửa một index cụ thể. Không tự chốt DEVIATION mới chỉ từ tên “nose_tip”, cũng không tự gắn EXACT vì test số học đạt.

## Self-match tách khỏi công thức chuẩn hóa

Legacy A-only loại theo path; B-only đã duyệt D17 dùng image_id; A+B dùng hash byte→IDs và filename tie-break. A+B v2 tái sử dụng đúng chính sách đó. Bản PNG mã hóa lại có byte khác được coi là query mới và có thể trả ảnh gốc; không tự thêm pixel hash/face identity heuristic. PDF không định nghĩa đầy đủ self-match, nên không gán quy tắc của code là nguyên văn PDF. Không loại các ảnh khác chỉ vì metadata ghi cùng người.

## Việc cần làm để đóng các mục còn mở

Chốt canonical68/MediaPipe mapping và quy ước trái/phải có thẩm quyền; đánh dấu thủ công các endpoint trên đúng ảnh minh họa và mẫu đa dạng; so sánh tọa độ/sai số theo protocol định trước. Làm rõ cao mặt, gò má, EAR, chóp/base mũi, khóe miệng và góc hàm. Chỉ sửa khi có bằng chứng rõ, trong version mới và giữ baseline; không chọn công thức bằng Top-5. **Chưa triển khai C1/C2.**
