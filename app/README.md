# Portrait Atlas — ứng dụng tra cứu cục bộ

Ứng dụng web chạy thật trên backend SQLite bốn bộ đã nghiệm thu. Chỉ đọc snapshot, không lưu lịch sử và không xử lý ảnh mới.

## Khởi chạy trên PowerShell

Tại `D:\TuNam4\portrait-retrieval`:

```powershell
& .\app\start.ps1 -Port 8765
```

Mở **http://127.0.0.1:8765/** trong Chromium. Dừng bằng `Ctrl+C`. Có thể chọn port khác qua `-Port`; chỉ bind `127.0.0.1`. Dùng đúng URL này thay vì `localhost` vì ứng dụng kiểm tra Host/Origin.

Không cần cài thêm dependency: `.venv311`, NumPy hiện có, `sqlite3`, `http.server`, HTML/CSS/JavaScript thuần. Không nâng cấp thư viện Computer Vision. Server này dành cho demo trên máy cục bộ.

## Chức năng

- Tổng quan 1.438 ảnh, 5.751 vector hợp lệ, 1 missing_B và pool so sánh 1.437 ảnh.
- Nhập ID/tên file hoặc chọn từ gallery có phân trang và lọc CFD/HF.
- A, B, C1, C2, Fusion và so sánh đồng thời năm chế độ; ảnh query, Top-5, rank, filename và score thực từ SQL.
- Bảng khoảng cách gốc/chuẩn hóa, chi tiết metadata nguồn và tọa độ mắt có role thực trong SQLite.
- Bốn trọng số Fusion mặc định 0,25; kiểm hữu hạn, không âm và tổng bằng 1 với atol `1e-12`. Không tự chia lại trọng số.
- HF00209 trả `fusion_unavailable`, không tạo kết quả hoặc fusion ba bộ.
- Giao diện desktop/mobile, dialog điều hướng bằng bàn phím, thông báo input/ảnh lỗi.

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

Ảnh mới, upload, trích xuất, đăng nhập, triển khai Internet và lịch sử ghi CSDL đều chưa được triển khai trong ứng dụng này. Không có nút Upload giả.
