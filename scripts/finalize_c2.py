"""C2 evidence, report and final baseline seal; no algorithm changes."""
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from features.C2_hog.src import root_hog as hog
from features.C2_hog.src.common import BASE,read_json,read_csv,write_json,baseline_check
from retrieval.search_c2 import C2Gallery


def text_new(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(value)


def pipeline_figure(gallery):
    identity='cfd_final_00001';image=cv2.imread(gallery.by_id[identity]['image_path'])
    result=hog.extract_c2(image);roi=hog.extract_face_roi(image)
    full=image.copy();cv2.rectangle(full,(48,32),(207,223),(0,190,255),1)
    gray=result['gray'].astype(np.uint8)
    # Display transformations only, never passed to extraction or retrieval.
    mag=np.rint(result['magnitude']/max(1.,float(result['magnitude'].max()))*255).astype(np.uint8)
    gx=np.rint(np.clip(result['gx']/2+128,0,255)).astype(np.uint8)
    gy=np.rint(np.clip(result['gy']/2+128,0,255)).astype(np.uint8)
    panels=[]
    for title,pixels in [('Original + locked crop',full),('ROI160w x192h + cell grid',roi),
                        ('Integer gray',gray),('Magnitude scaled for display',mag),('Gx signed display +128',gx),('Gy signed display +128',gy)]:
        if pixels.ndim==2:pixels=cv2.cvtColor(pixels,cv2.COLOR_GRAY2BGR)
        panel=np.full((330,320,3),250,np.uint8)
        # Preserve aspect ratio: ROI160x192 shown240x288, no feature-image resize.
        if pixels.shape[:2]==(192,160):
            rendered=cv2.resize(pixels,(240,288),interpolation=cv2.INTER_NEAREST);panel[30:318,40:280]=rendered
            if 'grid' in title:
                for j in range(1,4):
                    cv2.line(panel,(40+j*60,30),(40+j*60,317),(0,220,220),1)
                    cv2.line(panel,(40,30+j*72),(279,30+j*72),(0,220,220),1)
        else:panel[35:291,32:288]=pixels
        cv2.putText(panel,title,(8,21),0,.46,(20,20,20),1,cv2.LINE_AA);panels.append(panel)
    path=BASE/'evidence/cfd_final_00001_pipeline.png'
    if path.exists():raise FileExistsError('Pipeline evidence exists')
    if not cv2.imwrite(str(path),np.vstack([np.hstack(panels[:3]),np.hstack(panels[3:])])):raise OSError('Could not save figure')


def main():
    if (BASE/'evidence/created_files_manifest.json').exists():raise FileExistsError('C2 final evidence exists')
    trial=read_json(BASE/'trial100/verification.json');full=read_json(BASE/'full_v1/verification.json')
    assert trial['numerical_status']==full['numerical_status']=='PASS'
    assert all(trial[k]==full[k]==v for k,v in hog.lock().items())
    gallery=C2Gallery();baseline=baseline_check();manifest=gallery.manifest
    query_files=sorted((BASE/'full_v1/queries').glob('*/results.json'));assert len(query_files)==6
    expected={r['query']:r['top5'] for r in full['scalar_rankings']};tiles=0
    for path in query_files:
        result=read_json(path);query=result['query']['image_id'];rows=result['results']
        assert [r['image_id'] for r in rows]==expected[query]
        csv_rows=read_csv(path.parent/'results.csv')
        assert [r['image_id'] for r in rows]==[r['image_id'] for r in csv_rows]
        assert [r['distance'] for r in rows]==[float(r['distance']) for r in csv_rows]
        png=cv2.imread(str(path.parent/'comparison.png'));assert png.shape==(672,768,3)
        for i,row in enumerate([result['query']]+rows):
            x,y=(i%3)*256,40+(i//3)*316
            np.testing.assert_array_equal(png[y:y+256,x:x+256],cv2.imread(row['image_path']));tiles+=1
    pipeline_figure(gallery)
    hand=read_json(BASE/'full_v1/hand_calculation.json')
    max_euclid=max(r['scalar_distance_max_abs_error'] for r in full['scalar_rankings'])
    hashes='| Artifact | SHA-256 |\n|---|---|\n'
    for rel in ['trial100/features_C2.npy','trial100/verification.json','full_v1/features_C2.npy','full_v1/raw_cells.npy',
                'full_v1/raw_blocks.npy','full_v1/root_blocks.npy','full_v1/feature_rows.csv','full_v1/extraction_status.csv',
                'full_v1/feature_schema.json','full_v1/manifest.json','full_v1/verification.json']:
        hashes+=f'| {rel} | `{hog.sha256(BASE/rel)}` |\n'
    examples=''
    for identity in ['cfd_final_00001','hf_merged_00209']:
        rows=read_json(BASE/'full_v1/queries'/identity/'results.json')['results']
        examples+=f'\n### {identity}.png\n\n| Rank | Ảnh | Euclid324 |\n|---:|---|---:|\n'
        for row in rows:examples+=f"| {row['rank']} | {row['filename']} | {row['distance']:.12f} |\n"
        examples+=f'\n[PNG](../outputs/C2_hog/full_v1/queries/{identity}/comparison.png) · [CSV](../outputs/C2_hog/full_v1/queries/{identity}/results.csv) · [JSON](../outputs/C2_hog/full_v1/queries/{identity}/results.json).\n'
    prefix=f'''Ngày thực hiện: **24/11/2026**, Asia/Saigon. **TECHNICAL_PROTOTYPE_FIXED_CONVENTIONS**.
Nguồn cao nhất `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc trực tiếp §2.4.1–2.4.3 và§2.5.2.
Spec content SHA `{hog.SPEC_PIN}`; spec file SHA `{hog.lock()['spec_file_sha256']}`;
kernel SHA `{hog.lock()['implementation_sha256']}`; preprocessing `{hog.PREPROCESSING}`.
Spec/kernel được pin trước synthetic tests/trial/retrieval; không thay crop/parameter để cải thiện Top-5.
Không cài thư viện,không chạy alignment hoặc detector,không refit A/B hoặc chạy lại C1 full batch.
'''
    report='# C2 Root-HOG324 — triển khai và truy vấn toàn kho\n\n'+prefix+f'''
## Kết quả thực tế và gate

| Giai đoạn | Input | Valid | Missing | Scalar oracle | Tests |
|---|---:|---:|---:|---|---:|
| Synthetic trước trial | Fixtures | — | — | Random fixture đối chiếu đủ intermediate |15 PASS |
| Trial100 |100=50CFD+50HF |{trial['valid']} |{trial['missing']} |Toàn100 ảnh,3.002.000 tâm gradient |{trial['tests_run']} PASS |
| Full_v1 |1438=710CFD+728HF |{full['valid']} |{full['missing']} |12 case cố định,360.240 tâm;mọi intermediate full được kiểm |{full['tests_run']} PASS |

Trial dùng đúng manifest C1 trial đã thực thi `outputs/C1_lbp/trial100_spec_v0_1/input_trial100_manifest.json`,
giữ đủ ID/thứ tự và4 ảnh C1 v0.2 từng thiếu; không thay bằng bộ anatomical-review100.
Việc C2 valid trên4 ảnh đó không sửa lịch sử/ROI C1 hoặc chứng nhận ảnh không lỗi dataset.
Full batch chỉ chạy sau trial verification PASS và spec/kernel locks khớp.0 missing là kết quả thực tế,
không áp expectation hoặc zero-fill. Mỗi input có extraction_status.csv kể cả nếu không có vector.

## Đối chiếu PDF và các lựa chọn prototype

[Đặc tả và bảng PDF_EXACT/IMPLEMENTATION_DETAIL/DEVIATION/UNVERIFIED](C2_ROOT_HOG_324_SPEC.md)
ghi đủ từng yêu cầu. Đã xác minh ROI160×192,cells4×4 kích thước40×48,sai phân trung tâm PDF,
magnitude sqrt,hướng unsigned,vote magnitude/9 bins,2×2 block stride1,9×36=324,Root theo tổng block,
global L2 và Euclid324. Không có sai lệch yêu cầu rõ được xác nhận trong các kiểm tra này.
Không gọi convention chưa có trong PDF là PDF_EXACT hoặc dùng PASS làm chứng nhận anatomy/relevance.

Repository trước nhiệm vụ chỉ có placeholder C2 và hồ sơ nói chưa triển khai; không tìm được pipeline/provenance
crop160×192 thực sự. Dùng fallback được user chỉ định: **bgr[32:224,48:208]**, x48…207,y32…223 inclusive,
không resize input hoặc chạy face alignment mới. Center crop là IMPLEMENTATION_DETAIL,không phải tọa độ PDF
hay anatomical segmentation. Reviewer chưa chứng nhận extent/occlusion crop trên1438 ảnh.

Giữ gray nguyên C1: uint32 `(1868B+9617G+4899R+8192)//16384`,cast uint8 rồi float64;
không import C1 vector/kernel vào production C2. Standard-library SQLite catalog chỉ đọc
`mode=ro&immutable=1`; C2 không dùng landmarks478 hoặc môi trường Uniface/MediaPipe vì crop fixed không cần chúng.
I/O/hash/image_id patterns tái sử dụng theo cách đã kiểm của C1 nhưng không dùng công thức LBP cho HOG.

## Các bước số học thực tế

| Bước | Shape cho một ảnh | Công thức/ordering |
|---|---|---|
| Input |256×256×3 uint8 BGR |Ảnh source đã aligned trong dataset |
| Crop |192×160×3 uint8 |x[48,208),y[32,224) |
| Gray |192×160 float64 |Integer rounding đã khóa |
| Gx,Gy |192×160 mỗi mảng |I(x+1,y)−I(x−1,y);I(x,y+1)−I(x,y−1) |
| Magnitude,orientation |192×160 mỗi mảng |sqrt(Gx²+Gy²);degrees(atan2(Gy,Gx))%180 |
| Raw cells |4×4×9 float64 |Hard20° bin;pixel chỉ vote vào cell(y//48,x//40) |
| Raw blocks |9×36 float64 |block_y,x row-major;local2×2 cell row-major;bin innermost |
| Root blocks |9×36 float64 |sqrt(h/(sum(block)+1e-8)) |
| Final |324 float64 |Ghép9 block,row-major rồi chia exact global L2 |

Boundary convention: chỉ1≤x≤158,1≤y≤190 góp vote;toàn perimeter1px có Gx=Gy=magnitude0.
30020 tâm/ảnh,không padding/reflect/lấy pixel ngoài ROI. Cell vẫn40×48,không thay shape vì bỏ vote biên.
Unsigned [0,180),180/−180→0;PDF in[0°,180°],half-open wrapping là convention để không sinh bin10.
Hard bins[0,20),…,[160,180),không orientation/spatial interpolation. Tích lũy float64 theo y,x.
Block epsilon1e-8 là quy ước chứ PDF không chốt số. Không L2-Hys,cell L1,block L2,Sobel,RootSIFT hoặc clip0.2.
Final L2 không cộng epsilon. Zero block→root0 đúng công thức,nhưng zero final norm→missing_C2 có reason,
không vector giả. Invalid shape/dtype/nonfinite không impute,nan_to_num hoặc repair.

## Kiểm thử và oracle độc lập

Scalar oracle không import production: Python integer gray,crop indices cố định,loops sai phân,
math.sqrt/math.atan2,hard-bin vote,math.fsum tổng block và L2. Tolerance chốt trong spec trước trial,
không điều chỉnh để làm pass. Trial100 so toàn3.002.000 tâm;full12 case so360.240 tâm.
Max abs error gray,Gx,Gy,magnitude,orientation,cell histogram và raw block=0.0 trên môi trường hiện tại;
Root block tối đa={trial['max_abs_errors']['root_blocks']!r},finalvector={trial['max_abs_errors']['vector']!r}.
Mọi full saved cells→raw blocks→Root→L2 reconstruction khớp bitwise production,
và100 trial vectors khớp bitwise full theo image_id dù thứ tự metadata khác.
Full L2 norm min/max **{full['L2_min']!r}/{full['L2_max']!r}**;tất cả finite,float64,nonnegative,324 chiều.

118 tests cuối:23 C2(15 math+8 pipeline),95 regression A/B/C1 hiện có,0 failures/errors/skips.
Kiểm crop/16 cells,Gx/Gy khác Sobel,ngang/dọc/chéo,9 bins/wrap,unsigned,block layout36,
Root khác block-L2/Hys,epsilon/zero/nan,Euclid/self0/symmetry,ID permutation,ties và output source lock.
Ảnh ngoài gallery bị từ chối; ảnh trùng tên nhưng khác hash không được giả là ảnh aligned cũ.
Trên12 query cố định×1438 vectors,Euclid scalar đối chiếu17256 distances,max error **{max_euclid!r}**,
Top-5 khớp independent ranking. Không dùng cosine hoặc Chi-square.
Regressions có fit/calibration fixtures trong memory/temp,không refit artifact A/B và không ghi C1 full output.

## Ví dụ tính tay trên ảnh thật

CFD00001,tâm ROI(x80,y96) tương ứng source(x128,y128),chọn cố định không dựa query results.
Gray trái/phải/trên/dưới=201/205/199/201. **Gx=205−201=4,Gy=201−199=2**;
magnitude=sqrt(20)=**{hand['magnitude']!r}**;
orientation=atan2(2,4)=**{hand['unsigned_orientation']!r}°**,hard bin floor(theta/20)=**1**.
Pixel góp4.47213595499958 vào cell(row2,col2),bin1;hist tổng cell-bin từ mọi pixel={hand['total_cell_bin']!r}.
Block index4 có origin cell(1,1),component28 ứng với cell(2,2),bin1.
S_block={hand['block_sum']!r};Root=sqrt({hand['total_cell_bin']!r}/(S+1e-8))=
**{hand['expected_root_component']!r}**;sau global L2,component cùng vị trí=
**{hand['normalized_final_component']!r}**. Không lấy riêng magnitude pixel làm histogram cả cell.
[Hand calculation JSON](../outputs/C2_hog/full_v1/hand_calculation.json),
[pipeline PNG](../outputs/C2_hog/evidence/cfd_final_00001_pipeline.png).
Magnitudes/Gx/Gy trong PNG được scale chỉ để hiển thị,không đưa ảnh display đó vào extractor.

## Artifact và truy vấn

Trial: [outputs/C2_hog/trial100](../outputs/C2_hog/trial100/).Full: [full_v1](../outputs/C2_hog/full_v1/).
Đủfeatures_C2.npy,feature_rows.csv,extraction_status.csv,feature_schema.json,manifest.json,verification.json.
Bổ sung raw_cells.npy,raw_blocks.npy,root_blocks.npy,ROI coords trong từng row và source/spec/kernel/preprocess hashes.
ID joins tường minh;full orderimage_id tăng dần,trial theo manifest gốc,không dựa vị trí hàng catalog.
Missing nếu có phải có reason và không có feature row;không zero-fill.

`retrieval/search_c2.py --image <gallery ID/filename/path> --top-k 5` reuse vector lưu,
check schema/hash/preprocessing match,loại self theo image_id,sort(distance,image_id) tăng dần.
Không loại tất cả zero-distance duplicates. CLI chỉ hỗ trợ gallery,không giả preprocessing/alignment ảnh mới.
Mỗi run CSV/JSON/PNG trong namespace riêng,thư mục có sẵn sẽ bị từ chối ghi đè.

{examples}
Đã chạy thêmCFD00069,HF00001,HF00198,HF00722,tổng6 runs. CSV/JSON round-trip và36 source image tiles
trong PNG khớp pixel gốc. Top-5 này chỉ kiểm chức năng,khoảng cách là cấu trúc gradient trong crop,
không phải bằng chứng identity/relevance cao;không điều chỉnh thuật toán sau khi xem.

## Hash và bằng chứng bảo toàn

{hashes}
Spec JSON/lock,full/trial manifests pin version/source bytes và array artifacts;manifest file mới cuối
pin thêm reports/tests/query figures và tự loại chính nó để tránh vòng hash.
**{len(baseline)} file cũ giữ nguyên SHA-256 trước/sau**:PDF,dataset,A/B v2,stats/calibration,A+B outputs,
C1 full_v04/trial vectors/queries,SQLite/eye metadata và các hồ sơ review/ROI đã có.
[Baseline](../outputs/C2_hog/evidence/baseline_before.json),[final scope](../outputs/C2_hog/evidence/final_scope.json),
[created manifest](../outputs/C2_hog/evidence/created_files_manifest.json).
Không cập nhật production DB,không chạy lại C1 full batch,không triển khai fusion bốn bộ.

## Lệnh PowerShell thực tế và giới hạn

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C2_hog.src.batch --stage trial
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c2.py --stage trial
.\.venv311\Scripts\python.exe -X utf8 -B -m features.C2_hog.src.batch --stage full
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_c2.py --stage full
foreach ($c2Query in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00209.png','hf_merged_00722.png')) {{
    .\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c2.py --image $c2Query --top-k 5
    if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
}}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_c2.py
```

Preflight15 tests được chạy và ghi evidence/preflight_tests.log trước trial;trial oracle PASS trước full.
Các lệnh trên đã chạy thành công;rerun query phải dùng `--output <thư_mục_mới>`,không xóa output cũ để overwrite.
Kernel/spec pin giữ nguyên qua toàn bộ run. Giới hạn còn UNVERIFIED:crop anatomy/occlusion,alignment lịch sử,
endpoint dữ liệu và relevance labels. Các vi phạm dataset đã biết vẫn tồn tại;không crop/inpaint/xóa nguồn
để che chúng(center crop là input C2 versioned,không sửa file dataset). Không tuyên bố fully compliant
theo mọi diễn giải hoặc độ chính xác truy hồi cao chỉ từ numeric PASS.
'''
    text_new(ROOT/'docs/C2_FULL_IMPLEMENTATION_REPORT.md',report)
    numeric='# C2 Root-HOG324 — kiểm chứng số học độc lập\n\n'+prefix+f'''
## Gating và phạm vi kiểm tra

Preflight15 tests trước trial. Trial100 giữ đúng C1 manifest đã chạy,100 valid/0 missing.
Oracle independent toàn100 ảnh,30020 tâm/ảnh =3.002.000. Chỉ sau trial verification PASS cùng spec/kernel
mới chạy1438 ảnh,1438 valid/0 missing,710CFD+728HF. Full oracle12 case cố định,360.240 tâm.
Các stage đều lưu status cho từng input và rows chỉ cho valid,không ép success hoặc zero-fill.

| Intermediate | Shape mỗi ảnh | Verification |
|---|---|---|
| ROI BGR/gray |192×160×3 /192×160 |Crop đúng pixels,integer gray giống convention C1 |
| Gx,Gy,magnitude,theta |192×160 |Công thức PDF,border skip cố định,unsigned mod180 |
| Cells |4×4×9 |Hard bins20°,vote magnitude,row-major |
| Raw/Root blocks |9×36 |Sliding3×3,local2×2,row-major;sum denominator riêng block |
| Final |324 float64 |Exact global L2,norm min/max{full['L2_min']!r}/{full['L2_max']!r} |

Oracle không import/call production để tạo expected. Python int gray,loops/math gradient,
histogram accumulation vàmath.fsum total/Root/L2. Gradient vàhist raw maxabs error0.0;
Root block={trial['max_abs_errors']['root_blocks']!r},final={trial['max_abs_errors']['vector']!r}.
Tolerances đã khóa trước trial:gray/Gx/Gy exact,magnitude/angle1e-12,cells1e-8abs/1e-13rel,
Root/vector5e-14abs,L2 norm1e-12abs,Euclid1e-13abs. Không thay convention/tolerance theo results.
100 trial vectors trong full khớp bitwise bằng image_id,không metadata positional zip.
Mọi full stored raw/Root/final arrays được reconstruct và kiểm kiểu/finite/nonnegative/dimension.

## Tests và distance

118 tests PASS,0 failure/error/skip:23 C2+95 regression A/B/C1. Kiểm9 bins/20°boundaries,
180wrap,horizontal/vertical/diagonal,difference not Sobel,16 cells40×48,9 blocks36,epsilon,
Root khácL2/Hys,zero block vàzero final→missing,NaN/shape bad,magnitude votes,source ID permutation,
query lock mismatch,self exclusion,stableties vàEuclid số học.
Euclid scalar=math.sqrt(math.fsum((float(a)-float(b))**2)),không cosine/squared-only/Chi-square.
12×1438=17256 distances full,maxabs error{max_euclid!r},self0,12 Top-5 khớp scalar order.
[Full verification](../../outputs/C2_hog/full_v1/verification.json),
[trial verification](../../outputs/C2_hog/trial100/verification.json),
[full118 tests log](../../outputs/C2_hog/full_v1/tests.log).

## Tính tay trên CFD00001

ROI(80,96)→source(128,128).Gray left/right/up/down=201/205/199/201;
Gx4,Gy2,m=sqrt20={hand['magnitude']!r},angle26.56505117707799°,bin1.
Cell(y2,x2) nhận magnitude của pixel này;hist tổng cell-bin={hand['total_cell_bin']!r}.
Block4 origin(1,1),component28,S={hand['block_sum']!r};
Root=sqrt(h/(S+1e-8))={hand['expected_root_component']!r};global L2 component={hand['normalized_final_component']!r}.
[JSON trung gian](../../outputs/C2_hog/full_v1/hand_calculation.json),
[hình pipeline](../../outputs/C2_hog/evidence/cfd_final_00001_pipeline.png).

## Quy ước và phần chưa chứng minh

Các công thức/parameters rõ trongPDF được đối chiếu tại [spec](../C2_ROOT_HOG_324_SPEC.md).
Center crop(48,32,208,224),gray integer,border exclusion,hard bins,half-open180→0,layout vàepsilon1e-8
là IMPLEMENTATION_DETAIL. PDF ghi unsigned[0°,180°],không chốt cách biểu diễn endpoint vote;
wrapping0 là convention được user cho phép chọn,không thêm bin10.
Crop anatomy/occlusion vàrelevance/accuracy không có ground truth đầy đủ,nênUNVERIFIED.
Không có DEVIATION với yêu cầu rõ được xác nhận;không tự coi mọi convention làPDF_EXACT.
Không thay HOG thànhLBP,RootSIFT,L2-Hys,Sobel hoặcL2 từng block. Không sửa luật sau khi nhìn Top-5.

## Tính toàn vẹn

{hashes}
6 query CLI CSV/JSON/PNG đã kiểm round-trip và36 tile pixel nguồn,không thay gallery.
Baseline{len(baseline)} file cũ SHA-256 trước/sau0 đổi/thiếu,gồmA/B/C1/PDF/dataset/SQLite/eye metadata,
stats/calibration vàkết quả cũ. Regressions chỉ fit fixture/temp,không refit gallery stats hoặc rerun C1 full.
[Baseline](../../outputs/C2_hog/evidence/baseline_before.json),
[final scope](../../outputs/C2_hog/evidence/final_scope.json),
[new files manifest](../../outputs/C2_hog/evidence/created_files_manifest.json).
Không update SQLite,không fusion. [Lệnh thực tế vàTop-5](../C2_FULL_IMPLEMENTATION_REPORT.md).
'''
    text_new(ROOT/'docs/audits/C2_NUMERICAL_VERIFICATION.md',numeric)
    text_new(BASE/'README.md','''# C2 Root-HOG324

Fixed technical prototype; crop anatomy/relevance unverified. Spec and arithmetic pinned before trial.
trial100:100 valid,0 missing;full_v1:1438 valid,0 missing (710CFD,728HF).
features_C2.npy float64[N,324];raw_cells.npy[N,4,4,9];raw_blocks.npy/root_blocks.npy[N,9,36].
feature_rows.csv uses image_id and feature_row_index;all inputs have extraction_status.csv.
ROI BGR[32:224,48:208],no new alignment,hard20-degree bins,Root block epsilon1e-8 then exact global L2.
Standalone Euclid324 query only;source A/B/C1/SQLite/PDF/dataset and old outputs remain unchanged.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c2.py --image cfd_final_00001.png --top-k 5 --output outputs/C2_hog/full_v1/queries/cfd_final_00001_run2
```

Use fresh output paths. Gallery images only;do not assume external images have historical alignment.
See docs/C2_ROOT_HOG_324_SPEC.md,docs/C2_FULL_IMPLEMENTATION_REPORT.md and docs/audits/C2_NUMERICAL_VERIFICATION.md.
''')
    final=baseline_check()
    write_json(BASE/'evidence/final_scope.json',dict(schema_id='C2_FINAL_SCOPE_v1',**hog.lock(),
        trial_processed=100,trial_valid=trial['valid'],trial_missing=trial['missing'],full_processed=1438,
        full_valid=full['valid'],full_missing=full['missing'],preflight_tests=15,final_regression_tests=118,
        old_files_checked=len(final),old_files_changed=[],baseline_sha256=hog.sha256(BASE/'evidence/baseline_before.json'),
        query_CSV_JSON_PNG_roundtrips=6,original_image_tiles_verified=tiles,C1_full_batch_rerun=False,
        new_alignment_or_detector_runs=0,SQLite_writes=0,A_B_refit=False,fusion=False,
        crop_status='UNVERIFIED_CENTER_CROP_PROTOTYPE',accuracy_claimed=False))
    files=[]
    names=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    for name in sorted(names):
        p=ROOT/name
        if p.is_file() and str(p.resolve()) not in baseline:files.append(dict(path=name,bytes=p.stat().st_size,sha256=hog.sha256(p)))
    write_json(BASE/'evidence/created_files_manifest.json',dict(schema_id='C2_CREATED_FILES_v1',self_excluded=True,files=files))
    print('C2 complete:',len(files),'new files;',len(baseline),'old files unchanged;trial/full/oracle/118 tests/6 queries PASS',flush=True)


if __name__=='__main__':main()
