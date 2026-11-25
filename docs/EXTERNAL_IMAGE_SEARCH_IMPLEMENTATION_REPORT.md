# Import ảnh ngoài → crop 256×256 → truy vấn bốn bộ

Ngày kiểm chứng: **2026-11-24, Asia/Saigon**. Trạng thái: luồng thực tế đã chạy; gallery search tiếp tục dùng backend SQLite đã nghiệm thu. Không có thay đổi extractor, dataset, vector gallery, stats, calibration hoặc SQLite.

## 1. Phạm vi và nguồn chuẩn

Đã đọc source web stdlib `http.server`, các API/gallery/static assets, worker A/B cũ và v2, search/fusion/C1/C2, SQL API, cùng các khóa contract/spec/statistics. Tái sử dụng worker B **v2**, không dùng worker legacy với normalization v1. Không cài hay nâng cấp dependency.

PDF `C:\Users\USER\Downloads\csdldpt.pdf` có SHA-256:

```text
8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80
```

Mục 1.3 quy định ảnh 256×256, bicubic, landmark và alignment hai mắt; mục 2.4 quy định LBP/Root-HOG; mục 2.5 quy định các độ đo và median-normalized weighted fusion. Luồng mới chỉ áp dụng crop thủ công được xác nhận, **không chứng nhận đã tái hiện alignment lịch sử**. Không thay đổi PDF hoặc các quy ước đã khóa để cải thiện Top-5.

## 2. Thay đổi source

| File | Vai trò |
|---|---|
| `app/server.py` | Routes upload/crop/confirm/jobs/media/discard; giữ gallery SQL API; socket độc quyền trên Windows |
| `app/external_config.py` | Preprocessing version, giới hạn, TTL, model hash, namespace QA |
| `app/external.py` | Validate/decode/EXIF, crop backend, phiên UUID, queue worker, kiểm receipt/schema/stats, external query và cleanup |
| `app/external_worker.py` | Adapter A/C1/C2 thật trong `.venv311`, chia sẻ native478 của đúng query |
| `app/static/index.html`, `app/static/app.js` | Hai input modes, trạng thái query, kết quả và liên kết crop |
| `app/static/crop.js`, `app/static/crop.css` | Công cụ crop offline, preview từ backend, file picker và drag/drop |
| `app/tests/test_web.py` | Cập nhật hai assertion về capability upload có thật; 14 test gallery cũ vẫn chạy |
| `app/tests/test_external.py` | 14 test mới về crop/decode, extraction thật, số học, lỗi/missing, schema/model hash và TTL |
| `app/tests/external_browser.mjs`, `external_crop_browser.mjs` | QA Chromium/CDP thật, không thư viện tải thêm |
| `app/tests/make_external_fixtures.py` | Sinh fixture QA có truy vết, không sửa ảnh nguồn |
| `app/verify_external.py`, `verify_external_numeric.py`, `seal_external.py` | Hồi quy toàn bộ, oracle độc lập và đối chiếu baseline/hash |
| `app/README.md`, `app/EXTERNAL_IMAGE_DEMO.md` | API, chạy Windows, demo và cleanup |

`app/static/styles.css` không cần thay đổi. Các extractor trong `features/`, module retrieval/database, các report/evidence cũ, `.gitignore` và artifact nghiệm thu giữ nguyên. Không stage, commit hoặc push Git trong nhiệm vụ này.

## 3. Import và preprocessing

Nhận PNG, JPEG, WebP tĩnh. Kiểm actual decoder format và MIME, không dựa vào đuôi file. Giới hạn cấu hình: **10 MiB**, **16.000.000 pixel**, cạnh tối đa **8192**, tối đa **8 phiên**. Từ chối file hỏng, định dạng khác, ảnh nhiều frame, MIME không khớp và tên file chứa path/control characters. Filename chỉ dùng để trình bày; đường dẫn thực dùng UUID do server sinh.

Preprocessing version:

```text
EXIF_TRANSPOSE_RGB_INTEGER_SQUARE_PIL_BICUBIC256_v1
```

1. Decode, kiểm kích thước trước khi load đầy đủ, EXIF transpose.
2. RGB từ các giá trị decoder, không ICC/gamma transform; bỏ metadata màu khỏi PNG preview để browser/OpenCV đọc cùng RGB. Alpha được ghép nền trắng. Đây là **IMPLEMENTATION_DETAIL**, không phải quy tắc màu mới từ PDF.
3. Crop `(x,y,size,size)` nguyên trên ảnh gốc **sau EXIF**, trong biên ảnh. Ghi cả kích thước encoded/oriented và orientation.
4. Resize về 256×256 bằng `Pillow.Image.Resampling.BICUBIC`, lưu PNG. Bicubic tuân theo tên nội suy PDF; kernel Pillow/version là quy ước triển khai, không tuyên bố bitwise với resize/alignment lịch sử.
5. Preview lấy chính PNG backend. Confirm chỉ nhận revision hiện tại; request tìm kiếm bị từ chối nếu chưa confirm. Mỗi revision có thư mục vector riêng, tránh dùng lại vector cũ khi crop đổi.

Đối với RGB PNG 256², crop toàn ảnh, EXIF=1 và không có metadata màu cần loại, giữ nguyên bytes để nhận biết exact-byte gallery duplicate. Ngoài trường hợp đó, file cuối là PNG do backend tạo. Self-match dựa vào **hash PNG cuối**, không suy ra từ filename hay chỉ từ người trông giống nhau.

UI giữ tỷ lệ 1:1; kéo trong khung để di chuyển, kéo góc để đổi kích thước, có X/Y/cạnh, zoom ±, pan, reset, chọn lại ảnh và Confirm Crop. Zoom/pan chỉ đổi phép chiếu trên canvas; tọa độ crop vẫn theo ảnh nguồn. Không CLAHE/sharpen/contrast/beautification, không alignment ngầm. Không dùng crop từ canvas CSS làm query.

## 4. Bốn extractor thật và provenance

| Bộ | Thực thi | Dữ liệu/khóa giữ nguyên |
|---|---|---|
| A150 | `.venv311`, helper normalize/calculate_ratios trong `geometry_features.py`, `report_v2.transform` | 136 tọa độ +14 ratios, mapping68, raw float32, Z-score float64 `(raw-mean)/(sigma+1e-8)` |
| B144 | `.venv-uniface`, subprocess `retrieval.ab_query_worker_v2 --kind b` | UniFace raw skin1/hair17, min100, HS48/Lab12/Hue12 mỗi vùng, Lab24 stage rồi final144 stage |
| C1_236 | `.venv311`, kernel `lbp236.Extractor(V04Context())` | Cùng native478 như A, ROI v0.4 project-selected/PROVISIONAL, P8R2, `>=`, NRI59, L1 riêng bốn vùng, support21/min64/overlap/bit order/codebook nguyên trạng |
| C2_324 | `.venv311`, `root_hog.extract_c2` | ROI `bgr[32:224,48:208]`, grid4×4, cell40×48, gradient trung tâm, hard9 bins, block2×2 stride1, Root từng block, L2 toàn vector |

A cần native478 để chia sẻ cho C1, trong khi API cũ trả68. Adapter chỉ lắp raw150 bằng các helper đã kiểm chứng, không thay công thức. Thêm lượt kiểm số mặt với **cùng model IMAGE/cap5**; chỉ khi đúng một mặt mới chạy descriptor **IMAGE/cap1** giữ cách A cũ. Không dùng cap1 để khẳng định ảnh chỉ có một mặt. Count này là kết quả model, không phải chứng minh detector hoàn hảo.

Tất cả worker đọc cùng đường dẫn PNG cuối; kiểm hash ảnh trước/sau và SHA pixel BGR từ worker. B chạy bằng executable môi trường riêng; không cross-import UniFace vào MediaPipe. Hai worker có timeout 180 giây mỗi lượt; lỗi worker/model/schema không có fallback gallery vector.

Model MediaPipe SHA-256:

```text
64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff
```

UniFace `parsing_resnet18.onnx` SHA-256:

```text
0d9bd318e46987c3bdbfacae9e2c0f461cae1c6ac6ea6d43bbe541a91727e33f
```

Khóa C1 ROI content `c6d839d420e03555a5e34a5ae9c5b02a3a5e6a6e8e456310576c11215031bb39`; LBP spec `7c078058780fc0de21f0b02084822c7b5fabfb767d2db2a9e71faead5afa3851`; C2 spec `a568f2eaec4d54cbc72c2a80d49c371362248367ff88224c158f8c5aaa10f169`. Các receipt lưu hash stats A, hai stats B, model, kernel, codebook, ROI/spec và image. Schema của query phải khớp các FeatureVersions trong SQLite; hash stats phải khớp NormalizationStages. Không fit lại bất kỳ stats nào.

Môi trường kiểm chứng: Python3.11.9, NumPy2.4.6, OpenCV5.1.0.95; `.venv311` có MediaPipe1.2.3; `.venv-uniface` có UniFace4.3.0/ONNXRuntime1.32.0 CPU. Không nâng cấp/cài thêm thư viện hoặc tải model.

## 5. SQLite, khoảng cách và API

`PortraitService` vẫn xác thực snapshot SHA và tạo `database.four_feature.SqlFourGallery` bằng connection `mode=ro`, `query_only=ON`. External search dùng **vector query vừa trích** cùng các vector gallery/medians đã load từ SQL. Không parse output terminal, không đọc vector gallery NumPy để thay SQL và không insert query.

Tái sử dụng `fusion_four.component_distances` và `combine`: Euclid A/B/C2, Chi-square C1 có hệ số0.5 và epsilon1e-8; chuẩn hóa `d/(median+1e-8)` rồi tổng trọng số. Không nối854 chiều để tính Euclid. Trọng số mặc định mỗi bộ0.25 là cấu hình thử nghiệm; kiểm finite, không âm, tổng1 atol1e-12, không renormalize. Cùng pool giao1437 cho cả năm mode; sort `(distance,image_id)` tăng dần; loại ID trùng SHA cuối. Có1437 ứng viên cho crop mới,1436 khi có một exact-byte duplicate trong pool.

Medians giữ nguyên: A16.441989840419168, B10.81430055226477, C1 0.30520587913351654, C2 0.21819130381743668.

| Endpoint | Hợp đồng |
|---|---|
| `POST /api/external/upload` | Raw bytes; MIME và `X-File-Name` URI encoded; trả201 với UUID/source URL/kích thước |
| `POST /api/external/crop` | JSON `{job_id,x,y,size,revision}`; PNG256, crop metadata, hash |
| `POST /api/external/confirm` | JSON `{job_id,revision}`; từ chối revision cũ |
| `POST /api/external/search` | JSON `{job_id,mode,weights,top_k}`;202, xử lý nền |
| `GET /api/external/jobs/<uuid>` | Busy/status/features/missing reason/result/events |
| `GET /api/external/media/<uuid>/source` | RGB nguồn sau EXIF của đúng phiên |
| `GET /api/external/media/<uuid>/crop?revision=N` | PNG crop revision hiện tại |
| `POST /api/external/discard` | Xóa UUID tạm không bận |

POST dùng token ứng dụng, kiểm Host/Origin cùng127.0.0.1. Không có endpoint nhận path tùy ý. API gallery cũ và `/media/<image_id>` không thay thuật toán. UI hiển thị original, query256, filename, feature statuses, selected mode/weights, Top-5 và thành phần raw/normalized. Kết quả cũ bị xóa khi input/crop/search đổi.

Không mặt/nhiều mặt: Failed, B không chạy và không có landmarks giả. Thiếu B: `missing_B`, lý do/pixel count thực, `fusion_unavailable`; không vector B/zero-fill, không reweight. Phiên bản này chưa hiển thị kết quả riêng nếu thiếu một bộ; mọi mode trả danh sách rỗng thay vì gắn nhãn fusion sai. Missing C1/C2 cũng giữ nguyên lý do thật từ extractor.

## 6. Thực nghiệm và oracle

**Mẫu1:** xuất lại `cfd_final_00001.png` với PNG metadata khác, filename `not-in-gallery.png`. Không trùng bytes catalog; đi qua model/worker thật. Bốn vector150/144/236/324 float64 hữu hạn. Trong môi trường hiện tại, max absolute difference so với đúng vector gallery tương ứng là **0 cho cả bốn bộ**; đây là quan sát cùng pixel/model/runtime, không cam kết bitwise cho mọi môi trường hay alignment khác. Cả1437 candidate được tính bằng scalar oracle; năm Top-5 khớp hoàn toàn.

**Mẫu2:** thao tác chuột thật trên Chrome cắt từ ảnh đó, tọa độ **x13,y6,size221**, resize256. File query/bytes/pixel mới không phải gallery entry, không có image_id query. Tất cả bốn vector được trích thực từ crop; không thay thế bằng vector gallery. Pixel BGR của ảnh hiển thị trong Chrome và worker có cùng SHA:

```text
9c893e0745cfb4492a787059f26d70e7ba66ca390142e2af65acca46709eedf2
```

Top-5 Fusion mặc định thực tế của crop này:

| Rank | Ảnh | dA | dB | dC1 | dC2 | D |
|---|---|---:|---:|---:|---:|---:|
|1|cfd_final_00001.png|2.781964027326|1.524315907178|0.042884240109|0.168292071232|0.305491693011|
|2|cfd_final_00038.png|11.876080301956|6.392967229327|0.114204347832|0.170423462186|0.617180490217|
|3|cfd_final_00029.png|11.546932418706|7.185704666810|0.128275313916|0.175004371994|0.647276472333|
|4|cfd_final_00031.png|13.339053384647|7.674777240614|0.082974839802|0.183005817012|0.657893211426|
|5|cfd_final_00050.png|14.042776175205|7.920425318955|0.085094437705|0.177724287779|0.669956790080|

Ảnh gốc vẫn có thể đứng đầu vì **crop đã khác bytes**. Không dùng filename để loại nó. Đây là fixture chân dung thật dẫn xuất từ CFD, không chứng minh truy hồi một danh tính chưa xuất hiện trong gallery hoặc accuracy trên ảnh ngoài tự nhiên chưa kiểm.

Oracle độc lập chạy trên cả hai mẫu: A sigma+epsilon và hai stage B sai số0; C1 dùng full-image polygon scan, support21 và scalar bilinear/codebook/histogram, counts chính xác và vector sai số0; C2 scalar Root-HOG maxabs **1.3877787807814457e-17**. Counts/eligible centres C1 theo thứ tự bốn vùng: mẫu1 **4632/3410/3751/3952**, crop **7160/4678/5243/5484**. Bốn histogram L1 sai số floating-point tối đa1.11e-16. Scalar Euclid/Chi-square/median/fusion trên1437 ảnh: max distance error **3.552713678800501e-15**, năm Top-5 đều khớp.

## 7. Kết quả kiểm thử

| Suite | Kết quả thực tế |
|---|---|
| `tests` |196 cases:194 PASS,2 skip chỉ vì môi trường không có UniFace |
| `database/tests` |36 PASS, gồm SQL/constraints/vector round-trip/query/backup-restore |
| `app/tests` cuối cùng |28 PASS =14 gallery cũ +14 external mới |
| `test_batch_uniface.py` trong `.venv-uniface` |8 PASS, bao gồm chính hai test đã skip ở trên |
| Chrome external end-to-end |8 nhóm kiểm tra PASS, không JavaScript exception |
| Chrome crop cases |8 nhóm PASS,7 định dạng/kích thước,28 vị trí sát bốn mép, drag/drop và viewport390px không tràn ngang |

Tổng **260 test Python phân biệt đã PASS** khi gộp hai môi trường;6 test UniFace đã chạy lặp trong cả hai môi trường. Không giấu hai skip ở interpreter sai dependency. Các suite có negative tests trên temp/RAM/query receipt riêng; không sửa baseline để tạo lỗi.

Đã kiểm thực: PNG/JPEG/WebP, EXIF6, landscape/portrait/square/large/small, crop biên, strict integer bounds, preview byte hash, resize/move bằng chuột, zoom/pan, reset, confirm revision, trạng thái và clear Top-5, noface,2faces, missing hair, sai model/schema/weights, exact bytes vs filename, TTL cleanup, scalar distances/ranking, đổi trọng số và lặp truy vấn. Gallery sau external search giữ nguyên năm Top-5 SQL baseline.

Browser bằng Node24 built-ins/CDP, **Google Chrome158.0.8127.38 trên Windows**, desktop1600×1100, mobile390×844. Có8 screenshot thật trong `app/evidence/external_v1/screenshots/`. Brave thử ban đầu có canvas readback lệch tối đa1 mức ở266 giá trị kênh; lần đó không dùng để chứng nhận pixel parity. Chrome đã chứng minh parity chính xác. Không thay crop/kernel để làm test đạt.

## 8. Bất biến và dữ liệu tạm

Snapshot SQL giữ SHA:

```text
4d9b5436ac40209fe24b23c46657d00b3befafdbf2e40e37e4ce4f755ce9e2c7
```

Trước/sau đối chiếu **18.051 file được bảo vệ**, bao gồm PDF, dataset, extractor/mapping, artifact A/B/C1/C2, calibration, SQLite/backup và evidence/query cũ: **không đổi**. Snapshot vẫn1438 ảnh,5751 vector valid và1missing_B;4medians; history6runs/125results không tăng. Không refit, không full-dataset extraction, không update bảng/vector/calibration.

Query tạm dùng UUID dưới `app/runtime/uploads/` đã ignore. Một queue extraction, tối đa8phiên; thay ảnh xóa phiên cũ, đóng server bình thường chờ worker rồi dọn phiên thuộc nó. Janitor mỗi30giây, TTL30phút từ upload cho phiên không bận. Sau crash chỉ dọn thư mục UUID có ownership marker hợp lệ; marker bận chờ khoảng80phút để tránh xóa tiến trình khác còn chạy. Đường dẫn cleanup phải resolve dưới đúng runtime; không dọn source/dataset. Không ghi history SQL. QA chủ động sao chép fixture vào namespace evidence riêng; production upload không tự lưu lâu dài vào evidence.

`protected_before.json`, `protected_after.json`, `allowed_source_before.json`, `regression_tests.json`, `app_final_tests.json`, `uniface_tests.log`, `browser_verification.json`, `crop_browser_verification.json`, `numerical_verification.json`, receipts/vectors thực và `final_manifest.json` nằm trong `app/evidence/external_v1/`. Evidence/runtime bị ignore; không đưa ảnh/vector/SQL lên Git.

## 9. Lệnh PowerShell đã chạy thành công

Tại `D:\TuNam4\portrait-retrieval`:

```powershell
& .\app\start.ps1 -Port 8766
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.verify_external
& .\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s app/tests -v
& .\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_batch_uniface.py -v
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.tests.make_external_fixtures
node .\app\tests\external_browser.mjs
node .\app\tests\external_crop_browser.mjs
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.verify_external_numeric
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.seal_external
```

Lần `app.verify_external` ghi app27cases; sau bổ sung kiểm alpha/metadata, lần chạy app/tests cuối có28PASS và log riêng xác nhận. Chrome9225/profile QA tạm đã được khởi chạy để kiểm browser; hướng dẫn đầy đủ và namespace chạy lại tại [EXTERNAL_IMAGE_DEMO.md](../app/EXTERNAL_IMAGE_DEMO.md). Port8765 ban đầu có server cũ cùng bind; đã bổ sung socket exclusive cho phiên bản mới và dùng8766 khi QA.

## 10. Giới hạn còn lại

Không tuyên bố100% compliance toàn hệ thống: alignment ảnh mới chưa được chứng minh tương đương dataset; mapping A và anatomy C1 v0.4 giữ các giới hạn UNVERIFIED/PROVISIONAL của audit trước. Người dùng chọn crop; detector/parser có thể thất bại và chất lượng ảnh ngoài chưa có relevance ground truth. Không suy đoán nhãn nhân khẩu học hoặc person_id. Chưa hỗ trợ kết quả partial khi thiếu một bộ, persistence lịch sử, đăng nhập hoặc hosting Internet. Luồng Import → crop → extractor thật → SQLite-gallery similarity search đã chạy với ảnh thật và có bằng chứng số học; không có mock search hay Top-5 hardcode.
