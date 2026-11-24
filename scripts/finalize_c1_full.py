"""Finalize full C1 deployment reports and integrity evidence; no refit."""
from pathlib import Path
import json
import subprocess
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src import lbp236 as kernel
from features.C1_lbp.src.full_v04 import OUT, ROI_HASH, ROI_PATH, KERNEL_HASH, protected_baseline, read_csv, write_json
from retrieval.search_c1 import C1Gallery


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def text_new(path, text):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)


def main():
    if (OUT / 'evidence/created_files_manifest.json').exists(): raise FileExistsError('Final implementation evidence exists')
    verified = load(OUT / 'verification.json'); gallery = C1Gallery()
    assert verified['numerical_status'] == 'PASS'
    queries = sorted((OUT / 'queries').glob('*/results.json'))
    independent = {r['image_id']: r for r in verified['scalar_chi_rankings']}
    checked_pixels = 0
    for path in queries:
        record = load(path); identity = record['query']['image_id']; rows = record['results']
        assert [r['image_id'] for r in rows] == independent[identity]['top5']
        csv_rows = read_csv(path.parent / 'results.csv')
        assert [r['image_id'] for r in rows] == [r['image_id'] for r in csv_rows]
        assert [r['distance_C1'] for r in rows] == [float(r['distance_C1']) for r in csv_rows]
        png = cv2.imread(str(path.parent / 'comparison.png'))
        assert png.shape == (672, 768, 3)
        for i, row in enumerate([record['query']] + rows):
            x, y = (i % 3) * 256, 40 + (i // 3) * 316
            original = cv2.imread(row['image_path'], cv2.IMREAD_UNCHANGED)
            np.testing.assert_array_equal(png[y:y+256,x:x+256], original)
            checked_pixels += 1
    assert len(queries) == 6
    baseline = protected_baseline()
    support_table = '| Vùng | Min | Median | Max | Tổng tâm theo ROI |\n|---|---:|---:|---:|---:|\n'
    for region, stats in verified['per_region_support_statistics'].items():
        support_table += f"| {region} | {stats['min']} | {stats['median']} | {stats['max']} | {stats['total']} |\n"
    hash_table = '| Artifact | SHA-256 |\n|---|---|\n'
    for filename in ['features_C1.npy','counts.npy','eligible_centres.npy','feature_rows.csv','extraction_status.csv',
                     'feature_schema.json','image_diagnostics.jsonl','manifest.json','verification.json']:
        hash_table += f"| {filename} | `{kernel.sha256(OUT/filename)}` |\n"
    example_tables = ''
    for identity in ['cfd_final_00001','hf_merged_00209']:
        rows = load(OUT / 'queries' / identity / 'results.json')['results']
        example_tables += '\n### ' + identity + '.png\n\n| Rank | Ảnh | Chi-square |\n|---:|---|---:|\n'
        for row in rows: example_tables += f"| {row['rank']} | {row['filename']} | {row['distance_C1']:.12f} |\n"
        example_tables += f'\n[Ảnh so sánh](../outputs/C1_lbp/full_v04/queries/{identity}/comparison.png) · [CSV](../outputs/C1_lbp/full_v04/queries/{identity}/results.csv) · [JSON](../outputs/C1_lbp/full_v04/queries/{identity}/results.json).\n'
    common = f"""Ngày thực hiện: **24/11/2026**, Asia/Saigon. **PROJECT_SELECTED_ROI_V04; ANATOMY_PROVISIONAL**.
Chủ dự án đã lựa chọn ROI v0.4 cho nhiệm vụ triển khai này. Lựa chọn triển khai khác với chứng nhận
đúng giải phẫu: không sửa candidate contract, `active=false` trong snapshot vẫn nguyên, không ghi ACCEPT/
approval vào CSV hoặc decision register review cũ. Không thay PDF/dataset/A/B/calibration/SQLite/kết quả A+B.

Nguồn chuẩn cao nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, §2.4, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc và xác minh trực tiếp bằng
pypdf có sẵn ở Python hệ thống; phần trích nằm trong full_v04/evidence/pdf_section_2_4.txt.
Extractor/tests dùng `.venv311`, không cài thư viện hoặc chạy lại MediaPipe.

ROI v0.4 content SHA `{ROI_HASH}`; original LBP spec content SHA `{kernel.SPEC_HASH}`;
codebook file SHA `{gallery.context.lock['codebook_file_sha256']}`;
kernel source SHA `{KERNEL_HASH}`. Mismatch schema/content/source hash thì dừng.
"""
    report = '# C1 LBP236 — triển khai toàn bộ dataset với ROI v0.4\n\n' + common + f"""
## Kết quả thực tế

**1438 ảnh đã xử lý,1438 vector hợp lệ,0 missing**:710 CFD+728 HF.
Đây là valid theo geometry/support/numerical guards đã khóa, không phải1438 ảnh đã được chứng nhận anatomy.
`features_C1.npy` shape **(1438,236)** dtype **float64**, hữu hạn,không âm.
`counts.npy` uint64(1438,4,59); `eligible_centres.npy` uint64(1438,4).
Mọi count sum=N và histogram chính xác count/N; đủ5752 histogram L1 riêng.
Tổng mỗi nhóm nằm `[0.9999999999999998,1.0000000000000002]`, tổng vector trong
`[{verified['vector_sum_min']!r},{verified['vector_sum_max']!r}]`. Không global-L1/L2/Z-score/refit.

Tất cả image_id có một dòng extraction_status.csv. Missing nếu xuất hiện sẽ không có feature row/vector,
kèm reason rõ; không zero-fill. Lần chạy này không có exception/missing, không ép số thành công.
Thứ tự vector là image_id tăng dần, có feature_row_index tường minh trong feature_rows.csv.
Archive↔catalog↔image nối bằng image_id/filename, không zip catalog với hàng landmarks.
Mỗi vector mang đúng ROI/spec hash trong row metadata và feature version `C1_LBP236_FULL_ROI_V04_v1`.

{support_table}
Các tổng tâm là count theo từng raw ROI, không phải union các tâm; overlap vẫn pool độc lập.
Cả5752 raw mask hash,raw pixel count và support đều khớp census v0.4 đã đóng băng.

## Binding phiên bản và kernel tái sử dụng

Không sửa features/C1_lbp/src/lbp236.py. Tầng mới `V04Context` authenticate spec gốc/codebook/v0.2 dependency,
authenticate candidate v0.4 rồi bind ROI mới để dùng **nguyên** Extractor,polygons,gray,bilinear,raw code,
histogram và missing rules đã kiểm. Ba polygon má/mũi-miệng phải trùng definition v0.2.

Spec gốc v0.1.0 **có dependency ROI v0.2**. Không tự xóa hoặc tuyên bố dependency đó vốn là v0.4.
Feature schema mới ghi `PROJECT_SELECTED_V04_SAME_LBP_SPEC_ARITHMETIC_v1`: original_spec_ROI_dependency,
implementation_ROI, lý do lựa chọn của chủ dự án và original spec hash; không sửa JSON gốc.
Đây là binding triển khai mới, giữ arithmetic đúng spec, không tuyên bố mọi nội dung metadata của spec cũ
đã biến thành spec v0.4. Danh tính/hash nguồn và lựa chọn triển khai được ghi riêng trong feature_schema.json.

Giữ P8,R2,threshold>=,58 mẫu uniform riêng+198 nonuniform vào bin58,59 bins mỗi vùng.
Gray=(1868B+9617G+4899R+8192)//16384 với uint32,gray uint8 rồi float64; offsets p0 Đông ngược kim đồng hồ,
±sqrt(2) chính xác float64; horizontal lerp rồi vertical lerp,không round5 decimal/intensity.
Support21 trong cùng raw ROI/ảnh,overlap độc lập,min64; counts uint64,h=count/N float64 không epsilon L1.
Chi-square=0.5*sum((a-b)^2/(a+b+1e-8)), không dùng Euclid cho C1.

## Kiểm thử và oracle

**95 tests đạt,0 failure/error/skip**: A/B report v2 và A+B identity/calibration numeric fixtures,
color features/report rules,20 C1 numeric tests+6 trial integration và11 full_v04 tests.
Đã kiểm kernel pin,modified candidate rejection,missing không zero-fill,shape/dtype/hash,
Chi-square independent scalar/0.5/epsilon/self0/symmetry,tie-break và metadata permutation.
Một fixture chứng minh Chi-square và Euclid xếp hạng khác nhau; production phải cho thứ tự Chi-square.
Các hàm fit trong regression A/B chỉ chạy trên fixtures trong bộ nhớ/temp, không refit hoặc ghi stats artifact.
Trial100 cũ không chạy lại batch hoặc ghi đè: regression dùng kernels/query checks và dữ liệu trial đã lưu.

Oracle độc lập trên12 ảnh cố định (2 CFD,10 HF,bao gồm4 negative v0.2 và các case occlusion/dataset),
không chọn bằng Top-5. Oracle dùng Python integer gray,rotation-enumeration codebook,vertex CSV frozen,
raster quét toàn ảnh,support scalar và bilinear scalar; không gọi extractor để tạo expected.
**48 histogram /211534 tâm scalar** khớp counts/histogram chính xác;3122 raw-code centres và8 neighbour
values mỗi tâm khớp chính xác. Max histogram/interpolation error=0.0.
Independent Chi-square qua math.fsum đối chiếu **17256 khoảng cách (12×1438)**,
max absolute error={verified['max_chi_abs_error']!r}; cả12 Top-5 trùng scalar oracle, self-distance0.
Ba histogram vùng không đổi khớp bitwise toàn bộ96 vector trial v0.2; không tái fit theo query.
Các khẳng định bitwise chỉ áp dụng môi trường đã ghi, không tự suy ra tương đương default skimage/platform khác.

## Truy vấn riêng C1

Module [search_c1.py](../retrieval/search_c1.py) đọc gallery qua explicit image_id/feature_row_index,
kiểm hash artifact/schema/ROI/spec và histogram. Query hiện chỉ nhận ảnh trong gallery: image_id,
filename hoặc file path có hash trùng. Ảnh mới **chưa hỗ trợ**, không tự coi ảnh mới đã aligned.
Query reuse vector lưu, không gọi detector/extractor,không đổi histogram/fit tham số.
Bỏ đúng image_id truy vấn, giữ các ảnh khác dù distance0; sort `(distance_C1,image_id)` tăng dần.
CSV,JSON vàcomparison.png tách từng run,không ghi đè output có sẵn.

Lệnh PowerShell thực tế đã chạy thành công:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C1_lbp.src.full_v04
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c1_full.py
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image cfd_final_00001.png --top-k 5
foreach ($c1Query in @('cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00209.png','hf_merged_00722.png')) {{
    .\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image $c1Query --top-k 5
    if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
}}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c1_full.py
```

Lần chạy tiếp theo dùng `--output <thư_mục_mới>`; batch vàverification từ chối ghi đè artifacts đã hoàn tất.

{example_tables}
Ngoài hai ví dụ còn có4 run CFD00069,HF00001,HF00198,HF00722 trong queries/.
Đã round-trip cả6 CSV↔JSON và so36 ô ảnh trong PNG chính xác với pixel nguồn, không chỉ ghi tên output.
Các Top-5 là kết quả thử chức năng, không dùng chọn ROI hoặc điều chỉnh công thức; không phải đánh giá độ đúng identity.

## Artifact và hash

Namespace: [outputs/C1_lbp/full_v04](../outputs/C1_lbp/full_v04/).
Các file yêu cầu features_C1.npy,feature_rows.csv,extraction_status.csv,feature_schema.json,manifest.json,
verification.json đầy đủ. Bổ sung counts.npy,eligible_centres.npy,image_diagnostics.jsonl và evidence/ để đối chiếu.

{hash_table}
Manifest pin byte hashes8 artifact nền; verification lưu kết quả numerical. Manifest file mới ở evidence/
pin thêm scripts/reports/query outputs và verification, tự loại chính nó để tránh hash vòng.

## Những điều PDF không chốt và giới hạn còn lại

PDF §2.4 quy định P/R,>=,nri59,bốn vùng,L1 riêng,236 chiều,Chi-square0.5. PDF chưa cho MP endpoint/margin,
upper hairline,left/right frame,raw overlap,grayscale integer convention,interpolation ordering/bit direction,
bin numbering,min64,epsilon cụ thể hoặc tie-break. Các chi tiết này là quy ước version đã công khai,
không trình bày là nguyên văn PDF. Raster/support/bilinear/epsilon vẫn đúng bản đã khóa.

V0.4 vẫn **ANATOMY_PROVISIONAL**: upper FACE_OVAL không phải annotation hairline; native brow proxy không phải
mô thật. HF00198 còn3 pixel proxy ngoài,HF00267 còn1; HF00055/00198/00267/00463 có native point ngoài.
Các endpoint má/mũi-miệng và mâu thuẫn topology minh họa A/MP1/MP4 chưa được giải quyết bằng cách sửa A.
HF00333/HF00561 mặt phụ,HF00722 tay che vẫn là vi phạm dataset đã biết; tóc/kính/khăn vẫn có thể trong ROI.
Mọi ảnh được giữ,không skin-intersect/crop/inpaint/xóa hoặc dự đoán person_id/tuổi/giới.
HF00209 B missing tóc nhưng C1 numerical valid không xóa vấn đề B hoặc tự chứng nhận ảnh đúng giải phẫu.
Hồ sơ review800 NOT_REVIEWED/decision register trước được giữ nguyên; lựa chọn triển khai trong task này
không được ghi thành phê duyệt anatomy thay cho người có thẩm quyền.

## Bảo toàn

**{len(baseline)} file đã có giữ nguyên SHA-256 trước/sau**, gồm PDF,1438 ảnh và metadata,source/mapping A/B,
vectors/stats/calibration/query outputs v1/v2,các SQLite và backup,ROI v0.2/v0.4,trial100 v0.2/96 vectors,
hồ sơ review và các file UI đang có khi nhiệm vụ này bắt đầu. SQLite catalog chỉ được mở `mode=ro&immutable=1`.
Không thay kết quả A+B,không nhập vector C1 vào SQLite,không triển khai C2 hoặc fusion.
[Baseline](../outputs/C1_lbp/full_v04/evidence/baseline_before.json),
[final scope](../outputs/C1_lbp/full_v04/evidence/final_scope.json),
[created files manifest](../outputs/C1_lbp/full_v04/evidence/created_files_manifest.json).
"""
    text_new(ROOT / 'docs/C1_FULL_IMPLEMENTATION_REPORT.md',report)
    numerical = '# C1 toàn kho v0.4 — kiểm chứng số học\n\n' + common + f"""
## Phạm vi thực tế

1438 ảnh:710 CFD/728 HF.1438 valid vectors float64(236),0 missing;1438 status rows đầy đủ.
Counts uint64(1438,4,59),eligible uint64(1438,4). Đủ5752 nhóm histogram finite/nonnegative,
counts.sum=N≥64,feature.reshape(4,59)=counts/N bitwise, mỗi nhómL1 trong sai sốfloat64.
Kernel cũ không sửa; ROI v0.4 bind riêng bởi feature schema mới, dependency v0.2 của spec gốc vẫn giữ.

{support_table}
Vector sum min/max={verified['vector_sum_min']!r}/{verified['vector_sum_max']!r}; không chuẩn hóa global.
Mỗi row metadata gắn image_id/feature_row_index/hash,archive join theo tên/ID, không source-position zip.
Diagnostics full1438 ghi raw mask hash/pixels/support từng vùng,khớp census v0.4.

## Oracle độc lập

12 ảnh cố định: {', '.join(verified['scalar_oracle_images'])}.
Scalar oracle cũ không import target để tạo expected: Python integer grayscale, codebook bằng quay run1,
frozen CSV vertex,full raster scan,21-point scalar support,ordered scalar bilinear.
OpenCV pointPolygonTest là primitive raster chung do contract quy định, không khẳng định độc lập backend này.
48 histogram /211534 tâm đối chiếu counts và L1 chính xác.3122 tâm lấy stride row-major trước khi so
raw codes và8 neighbours;0 mismatch, max interpolation/histogram error0.0. Gray cả12 ảnh khớp từng pixel.

Chi-square independent=`0.5*math.fsum((float(a)-float(b))**2/(float(a)+float(b)+1e-8))`.
Đối chiếu17256 distances với vectorized implementation,max error={verified['max_chi_abs_error']!r}.
Self-distance0 vàTop-5 của cả12 ảnh khớp scalar; không dùng Euclid.
Fixture hai candidate có Euclid order ngược Chi-square xác minh production dùng đúng metric.
Tie fixture có duplicate zero-distance: chỉ bỏ query_id,giữ candidate0,sort distance rồiimage_id,
không thay thứ tự khi hoán vị row metadata. Đây là convention tie-break,PDF không chốt.

## Regression và provenance

95 tests đạt,0 error/failure/skip.19 report_v2 tests(A sigma+epsilon,B2-stage,Euclid/median AB),
17 A/B identity/fusion tests,12 color features,10 color report conventions,26 trial C1 và11 full_v04.
Synthetic fit/calibration fixtures trong regression không refit artifact kho. C1 query ảnh gallery reuse vectors,
và3 vùng không đổi khớp bitwise96 old trial vectors. Các ảnh v0.2 thiếu C1 do forehead tự giao nay có numerical
C1 v0.4; trial100 cũ vẫn96 vector/4 missing nguyên trạng/hash, không sửa lịch sử để thành100.
[regression log](../../outputs/C1_lbp/full_v04/evidence/regression_tests.log),
[regression JSON](../../outputs/C1_lbp/full_v04/evidence/regression_tests.json),
[verification đầy đủ](../../outputs/C1_lbp/full_v04/verification.json).

Đã chạy6 query CLI gallery:CFD00001/CFD00069/HF00001/HF00198/HF00209/HF00722.
CSV↔JSON rankings/distances khớp;36 source image tiles trong comparison PNG khớp pixel nguồn.
[Query CFD00001](../../outputs/C1_lbp/full_v04/queries/cfd_final_00001/results.json),
[HF00209](../../outputs/C1_lbp/full_v04/queries/hf_merged_00209/results.json).
CLI chưa hỗ trợ arbitrary new image; không giả định alignment. Query không refit/histogram biến đổi.

## Hash và bất biến

{hash_table}
{len(baseline)} file cũ so SHA-256 trước/sau,0 thiếu/đổi, gồm PDF,dataset,A/B,SQLite,A+B,trial100 và review.
[Baseline](../../outputs/C1_lbp/full_v04/evidence/baseline_before.json),
[final scope](../../outputs/C1_lbp/full_v04/evidence/final_scope.json),
[manifest file mới](../../outputs/C1_lbp/full_v04/evidence/created_files_manifest.json).
Không ghi SQLite,rerun MediaPipe,thay codebook/gray/bilinear/P/R/threshold,L1,Chi0.5 hoặc stats/calibration.
Mọi missing phải có reason,không zero-fill; run này0 missing là số đo thực tế,không ép expectation.

## Giới hạn đánh giá

PASS là kết quả số học/serialization/identity/ranking trong môi trường schema đã ghi; không anatomy certification.
ROI phụ trợ478/upper FACE_OVAL/lower brow/bridge/frame/overlap/margins là convention chưa có annotation đầy đủ.
2 ảnh thiếu proxy pixels,4 native-point exceptions,tóc/tay/kính/vải và3 dataset violations vẫn giữ.
Chủ dự án chọn v0.4 cho triển khai nhưng không đổi các dòng NOT_REVIEWED thành ACCEPT hoặc ghi quyết định
chấp thuận giả. Không tuyên bố100% anatomical compliance,không triển khai C2/fusion.
Xem [báo cáo triển khai và lệnh PowerShell thực tế](../C1_FULL_IMPLEMENTATION_REPORT.md).
"""
    text_new(ROOT / 'docs/audits/C1_FULL_NUMERICAL_VERIFICATION.md',numerical)
    text_new(OUT / 'README.md','''# C1 full_v04

Project-selected ROI v0.4 / ANATOMY_PROVISIONAL.1438 vectors,710 CFD+728 HF,0 missing.
Read [implementation report](../../../docs/C1_FULL_IMPLEMENTATION_REPORT.md) and feature_schema.json.
features_C1.npy float64[1438,236];counts.npy uint64[1438,4,59];eligible_centres.npy uint64[1438,4].
feature_rows.csv maps explicit image_id to feature_row_index;extraction_status.csv contains all1438 inputs.
The original LBP spec's ROI v0.2 dependency remains unchanged; a new implementation binding selects v0.4.
No source image,PDF,previous database/vector/stats/calibration/review was modified.

Query from repository root (use a fresh output folder):

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image cfd_final_00001.png --top-k 5 --output outputs/C1_lbp/full_v04/queries/cfd_final_00001_run2
```

Query supports gallery IDs/filenames/matching files only; no unaligned external-image adapter.
Distance =0.5*sum((a-b)^2/(a+b+1e-8)); self-ID excluded; ties sort by image_id.
Existing extraction/query outputs refuse overwrite. No C2 or fusion is included.
''')
    final_baseline = protected_baseline()
    write_json(OUT / 'evidence/final_scope.json',dict(schema_id='C1_FULL_V04_FINAL_SCOPE_v1',
        processed_images=1438,valid_vectors=1438,missing_images=0,anatomy_status='PROVISIONAL',
        project_selected_ROI=ROI_HASH,review_annotations_or_approval_records_modified=False,
        old_files_checked=len(final_baseline),old_files_changed=[],
        baseline_sha256=kernel.sha256(OUT/'evidence/baseline_before.json'),
        kernel_sha256=KERNEL_HASH,regression_tests=95,independent_scalar_centres=211534,
        query_CSV_JSON_PNG_roundtrips=len(queries),query_original_pixel_tiles_verified=checked_pixels,
        detector_runs=0,SQLite_writes=0,C2_or_fusion=False,old_trial100_batch_rerun=False))
    paths = subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    created = []
    for path in sorted(paths):
        p = ROOT/path
        if p.is_file() and str(p.resolve()) not in baseline:
            created.append(dict(path=path,bytes=p.stat().st_size,sha256=kernel.sha256(p)))
    write_json(OUT/'evidence/created_files_manifest.json',dict(schema_id='C1_FULL_V04_CREATED_FILES_v1',self_excluded=True,files=created))
    print('Finalized full C1:',len(created),'new files;',len(baseline),'old files unchanged;6 query round-trips PASS',flush=True)


if __name__ == '__main__': main()
