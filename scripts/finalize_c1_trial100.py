"""Write new trial reports and freeze evidence, checking protected artifacts."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src.lbp236 import Context, REGIONS, sha256
from features.C1_lbp.src.trial100 import OUT, write_json


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_text_new(path, text):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main():
    context = Context()
    baseline = load(OUT / 'evidence/baseline_before.json')
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or sha256(p) != h]
    if changed:
        raise ValueError('Protected artifact changed: ' + repr(changed[:10]))
    verification = load(OUT / 'evidence/numerical_verification.json')
    tests = load(OUT / 'evidence/unit_integration_tests.json')
    hand = load(OUT / 'evidence/hand_calculation.json')
    manifest = load(OUT / 'manifest.json')['images']
    assert tests['successful'] and tests['skipped'] == 0 and verification['numerical_status'] == 'PASS'
    assert verification['input_count'] == 100 and verification['valid_count'] == 96 and verification['missing_count'] == 4
    protected = len(baseline)
    scope = dict(context.lock, protected_file_count=protected, protected_missing_or_changed=changed,
                 protected_manifest_sha256=sha256(OUT / 'evidence/baseline_before.json'),
                 protected_paths_include_pdf_dataset_sources_AB_vectors_stats_calibration_queries_all_old_databases=True,
                 mediapipe_runs=0, database_writes=0, c2_vectors_created=0, rankings_computed=0,
                 original_alignment_reconstructed=False, added_library_installs=0)
    write_json(OUT / 'evidence/final_scope.json', scope)
    write_json(OUT / 'evidence/implementation_provenance.json', dict(context.lock,
        saved478_archive_sha256='a21e4abce28354d3a1fe5541bf0d2b7ab6d4b6d1119207d3231471bcacf263ed',
        measurement_role='audit_remeasurement; reused saved landmarks, not historical alignment proof',
        model_asset_sha256='64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff',
        original_mediapipe_distribution_version=None,
        numpy_opencv_python_versions=load(OUT / 'contract_lock.json')['environment'],
        numerical_implementation_corrections=[],
        nonnumerical_changes_after_first_trial=['Replace dynamic hashlib import with standard module import; no arithmetic/data change'],
        test_harness_note=tests['note'],
        source_hashes={p: sha256(ROOT / p) for p in [
            'features/C1_lbp/src/lbp236.py', 'features/C1_lbp/src/gallery.py', 'features/C1_lbp/src/trial100.py',
            'features/C1_lbp/verification/scalar_oracle.py', 'scripts/verify_c1_trial100.py',
            'scripts/test_c1_trial100.py', 'tests/test_c1_lbp236.py', 'tests/test_c1_trial100_integration.py']}))

    region_table = '| Vùng (96 vector) | Raw pixels min–max | Eligible min–max | Tổng tâm | Bin có count>0 |\n|---|---:|---:|---:|---:|\n'
    for region in REGIONS:
        r = verification['region_statistics'][region]
        region_table += f"| {region} | {r['raw_mask_min']}–{r['raw_mask_max']} | {r['centres_min']}–{r['centres_max']} | {r['centres_total']} | {r['occupied_bins_min']}–{r['occupied_bins_max']} |\n"
    missing_table = '| image_id | Kết quả | Nguyên nhân |\n|---|---|---|\n'
    for row in manifest:
        if row['status'] == 'missing_C1':
            missing_table += f"| {row['image_id']} | missing_C1; feature_row_index=NULL | {row['missing_reason']} |\n"
    hand_table = '| p | (x,y) láng giềng | gp float64 | gp>=195 |\n|---:|---|---:|---:|\n'
    for p, n in enumerate(hand['neighbours']):
        hand_table += f"| {p} | ({n['x']:.15g}, {n['y']:.15g}) | {n['gp']:.15g} | {n['bit']} |\n"
    commands = r"""```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C1_lbp.src.trial100
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/test_c1_trial100.py
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c1_trial100.py
```
"""
    preamble = f"""Ngày thực hiện: **24/11/2026**, Asia/Saigon.

**EXPERIMENTAL_TECHNICAL_TRIAL** — **ROI_ANATOMY_STATUS=PROVISIONAL**.
Thành công số học không chứng nhận ROI giải phẫu hoặc toàn hệ thống.

PDF chuẩn duy nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`.
Đã đọc trực tiếp §2.4 từ PDF vật lý trang13–16 bằng `pypdf` có sẵn trong Python hệ thống;
extractor/tests chạy `.venv311`, không cài thêm thư viện. Bản trích và nguồn nằm trong evidence của trial.

Khóa `C1_ROI_RAW_CONTRACT_v0.2.0`: `{context.lock['roi_contract_hash']}`;
`C1_LBP_236_IMPLEMENTATION_SPEC_v0.1.0`: `{context.lock['lbp_spec_hash']}`;
codebook file SHA-256 `{context.lock['codebook_file_sha256']}`.
Cả hai content hash được tính lại từ JSON canonical (bỏ trường content_sha256), so với giá trị yêu cầu;
sai schema/hash thì dừng. Không sửa spec, mapping A hoặc áp dụng proposal forehead v0.3.
"""
    report = '# C1 LBP236 — kết quả technical trial100\n\n' + preamble + f"""
## Kết quả thực tế và phạm vi

Đúng manifest đã khóa: **100 ảnh =50 CFD+50 HF**, **96 vector** (50 CFD+46 HF), **4 missing_C1**.
Không chọn lại ảnh. Gallery chỉ có shape **(96,236)** float64; counts **(96,4,59)** uint64;
histograms **(96,4,59)** float64. Manifest100 ghi image_id, nguồn, feature_row_index hoặc NULL,
hash contract/spec, provenance và các trạng thái tách riêng. Nối archive/DB/catalog bằng image_id hoặc filename,
không giả định thứ tự hàng giống nhau. SQLite chỉ mở URI `mode=ro&immutable=1` để đọc catalog.

{missing_table}
Mask/support của bốn ảnh lỗi chỉ được đo để chẩn đoán. Không chạy LBP cho bất kỳ vùng nào của ảnh đó;
counts/histograms/vector đều JSON null, không tạo dòng gallery và không zero-fill.
**396/400 ROI valid hình học**, bốn ROI forehead_brow invalid. Cả400 raw masks/hash/pixel-count/support-count
khớp census ROI đã đóng băng. Đây là xác minh tái lập hình học, chưa phải giải phẫu.

## Công thức và các quy ước được giữ nguyên

PDF quy định P8,R2, `gp>=gc`, non-rotation-invariant uniform59 (58 mẫu riêng+198 mã vào bin58),
bốn vùng theo thứ tự và L1 từng vùng; vector236; khoảng cách Chi-square hệ số0.5.
Triển khai dùng đúng các lựa chọn kỹ thuật đã khóa: gray uint32 `(1868B+9617G+4899R+8192)//16384`,
gray uint8 rồi float64; p0 Đông, ngược kim đồng hồ trên ảnh; bán kính2 và ±sqrt(2) float64;
bilinear horizontal lerp rồi vertical lerp, không làm tròn gp/offset. Không epsilon ở bit test,
không padding/reflect. Support đủ21 điểm nguyên trong cùng raw ROI/ảnh. Shared pixels giữ trong từng ROI;
không priority subtraction, không giao mask với skin/hair B. Guard64 tâm là quy ước kỹ thuật, không yêu cầu PDF.
Counts uint64; h=count/N float64, không epsilon L1, không global-L1/L2/Z-score hoặc refit.
Chi-square =`0.5*sum((a-b)^2/(a+b+1e-8))`; epsilon1e-8 là quy ước version của spec, PDF không chốt số này.

`Extractor.extract` và `TrialGallery.extract_query` dùng cùng Context/contract/codebook/support,
hash lệch thì reject. Query adapter nhận BGR256² đã aligned và478 pixel landmarks có provenance do caller cung cấp;
không tự chạy detector hoặc tuyên bố tái tạo alignment gốc. Đã tái trích xuất96 ảnh valid theo query adapter,
khớp bitwise với vector gallery đọc lại; self-distance0. Không tính Top-5 hoặc fusion.

## Số học, histogram và oracle

**{tests['tests_run']} tests đạt**, không skip/failure/error. Codebook đủ256→0..58,
58 uniform riêng/198 nonuniform; test constant255→57, equality bit1, threshold không epsilon,
định hướng không gộp, tất cả256 stencil bit fixtures, grayscale màu, sqrt(2), support21,
ngoài ROI, overlap, missing/invalid, query/gallery lock và hệ số0.5.
Oracle không import/call extractor để tạo expected: Python integer gray, enumerate right rotations cho codebook,
đọc đỉnh float64 từ CSV audit, quét raster riêng, duyệt21 support scalar và nội suy scalar.
Đối chiếu10 ảnh gồm năm case HF bắt buộc, CFD00001 và bốn ảnh chọn seed6112026 trước khi so kết quả:
**{verification['scalar_centres']} tâm /40 histogram**. Sai khác raw_code/counts=0;
max absolute interpolation/histogram error đều **0.0** trên môi trường ghi trong contract_lock.json.
Không suy rộng bitwise equivalence sang mọi backend khác hoặc mặc định skimage.

{region_table}
Mọi counts sum đúng eligible N; mỗi histogram sum nằm trong
`[0.9999999999999998,1.0000000000000002]`; tổng236 trong `[3.999999999999999,4.0]`.
Tất cả hữu hạn, không âm, đúng dimension/dtype. Đã đối chiếu NumPy↔JSON↔gallery và identity mapping.

## Ví dụ tính tay trên ảnh thật

Ảnh `cfd_final_00001.png`, vùng forehead_brow, tâm `(106,61)` là phần tử giữa danh sách tâm row-major,
không chọn bằng retrieval. BGR=(148,190,223):
`floor((1868*148+9617*190+4899*223+8192)/16384)=195`.

{hand_table}
Bits theo p0→p7 là `10111111`; code=`1+4+8+16+32+64+128=253`.
Chuỗi có7 bit1, run_start=2; label=`1+8*(7-1)+((-2)%8)=55`.
Ví dụ p1: stencil `(189,194;196,193)`, tx=0.41421356237309226,ty=0.5857864376269077;
upper=191.07106781186548,lower=194.75735931288074,
gp=193.23044737829954<195→bit0. Không round gp thành uint8.

## Trạng thái giải phẫu và dataset

- Số học: PASS trong phạm vi thử nghiệm và oracle đã nêu.
- Hình học:396 valid/4 invalid trong400 ROI, không sửa polygon.
- Giải phẫu: cả100 vẫn UNVERIFIED/PROVISIONAL, kể cả96 có vector.
- Dataset: HF00333/HF00561 có mặt phụ, HF00722 có tay che miệng, vẫn giữ và tạo vector kỹ thuật;
  không coi thành công C1 là đã giải quyết vi phạm PDF. HF00209 thiếu B tóc nhưng có C1 kỹ thuật;
  thiếu B không tự làm thiếu C1. HF00694 khăn/kính vẫn cần review, không tự gắn nhãn vi phạm.
- Vector:96 valid_C1,4 missing_C1, không đưa C1 vào SQLite production.

Trước khi chạy1438 chính thức: cần xác nhận có thẩm quyền endpoint/frame trái–phải và mô giải phẫu;
xử lý undercoverage proxy lông mày (audit toàn kho44.29–67.14%, chưa phải skin ground truth);
chốt quy trình giải quyết bốn forehead tự giao, occlusion tóc/tay/kính/vải và dataset vi phạm;
review candidate contract bằng annotation độc lập rồi version/hash mới nếu được chấp nhận.
Proposal v0.3 chưa active và vẫn có case HF00198 tự giao. Không chọn ROI bằng Top-5.
Mapping canonical478→68 chưa có trong PDF; lệch topology mũi MP1/MP4 đã báo cáo vẫn giữ nguyên.

## Artifact và tính toàn vẹn

Output riêng: [trial100_spec_v0_1](../outputs/C1_lbp/trial100_spec_v0_1/).
[Manifest100](../outputs/C1_lbp/trial100_spec_v0_1/manifest.json),
[gallery96](../outputs/C1_lbp/trial100_spec_v0_1/gallery_vectors.npy),
[counts](../outputs/C1_lbp/trial100_spec_v0_1/counts.npy),
[histograms](../outputs/C1_lbp/trial100_spec_v0_1/histograms.npy),
[missing](../outputs/C1_lbp/trial100_spec_v0_1/missing_C1.json).
Mỗi ảnh có JSON riêng trong images/ với vector/counts/histograms hoặc null,
mask pixels/support, hash ảnh/landmark row, included_for và status.
Nguồn landmarks478 đã được xác thực theo hash archive/audit; không chạy lại MediaPipe.
Model asset hash được ghi, phiên bản distribution MediaPipe lịch sử không có log nên để null.

**{protected} file đã có được so SHA-256 trước/sau:0 thay đổi/thiếu**. Bao gồm PDF,1438 ảnh nguồn,
metadata, A/B source/mapping/vectors/stats/calibration/query v1/v2, ROI outputs và các SQLite cũ/backup/restore.
[Baseline đầy đủ](../outputs/C1_lbp/trial100_spec_v0_1/evidence/baseline_before.json),
[kết quả integrity](../outputs/C1_lbp/trial100_spec_v0_1/evidence/final_scope.json),
[manifest file mới](../outputs/C1_lbp/trial100_spec_v0_1/evidence/created_files_manifest.json).
Giữ nguyên cả README/spec cũ như hồ sơ lần trước; báo cáo này ghi nhận bước technical trial mới.

Lệnh PowerShell thực tế đã chạy thành công từ repository root:

{commands}
Runner, verifier và test logger từ chối ghi đè output đã hoàn tất. Các lệnh là hồ sơ thực thi;
không xóa artifact để chạy lại. Thử nghiệm tương lai cần version/output mới hoặc checkout độc lập.
Lần wrapper PowerShell `2>&1|Tee-Object` báo exit1 vì unittest dùng stderr mặc dù26 tests OK;
đã dùng runner stdout riêng, chạy26 tests thành công exit0. Không đổi công thức để làm test pass.
Không triển khai C2/fusion, không ghi CSDL, không sửa kết quả A+B; hash của chúng bất biến.
"""
    write_text_new(ROOT / 'docs/C1_LBP_TRIAL100_REPORT.md', report)
    numerical = '# Xác minh số học C1 LBP236 — technical trial100\n\n' + preamble + f"""
## Bằng chứng kiểm thử độc lập

**{tests['tests_run']} tests đạt**,0 failure/error/skip;
[unit/integration log](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/unit_integration_tests.log),
[JSON trạng thái](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/unit_integration_tests.json).
Tests nằm ở tests/test_c1_lbp236.py và tests/test_c1_trial100_integration.py.
Oracle features/C1_lbp/verification/scalar_oracle.py không import target;
expected codebook được dựng bằng run bit1 và phép quay phải, không gọi LUT builder production.
Expected gray dùng Python int từng pixel; stencil/support duyệt scalar thay cv2.erode;
mask quét full256² với contour float32 của vertex CSV frozen thay dùng polygon builder target.
OpenCV pointPolygonTest là primitive chung bắt buộc theo contract; không tuyên bố oracle raster hoàn toàn khác backend.
Expected bilinear là phép lerp scalar có cùng thứ tự quy định, không dùng phép nội suy NumPy production.

Codebook kiểm đủ256 mã,58 uniform riêng và198 mã vào bin58; test stencil dựng riêng đủ256 bit words;
orientation khác nhau có nhãn khác, không dùng10-bin rotation invariant.
Gray fixtures blue29,green150,red76,white255,black0 và fixture ngẫu nhiên xác nhận tránh overflow.
Constant73 cho raw255/bin57; equality bit1; chênh thấp1e-12 phải bit0.
Bilinear ở sqrt(2) kiểm analytic affine plane và fixture scalar; không round5 decimal/intensity.
Support21 gồm5+4+3+4+5 điểm; bỏ bất kỳ điểm nào làm tâm không eligible, bỏ điểm(1,0) không làm mất tâm.
Ngoài raw ROI không ảnh hưởng counts; hai polygon trùng vẫn giữ đủ histogram cả hai.
Self-cross/missing/<64/nonfinite input đi missing cả ảnh; unit test chặn mọi lời gọi LBP ở self-cross.
Chi-square symmetric/nonnegative/self0, fixture bốn nhóm one-hot khác bin cho `4/(1+1e-8)`, xác minh hệ số0.5.
Reject vector global-L1 sai schema. Query/gallery hash mismatch phải reject, không fit tham số.

## Kết quả dữ liệu thật

100 bản ghi serialized được kiểm;96 vector236 float64 và counts uint64 round-trip chính xác.
Cả96 query adapter tái trích đúng bitwise gallery; không xếp hạng.
Cả400 raw masks/pixels/support khớp census đóng băng; bốn negative không có dòng vector.
Oracle10 ảnh cố định: {', '.join(verification['scalar_subset'])}.
Seed6112026 chỉ chọn bốn ảnh bổ sung từ manifest, không dùng output retrieval hoặc tối ưu ROI.
Đã tính scalar toàn bộ tâm eligible trên10 ảnh: **{verification['scalar_centres']} tâm,40 histogram**,
so đủ raw words và8 giá trị gp mỗi tâm. Raw code/count mismatch=0;
max |gp_production−gp_scalar|=0.0, max |hist_production−hist_scalar|=0.0.
[JSON đầy đủ](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/numerical_verification.json).
Đây là equivalence trên môi trường NumPy/OpenCV/Python ghi trong lock; không khẳng định bitwise trên mọi platform.

{region_table}
Mỗi count sum=N; mỗi nhóm L1 nằm `[0.9999999999999998,1.0000000000000002]`,
vector sum `[3.999999999999999,4.0]`; hữu hạn, nonnegative, C1 đúng236 chiều,
không sử dụng stats150/144 hoặc global normalization của A/B.

## Ví dụ truy vết phép tính

`cfd_final_00001.png`, forehead_brow, tâm(106,61), BGR148/190/223→gray195.

{hand_table}
Bits p0→7=`10111111`, code253, run_start2, ones7→bin55.
Ở p1: gray stencil(189,194;196,193), tx0.41421356237309226,ty0.5857864376269077,
lerp ngang191.07106781186548/194.75735931288074, lerp dọc193.23044737829954<195→0.
Tất cả tọa độ, stencil và kết quả trung gian nằm ở
[hand_calculation.json](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/hand_calculation.json).

## Giới hạn và bảo toàn

{missing_table}
396 ROI valid hình học không xác nhận anatomy; cả100 giữ PROVISIONAL.
HF333/HF561 mặt phụ và HF722 tay che vẫn là vi phạm dataset đã biết; HF209 thiếu B tóc nhưng C1 kỹ thuật valid;
HF694 kính/khăn còn UNVERIFIED. Không sửa mapping A, ROI, ảnh hoặc loại ảnh khó.
Contract raw v0.2 ưu tiên cao hơn proposal v0.1 cũ về overlap: không priority subtraction.
Proxy lông mày undercoverage và endpoint canonical478→68/topology mũi MP1/MP4 chưa giải quyết.
Trước chạy1438 chính thức cần review giải phẫu, occlusion và contract có quyết định được ghi nhận;
không dùng numerical PASS làm chứng nhận toàn hệ thống.

{protected} protected file SHA-256 giữ nguyên,0 thiếu/đổi.
[final_scope.json](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/final_scope.json),
[baseline](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/baseline_before.json),
[nguồn/phiên bản implementation](../../outputs/C1_lbp/trial100_spec_v0_1/evidence/implementation_provenance.json).
Không có sửa số học sau khi oracle chạy; chỉ thay import hashlib tĩnh và sửa logger PowerShell.
Không cài thư viện, không rerun MediaPipe, không ghi SQLite hoặc tạo C2/calibration/fusion/ranking.
Ảnh chưa aligned hoặc thiếu landmarks có provenance nằm ngoài phạm vi adapter; không suy đoán alignment lịch sử.

Lệnh thành công (repository root):

{commands}
Xem [báo cáo trial](../C1_LBP_TRIAL100_REPORT.md) về cấu trúc output và giới hạn giải phẫu/dataset.
"""
    write_text_new(ROOT / 'docs/audits/C1_LBP_NUMERICAL_VERIFICATION.md', numerical)
    write_text_new(OUT / 'README.md', f"""# C1 trial100

EXPERIMENTAL_TECHNICAL_TRIAL — ROI_ANATOMY_STATUS=PROVISIONAL.

100 image records;96 vectors;4 missing. See [report](../../../docs/C1_LBP_TRIAL100_REPORT.md).
`gallery_vectors.npy`: float64[96,236], `counts.npy`: uint64[96,4,59], `histograms.npy`: float64[96,4,59].
Join `manifest.json` by image_id and feature_row_index (missing=null), never by row position in a source catalog.
Per-image JSON in images/ preserves both hashes, measurements, counts/histograms/vector or null and missing reasons.
`contract_lock.json` pins semantics/environment. Negative masks are diagnostic only, no LBP or partial vectors.
`evidence/` holds independent checks, tests, hand calculation, original hash baseline, integrity and new files manifest.
Do not import into production SQLite. Old historical specs/README remain frozen; this directory records the authorized new trial.

Read-only usage from repository root:

```python
from features.C1_lbp.src.gallery import TrialGallery
g = TrialGallery('outputs/C1_lbp/trial100_spec_v0_1')
vector = g.vector('cfd_final_00001')
# g.vector('hf_merged_00069') raises KeyError, no zero-fill.
# g.extract_query(bgr256_uint8, pixel_landmarks478_float32, image_id='query')
# Caller must supply aligned image and authenticated landmark provenance.
```

The trial runner/test logger/verifier refuse overwrite. Preserve this completed version.
""")
    new_paths = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    created = []
    for path in sorted(new_paths):
        p = ROOT / path
        if p.is_file():
            created.append(dict(path=path, bytes=p.stat().st_size, sha256=sha256(p)))
    write_json(OUT / 'evidence/created_files_manifest.json', dict(context.lock, self_excluded=True, files=created))
    print('Finalized:', protected, 'old files unchanged;', len(created), 'new files manifested;26 tests PASS')


if __name__ == '__main__':
    main()
