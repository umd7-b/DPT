# C1 v0.4 — sổ quyết định chờ xác nhận

Ngày tạo24/11/2026, Asia/Saigon. **8 quyết định chưa duyệt;0 người có thẩm quyền/biên bản chấp thuận được ghi nhận.**
Các mô tả và proposed roles dưới đây là nội dung để người có thẩm quyền xem xét, không phải quyết định của họ.
Không tự đánh dấu approval từ nhận xét Agent, topology membership hay geometry5752/5752.

Nguồn cao nhất là PDF đã hash trong [protocol](C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md).
Endpoint/topology evidence có tại C1_ANATOMICAL_VALIDATION.md và C1_ROI_REMEDIATION_REPORT.md;
không dùng những audit đó như chữ ký nghiệm thu. Dữ liệu register:
[CSV](c1_v04_review/decision_register.csv), [JSON](c1_v04_review/decision_register.json).
Mọi authority name/date/evidence hiện trống. Khi con người quyết định, ghi vào bản round mới,
giữ snapshot này và liên kết biên bản có thẩm quyền/hash; không tự sửa PDF theo code.

## D01 — 15 MP phụ trợ vùng trán

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | §2.4: chia4 vùng dựa landmarks. §2.2: A dùng478→68. PDF không cho danh sách MP riêng của C1. |
| Quy ước được đề xuất | Giữ15 upper FACE_OVAL MP127,162,21,54,103,67,109,10,338,297,332,284,251,389,356; không thêm vào A150. |
| Căn cứ geometry/topology/ảnh | 14 cạnh liên tiếp thuộc FACE_OVAL native; hash topology và source archive đã xác thực. |
| Giới hạn còn thiếu | Membership mô hình không chứng minh đây là canonical anatomical boundary hoặc auxiliary478 đã được nhóm chấp nhận cho C1. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả/đại diện nhóm xác nhận diễn giải PDF; reviewer CV/giải phẫu được chủ dự án chỉ định đánh giá ảnh. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D02 — Upper FACE_OVAL có đại diện vùng trán

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF gọi vùng trán và lông mày; không định nghĩa hairline, extent hoặc vertex. |
| Quy ước được đề xuất | Dùng upper FACE_OVAL làm upper boundary ổn định; không coi nó là đường chân tóc hay toàn bộ trán. |
| Căn cứ geometry/topology/ảnh | Overlay CFD/HF cho thấy arc nằm dưới chân tóc ở một số mẫu; census chỉ chứng minh hình học. |
| Giới hạn còn thiếu | Thiếu annotation trán/hairline và tiêu chí mức cắt bỏ chấp nhận được. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả chốt ý nghĩa vùng trán; reviewer có thẩm quyền đánh giá annotation/mức coverage. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D03 — Native lower eyebrow v0.4

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF yêu cầu vùng trán+lông mày, không chốt contour trên/dưới hoặc margin. |
| Quy ước được đề xuất | Lower chain MP276,283,282,295,285,55,65,52,53,46; offset0; upper chain giữ nguyên. |
| Căn cứ geometry/topology/ảnh | Topology8 cạnh lower EYEBROW; proxy pixel đủ1436 ảnh, HF198 thiếu3px/HF267 thiếu1px.4 native point ngoài biên. |
| Giới hạn còn thiếu | Proxy20 điểm không phải pixel annotation mô mày; zero margin chưa được tác giả nghiệm thu. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Reviewer anatomy/CV được chỉ định và tác giả nhóm xác nhận boundary/margin. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D04 — Cạnh nối thái dương và glabella

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF không định nghĩa graph polygon hay cách nối giữa hai contour. |
| Quy ước được đề xuất | Cạnh MP356→MP276, MP285→MP55 và MP46→MP127; nối thẳng theo thứ tự contract. |
| Căn cứ geometry/topology/ảnh | V0.2 có4 crossing cạnh nội bộ; v0.3 còn HF198 do offset; v0.4 đơn giản5752/5752 ROI. |
| Giới hạn còn thiếu | Các bridge không phải native anatomical contour; cần xác minh side tissue và phần cắt bỏ, kể cả HF55/HF198/HF267/HF463. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Reviewer có chuyên môn giải phẫu/CV theo ủy quyền; tác giả xác nhận diễn giải ranh. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D05 — Ranh giới hai má và mũi–miệng

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF chỉ cho tên3 vùng này và dựa landmarks, không cho vertex/margin/đường phân cách. |
| Quy ước được đề xuất | Giữ12 đỉnh mỗi vùng của v0.2, offsets0.08/0.06D và±0.05D; MP129/358 làm nose-side proxy. |
| Căn cứ geometry/topology/ảnh | Ba vùng mask bitwise không đổi toàn kho; eye/lips/oval memberships có source. MP129/358 không thuộc sparse NOSE. |
| Giới hạn còn thiếu | Thiếu canonical nose-side/cheek endpoints và annotation khi biểu cảm; khác biệt A với hình PDF không tự cho phép sửa A. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả nhóm chốt endpoint interpretation; reviewer anatomy/CV thẩm định ảnh. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D06 — Hệ quy chiếu trái/phải

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF gọi má trái/phải; không nêu frame người xem hay người trong ảnh. |
| Quy ước được đề xuất | Contract viewer/code-left/right, x sang phải/y xuống; API eye/brow names có thể ngược phía người xem. |
| Căn cứ geometry/topology/ảnh | Mapping và overlays ghi A68/MP rõ ràng; hai nhóm mắt dùng mean6 float32 hiện hành. |
| Giới hạn còn thiếu | Không có quyền tự diễn giải anatomical-left thành viewer-left; reviewer phải chọn frame và mô tả mapping. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả/đại diện nhóm xác nhận frame; người quản trị dữ liệu ghi nhận convention được duyệt. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D07 — Overlap độc lập

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | PDF nêu4 vùng độc lập, chưa chốt disjoint pixels hay independent pooling. |
| Quy ước được đề xuất | Raw membership riêng; shared pixels được giữ ở mọi vùng chứa chúng; không priority subtraction. |
| Căn cứ geometry/topology/ảnh | Toàn kho overlap91…208px, chỉ má–mũi/miệng; inclusion-exclusion và mask hashes đã kiểm. |
| Giới hạn còn thiếu | Số học không quyết định nghĩa độc lập trong báo cáo; cần tác giả chấp thuận interpretation. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả nhóm xác nhận interpretation; reviewer phương pháp xác nhận ghi nhận version. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## D08 — Tóc/tay/kính/vải và missing

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | §1.2–1.3 có tiêu chí ảnh/che khuất; §2.4 chưa quy định occlusion mask hay ngưỡng min-support của C1. |
| Quy ước được đề xuất | Không tự skin-intersect/inpaint/crop; invalid hoặc<64 support →missing theo rule kỹ thuật hiện hành. Occlusion có phiếu riêng. |
| Căn cứ geometry/topology/ảnh | HF311/55 có tóc, HF198/694 kính, HF209/694 khăn, HF722 tay; hair model mask không phải ground truth. |
| Giới hạn còn thiếu | Chưa chốt mức che khuất/tissue contamination và khi nào semantic rejection trở thành missing. Dataset vi phạm không hết vì ROI hợp lệ. |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | Tác giả/chủ dataset chốt tiêu chí; reviewer được chỉ định đánh giá và adjudicate các ca occlusion. |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |

## Cách đóng một quyết định

Người/nguồn có thẩm quyền phải được chủ dự án xác minh phạm vi ủy quyền. Ghi rõ kết luận,
contract/hash và điều kiện áp dụng, ngày, người, biên bản và SHA-256. Tài liệu phải cho thấy sự xác nhận
thực tế; một URL topology, screenshot polygon hoặc tên reviewer không đủ. Lưu cả rejection/disagreement.
Trạng thái của bản round chỉ chuyển theo kết luận thực tế, ví dụ ACCEPTED_WITH_AUTHORITY_EVIDENCE,
REJECTED_WITH_AUTHORITY_EVIDENCE hoặc UNCERTAIN_REQUIRES_EVIDENCE; snapshot này giữ PENDING.

Không quyết định nào được phép thay P8,R2,threshold>=,59 bins,L1,Chi-square0.5 hoặc sửa PDF để khớp code.
Nếu convention được yêu cầu sửa, tạo candidate/version/hash mới và audit lại; không ghi đè v0.2/v0.4 cũ.
