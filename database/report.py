"""Write the delivery report and hash manifests after completed verification."""
from contextlib import closing
from pathlib import Path
import re

from database import store as db
from shared.report_v2 import read_json, read_csv, write_json

ROOT = db.ROOT
FOLDER = ROOT/'database'
E = FOLDER/'evidence'


def table(headers, rows):
    def cell(x):
        return str(x).replace('|','∣').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(cell,r))+' |' for r in rows])


def main():
    summary=read_json(E/'verification_summary.json')
    assert summary['status']=='PASS' and db.digest(db.DEFAULT_DB)==summary['database_sha256']
    for log in ['tests.log','v2_regression_tests.log']:
        text=(E/log).read_text(encoding='utf-8-sig')
        assert 'Ran 19 tests' in text and text.rstrip().endswith('OK')
    with closing(db.connect()) as c:
        assert db.counts(c)==summary['counts']
        assert c.execute("SELECT count(*) FROM FeatureVersions WHERE logical_group='C'").fetchone()[0]==0
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        table_count=c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        eyes=[dict(r) for r in c.execute('SELECT image_id,left_x,left_y,right_x,right_y,coordinate_role FROM EyeCoordinates ORDER BY image_id')]
        eye_rows=[[r['image_id'],r['left_x'],r['left_y'],r['right_x'],r['right_y'],r['coordinate_role']] for r in eyes]
    top_rows=[r for r in read_csv(E/'top5_before_after.csv') if r['query']=='cfd_final_00001' and r['mode']=='AB']
    top=[[r['rank'],r['image_name'],r['database_dA'],r['database_dB'],r['database_D_AB'],r['all_fields_exactly_equal']] for r in top_rows]
    backup=read_json(E/'backup_restore.json')
    for item in [backup['backup'],backup['restore']]:
        assert db.digest(item['destination'])==item['sha256']
    report=f'''# Triển khai CSDL cho Portrait Retrieval A/B v2

Ngày nghiệm thu: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu duy nhất: `csdldpt.pdf`, §1.3 và §2.5, SHA-256 `{db.legacy.REPORT_SHA256}` đã đối chiếu. Đã đọc năm báo cáo được yêu cầu; giữ nguyên chúng như hồ sơ trước khi có tầng CSDL.

**Đã triển khai và kiểm chứng tầng SQLite thực sự. Chưa chứng nhận toàn hệ thống tuân thủ 100% PDF.** Chỉ thêm thư mục `database/`; không sửa pipeline, mapping, dataset, PDF, vector, stats, calibration hay kết quả query v1/v2. Không triển khai C1/C2.

## Phạm vi yêu cầu và lựa chọn triển khai

| Yêu cầu | Hiện thực và bằng chứng | Kết luận có giới hạn |
| --- | --- | --- |
| §1.3: mã ảnh, đường dẫn và metadata vào CSDL | Images có PK, hash, kích thước, source, dataset version; INSERT/SELECT thực tế 1438 ảnh | Đã có lưu trữ quan hệ và truy xuất metadata; không chứng nhận tiêu chí nội dung từng ảnh. |
| §1.3: vị trí hai mắt | EyeCoordinates có method/model/frame/role/provenance và ba phép đo audit | Chưa có tọa độ tiền xử lý gốc; 1435 ảnh chưa có phép đo audit. Không khai báo hoàn tất phần metadata mắt. |
| §2.5.1: giữ vector riêng để so sánh từng bộ/kết hợp | FeatureVectors chứa BLOB A150/B144 tách theo image_id và feature_version | Đã thực hiện cho A/B; không tự coi số bảng/cột SQL là nguyên văn PDF. |
| §2.5.2: tham số chuẩn hóa đã lưu | Một NPZ A và hai NPZ B được lưu nguyên byte và có hash/version/thứ tự stage | Giữ đúng v2 đã nghiệm thu; không fit lại, không đổi công thức. |
| §2.5.2: median normalization | Calibration relational lưu 20.000 cặp, 40.000 dA/dB, median/epsilon, candidate order và fingerprint | Dùng lại calibration v2, không tính median theo query. |
| §2.5.3: tổng có trọng số | SQL SELECT vector rồi hàm Euclid/median/rank hiện hành; RetrievalRuns/Results lưu version, trọng số và mọi khoảng cách | Chỉ thử nghiệm A+B 0.5/0.5; chưa phải fusion A/B/C1/C2 chính thức. |
| Khóa người | Persons có source_namespace + source_person_id; Images FK có thể NULL | 407 ID CFD; 728 ảnh HF không suy đoán identity. |

SQLite **{summary['sqlite_version']}** qua module chuẩn `sqlite3` là IMPLEMENTATION DETAIL cho prototype cục bộ. PDF không chọn DBMS, kiểu BLOB, dtype/endian serialization, UUID run ID, schema migration/version hay số bảng. Schema version 1 có **{table_count} bảng**, các PK/FK/UNIQUE/CHECK và view/trigger; đây là thiết kế triển khai, không phải số bảng do PDF quy định.

PDF nói ba nhóm A/B/C nhưng bốn vector A/B/C1/C2. Schema thể hiện `logical_group` riêng với `feature_name`; mỗi vector/version là bản ghi độc lập, tránh ghép số chiều hoặc tạo vector giả. CalibrationComponents và các bảng cặp cho phép thêm version sau này. Loader/retrieval hiện chỉ phục vụ A/B; bổ sung C cần nhiệm vụ riêng, không có bản ghi C trong file bàn giao.

## Dữ liệu bàn giao

{table(['Hạng mục','Số lượng'],summary['counts'].items())}

- [CSDL chính](data/portrait_ab_v2.sqlite3), SHA-256 `{summary['database_sha256']}`.
- [Schema SQL](schema.sql), [module import/load/query](store.py), [CLI](__main__.py), [ví dụ SQL](examples.sql).
- [Snapshot backup](backups/portrait_ab_v2.backup.sqlite3) và [file phục hồi](restored/portrait_ab_v2.sqlite3).
- [README và hướng dẫn API](README.md).

Nhãn `dataset_HF_CFD_final:immutable_v1` là nhãn truy vết cục bộ, không tự gán nó là một release upstream. Catalog gốc có thứ tự khác A; Images giữ cả `catalog_row_index` lẫn `a_row_index`. Import A kiểm chỉ số hàng tường minh, B tra image_id rồi lấy đúng feature_row_index. HF00209 có a_row_index=918 nhưng thiếu B; HF00210 có a_row_index=919, B row=918. Không zip hai matrix.

## Vector, chuẩn hóa và calibration

**{summary['exact_vector_roundtrips']} vector hợp lệ** đọc từ SQLite khớp dtype, shape và byte với artifact v2: 1438 A150 và 1437 B144 float64. SHA payload từng hàng lưu trong CSDL và [vector_roundtrip.csv](evidence/vector_roundtrip.csv). Không serialize qua decimal/JSON số. Length CHECK cùng composite FK version/dtype/dimension ngăn mất chiều hoặc metadata dtype sai.

Ba NPZ normalization giữ nguyên byte, gồm scalar metadata và mảng tham số; [normalization_roundtrip.json](evidence/normalization_roundtrip.json). A dùng `(raw−mean)/(raw_sigma+1e-8)`, ddof=0. B giữ Lab24 trước concat và final144 riêng theo D15. Loader có thể đọc các tham số từ BLOB, không cần NPZ nguồn cho query ảnh đã có.

Median A=`{db.read_json(db.v2.OUT/'calibration/median_params.json')['median_a']}`, B=`{db.read_json(db.v2.OUT/'calibration/median_params.json')['median_b']}`, epsilon=`1e-8`. BLOB JSON/CSV calibration, danh sách ứng viên, thứ tự cặp và khoảng cách đều được bảo toàn. Tính lại Euclid từ vector SELECT cho toàn bộ 20.000 cặp cho max sai số A={summary['pair_euclid_max_error']['a']}, B={summary['pair_euclid_max_error']['b']}; phép kiểm này không thay median/stats đã lưu.

HF00209: B `status='missing'`, payload và feature_row_index đều NULL, reason `hair:missing_empty(0<100)`. Các thử INSERT/UPDATE sai bị từ chối bằng ràng buộc; [missing_b.json](evidence/missing_b.json), [constraints.json](evidence/constraints.json). Không zero-fill, không đổi trọng số hay lọc thêm ảnh để cải thiện Top-5.

## Metadata mắt có giới hạn

{table(['image_id','left_x','left_y','right_x','right_y','Vai trò'],eye_rows)}

Ba dòng dùng dữ liệu đã lưu ở audit trước: scalar float64 mean của sáu điểm mí pixel float32. Import xác minh hash model tại thời điểm audit, ảnh, landmark, evidence và script. `model_version` gồm MediaPipe package version và hash `face_landmarker.task`; `provenance_json` ghi rõ không phải tọa độ tiền xử lý gốc. Trái/phải theo code/người xem, không ngầm đổi sang hệ quy chiếu giải phẫu.

1435 ảnh khác không có dòng đo; LEFT JOIN trả NULL. Cả 1438 ảnh vẫn thiếu bằng chứng về tọa độ mắt được dùng ở bước tiền xử lý gốc. Không suy ngược tọa độ tuyệt đối từ vector A1 đã chuẩn hóa, không gán eye_distance thành hai tâm mắt và không dùng vị trí trong hình PDF làm metadata.

## Đối chiếu truy vấn trước/sau import

Đã INSERT run, query vector và result thực tế, rồi SELECT lại để đối chiếu. **15 chế độ trên năm trường hợp, 65 hàng kết quả**, giữ chính xác rank, ID/tên, dA, dB, normalized A/B, D_AB và score. Các trường hợp: CFD00001, CFD00088, CFD00144, HF00209 và new_query. CLI mẫu trước đó tạo thêm ba run/15 result; file bàn giao tổng cộng 18 run và 80 result.

{table(['Rank','Ảnh A+B CFD00001','dA từ DB','dB từ DB','D_AB từ DB','Mọi trường bằng file'],top)}

[top5_before_after.csv](evidence/top5_before_after.csv) lưu cột trước/sau ở đầy đủ độ chính xác; [ranking_comparison.json](evidence/ranking_comparison.json) lưu từng run/version tham chiếu. [sql_examples_results.json](evidence/sql_examples_results.json) chứa kết quả SQL thực thi, không chỉ ví dụ văn bản.

Tập ứng viên cho cả ba mode giữ giao A/B 1437 ảnh, đúng thử nghiệm file. Query thiếu B có A-only 5 kết quả; B/AB rỗng, dB/D_AB NULL. Self-match theo hash byte và tie-break tên ảnh giữ nguyên. Euclid/rank chạy bằng hàm NumPy hiện hành sau SELECT; không tuyên bố SQLite có ANN hoặc vector extension.

Query mới dùng đúng hai worker và môi trường gốc, hash stats được đối chiếu với CSDL; [new_query_provenance.json](evidence/new_query_provenance.json). Worker vẫn cần gallery/model file v2 để xác minh và trích xuất; gallery dùng xếp hạng được đọc từ SQLite. Fixture là PNG mã hóa lại cùng pixel CFD00001, khác hash byte; đây là smoke test đường đi ảnh mới, không phải đánh giá khuôn mặt holdout hoặc chất lượng nhận diện.

## Kiểm chứng, transaction và backup/restore

**19 unit/integration tests CSDL +19 regression tests v2 đạt, không skip.** Tests kiểm byte/endian/signed-zero, ID/order sau ảnh thiếu B, NPZ hai stage B, calibration, constraints, corruption detection, persistence, rollback và backup/restore; không sửa tests hay code A/B hiện có. Query ảnh đã có được kiểm khi file gallery loaders bị vô hiệu hóa. Logs: [tests.log](evidence/tests.log), [v2_regression_tests.log](evidence/v2_regression_tests.log).

Import dùng transaction DDL+dữ liệu; file có sẵn bị từ chối. Lỗi import rollback và loại đúng file mới vừa tạo, có test riêng. Mỗi connection bật FK. Retrieval lưu các mode trong một transaction. Backup/restore dùng SQLite backup API, đích mới; kiểm integrity, FK, toàn bộ SQL dump và Top-5 sau phục hồi.

Hash SQL dump nguồn/khôi phục: `{backup['logical_sql_dump_sha256']}`. [backup_restore.json](evidence/backup_restore.json) có hash từng file và kết quả. Backup phản ánh snapshot lúc nghiệm thu; query mới có lưu sẽ thay DB chính nhưng không thay artifact A/B v2.

**{summary['protected_files_checked']} file có sẵn kiểm hash trước/sau: không có thay đổi**, gồm PDF, dataset/masks, source, vector/stats/calibration/output v1/v2 và các audit trước. [baseline_before.json](evidence/baseline_before.json), [verification_summary.json](evidence/verification_summary.json), [final_scope.json](evidence/final_scope.json). Chỉ các file mới trong `database/` thuộc thay đổi lần này.

## Lệnh PowerShell thực tế đã chạy thành công

Từ `D:\\TuNam4\\portrait-retrieval`; stdout/log được lưu trong `database/evidence/`:

```powershell
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m unittest discover -s database/tests -v
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database import-v2
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database search --image cfd_final_00001.png --top-k 5 --weight-a 0.5 --weight-b 0.5
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database image --image-id hf_merged_00209
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database.verify
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m unittest discover -s tests -p test_report_v2.py -v
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m database.report
```

`database.verify` đã chạy một lần và tạo snapshot; chạy lại sẽ từ chối trước khi ghi thêm run nếu snapshot tồn tại. Import/backup không ghi đè file có sẵn. Các lệnh dựng bản khác và backup thủ công ở README là ví dụ cho đích mới, không phải khẳng định đã chạy trên đường dẫn ví dụ đó.

## Những phần chưa được chứng minh hoặc chưa giải quyết

- Sai khác mapping với hình PDF ở đầu hàm/topology mũi đã được audit xác nhận; canonical MP ID thay thế, endpoint 14 A2, định nghĩa tâm mắt và frame trái/phải vẫn cần thẩm quyền. Không sửa mapping.
- HF00333/HF00561 có mặt phụ; HF00722 che miệng. CSDL nhập nguyên corpus, không xóa/crop/thay ảnh. HF00209 thiếu B không tự chứng minh vi phạm dataset; HF00694 còn vấn đề đại diện vùng tóc/che khuất cần review.
- Provenance chưa định vị được ảnh thay thế hợp lệ; nhãn người HF, tuổi/giới/cảm xúc, số 1135 người/303 ảnh cảm xúc và quy trình preprocessing/alignment còn thiếu bằng chứng.
- Tọa độ mắt audit không thay bằng chứng tiền xử lý gốc. Chưa có relevance labels để chứng nhận chất lượng truy hồi.
- Chỉ đóng khoảng trống **tầng CSDL A/B prototype đã triển khai và kiểm chứng**. Không nâng trạng thái toàn hệ thống lên 100% tuân thủ, không tạo C1/C2 hoặc fusion bốn vector.
'''
    (FOLDER/'implementation_report.md').write_text(report,encoding='utf-8')
    baseline=read_json(E/'baseline_before.json')
    changed=[p for p,h in baseline.items() if db.digest(p)!=h]
    assert not changed,changed
    write_json(E/'final_scope.json',dict(status='PASS',protected_files_checked=len(baseline),
        changed_existing_files=changed,added_scope='database/',database_sha256=db.digest(db.DEFAULT_DB),
        database_layer_implemented=True,vector_precision_preserved=True,full_system_compliance=False,
        mapping_changed=False,dataset_changed=False,v2_changed=False,c1_c2_implemented=False))
    broken=[]
    for name in ('README.md','implementation_report.md'):
        p=FOLDER/name
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not link.startswith(('http://','https://')) and not (p.parent/link).is_file():
                broken.append([name,link])
    assert not broken,broken
    files=[p for p in FOLDER.rglob('*') if p.is_file() and '__pycache__' not in p.parts
           and p != E/'created_files_manifest.json']
    write_json(E/'created_files_manifest.json',dict(self_excluded=True,files=[
        dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=db.digest(p)) for p in sorted(files)]))
    print(db.json_text(dict(status='PASS',protected_files_unchanged=len(baseline),new_files=len(files),broken_doc_links=broken,
        database_sha256=summary['database_sha256'],full_system_compliance=False)))


if __name__=='__main__':
    main()
