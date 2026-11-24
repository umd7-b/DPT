# C2 Root-HOG324 — đặc tả triển khai v1

Ngày24/11/2026, Asia/Saigon. Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã đọc trực tiếp §2.4.1–2.4.3/§2.5.2.
Đây là prototype với các quy ước chốt trước trial/retrieval, không chứng nhận giải phẫu crop hoặc relevance.
Spec máy đọc: [spec_v1.json](../features/C2_hog/spec_v1.json), content SHA-256
`a568f2eaec4d54cbc72c2a80d49c371362248367ff88224c158f8c5aaa10f169`.

## Đối chiếu thẩm quyền

| Hạng mục | Phân loại | Quy định/bằng chứng |
|---|---|---|
| ROI width160×height192; grid4×4; cell40×48 | PDF_EXACT | §2.4.2 |
| Gx=I(x+1,y)−I(x−1,y),Gy=I(x,y+1)−I(x,y−1) | PDF_EXACT | §2.4.2; không Sobel |
| sqrt(Gx²+Gy²),atan2(Gy,Gx),hướng unsigned | PDF_EXACT | §2.4.2 |
|9 orientation bins/cell,vote magnitude | PDF_EXACT | §2.4.2 |
|2×2 cells/block,stride1,3×3 blocks,36 giá trị/block | PDF_EXACT | §2.4.2–2.4.3 |
|sqrt(h/(sum(block)+epsilon)) | PDF_EXACT | §2.4.2,không L2-Hys/L2 từng block |
|324 chiều,L2 toàn vector,Euclid324 | PDF_EXACT | §2.4.2–2.4.3 và§2.5.2 |
| Vị trí center crop[48:208,32:224] | IMPLEMENTATION_DETAIL | Không tìm thấy source/provenance C2 crop thực sự trong repository; user cho phép fallback |
| Gray nguyên C1,border skip,hard20°,layout,epsilon1e-8 | IMPLEMENTATION_DETAIL | PDF không chốt các lựa chọn số học này |
|[0,180),180→0 | IMPLEMENTATION_DETAIL | PDF in khoảng[0°,180°]; chọn half-open modulo180 để biểu diễn cùng hướng vô hướng và9 bins không tạo bin thứ10 |
| Crop có bao đủ giải phẫu/không che khuất | UNVERIFIED | Chưa có annotation anatomy/occlusion toàn kho |
| Alignment lịch sử và retrieval accuracy | UNVERIFIED | Không tự suy từ ảnh hiện hành/Top-5 khi thiếu logs/relevance labels |
| Khác yêu cầu rõ của PDF | DEVIATION | Chưa xác nhận sai lệch; tests/oracle và verification sẽ ghi bằng chứng thực nghiệm |

Không gọi các convention là PDF_EXACT. Các file A/B/C1/SQLite/PDF và baseline cũ giữ nguyên.
Tìm source trước triển khai chỉ thấy placeholder `features/C2_hog/README.md`/package markers và hồ sơ nói
C2 chưa triển khai; không tìm được pipeline160×192 thực sự được dùng. Giữ README cũ như hồ sơ lịch sử.

## Tiền xử lý và gradient

Input duy nhất của extractor: ảnh **đã căn chỉnh sẵn256×256×3 BGR uint8**. Không detector,alignment,
resize,gamma,CLAHE hoặc crop theo kết quả query. `roi=bgr[32:224,48:208]` shape(192,160,3), tọa độ gốc
inclusive x48…207,y32…223. Quy ước x sang phải,y xuống,theo người xem; không liên hệ canonical anatomy.

Gray uint32 `(1868B+9617G+4899R+8192)//16384`,cast uint8 rồi float64. Đây là convention giống C1,
không dùng vector C1 hoặc LBP để biến đổi thành HOG. Code C2 không import môi trường Uniface/MediaPipe.

Gx/Gy theo đúng sai phân PDF tại **1≤x≤158,1≤y≤190**, tổng30020 tâm. Toàn perimeter1 pixel bỏ vote:
Gx=Gy=magnitude=0. Không padding/reflect hoặc đọc pixel ngoài ROI. Bốn cell biên vẫn có kích thước40×48;
pixel biên có magnitude0 nên không thêm vote. Không nhân0.5 vào sai phân.
Magnitude float64=sqrt(Gx*Gx+Gy*Gy),angle=degrees(atan2(Gy,Gx)) modulo180.
atan2(0,0)=0 là convention; magnitude0 không đóng góp histogram.

## Histogram,layout và Root

16 cell hist shape(4,4,9). Pixel(x,y) vào cell(y//48,x//40),orientation bin=floor(theta/20).
Bins[0,20),[20,40),…,[160,180);180/−180 map0. Hard bin,mỗi pixel vote đúng một magnitude vào một cell,
không orientation/spatial interpolation. Float64 cộng theo ảnh row-major y rồi x.

Blocks shape(9,36): block_y0…2 ngoài,block_x0…2 trong. Trong một block nối localcell(0,0),(0,1),(1,0),(1,1),
bin0…8 innermost. `root[b,i]=sqrt(raw[b,i]/(sum(raw[b,:])+1e-8))`.
Không chuẩn hóa cell thêmL1,không L2/Hys/clip từng block. Block0 hợp lệ cho intermediate root0.
Ghép row-major thành324 rồi `norm=sqrt(sum(root324**2))`,chia chính xác cho norm>0 **không epsilon L2**.
Nếu norm0→missing_C2/zero_or_nonfinite_final_L2_norm,không giả vector0 để đủ chiều.
Input thiếu/sai shape/dtype hoặc nonfinite→missing_C2 có reason; không impute,nan_to_num,repair shape.

## Version và truy vấn

Schema `C2_ROOT_HOG_324_SPEC_v1`,preprocessing `BGR_GRAY_INT16384_CENTER160x192_BORDER_SKIP_v1`.
Spec/content/file/kernel hashes được khóa trước tests/trial và gắn mọi vector row. Query/gallery phải cùng lock.
Euclid=`sqrt(sum((a-b)**2))` trên324 float64 đãL2,không cosine/squared-only/Chi-square.
Self bị loại theo image_id,candidate trùngvector0 distance vẫn giữ;ties(distance,image_id) tăng dần.
CLI chỉ ảnh có trong gallery,không tự nhận ảnh mới là aligned. Output mỗi run mới,không overwrite.
Median normalization/fusion trong§2.5.2 không áp dụng cho truy vấn standalone; không làm fusion bốn bộ.

## Oracle và thứ tự gate

Oracle scalar không import production để tạo expected: Python integer gray,loop sai phân/math.sqrt/atan2,
hard bins/cell loops,math.fsum block/root/L2. Đối chiếu intermediate,không chỉ shape.
Tolerance chốt trong spec: gradient0 tuyệt đối,magnitude/angle1e-12,cell hist atol1e-8/rtol1e-13,
root/vector atol5e-14,L2 atol1e-12,Euclid atol1e-13. Không nới sau khi xem kết quả.
Test synthetic và một ảnh thật trước batch; trial100 dùng **manifest C1 trial đã chạy** (50CFD+50HF),
không thay bằng bộ anatomical-review100 khác. Chỉ chạyfull1438 sau trial verification PASS cùng hash.
Không ép số valid; mỗi input luôn có status/missing_reason và vector chỉ cho valid.
