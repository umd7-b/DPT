# Đặc tả C1 LBP 236 chiều — chưa viết extractor

Ngày kiểm tra: **23/11/2026**, Asia/Saigon. Nguồn yêu cầu cao nhất: `csdldpt.pdf`, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80` đã xác minh. Đã đọc toàn bộ §2.2/§2.4 qua bản trích PDF đóng băng, đối chiếu hình PDF và source/hash hiện hành. Không chỉnh PDF, dataset, mapping A, vector A/B, stats/calibration, CSDL hoặc kết quả A+B đã nghiệm thu.

Đợt này chỉ kiểm toán ROI và chốt đặc tả kỹ thuật có nguồn gốc rõ. Không chạy lại MediaPipe, không gọi LBP/HOG trên ảnh, không viết extractor hoặc tạo vector C1/C2. Tên file “final” là hồ sơ kết luận của lần rà soát; trạng thái giải phẫu vẫn **PROVISIONAL**.


Schema ID `C1_LBP_236_IMPLEMENTATION_SPEC_v0.1.0`, version `0.1.0`; status **SPEC_ONLY_PROVISIONAL_ROI**. [JSON đặc tả](../outputs/C1_lbp/roi_validation/lbp_implementation_spec.json), content SHA-256 `7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851`. ROI dependency `C1_ROI_RAW_CONTRACT_v0.2.0` / content hash `61b04936237bdc6a84f991688f667e06a252965d4e24b8028cc2e2f9f63eb69c`.

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

| Chi tiết PDF chưa chốt | Lựa chọn cụ thể | Nguồn gốc/giới hạn |
| --- | --- | --- |
| BGR→gray | uint8; floor((1868B+9617G+4899R+8192)/16384), tích lũy uint32 | Quy ước số nguyên cố định, không phụ thuộc backend cvtColor; không phải PDF |
| Nội suy | Float64 bilinear, horizontal lerp rồi vertical lerp; không làm tròn gray đã nội suy | Quy ước triển khai |
| Điểm đầu/chiều/bit | p0 Đông; ngược chiều kim đồng hồ trên ảnh; trọng số 2^p | PDF chỉ quy định tổng có 2^p, chưa cho orientation |
| Vị trí láng giềng | Bảng offset chứa ±2,0 và ±sqrt(2); cardinal ghi 0 chính xác | Không round tọa độ thành 5 decimal nếu dùng spec này |
| 58+1 labels | 0→0;255→57;nonuniform→58; còn lại theo run-start formula bên dưới | Chọn numbering có đối chiếu kỹ thuật; PDF chỉ quy định 59 bin |
| Biên ROI/ảnh | Centre và mọi pixel stencil bilinear có trọng số khác 0 phải nằm trong cùng raw ROI và ảnh | Footprint 21 điểm; không padding/reflect hoặc lấy vùng khác |
| Overlap | Mỗi mask pool riêng, shared pixel được tính ở từng vùng chứa nó; không priority subtraction | Quy ước prototype; nghĩa giải phẫu độc lập chưa được chứng nhận |
| Vùng thiếu/quá nhỏ | Bất kỳ ROI invalid hoặc <64 eligible centres → missing_C1 cho toàn descriptor | 64 là guard kỹ thuật, không PDF; không zero-fill |
| Ghép vùng | Trán+mày, má trái theo người xem, má phải theo người xem, mũi+miệng | Thứ tự nhóm theo PDF; frame trái/phải là quy ước ghi rõ |
| NaN/Inf | Reject input/intermediate, ghi missing_reason; không nan_to_num/impute | Quy ước fail rõ ràng |
| Histogram/dtype | Counts uint64; h_j=count_j/N ở float64, N nguyên; L1 từng vùng không cộng epsilon | L1 từng vùng là PDF; arithmetic/dtype là quy ước |
| Chi-square ε | 1e-8, bản tham số có version; không sửa epsilon/calibration A/B | PDF có ε nhưng chưa chốt giá trị |
| Query ảnh mới | 256×256 RGB đã căn chỉnh, cùng model asset/478→frame/gray/bin/support/ROI version; thiếu vùng trả missing | Không tự align/crop theo log lịch sử không có; future adapter riêng |

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
