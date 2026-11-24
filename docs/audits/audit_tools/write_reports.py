"""Build the six requested Markdown reports from the measured evidence/register."""
from common import *
from collections import Counter
from requirements import ROWS, EXACT, DETAIL, DEV, OPEN, A2_NAMES, A2_FORMULAS

DEST=ROOT/'docs/audits'
load=lambda name:json.loads((EVIDENCE/name).read_text(encoding='utf-8'))
a=load('a_verification.json');b=load('b_ab_verification.json');ds=load('dataset_verification.json')
counts=Counter(r['status'] for r in ROWS)
assert len({r['id'] for r in ROWS})==len(ROWS)
dump('requirements_register.json',ROWS)
csv_out('requirements_register.csv',ROWS)
dump('status_counts.json',dict(total=len(ROWS),counts=dict(counts),
    by_scope={s:dict(Counter(r['status'] for r in ROWS if r['scope']==s)) for s in ['SOURCE','A','B','DATASET','AB']},
    note='Counts of distinct registered requirements, not tests or percentages. AB14 inherits A12; B18 is inactive historical helper.'))


def clean(value):
    return str(value).replace('|','∣').replace('\n','<br>')


def table(rows):
    text=['| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |',
          '|---|---|---|---|---|---|---|']
    for r in rows:
        text.append('| '+' | '.join(clean(x) for x in [r['id']+' — '+r['requirement'],r['pdf_page'],r['code'],
                    r['formula'],r['evidence'],r['status'],r['action']])+' |')
    return '\n'.join(text)


def save(name,text):
    (DEST/name).write_text(text.strip()+'\n',encoding='utf-8')


COMMON='''Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\\Users\\USER\\Downloads\\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.
'''

summary_lines=['| Trạng thái | Số mục |','|---|---:|']+[f'| {s} | {counts[s]} |' for s in [EXACT,DETAIL,DEV,OPEN]]+[f'| **Tổng** | **{len(ROWS)}** |']
scope_table=['| Phạm vi | EXACT | APPROVED IMPLEMENTATION DETAIL | DEVIATION | UNVERIFIED |','|---|---:|---:|---:|---:|']
for scope in ['SOURCE','A','B','DATASET','AB']:
    c=Counter(r['status'] for r in ROWS if r['scope']==scope)
    scope_table.append(f'| {scope} | {c[EXACT]} | {c[DETAIL]} | {c[DEV]} | {c[OPEN]} |')

final=f'''# FINAL STRICT COMPLIANCE AUDIT — A150 & B144

**Kết luận: chưa đủ điều kiện chứng nhận A150/B144 làm nền tảng tuân thủ báo cáo để chuyển sang C1/C2.** A có sai mẫu số Z-score; B v1 thiếu stage chuẩn hóa mô-men trước ghép; dataset có vi phạm quan sát được về mặt phụ và che vùng miệng. C1/C2 không được triển khai hoặc thay đổi trong audit này. Không có tuyên bố “100% compliant”.

{COMMON}

## Tổng số mục

{chr(10).join(summary_lines)}

{chr(10).join(scope_table)}

Số đếm lấy từ [requirements_register.json](evidence/requirements_register.json); mỗi ID được tính một lần. Đây là số mục kiểm toán, không phải điểm chất lượng hoặc tỷ lệ tuân thủ. **AB14 là hệ quả A12, không phải nguyên nhân mới; B18 là helper nghiên cứu không được đường chạy B144 v1 dùng.**

## Sai lệch đã xác nhận

{table([r for r in ROWS if r['status']==DEV])}

1. **A12 — Z-score:** `std_safe=np.where(std<1e-8,1.0,std)` khác `(sigma+epsilon)` ở §2.5.2 trang17. Không tồn tại ε cộng vào mẫu số trong normalizer A. Với ε minh họa `1e-8`, khác **150 chiều ×1438 ảnh =215700 giá trị float64**; **214046 giá trị float32** đổi sau cast, sai số tuyệt đối tối đa `1.024806737e-5`. PDF không chốt trị số ε, vì vậy đây là phép đo độ nhạy có ghi rõ giả định, không phải âm thầm chọn epsilon chính thức.
2. **B12 — trình tự:** §2.3.3 trang13 và §2.5.2 trang17 đều nêu chuẩn hóa mô-men theo kho trước khi ghép; §2.3.3 còn nêu Z-score từng chiều sau ghép. Code hiện `raw descriptor → concat144 → một Z-score all144`. D14 cũ phê duyệt một lần scale sau ghép, nhưng không có quyền bỏ thứ tự mà PDF nêu rõ theo nguyên tắc audit này. Công thức cụ thể của stage trước ghép vẫn UNVERIFIED; không tự thêm lần chuẩn hóa trong audit.
3. **DS05/DS10 — dataset:** mặt phụ nhìn thấy trong HF00333/HF00561; bàn tay che miệng trong HF00722. Hai contact sheet audit chứa ảnh gốc và đúng raw masks. Không xóa ảnh, không sửa nhãn và không tối ưu Top-5.
4. **AB14 — phụ thuộc:** median/ranking hiện tại đúng với vector A cũ nhưng kế thừa A12. [legacy_dependency_register.json](evidence/legacy_dependency_register.json) gắn nhãn `LEGACY_A_NORMALIZATION_NONCONFORMING` và hash từng artifact phụ thuộc; không sửa metadata cũ để gắn nhãn hồi tố.
5. **B18 — helper lịch sử:** `moments_only` chỉ scale24/144 chiều. Runner bám báo cáo đã chặn nó; B144 v1 đang all144. Không gộp lỗi nhánh nghiên cứu này vào kết luận rằng mọi vector v1 thiếu bước cuối.

## Những phần đã kiểm chứng khớp trong phạm vi riêng

- Công thức chuẩn hóa tọa độ A, Euclid giữa mốc, arccos/góc độ, cấu trúc136+14 và Euclid đủ150 chiều. Bốn vector raw thật được tái trích cho audit và bằng đúng hàng raw cũ; kiểm tra số học A2 riêng cả14 đặc trưng. Chưa chứng nhận endpoint giải phẫu hoặc EAR do thiếu bảng chuẩn/định nghĩa PDF.
- B có đúng hai vùng×72, HS12×4/L1, CIE-Lab với bốn loại mô-men×3 kênh, Hue10/L1, chiếu góc `2πH/180`, circular values trong[0,1], bước cuối all144 và Euclid144. Công thức Pearson, ddof, clipping, class1/17, raw mask và missing policy giữ các quyết định D01–D13/D15–D17 đã phê duyệt. D14 là ngoại lệ do xung đột thứ tự rõ ràng.
- A+B ghép theo danh tính, dùng cùng tập cặp để lấy hai median, `d/(m+epsilon)` rồi tổng trọng số; không cộng d thô, không zero-fill thiếu B. Chứng nhận phép toán điều kiện trên vector cũ, không chứng nhận toàn pipeline đã tuân thủ.

## Kết quả thực nghiệm, không suy ra chất lượng

| Kiểm tra | Kết quả mới đo |
|---|---|
| PDF | Hash khớp;18 trang đã đọc |
| A |1438×150 raw và normalized float32; tái tạo normalized đúng từng phần tử theo code cũ; không có chiều std<1e-8 |
| A-only lịch sử |3/3 PNG Top-5 được dựng lại và khớp pixel giải mã;15 thứ hạng và khoảng cách tính lại |
| B |1438 đầu vào;1437×144 raw/z float64;1 ảnh thiếu HF00209 |
| Raw mask |2876 file kiểm hash/receipt/count/format, không chồng lấn |
| Histograms |5748 histogram tính lại độc lập từ pixel; sai số0 |
| Mô-men/Hue đầy đủ |18 vùng của9 ảnh thật đối chiếu scalar oracle; max error{b['max_descriptor_oracle_error']:.3g} |
| B Z-score hiện hành |1437×144 so với oracle fsum; max error{b['z_oracle_max_error']:.3g} |
| B Top-5 |50 dòng/10 query; scalar Euclid max error{b['max_saved_b_distance_error']:.3g} |
| A+B calibration |20000 pair IDs tái lập độc lập; medianA={b['ab_median_a']:.12f}, medianB={b['ab_median_b']:.12f} |
| Tests mới |23 A +16 B/AB =**39/39 đạt** |
| Tests hiện có |17 A+B +40 màu =**57/57 đạt** |
| Dataset |1438 PNG RGB8 256×256;1438 hash khớp;0 trùng byte;0 ảnh mồ côi |
| Face-count model |num_faces5:1 dự đoán trên1438 ảnh; **không phải ground truth**, vẫn thấy mặt phụ ở ảnh cụ thể |

Một oracle mới ban đầu bỏ quên clipping của circular std D07 (`1.183…` thay vì `1.0`). Đã sửa **expected của test audit**, không sửa code B; lưu log thất bại đầu tại `unit_tests_b_ab_initial_oracle_failure.log`. Kết quả39/39 trên là lần chạy cuối sau sửa oracle, không che log thất bại.

## Phần chưa đủ bằng chứng

Mapping478→68 từng điểm, định nghĩa cao mặt/rộng gò má/EAR/endpoint A2, ε A và các ngưỡng chưa phê duyệt; toán tử chuẩn hóa mô-men trước ghép B; chất lượng ngữ nghĩa masks; yaw/pitch5°, lịch sử bicubic/crop/PNG encoding;1135 danh tính và tuổi18–60; CSDL/eye-coordinate persistence; tính đại diện thống kê của seed42/20000 pairs; relevance/GT cho retrieval. Xem các báo cáo chi tiết, không lấy độ đẹp Top-5 để giải quyết mục nào.

## Tài liệu chi tiết và kế hoạch

- [A150_FORMULA_VERIFICATION.md](A150_FORMULA_VERIFICATION.md):14 tỉ lệ, numerator/denominator/landmarks/đơn vị, oracle ảnh thật, Z-score và A-only.
- [B144_FORMULA_VERIFICATION.md](B144_FORMULA_VERIFICATION.md): B1/B2/B3, D01–D17, trình tự chuẩn hóa, toàn vẹn và query.
- [DATASET_REPORT_COMPLIANCE.md](DATASET_REPORT_COMPLIANCE.md): đo toàn kho và danh sách ảnh cần xem xét.
- [AB_RETRIEVAL_COMPLIANCE.md](AB_RETRIEVAL_COMPLIANCE.md): median/weights/join/query và nhãn phụ thuộc phiên bản.
- [REMEDIATION_PLAN.md](REMEDIATION_PLAN.md): phương án sửa code theo PDF, chưa áp dụng sửa hoặc ghi đè artifact.

## Danh sách đầy đủ các yêu cầu và trạng thái

Các nội dung C tại §2.4 đã đọc để hiểu tài liệu, nhưng không kiểm toán/chứng nhận công thức C1/C2 riêng hay triển khai C. Giá trị thông tin định tính của §2.2.4–2.3 cần nhãn đánh giá để trở thành kết luận thực nghiệm; xem B19/AB15.

{table(ROWS)}

## Bảo toàn và danh sách file

Bản chụp chính gồm **13982 file** trước phép đo/kiểm thử. Phạm vi: source/features/retrieval/tests, outputs A/B và A+B, annotations/models, các Markdown cũ, toàn bộ dataset ngoài `.venv`/`__pycache__`, PDF và model UniFace đang dùng. Ba PNG A-only legacy được bổ sung hash trong `protected_supplement_legacy_previews.json` sau khi đã đọc nhưng trước mọi phép dựng preview; chúng không bị ghi. Đây là giới hạn thời điểm chụp được công khai, không trình bày supplemental snapshot là snapshot đầu tiên.

Kết quả kiểm hash cuối tại [scope_validation.json](evidence/scope_validation.json). Chỉ tạo mới trong `docs/audits/`; không ghi đè file có trước audit. Trạng thái Git trước audit vốn có các file A+B của nhiệm vụ trước; chúng không phải thay đổi của audit này.

Sáu báo cáo ở thư mục này; công cụ/oracle mới ở `audit_tools/`; dữ liệu đo/log/hash/ảnh minh họa ở `evidence/`. [created_files_manifest.json](evidence/created_files_manifest.json) liệt kê đường dẫn/hash/byte size toàn bộ file tạo mới (trừ chính manifest). Không tạo C1/C2, không cài thư viện hay tải model.
'''
save('FINAL_AB_COMPLIANCE_AUDIT.md',final)

first=[r for r in read(EVIDENCE/'a2_real_image_oracles.csv') if r['image_name']=='cfd_final_00001.png']
landmarks=['p2=MP132,p14=MP361;H dùng p21=MP107,p22=MP336,p8=MP152',
    'mean p36..41/MP33,160,158,133,153,144 và p42..47/MP362,385,387,263,373,380; H như trên',
    'p36=MP33,p39=MP133;d hai tâm mí', 'p42=MP362,p45=MP263;d hai tâm mí',
    'p37=MP160,p41=MP144,p38=MP158,p40=MP153; p36/p39',
    'p43=MP385,p47=MP380,p44=MP387,p46=MP373; p42/p45',
    'p31=MP129,p35=MP358', 'p48=MP61,p54=MP291', 'p62=MP13,p66=MP14',
    'E trung điểm hai tâm mí; p30=MP1', 'E và midpoint(p48=MP61,p54=MP291)',
    'p30=MP1,p8=MP152;H như trên', 'p4=MP172,p12=MP397;H như trên',
    'p4=MP172,p8=MP152,p12=MP397']
a2_table=['| STT / Nội dung PDF | Mốc code (0-based) | Tử số | Mẫu số thực tế | Đơn vị | Code / oracle ảnh thật | Trạng thái |',
          '|---|---|---:|---:|---|---|---|']
for i,r in enumerate(first):
    denominator=(f"{float(r['denominator_before_epsilon']):.12f} +1e-8" if i<13 else 'tích hai norm trong arccos; xem công thức')
    a2_table.append('| '+' | '.join(clean(s) for s in [f"{i+1}. {A2_NAMES[i]}",landmarks[i],f"{float(r['numerator']):.12f}",
         denominator,r['unit'],f"{float(r['code_value']):.12f} / {float(r['independent_scalar_value']):.12f}",OPEN])+' |')
sense=['| ε giả định | Chiều / ảnh / giá trị float64 khác | Giá trị float32 đổi | Max ∣Δ∣ float64 |','|---:|---|---:|---:|']
for case in a['epsilon_sensitivity']:
    sense.append(f"| {case['epsilon']:g} | {case['affected_dimensions']} / {case['affected_images']} / {case['affected_values']} | {case['changed_float32_values']} | {case['max_absolute_difference']:.12g} |")
real_table=['| Ảnh thật | Max sai số raw so với kho | Max sai số tọa độ oracle | Max sai số14 A2 |','|---|---:|---:|---:|']
for item in a['real_images']:
    real_table.append(f"| {item['image_name']} | {item['max_raw_error']:.3g} | {item['max_coordinate_oracle_error']:.3g} | {item['max_a2_oracle_error']:.3g} |")

save('A150_FORMULA_VERIFICATION.md',f'''# A150 — kiểm chứng công thức và artifact

{COMMON}

**Kết luận A:** tọa độ chuẩn hóa và số học14 A2 được kiểm chứng; Z-score **DEVIATION**. Không chứng nhận trọn14 đặc trưng EXACT khi endpoint/định nghĩa giải phẫu còn thiếu. Toàn bộ code/vector A giữ nguyên.

## A1 —478→68, tâm mắt và136 tọa độ

`geometry_features.py::INDICES` có68 phần tử duy nhất theo nhóm jaw17, mày5+5, nose9, mắt6+6, môi20. Bảng đầy đủ từng index68→MP478 và tọa độ thật nằm ở [landmark_mapping.csv](evidence/landmark_mapping.csv); bản code có dòng tại [source_listing.txt](evidence/source_listing.txt). `map_68_landmarks.py` có bảng cùng cấu trúc, nhưng chú thích của chính file gọi là ánh xạ thử nghiệm; không lấy tên file làm chứng nhận.

Code dùng `L=mean(p36..41)`, `R=mean(p42..47)`, `E=(L+R)/2`, `d=||L−R||₂`, `p′=(p−E)/d`. PDF viết trung điểm hai tọa độ mắt và phép chia d; **không chỉ định phải lấy mean của6 điểm mí**. Vì thế phép biến đổi tọa độ là EXACT có điều kiện, còn lựa chọn tâm mỗi mắt là UNVERIFIED về phê duyệt học thuật. Thứ tự A1 là x0,y0,…,x67,y67; không đưa z của MediaPipe vào vector.

Đã xem hai hình PDF trang8 (`pdf_page8_X31.png`, `pdf_page8_X33.png`) và ảnh audit có đánh số mốc. Có dấu hiệu topology mũi khác hình minh họa: code p30=MP1 có y≈149.59, p33=MP4 có y≈142.02 trên CFD00001, nên “đáy mũi” p33 nằm trên p30 trong cách gán code. Hình PDF không cho bảng ID MediaPipe hoặc nhãn index rõ từng nút để chốt mapping thay thế. **Ghi UNVERIFIED, không tự sửa mũi hoặc giả chứng minh đúng giải phẫu.** Tương tự, cách lấy rộng gò má p2/p14 và cao mặt từ midpoint hai đầu mày tới cằm cần thẩm quyền chốt endpoint.

`detect_landmarks` đặt `num_faces=1`, kiểm `len(result.face_landmarks)==1`; cấu hình này chỉ cho tối đa1 mặt trả về, không chứng minh ảnh không có mặt phụ. d<1e-6 bị từ chối; norm góc<1e-8 bị từ chối; vector cuối phải hữu hạn. PDF chưa quy định các ngưỡng đó. Không chạy main extractor/batch để ghi lại kho.

## A2 —14 đặc trưng, từng tử số/mẫu số/đơn vị

Mọi hàng dùng `features/A_geometry/src/geometry_features.py::calculate_ratios`; góc gọi `angle_degrees`. Ký hiệu `D(i,j)=||p_i−p_j||₂`, `H=D((p21+p22)/2,p8)`, `d=||L−R||₂`, `E=(L+R)/2`, `e=1e-8`. Mốc ghi 0-based; tên “trái/phải” là nhãn code, chưa xác nhận quy ước trái giải phẫu hay trái ảnh.

Ảnh thật minh họa **cfd_final_00001.png**. Số học oracle dùng `math.hypot/fsum/acos`, không lấy output hàm code làm expected. Tử số và mẫu số trong bảng tính scalar float64 từ cùng landmarks; code có phép toán/cast float32 nên có sai số làm tròn được đo riêng.

{chr(10).join(a2_table)}

Góc STT14: θ=degrees(acos(clip((p4−p8)·(p12−p8)/(||p4−p8||||p12−p8||),−1,1))). Tử số hiển thị ở hàng14 là góc kết quả scalar để tiện đối chiếu, không phải dot product; mẫu số thật của arccos được viết ở công thức này. Góc ở miền[0°,180°], đúng đơn vị độ PDF; góc quan sát vẫn phụ thuộc endpoint.

Với từng hàng: biểu thức code đầy đủ có trong bảng yêu cầu dưới đây; [a2_real_image_oracles.csv](evidence/a2_real_image_oracles.csv) lưu **56 dòng=14×4 ảnh**, numerator, denominator trước cộng ε, ε, code value, scalar value, tỷ lệ không guard và sai số. **UNVERIFIED không có nghĩa sai số học**:14 tests giải tích đều đạt, nhưng PDF chỉ nêu tên tỉ lệ, không đủ định nghĩa từng điểm/độ mở mắt và không có hồ sơ phê duyệt A tương đương D01–D17 của B.

{chr(10).join(real_table)}

Các regularizer A2 `+1e-8` làm biểu thức không bằng đúng phép chia không guard trên số thực; CSV lưu cả hai. Bảng PDF chưa cho công thức/biện pháp số học chi tiết cho từng tỉ lệ, nên ghi **quy ước chưa phê duyệt/UNVERIFIED**, không tự gộp nó thành EXACT hoặc âm thầm bỏ guard trong lần kiểm toán này. Riêng Z-score có phương trình mẫu số rõ ràng, xử lý ở mục tiếp theo.

## A3 — Z-score, ưu tiên cao nhất

PDF §2.5.2 trang17: `z_j=(x_j−mu_j)/(sigma_j+epsilon)`; query dùng lại tham số kho. Code thực tế:

```python
X = np.load(...).astype(np.float64)
mean = np.mean(X, axis=0)
std = np.std(X, axis=0)  # ddof=0
std_safe = np.where(std < 1e-8, 1.0, std)
X_normalized = (X - mean) / std_safe
np.save(..., X_normalized.astype(np.float32))
np.savez(..., mean=mean, std=std_safe)
```

Vị trí chính xác: `features/A_geometry/src/normalize_features.py` dòng24 tính mean, dòng25 tính std, **dòng28 thay std bằng1 theo ngưỡng**, **dòng31 chia cho std_safe**, dòng36 cast float32; từng dòng nằm trong source_listing. **DEVIATION** ở mẫu số so với PDF §2.5.2 trang17; `1e-8` trong `where` là ngưỡng, không phải ε được cộng. Saved key `std` là divisor hiệu dụng, không luôn là raw_sigma. Trên kho hiện tại0 chiều raw_sigma<1e-8; mọi divisor bằng raw_sigma, vẫn không bằng raw_sigma+ε với ε>0.

| Trường hợp độc lập | Code hiện tại | Công thức PDF với ε minh họa1e-8 |
|---|---|---|
| x=1,3,5; μ=3,σ=√(8/3) | z=(x−3)/σ | z=(x−3)/(σ+1e-8), khác dù rất nhỏ |
| Training7,7,7; query9 | divisor1 → qz=2 | divisor1e-8 → qz=200000000 |
| x=1e-10,3e-10,5e-10 | σ≈1.63299e-10<1e-8 → divisor1 | divisor≈1.01633e-8, khác xa divisor1 |

Không nhận hai công thức là tương đương chỉ vì training cột hằng cùng bằng0 hoặc thứ hạng ít thay đổi. PDF không chốt trị số ε; ba giá trị dưới đây chỉ là phép đo độ nhạy, không tạo output sửa chính thức:

{chr(10).join(sense)}

Chi tiết từng chiều tại [a_zscore_dimensions.csv](evidence/a_zscore_dimensions.csv). So sánh float64 ở đây dùng cùng μ, cùng raw_sigma của kho, tách khỏi sai số cast; cột float32 so sau cast giống dtype artifact. `mean_oracle_max_error={a['mean_oracle_max_error']}`, `std_oracle_max_error={a['std_oracle_max_error']:.3g}`, normalized cũ được tái tạo **đúng từng phần tử**. Nhất quán artifact cũ không loại bỏ DEVIATION.

## A4 —query và Top-5

Legacy search gọi đúng extractor và `(query_raw−saved_mean)/saved_std`, norm đủ150 chiều float64, loại chính query theo đường dẫn, argsort tăng dần. Worker A cũng dùng cùng stats cũ, đã thực thi thật trong `.venv311`. Bộ test kiểm lại3 ảnh legacy có PNG:00001,00088,00144, dựng ảnh mới trong audit và so pixel giải mã: **3/3 khớp**. Không ghi lại file legacy. CSV audit chứa15 dòng kết quả tính lại; file PNG lịch sử chỉ in khoảng cách3 chữ số, không có CSV gốc để đối chiếu float64 lịch sử đến mọi chữ số.

Phép thử giả định σ+ε cho2 query×2 chế độ A-only/A+B×3 epsilon tạo12 trường hợp. Top-5 không đổi trong12 trường hợp này, nhưng giá trị khoảng cách/median thay đổi; **không dùng việc thứ hạng trùng để chấp nhận code cũ hoặc chọn ε**. Xem `a_hypothetical_pdf_ranking_sensitivity.json`. Không phải benchmark chất lượng truy hồi.

## Bảng đối chiếu đầy đủ A

{table([r for r in ROWS if r['scope']=='A'])}
''')

save('B144_FORMULA_VERIFICATION.md',f'''# B144 — kiểm chứng công thức, mask và artifact

{COMMON}

**Kết luận B:** các thành phần, bin/L1, phép chiếu Hue, cấu trúc144, Euclid và số học của cấu hình hiện tại được kiểm chứng. Không chứng nhận toàn pipeline theo PDF vì **B12 thiếu stage mô-men chuẩn hóa trước ghép**. D01–D13/D15–D17 giữ nguyên phê duyệt; D14 không được dùng để bỏ yêu cầu thứ tự rõ của PDF.

Đã đọc trực tiếp `docs/B_implementation_decisions.md`, `B_color_feature_spec.md`, `report_compliance_audit.md`, `B_color_final_report.md` và source hiện tại. Báo cáo audit cũ ghi B30 UNVERIFIED trước phê duyệt; báo cáo finalize chốt D14. Trong audit nghiêm ngặt này, thứ tự được tái phân loại dựa vào nguyên văn PDF, không chỉ kế thừa kết luận cũ. Không sửa hồi tố bốn tài liệu đó.

## B1 — H–S

Source `region_descriptor`: lấy `image[mask>0]`, chuyển đúng BGR→HSV theo API OpenCV, chỉ H/S; histogram12×4, ravel C-order, chia tổng của48 bin. Bin đều H0,15,…,180, S0,64,…,256 là D01, không phải toàn bộ cạnh bin do PDF chốt. Không dùng V trong histogram; không lọc bão hòa và không thêm nền đen ngoài mask. Pixel đen thật nằm trong mask vẫn được tính.

Oracle mới tạo48 ô có khối lượng1..48, dùng chỉ số bin bằng phép chia nguyên và `bincount` thay `histogram2d`. Đã tính lại **5748 histogram=2 histogram×2 vùng×1437 ảnh**, từ ảnh gốc/raw mask; max sai số bằng0. Đây là kiểm chứng histogram trên toàn kho, không phải chỉ kiểm tổng L1.

## B2 — CIE-Lab

PDF yêu cầu mean/std/skewness/kurtosis trên L*,a*,b*; không chốt Pearson/excess, ddof/bias hay công thức suy biến. D02–D05 được chấp thuận: BGR float32/255→Lab; `mu=sum/N`, `m_k=sum((x−mu)^k)/N`, `std=sqrt(m2)`, `skew=m3/m2^(3/2)`, `kurt=m4/m2²` Pearson; std<1e-12 dùng std/skew/kurt0 và ghi warning.

Oracle giải tích black/white L*=0/100 cho mean50/std50/skew0/kurt1. Phân bố0,0,0,100 cho mean25/std25√3/skew2/√3/kurt7/3, khác excess−2/3. Phép chuyển màu đối chiếu thêm sRGB→XYZ→Lab bằng phương trình scalar/D65, tolerance0.3 cho LUT float OpenCV; phép kiểm này chứng minh biểu diễn CIE-Lab, **không thêm white point như điều khoản PDF mới**.

Đối chiếu full descriptor độc lập dùng `math.fsum` cho **18 vùng của9 ảnh thật** gồm CFD/HF, màu hiếm, khăn che và bàn tay; max error{b['max_descriptor_oracle_error']:.3g}. Các kỳ vọng không lấy từ `extract_color/region_descriptor`. Không tuyên bố đã tính độc lập toàn bộ mô-men của2874 vùng: kiểm toàn kho ở đây là histogram, stats/mapping/provenance; mô-men scalar đầy đủ là mẫu18 vùng có ghi danh tính.

## B3 — Hue vòng

Đúng10-bin Hue L1 và2 scalar; góc `phi=2*pi*H/180`. D06–D08: `C=mean(cos phi)`, `S=mean(sin phi)`, `R=clip(hypot(C,S),0,1)`, `mean=(atan2(S,C) mod2pi)/(2pi)`, `std=min(sqrt(-2log(max(R,1e-12)))/(2pi),1)`. R<1e-8: mean0+warning. Không thêm sin/cos vào vector; Euclid trên scalar Hue vẫn có mép vòng theo thiết kế, audit không thay metric.

Oracle hai góc H0/60 có mean1/6,R1/2,std√(2ln2)/(2π); H179/1 kiểm mép vòng; H0/90 có resultant≈0 và std clip1. Log oracle đầu có một expected quên clip; đã lưu thất bại và sửa expected của audit đúng D07, không thay code B.

## B4 — raw mask và ý nghĩa vùng

Nguồn `batch_uniface.py::make_masks` chọn labels1/17; class map gói UniFace hiện có ghi skin1,nose10,hair17. `full_color.py::verified_input` đọc đúng đường dẫn `masks/skin` và `masks/hair`, không đọc clean vào tuple tính descriptor. Mask clean có tồn tại phục vụ lịch sử, không được dùng cho B144_raw_v1.0.0.

Đã kiểm **2876 raw mask**: SHA-256 khớp manifest và receipt, binary uint8 256×256, count khớp, da/tóc không chồng lấn. Class-ID semantics của thư viện + code không phải GT pixel của mọi prediction. Contact sheet cho thấy da tay ở HF00722, tóc ở HF00694 chỉ355 pixel và vùng mặt phụ ở HF00333 có nguy cơ làm mask không đại diện đúng đối tượng. Không báo IoU/Dice/accuracy, không tự union skin+nose, erosion, đổi threshold hay chọn component lớn nhất.

HF00209, a_row_index918: skin22231 pixel/hair0 → `missing_region`, `hair:missing_empty(0<100)`, không có feature_row_index. Mask hợp lệ về định dạng có thể không đại diện màu tóc; ngưỡng100 là D12, không phải chứng nhận chất lượng.

## B5 — trình tự chuẩn hóa và thứ bậc thẩm quyền

PDF §2.3.3 trang13 mô tả mô-men chuẩn hóa theo kho trước khi ghép và Z-score từng chiều sau ghép. §2.5.2 trang17 tiếp tục nêu mô-men chuẩn hóa theo thống kê kho **trước khi ghép nối**; không hủy bước cuối được trang13 nêu.

Code hiện tại, xác minh trực tiếp:

```python
# color_features.py::extract_color
vector = np.r_[skin, hair].astype(np.float64)  # Lab moments chưa chuẩn hóa theo kho
# full_color.py::run
raw = np.asarray(vectors, dtype=np.float64).reshape(-1, 144)
stats = fit_standardizer(raw, profile='all144')
z = transform(raw, stats)  # duy nhất một stage kho sau ghép
```

**B12=DEVIATION về thứ tự/stage thiếu.** D14 cũ cho phép một lần all144 sau ghép không thể được dùng làm ngoại lệ cho câu mô-men-trước-ghép rõ của PDF. **B13=UNVERIFIED về công thức chi tiết stage trước ghép**: PDF không định nghĩa đầy đủ toán tử, epsilon/fallback; không tự khẳng định phải thêm bất kỳ standardizer cụ thể nào vào code trong audit.

Dòng nguồn cụ thể: `color_features.py:97` ghép72 với Lab moments chưa scale, `color_features.py:118` ghép Skin/Hair144; `full_color.py:187` tạo raw matrix và **`:189` fit/transform một lần sau ghép**. Biến `raw` được lưu làm descriptor chưa chuẩn hóa là hợp lý để truy vết; sai lệch được kết luận từ toàn luồng xử lý chỉ có một stage sau concat, không chỉ từ tên/raw dtype.

Phép minh họa hai lần Z-score với stage mô-men đầu dùng mean/std trên kho hiện tại, tất cả cột không hằng, cho khác biệt số tối đa≈7.93e-13 so với một lần. Đây là tính chất affine của trường hợp đã chọn, không chứng minh hai thuật toán bằng nhau với mọi epsilon/fallback/query. Ví dụ cột σ rất nhỏ có thể qua ngưỡng fallback khác giữa hai stage. Không được bỏ stage PDF chỉ vì số gần nhau hoặc Top-5 trùng.

Giữ D15 cho phép B dùng `std_safe` mà không cộng epsilon: phương trình `sigma+epsilon` ở trang17 được viết **riêng cho A**, không tự áp đặt cho B. B không bị đánh DEVIATION mẫu số chỉ vì giống hiện thực A; sai lệch B ở đây là stage trước ghép.

## B6 — artifacts/query/retrieval

Raw và normalized đều1437×144 float64, hữu hạn, khớp metadata/fit manifest;9 file core integrity khớp. Toàn ma trận normalized tái tạo chính xác bằng stats đã lưu, so oracle fsum max{b['z_oracle_max_error']:.3g}. Mean oracle max{b['mean_oracle_max_error']:.3g}, raw_std oracle max{b['std_oracle_max_error']:.3g};0 chiều std<1e-8 trên kho. Các cột hằng vẫn có analytic test, query khác mean chia divisor1 đúng D15.

Bốn cột circular của toàn raw matrix đã kiểm range: min={b['circular_raw_min']:.12f}, max={b['circular_raw_max']:.12f}, tất cả trong[0,1] trước Z-score. Sau Z-score không buộc histogram L1 hoặc circular trong[0,1]; không chuẩn hóa lại để làm đẹp miền giá trị.

Query worker đã thực thi trong `.venv-uniface` với raw masks hiện có, không inference segmentation mới, không refit: query00001 bằng đúng normalized hàng kho. QueryHF00209 không lưu vector B; có status thiếu rõ ràng. B-only Euclid đủ144, self-match theo image_id, tie theo filename; **50 dòng Top-5/10 query** tính lại scalar fsum khớp thứ tự, max distance error{b['max_saved_b_distance_error']:.3g}. Đây là kiểm số học, không phải relevance evaluation/holdout.

Helper `fit_standardizer(profile='moments_only')` còn callable và bỏ120 chiều Z-score, là B18 DEVIATION nếu dùng như cấu hình PDF. Runner hiện tại đã chặn, B144 v1 dùng all144. Giữ lịch sử, không xóa helper hoặc kết quả nghiên cứu trong audit.

## Bảng đối chiếu đầy đủ B

{table([r for r in ROWS if r['scope']=='B'])}
''')

measure_table=['| Chỉ số model/proxy | Min | Median | Max |','|---|---:|---:|---:|']
for key,value in ds['measurements'].items():
    measure_table.append(f"| {key} | {value['min']:.8f} | {value['median']:.8f} | {value['max']:.8f} |")
visual=read(EVIDENCE/'visual_review_findings.csv')
vtable=['| Ảnh | Quan sát trực tiếp / bằng chứng | Trạng thái |','|---|---|---|']
vtable += [f"| {r['image_name']} | {clean(r['observation'])}; {r['evidence']} | {r['status']} |" for r in visual]
save('DATASET_REPORT_COMPLIANCE.md',f'''# Dataset — đối chiếu §1.1–1.3

{COMMON}

**Kết luận:** định dạng/số lượng/catalog được kiểm chứng, nhưng dataset hiện có vi phạm tiêu chí không có mặt phụ và không che miệng. Chưa thể chứng nhận mọi ảnh chính diện,1135 người độc lập, độ tuổi18–60 hoặc lịch sử tiền xử lý. Không thay đổi/xóa bất kỳ ảnh hay nhãn nào.

## Phép đo thực tế toàn bộ1438 ảnh

Đọc trực tiếp PNG IHDR và decodeOpenCV:1438/1438 RGB8,256×256, tỉ lệ1:1;1438 SHA khớp metadata,0 duplicate byte,0 mồ côi;CFD710/HF728. Độ duy nhất byte không phải độ duy nhất danh tính. “PNG chất lượng95” ở PDF không ánh xạ một-một sang tham số nén của PNG; thiếu log encoder nên không bịa trị số nén/chất lượng hoặc đổi định dạng.

Detector audit dùng model FaceLandmarker cục bộ với `num_faces=5`, không dùng cấu hình capped1 của extractor làm phép kiểm một mặt. Kết quả model:1438 ảnh đều trả1 face,478 landmarks; lưu số lượng từng ảnh và toàn bộ landmarks trong `dataset_landmarks478.npz`. **Mô hình vẫn bỏ sót mặt phụ nhìn thấy ở mép**, nên không coi1438×1 là GT hay chứng nhận tiêu chí. Các Euler từ matrix model chưa hiệu chuẩn camera, không dùng làm bằng chứng chính xác yaw/pitch<5°.

{chr(10).join(measure_table)}

`roll_deg` dùng đường nối centroid6 mí; `iris_*` dùng MP468/473; hai định nghĩa được đo riêng để không tùy tiện đồng nhất tâm mí với tâm đồng tử. Centroid IPD có9 ảnh ngoài khoảng27.23–32.61% của PDF; median30.66188% khác29.45%. Iris median30.74760% cũng khác29.45%. Đây là **chênh lệch quan sát bằng model cần điều tra**, còn UNVERIFIED vì chưa có phép đo mắt chuẩn và provenance alignment để kết luận GT sai đúng. Không tự điều chỉnh scale ảnh cho khớp thống kê PDF.

Mesh-height median78.56407% gần78.6% trong PDF, nhưng mesh extrema không mặc nhiên là face bounding box/đỉnh đầu-cằm. Tâm mắt y và mặt nghiêng có phân bố đã đo; thiếu tolerance của “cố định/40%/giữa ảnh” nên không chứng nhận chính xác mọi ảnh hoặc tự đặt ngưỡng sau khi xem dữ liệu. Ngưỡng sàng lọc2 điểm phần trăm ở CSV chỉ là heuristic công khai để chọn review.

## Các ảnh cần xem xét, có bằng chứng

{chr(10).join(vtable)}

- [Contact sheet1](evidence/dataset_mask_review_page1.png): HF00313,00333,00561,00610; ảnh gốc/raw skin/raw hair.
- [Contact sheet2](evidence/dataset_mask_review_page2.png): HF00694,00722,00209,00676.
- [visual_review_findings.csv](evidence/visual_review_findings.csv):8 quan sát thủ công của audit.
- [dataset_model_review_candidates.csv](evidence/dataset_model_review_candidates.csv): toàn bộ ảnh được phép đo model/heuristic gắn cờ, kèm số đo và lý do. Cờ không phải nhãn GT hoặc đề nghị tự xóa ảnh.
- Dataset `review_candidates.csv` lịch sử có9 cờ; audit không tự coi tất cả đúng, vẫn giữ riêng nguồn/lý do. HF00313/HF00610 được báo cờ lịch sử nhưng chưa đủ quan sát để kết luận cùng lỗi DS05 như HF00333/HF00561.

Ảnh HF00722 cho thấy tay/ngón chồng vùng miệng, vi phạm rõ yêu cầu §1.2. Raw skin còn chọn da tay, nhưng “mask chứa da” không đồng nghĩa đã xác minh đúng facial ROI hoặc đo được segmentation accuracy. HF00694/HF00209 có khăn che tóc; PDF yêu cầu không che mắt/mũi/miệng, không cấm riêng mọi khăn trùm tóc, vì thế không tự đánh DEVIATION chỉ từ khăn.

## Danh tính và metadata

710 dòng CFD có person_id,407 ID phân biệt theo nguồn và303 dòng lặp thêm;728 HF không có person_id. Con số407+728=1135 chỉ đúng nếu giả định mỗi HF là người mới khác nhau và không trùng CFD, điều chưa được dữ liệu xác minh. Không có nhãn cảm xúc đủ để chứng nhận303 dòng lặp đều đúng diễn giải cảm xúc của PDF. Không suy đoán tuổi/giới/sắc tộc/danh tính từ ảnh; catalog hiện thiếu trường tuổi và provenance nhãn đủ để xác nhận18–60.

CSV lưu ID/name/path/hash và nguồn; không có vị trí x/y hai mắt đầy đủ, chưa tìm thấy hiện thực CSDL hoặc log alignment gốc chứng minh lưu vị trí hai mắt vào DB. Ảnh PNG cuối không chứng minh đã crop/rotate/resize bằng bicubic. `map_68_landmarks.py` dùng INTER_CUBIC để phóng ảnh minh họa không phải bằng chứng bicubic tiền xử lý dataset.

## Bảng đối chiếu dataset

{table([r for r in ROWS if r['scope']=='DATASET'])}
''')

save('AB_RETRIEVAL_COMPLIANCE.md',f'''# A+B — median normalization, join và phụ thuộc phiên bản

{COMMON}

**Kết luận:** số học/join/calibration của thử nghiệm hai bộ tái lập, nhưng mọi output phụ thuộc A hiện mang sai lệch A12. Chưa có fusion chính thức A+B+C1+C2. Không sửa file `retrieval/search_ab.py`, worker, calibration, CSV/JSON hoặc preview cũ trong lần audit này.

## Luồng đã đối chiếu source và oracle

`join_galleries` tạo map A bằng ID(stem nếu không có cột), kiểm tra chéo a_row_index, lấy B bằng feature_row_index. B chỉ1437 hàng do thiếu HF00209, không zip trực tiếp hai ma trận. Oracle có A mất hàng giữa, B đảo metadata và chỉ số vector khác thứ tự, cho đúng ghép3/6 và4/8; còn có tests trùng ID/chỉ số/ID không tồn tại.

`rankings` tính riêng Euclid trên150/144 chiều float64, rồi:

```text
mA = median of dA on saved common image pairs
mB = median of dB on the SAME saved common image pairs
normalizedA = dA / (mA + epsilon)
normalizedB = dB / (mB + epsilon)
D_AB = weight_a*normalizedA + weight_b*normalizedB
```

Không ghép294 chiều rồi tính norm, không dùng bình phương Euclid, không cộng raw d. Oracle3–4–5 nhiều chiều và epsilon0.5 cố ý khác mặc định kiểm chính xác vị trí ε trong mẫu số; tổng trọng số.25/.75 kiểm khác norm của block đã scale. Thứ hạng tie theo filename.

## Cặp đại diện và median

Sort1437 IDs chung; chọn20000 unordered non-self pairs không hoàn lại, seed42, từ1031766 cặp có thể có. Bảng ID được tái lập độc lập bằng **hạng tam giác + bisect** thay `np.triu_indices` của implementation; tất cả20000 ID khớp. Scalar fsum Euclid trên cùng pairs khớp khoảng cách đã lưu. Phân bố CFD/CFD4880,CFD/HF10073,HF/HF5047; không chọn theo Top-5.

MedianA={b['ab_median_a']:.15f}; medianB={b['ab_median_b']:.15f}. Khác biệt≈3.6e-15 khi dùng fsum thay np.linalg ở medianA là làm tròn phép cộng, không sai công thức. Cùng pairs, không median theo query. Cache lưu fingerprint vector/stats/metadata, hash pairCSV, medians vàepsilon; nguồn hiện tại khớp. Tests cache stale/tamper từ chối đúng.

PDF không chỉ định seed42,20000 cặp hoặc ε=1e-8. Thuật toán/mẫu hiện tại được kiểm chứng về tái lập; tính đại diện cho mọi subgroup và phê duyệt riêng các con số chưa được chứng minh nên ghi UNVERIFIED, không gán “EXACT theo PDF” cho lựa chọn đó. Giữ nguyên trong audit.

## Query, self-match và thiếu B

Ảnh kho khớp hash dùng đúng saved normalized vectors; ảnh mới gọi subprocess `.venv311` cho A và `.venv-uniface` cho B, truyền.npy. Audit đã thực thi worker A/B với query00001, đầu ra bằng đúng transform cũ/hàng B; missing-B workerHF00209 không sinh vector. Đây là smoke test dùng ảnh có sẵn qua nhánh new-query, không phải holdout hay benchmark chất lượng. Không cài/tải model, không chạy segmentation mới khi đã truyền raw masks.

Self-match AB dùng hash byte→image IDs; loại mọi ID trùng. Ảnh PNG mã hóa lại có pixel y hệt nhưng byte khác không tự nhận trùng; đây là giới hạn đã công khai, PDF không định nghĩa danh tính theo pixel/person. Legacy A-only loại theo path và B-only chính thức theoID, không tự trình bày ba quy tắc là giống hệt.

Cả3 chế độ AB/A-only/B-only so trên cùng1437 ứng viên đủ A/B. HF00209 thiếu B được loại khỏi candidate sets; nếu nó là query: A-only có kết quả, B-only/AB rỗng, distanceB/total null; không vector0, không dB0, không tự thay weights. Phép tính normalizedA vẫn dùng cùng medianA. Dataset không bị xóa ảnh; đây là tập ứng viên hợp lệ của thử nghiệm.

## Trọng số và phạm vi

A=.5,B=.5 được người dùng yêu cầu ở nhiệm vụ thử nghiệm trước, là APPROVED IMPLEMENTATION DETAIL của **hai bộ**. PDF quy định tổng4 thành phần; string EXPERIMENT và results.json đều ghi chưa phải fusion chính thức4 bộ. Không tự triển khai C1/C2 hoặc gán đã có đủ854 chiều trong workspace.

## Cảnh báo phụ thuộc A12

File [legacy_dependency_register.json](evidence/legacy_dependency_register.json) liệt kê từng calibration/ranking/preview/query artifact trong A+B, các A-only preview và hồ sơ ab_validation; ghi hash A normalized/stats và trạng thái `LEGACY_A_NORMALIZATION_NONCONFORMING`. B-only của experiment còn cột dA/D_AB nên artifact cũng phụ thuộc A, dù thứ tự riêng dB có thể không đổi.

Sau sửa A phải tính lại normalized A, query A, medianA trên pairs cùng ID để so sánh, rồi D_AB/CSV/JSON/preview; không tái dùng median cũ chỉ vì giá trị gần nhau. Nếu B stage sửa tạo vector mới, medianB và B-only cũng phải tính lại. Hệ thống fingerprint đang có sẽ chặn cache khi nguồn đổi; các file legacy vẫn được giữ nguyên để truy vết.

Thử ε minh họa1e-12/1e-8/1e-6 cho2 query/2 chế độ với pairs giữ cố định không làm Top-5 đổi trong12 trường hợp, nhưng median/khoảng cách đổi. Không suy ra toàn kho ranking không đổi, không suy ra chất lượng tốt/xấu và không dùng để chọn ε. Xem `a_hypothetical_pdf_ranking_sensitivity.json`.

## Bảng đối chiếu A+B

{table([r for r in ROWS if r['scope']=='AB'])}
''')

save('REMEDIATION_PLAN.md',f'''# Phương án sửa theo PDF — chưa áp dụng

{COMMON}

**Trong nhiệm vụ này chỉ kiểm toán và chuẩn bị phương án. Chưa sửa code/vector A/B, chưa thay PDF/dataset, chưa triển khai C1/C2.** Việc sửa sau này phải theo đúng phạm vi sai lệch đã xác minh; không dùng Top-5 làm hàm mục tiêu.

## 1. Bảo lưu baseline

Giữ nguyên source hiện tại, hai kho vector/stats/mapping và toàn bộ output A-only/B-only/AB. Dùng hash tại `protected_before.json`, `protected_supplement_legacy_previews.json` và `legacy_dependency_register.json` làm mốc; không rename/xóa/ghi đè file cũ. Tạo schema/version/output mới khi được giao triển khai, ví dụ `outputs/A_geometry/features_report_v2/`, `outputs/B_color/color_features_report_v2/`, `outputs/retrieval/ab_report_v2/`; đây là **đường dẫn đề xuất, chưa tạo artifact sửa**.

## 2. A12 — sửa mẫu số Z-score A theo §2.5.2

Thay đúng phép biến đổi, giữ150 chiều, extractor/mapping/raw gallery và Euclid nếu chưa có căn cứ sai lệch khác. Dùng mean/std kho cũ có thể tính lại kiểm chứng từ raw, ddof0 giữ như hiện tại khi PDF chưa buộc đổi. Điều bắt buộc là **mẫu sốraw_sigma+epsilon**, không `where(sigma<threshold,1,sigma)`.

```python
# Pseudocode cho phiên bản mới; KHÔNG phải code đã áp dụng.
mean = raw.astype(float64).mean(axis=0)
raw_sigma = raw.astype(float64).std(axis=0, ddof=0)
epsilon = configured_positive_epsilon  # PDF chưa cho trị số; phải ghi nhận quyết định
divisor = raw_sigma + epsilon
z = (raw - mean) / divisor
```

Lưu riêng `mean`, `raw_sigma`, `epsilon`, `divisor`, fit manifest/hash, schema ID và dtype. Không ghi key `std` mơ hồ mà không mô tả raw hay effective divisor. Nếu giữ float32 để tương thích dung lượng thì cast ở cuối và công khai; query phải dùng đúng effective divisor/schema, không lấy std_safe từ legacy. Không tự loại chiềuσ0, không ép query chiều hằng thành0 và không bỏ sốhạngε cho chiềuσ>0.

PDF không quy định trị sốε nên audit không chọn một “ε chính thức” bằng thứ hạng. Trước implementation phải chốt một giá trị dương/versioned theo thẩm quyền dự án. Các trị1e-12/1e-8/1e-6 trong audit chỉ là độ nhạy; không phải phê duyệt config mới.

Phải cập nhật đồng bộ normalizer, A-only query, worker A và gallery loader theo phiên bản. Kiểm thử normalσ,σ0,σ rất nhỏ và query ngoài kho; expected phải dùng công thức PDF trực tiếp. Không chỉ kiểm training mean0/std1 hoặc Top-5.

## 3. B12 — khôi phục stage mô-men trước ghép, tách khỏi Z-score cuối

PDF trang13/17 buộc có chuẩn hóa mô-men theo kho trước concat; trang13 buộc Z-score từng chiều sau concat. Code mới cần biểu diễn/ghi nhận rõ hai phạm vi này. Tuy nhiên PDF không định nghĩa toán tử chi tiết của stage mô-men; không tự lấy “hai lần Z-score” làm đáp án duy nhất. Chốt mô tả toán tử/stats/fallback theo PDF và các quy ước không xung đột, lưu quyết định mới thay D14 chỉ ở phần thực sự mâu thuẫn thứ tự.

Luồng phiên bản mới đề xuất:

```text
Ảnh + raw masks class1/17
  -> descriptor HS48/Lab12/Hue12 của từng vùng
  -> normalize 24 Lab moments bằng tham số kho đã fit/lưu riêng
  -> concatenate B144, giữ nguyên serialization
  -> final all144 Z-score bằng stats kho của vector sau stage trước
  -> Euclid144
```

Giữ D01–D13/D15–D17 về bins, CIE-Lab, Pearson, ddof, circular std, class/ROI, raw mask, minimum100, serialization, missing, fit scope và metric trừ khi có bằng chứng mới mâu thuẫn yêu cầu rõ. Không đổi Skin+Nose/Clean, không xóa outlier, không tăng/giảm chiều, không thêm sin/cos hay đổi metric. Đặc biệt **không áp dụng `sigma+epsilon` của A sang B một cách máy móc**.

Lưu các stats của stage mô-men và stage cuối tách biệt; query dùng lại cả hai đúng thứ tự. Giữ raw descriptor cũ như baseline; không mặc định cần chạy segmentation lại vì raw masks hiện đã có lineage/hash. Kiểm tra trường hợp nonconstant, constant/tinyσ, new query, fallback và clipping; không nhận hai luồng bằng nhau chỉ vì affine cancel trên kho hiện tại.

## 4. B18 — cách ly helper lịch sử

`moments_only` không đạt bước cuối all144. Runner hiện đã chặn, nên không cần sửa vector v1 chỉ vì helper này tồn tại. Nếu bổ sung entry point mới, enforce schema/profile all144 ngay tại ranh giới production và có test từ chối profile khác. Giữ helper/snapshot nghiên cứu để truy vết; không tự xóa code hoặc đổi nhãn artifact cũ thành compliant.

## 5. Dataset DS05/DS10 và các mục UNVERIFIED

Giữ toàn bộ ảnh hiện tại. Gắn cờ trong audit/catalog phiên bản mới (không sửa catalog cũ), chỉ rõ HF00333/HF00561 mặt phụ, HF00722 che miệng. Chưa tự crop/inpaint/loại ảnh hoặc đổi mask để tạo dataset đẹp hơn. Nếu được giao làm một dataset tuân thủ mới, cần quy trình kiểm duyệt/source thay thế và version riêng; mọi thay đổi phải bám tiêu chí PDF, giữ mapping/lineage tới bản cũ.

Yaw/pitch, IPD/tâm mắt, face-height ratio,1135 người/303 cảm xúc,18–60 tuổi, bicubic/crop/PNG95 và CSDL cần chứng cứ bổ sung/định nghĩa phép đo đã chốt, không suy ra từ tên file, review cũ hay mô hình. Mapping A và14 endpoint cần bảng thẩm quyền; **chưa được tự đổi các điểm A vì chúng đang UNVERIFIED**. Cờ topology mũi cần giải quyết bằng đối chiếu tài liệu/mốc có thể kiểm chứng, không chọn phương án cho Top-5 đẹp.

## 6. Tính lại các phụ thuộc và đánh giá

1. Bảo toàn baseline/hash và giữ danh tính1438/1437 cùng missing policy.
2. Tạo A/B schema/stats/vector mới theo đúng phần sửa; không ghi đường dẫn legacy.
3. Dùng lại **cùng pair IDs** để so sánh phiên bản; tính lại dA/dB và median cho mọi bộ có vector thay đổi, lưu cả median mới và hash nguồn. Nếu tập ID đổi do dataset phiên bản mới, phải tạo pair manifest/calibration mới rõ ràng.
4. Tính lại query transforms, Euclid riêng, median normalization, D và Top-5/CSV/JSON/preview. Đánh dấu rõ version trong A-only/B-only/AB. Không nhận một loader std_safe cũ với một vector mới `sigma+epsilon`.
5. Chạy oracle công thức trước; so sánh số học/ranking để đánh giá tác động, **chấp nhận thứ hạng hoặc chất lượng trực quan kém hơn nếu đó là hệ quả tuân thủ PDF**. Không refit epsilon/weights theo query sau khi xem Top-5.
6. Chất lượng retrieval cần relevance labels/protocol độc lập (tách người/biểu cảm nếu có thẩm quyền nhãn). Kiểm tra công thức và relevance là hai kết luận khác nhau; không báo accuracy/IoU/Dice thiếu GT.

## 7. Điều kiện hoàn tất trước C1/C2

A12 và B12 đã sửa/kiểm chứng ở phiên bản mới; input dataset có giao thức tuân thủ và các vi phạm được giải quyết minh bạch; mapping/endpoint và ε được ghi nhận đủ; artifact/query/calibration nhất quán theo phiên bản. Chỉ sau đó mới có thể kết luận A/B sẵn sàng làm nền tảng phù hợp phạm vi C1/C2. **Chưa triển khai C1/C2 trong nhiệm vụ này.**

## Các sai lệch mà kế hoạch này xử lý

{table([r for r in ROWS if r['status']==DEV])}

## Lệnh kiểm chứng thực tế đã chạy thành công

Các lệnh sau chỉ tạo evidence mới trong `docs/audits/`; chúng không phải lệnh áp dụng remediation:

```powershell
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/verify_a.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/measure_dataset.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/verify_b_ab.py
.\\.venv311\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/test_a_oracles.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/test_b_ab_oracles.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/write_reports.py
.\\.venv-uniface\\Scripts\\python.exe -X utf8 -B docs/audits/audit_tools/verify_scope.py
```

Tests cũ được chạy qua unittest discovery với log chuyển vào evidence, không gọi các main ghi output chính thức. Worker query đã chạy bằng2 interpreter gốc, truyền raw masks B hiện có và `--output docs/audits/evidence/query_worker_*`; không chạy search main để ghi lại retrieval cũ. Không cài thư viện/tải model.
''')
print(json.dumps(dict(reports=6,requirements=len(ROWS),status_counts=dict(counts)),indent=2))
