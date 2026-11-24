# A+B — median normalization, join và phụ thuộc phiên bản

Ngày kiểm toán: **23/11/2026**, múi giờ Asia/Saigon. Tài liệu chuẩn duy nhất: `C:\Users\USER\Downloads\csdldpt.pdf`, **18 trang**, SHA-256 `8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`. Đã đọc toàn bộ văn bản và hai hình landmark nhúng trang 8; số trang dưới đây là trang PDF vật lý, không phải số trong mục lục.

PDF ưu tiên hơn code, SCHEMA và quyết định triển khai. EXACT chỉ chứng nhận phạm vi ghi trong hàng, có cả source và kiểm chứng độc lập. APPROVED IMPLEMENTATION DETAIL là quy ước đã được chấp thuận và không mâu thuẫn PDF. DEVIATION có bằng chứng khác yêu cầu rõ; UNVERIFIED gồm thiếu chứng cứ, định nghĩa hoặc phê duyệt. Test đạt về số học không biến một thuật toán khác PDF thành tuân thủ.


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

MedianA=16.441995192935671; medianB=10.814300552264744. Khác biệt≈3.6e-15 khi dùng fsum thay np.linalg ở medianA là làm tròn phép cộng, không sai công thức. Cùng pairs, không median theo query. Cache lưu fingerprint vector/stats/metadata, hash pairCSV, medians vàepsilon; nguồn hiện tại khớp. Tests cache stale/tamper từ chối đúng.

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

| Yêu cầu báo cáo | Trang PDF | File/hàm code | Công thức code | Bằng chứng test | Trạng thái | Hướng xử lý |
|---|---|---|---|---|---|---|
| AB01 — Euclid A150 và B144 riêng | 17 | retrieval/search_ab.py:221::rankings | norm(A−qa), norm(B−qb), không concat trước L2 | 39 audit tests; verify_b_ab scalar oracle | EXACT | Giữ metric; EXACT có điều kiện trên vector phiên bản hiện tại. |
| AB02 — Liên kết bằng ID/index, không ghép hàng mặc định | 16–17; yêu cầu truy vấn trước | retrieval/search_ab.py:92::join_galleries | image_id + kiểm tra a_row_index; lấy B feature_row_index | test_identity_join_with_missing_row_and_permuted_indices; old AB tests | EXACT | Giữ nguyên vì B có1437 hàng. |
| AB03 — Trung vị của mỗi bộ trên cùng tập cặp đại diện | 17 | retrieval/search_ab.py:173::calibrate | mA=median dA(i,j); mB=median dB(i,j), cùng20000 cặp | 20000 pair IDs tái lập bằng toán triangular-index độc lập; scalar distances | EXACT | Chứng nhận cùng tập cặp và median; tính đại diện thống kê xem AB05. |
| AB04 — Median normalization đúng d/(m+ε) | 17 | retrieval/search_ab.py:221::rankings | da/(median_a+epsilon); db/(median_b+epsilon) | test_euclidean_not_squared_and_weighted_median_formula | EXACT | Không cộng khoảng cách thô; giữ công thức. |
| AB05 — Mẫu20000 cặp uniform, seed42, đại diện cho kho | 17 không chốt sampling | retrieval/search_ab.py:151::representative_pairs | sample không hoàn lại từ sorted unordered i<j | 20k IDs tái lập; CFD/CFD4880,CFD/HF10073,HF/HF5047 | UNVERIFIED | Thuật toán hiện tại tái lập, chưa có phê duyệt riêng seed/count hay chứng minh đại diện cho mọi nhóm. |
| AB06 — Giá trị ε median | 17 không chốt trị số | retrieval/search_ab.py:173::calibrate | epsilon=1e-8, đã lưu rõ | median_params.json; independent weighted formula test | UNVERIFIED | Đây là quy ước hiện có, không nhận là trị số do PDF quy định; không tự đổi trong audit. |
| AB07 — Tổng trọng số không âm và bằng1 | 17 | retrieval/search_ab.py:215::validate_weights | wa,wb≥0, finite; abs(sum−1)≤1e-12 | old AB weight tests; scalar fusion oracle | EXACT | Công khai tolerance float1e-12; không tối ưu theo Top-5. |
| AB08 — Thử nghiệm hai bộ A=.5,B=.5 | 17; yêu cầu phiên trước | retrieval/search_ab.py:349::main | D=.5*normalizedA+.5*normalizedB | results.json; verify_b_ab; yêu cầu người dùng trước | APPROVED IMPLEMENTATION DETAIL | Giữ nhãn experimental, không gọi fusion chính thức bốn bộ. |
| AB09 — Lưu/tái sử dụng median và nhận ra calibration sai phiên bản | 17; yêu cầu phiên trước | retrieval/search_ab.py:173::calibrate | fingerprint vectors/stats/metadata + hash pairCSV + saved median | old AB stale-cache/tamper tests; current fingerprints verified | EXACT | Sửa A/B phải tạo calibration phiên bản mới; không tái dùng median cũ. |
| AB10 — Lưu dA,dB,normalizedA,normalizedB và D, xếp tăng dần | 17–18 | retrieval/search_ab.py:221::rankings | lexsort(filename,score); result fields đủ | 3 ranking modes tái lập trên query00001; CSV/JSON | EXACT | Đúng số học cũ không chứng nhận A/B toàn pipeline tuân thủ. |
| AB11 — Self-match của ảnh truy vấn | 18 không chốt thuật toán | retrieval/search_ab.py:262::identify_query | SHA256→IDs, loại ID; PNG mã hóa lại không tự nhận trùng | existing AB tests; query statuses; new_query original byte hash khác | UNVERIFIED | Quy ước đã công khai, không phải yêu cầu danh tính pixel/person trong PDF; không sửa heuristic. |
| AB12 — Thiếu B không zero-fill và xử lý rõ | 17; yêu cầu phiên trước | retrieval/search_ab.py:290::query_vectors | common1437; HF00209 query chỉ A-only, B/AB rỗng | missing query + missing worker no vector; all candidate IDs | EXACT | Giữ trạng thái thiếu, không tự đổi trọng số. |
| AB13 — Query dùng đúng extractor/stats, tương thích hai venv | 17; yêu cầu phiên trước | retrieval/search_ab.py:275::run_worker | .venv311 A; .venv-uniface B; giao tiếp .npy | query_worker_verification.json: query A/B tái trích thật, exact legacy transform | EXACT | Không cài thư viện hoặc sửa pipeline. |
| AB14 — Calibration/ranking phải thuộc phiên bản A đúng công thức | 17 | retrieval/search_ab.py:126::load_gallery | Hiện fingerprint trỏ A std_safe cũ | legacy_dependency_register.json; A12 confirmed | DEVIATION | Sai lệch kế thừa A12, không đếm là nguyên nhân mới; đánh dấu mọi phụ thuộc trong audit register. |
| AB15 — Fusion chính thức bốn bộ A/B/C1/C2 | 16–18 | retrieval/search_ab.py:349::main | Chỉ có A+B experimental; C1/C2 chưa có implementation | source_inventory.json; EXPERIMENT string | UNVERIFIED | Ngoài phạm vi triển khai: không tạo hoặc sửa C1/C2 trong nhiệm vụ này. |
