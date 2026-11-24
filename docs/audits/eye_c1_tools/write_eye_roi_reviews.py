"""Write the three requested reports and final immutable-input manifests."""
from contextlib import closing
from pathlib import Path
import re
import sys

import numpy as np
import prepare_eye_roi as task
from shared.report_v2 import read_json,write_json

ROOT=task.ROOT
DOC=ROOT/'docs/audits'
E=task.E


def table(headers,rows):
    def cell(x):
        return str(x).replace('|','∣').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(cell,row))+' |' for row in rows])


def save(name,text):
    (DOC/name).write_text(text.strip()+'\n',encoding='utf-8')


def endpoint_role(item):
    if item['ref']=='MP478_AUX':
        return 'Upper FACE_OVAL phụ trợ; không phải hairline/đỉnh trán GT'
    i=item['index']
    if i<=16:
        return 'JAW/FACE_OVAL proxy; biên dưới má được đề xuất'
    if i<=26:
        return 'Đường mày thưa hiện hành; biên dưới có offset đề xuất'
    if i==27:
        return 'Đầu nhánh sống mũi theo code; endpoint canonical chưa chốt'
    if i in (31,35):
        return 'Cánh/bên mũi proxy; MP129/358 không thuộc sparse NOSE'
    if 36<=i<=47:
        return 'Khóe/mí mắt thuộc EYE; offset ra vùng dưới mắt là đề xuất'
    return 'Khóe/đường môi ngoài thuộc LIPS; biên quanh miệng là đề xuất'


def main():
    s=read_json(E/'verification_summary.json')
    proof=read_json(E/'landmark_source_proof.json')
    spec=read_json(E/'c1_roi_contract_proposal_v0.json')
    preview=read_json(E/'roi_preview_validation.json')
    historical=read_json(E/'historical_eye_measurement_comparison.json')
    assert s['status']=='PASS' and task.db.digest(task.NEW_DB)==s['new_database_sha256']
    for name,count in [('tests.log',10),('v2_regression_tests.log',19)]:
        log=(E/name).read_text(encoding='utf-8-sig')
        assert f'Ran {count} tests' in log and log.rstrip().endswith('OK')
    intro=f'''Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256 `{task.db.legacy.REPORT_SHA256}` không đổi. Đọc lại §1.3, §2.2 và §2.4 qua bản trích text audit đã đóng băng; PDF gốc được kiểm hash trực tiếp. [Trang PDF liên quan và hash bản trích](eye_c1_evidence/pdf_sections_review.json).

Giữ nguyên CSDL đã nghiệm thu, source/mapping A, dataset, PDF, vector/stats/calibration/query artifacts v1/v2. Lần này thêm bản SQLite có tên mới, metadata đo lại, hợp đồng ROI **đề xuất** và công cụ/bằng chứng audit. Không chạy lại MediaPipe, không viết extractor LBP/HOG, không tạo vector C1/C2.
'''
    stats=[['Ảnh có metadata mắt mới',s['measured_images']],['Ảnh không thể đo',s['unmeasurable_images']],
        ['Dòng mới / dòng lịch sử giữ nguyên',f"{s['new_eye_rows']} / {s['inherited_historical_eye_rows']}"],
        ['Tổng dòng EyeCoordinates có version',s['total_versioned_eye_rows']],
        ['Ảnh có tọa độ alignment lịch sử đã xác minh',0],['MediaPipe chạy lại',False],
        ['SQLite round-trip đúng mọi giá trị',s['sqlite_roundtrip_exact']],
        ['Max sai số so với scalar mean float64',s['max_abs_delta_vs_scalar64_mean']],
        ['Max chênh IPD với metadata A hiện hành',s['max_ipd_delta_vs_a_metadata']]]
    history_rows=[[r['image_id'],r['historical_scalar64'],r['new_numpy32'],r['max_abs_difference']] for r in historical]
    save('EYE_METADATA_COMPLETION.md',f'''# Hoàn thiện metadata mắt từ landmark audit đã lưu

{intro}

## Kết quả

**Đã bổ sung bản đo mắt mới cho đủ 1438 ảnh, không có ảnh không thể đo trong archive được kiểm tra.** Trong đó 1435 ảnh được bổ sung coverage CSDL lần đầu; ba ảnh đã có phép đo cũ được thêm phiên bản phương pháp mới. Đây là tọa độ **đo lại khi audit**, không phải tọa độ được chứng minh đã dùng để alignment lịch sử.

{table(['Hạng mục','Kết quả'],stats)}

Bản CSDL trước mới nhập ba phép đo từ ba file landmark riêng. Archive `dataset_landmarks478.npz` của audit đầu tiên đã có đủ 1438 ảnh; đợt này khai thác archive đó và đóng khoảng trống coverage của CSDL. Giới hạn đã nhập của hồ sơ trước không có nghĩa kho chỉ có ba bộ landmark.

## Nguồn landmark và tính xác thực

Archive: `docs/audits/evidence/dataset_landmarks478.npz`, SHA-256 `{proof['archive_sha256']}`, shape `[1438,478,2]`, dtype `{proof['dtype']}`; có `image_names` riêng. Hash khớp **manifest audit gốc** và baseline đóng băng hiện tại. Import nối tên ảnh sang image_id trong Images, không coi thứ tự archive hay catalog là định danh.

Producer `docs/audits/audit_tools/measure_dataset.py` dùng model `face_landmarker.task`, IMAGE mode, `num_faces=5`, lưu face index 0; log từng ảnh ghi một face được model phát hiện và 478 điểm. Tọa độ pixel được tính ở float64 rồi cast thành float32 khi lưu archive. Mọi ảnh nguồn được đối chiếu lại hash, width/height, log và danh tính với CSDL; không ảnh nào có landmark rỗng, nonfinite hoặc tâm mắt ngoài ảnh trong bộ dữ liệu này.

Model asset SHA-256 `{proof['model_sha256']}` được đối chiếu với baseline tại audit; `model_version` dùng hash này như phiên bản nội dung. **Package version MediaPipe tại lần tạo archive toàn kho không được ghi lại**, nên giữ thông tin đó là chưa biết; không suy ra từ package version của một lần audit sau. Khuyết log này không ngăn tái sử dụng tọa độ đã lưu và đã xác thực byte; nó giới hạn khả năng tái lập lần suy luận model lịch sử. [landmark_source_proof.json](eye_c1_evidence/landmark_source_proof.json).

Hash mỗi nguồn landmark là SHA-256 **byte C-order của riêng hàng 478×2 float32**; kèm dtype/shape, NPZ member, chỉ số hàng và hash cả archive trong provenance. Không nhầm row hash với hash ảnh hoặc hash file NPZ.

## Phương pháp tâm mắt hiện hành

`geometry_features.py::normalize_landmarks` dùng:

```text
L = numpy.mean(P478[[33,160,158,133,153,144]], axis=0)
R = numpy.mean(P478[[362,385,387,263,373,380]], axis=0)
```

Hai nhóm tương ứng A68 `[36..41]` và `[42..47]` theo thứ tự mapping hiện tại. Input là float32 nên phép mean và kết quả hiện hành là float32. Khi đưa kết quả vào SQLite REAL, promote từng giá trị sang float64 biểu diễn **đúng giá trị float32 đó**, không tính lại mean bằng float64. Method: `{task.METHOD}`. Phép đo được thực hiện với NumPy `{np.__version__}` của môi trường hiện có; không import/chạy MediaPipe.

Coordinate system: `{task.COORDINATE_SYSTEM}`. Sáu mốc mí không tự đồng nghĩa tâm đồng tử/iris; trái/phải theo code/người xem, không ngầm đổi thành trái/phải giải phẫu. PDF cho công thức trung điểm hai mắt và chuẩn hóa theo khoảng cách, nhưng không chốt centroid sáu mí hoặc dtype arithmetic này. Vì vậy đây là **IMPLEMENTATION DETAIL của phép đo hiện hành**, không phải định nghĩa canonical do PDF quy định.

Oracle scalar float64 chỉ dùng để kiểm sai số làm tròn, không thay giá trị đã chọn. Max chênh toàn kho `{s['max_abs_delta_vs_scalar64_mean']}` pixel; round-trip SQLite là **exact**, không phải tolerance đó. IPD tính bằng phép toán float32 hiện hành khớp metadata A cho cả 1438 ảnh, max chênh `{s['max_ipd_delta_vs_a_metadata']}`. Điều này không chứng minh vị trí alignment lịch sử hoặc mọi endpoint giải phẫu đúng.

## CSDL mới và version hóa

- [CSDL metadata mắt mới](../../database/data/portrait_ab_v2_eye_metadata_v1.sqlite3), SHA-256 `{s['new_database_sha256']}`.
- CSDL nguồn vẫn có SHA-256 `{s['source_database_sha256']}`; không ghi đè file đó hoặc backup/restore đã nghiệm thu.
- [Migration cộng thêm](eye_c1_tools/eye_metadata_extension.sql): EyeMeasurementBatches, EyeCoordinateSources, EyeMeasurementAttempts và view **EyeMetadataAuditV1**.
- Batch `{task.BATCH}` lưu hash source DB/archive, method, model và coordinate system. `PRAGMA user_version=1` của A/B giữ để tương thích loader cũ; extension được version hóa bằng batch/table riêng.

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

{table(['Ảnh','Scalar-f64 lịch sử','NumPy-f32 mới','Max ∣Δ∣ pixel'],history_rows)}

## INSERT/SELECT, round-trip và phục hồi

Đã INSERT 1438 dòng EyeCoordinates và nguồn đo tương ứng trong một transaction trên bản sao mới, SELECT đủ 1438 dòng rồi đối chiếu tọa độ và row hash từng ảnh. [eye_measurements.csv](eye_c1_evidence/eye_measurements.csv), [eye_roundtrip_validation.csv](eye_c1_evidence/eye_roundtrip_validation.csv).

Đã kiểm PK/FK/hash-length/role bằng writes bị từ chối trên bản copy trong RAM. 16 bảng gốc được kiểm: 15 bảng giữ nguyên mọi giá trị; EyeCoordinates giữ đúng ba dòng cũ và chỉ thêm dòng mới. Vector, normalization, calibration, QueryVectors và RetrievalRuns/Results không đổi. [original_database_tables_validation.json](eye_c1_evidence/original_database_tables_validation.json).

Đã backup bằng SQLite API sang [snapshot mới](../../database/backups/portrait_ab_v2_eye_metadata_v1.backup.sqlite3), phục hồi sang [file mới](../../database/restored/portrait_ab_v2_eye_metadata_v1.sqlite3), so khớp toàn bộ SQL dump và view 1438 dòng; integrity/FK đạt. Truy vấn Top-5 A/B/AB sau phục hồi cũng khớp bản mới. [backup_restore.json](eye_c1_evidence/backup_restore.json), [restored_search_validation.json](eye_c1_evidence/restored_search_validation.json).

**10 tests mới +19 regression tests v2 đạt.** Xem [tests.log](eye_c1_evidence/tests.log), [v2_regression_tests.log](eye_c1_evidence/v2_regression_tests.log). Tất cả `{s['protected_files_checked']}` file đã có được so hash trước/sau và không đổi. Metadata mới không chứng nhận lại dataset hoặc alignment gốc.
''')

    part_names={'forehead_brow':'Trán và vùng lông mày','cheek_left_viewer':'Má trái theo ảnh/người xem',
        'cheek_right_viewer':'Má phải theo ảnh/người xem','nose_mouth':'Mũi và miệng'}
    polygon_sections=[]
    for key in task.REGIONS:
        vertex_rows=[]
        for order,item in enumerate(spec['polygons'][key]):
            ref=('A'+str(item['index'])) if item['ref']=='A68' else ('MP'+str(item['index'])+' phụ trợ')
            vertex_rows.append([order,ref,item['mediapipe_index'],item['offset_u_ipd'],item['offset_v_ipd'],
                endpoint_role(item),'IMPLEMENTATION DETAIL đề xuất; canonical endpoint UNVERIFIED'])
        polygon_sections.append('### '+part_names[key]+' — `'+key+'`\n\n'+table(
            ['Thứ tự đỉnh','Tham chiếu','MP index','α theo u','β theo v','Ý nghĩa/giới hạn','Phân loại'],vertex_rows))
    preview_rows=[]
    observations={
        'cfd_final_00001.png':'Bốn vùng dựng được; biên dưới vùng trán có thể bỏ một phần thân lông mày. Cần annotation, không tự tăng margin.',
        'cfd_final_00069.png':'Biểu cảm làm vùng mũi–miệng biến dạng; vẫn dựng được. Chưa chứng minh tính ổn định kết cấu.',
        'hf_merged_00001.png':'Trán/mày, hai má và mũi–miệng tách được về hình học; coverage giải phẫu chưa có GT.',
        'hf_merged_00333.png':'Mặt phụ vẫn xuất hiện ở mép ảnh; chọn một bộ landmark không giải quyết vi phạm dataset.',
        'hf_merged_00561.png':'Có mặt phụ và tóc phủ vùng trán; mask hình học có thể chứa tóc, không tự sửa ảnh hoặc loại pixel.',
        'hf_merged_00722.png':'Tay/ngón nằm trong polygon mũi–miệng và gần má; geometric-valid không phải unoccluded-valid.',
        'hf_merged_00209.png':'Có B thiếu tóc nhưng vẫn có landmark và bốn polygon; không suy ra thiếu B đồng nghĩa thiếu C1.',
        'hf_merged_00694.png':'Vùng trán chứa phần vải che; kính và biên má còn cần đánh giá. Chưa chứng nhận mô giải phẫu.'}
    for row in preview['cases']:
        preview_rows.append([row['image_name'],', '.join(f"{key}={row['assigned_pixels'][key]}" for key in task.REGIONS),
            row['raw_pairwise_overlap_pixels'],observations[row['image_name']]])
    save('C1_ANATOMICAL_ROI_SPEC.md',f'''# Hợp đồng vùng giải phẫu C1 — đề xuất v0.1, chưa phê duyệt

{intro}

## Phần PDF quy định rõ

PDF §2.4.2, trang vật lý **13**, quy định bốn vùng độc lập dựa trên landmark: **(1) Trán và vùng lông mày; (2) Má trái; (3) Má phải; (4) Mũi và miệng**. Trang 14–15 quy định LBP8,2, 59 bin uniform không bất biến quay, L1 riêng từng vùng và ghép thành 236 chiều. Lần này chỉ chuẩn bị vùng; không thực hiện các phép trích xuất đó.

PDF **không cho danh sách vertex, polygon, margin, clipping/rasterization, min-area hoặc quy tắc xử lý occlusion/chồng lấn**. Tên “trái/phải” chưa xác định hệ quy chiếu. Không gán các quyết định dưới đây thành quy định nguyên văn của PDF. Trạng thái hợp đồng: **`{spec['status']}`**.

## Landmark đã kiểm chứng và endpoint còn mở

Mapping A hiện có đủ 68 index duy nhất; từng index và nhóm được đối chiếu source, CSV audit, hình PDF và contour MediaPipe đã lưu. **Membership contour** là bằng chứng cấu trúc, không phải nhãn giải phẫu chuẩn. [A_MAPPING_FINAL_REVIEW.md](A_MAPPING_FINAL_REVIEW.md) giữ kết luận: hai đầu hàm và topology mũi khác hình minh họa trên cùng CFD00001; canonical MP ID thay thế và A2 endpoints chưa được xác minh.

MP1=A30, MP4=A33 giữ nguyên; không dùng một điểm khác để “sửa” hai index này. MP129=A31 và MP358=A35 vẫn là endpoint cánh/bên mũi proxy UNVERIFIED, không có trong sparse NOSE. Chúng vẫn được ghi rõ trong **đề xuất**, không được nâng thành alare canonical. MP1/MP4 được đánh đỏ trên overlay để giữ khả năng đối chiếu.

68 điểm A không có đường trán phía trên. Đề xuất dùng thêm **15 MP478 phụ trợ** trên upper FACE_OVAL: `{spec['auxiliary_upper_face_oval']}`. Membership của cả 15 điểm được kiểm với topology đã hash; chúng không được thêm vào A150 hoặc thay một index A nào. PDF chưa quy định rõ C1 có thể truy cập landmark ngoài 68 điểm hay không; việc dùng MP478 phụ trợ phải được chốt trước extractor. FACE_OVAL không tự chứng minh hairline/đỉnh trán; lựa chọn biên trên là IMPLEMENTATION DETAIL cần chốt.

## Hệ tọa độ và đỉnh dẫn xuất

Ảnh 256×256 không crop, align lại, warp hoặc nội suy để cải thiện ROI. P là pixel landmark float32 đã lưu, đưa sang float64 khi dựng polygon. L/R là các tâm float32 mean6 đã mô tả ở [EYE_METADATA_COMPLETION.md](EYE_METADATA_COMPLETION.md), promote sang float64; `D=norm64(R−L)`, `u=(R−L)/D`, `v=(−u_y,u_x)`. Y ảnh hướng xuống; yêu cầu u_x>0 và v_y>0, không tự swap mắt.

Mỗi hàng vertex dùng:

```text
V = P[MP_index] + D * (α*u + β*v)
```

Các hệ số **0.05, 0.08, 0.06** là margin đề xuất theo IPD, không được PDF chỉ định. D của khung ROI là float64; không thay eye_distance float32 của Bộ A. Số A là **index 0-based của 68 điểm hiện hành**; số MP là **index 0-based của 478 điểm**. Không nhầm MP21 với A21, hoặc cộng một rồi coi đó là một mapping PDF đã xác nhận.

## Toàn bộ đỉnh và thứ tự nối

Nối cạnh thẳng theo thứ tự 0→1→…→n−1→0; giữ nguyên thứ tự ghi, không convex-hull, spline hoặc sắp xếp đỉnh tự động. Ý nghĩa giải phẫu của mọi đường biên bên dưới còn UNVERIFIED; membership contour có thể đã xác minh nhưng không chứng nhận polygon.

{chr(10).join(polygon_sections)}

Định nghĩa máy đọc được: [c1_roi_contract_proposal_v0.json](eye_c1_evidence/c1_roi_contract_proposal_v0.json). Tọa độ thực tế **488 đỉnh =61×8 ảnh** kèm source index và offset: [roi_preview_vertices.csv](eye_c1_evidence/roi_preview_vertices.csv).

## Raster, chồng lấn, vùng thiếu và biên LBP

1. Dựng đỉnh ở float64, kiểm hữu hạn, D≥1e-6 pixel, diện tích contour≥1e-6 pixel², cạnh dài≥1e-9 pixel và không tự giao/chạm cạnh không kề; tolerance kiểm segment là 1e-9 như code audit. Đây là guard số học đề xuất, không phải ngưỡng chất lượng từ PDF. Lỗi thì vùng đó invalid; không sửa đỉnh để tạo một hình đẹp hơn.
2. Preview dùng contour float32, `cv2.pointPolygonTest >=0` tại tâm pixel nguyên (x,y), kể cả boundary. Chỉ đánh giá trong khung ảnh; không clamp từng đỉnh, không extrapolate mô ngoài ảnh. Preview ghi NumPy/OpenCV version để tái lập.
3. Raw polygons có thể chồng nhau. Để tôn trọng bốn vùng độc lập, đề xuất gán pixel theo ưu tiên **trán+mày → mũi+miệng → má trái theo ảnh → má phải theo ảnh**. Vùng sau trừ các pixel đã được gán; output masks không chồng lấn. Đây là lựa chọn cần chốt, không phải thứ tự ghép histogram.
4. Thứ tự ghép tương lai dự kiến giữ danh sách PDF: **trán+mày → má trái → má phải → mũi+miệng**. Quan hệ trái/phải giải phẫu với theo ảnh phải được tác giả chốt trước khi công nhận thứ tự đó.
5. Pixel không thuộc polygon nào để nguyên không gán. Không cố phủ toàn bộ mặt; số pixel “uncovered” trong JSON tính trên cả ảnh 256², gồm nền/tóc và các vùng mặt không chọn.
6. Thiếu landmark, sai frame, polygon tự giao/degenerate, hết pixel sau clipping/overlap là vùng thiếu. Đề xuất cho extractor tương lai: thiếu một trong bốn vùng bắt buộc thì `missing_C1`, không vector 236 và không zero-fill. Chưa đặt ngưỡng min-pixel mang ý nghĩa chất lượng, chưa triển khai extractor.
7. Với R=2, đề xuất tương lai chỉ nhận tâm LBP khi toàn bộ support nằm trong vùng được gán và trong ảnh. PDF chưa chốt cách xử lý support ở biên hoặc nội suy mẫu tròn; quy tắc này **chưa được phê duyệt và chưa được thực thi để tính LBP**. Không suy ra 59 bin hoặc histogram từ preview masks.
8. Polygon không phân biệt da, tóc, kính, vải hoặc tay. Không tự giao với mask skin Bộ B vì PDF C1 chưa quy định thao tác đó và vùng mày/môi có thể bị loại nhầm. Cần protocol occlusion có thẩm quyền, không chọn theo Top-5.

## Overlay và quan sát thực tế

[Contact sheet tám ảnh toàn khung](eye_c1_evidence/overlays/roi_contact_sheet.png). Đã xem CFD00001/CFD00069, HF00001 và năm trường hợp HF cần review. Tất cả **32 polygon trên tám ảnh** qua kiểm tra hình học; mask sau gán ưu tiên không overlap. Đây không phải kết luận về toàn bộ 1438 ROI hoặc chuẩn giải phẫu.

{table(['Ảnh','Pixel sau gán theo vùng','Overlap raw theo cặp','Quan sát/giới hạn'],preview_rows)}

Ảnh có nhãn vertex A/MP và dấu `*` cho offset: [CFD00001](eye_c1_evidence/overlays/cfd_final_00001_c1_roi_vertex_labels.png), [HF00001](eye_c1_evidence/overlays/hf_merged_00001_c1_roi_vertex_labels.png). Ảnh kết hợp: [CFD00001](eye_c1_evidence/overlays/cfd_final_00001_c1_roi_proposal.png), [HF00722 có tay](eye_c1_evidence/overlays/hf_merged_00722_c1_roi_proposal.png). Các ảnh khác nằm cùng thư mục. [roi_preview_validation.json](eye_c1_evidence/roi_preview_validation.json) lưu số pixel, version raster và trạng thái; **semantic_anatomy_verified=false**.

## Các quyết định phải chốt trước khi dùng C1

- Tác giả xác nhận hình PDF là ràng buộc endpoint hay minh họa; cung cấp annotation/canonical mapping cho vùng liên quan, đặc biệt trán, góc hàm, cánh mũi và khóe môi.
- Chốt trái/phải, 15 điểm phụ trợ, vertex/margin, coverage cả vùng lông mày, quy tắc overlap và phần mô bị bỏ lại. Không chọn bằng relevance/Top-5.
- Chốt xử lý tóc/tay/kính/vải, vùng thiếu và min-valid-support; review corpus theo protocol định trước. Dataset vi phạm không được tự “sửa” bằng ROI.
- Đóng băng contract đã duyệt với hash và đánh giá annotation độc lập trước khi viết extractor C1. Đề xuất v0.1 này **chưa được chấp nhận làm ROI giải phẫu chính thức**.
''')

    invariants=[['Metadata mới',f"{s['measured_images']} ảnh; {s['unmeasurable_images']} không đo được",'Đã hoàn thành coverage đo lại'],
        ['Landmark input','1438×478×2 float32, hash manifest audit gốc khớp','Không chạy lại detector'],
        ['CSDL nguồn','Hash trước/sau không đổi; 16 bảng được đối chiếu','Bản mới chỉ thêm eye metadata/extension'],
        ['Round-trip SQLite','1438 tọa độ và row hash khớp exact','Không dùng tolerance để che mất giá trị'],
        ['Backup/restore','SQL dump và toàn bộ view mắt khớp','Đạt integrity/FK'],
        ['A/B vectors, stats, calibration','Mọi bảng gốc tương ứng và file artifact giữ nguyên','Không fit lại hoặc đổi thuật toán'],
        ['A+B ranking','15 mode/case; toàn bộ rank và khoảng cách khớp, Top-5 khớp output v2','Không chỉ so ảnh đứng đầu'],
        ['ROI C1','4 polygon, 8 ảnh/32 vùng; chỉ kiểm hình học','Đề xuất chưa được phê duyệt giải phẫu'],
        ['C1/C2','0 version/vector mới, không extractor LBP/HOG','Chưa triển khai'],
        ['Toàn hệ thống','Mapping/dataset/metadata lịch sử còn giới hạn','Không chứng nhận 100%']]
    save('C1_PRE_IMPLEMENTATION_REVIEW.md',f'''# Kiểm tra trước triển khai C1

{intro}

**Metadata mắt đo lại đã đủ 1438 ảnh. Hợp đồng ROI C1 mới ở trạng thái đề xuất; chưa đủ cơ sở công nhận ROI giải phẫu chính thức hoặc toàn hệ thống tuân thủ 100%.**

{table(['Phạm vi','Bằng chứng','Kết luận'],invariants)}

## Yêu cầu rõ của PDF và khoảng trống đặc tả

§1.3 yêu cầu lưu vị trí mắt; đợt này đã lưu phép đo có provenance cho mọi ảnh, nhưng không khôi phục log alignment gốc chưa tồn tại. §2.2 quy định A150 và chuẩn hóa landmark; source và indices không đổi. §2.4 quy định bốn vùng theo landmark, LBP P=8/R=2, threshold s(x)=1 với x≥0, 59 bin uniform không bất biến quay, L1 từng vùng và ghép 236 chiều.

PDF chưa chốt polygon, hệ quy chiếu trái/phải, grayscale conversion, vị trí bắt đầu/chiều đi bit, nội suy mẫu tròn ở vị trí không nguyên, số thứ tự bin uniform, ROI support ở biên, ngưỡng vùng thiếu hoặc policy occlusion. Phải phân biệt các lựa chọn đó với điều khoản rõ; không triển khai biến thể rotation-invariant 10 bin rồi gọi là 59 bin.

## Những việc đã được chứng minh

Archive toàn kho có sẵn và hash xác thực; ảnh được join bằng tên/ID với metadata/hash, không gán theo vị trí row. Mỗi tâm mới là mean6 float32 đúng kiểu tính của code A hiện hành, kèm coordinate_system/model asset version/row hash/provenance và role audit_remeasurement. Ba dòng scalar64 trước được giữ nguyên; tổng 1441 dòng version không phải 1441 ảnh.

CSDL mới [portrait_ab_v2_eye_metadata_v1.sqlite3](../../database/data/portrait_ab_v2_eye_metadata_v1.sqlite3) được tạo từ backup nguồn và migration cộng thêm. Bản nguồn và các backup cũ không đổi. New metadata SELECT qua EyeMetadataAuditV1 đủ 1438 ID; không có giá trị suy đoán hoặc placeholder cho lỗi.

Các bảng FeatureVectors, FeatureVersions, NormalizationStages, Calibrations/Components/Candidates/Pairs/PairDistances và các run/result/query vector cũ giữ nguyên. Xếp hạng được kiểm đầy đủ cho ba query CFD, HF00209 thiếu B và query mới đã lưu: **15 mode/case**. Với new_query, verifier đọc QueryVectors đã lưu từ CSDL, không chạy lại worker hoặc MediaPipe. Không INSERT thêm retrieval run chỉ để kiểm tra.

10 tests mới và 19 regression tests v2 đạt. Backup/restore mới kiểm toàn bộ SQL dump, 1438 metadata mắt, integrity và FK. Hash toàn bộ **{s['protected_files_checked']} file đã đóng băng** được so trước/sau, không đổi, gồm ba file SQLite gốc và artifact A/B v1/v2. [verification_summary.json](eye_c1_evidence/verification_summary.json), [ranking_preservation.json](eye_c1_evidence/ranking_preservation.json), [final_scope.json](eye_c1_evidence/final_scope.json).

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
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/eye_c1_tools/prepare_eye_roi.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m unittest discover -s docs/audits/eye_c1_tools -p test_eye_roi.py -v
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/eye_c1_tools/verify_eye_roi.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database search --db database/data/portrait_ab_v2_eye_metadata_v1.sqlite3 --image cfd_final_00001.png --no-save
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/eye_c1_tools/write_eye_roi_reviews.py
```

Lệnh chuẩn bị tạo CSDL mới một lần và từ chối tên đã có; verifier cũng từ chối overwrite snapshot. Preview được cập nhật riêng bằng hàm audit prepare_roi_preview khi rà quy tắc hình học; không tạo lại CSDL hay chạy detector. Tra cứu từ CSDL mới dùng `--no-save` để giữ snapshot không đổi.
''')

    baseline=read_json(E/'baseline_before.json')
    changed=[p for p,h in baseline.items() if task.db.digest(p)!=h]
    assert not changed,changed
    reports=['EYE_METADATA_COMPLETION.md','C1_ANATOMICAL_ROI_SPEC.md','C1_PRE_IMPLEMENTATION_REVIEW.md']
    write_json(E/'final_scope.json',dict(status='PASS',protected_files_checked=len(baseline),changed_existing_files=changed,
        reports=reports,source_database_unchanged=True,new_eye_metadata_images=1438,unmeasurable=0,
        new_database_sha256=task.db.digest(task.NEW_DB),a_b_vectors_unchanged=True,calibration_unchanged=True,
        ranking_unchanged=True,mapping_indices_unchanged=True,dataset_unchanged=True,pdf_unchanged=True,
        mediapipe_rerun=False,c1_c2_extractors_or_vectors_created=False,
        original_alignment_verified=False,roi_contract_approved=False,full_system_compliance=False))
    broken=[]
    for name in reports:
        path=DOC/name
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not target.startswith(('http://','https://')) and not (path.parent/target).is_file():
                broken.append([name,target])
    assert not broken,broken
    new_files=[DOC/name for name in reports]+[task.NEW_DB,
        ROOT/'database/backups/portrait_ab_v2_eye_metadata_v1.backup.sqlite3',
        ROOT/'database/restored/portrait_ab_v2_eye_metadata_v1.sqlite3']
    for folder in [E,task.TOOLS]:
        new_files += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                      and p!=E/'created_files_manifest.json']
    write_json(E/'created_files_manifest.json',dict(self_excluded=True,files=[
        dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=task.db.digest(p)) for p in sorted(new_files)]))
    print(task.db.json_text(dict(status='PASS',reports=reports,new_files=len(new_files),
        protected_files_unchanged=len(baseline),measured_images=1438,unmeasurable=0,broken_links=broken,
        roi_approved=False,c1_c2_created=False)))


if __name__=='__main__':
    main()
