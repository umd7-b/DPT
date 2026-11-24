# Hoàn thiện metadata mắt từ landmark audit đã lưu

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` không đổi. Đọc lại §1.3, §2.2 và §2.4 qua bản trích text audit đã đóng băng; PDF gốc được kiểm hash trực tiếp. [Trang PDF liên quan và hash bản trích](eye_c1_evidence/pdf_sections_review.json).

Giữ nguyên CSDL đã nghiệm thu, source/mapping A, dataset, PDF, vector/stats/calibration/query artifacts v1/v2. Lần này thêm bản SQLite có tên mới, metadata đo lại, hợp đồng ROI **đề xuất** và công cụ/bằng chứng audit. Không chạy lại MediaPipe, không viết extractor LBP/HOG, không tạo vector C1/C2.


## Kết quả

**Đã bổ sung bản đo mắt mới cho đủ 1438 ảnh, không có ảnh không thể đo trong archive được kiểm tra.** Trong đó 1435 ảnh được bổ sung coverage CSDL lần đầu; ba ảnh đã có phép đo cũ được thêm phiên bản phương pháp mới. Đây là tọa độ **đo lại khi audit**, không phải tọa độ được chứng minh đã dùng để alignment lịch sử.

| Hạng mục | Kết quả |
| --- | --- |
| Ảnh có metadata mắt mới | 1438 |
| Ảnh không thể đo | 0 |
| Dòng mới / dòng lịch sử giữ nguyên | 1438 / 3 |
| Tổng dòng EyeCoordinates có version | 1441 |
| Ảnh có tọa độ alignment lịch sử đã xác minh | 0 |
| MediaPipe chạy lại | False |
| SQLite round-trip đúng mọi giá trị | True |
| Max sai số so với scalar mean float64 | 2.288818359375e-05 |
| Max chênh IPD với metadata A hiện hành | 0.0 |

Bản CSDL trước mới nhập ba phép đo từ ba file landmark riêng. Archive `dataset_landmarks478.npz` của audit đầu tiên đã có đủ 1438 ảnh; đợt này khai thác archive đó và đóng khoảng trống coverage của CSDL. Giới hạn đã nhập của hồ sơ trước không có nghĩa kho chỉ có ba bộ landmark.

## Nguồn landmark và tính xác thực

Archive: `docs/audits/evidence/dataset_landmarks478.npz`, SHA-256 `a21e4abce28354d3a1fe5541bf0d2b7ab6d4b6d1119207d3231471bcacf263ed`, shape `[1438,478,2]`, dtype `<f4`; có `image_names` riêng. Hash khớp **manifest audit gốc** và baseline đóng băng hiện tại. Import nối tên ảnh sang image_id trong Images, không coi thứ tự archive hay catalog là định danh.

Producer `docs/audits/audit_tools/measure_dataset.py` dùng model `face_landmarker.task`, IMAGE mode, `num_faces=5`, lưu face index 0; log từng ảnh ghi một face được model phát hiện và 478 điểm. Tọa độ pixel được tính ở float64 rồi cast thành float32 khi lưu archive. Mọi ảnh nguồn được đối chiếu lại hash, width/height, log và danh tính với CSDL; không ảnh nào có landmark rỗng, nonfinite hoặc tâm mắt ngoài ảnh trong bộ dữ liệu này.

Model asset SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` được đối chiếu với baseline tại audit; `model_version` dùng hash này như phiên bản nội dung. **Package version MediaPipe tại lần tạo archive toàn kho không được ghi lại**, nên giữ thông tin đó là chưa biết; không suy ra từ package version của một lần audit sau. Khuyết log này không ngăn tái sử dụng tọa độ đã lưu và đã xác thực byte; nó giới hạn khả năng tái lập lần suy luận model lịch sử. [landmark_source_proof.json](eye_c1_evidence/landmark_source_proof.json).

Hash mỗi nguồn landmark là SHA-256 **byte C-order của riêng hàng 478×2 float32**; kèm dtype/shape, NPZ member, chỉ số hàng và hash cả archive trong provenance. Không nhầm row hash với hash ảnh hoặc hash file NPZ.

## Phương pháp tâm mắt hiện hành

`geometry_features.py::normalize_landmarks` dùng:

```text
L = numpy.mean(P478[[33,160,158,133,153,144]], axis=0)
R = numpy.mean(P478[[362,385,387,263,373,380]], axis=0)
```

Hai nhóm tương ứng A68 `[36..41]` và `[42..47]` theo thứ tự mapping hiện tại. Input là float32 nên phép mean và kết quả hiện hành là float32. Khi đưa kết quả vào SQLite REAL, promote từng giá trị sang float64 biểu diễn **đúng giá trị float32 đó**, không tính lại mean bằng float64. Method: `numpy_mean6_float32_from_saved478_v1`. Phép đo được thực hiện với NumPy `2.4.6` của môi trường hiện có; không import/chạy MediaPipe.

Coordinate system: `pixel_xy; origin=top_left; x_right; y_down; original_256x256; left_right=viewer/code`. Sáu mốc mí không tự đồng nghĩa tâm đồng tử/iris; trái/phải theo code/người xem, không ngầm đổi thành trái/phải giải phẫu. PDF cho công thức trung điểm hai mắt và chuẩn hóa theo khoảng cách, nhưng không chốt centroid sáu mí hoặc dtype arithmetic này. Vì vậy đây là **IMPLEMENTATION DETAIL của phép đo hiện hành**, không phải định nghĩa canonical do PDF quy định.

Oracle scalar float64 chỉ dùng để kiểm sai số làm tròn, không thay giá trị đã chọn. Max chênh toàn kho `2.288818359375e-05` pixel; round-trip SQLite là **exact**, không phải tolerance đó. IPD tính bằng phép toán float32 hiện hành khớp metadata A cho cả 1438 ảnh, max chênh `0.0`. Điều này không chứng minh vị trí alignment lịch sử hoặc mọi endpoint giải phẫu đúng.

## CSDL mới và version hóa

- [CSDL metadata mắt mới](../../database/data/portrait_ab_v2_eye_metadata_v1.sqlite3), SHA-256 `6fc6213286c715edf997ed9484ca1da8da0d07dff59e2c486375fd53e34f4396`.
- CSDL nguồn vẫn có SHA-256 `a74617294f5d60af432ff781cdd50b11f636d9a3ba43ba19a51d03a86eb535c1`; không ghi đè file đó hoặc backup/restore đã nghiệm thu.
- [Migration cộng thêm](eye_c1_tools/eye_metadata_extension.sql): EyeMeasurementBatches, EyeCoordinateSources, EyeMeasurementAttempts và view **EyeMetadataAuditV1**.
- Batch `eye_mean6_saved478_v1` lưu hash source DB/archive, method, model và coordinate system. `PRAGMA user_version=1` của A/B giữ để tương thích loader cũ; extension được version hóa bằng batch/table riêng.

Mỗi trong 1438 bản ghi mới có đầy đủ các trường người dùng yêu cầu qua view:

```sql
SELECT image_id,left_x,left_y,right_x,right_y,coordinate_system,
       eye_center_method,model_version,source_landmark_hash,provenance,
       measurement_role
FROM EyeMetadataAuditV1
ORDER BY image_id;
```

Role luôn `audit_remeasurement`. EyeCoordinateSources có FK composite đến đúng bản ghi EyeCoordinates theo method/model/role; nguồn không xác thực hoặc ảnh lỗi không được đoán tọa độ. Nếu thiếu/invalid thì ghi EyeMeasurementAttempts với reason và không INSERT tọa độ. Lần này mọi 1438 dòng đều đo được; [unmeasurable_eyes.csv](eye_c1_evidence/unmeasurable_eyes.csv) chỉ có header.

EyeCoordinates tổng **1441 dòng có version**, phủ **1438 image_id**: 1438 dòng mới cộng ba dòng scalar-f64 lịch sử giữ nguyên. Dùng view version thay vì JOIN EyeCoordinates chỉ bằng image_id rồi vô tình nhân dòng. Ba phép đo cũ khác nhẹ về precision, không phải bị cập nhật hoặc thay thế:

| Ảnh | Scalar-f64 lịch sử | NumPy-f32 mới | Max ∣Δ∣ pixel |
| --- | --- | --- | --- |
| cfd_final_00001 | [88.17080307006836, 102.11359151204427, 168.9585215250651, 102.82492955525716] | [88.1707992553711, 102.11358642578125, 168.95851135253906, 102.8249282836914] | 1.0172526032192764e-05 |
| cfd_final_00069 | [87.96431223551433, 102.16291681925456, 166.66907246907553, 102.46160507202148] | [87.96431732177734, 102.16292572021484, 166.66908264160156, 102.46160888671875] | 1.0172526032192764e-05 |
| hf_merged_00001 | [88.83979161580403, 102.66320673624675, 167.23843892415366, 102.58268356323242] | [88.83979034423828, 102.6632080078125, 167.23843383789062, 102.58267974853516] | 5.0862630303072365e-06 |

## INSERT/SELECT, round-trip và phục hồi

Đã INSERT 1438 dòng EyeCoordinates và nguồn đo tương ứng trong một transaction trên bản sao mới, SELECT đủ 1438 dòng rồi đối chiếu tọa độ và row hash từng ảnh. [eye_measurements.csv](eye_c1_evidence/eye_measurements.csv), [eye_roundtrip_validation.csv](eye_c1_evidence/eye_roundtrip_validation.csv).

Đã kiểm PK/FK/hash-length/role bằng writes bị từ chối trên bản copy trong RAM. 16 bảng gốc được kiểm: 15 bảng giữ nguyên mọi giá trị; EyeCoordinates giữ đúng ba dòng cũ và chỉ thêm dòng mới. Vector, normalization, calibration, QueryVectors và RetrievalRuns/Results không đổi. [original_database_tables_validation.json](eye_c1_evidence/original_database_tables_validation.json).

Đã backup bằng SQLite API sang [snapshot mới](../../database/backups/portrait_ab_v2_eye_metadata_v1.backup.sqlite3), phục hồi sang [file mới](../../database/restored/portrait_ab_v2_eye_metadata_v1.sqlite3), so khớp toàn bộ SQL dump và view 1438 dòng; integrity/FK đạt. Truy vấn Top-5 A/B/AB sau phục hồi cũng khớp bản mới. [backup_restore.json](eye_c1_evidence/backup_restore.json), [restored_search_validation.json](eye_c1_evidence/restored_search_validation.json).

**10 tests mới +19 regression tests v2 đạt.** Xem [tests.log](eye_c1_evidence/tests.log), [v2_regression_tests.log](eye_c1_evidence/v2_regression_tests.log). Tất cả `14345` file đã có được so hash trước/sau và không đổi. Metadata mới không chứng nhận lại dataset hoặc alignment gốc.
