"""Seal fusion evidence and reports; all accepted inputs remain read-only."""
from collections import Counter
from pathlib import Path
import math
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from retrieval import fusion_four as f
from shared.report_v2 import read_json,write_json,digest,read_csv


def text_new(path,value):
    with Path(path).open('x',encoding='utf8',newline='\n') as stream:stream.write(value)


def main():
    evidence=f.OUT/'evidence'
    if (evidence/'created_files_manifest.json').exists():raise FileExistsError('Final evidence already sealed')
    verification=read_json(evidence/'verification.json');assert verification['status']=='PASS'
    # Final suite after strict filename validation and side-effect-free output test review.
    suite=unittest.TestSuite()
    for pattern in ['test_report_v2.py','test_search_ab.py','test_color_features.py','test_color_report_compliance.py',
                    'test_c1_lbp236.py','test_c1_trial100_integration.py','test_c1_full_v04.py',
                    'test_c2_root_hog.py','test_c2_pipeline.py','test_fusion_four.py']:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    with (evidence/'final_tests.log').open('x',encoding='utf8') as stream:
        tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    assert tests.wasSuccessful() and tests.testsRun==140 and not tests.skipped
    baseline=read_json(evidence/'baseline_before.json')
    changed=[name for name,expected in baseline.items() if not Path(name).is_file() or digest(name)!=expected]
    assert not changed,changed
    g=f.FourGallery();params=f.load_calibration(g)
    source_counts={k:dict(Counter(g.by_id[key]['source'] for key in g.maps[k])) for k in f.KINDS}
    source_counts['intersection']=dict(Counter(g.by_id[key]['source'] for key in g.ids))
    versions=g.policy['feature_versions']
    counts_table='| Bộ | Feature version | Shape | Dtype | CFD | HF |\n|---|---|---|---|---:|---:|\n'
    for k in f.KINDS:
        counts_table+=f"| {k.upper()} | `{versions[k]}` | {len(g.maps[k])}×{f.DIMENSIONS[k]} | float64 | {source_counts[k]['cfd']} | {source_counts[k]['hf']} |\n"
    medians_table='| Bộ | Khoảng cách | Median đã lưu | Sai số max so với scalar trên20.000 cặp |\n|---|---|---:|---:|\n'
    for k in f.KINDS:
        medians_table+=f"| {k.upper()} | {'Chi-square ×0.5' if k=='c1' else 'Euclid'} | {params['medians'][k]:.17g} | {verification['pair_distance_max_abs_errors'][k]:.17g} |\n"
    examples='';comparison='| Query | Top-5 A+B v2 (0.5/0.5) | Top-5 bốn bộ (0.25 mỗi bộ) | Số ID chung | Vị trí khác trên1436 ứng viên |\n|---|---|---|---:|---:|\n'
    for record in verification['scalar_rankings']:
        identity=record['query'];result=read_json(f.OUT/'queries'/identity/'results.json')
        examples+=f'\n### {identity}.png\n\n| Chế độ | Top-5 theo thứ tự: filename (distance) |\n|---|---|\n'
        for mode,rows in result['modes'].items():
            cells='; '.join(f"{r['filename']} ({r['score']:.12f})" for r in rows)
            examples+=f'| {mode.upper()} | {cells} |\n'
        examples+=f'\n[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/{identity}/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/{identity}/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/{identity}/results.json).\n'
        comparison+=f"| {identity} | {', '.join(record['ab_top5'])} | {', '.join(record['top5']['fusion'])} | {record['top5_AB_fusion_overlap']} | {record['ranking_positions_changed_AB_vs_fusion']} |\n"
    detailed='| Rank | Ảnh | dA | dB | dC1 | dC2 | D |\n|---:|---|---:|---:|---:|---:|---:|\n'
    for r in read_json(f.OUT/'queries/cfd_final_00001/results.json')['modes']['fusion']:
        detailed+=f"| {r['rank']} | {r['filename']} | {r['distance_a']:.12f} | {r['distance_b']:.12f} | {r['distance_c1']:.12f} | {r['distance_c2']:.12f} | {r['D']:.12f} |\n"
    hash_files=[f.POLICY_PATH,ROOT/'retrieval/fusion_four.py',ROOT/'retrieval/search_fusion.py',ROOT/'retrieval/fusion_oracle.py',
        f.OUT/'calibration/median_params.json',f.OUT/'calibration/representative_pairs.csv',evidence/'verification.json',
        evidence/'scalar_calibration_pairs.csv',evidence/'scalar_query_distances.csv',evidence/'baseline_before.json']
    hashes='| Artifact | SHA-256 |\n|---|---|\n'
    for path in hash_files:hashes+=f'| {path.relative_to(ROOT).as_posix()} | `{digest(path)}` |\n'
    prefix=f'''Ngày **24/11/2026**, Asia/Saigon. Đã triển khai và chạy thực tế: **EXPERIMENTAL_EQUAL_WEIGHTS**.
Nguồn cao nhất `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`{g.policy['report_sha256']}`, đã xác minh hash và đọc trực tiếp §2.5.1–2.5.3 bằng pypdf trong Python hệ thống.
Không coi cấu hình trọng số bằng nhau là trọng số do PDF chỉ định, không chứng nhận anatomy hoặc retrieval accuracy.

'''
    formulas='''```text
dA  = sqrt(sum((Aq-Ai)^2))                          # normalized A150 v2
dB  = sqrt(sum((Bq-Bi)^2))                          # normalized B144 v2
dC1 = 0.5*sum((C1q-C1i)^2/(C1q+C1i+epsilon_C1))    # four independent L1 histograms
dC2 = sqrt(sum((C2q-C2i)^2))                        # global L2 Root-HOG324
normalized_k = d_k/(median_k+epsilon)
D = wA*normalized_A + wB*normalized_B + wC1*normalized_C1 + wC2*normalized_C2
```

`epsilon=epsilon_C1=1e-8`. Epsilon C1 khớp schema/spec LBP hiện hành; median epsilon kế thừa AB v2.
Trọng số mặc định `(0.25,0.25,0.25,0.25)`, hữu hạn, không âm; tổng1 với **atol1e-12,rtol0**.
Không tự chia lại trọng số; giá trị nằm trong tolerance được dùng nguyên, không ép tổng về1.
Tolerance AB median và oracle **atol1e-12,rtol1e-12** được khóa trong policy trước khi tính median/Top-5.
Khoảng cách only là raw metric tương ứng để so sánh, không phải một phần của công thức fusion khác.
Không L2 lại C1, Z-score lại C1/C2, cosine Root-HOG, Euclid thay Chi-square hoặc refit stats theo query.

'''
    commands=r'''```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.fusion_four --calibrate
foreach ($fusionQuery in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00722.png','hf_merged_00209.png')) {
    .\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.search_fusion --image $fusionQuery --top-k 5 --weight-a 0.25 --weight-b 0.25 --weight-c1 0.25 --weight-c2 0.25
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_fusion.py
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_fusion_four.py -v
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_fusion.py
```
'''
    report='# Fusion A150 + B144 + C1_236 + C2_324 — triển khai\n\n'+prefix+'''## Kết quả và liên kết dữ liệu

**1437 ảnh đủ bốn vector**, gồm710 CFD+727 HF; toàn dataset1438 vẫn giữ nguyên.
Một query đầy đủ có1436 candidate sau loại1 self theo image_id. Cùng candidate pool cho cả năm chế độ.

'''+counts_table+'''
Chỉ `hf_merged_00209` thiếu B, lý do `hair:missing_empty(0<100)`. A/C1/C2 của ảnh này vẫn hợp lệ.
Query này trả `status=fusion_unavailable`, `missing_feature=missing_B`, không kết quả ở bất kỳ hàng so sánh nào;
không âm thầm triển khai fusion ba bộ. `gallery_intersection_count=1437`, `candidate_count=1437`,
`self_exclusion_count=0`, `ranked_candidate_count=0`: candidate_count là kích thước pool sau loại ID query,
không phải số kết quả đã tính khi query unavailable. Các truy vấn standalone cũ vẫn dùng bình thường.

Module mới `retrieval/fusion_four.py` dùng loader đã có để kiểm schema/stats, sau đó nối qua image_id.
A lấy a_row_index riêng; B/C1/C2 lấy feature_row_index riêng. Không zip hoặc ghép cùng vị trí hàng giữa các bộ.
Kiểm uniqueness ID/index, shape/dtype/finite, tập ID, filename, đường dẫn, SHA-256 nguồn và quan hệ a_row_index.
Mọi1438 ảnh nguồn được hash lại; B/source viết CFD/HF còn C1/C2 viết cfd/hf: chỉ so sánh source casefold,
không sửa metadata nguồn. Metadata đảo thứ tự vẫn nối đúng theo index từng bộ; B thiếu ở giữa không làm lệch hàng.

Policy SHA `'''+f.POLICY_SHA256+'''` pin55 file đầu vào/schema/manifests/stats/source và calibration cũ.
Các loader bổ sung xác thực dependency gốc (raw A, contract/codebook C1, spec/kernel C2). Sai hash/schema/version
hoặc intersection khác1437 đều dừng, không ép số liệu. C1 trial v0.2/C2 trial100 không được thay full gallery.
Policy có absolute paths cho snapshot Windows này; di chuyển/rebuild artifact cần một phiên bản fusion/calibration
mới được kiểm chứng, không sửa policy để cache cũ tiếp tục được dùng.

## Công thức và calibration

'''+formulas+medians_table+f'''
Đọc/reuse calibration AB v2 bằng nhánh read-only, không tái fit hoặc ghi file A+B.
Giữ đúng **20.000 cặp ID và thứ tự**, từ AB v2, không sampling lại.
Pair IDs SHA `{params['pair_ids_sha256']}`; mọi cặp thuộc giao1437 và là unordered nonself unique.
Recompute bốn khoảng cách trên cùng các cặp, lưu pair_id0…19999, hai image_id và bốn distance.
MedianA/B mới chênh AB v2 **0.0/0.0**. Median không phụ thuộc query; cache kiểm fingerprint/IDs/hash/version
và median so với CSV trước mỗi query. Không dùng AB hai-median như calibration bốn bộ.
Namespace mới `outputs/retrieval/fusion_ab_c1_c2_v1/calibration/`; không ghi đè calibration hoặc outputs cũ.

## CLI và output

`retrieval/search_fusion.py` hỗ trợ --image,--top-k,--weight-a,--weight-b,--weight-c1,--weight-c2,--output.
Chỉ gallery image_id, exact filename hoặc file có hash nguồn đã tồn tại. File đổi tên nhưng cùng bytes được map
về ID; hash trùng nhiều ID và tên không phân giải được thì từ chối. Tên ID đúng nhưng file bytes khác bị từ chối.
Không adapter ảnh mới, không giả ảnh mới aligned, không chạy detector hay thêm dependency.
Mọi phép tính ở .venv311 trên vector đã lưu; không gọi extractor A/B hoặc trộn .venv-uniface.

Sort tăng dần `(distance,image_id)`, loại self theo image_id, giữ duplicate vector khác ID nếu có.
CSV/JSON có mode,rank,ID,filename,source,bốn raw distance,bốn normalized distance,D,score riêng mode,
vector row indices. JSON có weights/medians/epsilon/pair hash/feature versions/calibration hash và candidate counts.
CSV mỗi query đầy đủ25 rows=5 mode×Top5. PNG năm hàng, sáu cột, nguyên pixel nguồn256×256,
mỗi hàng query+Top5. `top-k>5` lưu đủTopK CSV/JSON; hình vẫn Top5 theo yêu cầu so sánh.
Output dưới `outputs/retrieval/fusion_ab_c1_c2_v1/queries/<query_id>/`; --output chỉ thư mục con mới trong namespace này.
Mọi thư mục run/calibration đã tồn tại đều bị từ chối ghi đè. Query lại phải chọn --output tên mới.
Missing_B vẫn xuất CSV header0rows, JSON lý do và PNG báo unavailable, không chứa ảnh kết quả giả.

## Top-5 full fusion của cfd_final_00001.png

'''+detailed+'\n## So sánh năm chế độ trên cùng pool\n'+examples+'\n## Khác biệt so với A+B hai bộ\n\n'+comparison+'''
A+B so sánh được tính lại read-only trên đúng vector/median AB v2 và cùng1436 candidate; không sửa output AB.
Chỉ CFD00001 có đối chiếu JSON AB cũ trực tiếp; các query còn lại là baseline tái tính, không giả có file cũ.
Khác thứ hạng không chứng minh cải thiện chất lượng; chưa có relevance labels hoặc đánh giá retrieval có thẩm quyền.

## Kiểm thử, bảo toàn và giới hạn

140 tests PASS,0 failure/error/skip:118 regression A/B/C1/C2 +22 fusion.
Oracle độc lập đọc trực tiếp source CSV/NPY, dùng math.fsum, không gọi production ranking làm expected.
Đủ20.000 cặp, bốn median,5×1436 candidate và cả năm thứ hạng đầy đủ khớp; fixture trọng số khác(.1,.2,.3,.4)
cũng khớp full ranking, không dùng fixture để tối ưu weights.
125 rows CSV/JSON,155 tile ảnh nguồn và150 strip nhãn/filename/distance khớp pixel.
Self distance bốn bộ=0; self exclusion/tie-break/ID permutation/invalid weights/missingB/hash/schema/version
và từ chối trial/calibration hai bộ đều có test. [Kiểm chứng chi tiết](audits/FUSION_AB_C1_C2_NUMERICAL_VERIFICATION.md).

'''+f'''Baseline **{len(baseline)} file**, trước/sau **0 thay đổi hoặc thiếu**, gồm PDF,dataset,A/Bv2,
stats/ABcalibration,C1/C2full+trial,source cũ,SQLite và mọi output đã có trong baseline kế thừa.
Không ghi SQLite, refit gallery, sửa extractor/mapping/ROI/LBP/HOG, bổ sung vector hoặc chạy extraction batch.
Chỉ namespace fusion mới, module/test/oracle/script mới và hai báo cáo này được tạo.
Hash input trước toán học ở policy; hash toàn baseline trong evidence/baseline_before.json;
final_scope và created_files_manifest ghi bằng chứng cuối.

ROI C1 v0.4 là project-selected/provisional, không approved anatomy; không ghi ACCEPT vào hồ sơ con người.
A canonical478→68 và nose endpoints còn UNVERIFIED. C2 center-crop anatomy/alignment lịch sử chưa xác minh.
Dataset HF333/HF561 mặt phụ, HF722 tay che miệng vẫn là vi phạm đã biết; HF209 thiếu B là vấn đề feature
khác, không tự gán vi phạm dataset. Không suy person_id/tuổi/giới từ ngoại hình, không loại ảnh để làm đẹp Top-5.
Không tuyên bố100% toàn hệ thống tuân thủ, anatomy compliant hoặc fusion tốt hơn A+B khi chưa có bằng chứng.

## Hash

'''+hashes+'''
Các hash file mới còn lại ở [created_files_manifest](../outputs/retrieval/fusion_ab_c1_c2_v1/evidence/created_files_manifest.json).

## Lệnh PowerShell thực tế đã chạy thành công

Tại repository root, sử dụng môi trường đã có, không cài thư viện. Đây là các lệnh lần chạy đầu;
không chạy lại calibration để overwrite. Khi rerun query thêm --output một thư mục mới trong queries.

'''+commands
    text_new(ROOT/'docs/FUSION_AB_C1_C2_IMPLEMENTATION_REPORT.md',report)
    numeric='# Fusion bốn vector — kiểm chứng số học độc lập\n\n'+prefix+formulas+medians_table+f'''
## Toàn bộ calibration

20.000/20.000 ordered pairs giữ đúng AB v2, cùng intersection1437, không tạo lại mẫu.
Oracle `retrieval/fusion_oracle.py` không import production retrieval; trực tiếp load metadata/vector theo index
riêng từng bộ. Euclid=math.sqrt(math.fsum(squared differences)); Chi-square=0.5*math.fsum(fractions),
median=sort rồi lấy hai phần tử giữa, không gọi production median/ranking tạo expected.
Lưu toàn20.000 khoảng cách scalar ở evidence/scalar_calibration_pairs.csv.
Median scalar vs stored maxabs={verification['median_max_abs_error']:.17g}; A/B vs AB v2=0/0.
Pair IDs SHA `{params['pair_ids_sha256']}`; policy khóa trước phép tính `{f.POLICY_SHA256}`.

## Ranking và round-trip output

Năm query:CFD00001,CFD00069,HF00001,HF00198,HF00722. Mỗi query1436 candidate, loại1 self.
So sánh **toàn thứ hạng**1436 ở A-only/B-only/C1-only/C2-only/fusion, không chỉ Top5:khớp tất cả.
Đủ7180 bộ khoảng cách query-candidate độc lập ở evidence/scalar_query_distances.csv, kèm D_AB read-only.
Mỗi bộ gồm4 metric, normalized riêng vàD; maxabs error EuclidA={verification['query_distance_max_abs_errors']['a']:.17g},
B={verification['query_distance_max_abs_errors']['b']:.17g}, C1={verification['query_distance_max_abs_errors']['c1']:.17g},
C2={verification['query_distance_max_abs_errors']['c2']:.17g}, D={verification['fusion_max_abs_error']:.17g}.
Fixture unequal weights(.1,.2,.3,.4) kiểm thêm đủ1436 scores/full ranking, không phải weight selection.
Các median giữ nguyên qua query. Self-distance=0 ở cả4 metric; sort ties theo ID, không loại zero distance của ID khác.

125 CSV result rows khớpJSON và expected;155 image tiles khớp pixel nguồn (150 positive+5 query-only missingB).
150 strip nhãn/filename/distance được dựng lại từ metadata và số đã đối chiếu, khớp PNG.
PNG có5 hàng×(query+Top5),1640×1536 pixels. CSV giữfloat repr đủ round-trip, JSON allow_nan=False.
HF209 riêng:missing_B/fusion_unavailable,0 rows,1437 pool,0 self excluded,0 ranked;không zero-fill/redistribute.

## Tests thực tế

**140 tests PASS**,0 fail/error/skip,118 regression+22 fusion. Logs evidence/tests.log vàfinal_tests.log.
Final suite chạy sau review kiểm exact filename và loại test phụ thuộc output query có sẵn; arithmetic/ranking không đổi.
Unit tests dùng synthetic/temporary files cho lỗi, không sửa accepted artifact để test tamper.
Bao phủ negative/NaN/Inf/sum/shape weights, phép đo,epsilon,tie-break,permuted metadata,missing-middle-B,
duplicate/out-of-range index,bad shape/dtype/NaN,input/policyhash,query filehash,wrong schema/feature version,
wrong fingerprint/IDs/pair hash,corrupt median,trial C1v0.2,C2trial100,AB calibration dùng sai như four-way,
refuse overwrite vànamespace output. Full source signatures và manifests được loader kiểm thực tế.

## Bảo toàn

SHA-256 baseline{len(baseline)} file đều khớp:0 changed,0 missing. PDF/dataset/source/stats/normalization/calibration
A+Bv2,SQLite,C1full/trial,C2full/trial,output cũ không đổi. Kiểm baseline cuối bằng read-only hash;
không chạy lại feature extractor/refit,không khởi tạo hoặc update DB. New-file manifest không bao gồm chính nó.
'''+hashes+'''
## Phạm vi kết luận

Đã chứng minh công thức §2.5.2–2.5.3 và liên kết/fingerprint trên snapshot bốn vector hiện tại.
Epsilon, numeric tolerances,weights0.25,20k retained pairs,sort ties,output layout và byte-identity query
là quy ước triển khai, không gán cho PDF các giá trị/cột file không được quy định.
Không có relevance labels để tuyên bố quality tăng;không chứng nhận anatomy của C1v0.4/C2crop,
mapping A hoặc khắc phục dataset chỉ từ số họcPASS. Review con người/PDF/dataset/SQLite giữ nguyên.
[Lệnh thực tế, Top5 năm chế độ và so sánh AB](../FUSION_AB_C1_C2_IMPLEMENTATION_REPORT.md).
'''
    text_new(ROOT/'docs/audits/FUSION_AB_C1_C2_NUMERICAL_VERIFICATION.md',numeric)
    # Directly compare an actually existing AB query, never rewrite it.
    old=read_json(f.ab.OUT/'queries/cfd_final_00001/results.json')
    assert [r['image_id'] for r in old['results']['ab']]==verification['scalar_rankings'][0]['ab_top5']
    scalar_ab={r['candidate']:float(r['D_AB']) for r in read_csv(evidence/'scalar_query_distances.csv')
               if r['query']=='cfd_final_00001'}
    assert all(math.isclose(r['distance_total'],scalar_ab[r['image_id']],rel_tol=1e-12,abs_tol=1e-12)
               for r in old['results']['ab'])
    # Preserve original structure for traceable comparison in a new evidence record.
    write_json(evidence/'ab_existing_query_reference.json',dict(path=str(f.ab.OUT/'queries/cfd_final_00001/results.json'),
        sha256=digest(f.ab.OUT/'queries/cfd_final_00001/results.json'),original_query_result=old,
        recomputed_reference=verification['scalar_rankings'][0]['ab_top5']))
    write_json(evidence/'final_scope.json',dict(schema_id='FOUR_FEATURE_FINAL_SCOPE_v1',date='2026-11-24',timezone='Asia/Saigon',
        protected_files=len(baseline),changed=[],missing=[],source_counts=source_counts,
        valid_counts=g.policy['expected_counts'],missing_b=['hf_merged_00209'],
        feature_extraction_runs=0,normalization_refits=0,sqlite_writes=0,old_calibration_writes=0,
        baseline_sha256=digest(evidence/'baseline_before.json'),policy_sha256=f.POLICY_SHA256,
        final_tests_run=tests.testsRun,final_tests_status='PASS',final_tests_skipped=0,
        review_status_modified=False,anatomical_approval_claimed=False,retrieval_improvement_claimed=False))
    candidates=list(f.OUT.rglob('*'))
    candidates += [f.POLICY_PATH,ROOT/'retrieval/fusion_four.py',ROOT/'retrieval/search_fusion.py',ROOT/'retrieval/fusion_oracle.py',
        ROOT/'scripts/verify_fusion.py',ROOT/'scripts/finalize_fusion.py',ROOT/'tests/test_fusion_four.py',
        ROOT/'docs/FUSION_AB_C1_C2_IMPLEMENTATION_REPORT.md',ROOT/'docs/audits/FUSION_AB_C1_C2_NUMERICAL_VERIFICATION.md']
    files=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
           for p in sorted(set(candidates)) if p.is_file()]
    write_json(evidence/'created_files_manifest.json',dict(schema_id='FOUR_FEATURE_CREATED_FILES_v1',self_excluded=True,files=files))
    print('Final PASS:',tests.testsRun,'tests;',len(baseline),'protected files unchanged;',len(files),'new files sealed')


if __name__=='__main__':main()
