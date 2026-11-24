"""Write the requested v2 decision/acceptance reports and final scope evidence."""
from pathlib import Path
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_json, read_csv, write_json, save_csv, load_stats

DOC = ROOT / 'docs/audits'
E = DOC / 'v2_evidence'
A = ROOT / 'outputs/A_geometry/features_report_v2'
B = ROOT / 'outputs/B_color/color_features_report_v2'
AB = ROOT / 'outputs/retrieval/ab_report_v2'


def save(name, value):
    (DOC / name).write_text(value.strip() + '\n', encoding='utf-8')


def clean(value):
    return str(value).replace('|', '∣').replace('\n', '<br>')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] +
        ['| ' + ' | '.join(clean(value) for value in row) + ' |' for row in rows])


def main():
    summary = read_json(E / 'verification_summary.json')
    assert summary['status'] == 'PASS' and summary['a12_corrected'] and summary['b12_corrected']
    coverage = read_json(E / 'test_coverage.json')
    assert coverage['all_114_distinct_tests_covered']
    a_comparison, b_comparison = read_json(A / 'comparison_v1_v2.json'), read_json(B / 'comparison_v1_v2.json')
    prior = read_json(DOC / 'evidence/requirements_register.json')
    prior_a2 = [r for r in prior if r['id'].startswith('A2-')]
    source = ROOT / 'features/A_geometry/src/geometry_features.py'
    module = ast.parse(source.read_text(encoding='utf-8-sig'))
    assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in module.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.List)}
    groups = ['JAW', 'LEFT_EYEBROW', 'RIGHT_EYEBROW', 'NOSE', 'LEFT_EYE', 'RIGHT_EYE', 'MOUTH']
    group_rows = []
    offset = 0
    for group in groups:
        values = assignments[group]
        group_rows.append([group, f'{offset}–{offset + len(values) - 1}', ', '.join(map(str, values)),
                           'UNVERIFIED về đúng từng vị trí giải phẫu; giữ nguyên'])
        offset += len(values)
    assert offset == 68
    endpoints = [
        'p2=MP132,p14=MP361; H=D((p21=MP107+p22=MP336)/2,p8=MP152)',
        'L=mean(p36..41), R=mean(p42..47); H như trên',
        'p36=MP33,p39=MP133; d=||L−R||', 'p42=MP362,p45=MP263; d=||L−R||',
        'p37=MP160,p41=MP144,p38=MP158,p40=MP153; p36/p39',
        'p43=MP385,p47=MP380,p44=MP387,p46=MP373; p42/p45',
        'p31=MP129,p35=MP358', 'p48=MP61,p54=MP291', 'p62=MP13,p66=MP14',
        'E=(L+R)/2; p30=MP1', 'E và midpoint(p48=MP61,p54=MP291)',
        'p30=MP1,p8=MP152; H như trên', 'p4=MP172,p12=MP397; H như trên',
        'p4=MP172,p8=MP152,p12=MP397']
    gaps = [
        'Chưa chốt điểm zygion và định nghĩa chiều cao mặt: code dùng giữa đầu mày→cằm, không có bảng endpoint chuẩn PDF.',
        'Chưa chốt tâm mắt6 mí hay tâm đồng tử/iris, và endpoint cao mặt.',
        'Cần xác minh khóe mắt và quy ước trái theo giải phẫu hay theo ảnh.',
        'Cần xác minh khóe mắt và quy ước phải theo giải phẫu hay theo ảnh.',
        'PDF chỉ nêu độ mở mí, chưa quy định EAR trung bình2 đoạn/chiều ngang mắt.',
        'PDF chỉ nêu độ mở mí, chưa quy định EAR trung bình2 đoạn/chiều ngang mắt.',
        'Chưa đủ bằng chứng MP129/358 đúng hai cánh mũi trong mọi ảnh.',
        'Cần canonical endpoints hai khóe môi; không đổi theo visual retrieval.',
        'Cần xác minh p62/p66 chính là cặp biên trong phù hợp độ mở môi.',
        'p30=MP1 cần xác minh vai trò chóp mũi; topology mũi có dấu hiệu cần xem lại.',
        'PDF không nói rõ “khóe miệng” dùng một khóe hay trung điểm hai khóe.',
        'Cần xác minh chóp mũi/đáy cằm và endpoint chiều cao mặt.',
        'Chưa có canonical gonion/xương hàm cho lựa chọn p4/p12.',
        'Phép acos/độ khớp PDF; endpoint hai góc hàm tại p4/p12 chưa đủ thẩm quyền xác nhận.']
    a2_rows = []
    for i, (row, endpoint, gap) in enumerate(zip(prior_a2, endpoints, gaps), 1):
        a2_rows.append([i, f"{row['requirement']} (PDF {row['pdf_page']})", endpoint, row['formula'],
            'degrees' if i == 14 else 'dimensionless', 'UNVERIFIED; số học oracle đạt, không đổi công thức', gap,
            'Annotated anatomical/canonical68 GT trên đúng ảnh PDF và mẫu đa dạng; đối chiếu từng ID và sai số theo protocol chốt trước'])

    save('A_GEOMETRY_DECISIONS_V2.md', f'''# Hồ sơ quyết định hình học A — phiên bản2

Ngày23/11/2026. PDF chuẩn SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đối chiếu đủ6 báo cáo audit; giữ chúng như baseline lịch sử. Source geometry SHA-256 hiện tại: `{digest(source)}`; byte không đổi so baseline.

## Phần PDF rõ và phạm vi v2 đã sửa

PDF §2.2 yêu cầu478→68,136 tọa độ chuẩn hóa theo `(p−C)/d`,14 đặc trưng như bảng trang9–10; Euclid150. §2.5.2 quy định Z-score `(x−mu)/(sigma+epsilon)`. Yêu cầu v2 đã chốt **epsilon1e-8,ddof0**; `report_v2.py` thực hiện đúng và giữ raw A150 bất biến. Việc chốt normalizer **không đồng thời phê duyệt** mọi MP index, tâm mắt, endpoint A2 hoặc ε guard A2 cũ.

API extractor cũ, `geometry_features.py`, `map_68_landmarks.py`, batch extractor và normalizer/query legacy không bị sửa. V2 chỉ dùng extractor hiện có cho raw query rồi áp dụng stats v2. Không đưa478 điểm hoặc thêm chiều mới vào A150.

## Mapping và thứ tự hiện hành

Các index68 dưới đây **0-based**. PDF minh họa hình68 nhưng không cung cấp đầy đủ bảng478→68 có thể dùng như canonical labels.

{table(['Nhóm', 'Index68', 'Index MediaPipe478 đang dùng', 'Kết luận'], group_rows)}

Chứng cứ: [mapping đủ68 điểm](evidence/landmark_mapping.csv), [hình PDF trang8](evidence/pdf_page8_X31.png), [ảnh mốc audit](evidence/cfd_final_00001_68_annotated.png). Số lượng68/nhóm/thứ tự x0,y0,… có kiểm chứng; đúng vị trí giải phẫu từng mốc vẫn cần canonical/annotation.

## Tâm mắt và phép biến đổi tọa độ

`L=mean(p36..41)`, `R=mean(p42..47)`, `C=(L+R)/2`, `d=||L−R||₂`, `p′=(p−C)/d`; A1 flatten136. Phép tịnh tiến/chia d được PDF quy định và oracle kiểm chứng. Cách lấy tâm mỗi mắt bằng6 mí chưa được PDF chốt; không tự chuyển sang MP468/473 dù audit đã đo iris riêng. Ngưỡng d<1e-6, norm góc<1e-8 và regularizer A2 `+1e-8` giữ nguyên, là quy ước hiện hành chưa được nâng thành nguyên văn PDF.

## Từng đặc trưng A2

Ký hiệu `D(i,j)=||p_i−p_j||₂`, `E=(L+R)/2`, `H=D((p21+p22)/2,p8)`, `e=1e-8`. File/hàm hiện hành cho cả14 hàng: `features/A_geometry/src/geometry_features.py::calculate_ratios`; STT14 gọi `angle_degrees`. Tất cả được giữ nguyên.

{table(['STT', 'Phần PDF rõ', 'Mốc/định nghĩa code', 'Công thức hiện hành', 'Đơn vị', 'Trạng thái v2', 'Thiếu chứng cứ/dấu hiệu', 'Phép thử cần có'], a2_rows)}

[56 phép đối chiếu ảnh thật](evidence/a2_real_image_oracles.csv) chứng minh số học hiện hành trên14×4 ảnh; không chứng minh mọi endpoint đúng giải phẫu. Đặc biệt p30=MP1 có y≈149.59 và p33=MP4 có y≈142.02 trên CFD00001, nên topology “đáy mũi” cần xem lại với hình PDF. Đây là **dấu hiệu cần xác minh**, chưa có bảng ID chuẩn đủ để tự sửa một index cụ thể. Không tự chốt DEVIATION mới chỉ từ tên “nose_tip”, cũng không tự gắn EXACT vì test số học đạt.

## Self-match tách khỏi công thức chuẩn hóa

Legacy A-only loại theo path; B-only đã duyệt D17 dùng image_id; A+B dùng hash byte→IDs và filename tie-break. A+B v2 tái sử dụng đúng chính sách đó. Bản PNG mã hóa lại có byte khác được coi là query mới và có thể trả ảnh gốc; không tự thêm pixel hash/face identity heuristic. PDF không định nghĩa đầy đủ self-match, nên không gán quy tắc của code là nguyên văn PDF. Không loại các ảnh khác chỉ vì metadata ghi cùng người.

## Việc cần làm để đóng các mục còn mở

Chốt canonical68/MediaPipe mapping và quy ước trái/phải có thẩm quyền; đánh dấu thủ công các endpoint trên đúng ảnh minh họa và mẫu đa dạng; so sánh tọa độ/sai số theo protocol định trước. Làm rõ cao mặt, gò má, EAR, chóp/base mũi, khóe miệng và góc hàm. Chỉ sửa khi có bằng chứng rõ, trong version mới và giữ baseline; không chọn công thức bằng Top-5. **Chưa triển khai C1/C2.**
''')

    dataset_records = read_csv(B / 'manifest.csv')
    by_id = {row['image_id']: row for row in dataset_records}
    observations = [
        ('hf_merged_00333', 'DEVIATION', 'Mặt phụ nhìn thấy ở mép trái/phải, vi phạm §1.2 không có mặt phụ.', 'evidence/dataset_mask_review_page1.png'),
        ('hf_merged_00561', 'DEVIATION', 'Một phần mặt phụ/eye ở mép trái, vi phạm §1.2.', 'evidence/dataset_mask_review_page1.png'),
        ('hf_merged_00722', 'DEVIATION', 'Ngón tay chồng vùng miệng/mặt dưới, vi phạm yêu cầu không che mắt/mũi/miệng.', 'evidence/dataset_mask_review_page2.png'),
        ('hf_merged_00209', 'MISSING B; không zero-fill', 'Hair raw0 pixel, B144 không tồn tại; A vẫn có đủ150 chiều.', 'evidence/dataset_mask_review_page2.png'),
        ('hf_merged_00694', 'UNVERIFIED', 'Khăn che tóc, hair mask355 pixel; chưa chứng minh đại diện màu tóc.', 'evidence/dataset_mask_review_page2.png'),
        ('hf_merged_00610', 'UNVERIFIED', 'Mũ/phụ kiện và cờ face-count lịch sử; model mới báo1 chưa phải GT.', 'evidence/dataset_mask_review_page1.png')]
    dataset_table = [[key + '.png', status, observation, by_id[key]['source_sha256'], evidence]
                     for key, status, observation, evidence in observations]
    save('DATASET_REMEDIATION_V2.md', f'''# Dataset — hồ sơ xử lý phiên bản2, chưa thay dữ liệu

Ngày23/11/2026. Giữ nguyên toàn bộ1438 ảnh nguồn, metadata và masks; không xóa/crop/inpaint/tạo ảnh thay thế, không đổi mask để cải thiện retrieval. V2 chỉ tạo vector/stats/calibration/query artifacts mới, không giải quyết một vi phạm ảnh bằng thay đổi công thức.

## Các trường hợp giữ riêng

{table(['Ảnh', 'Trạng thái', 'Bằng chứng/quan sát', 'SHA-256 nguồn bất biến', 'Ảnh review đã có'], dataset_table)}

HF00333/HF00561/HF00722 vẫn có mặt trong A v2 và tập B hợp lệ v2. HF00209 vẫn có A; manifest B đủ1438 danh tính, ma trận compact chỉ1437 vector hợp lệ; missing row không có feature_row_index. Không biến cảnh báo/phụ kiện thành quy tắc tự loại ảnh hoặc sửa nhãn. Khăn trùm tóc không tự động vi phạm điều khoản mắt/mũi/miệng không bị che; chất lượng vùng tóc vẫn cần kiểm chứng.

## Chứng cứ cần có để giải quyết các tiêu chí PDF

| Tiêu chí PDF | Chứng cứ hiện có | Thiếu gì để kết luận | Cách giải quyết được đề xuất, chưa thực hiện |
|---|---|---|---|
|1438 ảnh,RGB8 PNG256×256|Audit đọc IHDR/hash toàn kho đạt|Lịch sử encoder “PNG95”/cùng mức nén chưa đủ|Bổ sung log/source encode; không thay ảnh hiện hành hoặc đổi sang JPEG.|
|1135 người,303 ảnh cảm xúc cùng người|CFD710 dòng có407 person_ids và303 dòng lặp thêm;HF728 thiếu person_id|HF có trùng nhau/CFD không, nhãn cảm xúc và provenance identity|Catalog person/expression có thẩm quyền, liên kết nguồn rõ; không suy đoán danh tính từ ảnh hoặc dùng hash byte làm ID người.|
|Một mặt,không có mặt phụ|Detector num_faces5 vẫn báo1 trên mọi ảnh; đã nhìn thấy mặt phụ HF00333/HF00561|Annotation/review đầy đủ; độ bao phủ detector tại mép|Gắn cờ trong hồ sơ riêng, duyệt theo protocol; nếu cần corpus tuân thủ mới thì xin tác vụ riêng và version/provenance riêng, giữ nguyên corpus cũ.|
|Không che mắt/mũi/miệng|HF00722 tay che miệng; raw skin có thể nhận da tay|Vùng occlusion/review độc lập toàn kho|Không inpaint/crop/đổi mask trong v2; thu thập bằng chứng/source phù hợp nếu sau này được giao sửa dataset.|
|Chính diện,yaw/pitch<5°|Pose model chưa hiệu chuẩn; roll có đo|GT/protocol camera/pose định nghĩa rõ|Hiệu chuẩn và annotation hoặc nguồn góc có thẩm quyền; không coi output model là GT.|
|IPD29.45%,min27.23,max32.61;tâm mắt40%|Audit centroid/iris khác số PDF; tâm mắt y có phân bố|Định nghĩa tâm mắt, sai số cho phép, log affine alignment|Truy lại pipeline đầu vào và phép đo chuẩn; không rescale ảnh để ép median.|
|Mặt70–90%,median78.6%,căn giữa|Mesh-height proxy median78.564%|Định nghĩa bbox/đỉnh đầu-cằm/tolerance|Đo theo định nghĩa chốt trước; không coi mesh bbox là ground truth face box.|
|Bicubic/crop vuông đỉnh đầu→cằm|Ảnh cuối cùng và code visualize|Source/log tiền xử lý gốc|Lưu provenance resize/affine/crop; phóng ảnh minh họa bằng bicubic không chứng minh preprocessing.|
|Metadata/CSDL gồmID/path/vị trí hai mắt|CSV ID/path/hash, không đủ eye x/y/DB hiện thực|SchemaDB/log lưu tọa độ/quy trình ingestion|Bổ sung bằng chứng/thiết kế trong tác vụ dữ liệu riêng; không tự dựng DB hoặc thay catalog nguồn.|
|Nhãn nữ,18–60/đa dạng|Metadata hiện thiếu tuổi/nhãn đủ|Nhãn nguồn và quyền/thẩm quyền của annotation|Không suy đoán tuổi/giới/sắc tộc từ ngoại hình; cần nhãn/provenance hợp lệ.|

Liên kết hồ sơ chi tiết: [audit dataset](DATASET_REPORT_COMPLIANCE.md), [số đo toàn kho](evidence/dataset_measurements.csv), [cờ model](evidence/dataset_model_review_candidates.csv), [quan sát thủ công](evidence/visual_review_findings.csv). Các cờ là bằng chứng screening, không phải nhãn GT hoặc accuracy. Không tạo segmentation/retrieval GT từ chính dự đoán.

## Phạm vi nghiệm thu v2

A12/B12 có thể được sửa và kiểm chứng số học trong khi dataset vẫn còn DEVIATION DS05/DS10. Hai kết luận này được giữ riêng. Không tuyên bố toàn hệ thống100% tuân thủ hoặc A/B đã chứng minh chất lượng nhận diện vì có vector/Top-5 hợp lệ. **Không triển khai C1/C2, không thay PDF.**
''')

    examples = read_json(AB / 'queries/cfd_final_00001/results.json')
    old_examples = read_json(ROOT / 'outputs/retrieval/ab_experiment/queries/cfd_final_00001/results.json')
    old_lookup = {r['image_id']: r for r in old_examples['results']['ab']}
    top_table = [[r['rank'], r['image_name'], f"{r['distance_a']:.12f}", f"{r['distance_b']:.12f}",
        f"{old_lookup[r['image_id']]['distance_total']:.12f}", f"{r['distance_total']:.12f}"] for r in examples['results']['ab']]
    answers = [
        [1, 'A12 đã đúng sigma+epsilon?', 'Đã khắc phục ở v2: epsilon1e-8,ddof0; lưu raw_sigma/effective_divisor riêng, không thay std nhỏ bằng1,không bỏ chiều0 variance.', 'A1501438×150;19 tests mới + oracle toàn kho.'],
        [2, 'B12 đã chuẩn hóa mô-men trước ghép thật sự?', 'Đã khắc phục: fit24 Lab moments; thay12 Lab trong mỗi region72 còn tách riêng; sau đó concatenate144 và fit/transform final144 riêng.', 'features_B_after_moments.npy;stats moments24/final144;oracle độc lập cả2 stage.'],
        [3, 'Query dùng đúng stats/version?', 'Đã kiểm chứng: A dùng mean/raw_sigma/epsilon v2; B dùng2 stats v2 theo thứ tự; worker trả schemaID/hash từngstats. Loader từ chối sai stage/v1/A-vs-B.', 'Real new_query trong2 venv, q vector bằng đúng hànggallery khi pixel gốc không đổi.'],
        [4, 'Legacy có thay đổi?', f"Không: hash {summary['legacy_files_hash_checked']} file baseline đều giữ nguyên; không sửa API/file hiện có,không ghi đè vectors/stats/outputs/audit/PDF/dataset/C1/C2.", 'baseline_before.json;final_scope.json;new_source_inventory.json.'],
        [5, 'Oracle độc lập đạt?', 'Đạt:19 tests mới;114 testcases trong tests/đã được phủ qua2 venv;39 oracle audit cũ đạt. Oracle fsums toàn kho/query/pairs không gọi fit/transform/rank mục tiêu làm expected.', 'verification_summary.json và logs/test_coverage.json.'],
        [6, 'Khoảng cách/ranking thay đổi gì?', 'Khoảng cáchA vàmedianA đổi;B thay đổi mức làm tròn dùthứtự thực thi đã sửa;9/9 bảng Top5của3 query giữ nguyên,50 hàng B-only cũ giữ thứtự.', 'distance_comparison.csv,top5_comparison.csv,ranking_comparison.json,b_only_10_queries_comparison.csv.'],
        [7, 'Còn DEVIATION trong code A/B v2 đang dùng?', 'Không còn sai lệch đã xác nhận A12/B12 trong luồng chuẩn hóa v2 được kiểm tra;AB14được giải quyết bằng calibration v2. B18 chỉ helperlegacy,không được chuẩn hóa v2 gọi. Chưa chứng nhận toàn bộ geometry/A2do các mục UNVERIFIED.', 'Schema/step artifacts/independent tests;no full-system compliance claim.'],
        [8, 'Còn điều kiện chưa chứng minh/vi phạm?', 'Mapping478→68,tâm mắt,A2endpoints/guards,self-match định nghĩa;dataset mặtphụ/chemiệng;identity/age/pose/alignment/encoder/CSDL;mask semanticquality vàrelevance.', 'A_GEOMETRY_DECISIONS_V2.md;DATASET_REMEDIATION_V2.md;6 auditbaseline.']]
    stats_table = [
        ['A normalized', '1438×150 float32', '1438×150 float64', f"max∣Δ∣={a_comparison['max_absolute_difference_vs_saved_v1']:.12g}"],
        ['A divisor', 'std_safe', 'raw_sigma+1e-8', f"max formula-only∣Δz∣={a_comparison['max_formula_difference_before_legacy_float32_cast']:.12g}"],
        ['B raw', '1437×144 float64', '1437×144 float64', 'Tính lại từrawmasks,đúng từng phần tửV1'],
        ['B Lab stage', 'Không có stage riêng', '24 mean/raw_sigma/divisors;post-stage1437×144', 'Chỉ24Lab thay đổi;HS/Hue/circular giữ nguyên ở stage này'],
        ['B final', 'Fit trên raw144', 'Fit trên post-moment144', f"max∣Δz∣={b_comparison['max_normalized_difference_vs_v1']:.12g}"],
        ['MedianA', f"{summary['median_a_v1']:.15f}", f"{summary['median_a_v2']:.15f}", f"Δ={summary['median_a_delta']:.12g}"],
        ['MedianB', f"{summary['median_b_v1']:.15f}", f"{summary['median_b_v2']:.15f}", f"Δ={summary['median_b_delta']:.12g}"]]
    error_table = [
        ['A gallery sigma+epsilon', summary['a_full_oracle_max_error']],
        ['B Lab24 stage', summary['b_moment_stage_max_error']],
        ['B full2-stage final', summary['b_full_two_stage_oracle_max_error']],
        ['A query', summary['a_query_oracle_max_error']],
        ['B queryLab24', summary['b_query_moment_max_error']],
        ['B queryfinal144', summary['b_query_final_max_error']],
        ['Pair EuclidA', summary['independent_pair_a_max_error']],
        ['Pair EuclidB', summary['independent_pair_b_max_error']]]
    distance_rows = len(read_csv(E / 'distance_comparison.csv'))
    save('AB_V2_IMPLEMENTATION_REPORT.md', f'''# Nghiệm thu A150/B144 report v2

Ngày **23/11/2026**. **Đã triển khai, chạy và kiểm chứng A12/B12 ở phiên bản 2; chưa thể tuyên bố toàn hệ thống tuân thủ 100%.** PDF giữ nguyên SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Quy ước epsilon/ddof A và Lab24 B được người dùng chốt trong yêu cầu v2: [v2_authority.json](v2_evidence/v2_authority.json). Đã đọc và giữ nguyên sáu báo cáo audit; hash ở [phase1_review.json](v2_evidence/phase1_review.json).

## Trả lời tám câu nghiệm thu

{table(['Câu', 'Yêu cầu', 'Kết luận có giới hạn', 'Bằng chứng'], answers)}

## Module và entry point mới

Không sửa hàm hoặc API legacy. Tám file mới:

- `shared/report_v2.py`: I/O, stats, hash, integrity và bảo vệ output.
- `features/A_geometry/src/report_v2.py`: fit/transform/build/load A150_report_v2.0.0.
- `features/B_color/src/report_v2.py`: descriptor từng vùng, Lab24 trước ghép và final144.
- `retrieval/search_ab_v2.py`: load đúng gallery v2, join danh tính, calibration và query.
- `retrieval/ab_query_worker_v2.py`: extractor trong hai môi trường gốc, schema/stats hashes v2.
- `tests/test_report_v2.py`: 19 tests mới về công thức, query và version.
- `scripts/verify_ab_report_v2.py`: oracle độc lập toàn kho/query/pairs/ranking/hash.
- `scripts/report_ab_v2.py`: ba hồ sơ v2 và xác minh phạm vi cuối.

Phạm vi dự kiến trước sửa: [implementation_scope.json](v2_evidence/implementation_scope.json). Danh sách file/hàm/dòng/hash thực tế: [new_source_inventory.json](v2_evidence/new_source_inventory.json).

## A12 — công thức và dtype

```text
mean = mean(raw_A, axis=0)
raw_sigma = std(raw_A, axis=0, ddof=0)
effective_divisor = raw_sigma + 1e-8
normalized = (raw_A - mean) / effective_divisor
```

Raw A1438×150 float32 giữ nguyên. `raw_reference.json` lưu đường dẫn/hash raw bất biến; metadata có image_id/a_row_index. Stats lưu riêng mean, raw_sigma, epsilon, effective_divisor, ddof, fit_count, schema và hash raw/fit manifest. Không std_safe, không bỏ chiều, không ép query chiều hằng thành 0. Query dùng lại mean/raw_sigma/epsilon đúng phiên bản, không fit lại.

Normalized A v2 lưu float64, thống nhất phép tính gallery/query với B. V1 normalized float32; raw A không đổi. So sánh tách phần thay công thức trước cast khỏi sai số cast float32 v1 (max `{a_comparison['legacy_float32_cast_max_error']:.12g}`). Không quy toàn bộ chênh lệch file v1/v2 cho epsilon hoặc chọn dtype bằng Top-5.

## B12 — chuẩn hóa mô-men trước ghép

Tính lại descriptor từ **1438 ảnh và 2876 raw mask** đã kiểm hash/receipt, không chạy segmentation lại. 1437 raw B144 khớp từng phần tử v1. Giữ HS48/Lab12/Hue12, class1/17, raw mask, min100, Pearson/circular đã duyệt; không erosion/gộp nose.

```text
skin72 và hair72 riêng, chứa Lab12 chưa chuẩn hóa
 -> fit 24 Lab moments: ddof0, divisor1 nếu sigma<1e-8
 -> chuẩn hóa 12 Lab trong mỗi vùng72 còn tách riêng
 -> ghép Skin72 + Hair72 thành B144
 -> fit bộ mean/raw_sigma/divisor D15 riêng trên 144 chiều SAU bước Lab
 -> final Z-score144 -> Euclid144
```

`normalize_moments_before_concat` trả hai vùng72; `assemble_after_moments` mới ghép B144. Raw serialization chỉ để lưu/đối chiếu, không đưa thẳng vào final fit. D14 cũ được thay bằng quy ước hai bước người dùng chốt. **B giữ D15 ở cả hai bước, không cộng epsilon của A.**

Lưu raw, `features_B_after_moments.npy`, normalized, stats24 và stats144 riêng, manifest/mapping/schema/source/integrity. Chỉ24 Lab đổi tại bước đầu; HS/Hue/circular giữ nguyên tại bước đó. Query dùng cả hai stats theo đúng thứ tự, không refit. Giá trị final gần v1 không phải lý do bỏ bước được PDF quy định.

Stats v1 chỉ đọc để kiểm tra/so sánh baseline. Loader v2 kiểm schema, stage24/144, fit manifest/hash và quan hệ giữa các vector. Calibration pin hash vectors/stats/schema v2, từ chối v1 hoặc cache stale/tamper.

## So sánh trước/sau

{table(['Hạng mục', 'V1', 'V2', 'Ảnh hưởng đã đo'], stats_table)}

Toàn bộ 150+24+144 bộ mean/raw_sigma/divisor ở [normalization_stats_comparison.csv](v2_evidence/normalization_stats_comparison.csv). Stats final B cho24 Lab dùng đơn vị sau biến đổi, không so trực tiếp với raw Lab rồi gọi là sai số fit.

## A+B và ranking

Join bằng image_id/a_row_index; B lấy theo feature_row_index. Giữ nguyên **20000 cặp ID và thứ tự** từ v1; dA/dB và median được tính lại trên vectors v2. Lưu hash source pair CSV và hash danh sách ID. Median normalization `d/(m+1e-8)`, trọng số cố định thử nghiệm0.5/0.5; chưa phải fusion chính thức bốn bộ.

Ba query00001/00088/00144 có chín bảng A-only/B-only/A+B trên cùng1437 ứng viên. **0/9 Top-5 đổi thứ tự**, không có vị trí toàn ranking đổi trong các phép thử này; không suy ra kết quả cho mọi query. Đối chiếu thêm mười query B-only v1/50 hàng: thứ hạng giữ nguyên. Khoảng cách và median vẫn đổi. Không dùng Top-5 trùng để kết luận công thức cũ đúng.

Baseline được tính lại bằng vector/median v1 trên cùng tập ứng viên; không giả đã có CSV A+B v1 cho00088/00144. [distance_comparison.csv](v2_evidence/distance_comparison.csv) có **{distance_rows} dòng**, [top5_comparison.csv](v2_evidence/top5_comparison.csv)45 dòng; [ranking_comparison.json](v2_evidence/ranking_comparison.json) ghi đầy đủ thay đổi.

Top-5 A+B của `cfd_final_00001.png`:

{table(['Hạng', 'Ảnh', 'dA v2', 'dB v2', 'D_AB v1', 'D_AB v2'], top_table)}

[Ảnh so sánh ba hàng](../../outputs/retrieval/ab_report_v2/queries/cfd_final_00001/comparison_top5.png), [JSON kết quả](../../outputs/retrieval/ab_report_v2/queries/cfd_final_00001/results.json). CSV/JSON lưu dA/dB, normalizedA/B, D_AB và score chế độ. Chưa có relevance labels để kết luận chất lượng nhận diện.

## Query mới, thiếu B và môi trường

Fixture `new_query.png` đã có từ baseline, pixel giống00001 nhưng encoding/hash khác, buộc qua nhánh query mới. V2 không tạo/sửa ảnh nguồn. Worker A chạy `.venv311`, B chạy `.venv-uniface` với model cục bộ đã kiểm hash, rồi đúng hai bước chuẩn hóa v2. Raw query/bước Lab/normalized được lưu để oracle; vectors query bằng đúng hàng gallery00001 của cả A/B. Đây là smoke test bằng ảnh có sẵn, không phải holdout.

HF00209 vẫn có A, B thiếu tóc: A-only có kết quả, A+B/B-only rỗng, dB/D null. Worker B chạy riêng với raw masks của ảnh này trả missing_B và không tạo.npy. Không zero-fill hoặc đổi trọng số. Self-match byte→ID giữ nguyên; PNG khác encoding có thể trả ảnh gốc, như hồ sơ quyết định đã ghi.

## Oracles và tests

{table(['Phép đối chiếu độc lập', 'Max sai số tuyệt đối'], [[name, f'{value:.12g}'] for name,value in error_table])}

Expected toàn kho dùng math.fsum và phương trình scalar cho mean/std/Euclid, không gọi fit/transform/rank/calibrate mục tiêu làm expected. Raw descriptors và pair IDs kiểm đúng từng phần tử; sai số cộng float tách khỏi sai công thức.

`tests/` có **95 tests cũ +19 tests v2 =114**. `.venv311`:112 đạt, hai test skip vì thiếu UniFace. `.venv-uniface`:tám batch tests đều đạt, gồm đúng hai test đã skip; đối chiếu ID test xác nhận đủ114 testcase.19 tests v2 cũng đạt ở UniFace. Chạy thêm23+16 oracle audit cũ qua unittest loader với log mới, không ghi lại log baseline. Không cài thư viện hoặc trộn site-packages. Xem [test_coverage.json](v2_evidence/test_coverage.json), [verification_summary.json](v2_evidence/verification_summary.json).

## Thời gian thực tế và phạm vi đo

Builder ghi thời gian đến mốc comparison: A `{a_comparison['elapsed_seconds']:.6f}` giây; B `{b_comparison['elapsed_seconds']:.6f}` giây. B gồm đọc/hash/receipt, tính descriptor, fit/lưu hai bước; chưa gồm verify_sources/integrity cuối hoặc khởi động interpreter. Oracle validation `{summary['elapsed_seconds']:.6f}` giây; query00001 `{examples['elapsed_seconds']:.6f}` giây đến trước ghi results.json. Không coi đây là cam kết hiệu năng hoặc so trực tiếp với thời gian segmentation v1.

## Output và bảo toàn

- `outputs/A_geometry/features_report_v2/`:raw reference, metadata, normalized A, stats/schema/source/integrity/comparison.
- `outputs/B_color/color_features_report_v2/`:raw/post-Lab/final B, stats24/144, manifest1438/rows1437/missing1.
- `outputs/retrieval/ab_report_v2/`:calibration và query CSV/JSON/PNG v2, kiểm worker thiếu B.
- `docs/audits/v2_evidence/`:baseline, phạm vi, logs, oracles, bảng so sánh và manifest mới.
- [A_GEOMETRY_DECISIONS_V2.md](A_GEOMETRY_DECISIONS_V2.md), [DATASET_REMEDIATION_V2.md](DATASET_REMEDIATION_V2.md).

**14057 file baseline không đổi byte.** Dataset/masks/metadata, sáu audit cũ, PDF và C1/C2 giữ nguyên. Không xóa/crop/inpaint/tạo ảnh thay thế; không triển khai C1/C2. [final_scope.json](v2_evidence/final_scope.json) và [created_files_manifest.json](v2_evidence/created_files_manifest.json) ghi phạm vi/hash.

## Lệnh PowerShell đã chạy thành công

Chạy tại repository root:

```powershell
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m features.A_geometry.src.report_v2
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B -m features.B_color.src.report_v2
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image hf_merged_00209.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00088.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image cfd_final_00144.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B -m retrieval.search_ab_v2 --image outputs/retrieval/ab_validation/new_query.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B scripts/verify_ab_report_v2.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B scripts/report_ab_v2.py
```

Output tồn tại được từ chối ghi đè. Query lại dùng `--output outputs/retrieval/ab_report_v2/queries/<new_run_name>`; calibration v2 dùng lại nếu mọi hash khớp. Build lại dùng thư mục mới đúng prefix `features_report_v2*` hoặc `color_features_report_v2*`, rồi chọn gallery/calibration v2 mới. Không ghi vào đường dẫn v1.
''')

    # Final scope: every pre-existing file must be byte-identical.
    baseline = read_json(E / 'baseline_before.json')
    changed = [name for name, expected in baseline.items() if not Path(name).is_file() or digest(name) != expected]
    assert not changed, changed
    plan = read_json(E / 'implementation_scope.json')
    inventory = []
    for name in plan['new_modules']:
        path = ROOT / name
        tree = ast.parse(path.read_text(encoding='utf-8'))
        inventory.append(dict(path=name, sha256=digest(path), definitions=[dict(name=n.name, line=n.lineno)
            for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]))
    write_json(E / 'new_source_inventory.json', inventory)
    known_new = {str((ROOT / name).resolve()) for name in plan['new_modules']}
    for folder in ['features', 'shared', 'retrieval', 'tests', 'scripts', 'models', 'annotations']:
        unexpected = [str(p.resolve()) for p in (ROOT / folder).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and str(p.resolve()) not in baseline and str(p.resolve()) not in known_new]
        assert not unexpected, unexpected
    write_json(E / 'final_scope.json', dict(status='PASS', legacy_files_checked=len(baseline), changed_legacy_files=changed,
        legacy_functions_modified=[], new_source_files=list(plan['new_modules']),
        new_output_roots=[str(A), str(B), str(AB), str(E)],
        reports=['A_GEOMETRY_DECISIONS_V2.md', 'DATASET_REMEDIATION_V2.md', 'AB_V2_IMPLEMENTATION_REPORT.md'],
        pdf_unchanged=True, dataset_unchanged=True, masks_unchanged=True, c1_c2_unchanged=True, full_system_compliance=False))
    new_files = []
    candidates = [ROOT / name for name in plan['new_modules']]
    for folder in [A, B, AB, E]:
        candidates += [p for p in folder.rglob('*') if p.is_file() and p.name != 'created_files_manifest.json']
    candidates += [DOC / name for name in ['A_GEOMETRY_DECISIONS_V2.md', 'DATASET_REMEDIATION_V2.md', 'AB_V2_IMPLEMENTATION_REPORT.md']]
    for path in sorted(set(candidates)):
        new_files.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=digest(path)))
    write_json(E / 'created_files_manifest.json', dict(count=len(new_files), files=new_files, self_excluded=True))
    print(json.dumps(dict(status='PASS', reports=3, legacy_files_unchanged=len(baseline), new_files=len(new_files),
                          a12='fixed in v2', b12='fixed in v2', full_system_compliance=False), indent=2))


if __name__ == '__main__':
    main()
