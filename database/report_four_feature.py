"""Write integration reports and seal only the new SQLite fusion namespace."""
from contextlib import closing
from pathlib import Path
import re

from database import four_feature as four
from database import store as db
from shared.report_v2 import read_json,write_json

E=four.BASE/'evidence'


def new_text(path,text):
    with Path(path).open('x',encoding='utf8',newline='\n') as stream:stream.write(text)


def main():
    if (E/'created_files_manifest.json').exists():raise FileExistsError('Integration evidence already sealed')
    v=read_json(E/'verification.json');assert v['status']=='PASS' and db.digest(four.DEFAULT_DB)==v['database_sha256']
    baseline=read_json(E/'baseline_before.json')
    changed=[p for p,h in baseline.items() if not Path(p).is_file() or db.digest(p)!=h]
    assert not changed,changed
    schema=read_json(E/'schema_inventory.json')
    with closing(db.connect(four.DEFAULT_DB)) as c:
        assert four.summary(c)==v['counts']
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
    version_counts='| Bộ | Phiên bản | Dimension/dtype | Valid | Missing |\n|---|---|---|---:|---:|\n'
    for kind in ['A','B','C1','C2']:
        records=[r for r in v['counts']['coverage'] if r['feature_name']==kind]
        valid=next(r for r in records if r['status']=='valid');missing=sum(r['record_count'] for r in records if r['status']=='missing')
        dimension=four.fusion.DIMENSIONS[kind.lower()]
        version_counts+=f"| {kind} | `{valid['feature_version']}` | {dimension}/`<f8` | {valid['record_count']} | {missing} |\n"
    tables='| Bảng mới | Các cột |\n|---|---|\n'
    for name,columns in schema['columns'].items():tables+=f"| {name} | {', '.join(c['name'] for c in columns)} |\n"
    indexes=[r['name'] for r in schema['objects'] if r['type']=='index']
    query_table='| Query | Trạng thái | Candidate | Loại self | Đã xếp hạng | Rows Top5 đã lưu |\n|---|---|---:|---:|---:|---:|\n'
    for r in v['queries']:
        query_table+=f"| {r['query']} | {r['status']} | {r['candidate_count']} | {r['self_exclusion_count']} | {r['ranked_candidate_count']} | {r['result_rows']} |\n"
    medians='| Bộ | Median giữ nguyên |\n|---|---:|\n'
    for k,m in v['medians'].items():medians+=f'| {k.upper()} | {m:.17g} |\n'
    top5=''
    for q in v['queries']:
        key=q['query'];r=read_json(four.BASE/'queries'/(key+'.json'))
        if r['status']!='ok':continue
        top5+=f'\n### {key}.png\n\n| Chế độ | Top5: filename (distance) |\n|---|---|\n'
        for mode,rows in r['modes'].items():
            text='; '.join(f"{x['filename']} ({x['score']:.12f})" for x in rows)
            top5+=f'| {mode.upper()} | {text} |\n'
        top5+=f'\n[JSON query](four_feature_v1/queries/{key}.json).\n'
    hashes='| File | SHA-256 |\n|---|---|\n'
    hash_paths=[four.SOURCE_DB,four.DEFAULT_DB,four.MIGRATION,four.AUTHORITY,four.ROOT/'database/four_feature.py',
                four.ROOT/'database/verify_four_feature.py',E/'verification.json',E/'full_ranking_comparison.csv',
                E/'vector_roundtrip.csv',E/'baseline_before.json']
    for p in hash_paths:hashes+=f'| {p.relative_to(four.ROOT).as_posix()} | `{db.digest(p)}` |\n'
    backups='| File | SHA-256 | Integrity/full ranking |\n|---|---|---|\n'
    for r in v['backups']:
        backups+=f"| {Path(r['path']).relative_to(four.ROOT).as_posix()} | `{r['sha256']}` | ok/exact |\n"
    prefix=f'''Ngày **24/11/2026**, Asia/Saigon. **Đã tích hợp và kiểm chứng SQLite cho bốn vector; EXPERIMENTAL_EQUAL_WEIGHTS.**
Nguồn cao nhất `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`, đã đọc trực tiếp §1.3 và§2.5.1–2.5.3.
Đã đọc schema, toàn bộ module database cũ, nguồn retrieval và các báo cáo C1/C2/fusion yêu cầu.
Không tuyên bố anatomy-approved, accuracy tăng hoặc 100% toàn hệ thống tuân thủ.

'''
    formulas='''```text
dA,dB,dC2 = sqrt(sum((q-i)^2)) trên từng vector riêng
dC1 = 0.5*sum((q-i)^2/(q+i+epsilon_C1))
normalized_k = d_k/(median_k+epsilon)
D = wA*normalized_A + wB*normalized_B + wC1*normalized_C1 + wC2*normalized_C2
```

Epsilon median và epsilon_C1 đều 1e-8. Weights (.25,.25,.25,.25) giữ nguyên;
hữu hạn, không âm, tổng 1 với atol1e-12/rtol0; không tự normalize weights hoặc optimize theo Top5.
Trọng số đều là EXPERIMENTAL_EQUAL_WEIGHTS, không phải trọng số PDF chỉ định.
Tolerance parity được khóa trước import: atol1e-12/rtol1e-12; quan sát thực tế exact, max error 0.
Không ghép854 chiều để tính Euclid; không refit/re-extract hay chuẩn hóa lại vector.

'''
    commands=r'''```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature import
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s database/tests -p test_four_feature.py -v
foreach ($sqlFusionQuery in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00722.png','hf_merged_00209.png')) {
    $sqlFusionId = [System.IO.Path]::GetFileNameWithoutExtension($sqlFusionQuery)
    $sqlFusionOutput = "database/four_feature_v1/queries/$sqlFusionId.json"
    $sqlFusionResult = .\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature search --image $sqlFusionQuery --top-k 5 --weight-a 0.25 --weight-b 0.25 --weight-c1 0.25 --weight-c2 0.25 --output $sqlFusionOutput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $sqlFusionResult | ConvertFrom-Json | Select-Object status, run_id, candidate_count, self_exclusion_count, ranked_candidate_count
}
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature backup --destination database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3
.\.venv311\Scripts\python.exe -X utf8 -B -m database.four_feature backup --db database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3 --destination database/four_feature_v1/restored/portrait_four_features_v1.sqlite3
.\.venv311\Scripts\python.exe -X utf8 -B -m database.verify_four_feature
& .\database\four_feature_v1\demo.ps1 -Image cfd_final_00001.png -TopK 5 | ConvertFrom-Json | Select-Object status, candidate_count, self_exclusion_count, ranked_candidate_count
.\.venv311\Scripts\python.exe -X utf8 -B -m database.report_four_feature
```
'''
    report='# SQLite — tích hợp fusion A150/B144/C1_236/C2_324\n\n'+prefix+'''## CSDL bàn giao và số liệu thực tế

Nguồn được giữ nguyên `database/data/portrait_ab_v2_eye_metadata_v1.sqlite3`; SQLite backup API tạo bản mới
`database/four_feature_v1/data/portrait_four_features_v1.sqlite3`, rồi migration additive trong một transaction.
Import từ chối đích đã tồn tại; không ghi đè source hoặc artifact nào có trước nhiệm vụ.

1438 Images, 407 Persons; 1441 EyeCoordinates (1438 phép đo audit mới + 3 phép đo audit lịch sử),
1438 EyeCoordinateSources giữ nguyên; không gọi các tọa độ audit là alignment gốc.
5752 FeatureVectors gồm 5751 valid và 1 missing, 4 FeatureVersions.

'''+version_counts+'''
Missing duy nhất `hf_merged_00209` ở B với `hair:missing_empty(0<100)`, BLOB và feature_row_index NULL.
A/C1/C2 của ảnh đó giữ nguyên, hợp lệ. Không zero-fill hoặc chia trọng số sang ba bộ.
1437 ảnh đủ bốn vector = 710 CFD + 727 HF; dataset vẫn gồm 1438 = 710 CFD + 728 HF.

## Thiết kế additive và phiên bản

Giữ nguyên `database/schema.sql`, base `PRAGMA user_version=1` để loader AB cũ tương thích.
Extension `FOUR_FEATURE_SQLITE_v1` có version riêng ở FourFeatureMigrations; migration SHA:
`'''+four.MIGRATION_SHA+'''`.
Không ALTER cột bảng cũ; tận dụng FeatureVersions/FeatureVectors/Calibrations/CalibrationComponents/
Candidates/Pairs/PairDistances bằng INSERT append-only. 19 bảng nguồn giữ nguyên toàn bộ dòng đã có;
các bảng khác chỉ đọc. Thống kê scope và schema thực nghiệm trong evidence.

'''+tables+f'''
Explicit indexes mới: {', '.join(indexes)}. Các PK/UNIQUE cũng sinh autoindex SQLite.
View mới FourFeatureCoverage; trigger mới FourFeatureResult_contract.
PK/FK/UNIQUE bảo vệ image_id + feature_version, row index, calibration/version và run/mode/rank.
Trigger chặn self, candidate ngoài intersection, rank vượt TopK, run unavailable và thiếu bốn component version.
SQL CHECK bảo vệ payload length, dtype/dimension, status/null, finite bounds và weights; ứng dụng kiểm hữu hạn.

PDF nói ba nhóm A/B/C nhưng bốn vector A/B/C1/C2. Schema lưu logical_group=C và feature_name=C1/C2 riêng,
không vector giả hoặc ép ba cột vật lý. SQLite, schema dạng hàng, kiểu BLOB, index, UUID, tên bảng/cột và migration
là IMPLEMENTATION DETAIL; PDF không quy định chính xác thiết kế SQL hay DBMS.

## Serialization, provenance và chuẩn hóa

Tái sử dụng database.store.encode_vector/decode_vector: IEEE754 C-order bytes, <f8, không cast làm mất số.
Mỗi FeatureVectors có image_id, feature_version, dimension, dtype, status, missing_reason, vector_sha256,
a_row_index, feature_row_index và provenance_json. BLOB khớp chính xác artifact nguồn ở cả 5751 vector hợp lệ.
FourFeatureVectorBindings lưu source row/hash ảnh/hash vector độc lập; query kiểm cả binding và payload,
phát hiện sửa byte kể cả khi sửa lại hash tự khai báo của FeatureVectors.
Join image_id, không ROWID hay vị trí hàng SELECT; row index chỉ tham chiếu trong đúng bộ/version.

A/B stats và ba NPZ normalization stage giữ nguyên byte từ CSDL nguồn, không fit lại.
C1/C2 đã có chuẩn hóa nội bộ, không có fitted gallery stats mới. Trường stats_hash của hai version này là
hash định nghĩa chuẩn hóa và schema đã có (ghi rõ trong provenance), không tạo NPZ stats giả.
FourFeatureArtifacts lưu nguyên byte schema/manifest/feature_rows/extraction_status C1/C2 cùng hash;
schema/provenance giữ ROI/spec/codebook/kernel/preprocessing hashes.
VersionLocks ghi hash toàn bản ghi FeatureVersions và vector artifact; schema/source mismatch bị từ chối.

## Calibration bốn bộ và cách ly lịch sử

ID mới `'''+four.CALIBRATION_ID+'''`; calibration AB `AB_report_v2:frozen_pairs_v1` giữ nguyên.
Tổng 2 calibrations, 40.000 pair rows, 120.000 component distance rows: AB cũ 20k/40k và four-way 20k/80k.
Nhập đúng 20.000 cặp ID/thứ tự và 80.000 scalar distance đã nghiệm thu; không sampling hoặc tính lại median.
Calibrations giữ nguyên byte params JSON/pairs CSV và hash; bảng quan hệ lưu pair IDs, 4 distance, 4 median,
candidate IDs/index. FourFeatureCalibrations lưu policy hash, epsilon_C1 và feature version mapping.

'''+medians+f'''
Pair IDs SHA `{v['pair_ids_sha256']}`; policy SHA `{v['policy_sha256']}`.
Authority SHA `{four.AUTHORITY_SHA}` khóa source DB, source/schema và calibration hashes trước import.
Query đọc calibration từ SQL, kiểm nguyên BLOB so với source hash đã khóa, rồi đối chiếu đủ 20k pair IDs,
80k distance, 4 version/median, epsilon và fingerprint. Không dùng AB calibration cho four-way hoặc ngược lại.

## Query từ SQLite và lịch sử

Module `database/four_feature.py`: CLI import, search, info, backup.
SqlFourGallery đọc metadata, vectors, stats, calibration từ SQLite; không đọc NPY/CSV gallery hoặc file calibration.
Kiểm source module số học/serialization bằng hash; tái sử dụng fusion_four.component_distances/combine/
rank_indices và resolve. Chỉ bổ sung luồng điều phối và lưu lịch sử, không viết lại công thức.

'''+formulas+'''
Hỗ trợ gallery ID/exact filename/path có hash nguồn; không adapter ảnh mới hoặc giả ảnh đã aligned.
Candidate pool chung gồm giao 1437 cho A-only/B-only/C1-only/C2-only/fusion; loại self ID, sort(distance,image_id).
Query đầy đủ: 1436 candidate, 1 self; missing B: pool 1437, 0 self, 0 ranked và fusion_unavailable.
Chế độ only dùng raw metric tương ứng; D vẫn lưu để giải thích fusion cùng bốn raw/normalized components.

Một FourFeatureRuns lưu một request, năm mode trong FourFeatureResults; FourFeatureRunComponents lưu
bốn feature versions/weights/medians. INSERT run/components/results commit atomically; unavailable
vẫn có run và bốn version refs nhưng 0 results. Demo 6 requests có 6 runs, 24 component refs, 125 Top5 results.
Giữ nguyên 18 RetrievalRuns/80 RetrievalResults AB lịch sử; không sửa QueryVectors cũ.
--no-save chỉ đọc; --output JSON có sẵn bị từ chối trước khi ghi lịch sử. CSDL mới là bản làm việc có thể
thay hash khi người dùng lưu thêm run; backup/restored là snapshot nghiệm thu, không ghi đè chúng.

'''+query_table+'''
## Top-5 file và SQLite: khớp chính xác ở mọi chế độ
'''+top5+'''
## Kiểm chứng và bảo toàn

'''+f'''{v['tests_run']} tests PASS, 0 fail/error/skip: 17 tests SQLite mới, 19 CSDL cũ, 140 regression A/B/C1/C2/fusion.
Năm query đầy đủ × 1436 candidate × 5 mode = **35.900 ranking rows**: thứ tự ID và mọi trường số học khớp chính xác,
max absolute error quan sát = 0.0; 125 Top5 rows và cả 6 trạng thái query khớp file. Weights/median không đổi.
[Full ranking CSV](four_feature_v1/evidence/full_ranking_comparison.csv),
[Top5 trước/sau](four_feature_v1/evidence/top5_before_after.csv),
[5751 vector round-trip](four_feature_v1/evidence/vector_roundtrip.csv),
[tests log](four_feature_v1/evidence/tests.log).

Tests kiểm INSERT/SELECT, FK/UNIQUE, missing, version/hash/schema, dtype/dimension, corrupted bytes,
serialization exact, đảo thứ tự physical bindings và reverse_unordered_selects, calibration isolation,
query không đọc file vectors/calibration, backup/restore và từ chối ghi đè. Fault injection chỉ trên
bản sao trong RAM/temp từ dữ liệu thật; không commit dữ liệu giả hoặc sửa artifact nghiệm thu.
Regressions fit thống kê trên fixture/temp; không refit gallery hoặc chạy extractor.

Toàn bộ 19 bảng nguồn giữ mọi dòng cũ exact; 7 bảng cho phép append version/vector/calibration.
[Đối chiếu từng bảng](four_feature_v1/evidence/original_table_preservation.json).
Baseline {v['protected_files']} file SHA trước/sau: 0 changed, 0 missing; PDF, dataset, A/B/C1/C2 vectors,
stats, calibration, source, SQLite cũ, queries/trial/review cũ không đổi.
[Verification JSON](four_feature_v1/evidence/verification.json),
[schema inventory](four_feature_v1/evidence/schema_inventory.json),
[SQL đã thực thi](four_feature_v1/evidence/sql_examples_results.json).

## Backup/restore

'''+backups+f'''
SQLite backup API, đích mới. Integrity ok, FK empty, counts và toàn bộ SQL dump khớp;
logical dump SHA `{v['logical_sql_dump_sha256']}`.
Sau phục hồi, cả 6 query và toàn bộ 35.900 ranking rows khớp database chính, không chỉ Top5.

## Hash nguồn và artifact mới

'''+hashes+'''
Các file khác ở evidence/created_files_manifest.json; manifest không tự chứa chính nó.
SQLite vẫn được ignore theo yêu cầu Git trước đó; file thực tế lưu ở namespace trên.

## Giới hạn còn giữ nguyên

C1 ROI v0.4 là project-selected/provisional, không anatomy-approved; không ghi ACCEPT hoặc APPROVED vào hồ sơ review.
Mapping A478→68/nose endpoints và alignment lịch sử còn UNVERIFIED; metadata mắt là audit_remeasurement.
Anatomy của C2 fixed center crop chưa xác minh. Dataset HF333/HF561 có mặt phụ, HF722 có tay che miệng vẫn tồn tại;
HF209 thiếu B là vấn đề feature khác. Giữ nguyên person labels NULL của HF, không suy người/tuổi/giới từ ngoại hình.
Chưa có relevance ground truth để kết luận fusion nâng accuracy.
Không sửa PDF, dataset, extractor, normalization/calibration/weights hoặc Top5; không GUI hoặc xử lý ảnh mới.

## Lệnh PowerShell đã chạy thành công

Chạy tại repository root với .venv311 đã có, không cài thêm thư viện. Import/backup/JSON output chỉ dùng đích mới;
không rerun ghi đè những đích này. demo.ps1 dùng --no-save, có thể chạy lại mà không đổi snapshot.

'''+commands
    report_path=four.ROOT/'database/FOUR_FEATURE_INTEGRATION_REPORT.md'
    new_text(report_path,report)
    audit='# SQLite bốn bộ — kiểm chứng tích hợp\n\n'+prefix+version_counts+'\n'+medians+f'''
## Kết quả thực nghiệm

- Exact IEEE byte round-trip: 5751 valid vectors; 5752 status records gồm 1 missing B.
- C1/C2 mỗi bộ có 1438 float64 vectors 236/324 chiều; A/B v2 giữ nguyên.
- Nhập 20.000 pairs và 80.000 component distances mới exact; không sampling/refit median.
- Giữ calibration AB v2 và mọi phiên bản lịch sử; median 4 bộ và epsilon 1e-8 không đổi.
- Full ranking parity: 5 query × 1436 candidate × 5 mode = 35.900 rows; ordered IDs và mọi distance exact, max error 0.
- Declared parity tolerance atol1e-12/rtol1e-12 đã khóa trước import tại authority.json.
- 125 Top5 rows và 6 query histories INSERT/SELECT khớp; HF209 fusion_unavailable, 0 result, không zero-fill.
- {v['tests_run']} tests PASS, 0 skip/failure/error: 140 regression + 19 database cũ + 17 SQL mới.
- Backup/restore integrity ok, FK empty, SQL dump và mọi query/full ranking khớp.
- {v['protected_files']} file baseline trước/sau không đổi; 19 bảng nguồn giữ mọi dòng đã có exact.

'''+query_table+'''
## Nguồn expected và tính độc lập

Parity expected dùng gallery/calibration file đã nghiệm thu và retrieval.search_fusion; actual dùng SQL adapter
đọc BLOBs và calibration quan hệ. Hai luồng dùng cùng hàm số học đã kiểm chứng, đúng yêu cầu tái sử dụng.
Nhiệm vụ này kiểm serialization/identity/calibration/persistence, không viết lại numerical oracle.
Oracle math.fsum độc lập của 20.000 pairs và 5 full rankings đã được đóng băng ở
outputs/retrieval/fusion_ab_c1_c2_v1/evidence/verification.json; các tests cũ được chạy regression.
Không gọi SQL query để tự tạo expected, không dùng Top5 để chọn trọng số.

DB nguồn SHA-256: `6fc6213286c715edf997ed9484ca1da8da0d07dff59e2c486375fd53e34f4396`.
1438 Images, 1441 audit EyeCoordinates và 1438 sources được backup trước additive migration.
Nguồn/user_version=1 và schema.sql giữ nguyên; extension có version độc lập FOUR_FEATURE_SQLITE_v1.
Thêm 8 bảng, 3 explicit indexes, 1 trigger, 1 view; không ALTER cột cũ.

## Bằng chứng

- [Verification JSON](../../database/four_feature_v1/evidence/verification.json)
- [Toàn bộ 35900 ranking rows](../../database/four_feature_v1/evidence/full_ranking_comparison.csv)
- [5751 vector bytes](../../database/four_feature_v1/evidence/vector_roundtrip.csv)
- [125 Top5 rows](../../database/four_feature_v1/evidence/top5_before_after.csv)
- [Bảo toàn 19 bảng](../../database/four_feature_v1/evidence/original_table_preservation.json)
- [Schema/columns/constraints](../../database/four_feature_v1/evidence/schema_inventory.json)
- [Tests log](../../database/four_feature_v1/evidence/tests.log)

'''+backups+'\n'+hashes+'''
## Phạm vi kết luận

Đã triển khai lưu 4 vector riêng và truy vấn SQL đúng công thức PDF §1.3/§2.5 trên snapshot hiện có;
SQL/BLOB/version/schema là quy ước triển khai, không phải số bảng/cột do PDF chỉ định.
Không chứng nhận anatomy ROI/C2 crop, mapping A, alignment lịch sử, tiêu chí dataset hoặc retrieval accuracy.
Không GUI/ảnh mới và không sửa PDF/vectors/weights/calibration để thay Top5.
[Báo cáo đầy đủ và PowerShell demo](../../database/FOUR_FEATURE_INTEGRATION_REPORT.md).
'''
    audit_path=four.ROOT/'docs/audits/FOUR_FEATURE_DATABASE_VERIFICATION.md'
    new_text(audit_path,audit)
    for path in [report_path,audit_path]:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text('utf8')):
            if not link.startswith('http'):assert (path.parent/link).is_file(),link
    write_json(E/'final_scope.json',dict(status='PASS',date='2026-11-24',timezone='Asia/Saigon',
        protected_files=len(baseline),changed=[],missing=[],source_database_unchanged=True,
        database_sha256=db.digest(four.DEFAULT_DB),authority_sha256=four.AUTHORITY_SHA,migration_sha256=four.MIGRATION_SHA,
        schema_extension=four.EXTENSION,accepted_feature_or_calibration_writes=0,
        sqlite_writes='Only new database/four_feature_v1/data working copy; tests in RAM/temp',
        feature_extraction_runs=0,gallery_stats_refits=0,new_image_adapter=False,gui=False,
        anatomy_approval_claimed=False,accuracy_improvement_claimed=False,tests_run=v['tests_run']))
    candidates=list(four.BASE.rglob('*'))+[four.MIGRATION,four.ROOT/'database/four_feature.py',
        four.ROOT/'database/verify_four_feature.py',four.ROOT/'database/report_four_feature.py',
        four.ROOT/'database/tests/test_four_feature.py',report_path,audit_path]
    manifest=[dict(path=p.relative_to(four.ROOT).as_posix(),bytes=p.stat().st_size,sha256=db.digest(p))
              for p in sorted(set(candidates)) if p.is_file()]
    write_json(E/'created_files_manifest.json',dict(schema_id='FOUR_FEATURE_DATABASE_CREATED_FILES_v1',self_excluded=True,files=manifest))
    print(db.json_text(dict(status='PASS',tests=v['tests_run'],protected_files=len(baseline),new_files=len(manifest),
        database_sha256=v['database_sha256'],full_ranking_rows=35900,observed_max_abs_error=0.)))


if __name__=='__main__':main()
