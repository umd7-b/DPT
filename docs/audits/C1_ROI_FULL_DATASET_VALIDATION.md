# Kiểm tra ROI C1 trên toàn bộ dataset

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu cao nhất: `csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh. Đã đọc toàn bộ §2.2/§2.4 qua bản trích PDF đóng băng, đối chiếu hình PDF và source/hash hiện hành. Không chỉnh PDF, dataset, mapping A, vector A/B, stats/calibration, CSDL hoặc kết quả A+B đã nghiệm thu.

Đợt này chỉ kiểm toán ROI và chốt đặc tả kỹ thuật có nguồn gốc rõ. Không chạy lại MediaPipe, không gọi LBP/HOG trên ảnh, không viết extractor hoặc tạo vector C1/C2. Tên file “final” là hồ sơ kết luận của lần rà soát; trạng thái giải phẫu vẫn **PROVISIONAL**.


## Kết quả thực tế

Đã kiểm đủ **1438 ảnh ×4 =5752 ROI**, không lấy tám ảnh preview làm đại diện cho kết luận hình học toàn kho.

| Hạng mục | Kết quả |
| --- | --- |
| ROI kiểm tra | 5752 |
| Hợp lệ về hình học | **5748** |
| Không hợp lệ | **4**, đều forehead_brow tự giao |
| Sai số đỉnh/thứ tự, NaN/Inf, diện tích0 | 0 |
| Vertex vượt ảnh | 0 |
| Mask<256 pixel hoặc support<64 | 0 theo ngưỡng review đã khai báo |
| Ảnh có raw overlap | **1438/1438** |
| Ownership/priority subtraction | **Không áp dụng** |
| Tâm/mã LBP/histogram/vector được trích | **Không có**; support chỉ là thống kê hình học |
| Chứng nhận giải phẫu/occlusion toàn kho | **Chưa có** |

Định nghĩa valid: đủ thứ tự/số đỉnh, hữu hạn, không self-intersection/zero-edge, diện tích không degenerate và mask clipped không rỗng. Min-area số học1e-6 khác cờ diện tích nhỏ về chất lượng; 256 pixel review và 64 support là quy ước triển khai, không PDF. Diện tích/pixel của bốn polygon invalid vẫn được ghi để chẩn đoán, không đem làm feature.

[summary.json](../../outputs/C1_lbp/roi_validation/summary.json), [metrics.csv — 5752 dòng](../../outputs/C1_lbp/roi_validation/metrics.csv), [image_metrics.csv](../../outputs/C1_lbp/roi_validation/image_metrics.csv), [roi_vertices.csv — 87718 dòng](../../outputs/C1_lbp/roi_validation/roi_vertices.csv).

## Bốn vùng trán tự giao

| Ảnh | Cạnh thứ nhất | Cạnh thứ hai | Giao điểm x,y | Hình toàn khung |
| --- | --- | --- | --- | --- |
| hf_merged_00069 | MP389 → MP356 | A26 → A25 | 195.127497, 87.973927 | [Hình](../../outputs/C1_lbp/roi_validation/intersection_diagnostics/hf_merged_00069.png) |
| hf_merged_00198 | MP162 → MP21 | A18 → A17 | 61.708474, 76.788783 | [Hình](../../outputs/C1_lbp/roi_validation/intersection_diagnostics/hf_merged_00198.png) |
| hf_merged_00267 | MP251 → MP389 | A26 → A25 | 192.748556, 84.605495 | [Hình](../../outputs/C1_lbp/roi_validation/intersection_diagnostics/hf_merged_00267.png) |
| hf_merged_00463 | MP389 → MP356 | A26 → A25 | 193.941319, 86.410776 | [Hình](../../outputs/C1_lbp/roi_validation/intersection_diagnostics/hf_merged_00463.png) |

Giao được xác nhận thêm bằng solver determinant scalar độc lập, với giao điểm nằm trong cả hai segment, không phải chỉ cờ chung “có thể zero-edge”. Cạnh mày offset cắt đường upper FACE_OVAL ở thái dương. [geometry_anomalies.json](../../outputs/C1_lbp/roi_validation/geometry_anomalies.json). Các ảnh này vẫn có contact sheet và trial negative-path, không bị loại để làm thống kê đẹp.

## Diện tích và pixel từng vùng

| Vùng | Geometry valid/1438 | Raw pixel min | Median | Max | Support min | Median | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Trán và vùng lông mày | 1434 | 3451.0 | 5812.0 | 7757.0 | 2492.0 | 4762.5 | 6719.0 |
| Má trái theo người xem | 1438 | 2155.0 | 4347.5 | 7418.0 | 1645.0 | 3704.5 | 6610.0 |
| Má phải theo người xem | 1438 | 2095.0 | 4343.0 | 7429.0 | 1571.0 | 3698.5 | 6628.0 |
| Mũi và miệng | 1438 | 3887.0 | 5455.0 | 7686.0 | 3326.0 | 4741.0 | 6835.0 |

Các thống kê trên bao gồm toàn bộ1438 mask mỗi vùng, kể cả bốn mask trán invalid dưới vai trò chẩn đoán. Continuous/algebraic area, signed orientation, bbox/out-of-bounds và nguyên nhân được ghi riêng trong CSV; không dùng diện tích self-crossing như một polygon giải phẫu hợp lệ.

## Overlap từng cặp và gaps

| Cặp vùng | Overlap min px | Median | Max |
| --- | --- | --- | --- |
| forehead_brow / cheek_left_viewer | 0.0 | 0.0 | 0.0 |
| forehead_brow / cheek_right_viewer | 0.0 | 0.0 | 0.0 |
| forehead_brow / nose_mouth | 0.0 | 0.0 | 0.0 |
| cheek_left_viewer / cheek_right_viewer | 0.0 | 0.0 | 0.0 |
| cheek_left_viewer / nose_mouth | 44.0 | 70.0 | 107.0 |
| cheek_right_viewer / nose_mouth | 43.0 | 70.0 | 104.0 |

Unique overlap min/median/max91/140/208 pixel mỗi ảnh; max memberships=2. Không trừ mask, không gán ưu tiên hoặc tự cắt margin. [overlap_metrics.csv —8628 cặp](../../outputs/C1_lbp/roi_validation/overlap_metrics.csv). Kiểm độc lập inclusion-exclusion xác nhận tổng pixel bốn mask trừ pairwise overlap bằng union mỗi ảnh.

Unassigned **trong native FACE_OVAL proxy** min/median/max=6587.0/8777.5/11879.0 pixel. Có thể gồm mắt, cằm, vùng giữa các polygon; không suy ra tất cả đều là lỗ hổng sai yêu cầu PDF. Cột unassigned_image_pixels là số trên toàn256² khác hẳn số trong face proxy; enclosed_gap_components/pixels chỉ component không chạm biên proxy. Không lấp gaps hoặc kéo polygon cho khớp mặt.

## Coverage lông mày và rủi ro che khuất

10 điểm mày A68 đều nằm trong trán ở1434 ảnh; bốn ảnh còn lại chính là bốn case geometry invalid. **Không ảnh nào chứa đủ20 native brow nodes**, cũng không ảnh nào phủ100% proxy polygon lông mày. Proxy pixel coverage min/median/max=**44.29%/55.55%/67.14%**. Proxy được đóng từ hai chuỗi native trên/dưới bằng đường nối endpoint công khai; không phải nhãn mô/tóc thật và không thể dùng nó để ký nhận giải phẫu.

Đã kiểm saved raw hair mask có hash trên cả1438 ảnh, **không chạy segmentation mới**. Có overlap tóc dự đoán tại1401 ROI trán,710 má trái,843 má phải và1 mũi–miệng; pixel/fraction từng ROI trong metrics. Đây là model proxy, không chứng minh nhãn tóc đúng hoặc tự cho phép loại pixel đó.

Không có GT toàn kho cho tay/kính/vải hoặc mô giải phẫu; các ROI còn UNVERIFIED. Visual review xác nhận những case rõ như HF00722 có tay trong mũi–miệng, HF00198 có kính qua vùng má/mũi, HF00694 có vải/kính, HF00561/HF00311 nhiều tóc trán, HF00333/HF00561 có mặt phụ. Dữ liệu này được giữ nguyên, không gọi detector_count=1 là chứng nhận ảnh chỉ có một mặt. [visual_review_notes.json](../../outputs/C1_lbp/roi_validation/visual_review_notes.json).

## Contact sheets và lựa chọn case

Có **18 case**, chọn từ nhóm CFD/HF bắt buộc, các min/max quan sát thật, bất đối xứng diện tích và toàn bộ bốn geometry invalid; không dùng ranking. Không có mask thật sự dưới ngưỡng nhỏ, nên ảnh “smallest observed” chỉ là cực trị tương đối, không giả tạo một case ROI rất nhỏ.

Mỗi case có10 panel: nguồn toàn khung, A68, bốn polygon nguyên gốc, bốn mask raw riêng, overlap đỏ, unassigned-face và bảng số. Bốn binary PNG riêng/case cho **72 mask** được đọc lại kiểm hash/pixelcount; overlap còn nguyên. Nhãn geometry hợp lệ bao nhiêu/4 và anatomy UNVERIFIED luôn hiển thị.

[Index toàn bộ18 case](../../outputs/C1_lbp/roi_validation/contact_sheets/index.md), [overview](../../outputs/C1_lbp/roi_validation/contact_sheets/overview.png), [HF00198 lỗi/kính](../../outputs/C1_lbp/roi_validation/contact_sheets/hf_merged_00198/contact.png), [HF00722 tay](../../outputs/C1_lbp/roi_validation/contact_sheets/hf_merged_00722/contact.png). [case_selection.json](../../outputs/C1_lbp/roi_validation/case_selection.json) ghi lý do cho mọi case.

## Điều chỉnh chỉ được đề xuất

Đề xuất v0.3 chuyển biên dưới trán sang native lower brow chain +0.02D, không sửa A. Trên18 case: coverage proxy khoảng99.64–100%, nhưng chỉ17 case simple, HF00198 vẫn tự giao. **Chưa kích hoạt và chưa xác thực toàn5752 ROI**. Cần xử lý side closure có căn cứ giải phẫu và review annotation trước candidate mới. Không dùng coverage đẹp hơn/Top-5 làm tiêu chí tự duyệt. Các vùng má/mũi–miệng chưa có annotation canonical; không tự thay MP129/358 hoặc MP1/4.

Xem [C1_final_roi_contract.md](../C1_final_roi_contract.md) và [bộ hình so sánh](../../outputs/C1_lbp/roi_validation/forehead_amendment_comparisons.json).

## Điều kiện thử nghiệm kỹ thuật 100 ảnh

Đã chuẩn bị manifest100 ảnh **50 CFD/50 HF**, bắt buộc chứa18 case và bốn case lỗi, phần còn lại lấy theo SHA-256 seed `C1_trial100_v0.2` trên image_id, không theo retrieval hoặc chọn chỉ ảnh đẹp. Hiện có **96 ảnh geometry/support-ready và4 ảnh phải trả missing_C1**. [trial100_manifest.json](../../outputs/C1_lbp/roi_validation/trial100_manifest.json).

Có thể dùng100 input này cho **smoke test kỹ thuật có96 positive/4 negative paths** khi được giao viết extractor sau này, với contract/LBP-spec hashes đã pin, same raw-overlap/gray/bin/support và output namespace/version mới. Không đủ điều kiện tuyên bố có100 vector C1 hợp lệ hoặc 100 ROI anatomy-approved. Trước extraction chính thức cần sửa/kiểm toàn bộ lỗi hình học, chốt giải phẫu/brow coverage/occlusion và các convention đã chọn với thẩm quyền phù hợp.

**Chưa chạy trial, chưa viết extractor, chưa tạo vector.** Không thay calibration hoặc thuật toán A/B.

## Kiểm chứng và phạm vi bất biến

11 tests về raster float, support21, retention overlap, independent crossings, contract hash, 59-bin table, grayscale scalar fixtures, full5752 census, PNG round-trip và trial negative cases đạt. Bảng bit-word có58 uniform patterns vào58 bins riêng và198 nonuniform vào bin58; không xử lý LBP trên ảnh. [tests.log](../../outputs/C1_lbp/roi_validation/tests.log), [verification.json](../../outputs/C1_lbp/roi_validation/verification.json).

Hash toàn bộ **14387 file đã có** trước/sau không đổi, gồm proposal/overlay v0.1, các SQLite đã nghiệm thu, PDF, dataset, source/mapping A, vectors/stats/calibration/query A+B. [final_scope.json](../../outputs/C1_lbp/roi_validation/final_scope.json), [manifest file mới](../../outputs/C1_lbp/roi_validation/created_files_manifest.json).

Lệnh PowerShell thực tế đã chạy tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_final_tools/validate_roi_all.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_final_tools/render_contact_sheets.py
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s docs/audits/c1_final_tools -p test_c1_specs.py -v
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_final_tools/verify_full_validation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_final_tools/write_final_specs.py
```

Validation và contact stage từ chối ghi đè bộ đã hoàn tất; chỉ tạo output mới của nhiệm vụ này. Kết luận: **đã hoàn tất kiểm toán5752 ROI và đặc tả kỹ thuật, contract vẫn PROVISIONAL; không chứng nhận toàn hệ thống100%**.
