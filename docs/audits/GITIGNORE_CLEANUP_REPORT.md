# Gitignore cleanup audit — Portrait Retrieval

Ngày **24/11/2026**, Asia/Saigon. Phạm vi: **chỉ sửa .gitignore và tạo báo cáo này**.

**Đã hoàn tất kiểm toán ignore; chưa xác nhận sẵn sàng phát hành GitHub hoặc clone là chạy ngay.**
Còn các việc ngoài phạm vi: README lỗi encoding, requirements rỗng, bảo vệ EOL của source pin SHA và hướng dẫn cấp phát/khôi phục asset.
Không xóa, di chuyển, untrack, stage, commit, push, fetch hoặc sửa remote. Không sửa source, dữ liệu hay artifact.

## 1. Trạng thái repository

- Repository: D:\TuNam4\portrait-retrieval.
- Branch main; HEAD b203d73, first commit.
- Remote hiện tại: https://github.com/umd7-b/DPT.git. Không thay đổi remote hoặc truy cập network.
- git ls-files chỉ có **README.md**. Toàn bộ source/config/báo cáo còn là untracked.
- Staged: **0 file**.
- Trước sửa: **14.741 untracked files** theo git ls-files --others --exclude-standard.
- Sau sửa, trước tạo báo cáo: **278 untracked files**, 3.191.068 bytes, **3,04 MiB**.
- Tính thêm báo cáo: **279 untracked**, tổng **280 files** nếu sau này track toàn bộ source eligible và README hiện có.
- Dung lượng source ước tính khoảng 3,1 MiB sau báo cáo; đây là bytes worktree, không phải kích thước Git pack/network push.

Trạng thái rút gọn sau sửa ignore, trước tạo báo cáo:

~~~text
?? .gitattributes
?? .gitignore
?? annotations/
?? app/
?? database/
?? docs/
?? features/
?? outputs/
?? requirements.txt
?? retrieval/
?? scripts/
?? shared/
?? src/
?? tests/
~~~

models/ không còn hiện vì model binary đã ignored. Các file vẫn tồn tại trên đĩa.

## 2. Kiểm kê và phân loại

Quét **15.221 files**, tổng **2.558.358.313 bytes (2,38 GiB)**, không tính Git, virtualenv và refactor backup.
.gitignore và báo cáo này được loại khỏi digest bảo toàn vì là hai file được phép thay đổi.
Không thấy symlink/junction trong cây được quét và không có lỗi đọc.
Dataset chính nằm ngoài repository; không di chuyển hoặc xóa.

| Nhóm local | Files | MiB |
|---|---:|---:|
| outputs/B_color | 10,955 | 1252.69 |
| outputs/C1_lbp | 334 | 160.50 |
| outputs/retrieval | 93 | 50.40 |
| docs/audits | 2,921 | 491.88 |
| docs/reports | 531 | 64.80 |
| database/four_feature_v1 | 23 | 215.33 |
| database/data | 2 | 53.80 |
| database/backups | 2 | 53.80 |
| database/restored | 2 | 53.80 |

Có **12.040 raster files** PNG/JPG: ảnh, masks, overlays, contact sheets, screenshots và charts.
Không đánh đồng tất cả với dataset gốc; không tự xác nhận quyền chia sẻ chúng.
Không còn raster file nào trong danh sách eligible sau cập nhật.

| Nhóm | Phân loại | Quyết định |
|---|---|---|
| features/, retrieval/, shared/, src/, scripts/, tests/ | TRACK | Giữ source, workers, oracle, tests |
| database/ source, schema, migrations, SQL examples | TRACK | Giữ adapter/import/query, không giữ data mặc định |
| app/ frontend/backend/static/launcher/tests/README | TRACK | Giữ toàn bộ phần chạy ứng dụng |
| docs/ Markdown, report source HTML và audit tools | TRACK | Giữ tài liệu bảo vệ và code tạo báo cáo |
| Codebook/ROI/spec/schema/policy/hash manifests nhỏ | TRACK/REVIEW | Exception tường minh; review đường dẫn local trước public |
| .gitattributes/.gitignore/README/requirements | TRACK | README và requirements có vấn đề cần sửa riêng |
| Virtualenv/cache/log/build/IDE state | IGNORE | Giữ local, không thay dependency manifest |
| Dataset/manual masks/receipts/landmarks/vector matrices | IGNORE + external assets | Dữ liệu lớn hoặc nhạy cảm |
| SQLite data/backup/restore/sidecars | IGNORE + external assets | Có metadata/vector chân dung |
| Model weights | IGNORE + REVIEW giấy phép | Cấp phát riêng, không tự upload |
| Screenshots/contact sheets/generated PDF/figures/debug evidence | IGNORE + REVIEW chia sẻ | Có thể chứa ảnh người thật |
| Reviewer annotations/per-image vertices/query outputs | IGNORE + external evidence | Không public mặc định, giữ trạng thái review |
| .env/private keys/credentials | SECRET | Quy tắc bảo vệ; chưa thấy file thực thuộc nhóm này |

Không gán “file cũ” là vô dụng. .refactor_backup/ tiếp tục ở local theo quy tắc cũ; lịch sử/backup vẫn cần bảo quản.

## 3. Quy tắc cũ và mới

Rule cũ chỉ bảo vệ virtualenv, pycache, refactor backup, SQLite/sidecars và Chromium profile:

~~~gitignore
.venv/
.venv-*/
.venv311/
.refactor_backup/
__pycache__/
*.py[cod]

# Local SQLite databases, snapshots, and journal/WAL sidecars.
*.sqlite
*.sqlite3
*.db
*.sqlite-*
*.sqlite3-*
*.db-*

# Generated browser profiles include extensionless SQLite files.
/docs/reports/_build/chrome_profile*/
~~~

Rule mới có **122 pattern không trùng lặp**, chia nhóm có comment:

1. Python: .venv*/ thay ba rule env cũ; thêm venv/env/tox/nox, caches test/type/lint/coverage/package/build.
2. IDE/OS/log/temp: .idea, .vs, DS_Store, Desktop.ini, log/temp/editor files. Thumbs.db được *.db bao phủ.
   Chỉ ignore .vscode/settings.json và workspace cục bộ; giữ launch.json/tasks.json/extensions.json eligible.
3. Secrets: .env/.env.* nhưng giữ .env.example; private key containers và credential directories.
   Hiện không có .env.example; không tạo file ngoài phạm vi.
4. SQLite: database files/sidecars, không ignore schema/migrations/source.
5. NumPy matrices và model weights; không chặn checksum/config text.
6. Dataset copies: các root dataset/datasets/dataset_HF_CFD_final, không loại src hoặc app/static.
7. Manual annotations và outputs: default external, mở lại parent directories trước whitelist file nhỏ cần thiết.
8. Evidence/review/report build: bỏ generated data/ảnh/PDF; giữ tools, Markdown, review software và topology/spec.
9. App/database runtime evidence: tách khỏi source/static; giữ authority.json phục vụ import SQL.

Không có rule global *.json, *.csv, *.png hoặc *.md.
**/outputs/** là default deny đã kiểm ngoại lệ, không dùng outputs/ đóng parent.**
Các exception !/outputs/**/ mở lại directory để ngoại lệ file có hiệu lực.

~~~gitignore
!/outputs/**/
!/outputs/**/*.py
!/outputs/**/schema.json
!/outputs/**/feature_schema.json
!/outputs/**/manifest.json
!/outputs/**/gallery_integrity.json
!/outputs/**/median_params.json
!/outputs/C1_lbp/roi_validation/nri_uniform_59_codebook.csv
!/outputs/C1_lbp/roi_remediation_v0_4/candidate_contract_v0_4.json
!/database/four_feature_v1/evidence/authority.json
~~~

docs/audits/evidence/landmark_mapping.csv có cả tọa độ x/y của ảnh đầu tiên, không chỉ mapping thuần:
để external cùng evidence. Mapping thuật toán478→68 vẫn giữ tại features/A_geometry/src/map_68_landmarks.py.
Chưa có checksum manifest riêng trong models/; rule không chặn manifest tương lai.
Hash model thực tế nằm ở phần external assets dưới đây, không tạo thêm file checksum ngoài phạm vi.

## 4. File nhỏ bắt buộc giữ

Đã kiểm14 paths bằng git check-ignore -q: đều tồn tại và exit1, nghĩa là **không ignored**.
Bảng là SHA-256 file, không nhầm với content hash nội bộ JSON.

| File | File SHA-256 hiện tại | Kết quả |
|---|---|---|
| outputs/C1_lbp/roi_validation/nri_uniform_59_codebook.csv | `7eb6a7a12b7374efb50d487f2e399b3475ef0e03594da35971bf083b0188ac94` | TRACK |
| outputs/C1_lbp/roi_validation/contract_v0_2.json | `6d014ac00707bc158e8970a971548ed847331df19faebd4078bfca62347720a6` | TRACK |
| outputs/C1_lbp/roi_validation/lbp_implementation_spec.json | `25fca0d0e4428229294dfb27cf0f4e75b702e8dc41b99344fd99e36f05d63e6b` | TRACK |
| outputs/C1_lbp/roi_remediation_v0_4/candidate_contract_v0_4.json | `7535c7ce88ae54f5564f8f9da6bfcad212d7049703afbd9ced850ac285db1f68` | TRACK |
| features/C2_hog/spec_v1.json | `e16394a661adba43088af4e8106eb14949b9fdf9c7ac155bc9796f097ae5967a` | TRACK |
| retrieval/fusion_four_policy.json | `18f4b7d92d6926cfef48030609a0bba6d529a5860db7ce836fb8a44620cf3798` | TRACK |
| database/migrations/001_four_features_v1.sql | `f48ee1916f66aebc7f91b8d3ce4a479d2d08091173f0306bcf6fa62eeff3fba2` | TRACK |
| features/A_geometry/src/map_68_landmarks.py | `06df4021268fbb7a5c2649c3b19d4d70c3fc6bad40ade192c129cde6eb6296bf` | TRACK |
| database/four_feature_v1/evidence/authority.json | `ea0b144ac265b33a130b16ecf7ac3ef110283616bcfcac8a7da621049261dfea` | TRACK |
| docs/audits/pre_c_evidence/native_mediapipe_topology.json | `86a172923e8d18919e3cb58d50efbeca7512ab1f2548f3cb155dc5378024db12` | TRACK |
| app/static/index.html | `68e3ca5a970e43f6d99b6a49783afff496722e0fe2121dd2a9aa86012cd6256a` | TRACK |
| app/static/app.js | `cd5a5276049aba22c5ef02c835277a2143d00d5680be4a7acd9a7e11b535fa70` | TRACK |
| app/static/styles.css | `263cbb948e4011bc31aae08b8f49ff64356aff82bcb282324d32d6ce7c76334d` | TRACK |
| app/static/favicon.svg | `6628f67bad87b6501fb44822281872d9449f3e4018dcbc7120c6e94c3bac5b5e` | TRACK |

**169 file mã nguồn/script** .py/.ps1/.mjs/.js/.css/.sql được kiểm tra: **0 bị ignore**.
Giữ source generator trong docs/reports/_build dù sản phẩm build bị loại.
Các README trong outputs vẫn eligible để hướng dẫn khôi phục.

## 5. Tracked cần untrack và Git LFS

Hiện chỉ README.md tracked, thuộc TRACK. Vì vậy:
- **Danh sách đề xuất git rm --cached rỗng**.
- Không có SQLite/model/vector/ảnh/secret tracked trong checkout hiện tại.
- Không có staged file cần bỏ stage.
- Không thực thi git rm --cached, git rm -r --cached, git add hoặc reset.

Remote history chưa được fetch/audit; kết luận trên chỉ áp dụng local refs/index hiện có.
Nếu một lịch sử khác từng chứa secret, cần thu hồi/rotate secret còn hiệu lực:
.gitignore hoặc git rm --cached không xóa chúng khỏi lịch sử. Không rewrite history/force push.

Ba file local >50 MiB, tất cả ignored; không có file local >100 MiB trong phạm vi repo đã quét:

| File | Bytes | Quyết định |
|---|---:|---|
| database/four_feature_v1/backups/portrait_four_features_v1.backup.sqlite3 | 70,639,616 | IGNORE |
| database/four_feature_v1/data/portrait_four_features_v1.sqlite3 | 70,639,616 | IGNORE |
| database/four_feature_v1/restored/portrait_four_features_v1.sqlite3 | 70,639,616 | IGNORE |

Danh sách eligible: **0 file >50 MiB, 0 file >100 MiB**, không binary model/NumPy/SQLite/PDF hoặc raster.
File eligible lớn nhất trước báo cáo: docs/refactor_inventory.json, 198.449 bytes.

Không cấu hình Git LFS. Chỉ cân nhắc LFS cho binary được phép chia sẻ, hoặc dùng private asset storage.
SQLite/ảnh/biometric cần quyền truy cập phù hợp; LFS không làm public data thành private.
Không tự upload model/dataset hoặc thêm LFS filters.

## 6. External assets và khả năng tái lập

### App demo tối thiểu

App gallery search không cần chạy lại extractor/model. Cần:
- Python3.11, NumPy2.4.6 và opencv-python5.1.0.95 tương thích môi trường hiện có.
- Snapshot SQLite **đúng byte/hash**, source đã pin đúng byte, ảnh gallery đúng catalog hashes.
- Layout paths hiện tại, hoặc một nhiệm vụ portability có version/nghiệm thu riêng.

Thiếu .venv311: app/start.ps1 báo thiếu interpreter.
Thiếu SQLite: PortraitService gọi digest khi startup gây FileNotFoundError, server chưa phục vụ UI.
SQLite khác hash: ValueError “SQLite snapshot differs from the accepted database; refusing startup”.
Thiếu ảnh: media endpoint404; bytes ảnh khác hash:409.
Không được tuyên bố “clone là chạy ngay”.

### Dataset, model và full pipeline

Dataset ngoài repo: D:\TuNam4\dataset_HF_CFD_final, **1438 PNG** trong images/.
metadata.csv SHA-256: 3bfc895e2d8121477df756c8f50d29f952ad7cd7c9c0e5cc5e13e82e4454b83d.
Không thấy symlink/junction đưa dataset vào repo. Cấp phát riêng theo quyền sử dụng,
không mặc định suy quyền public từ việc đang có file local.

UniFace cache ngoài repo: C:\Users\USER\.uniface\models\parsing_resnet18.onnx,
53.205.364 bytes, SHA-256: 0d9bd318e46987c3bdbfacae9e2c0f461cae1c6ac6ea6d43bbe541a91727e33f.
Môi trường .venv-uniface hiện có UniFace4.3.0/onnxruntime1.32.0/NumPy2.4.6/OpenCV5.1.0.95.
.venv311 có MediaPipe1.2.3 cho pipeline A. Không cài hoặc đổi package.
B parser yêu cầu verified local weights, code tắt download/thay thế khi hash không khớp.

Danh mục file cấp phát riêng, tất cả vẫn còn local:

| External artifact | Bytes | File SHA-256 |
|---|---:|---|
| database/four_feature_v1/data/portrait_four_features_v1.sqlite3 | 70,639,616 | `4d9b5436ac40209fe24b23c46657d00b3befafdbf2e40e37e4ce4f755ce9e2c7` |
| database/data/portrait_ab_v2_eye_metadata_v1.sqlite3 | 34,406,400 | `6fc6213286c715edf997ed9484ca1da8da0d07dff59e2c486375fd53e34f4396` |
| outputs/A_geometry/features_report_v2/features_A_normalized.npy | 1,725,728 | `8305c3679ca2896795e17ac6bcd3d849e55d47e1da5c353b814173c26fa07f39` |
| outputs/B_color/color_features_report_v2/features_B_normalized.npy | 1,655,552 | `4b2ed87a67e49e101e53d10d6f9eceb78ab782c49250bcbd9f356a52f82d53ba` |
| outputs/C1_lbp/full_v04/features_C1.npy | 2,715,072 | `34d26e5b862e012ca537a03fa313eb087b8e58495e37e1da817485276f109f97` |
| outputs/C2_hog/full_v1/features_C2.npy | 3,727,424 | `fb732b4c8bba3a95d8f2281f05dc2eb8c7d9b02d750521b327c6077190272419` |
| outputs/retrieval/fusion_ab_c1_c2_v1/calibration/representative_pairs.csv | 2,289,926 | `d441a6447fccf1d7a6cfebf2427146710e0485a15d94df6a93fb579605053e82` |
| outputs/retrieval/ab_report_v2/calibration/representative_pairs.csv | 1,400,327 | `299bb1ab910cdd86a75d51c5fea48257ae97e785977ea5ef7e09f7b17e09d39d` |
| outputs/retrieval/ab_experiment/calibration/representative_pairs.csv | 1,400,183 | `ef336687bcacf4c8f6bc509b63ec1c1fb48305f6521307bbb91597863fd4eb9f` |
| docs/audits/evidence/dataset_landmarks478.npz | 4,848,343 | `a21e4abce28354d3a1fe5541bf0d2b7ab6d4b6d1119207d3231471bcacf263ed` |
| models/face_landmarker.task | 3,758,596 | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |

Cấp phát cả stats NPZ, raw/post-stage B, masks/receipts, feature_rows/status, metadata, manifests và source proof
đi cùng từng directory version, không chỉ features_*.npy.
Cần đúng ba CSV20k pairs đã đóng băng khi kiểm chứng/calibration A+B/four-way; không tự sampling lại.
Archive478 landmarks và annotations/evidence/backup/trial cần cho audit/regression tương ứng.
PDF chuẩn ngoài repo: C:\Users\USER\Downloads\csdldpt.pdf,
SHA-256: 8d390cbdbf888e0e51870eb2708531598cfdab852a85e87ecdb7a9e8f1d70c80.

### Scripts có sẵn và phần chưa đủ

Có các bước A/B report_v2, C1 full_v04, C2 batch, fusion_four, database import_v2/four_feature import và app/start.ps1.
Chúng là các bước riêng, **không phải bootstrap/restore hoàn chỉnh cho máy mới**.
Một số gate cần historical baseline/source DB/saved landmarks/mask receipts/frozen pairs có sẵn.
Builder từ chối output đã có; không chạy vào namespace đã nghiệm thu.

requirements.txt hiện **0 byte**. Chưa có dependency lock, installer hoặc bundle restore trọn bộ.
Không tạo env mới hoặc pip install trong audit này.

Tạo lại SQLite không bảo đảm cùng file hash do created_at, UUID và bytes SQLite có thể khác.
App pin snapshot gốc: cấp phát đúng file đã nghiệm thu hoặc nghiệm thu phiên bản mới,
không sửa dữ liệu/tham số để ép hash. Có đủ assets nhưng đổi layout paths vẫn có thể không startup.

## 7. Rào cản cần xử lý ở nhiệm vụ riêng

**P1 — EOL và byte pin.** core.autocrlf đang true.
git check-attr text eol trả unspecified cho:
- features/C1_lbp/src/lbp236.py;
- features/C2_hog/src/root_hog.py;
- retrieval/fusion_four.py và retrieval/fusion_four_policy.json;
- outputs/C1_lbp/roi_remediation_v0_4/candidate_contract_v0_4.json;
- app/server.py.

database/four_feature.py có text=unset do .gitattributes.
Windows checkout có thể đổi LF/CRLF ở các file chưa bảo vệ, gây source/spec SHA mismatch.
Đề xuất mở rộng .gitattributes cho đúng source/spec đã pin, rồi kiểm byte qua checkout tách biệt.
Không sửa .gitattributes hoặc thay core.autocrlf toàn máy trong nhiệm vụ này.

**P1 — đường dẫn tuyệt đối.** app/server.py, shared/paths.py, database/store.py,
các pipeline và JSON policy/authority đang dùng D:\TuNam4/C:\Users\USER.
SQL chứa image_path tuyệt đối; SqlFourGallery tra fingerprint theo str(ROOT/path).
Root mới có thể gây KeyError/fingerprint mismatch. Chưa có .env/config portable mà các source này đọc.
Chỉ thêm .env.example không giải quyết được. Đề xuất path-resolution/config và artifact rebinding có version;
không sửa source, policy hoặc database hiện tại.

**P1 — README/dependencies.** README.md chứa14 byte NUL, có dấu hiệu đuôi UTF-16LE trộn vào UTF-8.
SHA hiện tại: e237b93526e0bfcdc42be7e5cc1200d35141a2b81d7fa368e72f2046cf1dbf7d, giữ nguyên.
requirements.txt rỗng; README gốc chưa là hướng dẫn phát hành đủ C1/C2/fusion/SQLite/App.
Đề xuất sửa encoding UTF-8, cập nhật hướng dẫn và dependency manifest khi được phép riêng.

**P2 — tài liệu assets.** Đề xuất docs/EXTERNAL_ASSETS.md hoặc tên tương đương:
gói App tối thiểu/full pipeline/audit, hash, quyền chia sẻ, paths, version và verify/restore.
Chưa tạo file đó vì chỉ được tạo báo cáo Git trong nhiệm vụ này.

**P2 — liên kết báo cáo.** Markdown/HTML vẫn tham chiếu ảnh/evidence/PDF bị ignored.
Cần private bundle hoặc bản tài liệu public được cho phép. Không sửa báo cáo cũ để che thiếu file.

## 8. Secrets, privacy và giới hạn

Không thấy filename private-key/credentials/.env thực trong cây được quét.
Quét text dưới8MiB cho PEM private keys và token dạng GitHub/AWS/service thường gặp:0 candidate.
Quét literal credential assignments trên danh sách eligible:0 candidate.
Không in giá trị secret, chỉ path/loại nếu có nghi vấn.

Không coi đây là chứng nhận “không secret” tuyệt đối: không quét nội dung env/package caches/Git objects,
binary hoặc mọi remote history. Vẫn cần review staged diff và quyền chia sẻ trước commit.
216 file text trong inventory có đường dẫn local; source/policy cần giữ được đánh dấu REVIEW về portability/quyền public.
Không sửa nội dung các file đã pin hash.

Ảnh/overlays/screenshots/landmark coordinates/manual annotations/SQLite đã tách khỏi Git candidates.
Không đổi reviewer approval hoặc kết luận anatomy/dataset/retrieval quality.

## 9. Kiểm tra thực tế và bảo toàn

Đã chạy read-only:
~~~powershell
git status --short
git branch --show-current
git ls-files
git ls-files --others --exclude-standard
git diff --cached --name-status
git diff -- .gitignore
git check-ignore -v <representative-path>
git check-ignore -q -- <representative-path>
git check-attr text eol -- <representative-path>
git diff --check
~~~

- git diff -- .gitignore không có patch vì file đang **untracked**; không stage chỉ để tạo diff.
  Rule cũ/mới được ghi ở phần3.
- git diff --check exit0; kiểm whitespace trực tiếp .gitignore/báo cáo vì chúng chưa tracked.
- 27 probe hiện có/giả định cho env, examples, VSCode/static/test fixtures, SQL và generated assets đều đúng.
  Probe giả định không tạo file.
- 14 critical paths eligible; 169 source/script không ignored; staged 0.
- Không chạy regression suite có tempfile cleanup vì nhiệm vụ cấm xóa file; smoke test chỉ đọc API.

Smoke test sau sửa ignore:PortraitService khởi tạo PASS.
CFD00001 FusionTop5 vẫn là cfd_final_00038,cfd_final_00031,cfd_final_00034,cfd_final_00443,cfd_final_00029.
HF00209 vẫn fusion_unavailable. SQLite hash4d9b5436…9e2c7 không đổi; lịch sử6 runs/125 results.
Không mở server persistent hoặc ghi query history.

**15.221 file / 2.558.358.313 bytes ngoài hai file được phép không đổi.**
Digest cây trước/sau, sort directory/file rồi hash path+SHA từng file:
08643b74065187bfb74cc068dc708cb3be199d5bb58e3fb24228f44eed2bc549.
Không tính .git, virtualenv và .refactor_backup vào digest; không dùng mutation vào các thư mục đó.
External dataset/model chỉ được đọc, không truy cập ghi.

.gitignore là thay đổi được phép nên historical baseline từng pin .gitignore cũ có thể báo mismatch.
Không sửa manifest/baseline cũ để che thay đổi; báo cáo cũ là bằng chứng snapshot lịch sử.

## 10. Quyết định cần chấp thuận trước phát hành

1. Cho phép sửa README/requirements và bổ sung bootstrap/restore/EXTERNAL_ASSETS ở nhiệm vụ riêng.
2. Cho phép mở rộng .gitattributes, kiểm SHA qua checkout mới.
3. Chọn layout hiện tại D:\TuNam4 hay một phiên bản portable có rebinding/nghiệm thu.
4. Chốt quyền public Markdown/HTML/hash manifests có paths/bảng kết quả; giữ dữ liệu chân dung/SQLite/model/evidence trong kênh phù hợp.
5. Chọn nơi cấp phát bundle; LFS chỉ dùng khi đã rõ quyền chia sẻ, không tự upload.
6. Sau review từng path, người dùng tự quyết định stage/commit/push. Không chạy git add . tự động.

**Trạng thái cuối: quy tắc ignore đã được kiểm tra, source/config quan trọng được giữ,
dữ liệu local không mất. Chưa xác nhận ready-to-push như một bản phát hành tái lập hoàn chỉnh.**
