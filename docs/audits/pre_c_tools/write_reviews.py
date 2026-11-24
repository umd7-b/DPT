"""Build the four requested pre-C audit reports from fresh read-only evidence."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.report_v2 import digest, read_csv, read_json, write_json

DOC = ROOT / 'docs/audits'
E = DOC / 'pre_c_evidence'


def table(headers, rows):
    def cell(value):
        return str(value).replace('|', '∣').replace('\n', '<br>')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] +
                     ['| ' + ' | '.join(cell(x) for x in row) + ' |' for row in rows])


def save(name, content):
    (DOC / name).write_text(content.strip() + '\n', encoding='utf-8')


def main():
    authority = read_json(E / 'authority.json')
    mapping = read_json(E / 'mapping_verification.json')
    native = read_json(E / 'native_mediapipe_topology.json')
    dataset = read_json(E / 'dataset_source_review.json')
    db = read_json(E / 'database_inventory.json')
    frozen = read_json(E / 'v2_freeze_manifest.json')
    illustration = read_json(E / 'pdf_illustration_measurements.json')
    old_register = read_json(DOC / 'evidence/requirements_register.json')
    tests = (E / 'v2_tests.log').read_text(encoding='utf-8')
    assert 'Ran 19 tests' in tests and tests.rstrip().endswith('OK')
    intro = '''Ngày kiểm tra: **23/11/2026**, Asia/Saigon. PDF chuẩn duy nhất cho yêu cầu dự án: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, 18 trang, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh lại. Trang ghi dưới đây là trang PDF vật lý. Tài liệu MediaPipe chỉ giải thích topology/API; không thay PDF và không cung cấp bảng chuyển canonical 478→68 cho báo cáo nhóm.

Phạm vi lần này là kiểm toán, không sửa mapping, A2, code chuẩn hóa, nguồn ảnh, mask, vector/stats/calibration/output v1/v2; không tạo CSDL hoặc C1/C2. File mới chỉ nằm trong `docs/audits/`: bốn báo cáo này, `pre_c_tools/` và `pre_c_evidence/`.
'''

    groups = []
    for row in mapping['group_results']:
        groups.append([row['group'], len(row['selected']), row['native_contour'],
            f"{len(row['present'])}/{len(row['selected'])}", ', '.join(map(str, row['absent'])) or 'Không',
            'EXACT về membership contour' if not row['absent'] else 'UNVERIFIED cho MP129/358; 7 điểm còn lại có membership chính xác'])
    points = [r for r in read_csv(E / 'mapping_points_review.csv') if r['image_name'] == 'cfd_final_00001.png']
    point_rows = [[r['index68_zero_based'], r['index68_pdf_one_based'], r['mediapipe_index'], r['code_group'],
                   r['native_contour'], r['on_native_sparse_contour']] for r in points]
    endpoint_text = [
        'p2=MP132,p14=MP361;H từ midpoint(p21=MP107,p22=MP336) tới p8=MP152',
        'L=mean(MP33,160,158,133,153,144);R=mean(MP362,385,387,263,373,380);H như STT1',
        'p36=MP33,p39=MP133;d=||L−R||', 'p42=MP362,p45=MP263;d=||L−R||',
        'p37=MP160,p41=MP144,p38=MP158,p40=MP153;W_L=D(36,39)',
        'p43=MP385,p47=MP380,p44=MP387,p46=MP373;W_R=D(42,45)',
        'p31=MP129,p35=MP358', 'p48=MP61,p54=MP291', 'p62=MP13,p66=MP14',
        'E=(L+R)/2;p30=MP1', 'E và midpoint(p48=MP61,p54=MP291)',
        'p30=MP1,p8=MP152;H như STT1', 'p4=MP172,p12=MP397;H như STT1',
        'p4=MP172,p8=MP152,p12=MP397']
    gaps = [
        'Chưa có canonical zygion/cao mặt; các điểm nằm trên face-oval không tự chứng minh đúng rộng gò má.',
        'Chưa chốt tâm mắt là centroid mí hay tâm iris/pupil và endpoint cao mặt.',
        'Các điểm thuộc RIGHT_EYE theo API; cần chốt frame trái/phải PDF.',
        'Các điểm thuộc LEFT_EYE theo API; cần chốt frame trái/phải PDF.',
        'EAR dùng hai đoạn dọc/chiều ngang là công thức code; PDF chỉ ghi độ mở mí.',
        'EAR dùng hai đoạn dọc/chiều ngang là công thức code; PDF chỉ ghi độ mở mí.',
        'MP129/358 không thuộc sparse NOSE; chưa có chuẩn alar endpoint để kết luận sai/đúng.',
        'MP61/291 thuộc LIPS; cần xác nhận endpoint khóe môi theo chuẩn 68.',
        'MP13/14 thuộc LIPS; cần quy ước độ mở môi/biên trong phù hợp.',
        'MP1 thuộc NOSE nhưng PDF không chốt index chóp mũi.',
        'Code dùng midpoint hai khóe; PDF chưa định nghĩa rõ một khóe hay trung điểm.',
        'Chóp mũi, đáy cằm và cao mặt cần chuẩn endpoint có thẩm quyền.',
        'Membership face-oval không xác nhận MP172/397 đúng gonion/rộng xương hàm.',
        'Arccos/độ chính xác về phép toán; chọn hai điểm góc hàm vẫn chưa được chứng minh.']
    a2_rows = []
    first = [r for r in read_csv(E / 'a2_fresh_oracles.csv') if r['image_name'] == 'cfd_final_00001.png']
    for i, (row, actual) in enumerate(zip([r for r in old_register if r['id'].startswith('A2-')], first)):
        a2_rows.append([i+1, row['requirement'], endpoint_text[i], row['formula'], actual['unit'],
            f"{float(actual['code_value']):.12f} / {float(actual['scalar_oracle']):.12f}",
            'UNVERIFIED về định nghĩa endpoint; số học đã kiểm chứng', gaps[i]])
    nose_rows = [[r['image_name'], r['mp1'], r['mp4'], f"{r['y_mp1_minus_mp4']:.8f}",
                  f"{r['raw_vector_max_error']:.3g}", f"{r['a2_max_scalar_error']:.3g}"] for r in mapping['samples']]
    illustration_rows = [[r['label'],r['index68_zero_based'],r['current_mp_index'],
        ', '.join(f'{v:.3f}' for v in r['illustration_xy_approx']),
        ', '.join(f'{v:.3f}' for v in r['current_xy']),f"{r['y_current_minus_illustration']:.3f}"]
        for r in illustration['comparisons']]
    save('A_MAPPING_FINAL_REVIEW.md', f'''# Kiểm tra cuối mapping và A2 của Bộ A

{intro}

## Kết luận có giới hạn

**68 điểm đủ, duy nhất, nằm trong miền 478 điểm; hai file nguồn dùng cùng mapping.** Trên ba ảnh thật, raw A150 tái lập đúng từng phần tử. Đã kiểm cả 14 A2 bằng oracle scalar và xem hai hình PDF trang 8. **Đã xác nhận khác biệt vị trí/topology so với hình minh họa trên cùng ảnh CFD00001**, rõ nhất ở đầu hàm và nhóm mũi. Tuy nhiên, **chưa thể xác định một canonical mapping 478→68 thay thế hoặc xác minh toàn bộ endpoint nhân trắc**, vì PDF không cho bảng MP ID đầy đủ. Giữ nguyên source và vector.

Phân loại dùng trong báo cáo: EXACT cho điều khoản rõ có source và oracle; IMPLEMENTATION DETAIL cho quy ước code ở chỗ PDF chưa chốt, không tự mang nghĩa “đã được phê duyệt”; DEVIATION chỉ khi chứng minh khác yêu cầu rõ; UNVERIFIED khi thiếu chuẩn, ground truth hoặc thẩm quyền. Không tự thay index theo overlay hoặc Top-5.

## Tài liệu MediaPipe và phạm vi thẩm quyền

[Google Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) mô tả 478 landmarks. [FaceLandmarksConnections chính thức](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py) định nghĩa contour mặt, mắt, mày, môi, mũi. Đã đối chiếu tập cạnh đang cài trong MediaPipe **{native['package_version']}**, hash source `{native['package_source_sha256']}`; toàn bộ cạnh và so sánh lưu ở [native_mediapipe_topology.json](pre_c_evidence/native_mediapipe_topology.json). Tham chiếu web master được xem ngày 23/11/2026; không dùng như một phiên bản canonical mapping 68 của báo cáo nhóm.

{table(['Nhóm code','Số điểm','Contour chính thức đối chiếu','Membership','Ngoài sparse contour','Phân loại hẹp'],groups)}

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

{table(['Index code 0-based','Số thứ tự 1-based','MP index','Nhóm code','Contour đối chiếu','Thuộc sparse contour'],point_rows)}

## MP1, MP4 và topology mũi

Source chính thức nối nhánh trục mũi theo `168→6→197→195→5→4→1→19→94→2`. MP1 và MP4 là **hai điểm khác nhau**, đều thuộc NOSE. Code hiện dùng p30=MP1 ở cuối đoạn bốn điểm “sống mũi”, p33=MP4 ở giữa đoạn năm điểm được chú thích “đáy mũi”. [Canonical mesh chính thức](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj) cũng chứa hai vertex khác nhau: MP1=(0,−1.126865,7.475604), MP4=(0,−0.463170,7.586580). Mesh 468 đó không phải bảng chuyển canonical 478→68; không dùng vị trí nhô ra hơn để tự chọn index thay thế.

{table(['Ảnh thật','MP1 pixel(x,y)','MP4 pixel(x,y)','y(MP1)−y(MP4)','Max sai số raw A so với kho','Max sai số 14 A2 oracle'],nose_rows)}

MP4 nằm cao hơn MP1 trong ba ảnh đo. Hình PDF vẽ điểm giữa nhánh năm điểm đáy mũi **thấp hơn** điểm cuối nhánh bốn điểm sống mũi; code hiện hành có quan hệ ngược lại. Xem [hình CFD trích từ PDF](evidence/pdf_page8_X31.png) và [hình HF](evidence/pdf_page8_X33.png).

### Sai khác minh họa đã đo trên cùng CFD00001

Đọc marker trực tiếp từ raster nhúng PDF, nhận đủ 17 marker hàm và 9 marker mũi bằng tâm trắng và vòng màu. Quy đổi panel xấp xỉ về khung 256×256; dùng khoảng đọc khoảng 1 pixel nguồn, không coi đây là annotation giải phẫu. Phương pháp, tọa độ và hash hình ở [pdf_illustration_measurements.json](pre_c_evidence/pdf_illustration_measurements.json); không gán MP ID cho marker của PDF.

{table(['Mốc theo vị trí trong nhóm','Index code 0-based','MP hiện dùng','PDF x/y xấp xỉ','Code x/y','y code − y PDF'],illustration_rows)}

Trong hình, `y(giữa đáy)−y(cuối sống)` ≈ **{illustration['nose_base_minus_bridge_y_illustration']:.3f} pixel**; code = **{illustration['nose_base_minus_bridge_y_current']:.3f} pixel**. Dấu ngược nhau không thể giải thích bằng đổi tỉ lệ hoặc tịnh tiến panel. Hai đầu hàm lệch khoảng 34 pixel theo chiều dọc. Đây là **DEVIATION có phạm vi: code không tái hiện vị trí/topology của hình minh họa**, không phải xác nhận một MP index thay thế cụ thể. Cần tác giả làm rõ hình là ràng buộc endpoint hay sơ đồ minh họa và cung cấp mapping/annotation chuẩn. Canonical MP ID vẫn **UNVERIFIED**; **không sửa mapping** chỉ từ hình hoặc chỉ vì một MP khác trông gần marker hơn.

## Tâm mắt và 14 A2

Source `geometry_features.py::normalize_landmarks` và `calculate_ratios` dùng L/R là trung bình sáu mốc mí, `E=(L+R)/2`, `d=||L−R||₂`, `P′=(P−E)/d`. Phép trừ E/chia d là EXACT về toán học trên các tâm đã chọn; dùng sáu mí để định nghĩa tâm mắt là IMPLEMENTATION DETAIL chưa được PDF định nghĩa đủ, còn tương đương với tâm nhân trắc là UNVERIFIED. Không tự đổi sang MP468/473.

Ký hiệu D(i,j)=Euclid 2D, H=D((p21+p22)/2,p8), e=1e-8. Cả 14 hàng ở `geometry_features.py::calculate_ratios`, góc gọi `angle_degrees`; A2 không sửa. Bảng số dùng ảnh CFD00001; tên bộ phận là định nghĩa code, không phải gán nhãn canonical chính thức. Đối chiếu danh sách PDF ở trang 9–10: [trang 9](pre_c_evidence/pdf_page_09.txt), [trang 10](pre_c_evidence/pdf_page_10.txt).

{table(['STT','Tên trong PDF','Endpoint/định nghĩa hiện hành','Công thức code','Đơn vị','Code / oracle ảnh thật','Trạng thái','Bằng chứng còn thiếu'],a2_rows)}

[a2_fresh_oracles.csv](pre_c_evidence/a2_fresh_oracles.csv) lưu 42 phép đo=14×3 với tử/mẫu, ε, code, scalar oracle và sai số. Có chứng cứ số học riêng cho từng đặc trưng, nhưng phép chia đúng không xác nhận chúng đo đúng zygion/gonion/chóp mũi mà PDF nói đến. Cần annotation endpoint, quy ước trái/phải/cao mặt/độ mở mí có thẩm quyền; không lấy kết quả retrieval để quyết định.
''')

    observations = {
        'hf_merged_00333': ('DEVIATION', 'Mặt phụ hiện rõ ở hai mép; vi phạm không có khuôn mặt phụ, PDF trang5.'),
        'hf_merged_00561': ('DEVIATION', 'Một phần mặt phụ với mắt ở mép trái; vi phạm cùng tiêu chí, PDF trang5.'),
        'hf_merged_00722': ('DEVIATION', 'Tay/ngón chồng vùng miệng và mặt dưới; vi phạm không che vùng miệng, PDF trang5.'),
        'hf_merged_00209': ('IMPLEMENTATION DETAIL: thiếu B theo D12', 'Khăn che tóc; mắt/mũi/miệng quan sát được. Hair=0 làm thiếu B, không tự suy ra sai tiêu chí dataset hoặc lỗi segmentation.'),
        'hf_merged_00694': ('UNVERIFIED về che khuất/chất lượng ROI', 'Khăn và kính nhìn thấy; không tự coi mọi phụ kiện là vi phạm. Hair=355 hợp lệ về ngưỡng, chưa chắc đại diện tóc. Cần đánh giá riêng mức che mắt/mũi/miệng.')}
    ds_rows = []
    for row in dataset['records']:
        status, observation = observations[row['image_id']]
        ds_rows.append([row['image_name'],status,observation,f"{row['b_status']}; hair={row['b_hair_pixels']}",
            ', '.join(row['original_tokens']),row['source_person_id'] or 'Trống',
            'Không có ảnh thay thế đã xác minh trong phạm vi tìm cục bộ'])
    save('DATASET_FINAL_REVIEW.md',f'''# Kiểm tra dataset cuối trước Bộ C

{intro}

## Xem lại đúng ảnh nguồn

Đã mở trực tiếp cả năm PNG tại `D:\\TuNam4\\dataset_HF_CFD_final\\images`, so hash với metadata và xem lại tiêu chí PDF §1.2–1.3 trang 5. Không lấy cảnh báo detector làm ground truth. Các quan sát ảnh dưới đây xác nhận lại hai loại vi phạm trước đây; không suy đoán người, tuổi hay giới từ ngoại hình.

{table(['Ảnh','Phân loại dataset','Quan sát và điều khoản','Tình trạng B v2','Token nguồn gốc','Person ID nguồn','Khả năng thay thế hiện được chứng minh'],ds_rows)}

Ảnh HF00333/HF00561/HF00722 **có B hợp lệ nhưng sai tiêu chí ảnh**; HF00209 **thiếu B nhưng chưa chứng minh sai tiêu chí chỉ từ thiếu tóc**. HF00694 có B hợp lệ theo ngưỡng 100 pixel nhưng độ đại diện tóc và che khuất mắt bởi kính còn cần review. Không gộp ba tình huống này thành một nhãn “ảnh lỗi”. Không suy ra hair=0 là mô hình sai khi không có ground truth.

Chứng cứ trước đây vẫn được giữ nguyên: [contact sheet 1](evidence/dataset_mask_review_page1.png), [contact sheet 2](evidence/dataset_mask_review_page2.png). Nguồn/hash hiện tại và đối chiếu provenance lưu ở [dataset_source_review.json](pre_c_evidence/dataset_source_review.json).

## Có thể lấy ảnh thay thế hợp lệ từ nguồn không?

Đã đọc `metadata.csv` và `hf_provenance.csv`, đối chiếu năm SHA/tên và rà tên ảnh gốc/các alias trong repository, dataset hiện hành và các thư mục nguồn có tên liên quan được xác định trong phạm vi tìm kiếm. Thư mục thực sự có thể đọc: {', '.join('`'+x+'`' for x in dataset['search_roots'])}. Không tìm được file gốc/alias đủ để xác nhận một ảnh thay thế. **Không có ứng viên thay thế nào đã được chứng minh hợp lệ.** Kết luận này không có nghĩa nguồn ngoài máy không tồn tại.

- HF00333/HF00561/HF00694 có token `parquet_stream_3176/3481/1530`: thiếu Hugging Face repository/dataset ID, revision, split, shard và checksum để định vị lại bản ghi.
- HF00722 có `Female (10).parquet_row_5`: chưa thấy file parquet được chỉ ra; không biết revision/split hay quy ước đánh số row 0/1. Không suy ra person_id từ nhãn file.
- HF00209 có `hf_hf01044_01044.jpg`: có tên gốc nhưng chưa xác nhận đường dẫn hoặc checksum ảnh gốc.
- Alias `final_01094.png`, `final_01322.png`, `final_00768.png`, `final_00970.png`, `final_01455.png` thuộc collection lịch sử; cũng chưa tìm thấy trong phạm vi rà soát.
- Cả năm source_person_id đều trống. Ngay cả tìm được ảnh raw cũng chưa chứng minh có ảnh khác cùng người và đạt tiêu chí; không dùng nhận diện ngoại hình để tự bổ sung.

Chi tiết đường dẫn/tên đã thử và kết quả tìm kiếm có trong JSON. Không suy đoán repository nguồn từ token chung hoặc tải/thay ảnh để đủ số lượng.

## Phương án dataset phiên bản mới — chỉ thiết kế

1. Giữ dataset 1438 ảnh, masks, catalog v1/v2 bất biến; lưu membership và cờ review trong manifest phiên bản mới, tách vi phạm ảnh, thiếu feature và UNVERIFIED.
2. Khi có nguồn có thẩm quyền, thu thập locator/revision/checksum/source ID; xác minh identity bằng metadata nguồn nếu cần bảo toàn số người, không đoán bằng ảnh.
3. Review ảnh ứng viên theo cùng tiêu chí: một mặt, không mặt phụ, chính diện, không che mắt/mũi/miệng, kích thước và alignment. Quyết định của người review và ground truth tách khỏi dự đoán của mô hình.
4. Ảnh mới phải có image_id mới gắn với nội dung bất biến, quan hệ `replaces_image_id`, lý do, người review, bằng chứng và dataset_version. Không gán vector/mask cũ của ảnh khác cho ảnh mới; không xóa file cũ.
5. Tính lại số ảnh, số người và ảnh lặp cảm xúc từ nhãn có chứng cứ; không ép số liệu về 1438/1135/303 hoặc ép IPD cho khớp PDF. Nếu catalog thay đổi, các stats/features/calibration/query sau này phải có version mới; không ghi đè v2 đã đóng băng.

Chưa thực hiện các bước tạo/thay ảnh hoặc subset mới trong nhiệm vụ này. Những ảnh bị đánh dấu vẫn có mặt trong input hiện hành.

## Số liệu/điều khoản PDF còn thiếu dữ liệu gốc

| Nội dung PDF | Điều chứng minh được | Điều còn thiếu |
|---|---|---|
| 1438 ảnh, 256×256, PNG RGB | Audit kỹ thuật toàn kho trước đã đạt; hash corpus không đổi | “PNG chất lượng 95”, cùng encoder/mức nén cần log gốc. |
| 1135 người, 303 ảnh cảm xúc lặp | 710 CFD rows có 407 source-scoped IDs và 303 extra rows; 728 HF thiếu person_id | HF có khác nhau/trùng CFD không; nhãn cảm xúc có thẩm quyền. Không suy ra 1135 từ 407+728. |
| Tuổi 18–60, nhãn nữ và tính đa dạng | Catalog ghi nguồn CFD/HF | Chưa đủ tuổi/giới/nhãn phân bố và provenance để kiểm tra; không suy đoán từ mặt. |
| Một mặt, không mặt phụ, không che | Ba ảnh nêu trên có vi phạm quan sát trực tiếp | Review đầy đủ corpus; detector trả một mặt không chứng minh không có mặt phụ. |
| Yaw/pitch <5°, alignment | Có landmark/model proxies được lưu từ audit | Ground truth, quy trình camera/dung sai và source tiền xử lý. |
| IPD median 29.45%, min/max 27.23–32.61%; eye y=40% | Audit centroid/iris cho các số khác nhau | Định nghĩa tâm mắt và phép đo gốc; không rescale để ép thống kê. |
| Face height 70–90%, median 78.6% | Mesh-height proxy ≈78.564% | Định nghĩa bbox/đỉnh đầu–cằm thống nhất; proxy không phải ground truth. |
| Bicubic/crop và metadata/CSDL | Có output ảnh, catalog và feature files | Log/source tiền xử lý, lưu tọa độ mắt và tầng CSDL ứng dụng chưa có bằng chứng triển khai. |

Xem [DATABASE_COMPLIANCE_REVIEW.md](DATABASE_COMPLIANCE_REVIEW.md). Dataset **chưa đạt toàn bộ điều kiện PDF**; không có thay đổi số đo, nhãn hoặc dữ liệu nguồn trong lần review.
''')

    a_xy=db['eye_xy_columns_in_a_metadata']; ds_xy=db['eye_xy_columns_in_catalog']
    save('DATABASE_COMPLIANCE_REVIEW.md',f'''# Kiểm tra CSDL ứng dụng theo PDF

{intro}

## Kết luận trong phạm vi repository

**Tầng HQT/CSDL ứng dụng chưa được triển khai trong repository đã kiểm tra.** Hiện lưu artifact bằng CSV/NPY/NPZ/JSON; không có bằng chứng bảng/schema, kết nối, insert hoặc query bằng DBMS cho ảnh, metadata và vector. Việc NumPy load file không chứng minh đã query CSDL. Không suy ra rằng một CSDL chưa biết ở máy chủ khác không tồn tại.

PDF §1.3 trang 5 nêu lưu metadata gồm mã ảnh, đường dẫn, vị trí hai mắt vào CSDL; §2.5.1 trang 16 mô tả lưu vector riêng để so sánh/kết hợp. PDF không chốt SQLite/PostgreSQL/MySQL hoặc kiểu dữ liệu SQL. Cách diễn đạt “bốn vector” nhưng “ba cột” cần tác giả làm rõ trước khi công nhận schema vật lý là tuân thủ hoàn toàn. Khoảng trống triển khai CSDL và điểm chưa rõ của đặc tả cần được giải quyết riêng; không tạo DB mới trong audit.

## Bằng chứng rà source và file thực tế

- Scan AST/import và các pattern connection/DDL/insert/SQL trên **{db['active_python_files']} file Python đang hoạt động** ở features/src/shared/retrieval/scripts/tests: **{db['db_driver_import_count']} import driver/ORM, {db['db_pattern_match_count']} match DB pattern**.
- File DB/SQL thuộc phạm vi dự án, ngoài môi trường ảo, Git, backup và browser profiles: **{len(db['database_or_sql_files'])}**. Không dùng SQLite cache của trình duyệt như bằng chứng DB dự án.
- Không dò dịch vụ/credential hoặc kết nối DB ngoài dự án; không tạo file DB, DDL, migration hoặc insert thử. Việc máy có công cụ DB cài sẵn không chứng minh ứng dụng đã có CSDL.
- Source hàm/dòng/hash, configs và danh mục lưu trữ: [database_inventory.json](pre_c_evidence/database_inventory.json). Scan chỉ nêu vị trí match nếu có, không in connection secrets.

| Hạng mục | Hiện thực quan sát | Trạng thái |
|---|---|---|
| DBMS/connection/transaction | Không tìm thấy driver/ORM/config kết nối hoặc connection code ứng dụng | NOT IMPLEMENTED trong repository; hệ thống ngoài phạm vi là UNVERIFIED. |
| Bảng metadata | Catalog `metadata.csv`; A/B có CSV riêng | Có file catalog; chưa có bảng DB, FK hoặc transaction chứng minh đáp ứng phần CSDL. |
| Khóa ảnh | image_id từ mã ảnh/stem filename; SHA-256 là bằng chứng nội dung | Dùng được để join artifact; chưa có primary/unique key DB. |
| Khóa người | source_person_id trên 710 CFD rows, 407 source-scoped IDs; 728 HF trống | Chưa có bảng persons hoặc FK; không coi image_id là person_id. |
| Đường dẫn ảnh | image_path tuyệt đối trong metadata A/B; filename/path/hash ở catalog nguồn | Có giá trị file path thực; chưa lưu/query được qua DBMS. |
| Tọa độ tâm hai mắt | Catalog có các cột eyeXY={ds_xy}; A metadata có eyeXY={a_xy}; A có eye_distance | Khoảng cách không phải hai tọa độ. Mảng landmark ở audit không phải bảng tâm mắt của ứng dụng. |
| Vector A/B | `.npy`: A1438×150, B1437×144; stats `.npz`; schema/hash `.json` | File đúng version có kiểm chứng số học; chưa có cột/vector row DB theo image_id. |
| image_id/a_row_index/feature_row_index | CSV mapping và join Python | Liên kết đúng artifact; row index không phải khóa danh tính bền vững hoặc FK DB. |
| Load/query | `np.load`, `csv.DictReader`, norm và sort trong RAM | Retrieval trên file; chưa có DB select/load hoặc transaction round-trip. |
| Bằng chứng thực nghiệm | V2 query files, CSV, PNG và hash đã kiểm tra | Chứng minh file persistence và số học; chưa chứng minh insert/SELECT hoặc phục hồi DB. |

## Theo dõi code kết nối/insert/load/query

`shared/report_v2.py::read_csv/load_stats` đọc file. `features/A_geometry/src/report_v2.py::build/load_gallery` ghi/đọc metadata CSV, raw reference JSON, NPY/NPZ. Bộ B tương tự với hai stage stats. `retrieval/search_ab_v2.py::load_gallery` gọi các loader file; `retrieval/search_ab.py::join_galleries/rankings` join bằng dict và tính Euclid/lexsort NumPy. Main lưu CSV/JSON/PNG. Không có đường đi connection/insert để kiểm transaction hoặc query DB.

Một ví dụ quan hệ hiện hành: HF00209 có a_row_index=918 nhưng không có B feature_row_index; các ảnh hợp lệ sau nó lệch một chỉ số giữa A/B. Vì vậy schema sau này phải liên kết bằng image_id và feature version; row index chỉ làm provenance của manifest/matrix cụ thể.

## Thiết kế đề xuất — chưa tạo CSDL

| Thực thể đề xuất | Nội dung/khóa cần lưu | Ràng buộc cần chứng minh |
|---|---|---|
| Images | image_id, sha256, source locator/revision, image_path, width/height | image_id ổn định, hash nội dung; ảnh mới có ID và lineage mới. |
| Persons | person_key, source_namespace, source_person_id, evidence | FK ảnh→người có thể NULL; không gán theo ngoại hình; source IDs không mặc nhiên toàn cục. |
| DatasetVersions/Membership | dataset_version, image_id, review_flags, status, replaces_image_id | Bảo toàn corpus cũ; lịch sử review và tổng số người có chứng cứ. |
| EyeCoordinates | image_id, detector/model/mapping version, left_x/y, right_x/y, frame/method | Không nhầm centroid sáu mí với pupil/iris; lưu đơn vị, kích thước và định nghĩa. |
| FeatureVersions | kind=A/B, schema_id, fit manifest, stats/source hashes, dtype, dimension | A150/B144 giữ version và hai stage B rõ; không dùng stats v1 cho v2. |
| FeatureVectors | image_id, feature_version, vector, status/reason | Unique(image_id,feature_version); B thiếu có NULL/status, không vector zero-fill; row index chỉ là provenance. |
| Calibrations | version, pair IDs/hash, epsilon, median A/B, vector fingerprints | Tính lại khi vector/tập ID đổi; không tính median riêng theo query. |
| RetrievalRuns/Results | query ID/inputs, feature/calibration versions, weights, dA/dB/normalized/D, rank | Đối chiếu round-trip với oracle file; không lẫn image_id và person_id. |

Đây là mô hình khái niệm để phân tích trách nhiệm lưu trữ, chưa phải schema vật lý đã được chứng nhận. Nhóm cần chọn HQT, kiểu lưu vector và làm rõ “ba cột/bốn vector” với tác giả; ưu tiên giữ A/B tách riêng đúng mục đích so sánh từng bộ. Tham chiếu file có checksum chỉ là phương án storage cần được chấp nhận riêng, không tự coi là đã đáp ứng yêu cầu lưu vector trong CSDL.

Kiểm nghiệm tối thiểu khi triển khai: migration/version; insert/load/select bằng transaction; unique/FK; round-trip 150/144 giá trị và dtype/hash; query dùng đúng stats/calibration; thiếu B có trạng thái; không đổi ranking do lỗi lưu/khôi phục; backup/restore và truy vết. **Không có DDL/DB/table/row nào được tạo trong lần audit.** Không thêm C1/C2.
''')

    freeze_table = [[key,value] for key,value in [
        ('Schema A',frozen['schema_versions']['a']),('Schema B',frozen['schema_versions']['b']),
        ('Số file output v2 đóng băng',len(frozen['files'])),('Shape A chuẩn hóa',frozen['a_matrix_shape']),
        ('Shape B chuẩn hóa',frozen['b_matrix_shape']),('Sai số lớn nhất oracle A sigma+epsilon',frozen['a_full_oracle_error']),
        ('Sai số lớn nhất oracle B stage Lab',frozen['b_moment_oracle_error']),('Sai số lớn nhất oracle B đủ hai stage',frozen['b_full_oracle_error']),
        ('Số cặp calibration giữ nguyên',frozen['pair_count']),('Median A',frozen['median_a']),('Median B',frozen['median_b']),
        ('Số bảng Top-5 kiểm lại',frozen['ranking_cases_verified']),('Query mới qua hai môi trường: đạt',frozen['new_query_real_workers_verified']),
        ('Unit tests v2 chạy lại, không skip',19),('Thiếu B được xử lý rõ, không zero-fill',frozen['missing_B_verified'])]]
    readiness = [
        ['Số lượng 68 điểm, thứ tự, serialization','EXACT trong phạm vi cấu trúc','Hai file mapping giống nhau; 478→68→136+14; ba raw vector thật tái lập; 42 phép kiểm A2.','Có thể đóng câu hỏi số học và cấu trúc này.'],
        ['Membership của contour gốc','EXACT cho 66/68 điểm thuộc contour','59 điểm ngoài mũi và 7 điểm mũi thuộc contour tương ứng; MP129/358 không có trên sparse NOSE.','Không suy ra canonical mapping hoặc endpoint A2 từ membership.'],
        ['Chuẩn hóa A v2','EXACT về phương trình; có quy ước đã chốt','ddof=0, raw_sigma+1e-8, giữ 150 chiều; query tái sử dụng stats.','Đóng A12 trên v2 trong phạm vi số học.'],
        ['Chuẩn hóa B v2','EXACT về trình tự; có IMPLEMENTATION DETAIL đã duyệt','Chuẩn hóa Lab24 trước concat, sau đó chuẩn hóa toàn bộ 144 chiều; giữ hai stage theo D15, class 1/17 và ngưỡng 100 pixel.','Đóng B12 trên v2 trong phạm vi đã chốt.'],
        ['Pipeline số học A+B','EXACT có điều kiện trên vector v2','Euclid riêng, join ID, cùng 20.000 cặp, median normalization, trọng số 0.5/0.5 và xử lý thiếu B rõ ràng.','Đây là thử nghiệm hai bộ; chưa phải fusion bốn bộ hoặc chứng nhận chất lượng truy hồi.'],
        ['Đối chiếu hình minh họa 68 điểm','DEVIATION so với hình PDF','Trên cùng CFD00001, hai đầu hàm lệch dọc khoảng 34 pixel; thứ tự cao/thấp nhánh sống/đáy mũi ngược hình.','Đã đo sai khác, chưa đủ cơ sở chọn MP index thay thế; giữ nguyên v2.'],
        ['Canonical mapping và endpoint A2','UNVERIFIED','PDF thiếu bảng MP ID; endpoint giải phẫu, định nghĩa tâm mắt và hệ quy chiếu trái/phải còn mở.','Cần chuẩn hoặc annotation có thẩm quyền và xác nhận vai trò của hình trước khi sửa.'],
        ['Ba ảnh dataset vi phạm','DEVIATION đã xác nhận lại','HF00333/HF00561 có mặt phụ; HF00722 che miệng.','Corpus hiện tại chưa đạt; giữ ảnh và lập phương án review theo phiên bản.'],
        ['Ảnh thay thế từ nguồn','UNVERIFIED','Token provenance chưa định vị được nguồn, identity và ảnh thay thế hợp lệ.','Bổ sung repository/revision/shard/hash và nhãn nguồn trước khi thay.'],
        ['CSDL ứng dụng','NOT IMPLEMENTED trong repository','Rà 74 file Python: không có import driver, DB pattern hay file DB/SQL; hiện lưu bằng file.','Cần tác vụ CSDL riêng với schema và kiểm chứng insert/load/query.'],
        ['Toàn hệ thống tuân thủ 100% PDF','NOT READY','Dataset vi phạm, mapping/metadata còn thiếu bằng chứng, tầng CSDL ứng dụng chưa có.','Chưa đủ cơ sở ký nhận toàn hệ thống.']]
    save('PRE_C_READINESS_REPORT.md',f'''# Kết luận sẵn sàng trước Bộ C

{intro}

**Kết luận: A/B v2 là baseline số học có thể tái sử dụng với các giới hạn đã ghi; toàn hệ thống chưa đủ bằng chứng để công nhận 100% tuân thủ PDF.** Nhiệm vụ này không triển khai C1/C2 và không điều chỉnh thuật toán theo Top-5.

## Yêu cầu đã chứng minh và các khoảng trống

{table(['Phạm vi','Trạng thái','Bằng chứng thực tế','Quyết định'],readiness)}

**Sai khác mới được xác nhận:** mapping hiện hành không tái hiện vị trí/topology của hình 68 điểm trong PDF trên cùng CFD00001, đặc biệt đầu hàm và nhánh mũi. Phân loại DEVIATION này giới hạn ở việc đối chiếu minh họa; PDF chưa cho MP ID để xác định mapping thay thế. Canonical MP1/MP4, MP129/358 và endpoint A2 vẫn UNVERIFIED. Chưa phát hiện sai lệch mới ở luồng chuẩn hóa v2.

Các vi phạm ảnh đã biết được mở và xác nhận lại từ ảnh nguồn. Việc rà source xác định rõ tầng CSDL ứng dụng và phần lưu tọa độ hai tâm mắt còn thiếu trong repository; không có bằng chứng để kết luận về một CSDL ngoài phạm vi kiểm tra.

## Đóng băng A/B v2

{table(['Hạng mục kiểm tra lại','Kết quả'],freeze_table)}

[v2_freeze_manifest.json](pre_c_evidence/v2_freeze_manifest.json) ghi hash từng file trong ba thư mục output v2, schema, calibration, hash danh sách cặp ID và kết quả kiểm chứng mới. Đóng băng bằng manifest và hash; không đổi quyền, tên hay nội dung file v2. Source ứng dụng và toàn bộ baseline cũng được so hash lần cuối tại [final_scope.json](pre_c_evidence/final_scope.json).

Oracle dùng phép tính scalar/fsum trên toàn bộ A/B; kiểm riêng stage Lab24 và stage cuối 144 chiều của B. Giữ ID và thứ tự của 20.000 cặp calibration cũ, tính lại độc lập dA, dB và hai median; chín bảng xếp hạng khớp kết quả đã lưu. Query mới chạy worker A trong `.venv311` và worker B trong `.venv-uniface`, kiểm đúng stats/version/hash và hai stage B. Output mới chỉ ghi trong `pre_c_evidence/`. Cả 19 unit tests v2 chạy lại đạt, không skip. Không fit lại stats/median hay ghi lại artifact đã nghiệm thu.

Query fixture là bản PNG mã hóa lại của CFD00001, cùng pixel nhưng khác hash byte. Nó kiểm chứng đường đi dành cho ảnh chưa có hash trong gallery qua hai môi trường; không đại diện cho độ chính xác trên khuôn mặt chưa từng xuất hiện. Thử nghiệm thiếu B kiểm riêng HF00209 và xác nhận không có vector zero-fill.

## Quy ước triển khai được giữ hợp lệ trong phạm vi hiện có

A dùng epsilon=1e-8, ddof=0; B giữ hai stage theo quyết định D15 của v2. Các quy ước HS12×4, Hue10, L1, Lab Pearson, circular moments, class 1/17, raw mask, ngưỡng 100 pixel và xử lý thiếu B giữ theo quyết định v2 đã ghi. Lần kiểm toán này không phát hiện xung đột mới với PDF trong phạm vi đó; không nâng các thông số PDF chưa chốt thành nguyên văn báo cáo.

ID, hash file, row mapping và trọng số 0.5/0.5 thuộc quy trình thử nghiệm đã công khai. Tâm sáu mốc mí, EAR, endpoint A2 và hệ quy chiếu trái/phải vẫn là quy ước hiện hành cần xác minh ý nghĩa giải phẫu.

## Hành động cần thiết trước khi ký nhận toàn hệ thống

1. Chốt canonical mapping, endpoint và hệ quy chiếu trái/phải có thẩm quyền. Đối chiếu mốc và 14 A2 với annotation độc lập, đặc biệt mũi, cao mặt, gò má, gonion và độ mở mí. Không lựa chọn theo Top-5.
2. Giải quyết vi phạm corpus theo quy trình review và version có truy vết, giữ bản cũ. Xác minh nguồn, identity và tiêu chí của ảnh thay thế trước khi lập manifest thay thế.
3. Bổ sung provenance cho thống kê người, cảm xúc, tuổi; quy trình alignment/encoder/crop; camera, dung sai và metadata mắt. Không ép số liệu hoặc suy đoán nhãn từ ảnh.
4. Triển khai CSDL trong nhiệm vụ riêng theo PDF: khóa ảnh/người, tọa độ mắt, version vector và trạng thái thiếu feature. Kiểm thử thực tế insert/load/query, khôi phục dữ liệu và đối chiếu round-trip.
5. Nếu đánh giá chất lượng truy hồi, cần nhãn relevance và quy trình đánh giá độc lập với dự đoán. Test công thức không thay thế nhãn đánh giá.

## Phạm vi có thể dùng để chuẩn bị đầu vào C mà không nhận nhầm chứng nhận

| Có thể tái sử dụng làm baseline kỹ thuật | Điều kiện phải mang theo | Chưa được suy ra |
|---|---|---|
| A150/B144 v2, stats/schema/fingerprints, calibration thử nghiệm, ID mapping | Giữ nguyên hash/version; join bằng ID; giữ trạng thái thiếu B và cờ dataset | Toàn corpus hoặc mapping giải phẫu đã đạt PDF. |
| 1438 ảnh gốc và metadata làm nguồn thực nghiệm đã định danh | Giữ cờ vi phạm/UNVERIFIED riêng; ảnh và version mới phải có lineage | Mọi ảnh đạt một mặt/chính diện/không che hoặc đủ B. |
| Giao 1437 ID đủ A/B cho thử nghiệm fusion sau này | Không zero-fill; tạo calibration version mới nếu đặc trưng/tập ID đổi; phân biệt thử nghiệm với fusion chính thức | Đã có C1/C2, vector 854 chiều hoặc DBMS. |
| Interface và mapping hiện có để thiết kế hợp đồng dữ liệu, đánh giá | Nêu rõ endpoint A chưa được chốt; ROI cho C1 cần review theo PDF trước khi công nhận | Mọi landmark hiện tại đều là canonical hoặc ROI giải phẫu đã được chứng nhận. |

Đây là **khả năng tái sử dụng baseline kỹ thuật có điều kiện**. Nếu cần ký nhận hệ thống tuân thủ trước khi triển khai C chính thức, mapping, dataset và CSDL vẫn còn các điều kiện chưa đạt. Nhiệm vụ hiện tại không tạo feature, code, vector hay calibration cho C.

## Báo cáo và bằng chứng

- [A_MAPPING_FINAL_REVIEW.md](A_MAPPING_FINAL_REVIEW.md)
- [DATASET_FINAL_REVIEW.md](DATASET_FINAL_REVIEW.md)
- [DATABASE_COMPLIANCE_REVIEW.md](DATABASE_COMPLIANCE_REVIEW.md)
- [created_files_manifest.json](pre_c_evidence/created_files_manifest.json) liệt kê hash các file mới, trừ chính manifest này.

Lệnh PowerShell đã chạy thành công từ thư mục gốc repository:

```powershell
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/pre_c_tools/review_mapping.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/pre_c_tools/review_pdf_illustration.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/pre_c_tools/review_storage_dataset.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/pre_c_tools/freeze_v2.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/pre_c_tools/write_reviews.py
```

Worker query đã chạy với `--output docs/audits/pre_c_evidence/new_query_a` và `new_query_b`. Hash PDF và {authority['protected_files']} file baseline được kiểm tra trước/sau. Phạm vi loại trừ môi trường ảo, bytecode và browser profiles được ghi rõ ở [authority.json](pre_c_evidence/authority.json); đây là kiểm tra repository, không phải điều tra CSDL ngoài dự án.
''')

    baseline = read_json(E / 'baseline_before.json')
    changed = [name for name, expected in baseline.items() if not Path(name).is_file() or digest(name) != expected]
    assert not changed, changed
    output_reports = ['A_MAPPING_FINAL_REVIEW.md', 'DATASET_FINAL_REVIEW.md',
                      'DATABASE_COMPLIANCE_REVIEW.md', 'PRE_C_READINESS_REPORT.md']
    for name in output_reports:
        assert '23/11/2026' in (DOC / name).read_text(encoding='utf-8')
    write_json(E / 'final_scope.json', dict(status='PASS', protected_files_checked=len(baseline),
        changed_existing_files=changed, frozen_v2_output_files=len(frozen['files']),
        mapping_changed=False, a2_changed=False, new_database_created=False, c1_c2_implemented=False,
        mapping_illustration_difference_confirmed=True, canonical_mp_mapping_verified=False,
        output_reports=output_reports, full_system_compliance=False,
        readiness='REUSABLE_NUMERIC_BASELINE_WITH_LIMITS; FULL_COMPLIANCE_NOT_READY'))
    new_paths = [DOC / name for name in output_reports]
    for directory in [E, DOC / 'pre_c_tools']:
        new_paths += [p for p in directory.rglob('*') if p.is_file() and p.name != 'created_files_manifest.json']
    write_json(E / 'created_files_manifest.json', dict(self_excluded=True, files=[
        dict(path=str(p.relative_to(ROOT)), sha256=digest(p), bytes=p.stat().st_size) for p in sorted(new_paths)]))
    print(json.dumps(dict(status='PASS', reports=4, existing_files_unchanged=len(baseline),
        v2_files_frozen=len(frozen['files']), canonical_mapping_verified=False,
        application_database_implemented=False, full_system_compliance=False), indent=2))


if __name__ == '__main__':
    main()
