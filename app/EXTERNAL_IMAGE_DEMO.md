# Demo ảnh ngoài trên Windows

Ngày kiểm chứng: 2026-11-24 (Asia/Saigon). Không cài dependency mới. Cần hai môi trường đã có, model MediaPipe và UniFace đã khóa, snapshot SQLite và gallery tại đường dẫn được catalog xác thực.

## Khởi chạy

```powershell
Set-Location D:\TuNam4\portrait-retrieval
& .\app\start.ps1 -Port 8766
```

Mở `http://127.0.0.1:8766/`. Dùng đúng host 127.0.0.1. Nếu port đã được dùng, dừng đúng server cũ hoặc chọn port khác; ứng dụng dùng socket độc quyền trên Windows để tránh hai tiến trình cùng phục vụ một port. Nhấn Ctrl+C để dừng và dọn các phiên tạm của server.

## Các thao tác trình diễn

1. Ở **Gallery**, truy vấn `cfd_final_00001.png`; xem Fusion và So sánh năm chế độ.
2. Chọn **Import từ máy**. Chọn hoặc kéo thả PNG, JPEG hay WebP. Tên file không cần có trong SQLite.
3. Trong công cụ crop, kéo khung để di chuyển và kéo góc để đổi cạnh vuông. Có thể nhập X/Y/cạnh theo pixel ảnh gốc đã xử lý EXIF. Khung luôn nằm trong ảnh gốc. Zoom ± và Pan ảnh chỉ thay cách quan sát; Reset Crop trở về hình vuông lớn nhất ở giữa ảnh.
4. Kiểm tra preview **Ảnh cuối 256×256**, rồi nhấn **Confirm Crop**. Preview này là PNG backend dùng để trích xuất, không phải crop từ ảnh bị CSS scale.
5. Nhấn **Tìm kiếm**. Đợi trạng thái Extracting features, Searching và Completed; kết quả cũ bị xóa trong lúc xử lý. Bốn badge phải hợp lệ trước Full Fusion.
6. Xem Top-5 và bảng khoảng cách gốc/median-normalized. Chọn So sánh để xem năm chế độ. Đổi trọng số thành `0.1,0.2,0.3,0.4`, nhấn tìm kiếm lại. Tổng khác 1 bị từ chối.
7. Có thể dùng `hf_merged_00209.png` để trình diễn thiếu tóc: `missing_B` và `fusion_unavailable`, không có Top-5 giả. Ảnh không có mặt hoặc nhiều mặt bị từ chối rõ ràng.
8. Trở lại Gallery để kiểm tra truy vấn cũ vẫn giữ kết quả. Thay ảnh import sẽ xóa phiên trước; TTL còn lại và chính sách dọn sau crash được ghi trong README.

Crop vuông không chứng minh ảnh đã alignment hai mắt như dataset. C1 v0.4 được chủ dự án chọn, anatomy vẫn PROVISIONAL. Demo dùng ảnh chân dung thật; không suy đoán danh tính, tuổi hoặc giới từ ảnh.

## Chạy kiểm thử lại

```powershell
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.verify_external
& .\.venv-uniface\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_batch_uniface.py -v
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.tests.make_external_fixtures
```

Browser QA dùng Chrome có sẵn và Node 24, không npm/CDN. Khởi chạy server như trên; trong PowerShell khác:

```powershell
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --headless=new --no-sandbox --disable-gpu --disable-gpu-sandbox --in-process-gpu --no-first-run --no-default-browser-check --disable-background-networking --remote-debugging-port=9225 --user-data-dir=D:\TuNam4\portrait-retrieval\app\runtime\external-chrome about:blank
```

Trong PowerShell thứ ba:

```powershell
$env:PORTRAIT_BASE = 'http://127.0.0.1:8766'
$env:PORTRAIT_DEBUG = 'http://127.0.0.1:9225'
node .\app\tests\external_browser.mjs
node .\app\tests\external_crop_browser.mjs
& .\.venv311\Scripts\python.exe -X utf8 -B -m app.verify_external_numeric
```

Các cờ Chrome trên dành cho profile QA tạm trong môi trường kiểm thử hiện tại. Không dùng profile người dùng. `external_browser.mjs` từ chối ghi đè folder `browser_query` đã có: khi chạy lại sau lần nghiệm thu, đặt `$env:PORTRAIT_EVIDENCE` sang namespace mới trước khi tạo fixture/chạy QA. Không xóa evidence nghiệm thu để giả một lần chạy mới. Browser test đóng tab của nó; sau QA đóng đúng tiến trình Chrome/profile này và server của demo.

Evidence có ảnh/vector query thật, chỉ dùng fixture CFD/HF và dữ liệu tổng hợp của QA. Upload người dùng không được sao chép tự động vào evidence hoặc SQLite. Không chạy `browser.mjs`, `app.verify` hay các script trích full dataset cũ để kiểm tính năng mới: chúng thuộc các namespace nghiệm thu trước.
