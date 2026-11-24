"""Finalize new ROI remediation evidence; no feature extraction or activation."""
from collections import defaultdict
import subprocess

import numpy as np

import audit_remediation as audit


def text_new(path, text):
    with path.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)


def numbers(rows, field):
    values = np.array([float(r[field]) for r in rows])
    return f'{values.min():.3f} / {np.median(values):.3f} / {values.max():.3f}'


OBSERVATIONS = {
    'cfd_final_00001': 'Đường dưới ứng viên bao quanh proxy mày rõ hơn v0.2. Upper FACE_OVAL nằm dưới đường chân tóc quan sát được, không phải annotation toàn trán. Hai má và mũi-miệng có vẻ hợp vùng trên mẫu này; endpoint vẫn chưa canonical.',
    'cfd_final_00069': 'Biểu cảm miệng mở làm polygon mũi-miệng bao cả phần răng/miệng mở. Không đổi polygon để làm retrieval đẹp hơn; đây không chứng minh ổn định giải phẫu khi biểu cảm.',
    'cfd_final_00112': 'Tóc đi vào vùng trên trán; đường bao hình học không tự phân biệt tóc và da. Không gắn nhãn anatomical-valid từ geometry.',
    'cfd_final_00268': 'Ví dụ v0.2 thiếu coverage proxy nhiều nhất; native lower contour bao trọn proxy pixel trong ứng viên. Mô thật, độ đủ của trán và endpoint má vẫn chưa annotation.',
    'hf_merged_00001': 'Mày nhìn thấy, đường dưới native phù hợp tổng thể vùng mày trên ảnh mẫu. Các cạnh má/mũi-miệng dựng được; chưa xác minh tất cả endpoint theo PDF.',
    'hf_merged_00055': 'Tóc mái che một phần trán/mắt theo phía người xem trái. MP300 nằm ngoài candidate 0.403582px dù proxy raster pixel phủ100%; minh họa khác biệt continuous point với integer raster.',
    'hf_merged_00069': 'V0.2 có cạnh mày cắt upper FACE_OVAL phía phải ảnh; ứng viên không còn cắt trên cùng landmarks. Quan sát này xác nhận hình học, không tạo ground truth giải phẫu.',
    'hf_merged_00198': 'Kính nằm ngang vùng mắt và một phần biên gần má/thái dương. V0.3 còn giao ở phía trái ảnh. Ứng viên không giao nhưng MP70 ngoài đường oval proxy; không kết luận mô mày/trán đã đủ.',
    'hf_merged_00209': 'Khăn che tóc và sát biên trán. B thiếu tóc không tự làm thiếu ROI C1; B hair=0 cũng không chứng minh mọi pixel forehead là da. Khăn/occlusion vẫn cần annotation riêng.',
    'hf_merged_00267': 'V0.2 tự giao phía phải ảnh. Ứng viên hết giao nhưng còn1 pixel proxy mày và MP300 ngoài boundary; không coi gần100% là đủ chứng cứ giải phẫu.',
    'hf_merged_00311': 'Tóc mái che hầu hết vùng trán và lông mày. Hair mask đã lưu phủ93.364% forehead ứng viên là proxy mô hình, phù hợp cảnh báo nhìn thấy tóc nhưng không phải nhãn ground truth.',
    'hf_merged_00333': 'Mặt phụ nhìn thấy tại mép ảnh. Thay forehead không giải quyết vi phạm dataset; giữ nguyên ảnh và cờ review.',
    'hf_merged_00463': 'V0.2 tự giao phía phải ảnh. Ứng viên đơn giản nhưng MP300 vẫn ngoài0.099359px, pixel proxy có thể vẫn phủ100%; không điều chỉnh tiếp để ép số liệu.',
    'hf_merged_00561': 'Mặt phụ nhìn thấy ở mép trái, tóc phủ phần trán. Giữ nguyên hai vấn đề dataset/occlusion dù polygon mới không tự giao.',
    'hf_merged_00694': 'Khăn và kính nhìn thấy, ở gần các biên ROI. Hair proxy0 không phải bằng chứng không vải/kính. Chưa đủ cơ sở gắn nhãn sai tiêu chí dataset chỉ từ phụ kiện.',
    'hf_merged_00722': 'Tay/ngón chồng vùng miệng và phần má. Polygon hình học vẫn chứa vùng bị che; không crop/inpaint, giao skin mask hoặc loại ảnh để hợp thức hóa.',
}


def main():
    out = audit.OUT
    if (out / 'created_files_manifest.json').exists():
        raise FileExistsError('Final remediation manifest exists')
    baseline = audit.check_sources()
    summary = audit.read_json(out / 'summary.json')
    verified = audit.read_json(out / 'verification.json')
    assert verified['status'] == 'PASS'
    candidate = audit.read_json(out / 'candidate_contract_v0_4.json')
    metrics = audit.read_csv(out / 'roi_metrics.csv')
    pairs = audit.read_csv(out / 'overlap_metrics.csv')
    endpoints = audit.read_csv(out / 'endpoint_contract_review.csv')
    cases = audit.read_json(out / 'four_cases_intersections.json')
    outside = audit.read_csv(out / 'native_brow_outside_points.csv')
    selection = audit.read_json(out / 'contact_sheet_selection.json')
    selected_ids = {r['image_id'] for r in selection['images']} | {r['image_id'] for r in outside}
    assert selected_ids == set(OBSERVATIONS)
    audit.write_json(out / 'visual_observations.json', dict(schema_id='C1_LIMITED_ANATOMICAL_OBSERVATIONS_v0.4.0',
        date_local='2026-11-24', timezone='Asia/Saigon', images_visually_reviewed=len(selected_ids),
        images_not_manually_anatomically_reviewed=1438 - len(selected_ids),
        method='Direct inspection of original pixels enlarged with pinned landmark overlays; no anatomical segmentation annotations',
        material_viewed=['contact_sheets/overview_01.png', 'contact_sheets/overview_02.png', 'contact_sheets/overview_03.png',
            'contact_sheets/overview_04.png', 'contact_sheets/native_brow_fractional_exceptions.png',
            'contact_sheets/cfd_final_00001_all_regions_A_MP.png', 'contact_sheets/hf_merged_00001_all_regions_A_MP.png',
            'docs/audits/evidence/pdf_page8_X31.png'],
        anatomy_status='ANATOMY_PROVISIONAL', observations=[dict(image_id=k, observation=v, anatomical_clearance='UNVERIFIED') for k, v in OBSERVATIONS.items()]))
    map_metrics = {(r['variant'], r['image_id'], r['region']): r for r in metrics}
    pixel_exceptions = [r for r in metrics if r['variant'] == 'candidate_v0_4' and r['region'] == 'forehead_brow' and float(r['brow_proxy_coverage']) < 1]
    audit.write_json(out / 'remaining_proxy_discrepancies.json', dict(anatomy_status='ANATOMY_PROVISIONAL',
        integer_proxy_pixel_exceptions=[dict(image_id=r['image_id'], proxy_pixels=int(r['brow_proxy_pixels']),
             covered_pixels=int(r['brow_proxy_covered_pixels']), missing_pixels=int(r['brow_proxy_pixels']) - int(r['brow_proxy_covered_pixels']),
             combined_coverage=float(r['brow_proxy_coverage']), viewer_left_coverage=float(r['brow_left_coverage']),
             viewer_right_coverage=float(r['brow_right_coverage'])) for r in pixel_exceptions],
        fractional_landmark_exceptions=outside, no_rule_or_parameter_change_to_hide_exceptions=True))
    pair_map = {(r['variant'], r['image_id'], r['region_a'], r['region_b']): int(r['overlap_pixels']) for r in pairs}
    overlap_changed = sum(value != pair_map[('v0_2', identity, a, b)] for (variant, identity, a, b), value in pair_map.items() if variant == 'candidate_v0_4')
    assert overlap_changed == 0

    comparison = '| Phiên bản | ROI valid/5752 | Tự giao | Support<64 | Proxy mày min/median/max | Proxy pixel đủ |\n|---|---:|---:|---:|---|---:|\n'
    for tag, r in summary['variants'].items():
        comparison += f"| {tag} | {r['valid_geometry']} | {r['self_intersections']} | {r['insufficient_support']} | {100*r['brow_proxy_coverage_min']:.6f}% / {100*r['brow_proxy_coverage_median']:.6f}% / {100*r['brow_proxy_coverage_max']:.6f}% | {r['full_proxy_coverage_images']}/1438 |\n"
    cross_table = '| Ảnh | Cạnh upper FACE_OVAL | Cạnh mày v0.2 (offset+0.05D·v) | Giao điểm (x,y) |\n|---|---|---|---|\n'
    counter = '| Ảnh | v0.2 | Upper-brow v0.2 bỏ offset: chỉ test4 case | v0.3 | v0.4 |\n|---|---:|---:|---:|---:|\n'
    for case in cases:
        c = case['variants']['v0_2']['crossings'][0]
        a, b = c['endpoints']['edge_a'], c['endpoints']['edge_b']
        upper = ' → '.join('MP' + str(r['mediapipe_index']) for r in a)
        brow = ' → '.join('A' + str(r['index']) + '/MP' + str(r['mediapipe_index']) for r in b)
        x, y = c['intersection_xy']
        cross_table += f"| {case['image_id']} | {upper} (vertex{c['edge_a']}) | {brow} (vertex{c['edge_b']}) | {x:.9f}, {y:.9f} |\n"
        counter += f"| {case['image_id']} | {len(c['endpoints'])//2} | {len(case['diagnostic_counterfactual_A68_upper_brow_no_offset'])} | {len(case['variants']['v0_3']['crossings'])} | {len(case['variants']['candidate_v0_4']['crossings'])} |\n"
    regionstats = '| Variant / vùng | Area px² min/median/max | Raw pixels min/median/max | Support min/median/max |\n|---|---|---|---|\n'
    for tag in ['v0_2', 'v0_3', 'candidate_v0_4']:
        for region in audit.REGIONS:
            group = [r for r in metrics if r['variant'] == tag and r['region'] == region]
            regionstats += f"| {tag} / {region} | {numbers(group,'continuous_area_px2')} | {numbers(group,'raw_mask_pixels')} | {numbers(group,'eligible_centres')} |\n"
    changes = [r for r in metrics if r['variant'] == 'candidate_v0_4' and r['region'] == 'forehead_brow']
    overlap_table = '| Cặp vùng (candidate; bằng v0.2 từng ảnh) | Pixel min/median/max |\n|---|---|\n'
    for a, b in audit.itertools.combinations(audit.REGIONS, 2):
        group = [r for r in pairs if r['variant'] == 'candidate_v0_4' and r['region_a'] == a and r['region_b'] == b]
        overlap_table += f"| {a} / {b} | {numbers(group,'overlap_pixels')} |\n"
    outside_table = '| Ảnh | Native point ngoài candidate | Signed distance px | Pixel proxy thiếu |\n|---|---|---:|---:|\n'
    for row in outside:
        metric = map_metrics[('candidate_v0_4', row['image_id'], 'forehead_brow')]
        missed = int(metric['brow_proxy_pixels']) - int(metric['brow_proxy_covered_pixels'])
        outside_table += f"| {row['image_id']} | MP{row['mediapipe_index']} | {float(row['signed_distance_to_candidate_boundary']):.9f} | {missed} |\n"

    common = f"""Ngày kiểm tra: **24/11/2026**, Asia/Saigon. Trạng thái ứng viên:
**GEOMETRY_VALIDATED — ANATOMY_PROVISIONAL**. `active=false`; chưa sẵn sàng trích xuất C1 chính thức.

Nguồn chuẩn cao nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã kiểm lại trực tiếp.
Đã đọc toàn bộ §2.2/§2.4 bằng pypdf có sẵn ở Python hệ thống và xem hình minh họa68 điểm PDF trang8;
bản trích mới tại [pdf_sections_2_2_2_4.txt](../../outputs/C1_lbp/roi_remediation_v0_4/pdf_sections_2_2_2_4.txt).
Các script geometry dùng `.venv311`, không cài thư viện, không chạy lại MediaPipe.
Đã đọc các contract/spec, audit mapping/full-dataset và hai báo cáo trial100; chúng nằm trong baseline bất biến.

Contract active v0.2 content SHA `{audit.ROI_PIN}` và LBP spec `{audit.SPEC_PIN}` khớp canonical JSON;
proposal v0.3 file SHA `{audit.digest(audit.OLD / 'forehead_amendment_proposal_v0_3.json')}`.
Ứng viên mới **C1_ROI_ANATOMICAL_CANDIDATE_v0.4.0** content SHA
`{candidate['content_sha256']}`, file SHA `{audit.digest(out / 'candidate_contract_v0_4.json')}`.
Source links/hash, thứ tự25/12/12/12 đỉnh và offsets nằm trong JSON; không sửa/đổi contract active.
"""
    report = '# C1 ROI anatomical remediation — kết quả có giới hạn\n\n' + common + f"""
## Kết quả toàn kho

Kiểm **1438×4=5752 ROI cho từng phiên bản**, tổng17.256 hàng đo.
Không chỉ lấy bốn ảnh lỗi hoặc contact sheet để kết luận toàn kho.

{comparison}
Candidate hết tự giao, không có out-of-image vertex hoặc ROI thiếu support, nhưng **1438/1438 ảnh vẫn thiếu
annotation giải phẫu độc lập**. Coverage bảng là polygon proxy của mô hình, không phải độ phủ mô mày thật.
Full-dataset CSV/JSON và contact sheets nằm riêng tại `outputs/C1_lbp/roi_remediation_v0_4/`.

## Nguyên nhân chính xác bốn lỗi v0.2

{cross_table}
Index vertex/A68 dùng0-based. Đã xác minh giao bên trong hai segment bằng determinant và linear solve độc lập,
residual<1e-10. Tọa độ các endpoint, parameters t/u, frame mắt và source landmark row hash nằm trong
[four_cases_intersections.json](../../outputs/C1_lbp/roi_remediation_v0_4/four_cases_intersections.json).
Hash ảnh gốc được nối theo image_id từ catalog đã xác thực, ghi trong diagnostic,
contact_sheet_selection.json và baseline; không suy đoán tọa độ hoặc nguồn ảnh.

Cả bốn giao đều là **cạnh nội bộ upper FACE_OVAL với cạnh nội bộ mày**; không giao nào dùng cạnh đóng24→0.
Vì vậy không quy hết lỗi cho cạnh đóng polygon. Upper arc15 điểm có14 cạnh native
đúng thứ tự, hai đường mày có thứ tự vùng hợp lý, nhưng kết hợp endpoint thưa + offset chung không bảo đảm
hai contour không cắt ở thái dương. Không có bằng chứng để sửa detector hoặc mapping A.

### Tách endpoint/offset/đường nối

{counter}
Các số là số proper intersections, không phải điểm chất lượng retrieval. Counterfactual bỏ offset của đường
upper-brow cũ chỉ phân tích bốn ảnh: HF00069 hết giao, HF00198 vẫn giao, HF00267/HF00463 tăng hai giao.
Do đó chỉ xóa offset0.05 trên contour A cũ không phải cách sửa chung và không khắc phục proxy undercoverage.
Không kích hoạt counterfactual, không dùng hull/xóa đỉnh/reorder/clip vào oval để che giao.

V0.3 dùng lower-brow native +0.02D·v: hết ba lỗi nhưng HF00198 còn giao
**MP127→MP162 (0→1) với MP53+offset→MP46+offset (23→24)** tại
**(62.568903833,81.214931423)**. Native MP46=(62.339294434,79.981666565), sau shift thành
(62.312974548,81.522940826); displacement=(-0.026319885,+1.541274261)px.
Signed cross với MP127→162 đổi **+0.807109411→−5.660792207**: downshift theo frame mắt không phải
inward normal của cạnh oval nghiêng. Đây là bằng chứng số học cho crossing do quy tắc offset v0.3 ở case này,
không khẳng định mọi landmark là ground truth hoặc coi kính là nguyên nhân detector khi thiếu nhãn chuẩn.

## Ứng viên và căn cứ thay đổi

V0.4 giữ nguyên15 upper FACE_OVAL và25 vertex count; dùng lower chain
`MP276,283,282,295,285,55,65,52,53,46` **không offset**, thay đường mày A26…A17+0.05D của v0.2.
Không xóa đỉnh tùy ý, không đổi toàn bộ thứ tự để làm polygon hợp lệ. Bốn cạnh mỗi nửa lower chain có
membership EYEBROW native; bridge285→55 và hai đường nối thái dương vẫn là quy ước polygon chưa được
PDF/annotation chốt. Zero offset loại padding chưa có căn cứ giải phẫu; không phải giá trị được tìm bằng
quét tham số để đạt geometry hoặc Top-5. [Decision trước census](../../outputs/C1_lbp/roi_remediation_v0_4/decision_before_census.json)
đóng băng lựa chọn trước khi xem các metric ứng viên toàn kho.

Ba vùng má trái/má phải/mũi-miệng giữ nguyên cả definitions, coordinates, mask bytes, area và support;
mapping A và vector không đổi. Giữ frame viewer/code left-right, mean6 float32 mắt rồi float64 D/u/v,
pixel rule pointPolygonTest>=0 với contour float32, clipping chỉ khung ảnh; raw overlap độc lập.
Không đưa candidate vào Context/extractor/gallery trial100. Các rule LBP P8,R2,59 bins,L1,Chi-square0.5 và
epsilon/gray/bilinear/support21 trong spec cũ giữ nguyên; nhiệm vụ này không gọi extractor.

Tài liệu chính thức [FaceLandmarksConnections](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py)
xác nhận các cạnh mày/oval; [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
mô tả output478 landmarks. Chỉ dùng để xác nhận topology mô hình, không thay PDF hoặc chứng nhận mô thật.
Đối chiếu chính xác khi tính toán dùng native_mediapipe_topology.json đã hash, không lệ thuộc master thay đổi.

## Coverage lông mày và giới hạn giải phẫu

Proxy mỗi mày là polygon đóng từ5 điểm upper+5 điểm lower; cạnh đóng hai đầu do audit quy ước, không phải
annotation pixel lông mày. V0.2 min/median/max44.294606%/55.547956%/67.137809%.
V0.3/v0.4 min99.635922%, median/max100%; cả hai phủ đủ integer proxy ở1436 ảnh.
HF00198 phủ821/824 pixel (thiếu3 phía trái theo ảnh; riêng mày trái99.006623%), HF00267 phủ737/738
(thiếu1 phía phải; riêng mày phải99.638989%). Giữ nguyên số liệu, không chỉnh contract để ép100%.

{outside_table}
Ngoài2 pixel-mask exceptions còn có4 ảnh với một native landmark ngoài candidate (28.760 điểm đã kiểm).
HF00055/HF00463 vẫn có proxy integer coverage100% vì phần thiếu là nhỏ ở tọa độ phân số, không chứa tâm pixel
nguyên bị loại. [CSV](../../outputs/C1_lbp/roi_remediation_v0_4/native_brow_outside_points.csv) và
[ảnh exceptions](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/native_brow_fractional_exceptions.png).
Geometry-valid, integer proxy coverage và continuous point membership là ba phép đo khác nhau;
không phép nào xác nhận anatomical-valid. Native upper oval cũng không phải đường chân tóc/trán có annotation.

## Diện tích, pixels, support và thay đổi từng ảnh

{regionstats}
Stat v0.2/v0.3 gồm cả mask invalid với vai trò chẩn đoán; không dùng area tự giao làm feature.
Tất cả1438 ảnh thay pixel **chỉ ở forehead_brow**. Added pixels min/median/max={numbers(changes,'pixels_added_vs_v0_2')};
removed={numbers(changes,'pixels_removed_vs_v0_2')}. Diện tích/pixel từng ROI, thay đổi từng ảnh, hair proxy và
reason nằm trong [roi_metrics.csv](../../outputs/C1_lbp/roi_remediation_v0_4/roi_metrics.csv),
[image_metrics.csv](../../outputs/C1_lbp/roi_remediation_v0_4/image_metrics.csv),
[175436 vertex rows cho v0.3/v0.4](../../outputs/C1_lbp/roi_remediation_v0_4/candidate_vertices.csv).

{overlap_table}
Không cặp nào thay số overlap so với v0.2 trên bất kỳ ảnh nào; unique overlap91…208px, max memberships2.
Independent inclusion-exclusion xác minh raw sum−pair sum=union. Không ownership subtraction.

## Occlusion và dataset

Đã xem trực tiếp **16 ảnh khác nhau**:15 case sheets gồm CFD/HF, bốn lỗi và các extrema định trước,
cộng HF00055 từ continuous-node exceptions; hai overlay lớn có A68/MP labels cho đủ4 vùng.
Đây là review mẫu, không phải manual ground truth cho1438 ảnh.
[Quan sát từng ảnh](../../outputs/C1_lbp/roi_remediation_v0_4/visual_observations.json),
[bốn trang trước/sau](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/overview_01.png).
HF00311 tóc mái phủ trán, saved B hair proxy93.364070% forehead candidate; HF00055/CFD00112 cũng có tóc
đi vào ROI trên hình. HF00198/HF00694 có kính, HF00209/HF00694 có khăn.
B hair mask=0 ở hai ảnh khăn không phải clearance vải/kính/skin; không tự dùng proxy hair như nhãn mô thật.
HF00333/HF00561 vẫn có mặt phụ; HF00722 tay che miệng/má vẫn nằm trong ROI không sửa.
Các vi phạm dataset đã xác nhận giữ nguyên và tách khỏi geometric validity; không suy nhãn danh tính/tuổi/giới.

## Đối chiếu PDF và điều cần chốt

PDF §2.4 cho bốn tên vùng và landmark-based partition, không liệt kê MP endpoints, upper hairline,
margin, polygon graph, frame trái/phải, overlap hoặc occlusion masks. Vì vậy chứng minh rõ **undercoverage
proxy của v0.2**, nhưng chưa đủ tuyên bố mức undercoverage mô thật theo một ground truth không tồn tại.
Các khác biệt vị trí hàm/mũi của A với hình minh họa PDF trang8 (đặc biệt MP1/MP4) vẫn là findings từ
A_MAPPING_FINAL_REVIEW, không tự coi chúng là canonical mapping thay thế hoặc tự sửa A.
Endpoint vùng má/mũi-miệng và độ đầy đủ vùng trán cần annotation/xác nhận có thẩm quyền.
Chi tiết endpoint/phân loại ở [C1_ANATOMICAL_VALIDATION.md](C1_ANATOMICAL_VALIDATION.md).

Có thể xử lý bằng quy ước triển khai có version: raster/support/overlap, dùng lower native chain và loại
downshift không được chứng minh, identity join/provenance và guard missing. Các quy ước không cấp chứng nhận
giải phẫu. Trước C1 chính thức cần: tác giả chốt frame và ý nghĩa4 vùng; annotation upper/lower forehead/mày,
hai má/mũi-miệng và occlusion; adjudicate4 continuous-node exceptions; review dataset vi phạm; thẩm định lại
contract và toàn kho độc lập, rồi nghiệm thu version mới nếu đủ chứng cứ. Không tự thực hiện bước kích hoạt.

## Kiểm chứng và bảo toàn

8 tests geometry đạt, census độc lập kiểm2876 forehead polygons v0.3/v0.4 bằng determinant CSV,
đủ17.256 ROI metric rows,25.884 overlap rows. [verification.json](../../outputs/C1_lbp/roi_remediation_v0_4/verification.json),
[tests.log](../../outputs/C1_lbp/roi_remediation_v0_4/tests.log).
Baseline **{len(baseline)} file** (gồm PDF,dataset,A/B source/vector/stats/calibration,SQLite cũ và toàn bộ trial100)
được kiểm trước/sau **0 thay đổi/thiếu**. Không tính lại96 vector trial, không tạo C1/C2 mới, không fit hoặc
calibration/Top-5/fusion, không chạy lại MediaPipe và không ghi SQLite.
[Baseline](../../outputs/C1_lbp/roi_remediation_v0_4/baseline_before.json),
[final scope](../../outputs/C1_lbp/roi_remediation_v0_4/final_scope.json),
[manifest mới](../../outputs/C1_lbp/roi_remediation_v0_4/created_files_manifest.json).

Lệnh PowerShell thực tế tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/audit_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/audit_remediation.py --check-completed
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/render_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/verify_remediation.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/review_native_brows.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_remediation_tools/write_reports.py
```

Census đầu ghi đủ toàn bộ CSV/JSON rồi gặp lỗi **in summary ra stdout** do NumPy int64 JSON serializer,
exit1; đã sửa serialization log, kiểm completed CSV/JSON qua `--check-completed` exit0 và verifier exit0.
Không đổi geometry/rule/parameter hoặc chạy lại census để cải thiện số liệu; giữ nguyên artifacts đã ghi.
Các renderer/verifier/finalizer từ chối ghi đè bộ đã hoàn tất. Kết luận giới hạn vẫn
**GEOMETRY_VALIDATED / ANATOMY_PROVISIONAL**, không kích hoạt candidate và chưa triển khai C1 chính thức.
"""
    text_new(audit.ROOT / 'docs/audits/C1_ROI_REMEDIATION_REPORT.md', report)

    endpoint_tables = ''
    rationale = {
        'forehead_brow': 'Upper arc15 FACE_OVAL; lower native brow5+5; bridge giữa hai mày và nối thái dương là IMPLEMENTATION DETAIL. Không phải hairline/skin annotation.',
        'cheek_left_viewer': 'A36/41/40/39 thuộc EYE, offset0.08D đẩy xuống dưới mắt; A31/MP129 là nose-side proxy chưa canonical, A48/MP61 thuộc LIPS; A5…A0 thuộc FACE_OVAL. Các cạnh nối không phải contour má được PDF định nghĩa.',
        'cheek_right_viewer': 'A45/46/47/42 thuộc EYE, offset0.08D; A35/MP358 nose-side proxy chưa canonical, A54/MP291 thuộc LIPS; A11…A16 thuộc FACE_OVAL. Viewer-right chưa đồng nghĩa anatomical-right.',
        'nose_mouth': 'A27/MP168 trên sparse NOSE; A42/A39 là mắt với offset0.08D; A35/31 nose-side proxies; A54/48 khóe môi và A55…59 LIPS với offsets u±0.05,v0.06. Không dùng MP1/4 để tự sửa A; đường bao mũi-miệng chưa annotation.'}
    for region in audit.REGIONS:
        endpoint_tables += f'\n### {region}\n\n{rationale[region]}\n\n'
        endpoint_tables += '| Thứ tự | Index68 (0-based) | MP index | α·D·u | β·D·v | Membership mô hình |\n|---:|---|---:|---:|---:|---|\n'
        for row in endpoints:
            if row['variant'] != 'candidate_v0_4' or row['region'] != region: continue
            membership = row['contour_memberships'].replace('FACE_LANDMARKS_', '') or 'Không thuộc sparse contours đã xuất'
            endpoint_tables += f"| {row['vertex_order']} | {row['index68'] or 'Không có trong A68'} | {row['mediapipe_index']} | {row['offset_u_ipd']} | {row['offset_v_ipd']} | {membership} |\n"
    observations_table = '| Ảnh đã xem | Quan sát có giới hạn |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in OBSERVATIONS.items())
    validation = '# C1 anatomical validation — chứng cứ và phần chưa xác minh\n\n' + common + f"""
## Phân loại chứng cứ

| Vùng | PDF quy định | Quan sát/endpoint basis | Quy ước triển khai | Chưa đủ chứng cứ |
|---|---|---|---|---|
| Trán+lông mày | Tên vùng, dựa landmarks | Upper FACE_OVAL15 và native brow lower10; proxy coverage đo toàn kho | Upper oval không phải hairline; bridge/closure, zero margin, pixel rule | Toàn mô trán/mày; bốn continuous-node exceptions; tóc/khăn; canonical auxiliary478 |
| Má trái | Tên vùng, dựa landmarks | Lower-eye, nose-side, mouth-corner và FACE_OVAL endpoints trên mẫu CFD/HF | Viewer-left; offsets0.08D; straight polygon12 đỉnh | Ranh má thật/zygion/gonion, MP129, cơ sở cắt giữa má và mũi-miệng |
| Má phải | Tên vùng, dựa landmarks | Nhóm đối xứng phía phải ảnh, không tự chứng minh đối xứng giải phẫu | Viewer-right; cùng offsets,12 đỉnh | Ranh má thật, MP358, annotation hai bên và khi biểu cảm |
| Mũi+miệng | Tên vùng, dựa landmarks | Bridge nose, eye-inner, nose-side và LIPS;12 đỉnh | u±0.05D,v0.06/0.08D; giữ overlap | Full anatomical boundary; canonical nose-side; tay/răng/môi khi biểu cảm |

Tên bốn vùng là EXACT theo văn bản PDF trong phạm vi hẹp. Membership một điểm trong native contour được
đối chiếu đúng tập cạnh; **endpoint anatomical canonical của mọi vertex vẫn UNVERIFIED** khi chưa có chuẩn.
Số đỉnh/offset và những cạnh nối giữa contour không được PDF quy định. Không tự dùng nhãn EXACT cho toàn polygon.

[MediaPipe FaceLandmarksConnections](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py)
được xem24/11/2026 chỉ xác nhận danh sách contour. Snapshot local hash có trong source_proof/candidate JSON;
không dùng master như canonical mapping478→68 của nhóm. PDF là thẩm quyền cao nhất cho yêu cầu dự án.

## Mọi endpoint và thứ tự polygon ứng viên

A và thứ tự vertex0-based. MP native là0…477; không thêm điểm phụ vào vector A.
L/R mean6 float32 hiện hành, promote float64; D=norm(R−L),u=(R−L)/D,v=(-u_y,u_x).
P'=P_MP+D(αu+βv), nối0→1→…→n−1→0. Upper forehead và lower candidate không offset;
các offset của3 vùng còn lại đúng v0.2. Frame là theo người xem/code; quan hệ trái/phải của PDF cần tác giả chốt.
Overlap raw độc lập, uncovered không được lấp, missing/support guards giữ nguyên, không skin intersection.
CSV có endpoint status từng dòng cho cả3 phiên bản:
[endpoint_contract_review.csv](../../outputs/C1_lbp/roi_remediation_v0_4/endpoint_contract_review.csv).

{endpoint_tables}

## Hình minh họa PDF và giải phẫu thật phải tách riêng

Hình68 của PDF trang8 cho thấy layout nhóm hàm/mày/mắt/mũi/miệng trên CFD00001. Theo audit A,
đầu hàm trong implementation thấp hơn vị trí minh họa, MP1=A30 và MP4=A33 khác thứ tự cao-thấp so với hình.
Đây là **khác biệt so với hình minh họa**, không có đủ canonical MP-ID table để kết luận/tự đổi mọi endpoint.
MP129/358 không thuộc sparse NOSE không tự chứng minh sai vùng mũi; sparse contour không phải toàn mô mũi.
Không phát hiện chứng cứ mới đủ để sửa mapping A. C1 candidate giữ nguyên hàm, má và mũi-miệng.

Sai lệch đã chứng minh:4 proper self-intersections v0.2; undercoverage proxy mày toàn kho;
offset v0.3 gây crossing HF00198; các vi phạm dataset mặt phụ/tay có ảnh chứng cứ.
Những điều này khác với khẳng định mọi polygon sai giải phẫu hoặc mọi phụ kiện là vi phạm.
Không có anatomical segmentation annotation nên coverage mô thật cho toàn kho vẫn UNVERIFIED.

## Đo proxy, điểm liên tục và occlusion

{comparison}
HF00198 thiếu3/824 proxy pixels, HF00267 thiếu1/738; mày trái/phải tương ứng còn99.006623%/99.638989%.
V0.4 không tự giao vẫn có4 native point ngoài region; đã kiểm28.760 native brow points:

{outside_table}
Pixel coverage100% của HF00055/HF00463 không bao hàm continuous point membership100%.
Không âm thầm tăng margin hoặc dịch contour để làm bảng đạt100%. Những điểm mày proxy này cũng không phải
annotation đường biên lông thật. Upper FACE_OVAL không phải chân tóc; trên CFD/HF có phần trán nhìn thấy
nằm trên arc; PDF chưa chốt có bắt buộc toàn bộ mô trán hay một vùng ổn định. Cần tác giả/annotation chốt.

{observations_table}

15 before/after cases và HF00055 supplementary đã xem trực tiếp; **1422 ảnh còn lại chưa được review giải phẫu
bằng mắt trong nhiệm vụ này**. Đủ1438 ảnh được audit hình học/hair proxy/coverage tự động không làm thay đổi
sự thiếu ground truth. Cả16 mẫu cũng chỉ có observations, không được cấp anatomy clearance.
Ảnh A/MP toàn bộ4 vùng:
[CFD00001](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/cfd_final_00001_all_regions_A_MP.png),
[HF00001](../../outputs/C1_lbp/roi_remediation_v0_4/contact_sheets/hf_merged_00001_all_regions_A_MP.png).

## Kết luận sử dụng và các bước còn thiếu

- Có thể dùng v0.4 như **ứng viên hình học để review**, kèm đúng hash/schema và các exception, không tự chuyển
  thành input extractor/gallery hiện hành. Hiện geometry5752/5752; active contract/trial100 vẫn v0.2/96 valid4 missing.
- Cần annotation hoặc quyết định có thẩm quyền cho upper trán/hairline, lower mày, closure thái dương/glabella,
  viewer/anatomical left-right, endpoint má/mũi-miệng, overlap/occlusion, liên hệ sơ đồ68 với478 phụ trợ.
- Cần xem4 continuous-node cases, adjudication các vi phạm dataset và review mô thật độc lập trước nghiệm thu.
  Nếu chốt thay đổi, tạo version mới và kiểm toàn kho; không sửa PDF, A/B, SQL hoặc trial100 đã đóng băng.
- Không có cơ sở công nhận C1 chính thức/toàn hệ thống chỉ từ geometry. Không tạo vector trong nhiệm vụ này,
  không có Top-5 để chọn ROI, không triển khai C2 hoặc fusion.

{len(baseline)} protected files đã so SHA-256 trước/sau,0 thiếu/đổi;8 geometry tests đạt.
[Kiểm chứng](../../outputs/C1_lbp/roi_remediation_v0_4/verification.json),
[baseline](../../outputs/C1_lbp/roi_remediation_v0_4/baseline_before.json),
[final scope](../../outputs/C1_lbp/roi_remediation_v0_4/final_scope.json).
[Báo cáo remediation đầy đủ và lệnh thực thi](C1_ROI_REMEDIATION_REPORT.md).
"""
    text_new(audit.ROOT / 'docs/audits/C1_ANATOMICAL_VALIDATION.md', validation)
    # Recheck after report generation too; old files must remain untouched.
    final_baseline = audit.check_sources()
    audit.write_json(out / 'final_scope.json', dict(schema_id='C1_REMEDIATION_FINAL_SCOPE_v0.4.0',
        protected_file_count=len(final_baseline), missing_or_changed_files=[],
        baseline_sha256=audit.digest(out / 'baseline_before.json'),
        geometry_status=summary['geometry_status'], anatomy_status='ANATOMY_PROVISIONAL',
        C1C2_vectors_created=0, LBPHOG_calls=0, retrieval_comparisons=0, SQLite_writes=0,
        candidate_activated=False, parameter_search_or_retuning=False,
        all_previous_trial100_AB_calibration_PDF_dataset_SQLite_hashes_unchanged=True,
        execution_note='Initial census CSV/JSON complete; stdout serialization of numpy.int64 failed after data writes. Logging fixed; --check-completed and independent verification passed without recomputing/replacing artifacts.'))
    paths = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=audit.ROOT, text=True).splitlines()
    files = []
    for path in sorted(paths):
        p = audit.ROOT / path
        if p.is_file() and str(p.resolve()) not in baseline:
            files.append(dict(path=path, bytes=p.stat().st_size, sha256=audit.digest(p)))
    audit.write_json(out / 'created_files_manifest.json', dict(schema_id='C1_REMEDIATION_NEW_FILES_v0.4.0',
        anatomy_status='ANATOMY_PROVISIONAL', self_excluded=True, files=files))
    print('Reports complete;', len(files), 'new files;', len(baseline), 'protected old files unchanged', flush=True)


if __name__ == '__main__':
    main()
