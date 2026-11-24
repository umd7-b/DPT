"""Compose an editable, paginated Vietnamese report from audited real artifacts."""
from pathlib import Path
import csv,json,math,sys,shutil
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from features.B_color.src.audit_color_inputs import read_csv

OUT=ROOT/'docs/reports';BUILD=OUT/'_build';FIG=OUT/'figures'
f=json.loads((BUILD/'facts.json').read_text(encoding='utf-8')); g=f['sample_geometry'];q=g['quantities']
A=ROOT/'outputs/A_geometry/features'; B=ROOT/'outputs/B_color/color_features_full_v1'
plt.rcParams.update({'font.family':'Arial','font.size':10,'savefig.dpi':180})
def save(name):plt.savefig(FIG/name,bbox_inches='tight',facecolor='white');plt.close()
def grid(name,query,results):
    fig,axs=plt.subplots(2,3,figsize=(9,6.4))
    for i,(ax,n) in enumerate(zip(axs.flat,[query]+[r['image_name'] for r in results])):
        im=cv2.cvtColor(cv2.imread(str(Path('D:/TuNam4/dataset_HF_CFD_final/images')/n)),cv2.COLOR_BGR2RGB)
        ax.imshow(im);ax.axis('off')
        label='QUERY' if i==0 else f'TOP {i} · d={float(results[i-1]["distance"]):.6f}'
        ax.set_title(label+'\n'+n,fontsize=9)
    fig.tight_layout();save(name)
agrid=f['saved_A_top5']['cfd_final_00144.png']['results']
stored=read_csv(B/'retrieval/top5.csv');bgrid=[r for r in stored if r['query_name']=='cfd_final_00537.png']
grid('saved_A_grid.png','cfd_final_00144.png',agrid);grid('saved_B_grid.png','cfd_final_00537.png',bgrid)
shutil.copyfile(f['saved_A_top5']['cfd_final_00144.png']['image_path'],FIG/'original_A_top5.png')
shutil.copyfile(B/'retrieval/queries/cfd_final_00537_top5.png',FIG/'original_B_top5.png')
fig,ax=plt.subplots(figsize=(11,1.8));ax.axis('off')
for i,text in enumerate(['Ảnh\nđầu vào','Tiền xử lý\n/ căn chỉnh','Trích xuất\nA hoặc B','Chuẩn hóa\ntheo kho','Khoảng cách\nEuclid','Trả về\nTop-5']):
    x=i/6+.008
    ax.text(x+.067,.5,text,ha='center',va='center',fontsize=10,bbox=dict(boxstyle='round,pad=.65',fc='#edf3f6',ec='#235d78'))
    if i<5:ax.annotate('',xy=(x+.175,.5),xytext=(x+.14,.5),arrowprops=dict(arrowstyle='->',color='#235d78'))
ax.set_xlim(0,1);save('pipeline.png')
# Additional report-only comparison: derive B ranking for the saved A query.
bm=read_csv(B/'feature_rows.csv');z=np.load(B/'features_B_normalized.npy'); names=[r['image_name'] for r in bm]
qi=names.index('cfd_final_00144.png');d=np.linalg.norm(z-z[qi],axis=1);d[qi]=np.inf
inds=np.lexsort((np.array(names),d))[:5]
b_same=[dict(rank=i,image_name=names[j],distance=float(d[j])) for i,j in enumerate(inds,1)]
with (BUILD/'report_only_B_same_query.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    w=csv.DictWriter(stream,fieldnames=['rank','image_name','distance']);w.writeheader();w.writerows(b_same)
grid('derived_B_same_query.png','cfd_final_00144.png',b_same)
source=cv2.imread(str(B/'review/raw_mask_examples.png'))
cv2.imwrite(str(FIG/'mask_caveats.png'),np.vstack([source[:292],source[584:876]]))

pages=[]
def add(title,body):pages.append((title,body.strip()))
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in rows)
def pic(file,caption):return f'![{caption}](figures/{file})\n\n*{caption}*'
def eq(text):return '\n$$\n'+text+'\n$$\n'
def num(x,n=6):return f'{x:.{n}f}'

add('Bìa', '''# PHÂN TÍCH KỸ THUẬT
## BỘ ĐẶC TRƯNG A & B

**PORTRAIT RETRIEVAL**

Geometry A150 · Color B144

Báo cáo nghiên cứu và kiểm toán triển khai

**Dữ liệu đã kiểm tra:** 1.438 ảnh chân dung, 256×256, CFD và HF.

**Artifact:** A150 — 1.438 vector; B144 — 1.437 vector hợp lệ.

**Phiên bản màu:** B144_raw_v1.0.0, quyết định D01–D17 đã được chấp thuận.

Ngày lập: **22/11/2026**

Nguồn học thuật duy nhất: báo cáo nhóm `csdldpt.pdf`.

Phạm vi: giải thích công thức, dữ liệu và code đang chạy; không sửa A/B, không tạo lại kho và không triển khai C1/C2.

Tài liệu phân biệt rõ yêu cầu trong báo cáo gốc, quy ước hiện thực, quyết định được chấp thuận và những điểm chưa đủ bằng chứng. Kết quả kiểm thử chương trình không được diễn giải thành độ chính xác nhận diện hoặc phân đoạn.
''')
add('Mục lục', '''# MỤC LỤC
'''+table(['Nội dung','Trang'],[
('Chương 1. Tổng quan hệ thống và dữ liệu','3–4'),('Chương 2. Bộ A: landmarks, chuẩn hóa và A1','5–6'),('Chương 2. 14 đặc trưng A2, phân tích từng thành phần','7–13'),('Chương 3. Z-score Bộ A: công thức và dữ liệu','14–15'),('Chương 4. Bộ B: parsing, HS, Lab và Hue vòng','16–19'),('Chương 4. Bảng index đầy đủ B144','20–21'),('Chương 5. Z-score Bộ B','22'),('Chương 6. Euclid, Top-5 và kết quả thật','23–25'),('Chương 7. Kết quả, giới hạn và ngoại lệ','26–27'),('Nguồn, kiểm chứng và cách tái lập','28')])+'''

## Quy ước đọc tài liệu

**[PDF]**: nội dung được báo cáo nhóm quy định rõ; dẫn trang là **trang PDF đếm từ 1**, không phải số trang trong mục lục gốc.

**[CODE]**: biểu thức/lựa chọn được đọc trực tiếp từ source hiện tại. Khi PDF chưa chốt landmarks, epsilon hoặc serialization, tài liệu gọi đó là quy ước hiện thực.

**[APPROVED]**: D01–D17 được người dùng chấp thuận cho B v1, không mặc nhiên trở thành công thức nguyên văn của PDF.

**[AUDIT]**: kết quả đo trực tiếp từ artifact, hash hoặc phép kiểm tra độc lập trong lần lập báo cáo này.

**[DEVIATION]**: khác biệt cụ thể giữa code và quy định rõ trong PDF; không tự sửa trong nhiệm vụ viết báo cáo.

**[UNVERIFIED]**: chưa đủ bằng chứng để xác nhận. Không điền số liệu suy đoán.

Các phép tính minh họa được ghi rõ là ví dụ giải tích hoặc được tính từ `cfd_final_00001.png`. Hình chân dung/mask đều lấy từ dataset hoặc artifact thật, không dùng ảnh sinh tạo.
''')
add('Chương 1 — Tổng quan', '''# CHƯƠNG 1. TỔNG QUAN HỆ THỐNG

## 1.1. Từ ảnh đến biểu diễn đặc trưng

Hệ thống biểu diễn mỗi ảnh bằng một dãy số có ý nghĩa và thứ tự cố định — **feature vector**. Thay vì so sánh trực tiếp toàn bộ pixel, truy hồi tính khoảng cách giữa các vector của query và ảnh kho. Mỗi chiều đại diện một tọa độ, tỉ lệ hoặc thống kê màu; một vector chỉ có thể so sánh đúng với vector dùng cùng định nghĩa và cùng tham số chuẩn hóa.

**A150** mô tả hình học: vị trí tương đối của 68 điểm mốc, tỉ lệ và góc. **B144** mô tả phân bố màu của hai ROI da/tóc. Hai ảnh có hình học gần nhau vẫn có thể khác màu; hai ảnh cùng màu chưa chắc giống đường nét. Hai bộ cung cấp thông tin bổ sung chứ không chứng minh danh tính.

'''+pic('pipeline.png','Hình 1. Pipeline khái niệm; nhánh A và B có extractor và thống kê riêng.')+'''

## 1.2. Thiết kế 854 chiều và phạm vi hiện có

'''+table(['Bộ','Biểu diễn','Số chiều','Tình trạng'],[('A','Geometry: 136 tọa độ + 14 tỉ lệ/góc',150,'Đã có artifact'),('B','Skin72 + Hair72',144,'Đã có v1 chính thức'),('C1','LBP theo 4 vùng',236,'Chưa triển khai'),('C2','Root-HOG',324,'Chưa triển khai')])+'''

[PDF: §2.1, tr.7; §2.5.1, tr.16] Tổng thiết kế là 854 chiều. Báo cáo này kiểm tra hai bộ A/B đã có; không coi tổng 854 là một ma trận đã triển khai. Luồng A+B fusion và bốn bộ chưa hoàn thiện.

Khi tính riêng B, khoảng cách Euclid được áp dụng trên B144 đã Z-score. Chuẩn hóa khoảng cách theo median ở §2.5 dành cho kết hợp các bộ; không âm thầm cộng các khoảng cách thô hoặc trộn tham số A và B.
''')
add('Chương 1 — Dữ liệu và tiền xử lý', '''# 1.3. DỮ LIỆU VÀ TIỀN XỬ LÝ

[AUDIT] Đọc trực tiếp 1.438 file PNG trong dataset: tất cả có kích thước `(256,256,3)`. Metadata và prefix có **710 CFD + 728 HF**. README dataset nói ảnh được sao chép giữ nguyên byte và có ảnh HF cần duyệt; đây không phải bằng chứng mọi ảnh đều thỏa điều kiện một người/chính diện.

'''+table(['Bước được PDF mô tả','Bằng chứng trong repo hiện tại'],[
('Phát hiện khuôn mặt, loại ảnh có 0 hoặc >1 mặt','A giới hạn num_faces=1; chỉ kiểm tra số output. Không chứng minh đã sàng lọc đủ ảnh nhiều người.'),
('478 → 68 landmarks','Có mapping và code đang dùng; kiểm tra một ảnh thật tái tạo đúng vector đã lưu.'),
('Xoay đường mắt nằm ngang, scale/crop về khuôn chuẩn','Không thấy quy trình warp/crop này trong module A/shared/retrieval hiện tại; code đọc ảnh đã chuẩn hóa.'),
('Bicubic 256×256','Toàn bộ kích thước được xác minh; INTER_CUBIC trong map_68_landmarks chỉ phóng hình minh họa, không chứng minh lịch sử crop.'),
('Vị trí/scale mắt theo tiêu chí báo cáo','Metadata có eye_distance nhưng không có đầy đủ tọa độ mắt, ma trận biến đổi hoặc log alignment.')])+'''

[PDF: §1.2–1.3, tr.5] Báo cáo mô tả khoảng cách mắt trung vị 29,45% chiều rộng và tâm mắt ở 40% chiều cao. [AUDIT] Metadata A có trung vị d=**78,494411 px** (30,6619% của 256), min **72,415794**, max **85,929054**. Đây là khoảng cách hai tâm tính trung bình 6 landmarks/mắt của code; không nhất thiết là cùng thước đo/công đoạn của số liệu alignment trong PDF. Chưa đủ bằng chứng để xác nhận các con số lịch sử hoặc suy ra chính xác pipeline cũ.

Không suy đoán tuổi, giới tính hoặc nguồn gốc sinh trắc từ ảnh. Các mô tả tập dữ liệu trong PDF được ghi là thông tin của báo cáo, không thay cho nhãn đã được kiểm chứng độc lập.

## 1.4. Nguyên tắc kiểm toán

Đọc source và artifact trước khi viết công thức. Đối chiếu tên ảnh/thứ tự, shape, dtype, tính hữu hạn và thống kê thực. Giữ nguyên cả ảnh bất thường, warning và hàng thiếu B. Chỉ tạo tài liệu/hình dẫn xuất dưới `docs/reports/`; không chạy main ghi lại vector A/B hoặc mask nguồn.
''')
mapping=g['mapping']; group_rows=[]
for lo,hi,label in [(0,17,'Hàm'),(17,22,'Lông mày trái'),(22,27,'Lông mày phải'),(27,36,'Mũi'),(36,42,'Mắt trái'),(42,48,'Mắt phải'),(48,68,'Miệng')]:group_rows.append((label,f'{lo}–{hi-1}',', '.join(map(str,mapping[lo:hi]))))
add('Chương 2 — Landmarks', '''# CHƯƠNG 2. A150 — GEOMETRY

## 2.1. MediaPipe và ánh xạ 478 → 68

[PDF: §2.2.2, tr.8] Dùng 478 landmarks rồi ánh xạ về 68 điểm. [CODE] `geometry_features.detect_landmarks` đọc BGR, đổi RGB/SRGB, chạy `FaceLandmarker` chế độ IMAGE với model `.task` có sẵn và num_faces=1. Tọa độ x,y chuẩn hóa của model nhân w,h thành pixel float32; z không được đưa vào A150.

'''+pic('landmarks_68.png','Hình 2. 68 landmarks thật trên cfd_final_00001.png; chỉ số code bắt đầu từ 0.')+'''

Mapping là danh sách INDICES chọn trực tiếp các nút MediaPipe, không phải một lần chạy detector 68 điểm khác. PDF không liệt kê đủ 68 ID; danh sách này là quy ước code. Thứ tự nhóm: hàm → mày trái → mày phải → mũi → mắt trái → mắt phải → miệng. Tên trái/phải theo code; không suy ra mọi quy ước trái/phải giải phẫu đã được tài liệu gốc định nghĩa.

Ảnh đọc lỗi → FileNotFoundError; không có đúng một output → RuntimeError. Batch bắt exception, ghi failed_images và tiếp tục. Artifact hiện có 0 hàng lỗi. Do cap num_faces=1, len(output)==1 không chứng minh ảnh chỉ có một người.
''')
c=g['center']; p=g['points'][0]; pn=g['normalized_points'][0]
add('Chương 2 — Chuẩn hóa và A1', '''# 2.2. CHUẨN HÓA TỌA ĐỘ VÀ A1

[PDF: §2.2.2–2.2.3, tr.9] Công thức chuẩn hóa điểm:
'''+eq(r"p'_i=\frac{p_i-c}{d},\qquad c=\frac{e_L+e_R}{2},\quad d=\|e_L-e_R\|_2")+'''
[CODE] eL là mean p36…p41, eR là mean p42…p47. Trừ c đưa tâm mắt về gốc; chia d đặt khoảng cách hai tâm mắt thành 1. Lựa chọn trung bình 6 nút/mắt là quy ước hiện thực của `normalize_landmarks`, không phải danh sách điểm được PDF viết đầy đủ. d<1e-6 gây lỗi thay vì tạo vector giả.

## Ví dụ từ tọa độ thật

'''+table(['Đại lượng','Giá trị pixel hoặc chuẩn hóa'],[
('eL',str(tuple(round(x,6) for x in g['eye_left']))),('eR',str(tuple(round(x,6) for x in g['eye_right']))),('c',str(tuple(round(x,6) for x in c))),('d',num(g['eye_distance'])+' px'),('p0',str(tuple(round(x,6) for x in p))),('p′0',str(tuple(round(x,6) for x in pn)))])+f'''

`({p[0]:.6f}−{c[0]:.6f})/{g['eye_distance']:.6f} ≈ {pn[0]:.6f}`; tọa độ y tính tương tự. Ví dụ là `cfd_final_00001.png`. Tái trích một ảnh bằng model/code hiện tại khớp **đúng từng phần tử A150 đã lưu**. Sai số tính A2 độc lập bằng float64 tối đa {g['independent_A2_max_error']:.3e}, phù hợp khác biệt độ chính xác float32.

## 2.3. A1 và vector A150

68×2=136 tọa độ: `[x′0,y′0,x′1,y′1,…,x′67,y′67]`. Chỉ số 2i là x′i, 2i+1 là y′i. A150 nối **A1[0:136] và A2[136:150]**, float32. Không đưa eye_distance thành chiều thứ 151; nó được lưu riêng trong metadata.

Chuẩn hóa này bất biến tịnh tiến và scale dương trong mô hình toán học. Nó không tự loại xoay, phối cảnh, biểu cảm hoặc sai landmarks; d nhỏ khuếch đại nhiễu. Chỉ số (x,y) và mapping phải đồng nhất cho cả kho/query.
''')

features=[
('Rộng gò má / cao mặt','2,14,21,22,8',r'\frac{D(p_2,p_{14})}{h+\epsilon}',f"{q['wf']:.6f}/({q['h']:.6f}+1e-8)",'Tỉ lệ bề ngang so với chiều cao giúp phân biệt mặt rộng với mặt dài.','Code dùng p2–p14 làm đại diện bề ngang; h từ trung điểm mày đến cằm, không phải một phép đo gò má/đỉnh trán được PDF quy định đủ. Góc chụp ảnh hưởng cả hai độ dài.'),
('Khoảng cách hai mắt / cao mặt','36…47,21,22,8',r'\frac{d}{h+\epsilon}',f"{q['d']:.6f}/({q['h']:.6f}+1e-8)",'Mô tả độ tách hai tâm mắt tương đối với trục dọc mặt.','Tâm mắt là trung bình 6 điểm mỗi mắt. Nhắm mắt, nheo mắt hoặc mày/cằm sai làm thay đổi tỉ lệ; không phải khoảng cách đồng tử đo trực tiếp.'),
('Bề ngang mắt trái / khoảng cách hai mắt','36,39 và 36…47',r'\frac{D(p_{36},p_{39})}{d+\epsilon}',f"{q['wl']:.6f}/({q['d']:.6f}+1e-8)",'Chuẩn hóa chiều rộng mắt theo kích thước vùng giữa mặt, hỗ trợ đối sánh hình dạng mắt.','Đầu mút 36/39 do mapping quyết định. Tư thế nghiêng và che khuất làm bề ngang chiếu trên ảnh thay đổi; nhãn trái/phải theo code.'),
('Bề ngang mắt phải / khoảng cách hai mắt','42,45 và 36…47',r'\frac{D(p_{42},p_{45})}{d+\epsilon}',f"{q['wr']:.6f}/({q['d']:.6f}+1e-8)",'Bổ sung chiều rộng mắt bên còn lại và thông tin bất đối xứng quan sát được.','Chênh hai phía có thể do phối cảnh, che khuất hoặc sai điểm, không tự kết luận là bất đối xứng giải phẫu.'),
('Độ mở mi mắt trái','37,41,38,40,36,39',r'\frac{D(p_{37},p_{41})+D(p_{38},p_{40})}{2D(p_{36},p_{39})+\epsilon}',f"({q['vl1']:.6f}+{q['vl2']:.6f})/(2×{q['wl']:.6f}+1e-8)",'Hai khoảng dọc biểu diễn mức mở mi so với bề ngang mắt; phân biệt mắt mở lớn/hẹp.','PDF chỉ gọi tên độ mở mi. Công thức hai cặp dọc/chia bề ngang là quy ước code, nhạy mạnh với chớp mắt và nheo mắt.'),
('Độ mở mi mắt phải','43,47,44,46,42,45',r'\frac{D(p_{43},p_{47})+D(p_{44},p_{46})}{2D(p_{42},p_{45})+\epsilon}',f"({q['vr1']:.6f}+{q['vr2']:.6f})/(2×{q['wr']:.6f}+1e-8)",'Mô tả độ mở mắt còn lại và hỗ trợ so sánh hai bên.','Không thể coi khác biệt chớp mắt là khác danh tính. Bề ngang gần 0 hoặc sai landmark có thể làm tỉ lệ tăng bất thường.'),
('Rộng cánh mũi / khoảng cách hai mắt','31,35 và 36…47',r'\frac{D(p_{31},p_{35})}{d+\epsilon}',f"{q['wn']:.6f}/({q['d']:.6f}+1e-8)",'Biểu diễn bề ngang mũi tương đối với vùng giữa mặt.','Việc gán hai nút MediaPipe cho p31/p35 là xấp xỉ giải phẫu của mapping; phối cảnh hoặc tay che mũi làm sai khoảng cách.'),
('Rộng miệng / khoảng cách hai mắt','48,54 và 36…47',r'\frac{D(p_{48},p_{54})}{d+\epsilon}',f"{q['wm']:.6f}/({q['d']:.6f}+1e-8)",'Khoảng hai khóe miệng chuẩn hóa mô tả miệng rộng/nhỏ.','Nụ cười và biểu cảm làm khóe miệng dịch rõ; đây vừa là thông tin hình thái vừa nhạy với trạng thái ảnh.'),
('Độ mở môi / khoảng cách hai mắt','62,66 và 36…47',r'\frac{D(p_{62},p_{66})}{d+\epsilon}',f"{q['om']:.6f}/({q['d']:.6f}+1e-8)",'Phân biệt môi đóng, hé hoặc mở tương đối với kích thước mặt.','Dùng đúng cặp môi trong 62/66 của code. Biểu cảm và phát âm làm thay đổi lớn; số gần 0 không chứng minh môi đóng tuyệt đối khi landmark có nhiễu.'),
('Khoảng cách trung điểm mắt–mũi / khoảng cách hai mắt','36…47 và 30',r'\frac{D(c,p_{30})}{d+\epsilon}',f"{q['en']:.6f}/({q['d']:.6f}+1e-8)",'Mô tả vị trí mũi so với tâm hai mắt trong bố cục mặt.','Code dùng Euclid 2D, nên chịu cả lệch ngang lẫn dọc; không phải chỉ lấy chênh tọa độ y. Đầu mũi theo mapping là p30.'),
('Khoảng cách trung điểm mắt–khóe miệng / khoảng cách hai mắt','36…47,48,54',r'\frac{D(c,(p_{48}+p_{54})/2)}{d+\epsilon}',f"{q['em']:.6f}/({q['d']:.6f}+1e-8)",'Mô tả quan hệ bố cục nửa trên và nửa dưới mặt.','Code chọn trung điểm hai khóe miệng. PDF không chỉ rõ cách tổng hợp hai khóe; cười làm điểm giữa dịch chuyển.'),
('Khoảng cách chóp mũi–đáy cằm / cao mặt','30,8,21,22',r'\frac{D(p_{30},p_8)}{h+\epsilon}',f"{q['nc']:.6f}/({q['h']:.6f}+1e-8)",'Biểu diễn phần dưới mặt so với chiều cao mặt theo proxy đang dùng.','Cằm bị cắt, râu/phụ kiện hoặc landmark sai có thể làm thay đổi số đo. h là proxy mày–cằm, không phải một chiều cao giải phẫu được xác thực.'),
('Rộng xương hàm / cao mặt','4,12,21,22,8',r'\frac{D(p_4,p_{12})}{h+\epsilon}',f"{q['wj']:.6f}/({q['h']:.6f}+1e-8)",'Bổ sung độ rộng vùng hàm, hỗ trợ phân biệt mặt thuôn với hàm rộng.','Hai nút p4/p12 và phép chiếu 2D là lựa chọn code. Góc quay đầu và đường tóc/che khuất có thể làm landmark trôi.'),
('Góc xương hàm tại cằm','4,8,12',r'\theta=\frac{180}{\pi}\arccos\left(\operatorname{clip}\left(\frac{u\cdot v}{\|u\|\|v\|},-1,1\right)\right)',r'u=p4−p8; v=p12−p8; kết quả từ dot/norm thật','Góc ở cằm mô tả độ mở của hai cạnh hàm, giúp phân biệt cằm nhọn/tròn theo cấu trúc điểm đang dùng.','angle_degrees từ chối tích norm<1e-8; clip chống lỗi acos do làm tròn. Mapping điểm góc hàm chưa có chứng nhận giải phẫu độc lập.')]

u0=np.array(g['points'][4])-np.array(g['points'][8]);v0=np.array(g['points'][12])-np.array(g['points'][8])
last=list(features[-1]);last[3]=f"u=({u0[0]:.4f},{u0[1]:.4f}), v=({v0[0]:.4f},{v0[1]:.4f}); dot={np.dot(u0,v0):.4f}; norm(u)norm(v)={np.linalg.norm(u0)*np.linalg.norm(v0):.4f}; acos(dot/norms)×180/π";features[-1]=tuple(last)
for start in range(0,14,2):
    body=f'# 2.4. A2 — ĐẶC TRƯNG {start+1}–{start+2}\n\n'
    if start==0:body+='D(a,b)=norm Euclid 2D; h=D((p21+p22)/2,p8); d=norm(eL−eR); ε=1e-8 **trong code tỉ lệ**, đơn vị tương ứng tọa độ pixel. Đây không phải ε của phương trình Z-score trong PDF.\n\n'
    for i in range(start,start+2):
        name,points,formula,example,role,limit=features[i]
        body+=f'## {i+1}. {name}\n\n'
        body+=f'**Nguồn:** [PDF §2.2.3, tr.{9 if i<8 else 10}] quy định tên/ý nghĩa; [CODE] chốt điểm và biểu thức dưới đây. **Index A150:** {136+i}.\n\n'
        body+=f'**Landmarks:** p{points}. **Đơn vị/miền:** '+('độ, 0…180 khi hai cạnh không suy biến.' if i==13 else 'không thứ nguyên, không âm khi hợp lệ; không ép vào [0,1].')+'\n\n'
        body+=eq(formula)
        body+=f'**Ví dụ thật:** {example} → **{g["ratios"][i]:.6f}**'+('°' if i==13 else '')+'.\n\n'
        body+=f'**Hàm Python:** `geometry_features.calculate_ratios`'+(' gọi `angle_degrees`.' if i==13 else '; dùng distance/midpoint khi cần.')+'\n\n'
        body+=f'**Thông tin truy hồi:** {role}\n\n**Giới hạn:** {limit}\n\n'
    body+='Nguồn số liệu ví dụ: cfd_final_00001.png, tọa độ thật đã lưu trong _build/facts.json. Chữ số hiển thị được làm tròn; không gán công thức chi tiết do code bổ sung thành nguyên văn PDF.'
    add(f'Chương 2 — A2 {start+1}–{start+2}',body)

add('Chương 3 — Z-score A', '''# CHƯƠNG 3. Z-SCORE BỘ A

## 3.1. Công thức PDF và biểu thức code

[PDF §2.5.2, tr.17] Từng chiều j dùng thống kê kho:
'''+eq(r'z_j=\frac{x_j-\mu_j}{\sigma_j+\epsilon}')+'''
xj là giá trị đặc trưng; μj là trung bình trên các ảnh kho; σj là độ lệch chuẩn cùng chiều; ε ổn định mẫu số. PDF không chốt trị số ε. Fit theo cột của ma trận, không theo hàng từng ảnh: tọa độ và góc có đơn vị/thang đo khác nhau, nên chuẩn hóa riêng mỗi ảnh sẽ trộn các đại lượng không đồng nhất và làm query không còn cùng hệ tham chiếu với kho.

[CODE: normalize_features.main] Chuyển A raw sang float64, tính mean/std axis=0, NumPy ddof=0; **không cộng ε cho mọi chiều**:
'''+eq(r's_j=1\ (\sigma_j<10^{-8}),\quad s_j=\sigma_j\ (\sigma_j\geq10^{-8}),\qquad z_j=\frac{x_j-\mu_j}{s_j}')+'''
**[DEVIATION] Mẫu số s khác σ+ε.** Ngưỡng 1e-8 của code không được tự coi là ε cộng vào mẫu số. Khi σ>0, hai công thức thường gần nhau nếu ε nhỏ nhưng không bằng nhau; khi σ=0 và query khác mean, tác động có thể rất lớn. Không sửa thuật toán trong báo cáo này.

## 3.2. Ví dụ tính tay và NumPy

Cho cột minh họa x={1,3,5}: μ=3; variance=[4+0+4]/3=8/3; σ=1,632993162; code cho Z={−1,224744871;0;1,224744871}. NumPy std(ddof=0) và phép biến đổi cho cùng kết quả.

Nếu **giả định minh họa** ε=1e-8 trong công thức PDF (không phải giá trị PDF đã chốt), hai đầu là ±1,224744864. Cột {7,7,7}: training Z=0 ở cả hai cách; query x=9 thì code trả 2, còn σ+ε trả 2/ε. Training toàn số 0 không chứng minh hai chính sách giống nhau cho query.

Điều kiện dương của divisor, NaN/Inf và shape phải kiểm tra. Batch A hiện có lỗi thì ghi manifest lỗi; không tự thay vector không hợp lệ bằng zero.
''')
add('Chương 3 — Phân bố A', '''# 3.3. ARTIFACT A VÀ PHÂN BỐ THỰC

'''+pic('A_distributions.png','Hình 3. Ba chiều A thật trước/sau Z-score; mỗi cột histogram đếm số ảnh trong kho.')+'''

'''+table(['Kiểm tra A','Giá trị đo trực tiếp'],[
('Raw / normalized shape','(1438,150) / (1438,150)'),('Raw / normalized dtype','float32 / float32'),('Mean/std lưu','float64, 150 phần tử'),('Ảnh lỗi trong failed_images.csv','0'),('Chiều std<1e-8','0'),('Khoảng std raw',f'{f["A"]["raw_std_min"]:.6f} … {f["A"]["raw_std_max"]:.6f}'),('Sai số Z lưu so với phép tính float64',f'{f["A"]["max_z_float64_reconstruction_error"]:.3e}')])+'''

Normalized được cast float32 khi lưu. Vì vậy query tính float64 không nhất thiết bằng đúng từng bit với hàng normalized đã lưu, dù raw descriptor khớp. Audit kiểm tra **chính xác** phép tính float64 rồi cast float32 tạo ra artifact hiện có; sai số lượng tử không được coi là nhận diện sai.

`geometry_stats.npz` lưu mean và std_safe; query A dùng lại `(features.astype(float64)−mean)/std`. Không fit lại một ảnh. Mỗi đặc trưng vẫn giữ ngữ nghĩa khác nhau sau chuẩn hóa; Z-score không biến tỉ lệ/góc thành thước đo độc lập về thống kê hoặc loại bỏ biểu cảm.
''')
add('Chương 4 — Parsing và mask', '''# CHƯƠNG 4. B144 — COLOR

## 4.1. Face parsing và ROI

UniFace là thư viện hiện thực; BiSeNet ResNet18 phân lớp ngữ nghĩa pixel (semantic face parsing). [APPROVED D09] lấy class 1 làm Skin và class 17 làm Hair, tạo hai mask uint8 0/255. PDF §2.3 chỉ nêu hai vùng da/tóc, **không chỉ định UniFace/BiSeNet đích danh**.

Mask raw được chọn theo **D10**, giữ nguyên tập pixel dự đoán, không phải vì đã chứng minh tốt hơn erosion. Clean 3×3 và Skin+Nose là thí nghiệm lịch sử, không trộn vào vector chính thức. Skin=1 bỏ nose=10 và lớp tai/cổ theo schema; không tự thêm vào để hình nhìn đầy hơn.

'''+pic('raw_masks.png','Hình 4. Dự đoán thật: ảnh gốc, hai mask nhị phân và ROI màu; hàng dưới HF00209 có tóc raw rỗng.')+'''

Trước trích đặc trưng, code đối chiếu image hash, receipt, mask hash, số pixel, shape 256×256 và giá trị 0/255; kiểm tra hai vùng không chồng lấn. Trong kho đã có 2.876 raw mask kỹ thuật hợp lệ. Hash chỉ xác nhận tính toàn vẹn/provenance, không xác nhận pixel đúng ngữ nghĩa.

Model source: UniFace 4.3.0, parsing_resnet18.onnx, provider của lần parsing là CPUExecutionProvider. Nhiệm vụ lập báo cáo không chạy lại parsing hoặc tải model. ROI pixel lấy trực tiếp `image[mask>0]`; ảnh da/tóc nền đen chỉ dùng hiển thị, không làm đầu vào histogram.
''')
add('Chương 4 — B1', '''# 4.2. B1 — HSV 2D HISTOGRAM

Hue H mô tả hướng sắc màu, Saturation S mô tả độ bão hòa, Value V biểu diễn độ sáng trong HSV. [PDF §2.3.1, tr.12] chọn H và S để mô tả phổ màu/bão hòa, không lấy V trong histogram. Điều này giảm phụ thuộc trực tiếp V nhưng không tạo bất biến hoàn toàn với ánh sáng/cân bằng trắng.

12 Hue ×4 Saturation =48 chiều/vùng, 96 cho hai vùng. [D01] HSV uint8: H=0…179, S=0…255; cạnh H=0,15,…,180 và S=0,64,…,256. Với H,S hợp lệ: `h=floor(H/15)`, `s=floor(S/64)`, index trong HS48 là `4*h+s`. Ví dụ số học H=16,S=70 thuộc h=1,s=1,index=5; đây là ví dụ gán bin, không giả mạo pixel/nhãn thật.

'''+eq(r"h'_k=\frac{n_k}{\sum_i n_i},\qquad \sum_{k=0}^{47}h'_k=1")+pic('HS_histograms.png','Hình 5. H–S thực của da và tóc cfd_final_00001.png; colorbar là tần suất sau L1.')+f'''

Ở ảnh thật, bin da cực đại h=1,s=1 có khối lượng **{f['B_sample']['skin']['hs_peak']:.6f}**, tóc cực đại h=0,s=1 có khối lượng **{f['B_sample']['hair']['hs_peak']:.6f}**. Cả hai histogram tổng đúng 1 theo artifact.

Không cộng pixel nền đen ngoài mask; pixel đen thật trong mask vẫn được đếm (H=0,S=0 theo biểu diễn OpenCV). Không loại pixel S thấp theo cảm nhận: D11 chỉ ghi warning. Thay cạnh bin làm đổi phân bố dù tổng số chiều không đổi; biên bin là quy ước được chấp thuận, không phải tất cả đều được PDF ghi nguyên văn.
''')
labrows=[]
for region in ('skin','hair'):
    vals=f['B_sample'][region]['Lab12']
    for i,ch in enumerate(('L*','a*','b*')):labrows.append((region+' '+ch,*[f'{v:.5f}' for v in vals[4*i:4*i+4]]))
add('Chương 4 — B2', '''# 4.3. B2 — CIE-LAB COLOR MOMENTS

L* là độ sáng cảm nhận, a* là trục lục–đỏ, b* là trục lam–vàng. [PDF §2.3.2, tr.12] yêu cầu bốn thống kê trên ba kênh: 12/vùng, 24 cho hai vùng. [D02] BGR float32/255 → Lab float OpenCV, rồi mô-men float64; không dùng Lab uint8 có offset/scale như một phép thay thế ngầm.

[APPROVED D03–D05] Với N pixel có trọng số bằng nhau:
'''+eq(r'\mu=\frac{1}{N}\sum_i x_i,\quad m_k=\frac{1}{N}\sum_i(x_i-\mu)^k')+eq(r'\sigma=\sqrt{m_2},\quad \operatorname{skew}=\frac{m_3}{\sigma^3},\quad \operatorname{kurt}=\frac{m_4}{\sigma^4}')+'''
Mean biểu diễn mức màu trung tâm; std đo độ phân tán; skew mô tả bất đối xứng; kurtosis nhạy với đuôi/phần giá trị cực đoan. Đó không phải phép đo chất lượng ảnh độc lập. Code dùng std quần thể ddof=0, skew không bias và **Pearson kurtosis**, không trừ 3. PDF liệt kê tên thống kê nhưng không chốt các chi tiết này.

**Ví dụ giải tích** x={0,0,0,4}: μ=1; các sai lệch {−1,−1,−1,3}; m2=3, m3=6, m4=21. Vì vậy std=√3=1,732051; skew=2/√3=1,154701; Pearson=7/3=2,333333 (excess sẽ là −0,666667). Đây là oracle số học, không phải nhãn hoặc ảnh giả trong dataset.

'''+table(['ROI/kênh','Mean','Std','Skew','Pearson'],labrows)+'''

Bảng 1. Mô-men thật của cfd_final_00001.png. Nếu std<1e-12, code đặt std/skew/kurt=0 và warning; đây là fallback đã chấp thuận vì skew/kurt kênh hằng không xác định. Vùng <100 pixel không được áp fallback để tạo vector giả.
''')
add('Chương 4 — B3', '''# 4.4. B3 — CIRCULAR HUE STATISTICS

H=179 và H=1 có khoảng cách số học 178 nhưng gần nhau trên vòng Hue. Trung bình số học bằng 90 chỉ về phía đối diện; cần thống kê hướng (directional statistics). [PDF §2.3.3, tr.13] quy định histogram Hue10 L1, góc φ=2πH/180, circular mean/std và miền [0,1].
'''+eq(r'\varphi_i=\frac{2\pi H_i}{180},\quad C=\operatorname{mean}(\cos\varphi_i),\quad S=\operatorname{mean}(\sin\varphi_i)')+eq(r'R=\operatorname{clip}(\sqrt{C^2+S^2},0,1),\quad \bar H_c=\frac{\operatorname{atan2}(S,C)\bmod 2\pi}{2\pi}')+eq(r's_c=\min\left(\frac{\sqrt{-2\log(\max(R,10^{-12}))}}{2\pi},1\right)')+'''
Sin/cos chiếu hướng thành hai thành phần; mean của chúng là resultant. atan2 dùng cả dấu hai trục để xác định góc; modulo đưa góc về [0,2π), rồi chia 2π. R gần 1 biểu thị hướng tập trung; log tạo độ phân tán trong công thức hiện tại. Floor chống log(0), clip giữ miền. D06–D08 phê duyệt biểu thức cụ thể; PDF không cho đủ công thức scale std để gọi toàn bộ biểu thức là nguyên văn PDF.

'''+pic('hue_circle.png','Hình 6. Ví dụ giải tích vòng Hue; không phải một ảnh/nhãn tổng hợp thay dataset.')+f'''

Với H={{179,1}}, R=cos(π/90)=**{f['hue_example']['R']:.9f}**, mean vòng≈0, std vòng=**{f['hue_example']['std']:.9f}**. Với R<1e-8, mean=0 kèm warning; std tiếp tục theo floor/clip. Mean dạng scalar vẫn có mép vòng khi dùng Euclid; không tự đổi thành sin/cos tăng chiều.
''')
layout=read_csv(B/'feature_layout.csv')
for region,offset in (('Skin',0),('Hair',72)):
    items=layout[offset:offset+72]
    rows=[]
    for i in range(36):rows.append((items[i]['index'],items[i]['name'],items[i+36]['index'],items[i+36]['name']))
    add('Chương 4 — Index '+region,f'''# 4.5. B144 — ÁNH XẠ INDEX {region.upper()}

Nguồn trực tiếp: `color_features_full_v1/feature_layout.csv`. B144=[Skin72,Hair72]; index bắt đầu từ 0. Trang này liệt kê đủ 72 chiều {region}, không chỉ mô tả theo khoảng. Tên cùng schema phải dùng thống nhất trong vector, stats và query.

'''+table(['Index','Tên chính xác','Index','Tên chính xác'],rows)+'''

HS48 flatten theo Hue ngoài/S trong. Lab12 theo L,a,b và trong mỗi kênh mean,std,skew,kurtosis. Hue10 tiếp theo, cuối cùng mean vòng và std vòng. Hoán vị đồng bộ toàn bộ vector/stats giữ Euclid; trộn hai serialization khác nhau làm kết quả sai dù shape vẫn 144. D13 chốt thứ tự này, PDF không liệt kê từng index.
''')
add('Chương 5 — Z-score B', '''# CHƯƠNG 5. Z-SCORE BỘ B

## 5.1. Các lớp chuẩn hóa và tập fit

Histogram H–S và Hue10 được L1 riêng trong mỗi ROI; circular mean/std đưa về [0,1]; ghép đủ B144 rồi **một lần Z-score all144**. D14 chốt cách hiện thực thống nhất này. §2.3.3 (PDF 13) và §2.5.2 (PDF 17) diễn đạt khác về mô-men trước ghép; không khẳng định PDF chỉ cho duy nhất trình tự trên.

Fit mean/std ddof=0 trên **tất cả 1.437 vector hợp lệ** của kho 1.438 ảnh. `hf_merged_00209.png` không có tóc raw nên không có B144. Không có hàng vector zero/NaN để che thiếu. fit_manifest lưu danh sách ảnh, feature index và hash; warning không tự loại ảnh hợp lệ.

'''+eq(r'd_j=1\ (\sigma_j<10^{-8}),\quad d_j=\sigma_j\ (\sigma_j\geq10^{-8}),\qquad z_j=\frac{x_j-\mu_j}{d_j}')+'''
## 5.2. So sánh chính xác với A

**Code A và B hiện cùng quy tắc divisor dạng std_safe** (ddof=0, ngưỡng 1e-8, thay bằng 1). Không bịa rằng mẫu số hai code khác nhau. Khác biệt quan trọng: A lệch phương trình σ+ε của PDF, còn B được D15 phê duyệt rõ; A lưu normalized float32, B lưu float64; tập fit A=1.438 và B=1.437, số chiều khác nhau.

'''+pic('B_distributions.png','Hình 7. Ba chiều B thật trước/sau Z-score; không L1 lại sau bước cuối.')+'''

## 5.3. Query và giới hạn

Query dùng đúng mean/divisor đã lưu, không fit theo ảnh hoặc cặp query–candidate. Cột hằng có Z=0 trong training; query khác mean ở cột này vẫn chia 1 chứ không ép 0. Kho B hiện không có cột std<1e-8. Z-score có thể khuếch đại bin hiếm; histogram sau Z-score có thể âm và tổng khác 1. Không điều chỉnh để làm Top-5 đẹp hơn.
''')
add('Chương 6 — Euclid và A Top-5', '''# CHƯƠNG 6. TÌM KIẾM TƯƠNG ĐỒNG

## 6.1. Euclid và luồng Top-5
'''+eq(r'd(q,i)=\sqrt{\sum_{j=1}^{D}(z_{qj}-z_{ij})^2},\quad D=150\ (A),\ 144\ (B)')+'''
Trích query → dùng stats kho của đúng bộ → tính Euclid → loại self theo quy ước → sắp tăng dần → lấy 5. Khoảng cách A/B chưa cùng thang đo để cộng trực tiếp. L2 ở đây có căn bậc hai; không thay bằng cosine hoặc Chi-square cho B.

**Code A:** query trích lại từ ảnh, Z float64; kho normalized float32 cast float64 trước tính d. Self-match theo `Path(image_path).resolve()`; `np.argsort` mặc định, không có tie-break theo tên được code quy định rõ.

**Code B:** query dùng cùng schema và stats, self theo image_id (có nhận diện hash duy nhất khi gọi API); hòa d theo tên file (`lexsort`). Không tự áp quy ước B hồi tố lên A.

'''+pic('saved_A_grid.png','Hình 8. Top-5 A thật đã lưu cho cfd_final_00144.png; d và tên được kiểm tra lại, không ghi đè artifact.')+'''

'''+table(['Hạng','Ảnh kết quả','Euclid A'],[(r['rank'],r['image_name'],num(r['distance'])) for r in agrid])+'''

Danh tính ảnh trong 6 ô PNG gốc được xác định bằng khớp pixel với dataset; thứ tự khớp tính lại từ ma trận thật. Hình gốc một hàng giữ ở figures/original_A_top5.png. Khoảng cách bảng dùng độ chính xác tính lại; nhãn PNG lịch sử làm tròn ba chữ số.
''')
add('Chương 6 — B Top-5', '''# 6.2. TOP-5 B — KẾT QUẢ ĐÃ LƯU

Query `cfd_final_00537.png`, dùng B144_raw_v1.0.0 và stats kho hợp lệ 1.437 ảnh. Dữ liệu tên/thứ tự/d lấy từ `retrieval/top5.csv`, hình gốc từ `retrieval/queries/`; không tự gán các ảnh “trông giống” để thay cho kết quả máy.

'''+pic('saved_B_grid.png','Hình 9. Query và Top-5 B thật; bố cục lại từ ảnh thật, giữ tên, thứ tự và khoảng cách artifact.')+'''

'''+table(['Hạng','Ảnh kết quả','Euclid B'],[(r['rank'],r['image_name'],num(float(r['distance']))) for r in bgrid])+'''

Với query trong kho hợp lệ, sau bỏ self còn 1.436 ứng viên B. Các ảnh khác cùng người/khác biểu cảm vẫn có thể xuất hiện; image_id là ID ảnh, không phải danh tính người. Kho dữ liệu có ảnh cùng người theo mô tả PDF, nhưng việc kết quả gần không chứng minh thuật toán nhận diện đúng người.

Đây là minh họa khả năng vận hành: không có nhãn relevance độc lập để tính accuracy, precision/recall hoặc mAP truy hồi. Các số d chỉ là khoảng cách trong không gian B đã chuẩn hóa; không so sánh trực tiếp d nhỏ của A với d của B để chọn bộ tốt hơn.

Tập 10 query đã lưu của B gồm 5 CFD +5 HF, chọn theo độ phủ mean Lab. Quy tắc chọn query không thay metric; kiểm tra đủ 50 dòng không self-match đã có trong hồ sơ v1. Báo cáo này không sửa công thức dựa trên kết quả nhìn thấy.
''')
add('Chương 6 — So sánh cùng query', '''# 6.3. SO SÁNH ĐÚNG PHẠM VI

Hai hình trước là các ví dụ **đã lưu** nhưng khác query; không dùng chúng để kết luận A/B thắng nhau. Để minh họa cùng đầu vào, bảng dưới giữ kết quả A đã lưu cho CFD00144 và tính kiểm tra B từ hàng B144 normalized thật của đúng ảnh đó. Phần B bổ sung chỉ ghi dưới docs/reports/_build/report_only_B_same_query.csv; không thay kết quả Top-5 hiện có trong outputs.

'''+table(['Hạng','A: tên ảnh','dA','B: tên ảnh','dB'],[(i+1,agrid[i]['image_name'],num(agrid[i]['distance'],4),b_same[i]['image_name'],num(b_same[i]['distance'],4)) for i in range(5)])+'''

'''+pic('derived_B_same_query.png','Hình 10. B cho query CFD00144, tính kiểm tra từ artifact thật; không gắn nhãn giả là PNG lịch sử đã lưu.')+'''

A đo cấu trúc điểm và tỉ lệ; B đo phân bố màu trong ROI. Hai bộ có thể chọn ảnh khác nhau theo tiêu chí mà mỗi bộ biểu diễn. Không được suy ra chất lượng định danh hoặc “A+B đã hoàn thiện”. Một phân bố màu tương tự có thể thuộc hình học khác và ngược lại.

**Ba loại đánh giá khác nhau:** unit test xác nhận thuật toán số; đánh giá segmentation cần mask thủ công độc lập cùng protocol ROI; đánh giá retrieval cần nhãn/tiêu chí relevance và giao thức query/gallery. Không chuyển một loại kiểm tra thành số đo của loại còn lại.
''')
add('Chương 7 — Kết quả và kiểm chứng', '''# CHƯƠNG 7. KẾT QUẢ VÀ HẠN CHẾ

## 7.1. Tổng hợp đo trực tiếp

'''+table(['Hạng mục','Bộ A','Bộ B'],[
('Shape raw / normalized','(1438,150) / (1438,150)','(1437,144) / (1437,144)'),('Ảnh không có vector','0 theo failed_images.csv','1: hf_merged_00209.png'),('Dtype raw / Z','float32 / float32','float64 / float64'),('Fit theo cột','1.438 hàng hợp lệ','1.437 hàng hợp lệ'),('Chiều std<1e-8','0','0'),('NaN/Inf trong matrices','0','0'),('Max abs(mean Z)',f'{f["A"]["max_abs_z_mean"]:.3e}',f'{f["B"]["max_abs_z_mean"]:.3e}'),('Max abs(std Z−1)',f'{f["A"]["max_z_std_error"]:.3e}',f'{f["B"]["max_z_std_error"]:.3e}'),('Sai số reconstruct so với float64',f'{f["A"]["max_z_float64_reconstruction_error"]:.3e} (cast32)',f'{f["B"]["max_z_float64_reconstruction_error"]:.3e}')])+'''

Số đo mean/std trên đây được tính lại trong lần audit này, không sao chép summary để giả là kiểm tra độc lập. Sai số giảm tổng/cách bố trí mảng ở mức floating point có thể khác chữ số cuối so với summary lúc trích; ma trận không bị thay đổi. A khớp chính xác khi reconstruct rồi cast32; B reconstruct đúng bằng stats lưu.

## 7.2. Kiểm thử kỹ thuật

40/40 color unit tests chạy lại thành công trong .venv-uniface, log lưu riêng dưới _build. Repo chưa có bộ unit test riêng đầy đủ cho A; báo cáo bổ sung kiểm tra số học độc lập của 14 A2 trên tọa độ thật, sai số tối đa 3,345e-7, tái tạo A150 sample bằng đúng hàng kho, và đối chiếu trực tiếp thống kê toàn ma trận. Không gọi những kiểm tra này là accuracy.

B v1 đã có hồ sơ xác minh 2.876 raw mask, 5.748 histogram L1, đủ 144 chiều và 50 dòng Top-5. Báo cáo đối chiếu lại dtype/shape/finite/statistics và nguồn; không chạy lại segmentation hoặc trích toàn kho. Chỉ chạy landmarks cho một ảnh thật để dựng hình/ví dụ, không ghi vào kho A.

## 7.3. Sai lệch A cần nêu rõ

Mẫu số A std_safe không giống σ+ε của PDF. Face-height và các điểm đại diện gò má/hàm là proxy hiện thực; mapping 68 điểm không được PDF liệt kê đủ để xác nhận từng nút. Bản đồ 2D, pose, ánh sáng tác động detector và biểu cảm đều có thể ảnh hưởng A. Không sửa code hoặc che các giới hạn này bằng tên “đặc trưng nhân trắc”.
''')
add('Chương 7 — ROI và hướng tiếp theo', '''# 7.4. CHẤT LƯỢNG MASK VÀ DỮ LIỆU THIẾU

B có **1.169 ảnh có warning raw/feature**, trong đó **1.168 vector hợp lệ**; warning không tự loại khỏi fit. Có **305 ảnh abs(Z)>5** ở ít nhất một chiều theo hồ sơ v1, không đồng nghĩa 305 lỗi. Pixel tóc ít nhất trong các vector hợp lệ là **106**; ngưỡng 100 không bảo đảm tính đại diện màu tóc.

'''+pic('mask_caveats.png','Hình 11. Hai dự đoán thật: khăn che tóc HF00694 và tay che mặt HF00722; không phải nhãn chuẩn.')+'''

Ở HF00694, hair raw chỉ 355 pixel sát mép trên, dễ không đại diện cho tóc nhìn thấy. Ở HF00722, raw skin quan sát chứa phần tay; không có nhãn độc lập để định lượng ảnh hưởng. HF00676 có tóc hồng hiếm và kết quả khác màu quan sát; không thay công thức để tối ưu ví dụ này. HF00209 có hair=0; trạng thái thiếu là dữ liệu được công khai, không bịa màu tóc.

## 7.5. Trước khi chuyển sang C

Cần protocol ROI và relevance độc lập nếu muốn đo chất lượng, đặc biệt khi nhiều người, che khuất, nền phức tạp hoặc hue ít bão hòa. Nhãn thủ công lịch sử không tự trở thành bộ GT đầy đủ cho UniFace toàn kho hoặc nhãn truy hồi.

Giữ đúng thiết kế §2.5: khi kết hợp, dùng median normalization từng d rồi tổng trọng số không âm, tổng bằng 1. Ghép theo image_id/a_row_index, không theo số hàng mặc định vì B thiếu một ảnh. Không gán dB=0 hay vector B=0 để che thiếu. C1/C2 và A+B fusion chưa triển khai; tài liệu không tự công bố chúng đã hoàn thiện.
''')
add('Nguồn và tái lập', '''# NGUỒN, KIỂM CHỨNG VÀ TÁI LẬP

## 8.1. Nguồn chính và hồ sơ cục bộ

1. Báo cáo nhóm `csdldpt.pdf`, 18 trang; SHA-256 **8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80**. Các công thức viện dẫn từ tr.9–13 và 17; quy trình dataset tại tr.4–5.
2. A: `geometry_features.py`, `extract_all_features.py`, `normalize_features.py`, `map_68_landmarks.py`; `shared/paths.py`, `shared/detect_landmarks.py`; `retrieval/search_geometry.py`.
3. B: `color_features.py`, `full_color.py`, `search_full_color.py`, `verify_full_color.py`, `batch_uniface.py`; schema/feature_layout/stats/manifest của color_features_full_v1.
4. `docs/report_compliance_audit.md`, `B_implementation_decisions.md`, `B_color_feature_spec.md`, `B_color_final_report.md`; README/metadata dataset và log tests.

Không dùng nguồn web để bổ sung ngầm công thức. Phần giải thích toán học suy ra trực tiếp từ công thức và dữ liệu, được phân biệt với trích dẫn báo cáo. Chi tiết source của 42 module được lưu cùng hash/dòng/hàm trong `_build/source_inventory.json` và bản source_review.txt để truy vết, gồm cả module cũ không thuộc pipeline B v1.

## 8.2. File đi kèm

`A_B_Feature_Analysis.md` là bản nguồn có thể chỉnh sửa; `A_B_Formula_Audit.md` đối chiếu công thức; `A_B_Report_Validation.md` ghi kiểm tra dữ liệu/PDF. Hình, số liệu và script build đặt trong figures/ và _build/. Công thức LaTeX trong Markdown được render SVG vector, không chụp công thức bằng ảnh mờ.

Muốn render lại sau khi chỉnh Markdown: chạy `.venv311\\Scripts\\python.exe -X utf8 -B docs/reports/_build/render_report.py`, rồi Chrome headless theo lệnh trong file validation. Không cần cài thư viện hoặc tải model. Không chạy main của extractor/normalizer A/B để tạo báo cáo.

## 8.3. Phạm vi bảo toàn

Hash được chụp trước/sau cho source, artifact, dataset, annotations, model và PDF gốc, loại trừ thư mục báo cáo mới và bytecode cache. Mọi sai lệch được ghi, không tự sửa thuật toán. Kiểm tra PDF gồm A4, số trang, font tiếng Việt, cấu trúc bảng/công thức, không tràn vùng nội dung và raster từng trang để review.

Báo cáo mô tả **hệ thống đã quan sát**, nêu rõ phần chưa đủ bằng chứng. Vector hữu hạn, unit tests đạt và Top-5 vận hành không thay thế đánh giá phân đoạn hoặc nhận diện có ground truth.
''')
title,body=pages[5]
body=body.replace('Chuẩn hóa này bất biến','Bảng mapping đầy đủ theo INDICES (0-based code → ID MediaPipe):\n\n'+table(['Nhóm','Index code','ID MediaPipe theo thứ tự'],group_rows)+'\n\nChuẩn hóa này bất biến')
pages[5]=(title,body)
assert len(pages)==28,len(pages)
md='\n\n'.join(f'<!-- PAGE {i}: {title} -->\n\n{body}' for i,(title,body) in enumerate(pages,1))+'\n'
(OUT/'A_B_Feature_Analysis.md').write_text(md,encoding='utf-8')
(BUILD/'page_titles.json').write_text(json.dumps([t for t,_ in pages],ensure_ascii=False,indent=2),encoding='utf-8')
# Separate formula audit, with all fourteen implementation formulas explicit.
audit='''# A/B — Đối chiếu công thức với báo cáo và source hiện tại

Ngày 22/11/2026. PDF chuẩn SHA-256 8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80. Số trang PDF từ 1. Không sửa thuật toán hoặc artifact.

## Bộ A

`geometry_features.py` là nguồn extractor; `map_68_landmarks.py` là công cụ vẽ. A1 interleaved x,y theo INDICES; A2 nối đúng thứ tự 14 mục. Các ID landmarks/epsilon trong A2 là quy ước code khi PDF chưa quy định đủ, không đánh EXACT cho toàn bộ biểu thức chỉ vì tên trùng báo cáo.

'''+table(['Mục','PDF','Code/công thức đang dùng','Trạng thái/ảnh hưởng'],[
('478 → 68','§2.2.2, tr.8','INDICES chọn 68 nút từ model 478; num_faces=1','IMPLEMENTATION DETAIL: PDF không cho đủ mapping; cap output không chứng minh ảnh chỉ có một người'),
('Chuẩn hóa điểm','§2.2.2, tr.9',"p′=(p−c)/d; c=mid(mean(p36:42),mean(p42:48))",'EXACT về công thức; IMPLEMENTATION DETAIL về định nghĩa tâm bằng 6 nút'),
('A1/A2','§2.2.3, tr.9–10','136 tọa độ +14 ratio/angle; float32','EXACT về kích thước; serialization là quy ước'),
('Z-score A','§2.5.2, tr.17','where(std<1e-8,1,std), không phải std+epsilon','DEVIATION: không được nói hai cách giống nhau; ε PDF chưa cho trị số'),
('Query A','§2.5.2, tr.17','Dùng stats kho, gallery float32/query float64','EXACT reuse; precision và self-match theo đường dẫn là implementation detail')])+'''

## Đủ 14 thành phần A2

Ký hiệu D(a,b)=Euclid2D; eL/eR là mean 6 điểm mắt; c=(eL+eR)/2; d=D(eL,eR); h=D((p21+p22)/2,p8); epsilon ratio=1e-8. Nguồn hàm `geometry_features.calculate_ratios`, với `angle_degrees` cho mục 14. PDF §2.2.3 tr.9–10 nêu tên, tỉ lệ và ý nghĩa; công thức điểm cụ thể bên dưới là hiện thực code.

'''
for i,item in enumerate(features):
    audit+=f'### A2-{i+1:02}: {item[0]}\n\n- Index A150: {136+i}; landmarks p{item[1]}.\n- Công thức code: `{item[2]}`.\n- Ví dụ ảnh thật: `{item[3]}` → {g["ratios"][i]:.9f}.\n- Trạng thái: IMPLEMENTATION DETAIL cho điểm/proxy/epsilon; công thức góc dot/acos và khoảng cách Euclid được PDF nêu rõ nhưng điểm/clip/guard là chi tiết code.\n- Hạn chế: {item[5]}\n\n'
audit+='''## Bộ B — yêu cầu PDF và quy ước đã được phê duyệt

'''+table(['Thành phần','Nguồn PDF','Code/schema thực tế','Phân loại'],[
('HS12×4, L1','§2.3.1, tr.12','region_descriptor; bins (12,4), H [0,180), S [0,256)','EXACT số bins/L1; cạnh bin D01 APPROVED'),
('CIE-Lab 4×3','§2.3.2, tr.12','BGR float32/255 → Lab, mô-men float64','EXACT tên/chiều; D02 APPROVED đơn vị/precision'),
('Std/skew/Pearson','§2.3.2, tr.12','sqrt(m2), m3/std³, m4/std⁴; không trừ 3','D03–D05 APPROVED; không gán công thức chi tiết cho PDF'),
('Hue10 L1','§2.3.3, tr.13','np.histogram 10 bin, [0,180), L1','EXACT số bin/miền/L1; cạnh D01 APPROVED'),
('Phi','§2.3.3, tr.13','2*pi*H/180','EXACT biểu thức'),
('Mean/std vòng','§2.3.3, tr.13','atan2(S,C) modulo 2π /2π; min(sqrt(-2log(max(R,1e-12)))/2π,1)','D06–D08 APPROVED; PDF chỉ nêu góc/tên/[0,1]'),
('ROI raw skin1/hair17','§2.3, tr.11–13','class1/class17; không erosion, không gộp nose','D09–D12 APPROVED, không phải UniFace được PDF chỉ định'),
('B144 order','§2.3, tr.11–13','Skin72,Hair72; HS48/Lab12/Hue10/mean/std','D13 APPROVED; đủ144, index đầy đủ trong báo cáo chính'),
('Z-score B','§2.3.3, tr.13; §2.5.2, tr.17','descriptor→concat→all144; ddof0, std<1e-8 divisor1','D14–D16 APPROVED; không tuyên bố PDF chỉ cho một trình tự'),
('Euclid/self/tie','§2.3.3, tr.13; §2.5, tr.17–18','L2 đủ144; self ID; tie filename','EXACT Euclid; D17 APPROVED giao thức')])+'''

## Kết luận kiểm toán có giới hạn

A và B code hiện dùng cùng dạng std_safe, nhưng nguồn thẩm quyền khác: A đang khác mẫu số σ+ε của PDF; B được D15 phê duyệt. A lưu Z float32, B float64. Không sửa A để làm báo cáo đẹp hơn; không đổi công thức B theo ví dụ Top-5. A2 có đủ 14 tên theo PDF nhưng proxy mốc/chiều cao và các guard chưa được PDF liệt kê đủ. Chất lượng landmarks/ROI và relevance không được chứng nhận bởi kiểm tra số học.

Nguồn code đầy đủ và vị trí hàm: _build/source_inventory.json (42 module), _build/source_review.txt. Số liệu: _build/facts.json. Không triển khai hoặc kiểm toán công thức C1/C2 như thể đã có code.
'''
(OUT/'A_B_Formula_Audit.md').write_text(audit,encoding='utf-8')
print('Composed',len(pages),'pages;',len(md),'characters; 14 A2 and 144 B indices')
