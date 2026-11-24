# Fusion A150 + B144 + C1_236 + C2_324 — triển khai

Ngày **24/11/2026**, Asia/Saigon. Đã triển khai và chạy thực tế: **EXPERIMENTAL_EQUAL_WEIGHTS**.
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`, đã xác minh hash và đọc trực tiếp §2.5.1–2.5.3 bằng pypdf trong Python hệ thống.
Không coi cấu hình trọng số bằng nhau là trọng số do PDF chỉ định, không chứng nhận anatomy hoặc retrieval accuracy.

## Kết quả và liên kết dữ liệu

**1437 ảnh đủ bốn vector**, gồm710 CFD+727 HF; toàn dataset1438 vẫn giữ nguyên.
Một query đầy đủ có1436 candidate sau loại1 self theo image_id. Cùng candidate pool cho cả năm chế độ.

| Bộ | Feature version | Shape | Dtype | CFD | HF |
|---|---|---|---|---:|---:|
| A | `A150_report_v2.0.0` | 1438×150 | float64 | 710 | 728 |
| B | `B144_report_v2.0.0` | 1437×144 | float64 | 710 | 727 |
| C1 | `C1_LBP236_FULL_ROI_V04_v1` | 1438×236 | float64 | 710 | 728 |
| C2 | `C2_ROOT_HOG324_FULL_v1` | 1438×324 | float64 | 710 | 728 |

Chỉ `hf_merged_00209` thiếu B, lý do `hair:missing_empty(0<100)`. A/C1/C2 của ảnh này vẫn hợp lệ.
Query này trả `status=fusion_unavailable`, `missing_feature=missing_B`, không kết quả ở bất kỳ hàng so sánh nào;
không âm thầm triển khai fusion ba bộ. `gallery_intersection_count=1437`, `candidate_count=1437`,
`self_exclusion_count=0`, `ranked_candidate_count=0`: candidate_count là kích thước pool sau loại ID query,
không phải số kết quả đã tính khi query unavailable. Các truy vấn standalone cũ vẫn dùng bình thường.

Module mới `retrieval/fusion_four.py` dùng loader đã có để kiểm schema/stats, sau đó nối qua image_id.
A lấy a_row_index riêng; B/C1/C2 lấy feature_row_index riêng. Không zip hoặc ghép cùng vị trí hàng giữa các bộ.
Kiểm uniqueness ID/index, shape/dtype/finite, tập ID, filename, đường dẫn, SHA-256 nguồn và quan hệ a_row_index.
Mọi1438 ảnh nguồn được hash lại; B/source viết CFD/HF còn C1/C2 viết cfd/hf: chỉ so sánh source casefold,
không sửa metadata nguồn. Metadata đảo thứ tự vẫn nối đúng theo index từng bộ; B thiếu ở giữa không làm lệch hàng.

Policy SHA `18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798` pin55 file đầu vào/schema/manifests/stats/source và calibration cũ.
Các loader bổ sung xác thực dependency gốc (raw A, contract/codebook C1, spec/kernel C2). Sai hash/schema/version
hoặc intersection khác1437 đều dừng, không ép số liệu. C1 trial v0.2/C2 trial100 không được thay full gallery.
Policy có absolute paths cho snapshot Windows này; di chuyển/rebuild artifact cần một phiên bản fusion/calibration
mới được kiểm chứng, không sửa policy để cache cũ tiếp tục được dùng.

## Công thức và calibration

```text
dA  = sqrt(sum((Aq-Ai)^2))                          # normalized A150 v2
dB  = sqrt(sum((Bq-Bi)^2))                          # normalized B144 v2
dC1 = 0.5*sum((C1q-C1i)^2/(C1q+C1i+epsilon_C1))    # four independent L1 histograms
dC2 = sqrt(sum((C2q-C2i)^2))                        # global L2 Root-HOG324
normalized_k = d_k/(median_k+epsilon)
D = wA*normalized_A + wB*normalized_B + wC1*normalized_C1 + wC2*normalized_C2
```

`epsilon=epsilon_C1=1e-8`. Epsilon C1 khớp schema/spec LBP hiện hành; median epsilon kế thừa AB v2.
Trọng số mặc định `(0.25,0.25,0.25,0.25)`, hữu hạn, không âm; tổng1 với **atol1e-12,rtol0**.
Không tự chia lại trọng số; giá trị nằm trong tolerance được dùng nguyên, không ép tổng về1.
Tolerance AB median và oracle **atol1e-12,rtol1e-12** được khóa trong policy trước khi tính median/Top-5.
Khoảng cách only là raw metric tương ứng để so sánh, không phải một phần của công thức fusion khác.
Không L2 lại C1, Z-score lại C1/C2, cosine Root-HOG, Euclid thay Chi-square hoặc refit stats theo query.

| Bộ | Khoảng cách | Median đã lưu | Sai số max so với scalar trên20.000 cặp |
|---|---|---:|---:|
| A | Euclid | 16.441989840419168 | 7.1054273576010019e-15 |
| B | Euclid | 10.81430055226477 | 1.4210854715202004e-14 |
| C1 | Chi-square ×0.5 | 0.30520587913351654 | 2.2204460492503131e-16 |
| C2 | Euclid | 0.21819130381743668 | 5.5511151231257827e-17 |

Đọc/reuse calibration AB v2 bằng nhánh read-only, không tái fit hoặc ghi file A+B.
Giữ đúng **20.000 cặp ID và thứ tự**, từ AB v2, không sampling lại.
Pair IDs SHA `eb93d6da4ac56fcdc79a1fe66a12cacf754bd1b428acecaf302f2f3525926072`; mọi cặp thuộc giao1437 và là unordered nonself unique.
Recompute bốn khoảng cách trên cùng các cặp, lưu pair_id0…19999, hai image_id và bốn distance.
MedianA/B mới chênh AB v2 **0.0/0.0**. Median không phụ thuộc query; cache kiểm fingerprint/IDs/hash/version
và median so với CSV trước mỗi query. Không dùng AB hai-median như calibration bốn bộ.
Namespace mới `outputs/retrieval/fusion_ab_c1_c2_v1/calibration/`; không ghi đè calibration hoặc outputs cũ.

## CLI và output

`retrieval/search_fusion.py` hỗ trợ --image,--top-k,--weight-a,--weight-b,--weight-c1,--weight-c2,--output.
Chỉ gallery image_id, exact filename hoặc file có hash nguồn đã tồn tại. File đổi tên nhưng cùng bytes được map
về ID; hash trùng nhiều ID và tên không phân giải được thì từ chối. Tên ID đúng nhưng file bytes khác bị từ chối.
Không adapter ảnh mới, không giả ảnh mới aligned, không chạy detector hay thêm dependency.
Mọi phép tính ở .venv311 trên vector đã lưu; không gọi extractor A/B hoặc trộn .venv-uniface.

Sort tăng dần `(distance,image_id)`, loại self theo image_id, giữ duplicate vector khác ID nếu có.
CSV/JSON có mode,rank,ID,filename,source,bốn raw distance,bốn normalized distance,D,score riêng mode,
vector row indices. JSON có weights/medians/epsilon/pair hash/feature versions/calibration hash và candidate counts.
CSV mỗi query đầy đủ25 rows=5 mode×Top5. PNG năm hàng, sáu cột, nguyên pixel nguồn256×256,
mỗi hàng query+Top5. `top-k>5` lưu đủTopK CSV/JSON; hình vẫn Top5 theo yêu cầu so sánh.
Output dưới `outputs/retrieval/fusion_ab_c1_c2_v1/queries/<query_id>/`; --output chỉ thư mục con mới trong namespace này.
Mọi thư mục run/calibration đã tồn tại đều bị từ chối ghi đè. Query lại phải chọn --output tên mới.
Missing_B vẫn xuất CSV header0rows, JSON lý do và PNG báo unavailable, không chứa ảnh kết quả giả.

## Top-5 full fusion của cfd_final_00001.png

| Rank | Ảnh | dA | dB | dC1 | dC2 | D |
|---:|---|---:|---:|---:|---:|---:|
| 1 | cfd_final_00038.png | 11.311268707635 | 6.985326867075 | 0.073167494091 | 0.126457115553 | 0.538296454408 |
| 2 | cfd_final_00031.png | 13.513428773540 | 7.854466010267 | 0.060254840514 | 0.126752857262 | 0.581634447663 |
| 3 | cfd_final_00034.png | 13.501476005258 | 8.155747524706 | 0.075597733855 | 0.131376947373 | 0.606283457224 |
| 4 | cfd_final_00443.png | 12.567793513972 | 9.052218935522 | 0.090935237229 | 0.116819001244 | 0.608694041697 |
| 5 | cfd_final_00029.png | 11.740416532629 | 7.282024837326 | 0.146027263079 | 0.125811734743 | 0.610621929810 |

## So sánh năm chế độ trên cùng pool

### cfd_final_00001.png

| Chế độ | Top-5 theo thứ tự: filename (distance) |
|---|---|
| A | hf_merged_00136.png (8.837416381528); cfd_final_00336.png (8.885966327716); cfd_final_00382.png (9.392805515224); cfd_final_00312.png (10.575001074429); cfd_final_00502.png (10.709277159797) |
| B | cfd_final_00439.png (6.959676513697); cfd_final_00038.png (6.985326867075); cfd_final_00029.png (7.282024837326); cfd_final_00440.png (7.463745705506); cfd_final_00036.png (7.631354089981) |
| C1 | cfd_final_00429.png (0.050103653496); cfd_final_00757.png (0.052864582413); cfd_final_00686.png (0.054052967661); cfd_final_00439.png (0.055542644036); cfd_final_00462.png (0.056340935589) |
| C2 | cfd_final_00724.png (0.108779552421); cfd_final_00453.png (0.110432430634); cfd_final_00426.png (0.114284882695); cfd_final_00445.png (0.116672192870); cfd_final_00443.png (0.116819001244) |
| FUSION | cfd_final_00038.png (0.538296454408); cfd_final_00031.png (0.581634447663); cfd_final_00034.png (0.606283457224); cfd_final_00443.png (0.608694041697); cfd_final_00029.png (0.610621929810) |

[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00001/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00001/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00001/results.json).

### cfd_final_00069.png

| Chế độ | Top-5 theo thứ tự: filename (distance) |
|---|---|
| A | hf_merged_00443.png (5.802768782401); cfd_final_00592.png (6.731731747160); hf_merged_00494.png (7.061874926637); cfd_final_00213.png (7.307968450465); cfd_final_00278.png (7.352300096209) |
| B | cfd_final_00072.png (4.698668360785); cfd_final_00086.png (9.058056090274); cfd_final_00126.png (9.621999737723); cfd_final_00124.png (10.059857377336); cfd_final_00085.png (10.198264678849) |
| C1 | cfd_final_00072.png (0.057946145836); cfd_final_00258.png (0.065849660620); cfd_final_00205.png (0.068737062742); cfd_final_00184.png (0.072334255579); cfd_final_00283.png (0.072488134115) |
| C2 | cfd_final_00294.png (0.115955581536); cfd_final_00150.png (0.124052266249); cfd_final_00163.png (0.125964975273); cfd_final_00666.png (0.129891106137); cfd_final_00278.png (0.130184669210) |
| FUSION | cfd_final_00072.png (0.514484575774); cfd_final_00124.png (0.661486017940); cfd_final_00079.png (0.677560160494); cfd_final_00154.png (0.707019113962); cfd_final_00205.png (0.737890108135) |

[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00069/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00069/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/cfd_final_00069/results.json).

### hf_merged_00001.png

| Chế độ | Top-5 theo thứ tự: filename (distance) |
|---|---|
| A | hf_merged_00030.png (4.794145871799); hf_merged_00577.png (5.718433125788); hf_merged_00719.png (5.875493490954); hf_merged_00524.png (5.913185115047); hf_merged_00067.png (6.463303842859) |
| B | hf_merged_00565.png (2.895577742443); hf_merged_00002.png (3.157583670499); hf_merged_00330.png (3.249534582683); hf_merged_00033.png (3.263802046551); cfd_final_00719.png (3.783165518617) |
| C1 | hf_merged_00408.png (0.090548391171); hf_merged_00152.png (0.095828466696); hf_merged_00243.png (0.105497220974); hf_merged_00485.png (0.115777382728); hf_merged_00169.png (0.115878986777) |
| C2 | hf_merged_00524.png (0.130121423722); hf_merged_00319.png (0.137304874064); hf_merged_00486.png (0.142581400445); hf_merged_00500.png (0.144808546988); hf_merged_00621.png (0.145113277741) |
| FUSION | hf_merged_00152.png (0.540332830369); hf_merged_00030.png (0.541817390925); hf_merged_00319.png (0.547570327944); hf_merged_00511.png (0.574386871815); hf_merged_00017.png (0.586003006240) |

[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00001/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00001/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00001/results.json).

### hf_merged_00198.png

| Chế độ | Top-5 theo thứ tự: filename (distance) |
|---|---|
| A | hf_merged_00333.png (14.454630240536); hf_merged_00708.png (14.658781243593); hf_merged_00485.png (14.746536938292); hf_merged_00358.png (15.153763562385); hf_merged_00315.png (15.216349985527) |
| B | hf_merged_00079.png (5.894313737030); hf_merged_00012.png (6.040612459501); hf_merged_00455.png (6.059764097815); hf_merged_00041.png (6.133008876236); hf_merged_00310.png (6.669284340139) |
| C1 | hf_merged_00459.png (0.124144203608); hf_merged_00126.png (0.125887306239); hf_merged_00624.png (0.134828645572); hf_merged_00275.png (0.138625657639); hf_merged_00093.png (0.145551264441) |
| C2 | hf_merged_00530.png (0.186408266253); hf_merged_00297.png (0.193236418035); cfd_final_00637.png (0.198475057098); hf_merged_00496.png (0.199872561140); hf_merged_00197.png (0.200168746326) |
| FUSION | hf_merged_00275.png (0.853847093002); hf_merged_00135.png (0.886857881821); hf_merged_00298.png (0.895247880163); hf_merged_00496.png (0.903500680530); hf_merged_00259.png (0.910781323410) |

[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00198/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00198/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00198/results.json).

### hf_merged_00722.png

| Chế độ | Top-5 theo thứ tự: filename (distance) |
|---|---|
| A | hf_merged_00208.png (10.846602851010); hf_merged_00304.png (11.647818132911); cfd_final_00046.png (12.396058697184); hf_merged_00190.png (12.492702709612); hf_merged_00389.png (12.636934390671) |
| B | hf_merged_00688.png (16.593418012030); hf_merged_00678.png (18.996367554990); hf_merged_00547.png (18.996849962847); hf_merged_00643.png (19.239233405601); hf_merged_00546.png (19.700046289228) |
| C1 | hf_merged_00248.png (0.142214408448); hf_merged_00272.png (0.143747323080); hf_merged_00245.png (0.151181556676); hf_merged_00474.png (0.158408917841); hf_merged_00226.png (0.159234913227) |
| C2 | hf_merged_00062.png (0.181915367125); hf_merged_00557.png (0.189896634648); hf_merged_00458.png (0.190323116752); cfd_final_00584.png (0.191114608101); cfd_final_00216.png (0.195680349516) |
| FUSION | hf_merged_00474.png (1.101994556175); hf_merged_00208.png (1.103368316866); hf_merged_00227.png (1.122969730172); hf_merged_00304.png (1.168378158196); hf_merged_00505.png (1.179334535004) |

[PNG năm hàng](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00722/comparison.png) · [CSV](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00722/results.csv) · [JSON](../outputs/retrieval/fusion_ab_c1_c2_v1/queries/hf_merged_00722/results.json).

## Khác biệt so với A+B hai bộ

| Query | Top-5 A+B v2 (0.5/0.5) | Top-5 bốn bộ (0.25 mỗi bộ) | Số ID chung | Vị trí khác trên1436 ứng viên |
|---|---|---|---:|---:|
| cfd_final_00001 | cfd_final_00038, cfd_final_00029, cfd_final_00036, cfd_final_00044, cfd_final_00031 | cfd_final_00038, cfd_final_00031, cfd_final_00034, cfd_final_00443, cfd_final_00029 | 3 | 1430 |
| cfd_final_00069 | cfd_final_00072, cfd_final_00124, cfd_final_00154, cfd_final_00174, cfd_final_00079 | cfd_final_00072, cfd_final_00124, cfd_final_00079, cfd_final_00154, cfd_final_00205 | 4 | 1430 |
| hf_merged_00001 | hf_merged_00555, hf_merged_00501, hf_merged_00030, hf_merged_00719, hf_merged_00404 | hf_merged_00152, hf_merged_00030, hf_merged_00319, hf_merged_00511, hf_merged_00017 | 1 | 1426 |
| hf_merged_00198 | hf_merged_00190, hf_merged_00167, hf_merged_00358, hf_merged_00708, hf_merged_00485 | hf_merged_00275, hf_merged_00135, hf_merged_00298, hf_merged_00496, hf_merged_00259 | 0 | 1433 |
| hf_merged_00722 | hf_merged_00208, hf_merged_00304, hf_merged_00227, hf_merged_00708, hf_merged_00389 | hf_merged_00474, hf_merged_00208, hf_merged_00227, hf_merged_00304, hf_merged_00505 | 3 | 1427 |

A+B so sánh được tính lại read-only trên đúng vector/median AB v2 và cùng1436 candidate; không sửa output AB.
Chỉ CFD00001 có đối chiếu JSON AB cũ trực tiếp; các query còn lại là baseline tái tính, không giả có file cũ.
Khác thứ hạng không chứng minh cải thiện chất lượng; chưa có relevance labels hoặc đánh giá retrieval có thẩm quyền.

## Kiểm thử, bảo toàn và giới hạn

140 tests PASS,0 failure/error/skip:118 regression A/B/C1/C2 +22 fusion.
Oracle độc lập đọc trực tiếp source CSV/NPY, dùng math.fsum, không gọi production ranking làm expected.
Đủ20.000 cặp, bốn median,5×1436 candidate và cả năm thứ hạng đầy đủ khớp; fixture trọng số khác(.1,.2,.3,.4)
cũng khớp full ranking, không dùng fixture để tối ưu weights.
125 rows CSV/JSON,155 tile ảnh nguồn và150 strip nhãn/filename/distance khớp pixel.
Self distance bốn bộ=0; self exclusion/tie-break/ID permutation/invalid weights/missingB/hash/schema/version
và từ chối trial/calibration hai bộ đều có test. [Kiểm chứng chi tiết](audits/FUSION_AB_C1_C2_NUMERICAL_VERIFICATION.md).

Baseline **17876 file**, trước/sau **0 thay đổi hoặc thiếu**, gồm PDF,dataset,A/Bv2,
stats/ABcalibration,C1/C2full+trial,source cũ,SQLite và mọi output đã có trong baseline kế thừa.
Không ghi SQLite, refit gallery, sửa extractor/mapping/ROI/LBP/HOG, bổ sung vector hoặc chạy extraction batch.
Chỉ namespace fusion mới, module/test/oracle/script mới và hai báo cáo này được tạo.
Hash input trước toán học ở policy; hash toàn baseline trong evidence/baseline_before.json;
final_scope và created_files_manifest ghi bằng chứng cuối.

ROI C1 v0.4 là project-selected/provisional, không approved anatomy; không ghi ACCEPT vào hồ sơ con người.
A canonical478→68 và nose endpoints còn UNVERIFIED. C2 center-crop anatomy/alignment lịch sử chưa xác minh.
Dataset HF333/HF561 mặt phụ, HF722 tay che miệng vẫn là vi phạm đã biết; HF209 thiếu B là vấn đề feature
khác, không tự gán vi phạm dataset. Không suy person_id/tuổi/giới từ ngoại hình, không loại ảnh để làm đẹp Top-5.
Không tuyên bố100% toàn hệ thống tuân thủ, anatomy compliant hoặc fusion tốt hơn A+B khi chưa có bằng chứng.

## Hash

| Artifact | SHA-256 |
|---|---|
| retrieval/fusion_four_policy.json | `18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798` |
| retrieval/fusion_four.py | `24c7250c44a89ad117277e793f501b8886eb27400a7dc2c0d89471d6f623cd2b` |
| retrieval/search_fusion.py | `fea09c9bd6d28215df18a9e0457746e5f75fece3554db7b1c3a0a6a7b5bcc880` |
| retrieval/fusion_oracle.py | `7f791b27224936ee05cb348efd1de910f8fdd0fa41364bd63382abdd2ac6ad0f` |
| outputs/retrieval/fusion_ab_c1_c2_v1/calibration/median_params.json | `fbe5c728bf348af89dfcd7445d98bfcc6cf314339c68213460c18db6b2abc956` |
| outputs/retrieval/fusion_ab_c1_c2_v1/calibration/representative_pairs.csv | `d441a6447fccf1d7a6cfebf2427146710e0485a15d94df6a93fb579605053e82` |
| outputs/retrieval/fusion_ab_c1_c2_v1/evidence/verification.json | `eebd8f32bf9035b553fdef97bf8dcc6b13a85aa4df98c063c5dc4aa036708bc7` |
| outputs/retrieval/fusion_ab_c1_c2_v1/evidence/scalar_calibration_pairs.csv | `cd0323c6707fa4cb5e2878b3766e9b9adc7a706249c6fded180a50f4c6e7bd82` |
| outputs/retrieval/fusion_ab_c1_c2_v1/evidence/scalar_query_distances.csv | `aad01f1f908ca2852dca041946aad28fd4df2fbb37cc3a990aab787f9a4d965c` |
| outputs/retrieval/fusion_ab_c1_c2_v1/evidence/baseline_before.json | `e1e42af182c78832e405d5f9f6ce812b1e47c5a653d35471bde55bac1a39cf2b` |

Các hash file mới còn lại ở [created_files_manifest](../outputs/retrieval/fusion_ab_c1_c2_v1/evidence/created_files_manifest.json).

## Lệnh PowerShell thực tế đã chạy thành công

Tại repository root, sử dụng môi trường đã có, không cài thư viện. Đây là các lệnh lần chạy đầu;
không chạy lại calibration để overwrite. Khi rerun query thêm --output một thư mục mới trong queries.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.fusion_four --calibrate
foreach ($fusionQuery in @('cfd_final_00001.png','cfd_final_00069.png','hf_merged_00001.png','hf_merged_00198.png','hf_merged_00722.png','hf_merged_00209.png')) {
    .\.venv311\Scripts\python.exe -X utf8 -B -m retrieval.search_fusion --image $fusionQuery --top-k 5 --weight-a 0.25 --weight-b 0.25 --weight-c1 0.25 --weight-c2 0.25
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
.\.venv311\Scripts\python.exe -X utf8 -B scripts/verify_fusion.py
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_fusion_four.py -v
.\.venv311\Scripts\python.exe -X utf8 -B scripts/finalize_fusion.py
```
