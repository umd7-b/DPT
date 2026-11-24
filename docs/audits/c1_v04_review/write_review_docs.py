"""Write pending human decision records and review instructions; never approve."""
from pathlib import Path
import json

import build_review as bundle


DECISIONS = [
    ('D01', '15 MP phụ trợ vùng trán',
     '§2.4: chia4 vùng dựa landmarks. §2.2: A dùng478→68. PDF không cho danh sách MP riêng của C1.',
     'Giữ15 upper FACE_OVAL MP127,162,21,54,103,67,109,10,338,297,332,284,251,389,356; không thêm vào A150.',
     '14 cạnh liên tiếp thuộc FACE_OVAL native; hash topology và source archive đã xác thực.',
     'Membership mô hình không chứng minh đây là canonical anatomical boundary hoặc auxiliary478 đã được nhóm chấp nhận cho C1.',
     'Tác giả/đại diện nhóm xác nhận diễn giải PDF; reviewer CV/giải phẫu được chủ dự án chỉ định đánh giá ảnh.'),
    ('D02', 'Upper FACE_OVAL có đại diện vùng trán',
     'PDF gọi vùng trán và lông mày; không định nghĩa hairline, extent hoặc vertex.',
     'Dùng upper FACE_OVAL làm upper boundary ổn định; không coi nó là đường chân tóc hay toàn bộ trán.',
     'Overlay CFD/HF cho thấy arc nằm dưới chân tóc ở một số mẫu; census chỉ chứng minh hình học.',
     'Thiếu annotation trán/hairline và tiêu chí mức cắt bỏ chấp nhận được.',
     'Tác giả chốt ý nghĩa vùng trán; reviewer có thẩm quyền đánh giá annotation/mức coverage.'),
    ('D03', 'Native lower eyebrow v0.4',
     'PDF yêu cầu vùng trán+lông mày, không chốt contour trên/dưới hoặc margin.',
     'Lower chain MP276,283,282,295,285,55,65,52,53,46; offset0; upper chain giữ nguyên.',
     'Topology8 cạnh lower EYEBROW; proxy pixel đủ1436 ảnh, HF198 thiếu3px/HF267 thiếu1px.4 native point ngoài biên.',
     'Proxy20 điểm không phải pixel annotation mô mày; zero margin chưa được tác giả nghiệm thu.',
     'Reviewer anatomy/CV được chỉ định và tác giả nhóm xác nhận boundary/margin.'),
    ('D04', 'Cạnh nối thái dương và glabella',
     'PDF không định nghĩa graph polygon hay cách nối giữa hai contour.',
     'Cạnh MP356→MP276, MP285→MP55 và MP46→MP127; nối thẳng theo thứ tự contract.',
     'V0.2 có4 crossing cạnh nội bộ; v0.3 còn HF198 do offset; v0.4 đơn giản5752/5752 ROI.',
     'Các bridge không phải native anatomical contour; cần xác minh side tissue và phần cắt bỏ, kể cả HF55/HF198/HF267/HF463.',
     'Reviewer có chuyên môn giải phẫu/CV theo ủy quyền; tác giả xác nhận diễn giải ranh.'),
    ('D05', 'Ranh giới hai má và mũi–miệng',
     'PDF chỉ cho tên3 vùng này và dựa landmarks, không cho vertex/margin/đường phân cách.',
     'Giữ12 đỉnh mỗi vùng của v0.2, offsets0.08/0.06D và±0.05D; MP129/358 làm nose-side proxy.',
     'Ba vùng mask bitwise không đổi toàn kho; eye/lips/oval memberships có source. MP129/358 không thuộc sparse NOSE.',
     'Thiếu canonical nose-side/cheek endpoints và annotation khi biểu cảm; khác biệt A với hình PDF không tự cho phép sửa A.',
     'Tác giả nhóm chốt endpoint interpretation; reviewer anatomy/CV thẩm định ảnh.'),
    ('D06', 'Hệ quy chiếu trái/phải',
     'PDF gọi má trái/phải; không nêu frame người xem hay người trong ảnh.',
     'Contract viewer/code-left/right, x sang phải/y xuống; API eye/brow names có thể ngược phía người xem.',
     'Mapping và overlays ghi A68/MP rõ ràng; hai nhóm mắt dùng mean6 float32 hiện hành.',
     'Không có quyền tự diễn giải anatomical-left thành viewer-left; reviewer phải chọn frame và mô tả mapping.',
     'Tác giả/đại diện nhóm xác nhận frame; người quản trị dữ liệu ghi nhận convention được duyệt.'),
    ('D07', 'Overlap độc lập',
     'PDF nêu4 vùng độc lập, chưa chốt disjoint pixels hay independent pooling.',
     'Raw membership riêng; shared pixels được giữ ở mọi vùng chứa chúng; không priority subtraction.',
     'Toàn kho overlap91…208px, chỉ má–mũi/miệng; inclusion-exclusion và mask hashes đã kiểm.',
     'Số học không quyết định nghĩa độc lập trong báo cáo; cần tác giả chấp thuận interpretation.',
     'Tác giả nhóm xác nhận interpretation; reviewer phương pháp xác nhận ghi nhận version.'),
    ('D08', 'Tóc/tay/kính/vải và missing',
     '§1.2–1.3 có tiêu chí ảnh/che khuất; §2.4 chưa quy định occlusion mask hay ngưỡng min-support của C1.',
     'Không tự skin-intersect/inpaint/crop; invalid hoặc<64 support →missing theo rule kỹ thuật hiện hành. Occlusion có phiếu riêng.',
     'HF311/55 có tóc, HF198/694 kính, HF209/694 khăn, HF722 tay; hair model mask không phải ground truth.',
     'Chưa chốt mức che khuất/tissue contamination và khi nào semantic rejection trở thành missing. Dataset vi phạm không hết vì ROI hợp lệ.',
     'Tác giả/chủ dataset chốt tiêu chí; reviewer được chỉ định đánh giá và adjudicate các ca occlusion.'),
]


def write_new(path, text):
    with path.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)


def main():
    manifest = bundle.source.read_json(bundle.OUT / 'review_manifest.json')
    records = []
    for key, title, pdf, proposed, basis, limits, authority in DECISIONS:
        records.append(dict(decision_id=key, topic=title, PDF_actual_requirement=pdf,
            proposed_implementation_convention=proposed, evidence_basis=basis, limitations=limits,
            authority_role_needed=authority, authority_person_or_confirmed_source='',
            authority_evidence_path='', authority_evidence_sha256='', decision_date='',
            decision_status='PENDING_AUTHORITY_REVIEW', decision_notes=''))
    bundle.source.save_csv(bundle.OUT / 'decision_register.csv', records)
    bundle.source.write_json(bundle.OUT / 'decision_register.json', dict(schema_id='C1_V04_PENDING_DECISION_REGISTER_v1',
        decisions=records, confirmed_authorities=0, decisions_accepted=0,
        agent_observations_are_not_authority_decisions=True))
    mandatory = '| ID bắt buộc | Lý do chọn |\n|---|---|\n'
    for row in manifest['images']:
        if row['mandatory']: mandatory += '| ' + row['image_id'] + ' | ' + '; '.join(row['selection_reasons']) + ' |\n'
    protocol = f'''# C1 v0.4 — protocol review giải phẫu và ghi nhận chứng cứ

Ngày tạo: **24/11/2026**, Asia/Saigon. Hồ sơ chờ đánh giá của con người.
**800/800 dòng NOT_REVIEWED**, reviewer/date trống,0 quyết định có thẩm quyền, không kích hoạt v0.4.

## Nguồn và phạm vi

Thẩm quyền yêu cầu cao nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã kiểm trực tiếp.
Đã đọc các audit remediation/anatomical validation/mapping/full-corpus và hai spec hiện hành.
PDF §2.2/§2.4 được đọc trực tiếp bằng pypdf có sẵn; bản trích và hai hình trang8 trong
[reference/](c1_v04_review/reference/). Snapshot hình PDF chỉ là tham chiếu, không phải canonical MP-ID table.

Contract v0.2 content SHA: `{bundle.PINS[bundle.V02]}`.
Candidate v0.4 content SHA: `{bundle.PINS[bundle.V04]}`. Cả hai được tính lại canonical JSON, loại field content_sha256.
V0.4 giữ `active=false`. Không sửa vertex, offsets, frame, PDF, A/B, calibration, SQLite hoặc trial100 cũ.
P8,R2,threshold>=,NRI59,L1 riêng,Chi-square0.5,gray/bilinear/bit-order/codebook đã khóa giữ nguyên.
Không gọi LBP/HOG hay tạo vector; chỉ raster lại ROI cho100 ảnh và đối chiếu hash census đã đóng băng.

## Tập review100 ảnh

**50 CFD+50 HF**, gồm **18 ID bắt buộc** và82 ảnh lấy mẫu phần còn lại.
Seed `{manifest['seed']}`; `random.Random(seed).sample` trên pool ID đã sort, lần lượt CFD rồi HF,
bù đủ50 mỗi nguồn sau khi chọn mandatory. Không dùng ranking, distance hoặc kết quả tìm kiếm để chọn.
Danh sách đầy đủ, lý do, extrema values và source hashes:
[review_manifest.json](c1_v04_review/review_manifest.json).
Đây là mẫu pha mandatory/risk/extrema với lấy mẫu ngẫu nhiên bổ sung, không phải100 ảnh random thuần
hay mẫu đủ để chứng nhận1438 ảnh về giải phẫu.

{mandatory}
Extrema đã lấy cả diện tích liên tục lẫn số raw pixels, cho cảv0.2/v0.4:
forehead nhỏ nhất CFD00112; lớn nhất v0.2 CFD00529; lớn nhất v0.4 HF00082.
Bốn lỗi v0.2 và bốn native-node exceptions có phần trùng ID; không hiểu đây là8 ảnh khác nhau.

## Xem bằng chứng

Mở [index.html](c1_v04_review/index.html) trong trình duyệt cục bộ; lọc ID/lý do rồi nhấn từng ảnh.
Mỗi trang có ảnh gốc sao chép nguyên bytes, overlay hai contract, overlay toàn bộ68 điểm với bảng A68→MP,
các MP phụ trợ,8 raw mask PNG (4 mỗi contract),4 ảnh đổi pixel và binary added/removed masks.
Contact sheet tổng quan có4 raw masks v0.4; trang chi tiết có cả mask v0.2.
Màu mask độc lập, không trừ overlap. Chấm đỏ/cross ở native brow ngoài v0.4 chỉ là model-proxy finding.
V0.2 self-cross được vẽ đỏ và mask chỉ dùng chẩn đoán; không coi đó là một vùng valid để trích LBP.
Added=green,removed=red; ba vùng còn lại không thay pixel. Nhấn ảnh để xem đúng độ phân giải.

`evidence.json` từng ảnh ghi measurements, hash ảnh/landmark row, source index, điểm liên quan ngoài polygon,
pixel changes và các quan sát trước đây. [landmark_membership.csv](c1_v04_review/landmark_membership.csv)
ghi containment cho A68 và MP liên quan: điểm A68 ngoài một vùng khác không tự là lỗi;
điểm source chưa offset có thể nằm ngoài vì offset eye/cheek có chủ đích. Không đánh đồng với vertex sai.
Quan sát tóc/kính/khăn/tay lấy từ hồ sơ trước được ghi rõ **prior agent observation**, không phải annotation
hoặc quyết định của reviewer. Các ảnh chưa có quan sát ghi NO_PRIOR_OBSERVATION_RECORDED,
không phải clearance không che khuất. Reviewer phải tự điền occlusion_observation.

## Phiếu đánh giá

[review_annotations.csv](c1_v04_review/review_annotations.csv): **100×4×2=800 dòng**,400 dòng cho mỗi contract.
Khóa duy nhất `(image_id,roi_name,contract_version)`; không gộp accept v0.2 và v0.4 dù ba mask giống nhau.
`geometry_status` và hash/evidence metadata là dữ liệu frozen, độc lập với anatomy_review_status.
Tất cả reviewer/date/reason/decision_notes/occlusion observation/bằng chứng quyết định ban đầu trống.

| Nội dung cần người review trả lời | Cột | Giá trị |
|---|---|---|
| Có bao phủ đúng phần được mô tả? | covers_described_anatomy | YES/NO/UNCERTAIN/NOT_ANSWERED |
| Có cắt mất phần quan trọng? | cuts_important_part | như trên |
| Có quá nhiều tóc/nền/vải/kính/tay? | excess_non_target_material | như trên; mô tả vật thể và vị trí ở notes |
| Ranh giới hợp lý với biểu cảm đang thấy? | expression_boundary_reasonable | như trên; không chứng nhận temporal stability từ ảnh đơn |
| Có landmark cần đối chiếu hình PDF? | pdf_landmark_verification_needed | như trên; ghi A/MP ID ở notes |
| Trái/phải hiểu theo ai? | left_right_reference | VIEWER/IMAGE_SUBJECT/UNCERTAIN/NOT_ANSWERED |

Contract dùng **VIEWER**; người review hiểu theo người trong ảnh phải ghi IMAGE_SUBJECT và giải thích quan hệ,
không tự đổi tên cột, thứ tự vùng hoặc vector. Geometry không quyết định anatomy status tự động.

`anatomy_review_status` chỉ nhận **ACCEPT,REJECT,UNCERTAIN,NOT_REVIEWED**; mặc định NOT_REVIEWED.
ACCEPT là kết luận con người trên **một ảnh/một ROI/một hash contract**, không chấp nhận toàn hệ thống.
REJECT phải có lý do/vị trí; UNCERTAIN dùng khi thiếu chứng cứ hoặc cần tác giả/annotation;
NOT_REVIEWED nghĩa chưa có đánh giá, không thay bằng dự đoán detector hoặc nhận xét Agent.
Không có ngưỡng proxy coverage tự động chuyển thành ACCEPT. Cả người review cũng không được dùng Top-5 để chọn ROI.

## Ghi nhận thẩm quyền và quyết định

1. Chủ dự án/tác giả chỉ định người review, vai trò và phạm vi; lưu tài liệu chỉ định/ký xác nhận có thể kiểm tra.
   [reviewer_authorities.csv](c1_v04_review/reviewer_authorities.csv) ban đầu chỉ có header, không bịa tên người.
2. Giữ template bất biến; sao chép CSV và register sang **namespace round mới** (ví dụ `review_submissions/round_01/`).
   Ghi `reviewer`, ngàyISO YYYY-MM-DD, sáu câu trả lời, quan sát che khuất, reason/decision_notes.
   Nếu có nhiều reviewer, lưu file riêng theo reviewer/round, giữ cả disagreement thay vì ghi đè nhau.
3. `reviewer_authority_evidence` phải trỏ văn bản chỉ định khớp register; register ghi role, hash tài liệu và
   authority_confirmation_status do chủ dự án xác nhận. Không dùng tên Agent hoặc output model làm thẩm quyền.
4. `decision_evidence_path`/SHA phải trỏ biên bản/ghi chú ký nhận hoặc bằng chứng quyết định có nguồn gốc.
   `evidence_path` chỉ là hình review; không dùng trang polygon làm bằng chứng đã chấp thuận.
   Ghi rõ contract content hash, ID ảnh/ROI, người, ngày, phạm vi, lý do và nguồn viện dẫn trong biên bản.
5. Với các quyết định convention ở D01–D08, ghi kết luận được ủy quyền vào **bản register round mới**,
   authority person/source, ngày, đường dẫn/hash evidence và phạm vi/điều kiện. Không lấy nhận xét Agent làm quyết định.
   Tranh chấp/REJECT/UNCERTAIN cần adjudication có người chịu trách nhiệm; không xóa ảnh khó khỏi manifest.

Validator chỉ đọc file; kiểm đủ800 khóa, metadata/hash, enum, tên/ngày, câu trả lời và evidence refs đối với
các dòng đã review. Nó **không xác thực danh tính, chữ ký, tính thật của văn bản ủy quyền hoặc tự cấp approval**.
Project owner vẫn phải kiểm nguồn văn bản và xác nhận thẩm quyền. Các proposed gate trong readiness cũng
phải được chủ dự án chấp nhận; báo cáo này không tự thay người nghiệm thu.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py
# Với một round do con người thực hiện, dùng đường dẫn CSV/register của round đó:
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py --annotations <round.csv> --authority-register <authorities.csv> --evidence-base <thu_muc_chua_evidence>
```

Lệnh đầu đã chạy PASS với800 NOT_REVIEWED,0 human reviews. Lệnh có placeholder chỉ là hướng dẫn tương lai,
không được ghi là một human review đã thực hiện. Case evidence_path phải còn resolve trong evidence-base;
nếu dùng round ở nơi khác, mirror/link cấu trúc contact_sheets và lưu nguồn gốc, không sửa immutable evidence fields.

## Bảo toàn và bước tiếp theo

Kiểm800 raw mask round-trips,800 binary diff,100 source image hashes và8 tests về enum/provenance/selection.
[verification.json](c1_v04_review/verification.json), [tests.log](c1_v04_review/tests.log).
Baseline trước đợt này **{manifest['protected_file_count']} file**, gồm toàn bộ trial100, hai contract, A/B,
dataset/PDF/SQLite và remediation cũ. Các hash phải không đổi trước/sau; evidence tại
[baseline_before.json](c1_v04_review/baseline_before.json), [final_scope.json](c1_v04_review/final_scope.json).

[Decision register](C1_V04_DECISION_REGISTER.md) và [approval readiness](C1_V04_APPROVAL_READINESS.md)
ghi rõ phần còn thiếu và điều kiện tương lai. Việc tạo hồ sơ không kích hoạt contract, không tính C1,
không chỉnh thuật toán, không chứng nhận anatomy100% từ100 ảnh.
'''
    write_new(bundle.ROOT / 'docs/audits/C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md', protocol)
    tables = ''
    for row in records:
        tables += f'''\n## {row['decision_id']} — {row['topic']}

| Hạng mục | Nội dung |
|---|---|
| PDF thực sự quy định | {row['PDF_actual_requirement']} |
| Quy ước được đề xuất | {row['proposed_implementation_convention']} |
| Căn cứ geometry/topology/ảnh | {row['evidence_basis']} |
| Giới hạn còn thiếu | {row['limitations']} |
| Vai trò cần xác nhận (đề xuất, chưa chỉ định) | {row['authority_role_needed']} |
| Người/nguồn có thẩm quyền thực tế | **Chưa ghi nhận** |
| Ngày, đường dẫn/hash bằng chứng xác nhận | **Trống** |
| Trạng thái | **PENDING_AUTHORITY_REVIEW** |
'''
    decision_doc = '''# C1 v0.4 — sổ quyết định chờ xác nhận

Ngày tạo24/11/2026, Asia/Saigon. **8 quyết định chưa duyệt;0 người có thẩm quyền/biên bản chấp thuận được ghi nhận.**
Các mô tả và proposed roles dưới đây là nội dung để người có thẩm quyền xem xét, không phải quyết định của họ.
Không tự đánh dấu approval từ nhận xét Agent, topology membership hay geometry5752/5752.

Nguồn cao nhất là PDF đã hash trong [protocol](C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md).
Endpoint/topology evidence có tại C1_ANATOMICAL_VALIDATION.md và C1_ROI_REMEDIATION_REPORT.md;
không dùng những audit đó như chữ ký nghiệm thu. Dữ liệu register:
[CSV](c1_v04_review/decision_register.csv), [JSON](c1_v04_review/decision_register.json).
Mọi authority name/date/evidence hiện trống. Khi con người quyết định, ghi vào bản round mới,
giữ snapshot này và liên kết biên bản có thẩm quyền/hash; không tự sửa PDF theo code.
''' + tables + '''
## Cách đóng một quyết định

Người/nguồn có thẩm quyền phải được chủ dự án xác minh phạm vi ủy quyền. Ghi rõ kết luận,
contract/hash và điều kiện áp dụng, ngày, người, biên bản và SHA-256. Tài liệu phải cho thấy sự xác nhận
thực tế; một URL topology, screenshot polygon hoặc tên reviewer không đủ. Lưu cả rejection/disagreement.
Trạng thái của bản round chỉ chuyển theo kết luận thực tế, ví dụ ACCEPTED_WITH_AUTHORITY_EVIDENCE,
REJECTED_WITH_AUTHORITY_EVIDENCE hoặc UNCERTAIN_REQUIRES_EVIDENCE; snapshot này giữ PENDING.

Không quyết định nào được phép thay P8,R2,threshold>=,59 bins,L1,Chi-square0.5 hoặc sửa PDF để khớp code.
Nếu convention được yêu cầu sửa, tạo candidate/version/hash mới và audit lại; không ghi đè v0.2/v0.4 cũ.
'''
    write_new(bundle.ROOT / 'docs/audits/C1_V04_DECISION_REGISTER.md', decision_doc)
    readiness = f'''# C1 v0.4 — trạng thái sẵn sàng cho nghiệm thu có bằng chứng

Ngày24/11/2026, Asia/Saigon. **REVIEW_PACKAGE_READY — HUMAN_REVIEW_PENDING**.
Candidate vẫn **GEOMETRY_VALIDATED / ANATOMY_PROVISIONAL**, `active=false`.
Đã tạo công cụ/hình review; chưa có con người đánh giá hoặc bằng chứng chấp thuận trong hồ sơ này.

| Hạng mục | Điều đã chứng minh / trạng thái hiện tại |
|---|---|
| Hash contract | v0.2 `{bundle.PINS[bundle.V02]}`; v0.4 `{bundle.PINS[bundle.V04]}`; canonical hash khớp |
| Geometry toàn kho từ audit trước | v0.2 5748/5752 valid,4 tự giao; v0.4 5752/5752 valid,0 self-cross/support<64/out-of-image |
| Tính bất biến vùng | Ba vùng má/mũi-miệng không đổi mask; forehead đổi trên1438 ảnh; chưa tạo vector với ROI mới |
| Proxy mày | v0.4 1436/1438 đủ integer proxy; HF198 thiếu3px,HF267 thiếu1px;4 native points ngoài polygon |
| Anatomy | Bốn vùng ở cả1438 ảnh chưa có đủ anatomical annotation/clearance có thẩm quyền |
| Bộ review mới | 100 ảnh50CFD/50HF,18 mandatory+82 random fill;100 source copies,800 raw masks và binary diffs |
| Phiếu | 800 NOT_REVIEWED,0 ACCEPT/REJECT/UNCERTAIN;400 rows candidate và400 comparison |
| Quyết định PDF chưa chốt | D01–D08 đều PENDING_AUTHORITY_REVIEW; không có người/nguồn xác nhận thực tế |
| Bảo toàn | Baseline{manifest['protected_file_count']} file trước đợt này; các hash cũ phải giữ nguyên |
| Triển khai | Không kích hoạt v0.4,không tính lại96 vector trial cũ,không chạy C1 toàn kho,C2 hoặc fusion |

Geometry/proxy coverage không đủ chứng minh anatomy. Các vấn đề dataset HF333/HF561 mặt phụ,
HF722 tay che vẫn giữ; HF209 thiếu tóc B không tự là lỗi dataset hoặc thiếu C1,HF694 phụ kiện vẫn cần review.
Không suy đoán person_id/tuổi/giới, không sửa/crop/inpaint nguồn ảnh.

## Điều kiện đề xuất để xem xét kích hoạt contract mới

Các điều kiện này là **đề xuất protocol chờ project owner chốt**, không phải Agent cấp approval:

1. Xác minh reviewer/tác giả/đại diện nhóm có thẩm quyền và phạm vi; lưu ủy quyền/biên bản có hash.
   Người có thẩm quyền chốt D01–D08 đúng yêu cầu rõ của PDF, có evidence; quyết định không được trái công thức PDF.
2. Hoàn thành review400 ROI candidate trên100 ảnh, trả lời sáu prompts, ghi occlusion và đối chiếu ảnh/PDF.
   Mọi REJECT/UNCERTAIN phải được adjudicate hoặc có policy missing/exclusion được phê duyệt và version hóa;
   không xóa ca khó khỏi manifest hoặc ép mọi ảnh thành ACCEPT. Lưu độc lập review v0.2 nếu có.
3. Xác minh annotation anatomy: extent trán/mày,temple/glabella bridges,má/mũi-miệng,frame trái/phải,
   bốn continuous-node cases và tiêu chí tóc/nền/tay/kính/vải. Nếu cần sửa ROI,tạo version khác rồi audit lại;
   không sửa trực tiếp v0.4 hoặc mapping A.
4. Đánh giá độ đủ của review100 theo protocol do người có thẩm quyền xác nhận.100 ảnh không tự đủ để
   chứng nhận cả1438 anatomy-valid;1338 ảnh ngoài bộ này chưa được reviewer của bộ này xem xét.
   Các quan sát Agent ở audit trước không thay annotation/ủy quyền cho bộ mới.
5. Biên bản activation phải bind đúng content/file/geometry hashes,schema,dataset version,policy và phạm vi,
   nêu giới hạn và bên chịu trách nhiệm. Lưu activation record/registry mới bên ngoài candidate đã đóng băng,
   không sửa cờ active trong snapshot hoặc thay PDF theo implementation. Thao tác activation cần nhiệm vụ
   được giao riêng sau khi có evidence; công cụ ở đây không có chức năng activation.

Các bản form và register ban đầu giữ nguyên; review con người phải được lưu trong round/namespace mới.
Validator PASS chỉ chứng minh cấu trúc/hash/reference, không xác thực chữ ký,identity hay cấp chấp thuận.

## Điều kiện tính C1 lại trên100 ảnh — chỉ cho nhiệm vụ tương lai

Cần ủy quyền chạy technical trial mới cùng contract/hash đã được quyết định cho phạm vi thử nghiệm,
policy missing/occlusion và namespace mới; đây là quyết định riêng với activation production.
Giữ exact seed/manifest review hoặc manifest100 được chốt trước,không chọn theo Top-5.
Adapter/context cho hash ROI mới phải được version hóa riêng,giữ nguyên kernel số học đã kiểm:
P8,R2,>=,NRI59,L1 riêng,Chi-square0.5 và gray/bilinear/bit/codebook/support21 hiện hành.
Chỉ reuse landmarks có provenance; nếu thiếu nguồn,dừng rõ thay vì tự align/detect theo giả định.
Kiểm counts/dtype/dimension,L1 và scalar oracle độc lập,query/gallery hashes,negative/missing cases,
đối chiếu baseline trước/sau. Không sửa expectation về số vector để che rejection/occlusion;
trial100 v0.2 và96 vector cũ vẫn nguyên hash,không đưa vector thử nghiệm vào SQLite production.
Chưa thực hiện bất kỳ bước trích xuất nào trong nhiệm vụ hồ sơ này.

## Điều kiện tính C1 toàn bộ1438 ảnh — chỉ cho nhiệm vụ tương lai

Ngoài các điều kiện kỹ thuật100 ảnh,phải có quyết định triển khai cho phạm vi1438 và protocol anatomical/
occlusion đủ phạm vi,quyết định dataset có truy vết,adjudication các exception và biên bản nghiệm thu
contract/version phù hợp. Nếu chỉ có sampled review,ghi giới hạn coverage,không dán nhãn100% anatomy compliant.
Audit lại toàn5752 ROI cho version được chọn nếu khác hash hiện hành; khóa nguồn/hash dữ liệu,stats/calibration
A/B không refit; tạo output/version mới,mapping image_id và missing_reason,không zero-fill hoặc ghi đè DB/vector.
Chốt phương án rollback/activation registry và bài kiểm numeric/provenance trước khi giao thực thi riêng.
Không triển khai C2 hoặc fusion dưới phạm vi chấp thuận C1.

## Hồ sơ giao người review

- [Trang bắt đầu100 ảnh](c1_v04_review/index.html) · [Manifest](c1_v04_review/review_manifest.json).
- [Phiếu800 dòng](c1_v04_review/review_annotations.csv) · [Registry reviewer trống](c1_v04_review/reviewer_authorities.csv).
- [Protocol và18 ID bắt buộc](C1_V04_ANATOMICAL_REVIEW_PROTOCOL.md) · [8 quyết định chưa duyệt](C1_V04_DECISION_REGISTER.md).
- [Kiểm chứng](c1_v04_review/verification.json) · [baseline](c1_v04_review/baseline_before.json) · [final scope](c1_v04_review/final_scope.json).

Lệnh thực tế tạo và kiểm hồ sơ tại repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/build_review.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/validate_review.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/verify_bundle.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/write_review_docs.py
.\.venv311\Scripts\python.exe -X utf8 -B docs/audits/c1_v04_review/finalize_review.py
```

Tất cả là thao tác hồ sơ/geometry display. Không có ACCEPT do Agent điền vào CSV,không có chấp thuận
toàn hệ thống hoặc activation được cấp từ việc hồ sơ đã tạo xong.
'''
    write_new(bundle.ROOT / 'docs/audits/C1_V04_APPROVAL_READINESS.md', readiness)
    print('Wrote3 review documents and8 PENDING decisions; no human acceptance recorded', flush=True)


if __name__ == '__main__': main()
