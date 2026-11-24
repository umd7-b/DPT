# B144 — kiểm chứng công thức, mask và artifact

Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.


**Kết luận B:** các thành phần, bin/L1, phép chiếu Hue, cấu trúc144, Euclid và số học của cấu hình hiện tại được kiểm chứng. Không chứng nhận toàn pipeline theo PDF vì **B12 thiếu stage mô-men chuẩn hóa trước ghép**. D01–D13/D15–D17 giữ nguyên phê duyệt; D14 không được dùng để bỏ yêu cầu thứ tự rõ của PDF.

Đã đọc trực tiếp `docs/B_implementation_decisions.md`, `B_color_feature_spec.md`, `report_compliance_audit.md`, `B_color_final_report.md` và source hiện tại. Báo cáo audit cũ ghi B30 UNVERIFIED trước phê duyệt; báo cáo finalize chốt D14. Trong audit nghiêm ngặt này, thứ tự được tái phân loại dựa vào nguyên văn PDF, không chỉ kế thừa kết luận cũ. Không sửa hồi tố bốn tài liệu đó.

## B1 — H–S

Source `region_descriptor`: lấy `image[mask>0]`, chuyển đúng BGR→HSV theo API OpenCV, chỉ H/S; histogram12×4, ravel C-order, chia tổng của48 bin. Bin đều H0,15,…,180, S0,64,…,256 là D01, không phải toàn bộ cạnh bin do PDF chốt. Không dùng V trong histogram; không lọc bão hòa và không thêm nền đen ngoài mask. Pixel đen thật nằm trong mask vẫn được tính.

Oracle mới tạo48 ô có khối lượng1..48, dùng chỉ số bin bằng phép chia nguyên và `bincount` thay `histogram2d`. Đã tính lại **5748 histogram=2 histogram×2 vùng×1437 ảnh**, từ ảnh gốc/raw mask; max sai số bằng0. Đây là kiểm chứng histogram trên toàn kho, không phải chỉ kiểm tổng L1.

## B2 — CIE-Lab

PDF yêu cầu mean/std/skewness/kurtosis trên L*,a*,b*; không chốt Pearson/excess, ddof/bias hay công thức suy biến. D02–D05 được chấp thuận: BGR float32/255→Lab; `mu=sum/N`, `m_k=sum((x−mu)^k)/N`, `std=sqrt(m2)`, `skew=m3/m2^(3/2)`, `kurt=m4/m2²` Pearson; std<1e-12 dùng std/skew/kurt0 và ghi warning.

Oracle giải tích black/white L*=0/100 cho mean50/std50/skew0/kurt1. Phân bố0,0,0,100 cho mean25/std25√3/skew2/√3/kurt7/3, khác excess−2/3. Phép chuyển màu đối chiếu thêm sRGB→XYZ→Lab bằng phương trình scalar/D65, tolerance0.3 cho LUT float OpenCV; phép kiểm này chứng minh biểu diễn CIE-Lab, **không thêm white point như điều khoản PDF mới**.

Đối chiếu full descriptor độc lập dùng `math.fsum` cho **18 vùng của9 ảnh thật** gồm CFD/HF, màu hiếm, khăn che và bàn tay; max error1.07e-14. Các kỳ vọng không lấy từ `extract_color/region_descriptor`. Không tuyên bố đã tính độc lập toàn bộ mô-men của2874 vùng: kiểm toàn kho ở đây là histogram, stats/mapping/provenance; mô-men scalar đầy đủ là mẫu18 vùng có ghi danh tính.

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

Raw và normalized đều1437×144 float64, hữu hạn, khớp metadata/fit manifest;9 file core integrity khớp. Toàn ma trận normalized tái tạo chính xác bằng stats đã lưu, so oracle fsum max7.11e-15. Mean oracle max7.11e-15, raw_std oracle max7.11e-15;0 chiều std<1e-8 trên kho. Các cột hằng vẫn có analytic test, query khác mean chia divisor1 đúng D15.

Bốn cột circular của toàn raw matrix đã kiểm range: min=0.000901529500, max=0.999898103108, tất cả trong[0,1] trước Z-score. Sau Z-score không buộc histogram L1 hoặc circular trong[0,1]; không chuẩn hóa lại để làm đẹp miền giá trị.

Query worker đã thực thi trong `.venv-uniface` với raw masks hiện có, không inference segmentation mới, không refit: query00001 bằng đúng normalized hàng kho. QueryHF00209 không lưu vector B; có status thiếu rõ ràng. B-only Euclid đủ144, self-match theo image_id, tie theo filename; **50 dòng Top-5/10 query** tính lại scalar fsum khớp thứ tự, max distance error3.55e-15. Đây là kiểm số học, không phải relevance evaluation/holdout.

Helper `fit_standardizer(profile='moments_only')` còn callable và bỏ120 chiều Z-score, là B18 DEVIATION nếu dùng như cấu hình PDF. Runner hiện tại đã chặn, B144 v1 dùng all144. Giữ lịch sử, không xóa helper hoặc kết quả nghiên cứu trong audit.

## Bảng đối chiếu đầy đủ B

| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |
|---|---|---|---|---|---|---|
| B01 — Hai vùng da/tóc, 72 mỗi vùng, tổng B144 | 11–13,16 | features/B_color/src/color_features.py:111::extract_color | 2×(48+12+10+1+1)=144 | raw shape1437×144; selected descriptor oracles | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B02 — HSV chỉ dùng H và S, không V trong histogram | 12 | features/B_color/src/color_features.py:64::region_descriptor | HS bins trên hsv[:,0],hsv[:,1] | test_hsv_48_distinct_weighted_bins; test_background_outside_mask_has_no_effect | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B03 — 12×4 bins, 48 chiều mỗi vùng | 12 | features/B_color/src/color_features.py:64::region_descriptor | histogram2d bins=(12,4) | test_hsv_48_distinct_weighted_bins; 2874 HS histogram tính lại | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B04 — L1 histogram H–S | 12 | features/B_color/src/color_features.py:64::region_descriptor | hs/hs.sum() | 5748 histogram HS/Hue tính lại từ pixel, max error=0 | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B05 — CIE-Lab, bốn loại thống kê trên L*,a*,b* | 12 | features/B_color/src/color_features.py:64::region_descriptor | 3×(mean,std,skew,kurt)=12 | test_float_lab_conversion_matches_independent_srgb_xyz_equations; 18 region oracles | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B06 — Hue10 L1 + circular mean/std, 12 mỗi vùng | 13 | features/B_color/src/color_features.py:64::region_descriptor | 10+1+1; histogram Hue/sum | test_hue_histogram_10_bins_with_known_rgb_primaries; toàn kho raw | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B07 — Phép chiếu góc φ=2πH/180 | 13 | features/B_color/src/color_features.py:48::hue_statistics | angles=H*(2*pi/180) | test_circular_projection_mean_std_known_two_angles; wrap test | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B08 — Hai thống kê vòng trong [0,1] trước Z-score | 13,17 | features/B_color/src/color_features.py:48::hue_statistics | mean/(2π); std clipped ≤1 | 18 region scalar oracles; raw matrix range; undefined-resultant test | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B09 — Chỉ tính pixel trong mask, không cộng nền ngoài mask | 11–12 | features/B_color/src/color_features.py:64::region_descriptor | pixels=image[mask>0] | test_background_outside_mask_has_no_effect; 5748 histogram từ raw masks | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B10 — Bước cuối Z-score trên đủ 144 chiều | 13 | features/B_color/src/color_features.py:123::fit_standardizer | profile=all144, indices=arange(144) | b_ab_verification.json: toàn ma trận Z khớp oracle≤7.11e-15 | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B11 — Query dùng lại tham số kho | 13,17 | features/B_color/src/color_features.py:135::transform | (q−saved_mean)/saved_std | query_worker_verification.json; test_b_zscore_saved_statistics_and_constant_query | EXACT | Kết luận chỉ áp dụng đúng phần yêu cầu ghi ở hàng này. |
| B-D01 — Cạnh bin HSV/Hue và số uint8 | 12–13 | features/B_color/src/color_features.py:64::region_descriptor | H [0,180), S [0,256), cạnh đều 15/64/18 | 48-bin và Hue10 analytic tests | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D02 — Chuyển CIE-Lab và dtype | 12 | features/B_color/src/color_features.py:64::region_descriptor | OpenCV BGR float32/255 → Lab; moment float64 | sRGB/XYZ/Lab analytic check, tolerance0.3; source conversion | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D03 — Mean/std/skew quần thể không bias | 12 | features/B_color/src/color_features.py:64::region_descriptor | mean; sqrt(m2); m3/m2^(3/2) | black/white and asymmetric L* oracles | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D04 — Pearson kurtosis, không trừ 3 | 12 | features/B_color/src/color_features.py:64::region_descriptor | m4/m2² | asymmetric oracle kurtosis7/3 khác excess−2/3 | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D05 — Kênh hằng/gần hằng | 12 | features/B_color/src/color_features.py:64::region_descriptor | std<1e-12 → std/skew/kurt=0 kèm warning | constant a*,b* trong black/white tests | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D06 — Circular mean atan2/modulo và scale | 13 | features/B_color/src/color_features.py:64::region_descriptor | atan2(S,C) mod2π /2π | two-angle and wrap analytic oracles | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D07 — Circular std, scale/floor/clip | 13 | features/B_color/src/color_features.py:64::region_descriptor | min(sqrt(−2ln(max(R,1e-12)))/(2π),1) | two-angle and R≈0 oracles | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D08 — Resultant gần 0 | 13 | features/B_color/src/color_features.py:64::region_descriptor | R<1e-8 → circular_mean=0 + warning | test_undefined_resultant_convention_is_flagged | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D09 — Raw skin class1, hair class17, không gộp nose10 | 11–13 | features/B_color/src/batch_uniface.py:95::make_masks | make_masks(labels==1/17) | batch_uniface.py::make_masks; installed uniface/draw.py label list | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D10 — Không erosion cho B144 v1 | 11–13 | features/B_color/src/batch_uniface.py:95::make_masks | full_color nhận tuple(raw skin,raw hair) | 2876 raw mask hashes/receipts; histogram recomputation exact | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D11 — Không lọc theo S, chỉ cảnh báo | 12–13 | features/B_color/src/color_features.py:64::region_descriptor | Không xóa pixel S<10; warning fraction>0.5 | black/white test S=0 vẫn được tính; source_listing.txt | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D12 — Vùng dưới100 pixel không có B, không zero-fill | 12 | features/B_color/src/color_features.py:64::region_descriptor | extract_color.vector=None | test_missing_region_no_zero_fill; query_worker_missing_b/b_status.json | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D13 — Serialization Skin72/Hair72, HS/Lab/Hue | 11–13 | features/B_color/src/color_features.py:64::region_descriptor | [HS48,Lab12,Hue10,mean,std]×2 | weighted bin oracle; 18 region full vector oracles | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D15 — B ddof0, std<1e-8→divisor1, giữ144 chiều | 13,17 | features/B_color/src/full_color.py:115::run; features/B_color/src/color_features.py:123::fit_standardizer | (x−mu)/where(sigma<1e-8,1,sigma) | test_b_zscore_saved_statistics_and_constant_query; all gallery stats | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D16 — Fit toàn bộ 1437 B hợp lệ, không tự loại warning | 13,17 | features/B_color/src/full_color.py:115::run; features/B_color/src/color_features.py:123::fit_standardizer | manifest1438, feature_rows/fit_manifest1437 | manifest/status/count/mapping/hash checks; warning1169 | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B-D17 — B self-match theo image_id, tie filename | 17–18 | features/B_color/src/search_full_color.py:44::rank | lexsort(filename,distance); exclude ID | 50 Top-5 rows recomputed by scalar fsum; existing color tests | APPROVED IMPLEMENTATION DETAIL | Giữ quyết định đã phê duyệt ngày22/11/2026; không gán nó là công thức nguyên văn PDF. |
| B12 — Mô-men phải được chuẩn hóa theo kho trước khi ghép | 13 §2.3.3;17 §2.5.2 | features/B_color/src/color_features.py:111::extract_color; features/B_color/src/full_color.py:115::run | Đang raw descriptor → concat144 → fit/transform all144 một lần | test_no_preconcat_moment_standardization_in_current_descriptor; source run(); b_stage_order_illustration.json | DEVIATION | D14 mâu thuẫn thứ tự được PDF nói rõ; chuẩn bị stage riêng trong phiên bản mới, chưa tự thêm ở audit. |
| B13 — Công thức cụ thể cho bước chuẩn hóa mô-men trước ghép | 13,17 | features/B_color/src/full_color.py:115::run | PDF không chốt toán tử/epsilon/fallback của stage trước ghép | Đọc nguyên văn PDF; D14 không giải quyết đủ thứ tự | UNVERIFIED | Chốt toán tử tuân thủ PDF; không tự coi hai lần Z-score là định nghĩa đầy đủ duy nhất. |
| B14 — Vùng mask phù hợp ngữ nghĩa da mặt/tóc của đối tượng | 11–13 | features/B_color/src/full_color.py:68::verified_input | Class1/17 không bảo đảm ngữ nghĩa prediction từng pixel | dataset_mask_review_page1/2.png; visual_review_findings.csv | UNVERIFIED | Không có GT độc lập; ghi hand/secondary-face/covering, không đổi ROI sang skin+nose hoặc clean. |
| B15 — 1438 input,1437 valid,1 missing HF00209 | 11,16; yêu cầu nhiệm vụ | features/B_color/src/full_color.py:115::run | manifest1438; compact raw/z1437×144; missing row918 | b_ab_verification.json; missing_features.csv | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| B16 — Mapping feature_row_index/a_row_index và stats provenance | 13,17 | features/B_color/src/search_full_color.py:17::load_gallery | feature row→A row/ID; hash fit_manifest, schema và 9 integrity files | 2876 masks/source hashes; full normalization and mapping checks | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| B17 — Euclid đủ144 và kết quả tăng dần | 13,17–18 | features/B_color/src/search_full_color.py:44::rank | sqrt(sum_{j=1..144}(qj−xj)²) | 50 saved rows; scalar Euclid max error3.56e-15 | EXACT | Giữ nguyên trong audit; xem kế hoạch sửa theo phiên bản. |
| B18 — Helper lịch sử moments_only không phải chuẩn hóa all144 theo PDF | 13 | features/B_color/src/color_features.py:123::fit_standardizer | profile=moments_only chỉ scale24/144 chiều | run_color_experiment.py từ chối profile này; helper vẫn callable | DEVIATION | Chỉ nhánh nghiên cứu, không được gọi v1 bám báo cáo; giữ lịch sử, không xóa hay thay artifact. |
| B19 — Chất lượng segmentation/retrieval đã được đo với nhãn độc lập | 11–13 (giá trị thông tin) | features/B_color/src/search_full_color.py:74::evaluate | Không có relevance/GT độc lập trong audit này | visual_review_findings.csv; danh sách nguồn nhãn chưa đầy đủ | UNVERIFIED | Không báo accuracy/IoU/Dice hoặc lấy Top-5 làm căn cứ sửa công thức. |
