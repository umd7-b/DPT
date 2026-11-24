QUY TRÌNH KIỂM CHỨNG MASK DA/TÓC — 22/11/2026

1. KẾT QUẢ KIỂM TRA NGUỒN

Đã đối chiếu 1.438 ảnh với metadata.csv: HF 728, CFD 710; không trùng filename metadata, không ảnh mồ côi, không hash ảnh sai. 1.436 skin mask đều khớp skin_mask_sha256 được ghi trong metadata; nội dung giải mã của cả 1.436 mask vẫn giống hệt nhau, mỗi mask 16.952 pixel trắng. Hai ảnh thiếu mask: hf_merged_00723.png, hf_merged_00728.png.

README nói ảnh và mask được sao chép giữ nguyên byte từ nguồn. hf_provenance.csv có 966 dòng lịch sử cho 728 ảnh HF (có ảnh xuất hiện ở nhiều nguồn cũ); không phát hiện sai hash hoặc ảnh HF thiếu truy vết. Đây là bằng chứng về nguồn bản sao và tính toàn vẹn, không phải bằng chứng về phương pháp tạo nhãn hoặc độ chính xác segmentation.

Không xác định được người/công cụ tạo mask ban đầu từ tài liệu hiện có. Ba file .py trong dataset/src hiện có kích thước 0 byte. support_for_tasks_2_3_4_5/requirment.md và historical_metadata.zip được README nhắc tới nhưng không có tại bản dataset cục bộ này. Không kết luận mask bị hỏng trong quá trình sao chép, cũng không coi chúng là GT: phù hợp hơn là template ROI chưa được kiểm chứng theo từng ảnh.

Các khẳng định trong description.txt về nền đồng nhất, tư thế tuyệt đối, không phụ kiện/che khuất không dùng làm điều kiện thật cho toàn bộ ảnh. Contact sheet có kính, mũ, hoa, người phụ, nền phức tạp và tóc nhiều màu. Đây là bằng chứng trực quan của các ngoại lệ; chưa thực hiện đo định lượng mọi khẳng định trong description.txt.

Chi tiết: dataset_audit.csv, audit_summary.json. Dữ liệu nguồn chỉ được đọc.

2. TẬP 40 ẢNH

panel40.csv: đúng 20 CFD + 20 HF, có ba ảnh hồi quy. 20 ảnh neo có quan sát trực quan từ vòng trước: tóc dài/ngắn, tối/nâu sáng/vàng, nền studio/nền tự nhiên, kính, khuyên tai, mũ, hoa, tóc mái, ngược sáng, thiếu mask da. Bổ sung 20 ảnh bằng farthest-point sampling với descriptor màu HSV và thumbnail không gian, phân tầng theo nguồn. Chọn mẫu không dùng mask dự đoán hoặc nhãn thủ công. Contact sheet xác nhận tập còn có tóc bạc/hồng và nhiều biểu cảm.

observed_tags là ghi chú quan sát hỗ trợ chọn mẫu, không phải nhãn segmentation; tags_user_verified=no cho tới khi người dùng xác nhận. Các ảnh tự chọn chưa có tag kiểu tóc được để unreviewed, không giả định descriptor màu tự hiểu kiểu tóc. Nên duyệt panel40_contact_sheet.png và xác nhận tính đa dạng trước khi gán nhãn.

split=development cho 20 ảnh đã xem/tinh chỉnh trước đây; split=held_out_do_not_tune cho 20 ảnh mới. Đây là holdout quy ước cho bước tinh chỉnh sắp tới, không bảo đảm tách danh tính (CFD có thể có cùng người với biểu cảm khác). Nếu thay đổi thuật toán dựa trên nhãn holdout, cần lập tập đánh giá mới. Farthest-point ưu tiên ngoại lệ để stress-test, không phải mẫu đại diện ngẫu nhiên của phân bố 1.438 ảnh. Script chạy lại sẽ ghi lại manifest; hãy lưu bản cố định trước khi thay đổi tags/split.

3. QUY ƯỚC NHÃN THỦ CÔNG

Protocol: visible-face-skin-scalp-hair-v1.

- Skin: vùng da nhìn thấy trên khuôn mặt. Loại tóc, lông mày, mắt, môi, lỗ mũi tối, kính/phụ kiện che khuất. Không gán tai, cổ, vai, tay vào vùng da khuôn mặt. Da vẫn nhìn rõ qua tròng kính trong có thể gán; không suy diễn vùng bị gọng/ánh phản chiếu che kín.
- Hair: tóc đầu thực sự nhìn thấy, gồm tóc mái và tóc dài hai bên. Loại lông mày, mũ, hoa, khuyên tai, nền, áo. Không vẽ phần tóc bị che. Với sợi quá mảnh/mờ, gán pixel khi đa số diện tích pixel thể hiện tóc; thống nhất quy tắc này giữa các ảnh.
- Cả hai mask là uint8 0/255, cùng kích thước ảnh; không chồng lên nhau. Khi vẽ một vùng đè vùng kia, vùng kia bị xóa ở phần chồng và mất xác nhận.
- Hoàn thành toàn bộ vùng nhìn thấy, không chỉ vẽ phần chắc chắn dễ nhất. Nhãn chuẩn đầy đủ phục vụ đánh giá full prediction; ROI màu bảo thủ được đánh giá riêng.
- S lưu nháp; C rồi Y mới xác nhận vùng đang chọn là hoàn chỉnh. E rồi Y chỉ dùng khi vùng đó thực sự vắng mặt (ví dụ không thấy tóc). Mask rỗng chưa xác nhận không có nghĩa là âm tính thật.
- Mỗi vùng được xác nhận độc lập, có tên người duyệt và thời điểm. Sửa/xóa sau xác nhận sẽ chuyển vùng đó về draft; U hoàn tác cả nét vẽ và trạng thái duyệt. Lịch sử U giới hạn 60 thao tác trong ảnh đang mở; mở lại phục hồi bản lưu, không phục hồi stack undo.
- Nên vẽ khi prediction reference đang tắt (mặc định). P chỉ bật xem tham khảo; tuyệt đối không có thao tác chép prediction thành GT. Tốt nhất nhờ người thứ hai kiểm tra độc lập trước khi C/Y cho bản cuối. Tên người duyệt là khai báo cục bộ, không phải chữ ký/chứng thực danh tính.
- Annotation nằm riêng annotations/manual_masks/. Mỗi lần lưu tạo revision bất biến và cập nhật con trỏ current.json bằng thao tác atomic. Có hash ảnh nguồn và hash từng mask; evaluator từ chối nhãn đã sửa ngoài công cụ, sai hình dạng, sai protocol, sai ảnh hoặc thiếu xác nhận. Thư mục revision dang dở nếu máy dừng khi đang lưu sẽ không được current.json trỏ tới.

4. CÁCH DÙNG POWERSHELL TỪ REPOSITORY

Kiểm tra nguồn và tạo lại panel (không tạo nhãn):
.\.venv311\Scripts\python.exe src/prepare_mask_validation.py

Mở ba ảnh hồi quy để người dùng vẽ:
.\.venv311\Scripts\python.exe src/annotate_masks.py --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png --annotator "TenNguoiGanNhan"

Mở toàn bộ panel40:
.\.venv311\Scripts\python.exe src/annotate_masks.py --annotator "TenNguoiGanNhan"

Điều khiển trong cửa sổ OpenCV (click vùng vẽ bên trái; phím chữ thường):
1 da, 2 tóc; chuột trái vẽ, chuột phải xóa; [ / ] giảm/tăng cỡ cọ.
U hoàn tác; X xóa mask vùng đang chọn; S lưu nháp.
C rồi Y xác nhận vùng đã hoàn chỉnh; E rồi Y xác nhận vùng thực sự trống.
N ảnh sau, B ảnh trước, Q/Esc thoát; chuyển/thoát tự lưu thay đổi, không tự xác nhận.
P bật/tắt overlay prediction ở ô tham khảo bên phải; mặc định tắt.
Mở lại cùng lệnh sẽ nạp revision mới nhất của các ảnh đã lưu.

Thử hiển thị nhanh, tự đóng và không lưu nhãn:
.\.venv311\Scripts\python.exe src/annotate_masks.py --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png --smoke-test

Đánh giá panel40 sau khi người dùng gán/xác nhận nhãn:
.\.venv311\Scripts\python.exe src/evaluate_masks.py

Chỉ đánh giá ba ảnh:
.\.venv311\Scripts\python.exe src/evaluate_masks.py --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png --output outputs/mask_validation/evaluation_three

Nếu đổi thuật toán, chỉ chạy dự đoán đúng 40 ảnh, không phải --all:
$panelNames = (Import-Csv outputs/mask_validation/panel40.csv).filename
.\.venv311\Scripts\python.exe src/refine_hair_mask.py --image $panelNames --output-dir outputs/mask_validation/predictions/hair --evaluation-dir outputs/mask_validation/prediction_run

Evaluator mặc định dùng dataset/skin_masks làm baseline da chưa kiểm chứng và outputs/mask_validation/predictions/hair làm dự đoán tóc. Có thể đổi --skin-pred-dir và --hair-pred-dir; hậu tố tên file tương ứng _skin.png, _hair_mask.png. Tạo --output riêng cho mỗi phiên bản thuật toán để giữ kết quả. Kiểm tra cột status để biết ảnh nào thiếu prediction hoặc nhãn.

5. CHỈ SỐ VÀ ẢNH ĐỐI CHIẾU

metrics.csv chứa hai dòng mỗi ảnh: skin và hair. Chỉ dòng status=evaluated mới có TP/FP/FN, IoU, Dice, precision, recall. Nhãn thiếu, draft, sai hash/schema/shape/protocol, thiếu prediction hoặc prediction sai nhị phân đều bị bỏ qua và ghi trạng thái. Không tính accuracy từ nhãn giả hoặc template.

IoU = TP/(TP+FP+FN); Dice = 2TP/(2TP+FP+FN); precision = TP/(TP+FP); recall = TP/(TP+FN). Tính trên toàn bộ pixel ảnh. Phân số mẫu số 0 để trống; cả prediction và GT trống không được chấm điểm hoàn hảo giả tạo. GT trống đã được người dùng xác nhận + prediction có foreground: IoU/Dice/precision=0, recall không xác định. Báo cáo summary.json ghi số được chấm, coverage, số lượng chỉ số có mẫu số hợp lệ và macro average. Khi coverage khác nhau giữa các thuật toán, cần so sánh trên cùng tập ảnh được chấm.

comparisons/ gồm ảnh gốc, prediction overlay, GT overlay và error map (TP xanh lá, FP đỏ, FN xanh dương). Nếu chưa có GT hợp lệ, ô đó ghi NO VALID HUMAN GT, không giả mask đen thành GT. Báo cáo hiện tại cố ý không có số IoU/Dice: chưa có người dùng gán/xác nhận nhãn thật.

6. VÙNG MÀU TÓC ƯU TIÊN ĐỘ SẠCH

hair_color_core.py tạo đề xuất ROI từ prediction tóc, không tạo nhãn hoặc vector Bộ B. Co mask để bỏ viền trộn nền, loại mặt có biên an toàn, hạn chế ở đỉnh và hai bên trên (bỏ tóc gần vai/áo), loại màu tương tự patch da từ landmarks. Không sử dụng nhãn đánh giá để tạo ROI.

.\.venv311\Scripts\python.exe src/hair_color_core.py --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png

Đầu ra hair_core/: mask ROI, ảnh đối chiếu và core_report.csv. ROI dưới 100 pixel (ngưỡng kiểm tra vận hành ban đầu, chưa hiệu chuẩn) báo abstain_insufficient_core; không tự điền vector 0 hay dùng mask lớn hơn thay thế. ROI còn lại cũng được đánh dấu needs_human_review_not_calibrated: chưa phải xác suất tin cậy. Tóc vàng/nâu gần da có thể bị bỏ, mũ vẫn có thể lọt nếu prediction sai. Chỉ được gọi là độ tin cậy cao sau khi đo độ sạch trên nhãn độc lập.

Sau khi có GT, so sánh ROI bảo thủ với full prediction:
.\.venv311\Scripts\python.exe src/evaluate_masks.py --image cfd_final_00001.png cfd_final_00069.png cfd_final_00088.png --hair-pred-dir outputs/mask_validation/hair_core --output outputs/mask_validation/core_evaluation

Ưu tiên precision tóc cao và FP ở vùng da/nền thấp; chấp nhận recall thấp hơn. Điều chỉnh ngưỡng trên development, khóa cấu hình rồi đo holdout. Có thể đặt tiêu chí precision >=0.95 như mục tiêu thiết kế, chưa phải kết quả đo. Ngoài precision, kiểm tra số pixel còn lại và so sánh histogram màu của ROI với tóc được gán đầy đủ để phát hiện thiên lệch màu do chỉ lấy đỉnh/tóc tối. Mẫu bị từ chối cần người dùng sửa mask hoặc xác nhận riêng trước khi tạo Bộ B; không tự động coi vùng ROI này đại diện toàn bộ màu tóc.

7. KIỂM THỬ VÀ VIỆC NGƯỜI DÙNG CẦN LÀM

.\.venv311\Scripts\python.exe -m unittest discover -s tests -v

Tests mới chỉ tạo mask giả lập trong TemporaryDirectory với tên synthetic.png và reviewer synthetic_fixture_only. Không ghi mask GT cho ảnh dataset thật. Kiểm tra công thức bằng ma trận nhỏ tính tay; draft/missing không được chấm; xác nhận trống; lưu/mở lại/undo; chuyển ảnh; xác nhận hai phím; sửa thì hủy xác nhận; phát hiện sửa hash/đổi ảnh; prediction sai giá trị; chọn mẫu xác định/cân bằng; ROI chỉ là tập con và không sửa đầu vào. Cửa sổ OpenCV đã mở smoke-test trên ba ảnh yêu cầu; ảnh giao diện ở editor_smoke/.

Người dùng cần: duyệt tính đa dạng của panel40; thống nhất quy ước nhãn; vẽ và xác nhận riêng cả skin/hair cho từng ảnh; rà soát nhờ người thứ hai nếu có; chạy evaluator; kiểm tra từng FP/FN; chỉ sau đó chọn mask/ROI đạt yêu cầu cho Bộ B. Chưa có GT nên chưa thể kết luận pipeline đạt mức chất lượng nào. Bộ A, C1, C2 không thay đổi; không chạy --all; không tải model hoặc cài thư viện.

KẾT QUẢ CHẠY THỰC TẾ
- 20/20 unit tests đạt, gồm 7 tests pipeline có sẵn và 13 tests mới; xem unit_tests.log.
- 40 dự đoán tóc đã tạo ở predictions/hair/, không có lỗi thực thi. prediction_run/ giữ log và chỉ báo chất lượng; các dự đoán vẫn cần đánh giá thủ công, không phải nhãn chuẩn.
- predictions/prediction_manifest.json ghi hash mã segmentation, model sẵn có, ảnh nguồn và từng prediction để truy vết cấu hình đầu vào.
- Evaluation: 80 dòng (40 x 2 vùng), tất cả missing_manual_label, mọi chỉ số để trống. 80 ảnh so sánh ghi rõ NO VALID HUMAN GT.
- Smoke GUI: đã mở lần lượt 00001, 00069, 00088 và đóng tự động; chỉ lưu ba ảnh giao diện, không lưu mask hoặc xác nhận.
- ROI tóc bảo thủ của 00001/00069/00088 lần lượt còn 2.760 / 964 / 11.419 pixel; đây chỉ là diện tích ROI, không phải độ chính xác hoặc bằng chứng đạt precision mục tiêu.
- annotations/manual_masks/ hiện chỉ có README.txt, chưa có mask thật nào được gán hoặc xác nhận tự động.


C?P NH?T SAU KHI NG??I D?NG HO?N T?T BA ?NH
Ng??i d?ng t? v? v? ch?nh s?a nh?n 00001, 00069, 00088. Tool v?n l?u draft; sau l?i x?c nh?n trong chat "?? xong" (sau y?u c?u s?a v? x?c nh?n c? hai v?ng), ?? ghi nh?n x?c nh?n n?y cho c? skin/hair, l?u revision m?i v?i confirmation_method=user_chat v? b?ng ch?ng trong annotation.json. Kh?ng thay ??i b?t k? pixel mask n?o khi ghi nh?n x?c nh?n, kh?ng d?ng prediction t?o GT.

?? s?a x? l? ph?m c?a editor ?? C/Y vi?t hoa ho?t ??ng nh? c/y vi?t th??ng. C?c c?a s? c? ?ang ch?y c?n m? l?i c?ng c? ?? nh?n b?n s?a. T?ng 21/21 tests ??t, g?m ki?m th? ph?m vi?t hoa.

Macro tr?n ??ng ba ?nh ?? g?n nh?n:
- Baseline skin template: IoU 0.5502; Dice 0.7085; precision 0.9356; recall 0.5713.
- Full hair prediction: IoU 0.7936; Dice 0.8828; precision 0.9142; recall 0.8584.
- Conservative hair ROI: IoU 0.3276; Dice 0.4610; precision 0.9933; recall 0.3284.

ROI ??t ?? s?ch cao h?n tr?n ba ?nh n?y nh?ng gi? ?t t?c h?n. ??y l? ba ?nh development, ch?a ?? ch?ng minh t?ng qu?t h?a; c?n 37 ?nh c?n l?i v? ki?m tra sai l?ch histogram m?u tr??c B? B. Kh?ng coi precision 0.9933 l? ?? tin c?y cho to?n dataset.

Chi ti?t t?ng ?nh: evaluation_three/metrics.csv, core_evaluation/metrics.csv. ?nh ??i chi?u c? GT v? TP/FP/FN ? th? m?c comparisons/ t??ng ?ng. B?o c?o panel40 evaluation/ ?? c?p nh?t: 3/40 ?nh m?i v?ng ???c ch?m, 37/40 ?nh c?n thi?u nh?n. ?nh nh?n ng??i d?ng ?? x?c nh?n: manual_confirmed_review.png. C?c s? 0 nh?n ? ph?n k?t qu? ch?y ban ??u ph?a tr?n l? l?ch s? tr??c khi ng??i d?ng g?n nh?n.
