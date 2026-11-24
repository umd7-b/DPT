# Fusion bốn vector — kiểm chứng số học độc lập

Ngày **24/11/2026**, Asia/Saigon. Đã triển khai và chạy thực tế: **EXPERIMENTAL_EQUAL_WEIGHTS**.
Nguồn cao nhất `C:\Users\USER\Downloads\csdldpt.pdf`, SHA-256
`8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80`, đã xác minh hash và đọc trực tiếp §2.5.1–2.5.3 bằng pypdf trong Python hệ thống.
Không coi cấu hình trọng số bằng nhau là trọng số do PDF chỉ định, không chứng nhận anatomy hoặc retrieval accuracy.

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

## Toàn bộ calibration

20.000/20.000 ordered pairs giữ đúng AB v2, cùng intersection1437, không tạo lại mẫu.
Oracle `retrieval/fusion_oracle.py` không import production retrieval; trực tiếp load metadata/vector theo index
riêng từng bộ. Euclid=math.sqrt(math.fsum(squared differences)); Chi-square=0.5*math.fsum(fractions),
median=sort rồi lấy hai phần tử giữa, không gọi production median/ranking tạo expected.
Lưu toàn20.000 khoảng cách scalar ở evidence/scalar_calibration_pairs.csv.
Median scalar vs stored maxabs=5.5511151231257827e-17; A/B vs AB v2=0/0.
Pair IDs SHA `eb93d6da4ac56fcdc79a1fe66a12cacf754bd1b428acecaf302f2f3525926072`; policy khóa trước phép tính `18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798`.

## Ranking và round-trip output

Năm query:CFD00001,CFD00069,HF00001,HF00198,HF00722. Mỗi query1436 candidate, loại1 self.
So sánh **toàn thứ hạng**1436 ở A-only/B-only/C1-only/C2-only/fusion, không chỉ Top5:khớp tất cả.
Đủ7180 bộ khoảng cách query-candidate độc lập ở evidence/scalar_query_distances.csv, kèm D_AB read-only.
Mỗi bộ gồm4 metric, normalized riêng vàD; maxabs error EuclidA=7.1054273576010019e-15,
B=1.4210854715202004e-14, C1=2.2204460492503131e-16,
C2=5.5511151231257827e-17, D=4.4408920985006262e-16.
Fixture unequal weights(.1,.2,.3,.4) kiểm thêm đủ1436 scores/full ranking, không phải weight selection.
Các median giữ nguyên qua query. Self-distance=0 ở cả4 metric; sort ties theo ID, không loại zero distance của ID khác.

125 CSV result rows khớpJSON và expected;155 image tiles khớp pixel nguồn (150 positive+5 query-only missingB).
150 strip nhãn/filename/distance được dựng lại từ metadata và số đã đối chiếu, khớp PNG.
PNG có5 hàng×(query+Top5),1640×1536 pixels. CSV giữfloat repr đủ round-trip, JSON allow_nan=False.
HF209 riêng:missing_B/fusion_unavailable,0 rows,1437 pool,0 self excluded,0 ranked;không zero-fill/redistribute.

## Tests thực tế

**140 tests PASS**,0 fail/error/skip,118 regression+22 fusion. Logs evidence/tests.log vàfinal_tests.log.
Final suite chạy sau review kiểm exact filename và loại test phụ thuộc output query có sẵn; arithmetic/ranking không đổi.
Unit tests dùng synthetic/temporary files cho lỗi, không sửa accepted artifact để test tamper.
Bao phủ negative/NaN/Inf/sum/shape weights, phép đo,epsilon,tie-break,permuted metadata,missing-middle-B,
duplicate/out-of-range index,bad shape/dtype/NaN,input/policyhash,query filehash,wrong schema/feature version,
wrong fingerprint/IDs/pair hash,corrupt median,trial C1v0.2,C2trial100,AB calibration dùng sai như four-way,
refuse overwrite vànamespace output. Full source signatures và manifests được loader kiểm thực tế.

## Bảo toàn

SHA-256 baseline17876 file đều khớp:0 changed,0 missing. PDF/dataset/source/stats/normalization/calibration
A+Bv2,SQLite,C1full/trial,C2full/trial,output cũ không đổi. Kiểm baseline cuối bằng read-only hash;
không chạy lại feature extractor/refit,không khởi tạo hoặc update DB. New-file manifest không bao gồm chính nó.
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

## Phạm vi kết luận

Đã chứng minh công thức §2.5.2–2.5.3 và liên kết/fingerprint trên snapshot bốn vector hiện tại.
Epsilon, numeric tolerances,weights0.25,20k retained pairs,sort ties,output layout và byte-identity query
là quy ước triển khai, không gán cho PDF các giá trị/cột file không được quy định.
Không có relevance labels để tuyên bố quality tăng;không chứng nhận anatomy của C1v0.4/C2crop,
mapping A hoặc khắc phục dataset chỉ từ số họcPASS. Review con người/PDF/dataset/SQLite giữ nguyên.
[Lệnh thực tế, Top5 năm chế độ và so sánh AB](../FUSION_AB_C1_C2_IMPLEMENTATION_REPORT.md).
