"""Granular requirement register; a status applies only to the stated scope."""
from common import *

EXACT='EXACT'
DETAIL='APPROVED IMPLEMENTATION DETAIL'
DEV='DEVIATION'
OPEN='UNVERIFIED'
ROWS=[]
inventory=json.loads((EVIDENCE/'source_inventory.json').read_text(encoding='utf-8'))


def code(path,symbol=''):
    entry=next(r for r in inventory if r['path'].replace('\\','/')==path)
    definitions=[d for d in entry['definitions'] if d['name']==symbol]
    return f"{path}:{definitions[0]['line'] if definitions else 1}"+(f'::{symbol}' if symbol else '')


def add(scope,key,requirement,page,source,formula,evidence,status,action='Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản.'):
    assert status in (EXACT,DETAIL,DEV,OPEN)
    ROWS.append(dict(id=key,scope=scope,requirement=requirement,pdf_page=page,code=source,
                     formula=formula,evidence=evidence,status=status,action=action))


G='features/A_geometry/src/geometry_features.py'
N='features/A_geometry/src/normalize_features.py'
AS='retrieval/search_geometry.py'
C='features/B_color/src/color_features.py'
F='features/B_color/src/full_color.py'
BS='features/B_color/src/search_full_color.py'
AB='retrieval/search_ab.py'
W='retrieval/ab_query_worker.py'

add('SOURCE','S01','Đúng PDF chuẩn, SHA-256 trước audit','1–18','csdldpt.pdf','SHA-256 = 8d390c…70c80','protected_before.json; pdf_pages.json',EXACT,'Giữ PDF bất biến.')
add('SOURCE','S02','Đọc đủ 18 trang, phân biệt trang PDF với mục lục','1–18','PDF; source_inventory.json','18 trang; mục lục không trùng trang vật lý','pdf_full_text.txt; hai hình nhúng trang 8 đã kiểm tra',EXACT)
add('SOURCE','S03','Không sửa nguồn, vector, dataset, PDF hoặc C1/C2','Ràng buộc nhiệm vụ','features/; outputs/; dataset; models/','So sánh hash trước/sau; chỉ tạo docs/audits','protected_before.json; scope_validation.json',EXACT)

add('A','A01','478 landmarks từ MediaPipe, sau đó chọn 68','5,8',code(G,'detect_landmarks'),'pixel=(lm.x*w,lm.y*h); points_478[INDICES]','dataset_verification.json: 1438×478; a_verification.json',EXACT)
add('A','A02','Số điểm và thứ tự nhóm: hàm, mày, mũi, mắt, miệng','8–9',code(G),'17+5+5+9+6+6+20=68; 68 ID duy nhất','landmark_mapping.csv; test_flatten_order_x_y_and_136_plus_14',EXACT,'EXACT về số lượng/nhóm, không chứng nhận từng mốc giải phẫu.')
add('A','A03','Ánh xạ từng ID 478→68 và đúng vị trí giải phẫu','8 (hình),9',code(G),'Danh sách INDICES hiện có; đặc biệt NOSE=[168,6,197,1,129,48,4,278,358]','landmark_mapping.csv; pdf_page8_X31.png; cfd_final_00001_68_annotated.png',OPEN,'Cần bảng ID chuẩn/canonical có thẩm quyền; hình mũi có dấu hiệu khác, không tự thay ID.')
add('A','A04','Tâm hai mắt là trung điểm hai mắt','5,9',code(G,'normalize_landmarks'),'C=(eye_l+eye_r)/2','test_normalization_known_centers_and_ipd; oracle trên 4 ảnh thật',EXACT,'Kết luận điều kiện trên hai tâm mắt đã chọn; lựa chọn tâm xem A05.')
add('A','A05','Định nghĩa tọa độ tâm mỗi mắt','5,9',code(G,'normalize_landmarks'),'eye_l=mean(p36:p42); eye_r=mean(p42:p48)','Ảnh mốc và tọa độ thực; PDF không cho công thức trung bình 6 mí',OPEN,'Chốt quy ước tâm mí hay tâm mống mắt; không coi mặc nhiên đã được phê duyệt.')
add('A','A06','Chuẩn hóa tọa độ P′=(P−C)/d','9',code(G,'normalize_landmarks'),'(points-center)/||eye_l-eye_r||₂','test_normalization_known_centers_and_ipd; a_verification.json',EXACT)
add('A','A07','A1 136 tọa độ, thứ tự x,y theo từng mốc','9',code(G,'extract_geometry'),'normalized.flatten() → x0,y0,…,x67,y67','test_flatten_order_x_y_and_136_plus_14; raw shape 1438×150',EXACT,'Thứ tự x,y được kiểm chứng; PDF không liệt kê serialization chi tiết.')
add('A','A08','Xử lý thiếu landmark/không hợp lệ','8–9; PDF không chốt fallback',code(G,'detect_landmarks'),'num_faces=1; reject len!=1; d<1e-6 → ValueError; finite assert','test_zero_eye_distance_rejected; code caps num_faces at 1',OPEN,'Không dùng num_faces=1 làm bằng chứng không có mặt phụ; chốt chính sách lỗi.')
add('A','A09','Ghép A1 và đủ 14 thành phần A2 thành A150','9–10,16',code(G,'extract_geometry'),'concatenate(A1[136],A2[14])','test_flatten_order_x_y_and_136_plus_14; 4 vector thật tái lập',EXACT,'Chỉ chứng nhận cấu trúc, không thay cho kiểm toán từng tỉ lệ.')

A2_NAMES=['Rộng gò má / cao mặt','Khoảng cách hai mắt / cao mặt','Bề ngang mắt trái / khoảng cách hai mắt',
    'Bề ngang mắt phải / khoảng cách hai mắt','Độ mở mi mắt trái','Độ mở mi mắt phải',
    'Rộng cánh mũi / khoảng cách hai mắt','Rộng miệng / khoảng cách hai mắt','Độ mở môi / khoảng cách hai mắt',
    'Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt','Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt',
    'Khoảng cách chóp mũi–đáy cằm / cao mặt','Rộng xương hàm / cao mặt','Góc xương hàm tại cằm']
A2_FORMULAS=['D(2,14)/(H+e)','d/(H+e)','D(36,39)/(d+e)','D(42,45)/(d+e)',
    '(D(37,41)+D(38,40))/(2D(36,39)+e)','(D(43,47)+D(44,46))/(2D(42,45)+e)',
    'D(31,35)/(d+e)','D(48,54)/(d+e)','D(62,66)/(d+e)','D(E,p30)/(d+e)',
    'D(E,(p48+p54)/2)/(d+e)','D(30,8)/(H+e)','D(4,12)/(H+e)',
    'degrees(acos(clip((p4−p8)·(p12−p8)/(D(4,8)D(12,8)),−1,1)))']
for i,(name,formula) in enumerate(zip(A2_NAMES,A2_FORMULAS),1):
    add('A',f'A2-{i:02}',name,'9' if i<=8 else '10',code(G,'calculate_ratios'),formula,
        f'test_A2_{i:02}_analytic_operands; a2_real_image_oracles.csv: 4 ảnh, riêng đặc trưng {i}',OPEN,
        'Số học đã khớp oracle; PDF thiếu endpoint/định nghĩa chi tiết và A chưa có quyết định phê duyệt tương ứng. Không suy ra EXACT từ test đạt.')
add('A','A10','Công thức Euclid giữa hai mốc và góc arccos tính bằng độ','9–10',code(G,'angle_degrees'),'D=√(dx²+dy²); θ=degrees(acos(u·v/(||u||||v||)))','test_angle_right_straight_and_degenerate; 14 oracle A2',EXACT,'EXACT về phép toán/đơn vị, tách riêng câu hỏi endpoint ở A2-14.')
add('A','A11','ε và các ngưỡng bổ sung trong tỉ lệ/landmark','9–10 (không chốt)',code(G,'calculate_ratios'),'e=1e-8; d guard=1e-6; angle norm guard=1e-8','source_listing.txt; a2_real_image_oracles.csv có giá trị không cộng e',OPEN,'Công khai quy ước chưa phê duyệt; không gán epsilon A2 cho Z-score A.')
add('A','A12','Z-score A phải có mẫu số σ+ε','17 §2.5.2',code(N,'main'),'std_safe=where(std<1e-8,1,std); Z=(X−mean)/std_safe','3 oracle normal/zero/tiny sigma; a_zscore_epsilon_sensitivity.csv',DEV,'Sửa theo PDF trong phiên bản mới, lưu raw_sigma và epsilon; cập nhật query và mọi phụ thuộc.')
add('A','A13','Cách fit mean/std và ddof','11,17',code(N,'main'),'mean(X,axis=0), std(X,axis=0,ddof=0)','a_verification.json: mean error=0, sigma error≤8.89e-16',OPEN,'ddof=0 đã đo đúng code, nhưng PDF không chốt ddof; giữ nguyên khi sửa mẫu số nếu không có căn cứ đổi.')
add('A','A14','Giá trị ε Z-score A','17',code(N,'main'),'Không có epsilon cộng mẫu số; 1e-8 chỉ là ngưỡng std','source_listing.txt; sensitivity ε=1e-12/1e-8/1e-6',OPEN,'PDF không cho trị số; phải lưu rõ một ε dương, không nhận ngưỡng std là ε.')
add('A','A15','Raw, stats và normalized A nhất quán với phiên bản code hiện tại','11,17',code(N,'main'),'1438×150; raw float32→float64 fit→normalized float32','a_verification.json: tái tạo normalized đúng từng phần tử',EXACT,'EXACT về tính toàn vẹn phiên bản cũ; A12 vẫn DEVIATION.')
add('A','A16','Query A dùng lại đúng stats kho','17',code(AS,'main')+'; '+code(W,'normalize_a'),'(query_raw.astype(float64)−mean)/saved_std','query_worker_verification.json; tái lập 4 raw vector thật',EXACT,'Dùng lại đúng stats cũ không làm mẫu số cũ tuân thủ PDF.')
add('A','A17','Euclid đủ 150 chiều, sắp tăng dần','11,17–18',code(AS,'main'),'norm(X.astype(float64)−q,axis=1); argsort','3 PNG A-only tái tạo đúng pixel; 15 khoảng cách lưu trong evidence',EXACT)
add('A','A18','Self-match A-only và tie-break','18; PDF không chốt danh tính',code(AS,'main'),'Loại theo Path.resolve; argsort không có filename tie-break','source_listing.txt; A-only 3 query loại đúng path; AB khác legacy',OPEN,'Công khai quy ước; bản sao đổi tên/đổi encoding chưa được legacy loại theo ID.')
add('A','A19','Top-5 A-only đã lưu có tái lập được','11,18',code(AS,'main'),'3 query 00001/00088/00144, render lại layout hiện hành','a_verification.json::legacy_all_previews: 3/3 exact pixel reproduction',EXACT,'Không có CSV lịch sử; đối chiếu PNG xác nhận tên/thứ tự/nhãn khoảng cách đến 3 chữ số.')
add('A','A20','Giá trị thông tin: phương sai giữa người lớn, trong người nhỏ; ổn định màu/sáng/scale','7–8,10–11',code(G,'extract_geometry')+'; '+code(N,'main'),'Có sigma theo kho và invariance tọa độ; chưa có đánh giá giữa/trong người đầy đủ','a_zscore_dimensions.csv; translation/scale oracle; metadata HF thiếu person_id',OPEN,'Không đồng nhất độ phân tán kho với discriminability hoặc ổn định thực nghiệm; cần nhãn/protocol độc lập.')

for key,req,page,fn,formula,ev in [
    ('B01','Hai vùng da/tóc, 72 mỗi vùng, tổng B144','11–13,16','extract_color','2×(48+12+10+1+1)=144','raw shape1437×144; selected descriptor oracles'),
    ('B02','HSV chỉ dùng H và S, không V trong histogram','12','region_descriptor','HS bins trên hsv[:,0],hsv[:,1]','test_hsv_48_distinct_weighted_bins; test_background_outside_mask_has_no_effect'),
    ('B03','12×4 bins, 48 chiều mỗi vùng','12','region_descriptor','histogram2d bins=(12,4)','test_hsv_48_distinct_weighted_bins; 2874 HS histogram tính lại'),
    ('B04','L1 histogram H–S','12','region_descriptor','hs/hs.sum()','5748 histogram HS/Hue tính lại từ pixel, max error=0'),
    ('B05','CIE-Lab, bốn loại thống kê trên L*,a*,b*','12','region_descriptor','3×(mean,std,skew,kurt)=12','test_float_lab_conversion_matches_independent_srgb_xyz_equations; 18 region oracles'),
    ('B06','Hue10 L1 + circular mean/std, 12 mỗi vùng','13','region_descriptor','10+1+1; histogram Hue/sum','test_hue_histogram_10_bins_with_known_rgb_primaries; toàn kho raw'),
    ('B07','Phép chiếu góc φ=2πH/180','13','hue_statistics','angles=H*(2*pi/180)','test_circular_projection_mean_std_known_two_angles; wrap test'),
    ('B08','Hai thống kê vòng trong [0,1] trước Z-score','13,17','hue_statistics','mean/(2π); std clipped ≤1','18 region scalar oracles; raw matrix range; undefined-resultant test'),
    ('B09','Chỉ tính pixel trong mask, không cộng nền ngoài mask','11–12','region_descriptor','pixels=image[mask>0]','test_background_outside_mask_has_no_effect; 5748 histogram từ raw masks'),
    ('B10','Bước cuối Z-score trên đủ 144 chiều','13','fit_standardizer','profile=all144, indices=arange(144)','b_ab_verification.json: toàn ma trận Z khớp oracle≤7.11e-15'),
    ('B11','Query dùng lại tham số kho','13,17','transform','(q−saved_mean)/saved_std','query_worker_verification.json; test_b_zscore_saved_statistics_and_constant_query')]:
    add('B',key,req,page,code(C,fn),formula,ev,EXACT,'Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này.')

DECISIONS=[
('D01','Cạnh bin HSV/Hue và số uint8','12–13','H [0,180), S [0,256), cạnh đều 15/64/18','48-bin và Hue10 analytic tests'),
('D02','Chuyển CIE-Lab và dtype','12','OpenCV BGR float32/255 → Lab; moment float64','sRGB/XYZ/Lab analytic check, tolerance0.3; source conversion'),
('D03','Mean/std/skew quần thể không bias','12','mean; sqrt(m2); m3/m2^(3/2)','black/white and asymmetric L* oracles'),
('D04','Pearson kurtosis, không trừ 3','12','m4/m2²','asymmetric oracle kurtosis7/3 khác excess−2/3'),
('D05','Kênh hằng/gần hằng','12','std<1e-12 → std/skew/kurt=0 kèm warning','constant a*,b* trong black/white tests'),
('D06','Circular mean atan2/modulo và scale','13','atan2(S,C) mod2π /2π','two-angle and wrap analytic oracles'),
('D07','Circular std, scale/floor/clip','13','min(sqrt(−2ln(max(R,1e-12)))/(2π),1)','two-angle and R≈0 oracles'),
('D08','Resultant gần 0','13','R<1e-8 → circular_mean=0 + warning','test_undefined_resultant_convention_is_flagged'),
('D09','Raw skin class1, hair class17, không gộp nose10','11–13','make_masks(labels==1/17)','batch_uniface.py::make_masks; installed uniface/draw.py label list'),
('D10','Không erosion cho B144 v1','11–13','full_color nhận tuple(raw skin,raw hair)','2876 raw mask hashes/receipts; histogram recomputation exact'),
('D11','Không lọc theo S, chỉ cảnh báo','12–13','Không xóa pixel S<10; warning fraction>0.5','black/white test S=0 vẫn được tính; source_listing.txt'),
('D12','Vùng dưới100 pixel không có B, không zero-fill','12','extract_color.vector=None','test_missing_region_no_zero_fill; query_worker_missing_b/b_status.json'),
('D13','Serialization Skin72/Hair72, HS/Lab/Hue','11–13','[HS48,Lab12,Hue10,mean,std]×2','weighted bin oracle; 18 region full vector oracles'),
('D15','B ddof0, std<1e-8→divisor1, giữ144 chiều','13,17','(x−mu)/where(sigma<1e-8,1,sigma)','test_b_zscore_saved_statistics_and_constant_query; all gallery stats'),
('D16','Fit toàn bộ 1437 B hợp lệ, không tự loại warning','13,17','manifest1438, feature_rows/fit_manifest1437','manifest/status/count/mapping/hash checks; warning1169'),
('D17','B self-match theo image_id, tie filename','17–18','lexsort(filename,distance); exclude ID','50 Top-5 rows recomputed by scalar fsum; existing color tests')]
for key,req,page,formula,ev in DECISIONS:
    source=code('features/B_color/src/batch_uniface.py','make_masks') if key in ('D09','D10') else code(C,'region_descriptor')
    if key in ('D15','D16'):source=code(F,'run')+'; '+code(C,'fit_standardizer')
    if key=='D17':source=code(BS,'rank')
    add('B','B-'+key,req,page,source,formula,ev,DETAIL,'Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF.')
add('B','B12','Mô-men phải được chuẩn hóa theo kho trước khi ghép','13 §2.3.3;17 §2.5.2',code(C,'extract_color')+'; '+code(F,'run'),
    'Đang raw descriptor → concat144 → fit/transform all144 một lần','test_no_preconcat_moment_standardization_in_current_descriptor; source run(); b_stage_order_illustration.json',DEV,
    'D14 mâu thuẫn thứ tự được PDF nói rõ; chuẩn bị stage riêng trong phiên bản mới, chưa tự thêm ở audit.')
add('B','B13','Công thức cụ thể cho bước chuẩn hóa mô-men trước ghép','13,17',code(F,'run'),'PDF không chốt toán tử/epsilon/fallback của stage trước ghép','Đọc nguyên văn PDF; D14 không giải quyết đủ thứ tự',OPEN,'Chốt toán tử tuân thủ PDF; không tự coi hai lần Z-score là định nghĩa đầy đủ duy nhất.')
add('B','B14','Vùng mask phù hợp ngữ nghĩa da mặt/tóc của đối tượng','11–13',code(F,'verified_input'),'Class1/17 không bảo đảm ngữ nghĩa prediction từng pixel','dataset_mask_review_page1/2.png; visual_review_findings.csv',OPEN,'Không có GT độc lập; ghi hand/secondary-face/covering, không đổi ROI sang skin+nose hoặc clean.')
add('B','B15','1438 input,1437 valid,1 missing HF00209','11,16; yêu cầu nhiệm vụ',code(F,'run'),'manifest1438; compact raw/z1437×144; missing row918','b_ab_verification.json; missing_features.csv',EXACT)
add('B','B16','Mapping feature_row_index/a_row_index và stats provenance','13,17',code(BS,'load_gallery'),'feature row→A row/ID; hash fit_manifest, schema và 9 integrity files','2876 masks/source hashes; full normalization and mapping checks',EXACT)
add('B','B17','Euclid đủ144 và kết quả tăng dần','13,17–18',code(BS,'rank'),'sqrt(sum_{j=1..144}(qj−xj)²)','50 saved rows; scalar Euclid max error3.56e-15',EXACT)
add('B','B18','Helper lịch sử moments_only không phải chuẩn hóa all144 theo PDF','13',code(C,'fit_standardizer'),'profile=moments_only chỉ scale24/144 chiều','run_color_experiment.py từ chối profile này; helper vẫn callable',DEV,'Chỉ nhánh nghiên cứu, không được gọi v1 bám báo cáo; giữ lịch sử, không xóa hay thay artifact.')
add('B','B19','Chất lượng segmentation/retrieval đã được đo với nhãn độc lập','11–13 (giá trị thông tin)',code(BS,'evaluate'),'Không có relevance/GT độc lập trong audit này','visual_review_findings.csv; danh sách nguồn nhãn chưa đầy đủ',OPEN,'Không báo accuracy/IoU/Dice hoặc lấy Top-5 làm căn cứ sửa công thức.')

DATA_SOURCE='D:/TuNam4/dataset_HF_CFD_final/metadata.csv; audit_tools/measure_dataset.py'
for key,req,page,formula,ev,status,action in [
('DS01','Ít nhất1000 ảnh và đúng1438 ảnh hiện hành','3–4','1438 PNG, metadata1438','dataset_verification.json',EXACT,'Giữ nguyên toàn bộ ảnh.'),
('DS02','Nguồn CFD và HF, ID/tên file và metadata riêng','4','CFD710 + HF728; unique IDs, hash/name mapping','dataset_verification.json; metadata.csv',EXACT,'Xác nhận nguồn được ghi trong catalog, không suy ra toàn bộ lịch sử thu thập.'),
('DS03','1135 người phân biệt và303 ảnh cảm xúc của cùng người','4','710 CFD rows có407 source-scoped IDs +303 extra;728 HF không có person_id','dataset_verification.json',OPEN,'Không giả định728 HF đều khác nhau hoặc không trùng CFD; emotion labels không có.'),
('DS04','Quy trình giữ ảnh nhãn nữ và lọc bằng detector','4–5','Metadata hiện không có nhãn giới/tuổi hoặc log lọc gốc đủ','metadata_fields; source_inventory; dataset source files',OPEN,'Cần provenance nhãn nguồn, không suy đoán từ ngoại hình.'),
('DS05','Một mặt duy nhất, không có mặt phụ','5','Detector num_faces5 báo1 trên1438; hình thật có mặt phụ','visual_review_findings.csv: HF00333 và HF00561',DEV,'Không xóa ảnh; gắn cờ lỗi tiêu chí và chuẩn bị dataset phiên bản kiểm duyệt riêng nếu được giao.'),
('DS06','Chính diện, yaw/pitch nhỏ hơn5°','5','Model-transform Euler chỉ proxy, chưa hiệu chuẩn','dataset_measurements.csv',OPEN,'Không nhận proxy làm GT; cần pose/annotation protocol độc lập.'),
('DS07','Đường nối hai mắt nằm ngang','5–6','Roll centroid median−0.020817°, range−2.948612..2.651157°','dataset_verification.json; iris_roll đo riêng',OPEN,'Ảnh gần ngang theo model; PDF không cho tolerance cho khái niệm nằm ngang cố định.'),
('DS08','Tâm khuôn mặt căn giữa, tỉ lệ tương đồng','3–5','Eye-center x median50.0214%, range48.4284..51.5375%','dataset_verification.json',OPEN,'Proxy tâm mắt không thay GT tâm mặt; cần tolerance quy định trước.'),
('DS09','Mặt chiếm70–90%, median78.6% chiều cao','5','Mesh-height proxy median78.5641%, range69.5652..89.4985%','dataset_verification.json',OPEN,'Mesh bbox không phải face detector bbox/đỉnh đầu-cằm đã hiệu chuẩn; không khẳng định chính xác78.6%.'),
('DS10','Mắt, mũi, miệng không bị che bởi tay/phụ kiện/tóc','5','HF00722: ngón tay che vùng miệng','dataset_mask_review_page2.png row2',DEV,'Giữ nguyên ảnh và nhãn; lưu bằng chứng, không tối ưu mask/ranking để che vấn đề.'),
('DS11','Tất cả cùng256×256,1:1','4–6','1438/1438 PNG IHDR width=height=256','dataset_measurements.csv; đọc trực tiếp IHDR và OpenCV',EXACT,'Giữ nguyên.'),
('DS12','PNG, RGB8','4–6','IHDR bit_depth8, color_type2; decoded uint8 H×W×3','dataset_verification.json',EXACT,'OpenCV đọc BGR là quy ước API, không phải ảnh nguồn sai RGB.'),
('DS13','PNG “chất lượng95”, cùng mức nén','4,6','PNG lossless; số95 không xác định duy nhất mức nén/encoder','Đọc PDF/IHDR; không có encoder logs được xác nhận',OPEN,'Không thay bằng JPEG hoặc bịa thông số95; cần provenance encode.'),
('DS14','Độ tuổi18–60 và đa dạng tuổi/sắc tộc/tóc/ánh sáng','5–6','Catalog thiếu tuổi và nhãn phân bố đủ để kiểm tra định lượng','dataset metadata fields',OPEN,'Không suy luận thuộc tính nhân khẩu từ ảnh.'),
('DS15','Tiền xử lý loại0 hoặc nhiều hơn1 mặt','5','Pipeline trích A dùng num_faces1, không đủ chứng minh bộ lọc gốc; mặt phụ còn tồn tại','geometry_features.py; visual review; source preprocessing chưa đủ',OPEN,'Tiêu chí ảnh đã vi phạm ở DS05; quy trình lọc gốc riêng chưa xác minh.'),
('DS16','478→68 trong bước căn chỉnh gốc','5','Có extractor hiện tại, thiếu log preprocessing gốc theo từng ảnh','source_listing.txt; dataset files',OPEN,'Không lấy inference mới làm bằng chứng lịch sử.'),
('DS17','IPD median29.45%, min27.23%, max32.61% chiều rộng','5','Centroid: median30.66188%, range28.28742..33.56603%; iris:30.74760%,27.58422..33.32610%','dataset_verification.json; 9 centroid IPD ngoài khoảng PDF',OPEN,'Chênh lệch đo cần điều tra định nghĩa tâm mắt/provenance; chưa kết luận từ model estimate là GT.'),
('DS18','Tâm hai mắt ở40% chiều cao','5','Centroid y median39.78226%, range37.01634..41.80630%; iris median39.25197%','dataset_verification.json',OPEN,'Chưa có tolerance/định nghĩa chuẩn đủ; không chứng nhận40% mọi ảnh.'),
('DS19','Crop vuông đỉnh đầu→cằm, một phần tóc/vai; bicubic','5','Ảnh output không suy ra chắc interpolation/crop history','Không thấy pipeline warpAffine/resize bicubic preprocessing nguồn được truy vết',OPEN,'Cần source/log gốc, không resize hay crop lại trong audit.'),
('DS20','Metadata trong CSDL gồm ID/path/vị trí hai mắt','4–5,16','CSV hiện có ID/path nhưng không có eye x/y đầy đủ; không xác minh DB ngoài workspace','metadata.csv fields; repo code/storage search',OPEN,'Nêu thiếu bằng chứng CSDL/eye-coordinate persistence, không tự dựng DB.'),
('DS21','Tính toàn vẹn, không trùng byte/mồ côi','4 (catalog), yêu cầu audit','1438 SHA khớp,0 duplicate byte, tập file=metadata','dataset_verification.json; protected_before.json',EXACT,'Không đồng nhất0 duplicate byte với0 duplicate identity.')]:
    add('DATASET',key,req,page,DATA_SOURCE,formula,ev,status,action)

for key,req,page,fn,formula,ev,status,action in [
('AB01','Euclid A150 và B144 riêng','17','rankings','norm(A−qa), norm(B−qb), không concat trước L2','39 audit tests; verify_b_ab scalar oracle',EXACT,'Giữ metric; EXACT có điều kiện trên vector phiên bản hiện tại.'),
('AB02','Liên kết bằng ID/index, không ghép hàng mặc định','16–17; yêu cầu truy vấn trước','join_galleries','image_id + kiểm tra a_row_index; lấy B feature_row_index','test_identity_join_with_missing_row_and_permuted_indices; old AB tests',EXACT,'Giữ nguyên vì B có1437 hàng.'),
('AB03','Trung vị của mỗi bộ trên cùng tập cặp đại diện','17','calibrate','mA=median dA(i,j); mB=median dB(i,j), cùng20000 cặp','20000 pair IDs tái lập bằng toán triangular-index độc lập; scalar distances',EXACT,'Chứng nhận cùng tập cặp và median; tính đại diện thống kê xem AB05.'),
('AB04','Median normalization đúng d/(m+ε)','17','rankings','da/(median_a+epsilon); db/(median_b+epsilon)','test_euclidean_not_squared_and_weighted_median_formula',EXACT,'Không cộng khoảng cách thô; giữ công thức.'),
('AB05','Mẫu20000 cặp uniform, seed42, đại diện cho kho','17 không chốt sampling','representative_pairs','sample không hoàn lại từ sorted unordered i<j','20k IDs tái lập; CFD/CFD4880,CFD/HF10073,HF/HF5047',OPEN,'Thuật toán hiện tại tái lập, chưa có phê duyệt riêng seed/count hay chứng minh đại diện cho mọi nhóm.'),
('AB06','Giá trị ε median','17 không chốt trị số','calibrate','epsilon=1e-8, đã lưu rõ','median_params.json; independent weighted formula test',OPEN,'Đây là quy ước hiện có, không nhận là trị số do PDF quy định; không tự đổi trong audit.'),
('AB07','Tổng trọng số không âm và bằng1','17','validate_weights','wa,wb≥0, finite; abs(sum−1)≤1e-12','old AB weight tests; scalar fusion oracle',EXACT,'Công khai tolerance float1e-12; không tối ưu theo Top-5.'),
('AB08','Thử nghiệm hai bộ A=.5,B=.5','17; yêu cầu phiên trước','main','D=.5*normalizedA+.5*normalizedB','results.json; verify_b_ab; yêu cầu người dùng trước',DETAIL,'Giữ nhãn experimental, không gọi fusion chính thức bốn bộ.'),
('AB09','Lưu/tái sử dụng median và nhận ra calibration sai phiên bản','17; yêu cầu phiên trước','calibrate','fingerprint vectors/stats/metadata + hash pairCSV + saved median','old AB stale-cache/tamper tests; current fingerprints verified',EXACT,'Sửa A/B phải tạo calibration phiên bản mới; không tái dùng median cũ.'),
('AB10','Lưu dA,dB,normalizedA,normalizedB và D, xếp tăng dần','17–18','rankings','lexsort(filename,score); result fields đủ','3 ranking modes tái lập trên query00001; CSV/JSON',EXACT,'Đúng số học cũ không chứng nhận A/B toàn pipeline tuân thủ.'),
('AB11','Self-match của ảnh truy vấn','18 không chốt thuật toán','identify_query','SHA256→IDs, loại ID; PNG mã hóa lại không tự nhận trùng','existing AB tests; query statuses; new_query original byte hash khác',OPEN,'Quy ước đã công khai, không phải yêu cầu danh tính pixel/person trong PDF; không sửa heuristic.'),
('AB12','Thiếu B không zero-fill và xử lý rõ','17; yêu cầu phiên trước','query_vectors','common1437; HF00209 query chỉ A-only, B/AB rỗng','missing query + missing worker no vector; all candidate IDs',EXACT,'Giữ trạng thái thiếu, không tự đổi trọng số.'),
('AB13','Query dùng đúng extractor/stats, tương thích hai venv','17; yêu cầu phiên trước','run_worker','.venv311 A; .venv-uniface B; giao tiếp .npy','query_worker_verification.json: query A/B tái trích thật, exact legacy transform',EXACT,'Không cài thư viện hoặc sửa pipeline.'),
('AB14','Calibration/ranking phải thuộc phiên bản A đúng công thức','17','load_gallery','Hiện fingerprint trỏ A std_safe cũ','legacy_dependency_register.json; A12 confirmed',DEV,'Sai lệch kế thừa A12, không đếm là nguyên nhân mới; đánh dấu mọi phụ thuộc trong audit register.'),
('AB15','Fusion chính thức bốn bộ A/B/C1/C2','16–18','main','Chỉ có A+B experimental; C1/C2 chưa có implementation','source_inventory.json; EXPERIMENT string',OPEN,'Ngoài phạm vi triển khai: không tạo hoặc sửa C1/C2 trong nhiệm vụ này.')]:
    add('AB',key,req,page,code(AB,fn),formula,ev,status,action)
