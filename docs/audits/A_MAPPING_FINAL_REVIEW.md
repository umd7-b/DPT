# Kiểm tra cuối mapping và A2 của Bộ A

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. PDF chuẩn duy nhất cho yêu cầu dự án: `C:\Users\USER\Downloads\csdldpt.pdf`, 18 trang, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh lại. Trang ghi dưới đây là trang PDF vật lý. Tài liệu MediaPipe chỉ giải thích topology/API; không thay PDF và không cung cấp bảng chuyển canonical 478→68 cho báo cáo nhóm.

Phạm vi lần này là kiểm toán, không sửa mapping, A2, code chuẩn hóa, nguồn ảnh, mask, vector/stats/calibration/output v1/v2; không tạo CSDL hoặc C1/C2. File mới chỉ nằm trong `docs/audits/`: bốn báo cáo này, `pre_c_tools/` và `pre_c_evidence/`.


## Kết luận có giới hạn

**68 điểm đủ, duy nhất, nằm trong miền 478 điểm; hai file nguồn dùng cùng mapping.** Trên ba ảnh thật, raw A150 tái lập đúng từng phần tử. Đã kiểm cả 14 A2 bằng oracle scalar và xem hai hình PDF trang 8. **Đã xác nhận khác biệt vị trí/topology so với hình minh họa trên cùng ảnh CFD00001**, rõ nhất ở đầu hàm và nhóm mũi. Tuy nhiên, **chưa thể xác định một canonical mapping 478→68 thay thế hoặc xác minh toàn bộ endpoint nhân trắc**, vì PDF không cho bảng MP ID đầy đủ. Giữ nguyên source và vector.

Phân loại dùng trong báo cáo: EXACT cho điều khoản rõ có source và oracle; IMPLEMENTATION DETAIL cho quy ước code ở chỗ PDF chưa chốt, không tự mang nghĩa “đã được phê duyệt”; DEVIATION chỉ khi chứng minh khác yêu cầu rõ; UNVERIFIED khi thiếu chuẩn, ground truth hoặc thẩm quyền. Không tự thay index theo overlay hoặc Top-5.

## Tài liệu MediaPipe và phạm vi thẩm quyền

[Google Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) mô tả 478 landmarks. [FaceLandmarksConnections chính thức](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py) định nghĩa contour mặt, mắt, mày, môi, mũi. Đã đối chiếu tập cạnh đang cài trong MediaPipe **1.2.3**, hash source `69c822394b341e8fef4aea6351d4ef2285931cd7448a5c235c30a2a80f390412`; toàn bộ cạnh và so sánh lưu ở [native_mediapipe_topology.json](pre_c_evidence/native_mediapipe_topology.json). Tham chiếu web master được xem ngày 23/11/2026; không dùng như một phiên bản canonical mapping 68 của báo cáo nhóm.

| Nhóm code | Số điểm | Contour chính thức đối chiếu | Membership | Ngoài sparse contour | Phân loại hẹp |
| --- | --- | --- | --- | --- | --- |
| JAW | 17 | FACE_LANDMARKS_FACE_OVAL | 17/17 | Không | EXACT về membership contour |
| LEFT_EYEBROW | 5 | FACE_LANDMARKS_RIGHT_EYEBROW | 5/5 | Không | EXACT về membership contour |
| RIGHT_EYEBROW | 5 | FACE_LANDMARKS_LEFT_EYEBROW | 5/5 | Không | EXACT về membership contour |
| NOSE | 9 | FACE_LANDMARKS_NOSE | 7/9 | 129, 358 | UNVERIFIED cho MP129/358; 7 điểm còn lại có membership chính xác |
| LEFT_EYE | 6 | FACE_LANDMARKS_RIGHT_EYE | 6/6 | Không | EXACT về membership contour |
| RIGHT_EYE | 6 | FACE_LANDMARKS_LEFT_EYE | 6/6 | Không | EXACT về membership contour |
| MOUTH | 20 | FACE_LANDMARKS_LIPS | 20/20 | Không | EXACT về membership contour |

59 điểm ngoài nhóm mũi đều thuộc các contour tương ứng; thêm 7/9 điểm mũi nằm trên sparse NOSE, tổng 66/68. **Sparse contour không phải segmentation đầy đủ của vùng giải phẫu**, nên thiếu MP129/358 trong danh sách này không tự chứng minh chúng sai cánh mũi.

## Đánh giá giải phẫu theo nhóm

Đã xem overlay ba ảnh nguồn dưới đây và đối chiếu hai hình minh họa của PDF. Nhận xét chỉ áp dụng các ảnh đã kiểm, không suy rộng thành ground truth cho mọi ảnh:

| Nhóm và index code 0-based | Quan sát trên ảnh và đối chiếu sơ đồ PDF | Phân loại và giới hạn |
| --- | --- | --- |
| JAW 0–16 | Chuỗi đi từ má phía trái ảnh qua cằm p8 rồi lên má phía phải. Hai điểm đầu/cuối thấp hơn rõ rệt so với vị trí đầu hàm gần thái dương trong hình PDF. | EXACT về 17 điểm thuộc FACE_OVAL; DEVIATION so với vị trí minh họa; zygion tại p2/p14 và gonion tại p4/p12 vẫn UNVERIFIED. |
| Eyebrow 17–21 và 22–26 | Mỗi bên có năm điểm đi theo đường mày; thứ tự đi từ ngoài vào trong ở trái ảnh, từ trong ra ngoài ở phải ảnh. | Hợp lý về vùng và thứ tự trên mẫu; chọn một đường mày thưa và tên trái/phải là IMPLEMENTATION DETAIL, chưa chứng nhận từng điểm canonical. |
| Eye 36–41 và 42–47 | Mỗi mắt có hai khóe, hai điểm mí trên và hai điểm mí dưới, tạo vòng sáu điểm phù hợp dạng sơ đồ. | EXACT về membership EYE và cấu trúc sáu điểm; ý nghĩa từng mốc và định nghĩa tâm mắt vẫn cần chuẩn. |
| Nose 27–35 | Ba điểm đầu theo sống mũi; p30=MP1 và p33=MP4 đảo thứ tự cao/thấp so với hai nhánh trong hình PDF. p31/p35 ở hai bên vùng mũi nhưng không thuộc sparse NOSE. | DEVIATION so với topology minh họa; canonical MP ID và endpoint cánh/chóp/đáy mũi vẫn UNVERIFIED. |
| Mouth 48–59 và 60–67 | Vòng ngoài có 12 điểm, vòng trong có 8 điểm; hai khóe và hai đường môi nằm ở vùng miệng như sơ đồ. | EXACT về 20 điểm thuộc LIPS và số lượng; vị trí biên môi/khóe và độ mở cần canonical annotation. |

Đây là kiểm tra tính hợp lý giải phẫu có giới hạn. Membership cùng vùng và hình dạng tổng thể không đủ xác nhận độ chính xác nhân trắc của từng endpoint.

Tên LEFT_EYE/LEFT_EYEBROW trong code lấy các nhóm API đặt tên RIGHT; chiều kia tương ứng ngược lại. Trên các ảnh kiểm tra, đó là phía trái/phải theo người xem. Đây là **IMPLEMENTATION DETAIL về naming/frame**, chưa kết luận DEVIATION đối với PDF vì PDF không chốt tham chiếu trái/phải. Nếu một bên hiểu theo giải phẫu còn bên kia theo ảnh thì STT3/4,5/6 sẽ bị diễn giải ngược; cần quyết định rõ trước khi gắn nhãn dữ liệu.

## Overlay mới: cả index68 và index MediaPipe

Mỗi ảnh là toàn khung nguồn được phóng cho dễ đọc, có nhãn `A68:MP478` và bảng 68 dòng; không crop hoặc thay ảnh nguồn:

- [CFD00001:68/MP](pre_c_evidence/cfd_final_00001_68_mp_overlay.png) · [topology mũi toàn khung](pre_c_evidence/cfd_final_00001_nose_topology_fullframe.png)
- [HF00001:68/MP](pre_c_evidence/hf_merged_00001_68_mp_overlay.png) · [topology mũi toàn khung](pre_c_evidence/hf_merged_00001_nose_topology_fullframe.png)
- [CFD00069:68/MP](pre_c_evidence/cfd_final_00069_68_mp_overlay.png) · [topology mũi toàn khung](pre_c_evidence/cfd_final_00069_nose_topology_fullframe.png)

[mapping_points_review.csv](pre_c_evidence/mapping_points_review.csv) có 204 dòng=68×3, gồm index 0-based, index 1-based, MP index, nhóm, contour, x/y. Cột 1-based chỉ là cộng một để đối chiếu cách đánh số 1–68; không khẳng định PDF đã chỉ định MP index đó.

| Index code 0-based | Số thứ tự 1-based | MP index | Nhóm code | Contour đối chiếu | Thuộc sparse contour |
| --- | --- | --- | --- | --- | --- |
| 0 | 1 | 234 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 1 | 2 | 93 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 2 | 3 | 132 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 3 | 4 | 58 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 4 | 5 | 172 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 5 | 6 | 136 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 6 | 7 | 150 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 7 | 8 | 149 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 8 | 9 | 152 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 9 | 10 | 378 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 10 | 11 | 379 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 11 | 12 | 365 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 12 | 13 | 397 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 13 | 14 | 288 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 14 | 15 | 361 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 15 | 16 | 323 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 16 | 17 | 454 | JAW | FACE_LANDMARKS_FACE_OVAL | True |
| 17 | 18 | 70 | LEFT_EYEBROW | FACE_LANDMARKS_RIGHT_EYEBROW | True |
| 18 | 19 | 63 | LEFT_EYEBROW | FACE_LANDMARKS_RIGHT_EYEBROW | True |
| 19 | 20 | 105 | LEFT_EYEBROW | FACE_LANDMARKS_RIGHT_EYEBROW | True |
| 20 | 21 | 66 | LEFT_EYEBROW | FACE_LANDMARKS_RIGHT_EYEBROW | True |
| 21 | 22 | 107 | LEFT_EYEBROW | FACE_LANDMARKS_RIGHT_EYEBROW | True |
| 22 | 23 | 336 | RIGHT_EYEBROW | FACE_LANDMARKS_LEFT_EYEBROW | True |
| 23 | 24 | 296 | RIGHT_EYEBROW | FACE_LANDMARKS_LEFT_EYEBROW | True |
| 24 | 25 | 334 | RIGHT_EYEBROW | FACE_LANDMARKS_LEFT_EYEBROW | True |
| 25 | 26 | 293 | RIGHT_EYEBROW | FACE_LANDMARKS_LEFT_EYEBROW | True |
| 26 | 27 | 300 | RIGHT_EYEBROW | FACE_LANDMARKS_LEFT_EYEBROW | True |
| 27 | 28 | 168 | NOSE | FACE_LANDMARKS_NOSE | True |
| 28 | 29 | 6 | NOSE | FACE_LANDMARKS_NOSE | True |
| 29 | 30 | 197 | NOSE | FACE_LANDMARKS_NOSE | True |
| 30 | 31 | 1 | NOSE | FACE_LANDMARKS_NOSE | True |
| 31 | 32 | 129 | NOSE | FACE_LANDMARKS_NOSE | False |
| 32 | 33 | 48 | NOSE | FACE_LANDMARKS_NOSE | True |
| 33 | 34 | 4 | NOSE | FACE_LANDMARKS_NOSE | True |
| 34 | 35 | 278 | NOSE | FACE_LANDMARKS_NOSE | True |
| 35 | 36 | 358 | NOSE | FACE_LANDMARKS_NOSE | False |
| 36 | 37 | 33 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 37 | 38 | 160 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 38 | 39 | 158 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 39 | 40 | 133 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 40 | 41 | 153 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 41 | 42 | 144 | LEFT_EYE | FACE_LANDMARKS_RIGHT_EYE | True |
| 42 | 43 | 362 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 43 | 44 | 385 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 44 | 45 | 387 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 45 | 46 | 263 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 46 | 47 | 373 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 47 | 48 | 380 | RIGHT_EYE | FACE_LANDMARKS_LEFT_EYE | True |
| 48 | 49 | 61 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 49 | 50 | 40 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 50 | 51 | 37 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 51 | 52 | 0 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 52 | 53 | 267 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 53 | 54 | 270 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 54 | 55 | 291 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 55 | 56 | 321 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 56 | 57 | 314 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 57 | 58 | 17 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 58 | 59 | 84 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 59 | 60 | 91 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 60 | 61 | 78 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 61 | 62 | 81 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 62 | 63 | 13 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 63 | 64 | 311 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 64 | 65 | 308 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 65 | 66 | 402 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 66 | 67 | 14 | MOUTH | FACE_LANDMARKS_LIPS | True |
| 67 | 68 | 178 | MOUTH | FACE_LANDMARKS_LIPS | True |

## MP1, MP4 và topology mũi

Source chính thức nối nhánh trục mũi theo `168→6→197→195→5→4→1→19→94→2`. MP1 và MP4 là **hai điểm khác nhau**, đều thuộc NOSE. Code hiện dùng p30=MP1 ở cuối đoạn bốn điểm “sống mũi”, p33=MP4 ở giữa đoạn năm điểm được chú thích “đáy mũi”. [Canonical mesh chính thức](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj) cũng chứa hai vertex khác nhau: MP1=(0,−1.126865,7.475604), MP4=(0,−0.463170,7.586580). Mesh 468 đó không phải bảng chuyển canonical 478→68; không dùng vị trí nhô ra hơn để tự chọn index thay thế.

| Ảnh thật | MP1 pixel(x,y) | MP4 pixel(x,y) | y(MP1)−y(MP4) | Max sai số raw A so với kho | Max sai số 14 A2 oracle |
| --- | --- | --- | --- | --- | --- |
| cfd_final_00001.png | [126.93502044677734, 149.5855255126953] | [126.8865966796875, 142.0238037109375] | 7.56172180 | 0 | 3.34e-07 |
| hf_merged_00001.png | [131.85855102539062, 148.00021362304688] | [131.91806030273438, 140.47763061523438] | 7.52258301 | 0 | 8.29e-06 |
| cfd_final_00069.png | [125.37506866455078, 150.82752990722656] | [125.43547821044922, 142.60726928710938] | 8.22026062 | 0 | 4.99e-06 |

MP4 nằm cao hơn MP1 trong ba ảnh đo. Hình PDF vẽ điểm giữa nhánh năm điểm đáy mũi **thấp hơn** điểm cuối nhánh bốn điểm sống mũi; code hiện hành có quan hệ ngược lại. Xem [hình CFD trích từ PDF](evidence/pdf_page8_X31.png) và [hình HF](evidence/pdf_page8_X33.png).

### Sai khác minh họa đã đo trên cùng CFD00001

Đọc marker trực tiếp từ raster nhúng PDF, nhận đủ 17 marker hàm và 9 marker mũi bằng tâm trắng và vòng màu. Quy đổi panel xấp xỉ về khung 256×256; dùng khoảng đọc khoảng 1 pixel nguồn, không coi đây là annotation giải phẫu. Phương pháp, tọa độ và hash hình ở [pdf_illustration_measurements.json](pre_c_evidence/pdf_illustration_measurements.json); không gán MP ID cho marker của PDF.

| Mốc theo vị trí trong nhóm | Index code 0-based | MP hiện dùng | PDF x/y xấp xỉ | Code x/y | y code − y PDF |
| --- | --- | --- | --- | --- | --- |
| jaw_start_left_in_image | 0 | 234 | 45.464, 86.509 | 46.358, 121.233 | 34.724 |
| jaw_end_right_in_image | 16 | 454 | 211.864, 88.443 | 213.682, 122.558 | 34.115 |
| fourth_bridge_marker | 30 | 1 | 125.948, 142.002 | 126.935, 149.586 | 7.584 |
| middle_of_five_base_markers | 33 | 4 | 126.142, 156.310 | 126.887, 142.024 | -14.286 |

Trong hình, `y(giữa đáy)−y(cuối sống)` ≈ **14.308 pixel**; code = **-7.562 pixel**. Dấu ngược nhau không thể giải thích bằng đổi tỉ lệ hoặc tịnh tiến panel. Hai đầu hàm lệch khoảng 34 pixel theo chiều dọc. Đây là **DEVIATION có phạm vi: code không tái hiện vị trí/topology của hình minh họa**, không phải xác nhận một MP index thay thế cụ thể. Cần tác giả làm rõ hình là ràng buộc endpoint hay sơ đồ minh họa và cung cấp mapping/annotation chuẩn. Canonical MP ID vẫn **UNVERIFIED**; **không sửa mapping** chỉ từ hình hoặc chỉ vì một MP khác trông gần marker hơn.

## Tâm mắt và 14 A2

Source `geometry_features.py::normalize_landmarks` và `calculate_ratios` dùng L/R là trung bình sáu mốc mí, `E=(L+R)/2`, `d=||L−R||₂`, `P′=(P−E)/d`. Phép trừ E/chia d là EXACT về toán học trên các tâm đã chọn; dùng sáu mí để định nghĩa tâm mắt là IMPLEMENTATION DETAIL chưa được PDF định nghĩa đủ, còn tương đương với tâm nhân trắc là UNVERIFIED. Không tự đổi sang MP468/473.

Ký hiệu D(i,j)=Euclid 2D, H=D((p21+p22)/2,p8), e=1e-8. Cả 14 hàng ở `geometry_features.py::calculate_ratios`, góc gọi `angle_degrees`; A2 không sửa. Bảng số dùng ảnh CFD00001; tên bộ phận là định nghĩa code, không phải gán nhãn canonical chính thức. Đối chiếu danh sách PDF ở trang 9–10: [trang 9](pre_c_evidence/pdf_page_09.txt), [trang 10](pre_c_evidence/pdf_page_10.txt).

| STT | Tên trong PDF | Endpoint/định nghĩa hiện hành | Công thức code | Đơn vị | Code / oracle ảnh thật | Trạng thái | Bằng chứng còn thiếu |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Rộng gò má / cao mặt | p2=MP132,p14=MP361;H từ midpoint(p21=MP107,p22=MP336) tới p8=MP152 | D(2,14)/(H+e) | dimensionless | 1.046288609505 / 1.046288625764 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Chưa có canonical zygion/cao mặt; các điểm nằm trên face-oval không tự chứng minh đúng rộng gò má. |
| 2 | Khoảng cách hai mắt / cao mặt | L=mean(MP33,160,158,133,153,144);R=mean(MP362,385,387,263,373,380);H như STT1 | d/(H+e) | dimensionless | 0.537848174572 / 0.537848234585 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Chưa chốt tâm mắt là centroid mí hay tâm iris/pupil và endpoint cao mặt. |
| 3 | Bề ngang mắt trái / khoảng cách hai mắt | p36=MP33,p39=MP133;d=∣∣L−R∣∣ | D(36,39)/(d+e) | dimensionless | 0.398910999298 / 0.398910979712 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Các điểm thuộc RIGHT_EYE theo API; cần chốt frame trái/phải PDF. |
| 4 | Bề ngang mắt phải / khoảng cách hai mắt | p42=MP362,p45=MP263;d=∣∣L−R∣∣ | D(42,45)/(d+e) | dimensionless | 0.405409723520 / 0.405409654821 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Các điểm thuộc LEFT_EYE theo API; cần chốt frame trái/phải PDF. |
| 5 | Độ mở mi mắt trái | p37=MP160,p41=MP144,p38=MP158,p40=MP153;W_L=D(36,39) | (D(37,41)+D(38,40))/(2D(36,39)+e) | dimensionless | 0.405063658953 / 0.405063627870 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | EAR dùng hai đoạn dọc/chiều ngang là công thức code; PDF chỉ ghi độ mở mí. |
| 6 | Độ mở mi mắt phải | p43=MP385,p47=MP380,p44=MP387,p46=MP373;W_R=D(42,45) | (D(43,47)+D(44,46))/(2D(42,45)+e) | dimensionless | 0.410401463509 / 0.410401479333 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | EAR dùng hai đoạn dọc/chiều ngang là công thức code; PDF chỉ ghi độ mở mí. |
| 7 | Rộng cánh mũi / khoảng cách hai mắt | p31=MP129,p35=MP358 | D(31,35)/(d+e) | dimensionless | 0.579081058502 / 0.579080994596 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | MP129/358 không thuộc sparse NOSE; chưa có chuẩn alar endpoint để kết luận sai/đúng. |
| 8 | Rộng miệng / khoảng cách hai mắt | p48=MP61,p54=MP291 | D(48,54)/(d+e) | dimensionless | 0.680292546749 / 0.680292467171 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | MP61/291 thuộc LIPS; cần xác nhận endpoint khóe môi theo chuẩn 68. |
| 9 | Độ mở môi / khoảng cách hai mắt | p62=MP13,p66=MP14 | D(62,66)/(d+e) | dimensionless | 0.019763097167 / 0.019763093291 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | MP13/14 thuộc LIPS; cần quy ước độ mở môi/biên trong phù hợp. |
| 10 | Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt | E=(L+R)/2;p30=MP1 | D(E,p30)/(d+e) | dimensionless | 0.583537042141 / 0.583536864218 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | MP1 thuộc NOSE nhưng PDF không chốt index chóp mũi. |
| 11 | Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt | E và midpoint(p48=MP61,p54=MP291) | D(E,(p48+p54)/2)/(d+e) | dimensionless | 0.976535797119 / 0.976535748611 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Code dùng midpoint hai khóe; PDF chưa định nghĩa rõ một khóe hay trung điểm. |
| 12 | Khoảng cách chóp mũi–đáy cằm / cao mặt | p30=MP1,p8=MP152;H như STT1 | D(30,8)/(H+e) | dimensionless | 0.493947982788 / 0.493947996350 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Chóp mũi, đáy cằm và cao mặt cần chuẩn endpoint có thẩm quyền. |
| 13 | Rộng xương hàm / cao mặt | p4=MP172,p12=MP397;H như STT1 | D(4,12)/(H+e) | dimensionless | 0.873462677002 / 0.873462743079 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Membership face-oval không xác nhận MP172/397 đúng gonion/rộng xương hàm. |
| 14 | Góc xương hàm tại cằm | p4=MP172,p8=MP152,p12=MP397 | degrees(acos(clip((p4−p8)·(p12−p8)/(D(4,8)D(12,8)),−1,1))) | degrees | 128.195068359375 / 128.195068024916 | UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng | Arccos/độ chính xác về phép toán; chọn hai điểm góc hàm vẫn chưa được chứng minh. |

[a2_fresh_oracles.csv](pre_c_evidence/a2_fresh_oracles.csv) lưu 42 phép đo=14×3 với tử/mẫu, ε, code, scalar oracle và sai số. Có chứng cứ số học riêng cho từng đặc trưng, nhưng phép chia đúng không xác nhận chúng đo đúng zygion/gonion/chóp mũi mà PDF nói đến. Cần annotation endpoint, quy ước trái/phải/cao mặt/độ mở mí có thẩm quyền; không lấy kết quả retrieval để quyết định.
