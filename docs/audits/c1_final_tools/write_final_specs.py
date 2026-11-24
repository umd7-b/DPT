"""Finalize PROVISIONAL contracts, complete reports and immutable-input proof."""
from pathlib import Path
from collections import Counter
import json
import re

import cv2
import numpy as np

import validate_roi_all as audit
from shared.report_v2 import read_json,read_csv,write_json

ROOT=audit.ROOT
OUT=audit.OUT
DOC=ROOT/'docs'


def table(headers,rows):
    def cell(x):return str(x).replace('|','∣').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(cell,r))+' |' for r in rows])


def save(path,text):path.write_text(text.strip()+'\n',encoding='utf-8')


def main():
    s=read_json(OUT/'summary.json');v=read_json(OUT/'verification.json')
    contract=read_json(OUT/'contract_v0_2.json');lbp=read_json(OUT/'lbp_implementation_spec.json')
    assert s['geometry_valid_rois']==5748 and s['geometry_invalid_rois']==4 and s['roi_checked']==5752
    assert v['status']=='PASS' and not s['priority_subtraction_applied']
    log=(OUT/'tests.log').read_text(encoding='utf-8-sig')
    assert 'Ran 11 tests' in log and log.rstrip().endswith('OK')
    proposal=read_json(OUT/'forehead_amendment_comparisons.json')
    cases=read_json(OUT/'case_selection.json')['cases']
    anomalies=read_json(OUT/'geometry_anomalies.json')
    im=read_csv(OUT/'image_metrics.csv');metrics=read_csv(OUT/'metrics.csv')
    trial=read_json(OUT/'trial100_manifest.json')
    source=read_json(OUT/'source_proof.json')
    # Visual observations on the actual representative contacts: never pixel GT.
    visual_notes={
        'hf_merged_00198':'Glasses cross upper cheek/nose-mouth polygons; original and proposed forehead remain self-intersecting.',
        'hf_merged_00311':'Forehead hair covers a substantial part of the named forehead region; selected by saved hair-mask proxy.',
        'hf_merged_00561':'Forehead hair and partial secondary face at image edge.',
        'hf_merged_00333':'Secondary faces remain visible at image edges.',
        'hf_merged_00722':'Hand/fingers visibly cover part of the nose-mouth region and approach cheek boundary.',
        'hf_merged_00694':'Cloth in forehead polygon and glasses near the upper cheek/nose region.',
        'hf_merged_00209':'Head covering; B is missing hair, but raw C1 geometry is present; tissue visibility not certified.',
        'hf_merged_00069':'Strong left/right area asymmetry; original forehead has a proper crossing near the temple.',
        'hf_merged_00267':'Original forehead has a proper crossing at the temple.',
        'hf_merged_00463':'Original forehead has a proper crossing at the temple.'}
    write_json(OUT/'visual_review_notes.json',dict(method='Assistant visual inspection of representative contacts, not hand-labeled anatomical/occlusion ground truth',
        reviewed_cases=len(cases),all_anatomy_remains_unverified=True,
        cases=[dict(image_id=c['image_id'],selection_reasons=c['reasons'],
            observation=visual_notes.get(c['image_id'],'Observed relative size/shape example; no formal occlusion clearance or anatomical certification.'),
            formal_occlusion_clearance=False) for c in cases]))
    # Full-frame evidence for the independently confirmed crossings.
    names,points,images,_,_=audit.previous.load_archive()
    groups,indices=audit.previous.source_groups();positions={Path(n).stem:i for i,n in enumerate(names)}
    anomaly_rows=[]
    for item in anomalies:
        identity=item['image_id'];i=positions[identity];name=names[i]
        image=cv2.imread(images[name]['image_path']);poly=audit.previous.polygon_points(points[i],contract,groups)[item['region']]
        side=768;canvas=np.full((side+80,side,3),255,np.uint8)
        canvas[80:]=cv2.resize(image,(side,side),interpolation=cv2.INTER_NEAREST)
        q=np.rint(poly*3).astype(np.int32);q[:,1]+=80
        cv2.polylines(canvas,[q],True,(0,180,255),2)
        crossing=item['intersections'][0]
        for pair in ['edge_a','edge_b']:
            ia,ib=crossing[pair];cv2.line(canvas,tuple(q[ia]),tuple(q[ib]),(0,0,255),4)
        x,y=np.rint(np.array(crossing['intersection_xy'])*3).astype(int);y+=80
        cv2.circle(canvas,(int(x),int(y)),12,(255,0,0),2)
        cv2.putText(canvas,identity+' | FOREHEAD SELF-INTERSECTION',(10,27),0,.65,(0,0,0),1)
        cv2.putText(canvas,'Original geometry; no A mapping or ROI correction applied',(10,56),0,.55,(0,0,0),1)
        path=OUT/'intersection_diagnostics'/f'{identity}.png';path.parent.mkdir(exist_ok=True)
        assert cv2.imwrite(str(path),canvas)
        labels=[]
        for key in ['edge_a','edge_b']:
            refs=crossing['endpoint_refs'][key]
            labels.append(' → '.join(('A'+r['source_index'] if r['ref']=='A68' else 'MP'+r['source_index']) for r in refs))
        anomaly_rows.append([identity,labels[0],labels[1],', '.join(f'{z:.6f}' for z in crossing['intersection_xy']),
            f'[Hình](../../outputs/C1_lbp/roi_validation/intersection_diagnostics/{identity}.png)'])

    intro=f'''Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu cao nhất: `csdldpt.pdf`, SHA-256 `{audit.previous.db.legacy.REPORT_SHA256}` đã xác minh. Đã đọc toàn bộ §2.2/§2.4 qua bản trích PDF đóng băng, đối chiếu hình PDF và source/hash hiện hành. Không chỉnh PDF, dataset, mapping A, vector A/B, stats/calibration, CSDL hoặc kết quả A+B đã nghiệm thu.

Đợt này chỉ kiểm toán ROI và chốt đặc tả kỹ thuật có nguồn gốc rõ. Không chạy lại MediaPipe, không gọi LBP/HOG trên ảnh, không viết extractor hoặc tạo vector C1/C2. Tên file “final” là hồ sơ kết luận của lần rà soát; trạng thái giải phẫu vẫn **PROVISIONAL**.
'''
    region_names={'forehead_brow':'Trán và vùng lông mày','cheek_left_viewer':'Má trái theo người xem',
        'cheek_right_viewer':'Má phải theo người xem','nose_mouth':'Mũi và miệng'}
    vertex_sections=[]
    for key in audit.REGIONS:
        rows=[]
        for j,p in enumerate(contract['polygons'][key]):
            ref='A'+str(p['index']) if p['ref']=='A68' else 'MP'+str(p['index'])+' phụ trợ'
            rows.append([j,ref,p['mediapipe_index'],p['offset_u_ipd'],p['offset_v_ipd']])
        vertex_sections.append('### '+region_names[key]+'\n\n'+table(['Thứ tự','Nguồn','MP index','α·D·u','β·D·v'],rows))
    pair_rows=[[a+' / '+b,*[s['pairwise_overlap'][a+'__'+b][k] for k in ['min','median','max']]] for a,b in audit.PAIR_KEYS]
    area_rows=[[region_names[key],s['regions'][key]['geometry_valid'],
        *[s['regions'][key]['raw_mask_pixels'][field] for field in ['min','median','max']],
        *[s['regions'][key]['support_valid_centres'][field] for field in ['min','median','max']]] for key in audit.REGIONS]
    bad_candidate=[r['image_id'] for r in proposal if not r['candidate_geometry_valid']]
    candidate_min=min(r['proposed_brow_proxy_coverage'] for r in proposal)
    roi_doc=f'''# C1 ROI contract v0.2.0 — PROVISIONAL

{intro}

## Nhận dạng và phạm vi

- Schema ID: `{contract['schema_id']}`; version `{contract['version']}`; status **{contract['status']}**.
- [Contract JSON](../outputs/C1_lbp/roi_validation/contract_v0_2.json); file SHA-256 `{audit.digest(OUT/'contract_v0_2.json')}`.
- Canonical content SHA-256 `{contract['content_sha256']}`: JSON canonical sort-key, UTF-8, không gồm trường content_sha256. [Sidecar hash file](../outputs/C1_lbp/roi_validation/contract_v0_2.sha256).
- Geometry SHA-256 `{contract['geometry_sha256']}`; 61 vertex definition được giữ **đúng v0.1**, gồm 25/12/12/12 đỉnh. Proposal v0.1 và mọi output trước giữ nguyên.
- Thay đổi có chủ đích của đợt kiểm tra: dùng **bốn mask raw độc lập**, không áp dụng ownership hoặc trừ overlap theo ưu tiên của proposal cũ.

PDF §2.4.2 quy định bốn vùng: trán và lông mày, má trái, má phải, mũi và miệng. PDF không cho vertex, margin, hệ quy chiếu trái/phải, raster rule hoặc cách chia overlap. Tên vùng là EXACT theo văn bản; các lựa chọn hình học bên dưới là quy ước triển khai có giới hạn, không phải endpoint canonical được PDF xác nhận.

## Mapping, topology và hệ quy chiếu

A0…A67 là mapping 68 điểm hiện hành, MP0…MP477 là landmark gốc. Dữ liệu đến từ archive 1438×478×2 float32 có hash xác thực. Không dùng vị trí hàng làm danh tính; nối qua tên ảnh/image_id. [Source proof](../outputs/C1_lbp/roi_validation/source_proof.json).

Trái/phải chọn **theo người xem/code**; không tự swap sang giải phẫu. Tâm L/R là mean6 float32 của các nhóm `[33,160,158,133,153,144]` và `[362,385,387,263,373,380]`, rồi promote sang float64 để dựng frame: `D=norm64(R−L)`, `u=(R−L)/D`, `v=(−u_y,u_x)`. Mỗi vertex là `P[MP]+D*(αu+βv)`. Các offset 0.05/0.08/0.06 là quy ước, không nằm trong PDF.

Vùng trán dùng 15 MP phụ trợ upper FACE_OVAL `{contract['auxiliary_upper_face_oval']}`. Đã kiểm membership và **14 cạnh liên tiếp** trong topology đã hash. Dùng 478 phụ trợ cho C1 chưa được PDF mô tả rõ và cần xác nhận trước chứng nhận giải phẫu; không thêm chúng vào vector A.

MP1=A30, MP4=A33 giữ nguyên. Khác biệt topology với hình PDF trước đây chưa được giải quyết bằng cách đổi index. MP129=A31 và MP358=A35 vẫn là endpoint cánh/bên mũi proxy UNVERIFIED, không thuộc sparse NOSE. Membership mắt/mày/môi/FACE_OVAL đã kiểm không đồng nghĩa canonical anatomical endpoint. Xem [A_MAPPING_FINAL_REVIEW.md](audits/A_MAPPING_FINAL_REVIEW.md).

## Toàn bộ vertex và thứ tự

Nối cạnh thẳng theo thứ tự 0→1→…→n−1→0; không tự sắp xếp, convex-hull, spline hoặc sửa mapping để làm hình đơn giản/đẹp hơn. Các hệ số dùng theo đúng công thức frame ở trên.

{chr(10).join(vertex_sections)}

[roi_vertices.csv](../outputs/C1_lbp/roi_validation/roi_vertices.csv) lưu **87.718 vertex thực tế** của cả 1438 ảnh. Index nguồn, thứ tự và offset đều được ghi lại, không chỉ mô tả tên vùng.

## Raster, overlap, gaps và vùng không hợp lệ

Vertex tính float64, contour raster cast float32; điểm lấy mẫu là tâm pixel nguyên x/y, `pointPolygonTest>=0` kể cả boundary. Đánh giá trong khung 0…255; không clamp từng vertex, không warp ảnh. Guard số học: D≥1e-6, diện tích≥1e-6 pixel², cạnh≥1e-9; kiểm giao/chạm cạnh không kề với tolerance 1e-9 theo công cụ audit.

**Không áp dụng priority subtraction.** Mỗi ROI giữ membership riêng, pixel overlap được lưu ở cả hai mask. Quy ước pooling tương lai của bản đặc tả kỹ thuật cũng giữ shared pixels độc lập; đây là lựa chọn triển khai, không phải câu nguyên văn PDF. Việc hiểu “bốn vùng độc lập” thành disjoint hay independent pooling chưa có đặc tả pixel trong PDF; không gọi điều đó là đã chứng minh tuân thủ hoàn toàn.

Pixel ngoài union giữ unassigned; không ép bốn ROI phủ toàn bộ mặt. Báo cáo phân biệt unassigned trên toàn ảnh với unassigned **trong FACE_OVAL proxy**; cả hai có thể gồm mắt/cằm cố ý không chọn. “Enclosed gap” là component không chạm biên proxy, không tự coi là lỗi giải phẫu.

Mask của polygon tự giao vẫn được raster để đo/hiển thị **chẩn đoán**; nó không hợp lệ cho extractor tương lai. Thiếu/invalid một vùng hoặc <64 tâm có support hợp lệ thì future C1 phải trả `missing_C1`, không zero-fill. Ngưỡng 64 và cờ review mask<256 pixel là quy ước kỹ thuật công khai, không phải mức chất lượng do PDF quy định.

## Kết quả toàn kho và mức cho phép sử dụng

**5752 ROI đã kiểm: 5748 hợp lệ về hình học, 4 trán tự giao.** Không có out-of-bounds hoặc cờ quá nhỏ theo ngưỡng đã đặt. Bốn ảnh lỗi: HF00069, HF00198, HF00267, HF00463. [Báo cáo toàn kho](audits/C1_ROI_FULL_DATASET_VALIDATION.md).

Mọi 1438 ảnh có overlap, unique shared pixels min/median/max=91/140/208; chỉ hai cặp má–mũi/miệng có overlap. Proxy lông mày native chỉ được phủ khoảng **44.29–67.14%**, median **55.55%**; không ảnh nào phủ đủ proxy. Đây là bằng chứng undercoverage của proxy, không phải annotation mô lông mày thật.

**Chưa cho phép coi bản này là ROI giải phẫu chính thức hoặc sinh 100 vector hợp lệ.** Có thể dùng cho thử nghiệm kỹ thuật có kiểm soát sau khi được giao triển khai extractor: manifest 100 ảnh đã chuẩn bị, 96 đi nhánh tính toán và 4 bắt buộc trả missing vì hình học. Không chạy thử trong nhiệm vụ này. [trial100_manifest.json](../outputs/C1_lbp/roi_validation/trial100_manifest.json).

## Điều chỉnh được đề xuất, chưa áp dụng

1. Thay biên dưới trán bằng lower-eyebrow native chain `[276,283,282,295,285,55,65,52,53,46]` cộng 0.02D·v; giữ upper FACE_OVAL và toàn bộ A indices. Lý do: proxy undercoverage toàn kho. [Proposal v0.3](../outputs/C1_lbp/roi_validation/forehead_amendment_proposal_v0_3.json) **không phải contract active**.
2. Preview trên 18 case cho coverage proxy mới min `{candidate_min:.6f}`, nhưng chỉ **17/18** có hình học đơn giản; **{', '.join(bad_candidate)} vẫn tự giao**. Không chọn/triển khai proposal chỉ vì coverage tốt hơn. [So sánh HF00198](../outputs/C1_lbp/roi_validation/proposal_comparisons/hf_merged_00198_forehead.png), [toàn bộ kết quả proposal](../outputs/C1_lbp/roi_validation/forehead_amendment_comparisons.json).
3. Cần xác định đường nối ở thái dương có thẩm quyền để tránh cắt upper FACE_OVAL, rồi kiểm lại toàn bộ 5752 ROI của candidate mới; không tự convex-hull hoặc cắt đỉnh vì mục tiêu đẹp/hợp lệ giả.
4. Giữ occlusion flags và giải quyết bằng protocol riêng. Không tự giao ROI với skin/hair mask Bộ B, không inpaint/crop/xóa ảnh. Đổi ROI không giải quyết dataset có mặt phụ hoặc tay che.

Không lựa chọn ROI bằng kết quả retrieval/Top-5. Trạng thái sau rà soát: **PROVISIONAL, không APPROVED**.
'''
    save(DOC/'C1_final_roi_contract.md',roi_doc)

    choices=[
        ['BGR→gray','uint8; floor((1868B+9617G+4899R+8192)/16384), tích lũy uint32','Quy ước số nguyên cố định, không phụ thuộc backend cvtColor; không phải PDF'],
        ['Nội suy','Float64 bilinear, horizontal lerp rồi vertical lerp; không làm tròn gray đã nội suy','Quy ước triển khai'],
        ['Điểm đầu/chiều/bit','p0 Đông; ngược chiều kim đồng hồ trên ảnh; trọng số 2^p','PDF chỉ quy định tổng có 2^p, chưa cho orientation'],
        ['Vị trí láng giềng','Bảng offset chứa ±2,0 và ±sqrt(2); cardinal ghi 0 chính xác','Không round tọa độ thành 5 decimal nếu dùng spec này'],
        ['58+1 labels','0→0;255→57;nonuniform→58; còn lại theo run-start formula bên dưới','Chọn numbering có đối chiếu kỹ thuật; PDF chỉ quy định 59 bin'],
        ['Biên ROI/ảnh','Centre và mọi pixel stencil bilinear có trọng số khác 0 phải nằm trong cùng raw ROI và ảnh','Footprint 21 điểm; không padding/reflect hoặc lấy vùng khác'],
        ['Overlap','Mỗi mask pool riêng, shared pixel được tính ở từng vùng chứa nó; không priority subtraction','Quy ước prototype; nghĩa giải phẫu độc lập chưa được chứng nhận'],
        ['Vùng thiếu/quá nhỏ','Bất kỳ ROI invalid hoặc <64 eligible centres → missing_C1 cho toàn descriptor','64 là guard kỹ thuật, không PDF; không zero-fill'],
        ['Ghép vùng','Trán+mày, má trái theo người xem, má phải theo người xem, mũi+miệng','Thứ tự nhóm theo PDF; frame trái/phải là quy ước ghi rõ'],
        ['NaN/Inf','Reject input/intermediate, ghi missing_reason; không nan_to_num/impute','Quy ước fail rõ ràng'],
        ['Histogram/dtype','Counts uint64; h_j=count_j/N ở float64, N nguyên; L1 từng vùng không cộng epsilon','L1 từng vùng là PDF; arithmetic/dtype là quy ước'],
        ['Chi-square ε','1e-8, bản tham số có version; không sửa epsilon/calibration A/B','PDF có ε nhưng chưa chốt giá trị'],
        ['Query ảnh mới','256×256 RGB đã căn chỉnh, cùng model asset/478→frame/gray/bin/support/ROI version; thiếu vùng trả missing','Không tự align/crop theo log lịch sử không có; future adapter riêng']]
    lbp_doc=f'''# Đặc tả C1 LBP 236 chiều — chưa viết extractor

{intro}

Schema ID `{lbp['schema_id']}`, version `{lbp['version']}`; status **SPEC_ONLY_PROVISIONAL_ROI**. [JSON đặc tả](../outputs/C1_lbp/roi_validation/lbp_implementation_spec.json), content SHA-256 `{lbp['content_sha256']}`. ROI dependency `{contract['schema_id']}` / content hash `{contract['content_sha256']}`.

## Những điều PDF quy định bắt buộc

P=8, R=2 trên kênh mức xám; `b_p=s(g_p−g_c)` với **s(x)=1 khi x≥0**, ngược lại 0. `code=Σ(p=0…7) b_p·2^p`. Không thêm epsilon vào phép so sánh hoặc đổi dấu bằng >.

Uniform có **tối đa hai chuyển bit vòng**, giữ orientation: 58 mẫu uniform riêng và một bin nonuniform, **59 bins**. Không dùng rotation-invariant `uniform` 10 bins cho P=8. Bốn histogram 59 bin được **L1 riêng từng vùng** rồi ghép thành **236 chiều**. Không áp dụng Z-score của A/B, global L1 hoặc L2 bổ sung vào C1 dưới danh nghĩa báo cáo.

Chi-square theo PDF:

```text
d_C1(h1,h2) = 0.5 * Σ(k=0…235) (h1[k]−h2[k])² / (h1[k]+h2[k]+epsilon)
```

Hệ số **0.5** là bắt buộc; không thay Euclid cho C1. PDF §2.4 là nguồn cho các yêu cầu này. Hiện chưa tính code LBP, histogram, khoảng cách C1 hoặc calibration C1 trên ảnh.

## Các lựa chọn kỹ thuật đã ghi thành quy ước

Các lựa chọn dưới đây được chốt ở mức **đặc tả kỹ thuật v0.1.0** cho prototype tái lập; không trình bày là nguyên văn PDF hoặc chứng nhận giải phẫu.

{table(['Chi tiết PDF chưa chốt','Lựa chọn cụ thể','Nguồn gốc/giới hạn'],choices)}

Grayscale dùng thứ tự B,G,R của bộ đọc hiện tại. Hệ số nguyên tổng 16384, cộng nửa mẫu số rồi chia lấy floor; fixtures scalar BGR=(255,0,0)→29, (0,255,0)→150, (0,0,255)→76, (255,255,255)→255. Không tuyên bố mọi backend OpenCV cho cùng bit ở mọi pixel; chính công thức số nguyên này là quy ước đã chọn. Không thay gamma/contrast/CLAHE, sharpen, blur hoặc rescale ảnh để cải thiện retrieval.

## Sampling và bilinear rõ thứ tự

Với hệ ảnh x sang phải/y xuống, các offset p0…p7 là:

```text
(2,0), (sqrt(2),−sqrt(2)), (0,−2), (−sqrt(2),−sqrt(2)),
(−2,0), (−sqrt(2),sqrt(2)), (0,2), (sqrt(2),sqrt(2))
```

Giữ cardinal 0/±2 chính xác; sqrt(2) float64. Với vị trí q, floor/ceil xác định stencil; t_x,t_y là phần lẻ. Quy định thứ tự lerp: `top=g00+t_x*(g10−g00)`; `bottom=g01+t_x*(g11−g01)`; `g_p=top+t_y*(bottom−top)`. Khi floor=ceil chỉ dùng giá trị tương ứng. Không làm tròn g_p về uint8, không threshold epsilon. Constant gray giữ equality, nên mọi b_p=1 theo s(0)=1.

Chỉ centre có đầy đủ support nội ROI mới eligible. Support gồm centre, 4 cardinal và 16 góc stencil diagonal: **21 điểm nguyên trong footprint 5×5**. Các pixel (±1,0)/(0,±1) không cần vì không có trọng số nội suy tại các điểm này. [Footprint](../outputs/C1_lbp/roi_validation/lbp_implementation_spec.json) và cột support_valid_centres của metrics chỉ là kiểm hình học, không phải mã LBP đã được trích.

## Numbering nri_uniform 59 bin

Gọi `U=Σ |b_p−b_((p+1) mod 8)|`, `n=Σb_p`. U>2 → bin58. Code0 → bin0, code255 → bin57. Với 1≤n≤7 và U≤2, có đúng một s mà b_s=1 và b_(s−1 mod 8)=0; đặt `r=(−s) mod8`, rồi **bin=1+8(n−1)+r**. Giữ r nên không bất biến quay.

[Bảng lookup đầy đủ 256 mã](../outputs/C1_lbp/roi_validation/nri_uniform_59_codebook.csv) được kiểm bằng phép quay bit độc lập: 58 raw patterns đi vào 58 bins0…57 riêng biệt; 198 patterns còn lại gom bin58. Ví dụ raw1→bin1, raw2→bin8, raw3→bin9, raw129→bin10, raw170→bin58. Đây là bảng đặc tả bit-word, không phải LBP image extractor.

Thuật ngữ và numbering được đối chiếu [tài liệu scikit-image 0.25.2](https://scikit-image.org/docs/0.25.x/api/skimage.feature.html#skimage.feature.local_binary_pattern) và [source được gắn tag v0.25.2](https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/feature/_texture.pyx). Chỉ dùng như tham khảo kỹ thuật; PDF vẫn là thẩm quyền yêu cầu. Backend đó có quy ước rounding/border riêng, nên không tuyên bố gọi thư viện sẽ tự khớp toàn bộ đặc tả này.

## Pooling, L1, missing và layout

Mỗi eligible centre đóng góp đúng một count vào bin0…58 của **mỗi raw ROI chứa support của nó**. Không loại shared pixel theo thứ tự vùng. Dùng N là số centre hợp lệ của riêng vùng; N<64 hoặc ROI invalid thì toàn C1 missing, kèm reason; không tạo histogram zero/NaN để đủ chiều.

Khi đủ điều kiện, h_j=count_j/N, từng histogram có tổng1; vector ghép có tổng4 chứ không tự chuẩn hóa tổng về1. Layout: trán+mày `[0…58]`, má trái theo ảnh `[59…117]`, má phải `[118…176]`, mũi+miệng `[177…235]`. Counts và N không được thêm thành chiều đặc trưng. Dtype output tương lai float64, dimension236, pin ROI/codebook/grayscale/support hashes và status.

## Ảnh mới và quản lý phiên bản

Ảnh mới cần định dạng 256×256 RGB đã căn chỉnh theo protocol được khai báo; không suy ra hoặc giả mạo tọa độ alignment lịch sử. Nếu đã có archive có hash thì dùng lại. Nếu chưa có, adapter tương lai phải lấy đủ 478 điểm bằng model asset đã pin, IMAGE mode/num_faces=5 như archive, ghi package/runtime version và yêu cầu đúng một detection; không sửa mapping A. Package version lúc tạo archive cũ còn thiếu log, nên không khẳng định inference lịch sử tái lập bitwise.

Cùng một path xử lý phải dùng cho gallery/query: frame, vertex/raster, raw overlap, grayscale, bit order, bin map, support, min-size và per-region L1. Sai schema/hash, nhiều/không face, NaN/Inf hoặc vùng thiếu thì fail rõ. Model, adapter và output mới phải có version riêng; không ghi vào CSDL hoặc output A/B đã nghiệm thu. Query không fit lại hay điều chỉnh histogram theo kho để tăng Top-5.

Median normalization/fusion C1 chỉ được triển khai khi đã có vector hợp lệ và calibration version riêng phù hợp tập ảnh/cặp; không sửa calibration A+B hiện tại. Nhiệm vụ này **chưa viết extractor hoặc chạy trial100**. Các fixture cần có khi viết sau: equality/constant, 58 uniform/198 nonuniform, orientation khác nhau không gộp, bilinear diagonal, biên ROI, overlap retained, 4 ảnh hình học invalid phải missing, L1 riêng, Chi-square đối xứng/tự khoảng cách0/hệ số0.5 và query-version mismatch.
'''
    save(DOC/'C1_lbp_236_feature_spec.md',lbp_doc)

    validation_doc=f'''# Kiểm tra ROI C1 trên toàn bộ dataset

{intro}

## Kết quả thực tế

Đã kiểm đủ **1438 ảnh ×4 =5752 ROI**, không lấy tám ảnh preview làm đại diện cho kết luận hình học toàn kho.

| Hạng mục | Kết quả |
| --- | --- |
| ROI kiểm tra | 5752 |
| Hợp lệ về hình học | **5748** |
| Không hợp lệ | **4**, đều forehead_brow tự giao |
| Sai số đỉnh/thứ tự, NaN/Inf, diện tích0 | 0 |
| Vertex vượt ảnh | 0 |
| Mask<256 pixel hoặc support<64 | 0 theo ngưỡng review đã khai báo |
| Ảnh có raw overlap | **1438/1438** |
| Ownership/priority subtraction | **Không áp dụng** |
| Tâm/mã LBP/histogram/vector được trích | **Không có**; support chỉ là thống kê hình học |
| Chứng nhận giải phẫu/occlusion toàn kho | **Chưa có** |

Định nghĩa valid: đủ thứ tự/số đỉnh, hữu hạn, không self-intersection/zero-edge, diện tích không degenerate và mask clipped không rỗng. Min-area số học1e-6 khác cờ diện tích nhỏ về chất lượng; 256 pixel review và 64 support là quy ước triển khai, không PDF. Diện tích/pixel của bốn polygon invalid vẫn được ghi để chẩn đoán, không đem làm feature.

[summary.json](../../outputs/C1_lbp/roi_validation/summary.json), [metrics.csv — 5752 dòng](../../outputs/C1_lbp/roi_validation/metrics.csv), [image_metrics.csv](../../outputs/C1_lbp/roi_validation/image_metrics.csv), [roi_vertices.csv — 87718 dòng](../../outputs/C1_lbp/roi_validation/roi_vertices.csv).

## Bốn vùng trán tự giao

{table(['Ảnh','Cạnh thứ nhất','Cạnh thứ hai','Giao điểm x,y','Hình toàn khung'],anomaly_rows)}

Giao được xác nhận thêm bằng solver determinant scalar độc lập, với giao điểm nằm trong cả hai segment, không phải chỉ cờ chung “có thể zero-edge”. Cạnh mày offset cắt đường upper FACE_OVAL ở thái dương. [geometry_anomalies.json](../../outputs/C1_lbp/roi_validation/geometry_anomalies.json). Các ảnh này vẫn có contact sheet và trial negative-path, không bị loại để làm thống kê đẹp.

## Diện tích và pixel từng vùng

{table(['Vùng','Geometry valid/1438','Raw pixel min','Median','Max','Support min','Median','Max'],area_rows)}

Các thống kê trên bao gồm toàn bộ1438 mask mỗi vùng, kể cả bốn mask trán invalid dưới vai trò chẩn đoán. Continuous/algebraic area, signed orientation, bbox/out-of-bounds và nguyên nhân được ghi riêng trong CSV; không dùng diện tích self-crossing như một polygon giải phẫu hợp lệ.

## Overlap từng cặp và gaps

{table(['Cặp vùng','Overlap min px','Median','Max'],pair_rows)}

Unique overlap min/median/max91/140/208 pixel mỗi ảnh; max memberships=2. Không trừ mask, không gán ưu tiên hoặc tự cắt margin. [overlap_metrics.csv —8628 cặp](../../outputs/C1_lbp/roi_validation/overlap_metrics.csv). Kiểm độc lập inclusion-exclusion xác nhận tổng pixel bốn mask trừ pairwise overlap bằng union mỗi ảnh.

Unassigned **trong native FACE_OVAL proxy** min/median/max={s['unassigned_face_pixels']['min']}/{s['unassigned_face_pixels']['median']}/{s['unassigned_face_pixels']['max']} pixel. Có thể gồm mắt, cằm, vùng giữa các polygon; không suy ra tất cả đều là lỗ hổng sai yêu cầu PDF. Cột unassigned_image_pixels là số trên toàn256² khác hẳn số trong face proxy; enclosed_gap_components/pixels chỉ component không chạm biên proxy. Không lấp gaps hoặc kéo polygon cho khớp mặt.

## Coverage lông mày và rủi ro che khuất

10 điểm mày A68 đều nằm trong trán ở1434 ảnh; bốn ảnh còn lại chính là bốn case geometry invalid. **Không ảnh nào chứa đủ20 native brow nodes**, cũng không ảnh nào phủ100% proxy polygon lông mày. Proxy pixel coverage min/median/max=**44.29%/55.55%/67.14%**. Proxy được đóng từ hai chuỗi native trên/dưới bằng đường nối endpoint công khai; không phải nhãn mô/tóc thật và không thể dùng nó để ký nhận giải phẫu.

Đã kiểm saved raw hair mask có hash trên cả1438 ảnh, **không chạy segmentation mới**. Có overlap tóc dự đoán tại1401 ROI trán,710 má trái,843 má phải và1 mũi–miệng; pixel/fraction từng ROI trong metrics. Đây là model proxy, không chứng minh nhãn tóc đúng hoặc tự cho phép loại pixel đó.

Không có GT toàn kho cho tay/kính/vải hoặc mô giải phẫu; các ROI còn UNVERIFIED. Visual review xác nhận những case rõ như HF00722 có tay trong mũi–miệng, HF00198 có kính qua vùng má/mũi, HF00694 có vải/kính, HF00561/HF00311 nhiều tóc trán, HF00333/HF00561 có mặt phụ. Dữ liệu này được giữ nguyên, không gọi detector_count=1 là chứng nhận ảnh chỉ có một mặt. [visual_review_notes.json](../../outputs/C1_lbp/roi_validation/visual_review_notes.json).

## Contact sheets và lựa chọn case

Có **18 case**, chọn từ nhóm CFD/HF bắt buộc, các min/max quan sát thật, bất đối xứng diện tích và toàn bộ bốn geometry invalid; không dùng ranking. Không có mask thật sự dưới ngưỡng nhỏ, nên ảnh “smallest observed” chỉ là cực trị tương đối, không giả tạo một case ROI rất nhỏ.

Mỗi case có10 panel: nguồn toàn khung, A68, bốn polygon nguyên gốc, bốn mask raw riêng, overlap đỏ, unassigned-face và bảng số. Bốn binary PNG riêng/case cho **72 mask** được đọc lại kiểm hash/pixelcount; overlap còn nguyên. Nhãn geometry hợp lệ bao nhiêu/4 và anatomy UNVERIFIED luôn hiển thị.

[Index toàn bộ18 case](../../outputs/C1_lbp/roi_validation/contact_sheets/index.md), [overview](../../outputs/C1_lbp/roi_validation/contact_sheets/overview.png), [HF00198 lỗi/kính](../../outputs/C1_lbp/roi_validation/contact_sheets/hf_merged_00198/contact.png), [HF00722 tay](../../outputs/C1_lbp/roi_validation/contact_sheets/hf_merged_00722/contact.png). [case_selection.json](../../outputs/C1_lbp/roi_validation/case_selection.json) ghi lý do cho mọi case.

## Điều chỉnh chỉ được đề xuất

Đề xuất v0.3 chuyển biên dưới trán sang native lower brow chain +0.02D, không sửa A. Trên18 case: coverage proxy khoảng99.64–100%, nhưng chỉ17 case simple, HF00198 vẫn tự giao. **Chưa kích hoạt và chưa xác thực toàn5752 ROI**. Cần xử lý side closure có căn cứ giải phẫu và review annotation trước candidate mới. Không dùng coverage đẹp hơn/Top-5 làm tiêu chí tự duyệt. Các vùng má/mũi–miệng chưa có annotation canonical; không tự thay MP129/358 hoặc MP1/4.

Xem [C1_final_roi_contract.md](../C1_final_roi_contract.md) và [bộ hình so sánh](../../outputs/C1_lbp/roi_validation/forehead_amendment_comparisons.json).

## Điều kiện thử nghiệm kỹ thuật 100 ảnh

Đã chuẩn bị manifest100 ảnh **50 CFD/50 HF**, bắt buộc chứa18 case và bốn case lỗi, phần còn lại lấy theo SHA-256 seed `C1_trial100_v0.2` trên image_id, không theo retrieval hoặc chọn chỉ ảnh đẹp. Hiện có **96 ảnh geometry/support-ready và4 ảnh phải trả missing_C1**. [trial100_manifest.json](../../outputs/C1_lbp/roi_validation/trial100_manifest.json).

Có thể dùng100 input này cho **smoke test kỹ thuật có96 positive/4 negative paths** khi được giao viết extractor sau này, với contract/LBP-spec hashes đã pin, same raw-overlap/gray/bin/support và output namespace/version mới. Không đủ điều kiện tuyên bố có100 vector C1 hợp lệ hoặc 100 ROI anatomy-approved. Trước extraction chính thức cần sửa/kiểm toàn bộ lỗi hình học, chốt giải phẫu/brow coverage/occlusion và các convention đã chọn với thẩm quyền phù hợp.

**Chưa chạy trial, chưa viết extractor, chưa tạo vector.** Không thay calibration hoặc thuật toán A/B.

## Kiểm chứng và phạm vi bất biến

11 tests về raster float, support21, retention overlap, independent crossings, contract hash, 59-bin table, grayscale scalar fixtures, full5752 census, PNG round-trip và trial negative cases đạt. Bảng bit-word có58 uniform patterns vào58 bins riêng và198 nonuniform vào bin58; không xử lý LBP trên ảnh. [tests.log](../../outputs/C1_lbp/roi_validation/tests.log), [verification.json](../../outputs/C1_lbp/roi_validation/verification.json).

Hash toàn bộ **14387 file đã có** trước/sau không đổi, gồm proposal/overlay v0.1, các SQLite đã nghiệm thu, PDF, dataset, source/mapping A, vectors/stats/calibration/query A+B. [final_scope.json](../../outputs/C1_lbp/roi_validation/final_scope.json), [manifest file mới](../../outputs/C1_lbp/roi_validation/created_files_manifest.json).

Lệnh PowerShell thực tế đã chạy tại repository root:

```powershell
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/c1_final_tools/validate_roi_all.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/c1_final_tools/render_contact_sheets.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B -m unittest discover -s docs/audits/c1_final_tools -p test_c1_specs.py -v
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/c1_final_tools/verify_full_validation.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/c1_final_tools/write_final_specs.py
```

Validation và contact stage từ chối ghi đè bộ đã hoàn tất; chỉ tạo output mới của nhiệm vụ này. Kết luận: **đã hoàn tất kiểm toán5752 ROI và đặc tả kỹ thuật, contract vẫn PROVISIONAL; không chứng nhận toàn hệ thống100%**.
'''
    save(DOC/'audits/C1_ROI_FULL_DATASET_VALIDATION.md',validation_doc)
    # Stage-completion information is added only to this task's NEW summary.
    s.update(contact_sheet_cases=len(cases),raw_mask_png_count=len(cases)*4,unit_tests_passed=11,
        codebook_bins=59,codebook_uniform_patterns=58,codebook_nonuniform_patterns=198,
        lbp_spec_file_sha256=audit.digest(OUT/'lbp_implementation_spec.json'),
        trial100=dict(planned=100,processable=96,expected_missing=4,executed=False),
        proposed_forehead_candidate=dict(status='NOT_ACTIVE',preview_cases=18,geometry_valid_cases=17,
            geometry_invalid_cases=bad_candidate,min_proxy_coverage=candidate_min,full_dataset_validated=False),
        technical_trial_status='CONDITIONAL_SMOKE_TEST_96_PROCESSABLE_4_EXPECTED_REJECTS; NOT_100_VALID_VECTORS')
    write_json(OUT/'summary.json',s)
    baseline=read_json(OUT/'baseline_before.json')
    changed=[p for p,h in baseline.items() if audit.digest(p)!=h]
    assert not changed,changed
    write_json(OUT/'final_scope.json',dict(status='PASS',protected_files_checked=len(baseline),changed_existing_files=changed,
        approval_status='PROVISIONAL',roi_checked=5752,geometry_valid=5748,geometry_invalid=4,
        priority_subtraction_applied=False,source_proposal_preserved=True,accepted_databases_preserved=True,
        a_b_vectors_stats_calibration_ranking_unchanged=True,dataset_and_pdf_unchanged=True,
        mapping_indices_unchanged=True,media_pipe_rerun=False,lbp_extractor_written=False,
        c1_c2_vectors_created=False,trial_executed=False,full_system_compliance=False))
    reports=[DOC/'C1_final_roi_contract.md',DOC/'C1_lbp_236_feature_spec.md',DOC/'audits/C1_ROI_FULL_DATASET_VALIDATION.md']
    files=reports+[p for folder in [OUT,Path(__file__).parent] for p in folder.rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p!=OUT/'created_files_manifest.json']
    write_json(OUT/'created_files_manifest.json',dict(self_excluded=True,files=[
        dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=audit.digest(p)) for p in sorted(files)]))
    broken=[]
    for p in reports:
        text=p.read_text(encoding='utf-8')
        assert '\ufffd' not in text
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if not target.startswith(('https://','http://')) and not (p.parent/target).is_file():broken.append([str(p),target])
    assert not broken,broken
    print(json.dumps(dict(status='PASS',reports=[str(p.relative_to(ROOT)) for p in reports],
        protected_files_unchanged=len(baseline),new_files=len(files),broken_links=broken,
        roi_checked=5752,valid=5748,invalid=4,approval_status='PROVISIONAL',no_c1_c2_vectors=True),indent=2))


if __name__=='__main__':
    main()
