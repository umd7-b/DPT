# Portrait Atlas — ứng dụng tra cứu cục bộ

Ứng dụng web chạy thật trên backend SQLite bốn bộ đã nghiệm thu. Chỉ đọc snapshot, không lưu lịch sử. Hỗ trợ gallery search và ảnh import tạm qua crop 256×256 rồi trích xuất thật A/B/C1/C2.

## Khởi chạy trên PowerShell

Tại `D:\TuNam4\portrait-retrieval`:

```powershell
& .\app\start.ps1 -Port 8765
```

Mở **http://127.0.0.1:8765/** trong Chromium. Dừng bằng `Ctrl+C`. Có thể chọn port khác qua `-Port`; chỉ bind `127.0.0.1`. Dùng đúng URL này thay vì `localhost` vì ứng dụng kiểm tra Host/Origin.

Không cần cài thêm dependency: dùng `.venv311` có NumPy/Pillow/OpenCV/MediaPipe và `.venv-uniface` có UniFace/ONNXRuntime hiện tại; web dùng `sqlite3`, `http.server`, HTML/CSS/JavaScript thuần. Không nâng cấp thư viện Computer Vision. Server này dành cho demo trên máy cục bộ.

## Chức năng

- Tổng quan 1.438 ảnh, 5.751 vector hợp lệ, 1 missing_B và pool so sánh 1.437 ảnh.
- Nhập ID/tên file hoặc chọn từ gallery có phân trang và lọc CFD/HF.
- A, B, C1, C2, Fusion và so sánh đồng thời năm chế độ; ảnh query, Top-5, rank, filename và score thực từ SQL.
- Bảng khoảng cách gốc/chuẩn hóa, chi tiết metadata nguồn và tọa độ mắt có role thực trong SQLite.
- Bốn trọng số Fusion mặc định 0,25; kiểm hữu hạn, không âm và tổng bằng 1 với atol `1e-12`. Không tự chia lại trọng số.
- HF00209 trả `fusion_unavailable`, không tạo kết quả hoặc fusion ba bộ.
- Giao diện desktop/mobile, dialog điều hướng bằng bàn phím, thông báo input/ảnh lỗi.
- Import PNG/JPEG/WebP bằng file picker hoặc kéo thả; crop vuông, kéo góc/di chuyển, zoom/pan, reset và xác nhận preview PNG backend 256×256 trước khi tìm kiếm.
- `.venv311` trích A/C1/C2, `.venv-uniface` trích B qua subprocess; dùng frozen stats/specs. Không thêm ảnh/vector query vào SQLite.

Trọng số mặc định là **EXPERIMENTAL_EQUAL_WEIGHTS**, không phải trọng số PDF bắt buộc. C1 ROI v0.4 chưa anatomy-approved; chưa có relevance ground truth để kết luận accuracy.

## Backend và tính bất biến

`app/server.py` gọi trực tiếp `database.four_feature.SqlFourGallery` và `database.four_feature.query(..., persist=False)`. Không parse terminal và không viết lại thuật toán. Các vector được đọc từ SQLite một lần khi khởi động, kiểm tra rồi giữ trong bộ nhớ; mỗi request mở connection chỉ đọc. Không đọc file NumPy để tìm kiếm.

Snapshot: `database/four_feature_v1/data/portrait_four_features_v1.sqlite3`, SHA-256:

```text
4d9b5436ac40209fe24b23c46657d00b3befafdbf2e40e37e4ce4f755ce9e2c7
```

Startup từ chối snapshot khác hash. Connection dùng `mode=ro` và `PRAGMA query_only=ON`; không có endpoint ghi nguồn hoặc lịch sử. Nếu snapshot thay đổi trong lúc chạy, request tìm kiếm bị từ chối để tránh dùng cache cũ.

Ảnh chỉ được phục vụ qua `/media/<image_id>` từ catalog đã xác minh và thư mục ảnh cố định. Kiểm SHA-256 ảnh trước khi trả bytes. Không nhận đường dẫn từ request, không static-serve toàn repository. Metadata dùng textContent, không dựng HTML từ nhãn nguồn.

## API

| Endpoint | Chức năng |
|---|---|
| `GET /api/overview` | Counts, medians, versions, read-only state và token request cục bộ |
| `GET /api/gallery?q=&source=CFD&offset=0&limit=24` | Danh sách ảnh và feature status, giới hạn 100 ảnh/trang |
| `GET /api/images/<image_id>` | Metadata thực, person label nguồn nếu có, audit eye coordinates |
| `GET /media/<image_id>` | Bytes PNG khớp hash catalog |
| `POST /api/search` | Tìm kiếm qua SQL API, trả cả năm mode; không persist |

POST cần `Content-Type: application/json`, header `X-Application-Token` lấy từ overview và cùng origin. Body ví dụ:

```json
{
  "image": "cfd_final_00001.png",
  "mode": "fusion",
  "top_k": 5,
  "weights": {"a": 0.25, "b": 0.25, "c1": 0.25, "c2": 0.25}
}
```

`mode`: `a`, `b`, `c1`, `c2`, `fusion`, `compare`. `top_k`: 1–20; UI dùng 5. Response giữ số float của backend, bổ sung `image_url` để trình bày. Không trả vector BLOB ra trình duyệt. Invalid input/weights trả 422, ảnh không biết/thiếu file trả 404, hash không khớp trả 409. Request sửa nguồn trả 405. HF00209 là response nghiệp vụ 200 với status unavailable và không có results.

## Kiểm thử

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s app/tests -p test_web.py -v
```

Đã chạy 190 tests: 14 HTTP tests mới + 176 regression hiện có, không skip. Có kiểm cố ý lỗi trên bản sao RAM/temp hoặc bằng interception trong test, không sửa dataset/snapshot.

`node app/tests/browser.mjs` kiểm Chromium qua CDP bằng Node 24 có sẵn. Cần server 8765 và Chromium có remote-debugging port 9224 với profile tạm riêng. Không điều khiển profile trình duyệt của người dùng. Đã kiểm 12 tình huống và chụp ảnh thật ở desktop 1600×1100, mobile viewport 390×844. Script dùng WebSocket/fetch của Node, không Playwright/Selenium hay npm install.

`python -m app.verify` là lệnh tạo evidence nghiệm thu lần đầu; từ chối ghi đè `verification.json` đã có. Muốn chạy lại kiểm thử thông thường, dùng unittest ở trên. Không xóa evidence cũ để giả một lần nghiệm thu mới.

## Bằng chứng

- [Desktop Fusion](evidence/screenshots/desktop_fusion.png)
- [So sánh năm chế độ](evidence/screenshots/five_mode_comparison.png)
- [Metadata thực](evidence/screenshots/image_metadata.png)
- [Missing B](evidence/screenshots/missing_B.png)
- [Mobile](evidence/screenshots/mobile.png)
- [Browser checks](evidence/browser_verification.json)
- [190 tests và baseline](evidence/verification.json)
- [Báo cáo triển khai](../docs/WEB_APPLICATION_IMPLEMENTATION_REPORT.md)

## Ảnh import tạm

Chọn **Import từ máy**, mở PNG/JPEG/WebP hoặc kéo thả vào khung. Chọn vùng vuông từ ảnh gốc sau EXIF; kéo khung/góc hoặc nhập X/Y/cạnh. Zoom/pan hỗ trợ quan sát. Nhấn **Confirm Crop**, kiểm tra ảnh query 256×256, rồi **Tìm kiếm**. Kết quả chỉ xuất hiện sau khi cả bốn extractor thật hoàn tất. Không có mặt/nhiều mặt bị từ chối; thiếu tóc/da trả `missing_B`, không zero-fill hoặc fusion ba bộ.

Preprocessing `EXIF_TRANSPOSE_RGB_INTEGER_SQUARE_PIL_BICUBIC256_v1`: EXIF transpose, decoded RGB không chuyển ICC/gamma, bỏ metadata màu trong PNG preview, alpha ghép nền trắng, tọa độ crop nguyên và resize Pillow bicubic cố định. Giới hạn 10 MiB, 16 triệu pixel, cạnh 8192, 8 phiên. Đây là các quy ước triển khai; crop thủ công không chứng minh alignment lịch sử. C1 anatomy vẫn PROVISIONAL.

Ảnh query lưu dưới UUID tại `app/runtime/uploads/` (Git ignore). Thay ảnh sẽ xóa phiên trước; server xóa các phiên của nó khi đóng bình thường. Janitor kiểm mỗi 30 giây và xóa phiên không bận sau 30 phút tính từ lúc upload. Sau crash, lần khởi động sau dọn folder có ownership marker hợp lệ và hết hạn; marker bận có thời gian chờ khoảng 80 phút để tránh xóa query còn chạy. Không xóa dataset. Evidence QA giữ riêng trong `app/evidence/external_v1/`, dùng ảnh CFD/HF sẵn có và fixture tổng hợp.

API bổ sung (POST cần token cùng origin):

| Endpoint | Body / chức năng |
|---|---|
| `POST /api/external/upload` | Bytes ảnh; Content-Type thực, X-File-Name URI encoded; trả UUID/kích thước ảnh sau EXIF |
| `POST /api/external/crop` | `{job_id,x,y,size,revision}`; trả preview PNG 256×256 và SHA-256 |
| `POST /api/external/confirm` | `{job_id,revision}`; chỉ xác nhận crop hiện tại |
| `POST /api/external/search` | `{job_id,mode,weights,top_k}`; trả 202, chạy extractor thật |
| `GET /api/external/jobs/<uuid>` | Trạng thái, lý do lỗi/thiếu và kết quả năm mode |
| `GET /api/external/media/<uuid>/source` | Ảnh nguồn đã EXIF/RGB, chỉ trong phiên |
| `GET /api/external/media/<uuid>/crop?revision=N` | Đúng PNG crop hiện tại được các worker đọc |
| `POST /api/external/discard` | `{job_id}`; xóa phiên tạm không bận |

Gallery vẫn dùng SQL API cũ. External search dùng vector query vừa trích và gallery/calibration đọc từ SQL, tái sử dụng `fusion_four.component_distances/combine`. Trùng SHA-256 của **PNG cuối** với ảnh gallery thì loại đúng ID; filename không quyết định self-match. Bốn vector bắt buộc cho Full Fusion; phiên bản này chưa hiển thị các mode riêng khi query thiếu một bộ.

Kiểm thử cập nhật:

```powershell
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.verify_external
& .\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_batch_uniface.py -v
```

Hai test UniFace được skip trong `.venv311` và chạy thành công trong `.venv-uniface`. Xem [báo cáo ảnh ngoài](../docs/EXTERNAL_IMAGE_SEARCH_IMPLEMENTATION_REPORT.md) và [hướng dẫn demo Windows](EXTERNAL_IMAGE_DEMO.md) để chạy browser QA/oracle. Các con số 190 tests/bằng chứng ở phần trên mô tả lần nghiệm thu gallery trước đây; các artifact đó giữ nguyên. Script browser cũ tạo evidence gallery cũ, không chạy đè khi kiểm tính năng mới.

Chưa triển khai đăng nhập, hosting Internet, alignment ảnh mới được chứng nhận hoặc lịch sử ghi CSDL. Không suy đoán person_id/tuổi/giới từ ảnh import.
