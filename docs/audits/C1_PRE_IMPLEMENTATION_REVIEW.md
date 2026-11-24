# Kiểm tra trước triển khai C1

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` không đổi. Đọc lại §1.3, §2.2 và §2.4 qua bản trích text audit đã đóng băng; PDF gốc được kiểm hash trực tiếp. [Trang PDF liên quan và hash bản trích](eye_c1_evidence/pdf_sections_review.json).

Giữ nguyên CSDL đã nghiệm thu, source/mapping A, dataset, PDF, vector/stats/calibration/query artifacts v1/v2. Lần này thêm bản SQLite có tên mới, metadata đo lại, hợp đồng ROI **đề xuất** và công cụ/bằng chứng audit. Không chạy lại MediaPipe, không viết extractor LBP/HOG, không tạo vector C1/C2.


**Metadata mắt đo lại đã đủ 1438 ảnh. Hợp đồng ROI C1 mới ở trạng thái đề xuất; chưa đủ cơ sở công nhận ROI giải phẫu chính thức hoặc toàn hệ thống tuân thủ 100%.**

| Phạm vi | Bằng chứng | Kết luận |
| --- | --- | --- |
| Metadata mới | 1438 ảnh; 0 không đo được | Đã hoàn thành coverage đo lại |
| Landmark input | 1438×478×2 float32, hash manifest audit gốc khớp | Không chạy lại detector |
| CSDL nguồn | Hash trước/sau không đổi; 16 bảng được đối chiếu | Bản mới chỉ thêm eye metadata/extension |
| Round-trip SQLite | 1438 tọa độ và row hash khớp exact | Không dùng tolerance để che mất giá trị |
| Backup/restore | SQL dump và toàn bộ view mắt khớp | Đạt integrity/FK |
| A/B vectors, stats, calibration | Mọi bảng gốc tương ứng và file artifact giữ nguyên | Không fit lại hoặc đổi thuật toán |
| A+B ranking | 15 mode/case; toàn bộ rank và khoảng cách khớp, Top-5 khớp output v2 | Không chỉ so ảnh đứng đầu |
| ROI C1 | 4 polygon, 8 ảnh/32 vùng; chỉ kiểm hình học | Đề xuất chưa được phê duyệt giải phẫu |
| C1/C2 | 0 version/vector mới, không extractor LBP/HOG | Chưa triển khai |
| Toàn hệ thống | Mapping/dataset/metadata lịch sử còn giới hạn | Không chứng nhận 100% |

## Yêu cầu rõ của PDF và khoảng trống đặc tả

§1.3 yêu cầu lưu vị trí mắt; đợt này đã lưu phép đo có provenance cho mọi ảnh, nhưng không khôi phục log alignment gốc chưa tồn tại. §2.2 quy định A150 và chuẩn hóa landmark; source và indices không đổi. §2.4 quy định bốn vùng theo landmark, LBP P=8/R=2, threshold s(x)=1 với x≥0, 59 bin uniform không bất biến quay, L1 từng vùng và ghép 236 chiều.

PDF chưa chốt polygon, hệ quy chiếu trái/phải, grayscale conversion, vị trí bắt đầu/chiều đi bit, nội suy mẫu tròn ở vị trí không nguyên, số thứ tự bin uniform, ROI support ở biên, ngưỡng vùng thiếu hoặc policy occlusion. Phải phân biệt các lựa chọn đó với điều khoản rõ; không triển khai biến thể rotation-invariant 10 bin rồi gọi là 59 bin.

## Những việc đã được chứng minh

Archive toàn kho có sẵn và hash xác thực; ảnh được join bằng tên/ID với metadata/hash, không gán theo vị trí row. Mỗi tâm mới là mean6 float32 đúng kiểu tính của code A hiện hành, kèm coordinate_system/model asset version/row hash/provenance và role audit_remeasurement. Ba dòng scalar64 trước được giữ nguyên; tổng 1441 dòng version không phải 1441 ảnh.

CSDL mới [portrait_ab_v2_eye_metadata_v1.sqlite3](../../database/data/portrait_ab_v2_eye_metadata_v1.sqlite3) được tạo từ backup nguồn và migration cộng thêm. Bản nguồn và các backup cũ không đổi. New metadata SELECT qua EyeMetadataAuditV1 đủ 1438 ID; không có giá trị suy đoán hoặc placeholder cho lỗi.

Các bảng FeatureVectors, FeatureVersions, NormalizationStages, Calibrations/Components/Candidates/Pairs/PairDistances và các run/result/query vector cũ giữ nguyên. Xếp hạng được kiểm đầy đủ cho ba query CFD, HF00209 thiếu B và query mới đã lưu: **15 mode/case**. Với new_query, verifier đọc QueryVectors đã lưu từ CSDL, không chạy lại worker hoặc MediaPipe. Không INSERT thêm retrieval run chỉ để kiểm tra.

10 tests mới và 19 regression tests v2 đạt. Backup/restore mới kiểm toàn bộ SQL dump, 1438 metadata mắt, integrity và FK. Hash toàn bộ **14345 file đã đóng băng** được so trước/sau, không đổi, gồm ba file SQLite gốc và artifact A/B v1/v2. [verification_summary.json](eye_c1_evidence/verification_summary.json), [ranking_preservation.json](eye_c1_evidence/ranking_preservation.json), [final_scope.json](eye_c1_evidence/final_scope.json).

## Những vấn đề vẫn mở

| Vấn đề | Trạng thái và ảnh hưởng |
| --- | --- |
| Coordinate alignment lịch sử | UNVERIFIED cho mọi ảnh; audit_remeasurement không phải original_preprocessing. |
| Sáu mí so với tâm mắt giải phẫu | Quy ước code đã xác định, equivalence với pupil/iris chưa được chứng minh. |
| Package version lúc tạo full archive | Không ghi lại; model asset hash và byte landmark có thể xác thực, không khẳng định tái lập suy luận lịch sử hoàn toàn. |
| Mapping A so với hình PDF | Sai khác đã xác nhận ở hàm/mũi; không sửa A hoặc tự chọn index thay thế. |
| Canonical endpoints/polygon anatomy | UNVERIFIED; membership contour và polygon không tự giao không phải annotation giải phẫu. |
| Trán và toàn bộ lông mày | Biên dưới đề xuất có thể bỏ một phần mày; cần xác minh coverage trước khi công nhận. |
| Dataset | HF00333/HF00561 có mặt phụ; HF00722 che miệng. HF00694 có vải/kính cần review. Giữ nguyên ảnh. |
| Missing B và missing C1 | Hai trạng thái độc lập; HF00209 có thể dựng ROI dù thiếu B, nhưng chưa có C1 vector để chứng minh trạng thái C1. |
| Thống kê người, tuổi, cảm xúc/alignment | Các giới hạn audit trước vẫn còn; không suy đoán nhãn hoặc ép số đo cho khớp PDF. |
| Relevance | Chưa có nhãn độc lập; không dùng retrieval để chọn ROI hoặc chứng nhận thuật toán. |

## Các bước cần thiết để triển khai C1 đúng PDF

1. Chốt và đóng băng contract ROI với tác giả/annotation có thẩm quyền: endpoints, trái/phải, forehead auxiliary points, margin, overlap, coverage, clipping và policy vùng thiếu/che khuất. Giữ source A không đổi trừ khi có nhiệm vụ sửa riêng với chứng cứ.
2. Chốt grayscale, mẫu tròn P=8/R=2, interpolation, bit order và mapping **58 mẫu uniform riêng +1 bin nonuniform**. Quy ước triển khai phải có version, không thay 59 bin thành 10 bin.
3. Chốt support tại biên và điều kiện một vùng hợp lệ; test constant image, pattern có mã biết trước, pixel biên/đồng mức và ảnh thiếu vùng. Không zero-fill để ép đủ chiều.
4. Khi được giao viết extractor, tính histogram từng vùng và L1 riêng, ghép theo thứ tự đã chốt thành 236 chiều; lưu version và provenance. Hiện chưa thực hiện bước này.
5. Khi được giao retrieval C1, dùng Chi-square có hệ số 0.5 theo PDF, stats/calibration phiên bản mới và cùng protocol cặp đại diện phù hợp. Không ghi đè calibration A/B hoặc tự gọi A+B hiện tại là fusion bốn vector.
6. Review corpus/occlusion và đánh giá relevance theo protocol độc lập. Đóng các giới hạn dataset/mapping trước khi ký nhận toàn hệ thống.

Có thể dùng metadata/view mới và geometry proposal làm dữ liệu chuẩn bị kỹ thuật; **chưa dùng proposal để trích xuất/đánh giá vector C1 như một phương án đã được PDF chứng nhận**. Nhiệm vụ này hoàn tất phần metadata và hồ sơ chuẩn bị, không triển khai C1/C2.

## Hồ sơ và lệnh PowerShell thực tế

- [EYE_METADATA_COMPLETION.md](EYE_METADATA_COMPLETION.md)
- [C1_ANATOMICAL_ROI_SPEC.md](C1_ANATOMICAL_ROI_SPEC.md)
- [Contract JSON](eye_c1_evidence/c1_roi_contract_proposal_v0.json), [contact sheet](eye_c1_evidence/overlays/roi_contact_sheet.png)
- [Migration SQL](eye_c1_tools/eye_metadata_extension.sql), [công cụ chuẩn bị](eye_c1_tools/prepare_eye_roi.py), [verifier](eye_c1_tools/verify_eye_roi.py)

Chạy tại repository root, không cài thêm thư viện:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/eye_c1_tools/prepare_eye_roi.py
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s docs/audits/eye_c1_tools -p test_eye_roi.py -v
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/eye_c1_tools/verify_eye_roi.py
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\.venv311\Scripts\python.exe -X utf8 -B -m database search --db database/data/portrait_ab_v2_eye_metadata_v1.sqlite3 --image cfd_final_00001.png --no-save
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/eye_c1_tools/write_eye_roi_reviews.py
```

Lệnh chuẩn bị tạo CSDL mới một lần và từ chối tên đã có; verifier cũng từ chối overwrite snapshot. Preview được cập nhật riêng bằng hàm audit prepare_roi_preview khi rà quy tắc hình học; không tạo lại CSDL hay chạy detector. Tra cứu từ CSDL mới dùng `--no-save` để giữ snapshot không đổi.
