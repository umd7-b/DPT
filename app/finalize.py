"""Write web delivery evidence and report without changing any accepted artifact."""
from pathlib import Path
import re

from database import four_feature as four
from database import store
from shared.report_v2 import read_json,write_json

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'app/evidence'


def main():
    if (E/'created_files_manifest.json').exists():raise FileExistsError('Web delivery already sealed')
    result=read_json(E/'verification.json');browser=read_json(E/'browser_verification.json')
    assert result['status']==browser['status']=='PASS'
    baseline=read_json(E/'baseline_before.json')
    changed=[p for p,h in baseline.items() if not Path(p).is_file() or store.digest(p)!=h]
    assert not changed,changed
    assert result['database_sha256']==store.digest(four.DEFAULT_DB)
    screenshots='\n'.join(f'- [{name}](../app/evidence/screenshots/{name})' for name in browser['screenshots'])
    report=fr'''# Portrait Atlas ? ?ng d?ng web tra c?u b?n b? t? SQLite

Ng?y **24/11/2026**, Asia/Saigon. ?? tri?n khai, ch?y server, ki?m th? Chromium v? ch?p giao di?n th?c t?.
?ng d?ng n?m trong `app/`, ch? bind `127.0.0.1`. Gi? nguy?n PDF, dataset, extractor, vector, stats,
normalization, calibration, tr?ng s? m?c ??nh, SQLite ?? nghi?m thu v? k?t qu? Top-5 c?.

## Ki?n tr?c

?? ??c source database/four_feature.py, database/schema.sql, b?o c?o t?ch h?p CSDL,
retrieval/fusion_four.py, retrieval/search_fusion.py v? b?o c?o fusion. SQLite th?c t? c?
1438 ?nh; 5752 b?n ghi vector g?m 5751 valid v? 1 missing_B; 1437 ?nh ?? b?n b?, 4 median v? 5 ch? ??.

Dependency check ? .venv311 Python 3.11.9: ch?a c? Flask/FastAPI/Uvicorn/Playwright/Selenium.
Ch?n HTTP server chu?n Python v? HTML/CSS/JavaScript thu?n. Kh?ng c?i package ho?c n?ng c?p th? vi?n CV.

```text
Chromium UI -> app/server.py -> database.four_feature.query(persist=False)
                           -> SqlFourGallery ??c SQLite
                           -> fusion_four: component_distances / combine / rank_indices
```

Kh?ng parse terminal ho?c vi?t l?i thu?t to?n. Vectors/calibration ???c ??c v? x?c minh t? SQL khi startup,
r?i cache trong RAM. M?i request m? connection ch? ??c m?i. Kh?ng d?ng file NumPy thay cho gallery SQL.
Response ch? b? sung URL ?nh; kh?ng s?a th? h?ng ho?c kho?ng c?ch c?a backend.

## API

| Endpoint | Ch?c n?ng |
|---|---|
| GET / | HTML/CSS/JS c?c b? |
| GET /api/overview | Counts, median, phi?n b?n, read-only state, token request |
| GET /api/gallery | T?m ID/t?n file, l?c CFD/HF, ph?n trang t?i ?a 100 ?nh |
| GET /api/images/<image_id> | Metadata th?t, person label ngu?n n?u c?, t?a ?? m?t audit |
| GET /media/<image_id> | Bytes PNG kh?p hash catalog |
| POST /api/search | image, mode, top_k, weights; tr? c? n?m ch? ?? v? kh?ng persist |

POST c?n JSON v? X-Application-Token t? overview, c?ng origin. UI d?ng Top-5; API gi?i h?n Top-K 1?20.
Sai input/weights:422; ?nh kh?ng bi?t/thi?u file:404; hash mismatch:409; route ghi ngu?n:405.
HF00209 tr? HTTP200 v?i status fusion_unavailable, missing_B v? kh?ng c? k?t qu?.
Web ch? nh?n gallery ID/exact filename, kh?ng nh?n ???ng d?n file ho?c upload.

## SQLite v? b?o v? d? li?u

Snapshot: `{four.DEFAULT_DB.relative_to(ROOT).as_posix()}`.
SHA-256: `{result['database_sha256']}`.

Startup t? ch?i snapshot kh?c hash. Connection d?ng `mode=ro` v? `PRAGMA query_only=ON`;
query lu?n `persist=False`. Kh?ng t?o working DB v? kh?ng l?u l?ch s?. S? l?ch s? v?n l?
6 FourFeatureRuns v?125 FourFeatureResults sau m?i request/test. Snapshot ??i mtime/size khi ?ang
ch?y th? t? ch?i query ?? tr?nh cache stale.

Ch? ph?c v? ?nh c? image_id trong catalog. Path l?y t? Images, resolve ph?i n?m trong th? m?c ?nh
?? x?c minh; ki?m SHA-256 bytes tr??c khi tr? PNG. Kh?ng static-serve repository, PDF ho?c SQLite.
Ch?n path traversal, encoded/double-encoded traversal v? ???ng d?n Windows t?y ?.
Host/Origin loopback, token request, content type, body size v? JSON finite ??u ???c ki?m tra.
Metadata hi?n th? b?ng textContent, kh?ng d?ng HTML t? nh?n ngu?n.

## Giao di?n v? lu?ng s? d?ng

Dashboard l?y counts t? API. Ch?n query b?ng ID/t?n file, autocomplete ho?c gallery dialog c? ph?n trang.
Query v? Top-5 d?ng media URL g?n image_id; card c? filename, rank, source v? score th?c.
N?t A/B/C1/C2/Fusion ho?c So s?nh hi?n th? k?t qu? SQL t??ng ?ng, kh?ng hardcode Top-5.
B?ng gi?i th?ch c? b?n raw distance, b?n normalized distance v? D. Dialog c? float ??y ??,
metadata ngu?n v? t?a ?? m?t v?i role th?c. HF person_id NULL ???c ghi l? ch?a c? nh?n ngu?n.

Weights m?c ??nh 0.25 m?i b? l? **EXPERIMENTAL_EQUAL_WEIGHTS**, kh?ng ph?i tr?ng s? PDF b?t bu?c.
Client v? server ki?m h?u h?n, kh?ng ?m, t?ng b?ng1 v?i atol1e-12/rtol0; server t?i s? d?ng
validate_weights. Kh?ng t? normalize, chia l?i ho?c t?i ?u tr?ng s?. Khi s?a weights,
UI b?o ch?a ?p d?ng cho t?i khi nh?n T?m ki?m; gi? tr? ???c chuy?n nguy?n v?n ??n Python API.

Gi? Euclid A/B/C2, Chi-square C1 h? s?0.5, median normalization v?epsilon1e-8 theo phi?n b?n ?? kh?a.
Pool chung1437, lo?i self theo image_id, c?n1436 candidate khi query ??y ??; sort(distance,image_id).
HF00209 c? A/C1/C2 nh?ng thi?u B: UI b?o unavailable, kh?ng zero-fill hay fusion ba b?.
Input/?nh l?i c? th?ng b?o r? v? kh?ng tr?nh b?y k?t qu? c? nh? m?t truy v?n th?nh c?ng.

## Ki?m th? th?c t?

**{result['tests_run']} tests PASS**, 0 failure/error/skip:14 HTTP tests m?i +176 regression hi?n c?.
HTTP tests ki?m s?u query CFD00001/CFD00069/HF00001/HF00198/HF00722/HF00209.
125 Top-5 rows c?a n?m query ?? b? v? n?m ch? ?? kh?p baseline SQL ch?nh x?c;
median, weights v? candidate counts kh?ng ??i. Hash ?nh query v? m?i Top-5 c?a CFD00001 kh?p image_id.
Custom weights (.1,.2,.3,.4) kh?p Python SQL API; t?m ki?m l?p l?i c? c?ng response/k?t qu?.

Ki?m th?m invalid sum/negative/NaN/bool/huge integer, JSON l?i, path traversal, Host/Origin/token,
SQL write b? ch?n, metadata NULL v? missing/changed image. Fault injection ch? trong RAM/temp
ho?c request l?i c?a test; kh?ng s?a ?nh ngu?n/snapshot.

Chromium th?t `{browser['browser']['product']}` qua Brave headless c? s?n v? Node24/CDP:
**{len(browser['checks'])} checks PASS**, kh?ng Runtime exception; desktop1600?1100 v? mobile viewport390?844.
Ki?m b?n only tabs, so s?nh25 cards, metadata, weights request, invalid sum, repeat, missing_B,
unknown query, gallery filter/ch?n HF, kh?ng tr?n ngang mobile v? l?i ?nh query.
Screenshot d?ng Page.captureScreenshot, kh?ng mockup ho?c ?nh sinh AI.

Host b?o NT10.0.26200; registry DisplayVersion25H2/ProductName Windows10 Home.
Gi? nguy?n th?ng tin OS ?o ???c, kh?ng t? ??i nh?n t? userAgent. Ch?a ki?m th? tr?nh duy?t kh?c Chromium.

[190 tests log](../app/evidence/tests.log) ? [Verification](../app/evidence/verification.json) ?
[Browser checks](../app/evidence/browser_verification.json).

## Screenshots th?c t?

{screenshots}

## L?nh PowerShell th?c t? ?? ch?y

T? repository root:

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B -m app.server --port 8765
& .\app\start.ps1 -Port 8765
.\.venv311\Scripts\python.exe -X utf8 -B -m unittest discover -s app/tests -p test_web.py -v
node app/tests/browser.mjs
.\.venv311\Scripts\python.exe -X utf8 -B -m app.verify
.\.venv311\Scripts\python.exe -X utf8 -B -m app.finalize
```

Hai l?nh server l? hai c?ch kh?i ch?y thay th?; ?? stop/restart khi review source, kh?ng bind ch?ng port.
Browser QA d?ng port9224 v? profile t?m ri?ng, in-process GPU cho m?i tr??ng headless n?y.
?? ??ng browser/profile QA v? d?n file t?m, kh?ng t?c ??ng profile ng??i d?ng.
Server demo ???c d?ng l?c b?n giao; ch?y l?i app/start.ps1 r?i m? http://127.0.0.1:8765/.
app.verify/app.finalize t?o evidence l?n ??u v? t? ch?i ghi ??; ki?m th? th??ng d?ng unittest.

## B?o to?n v? ph?m vi k?t lu?n

**{len(baseline)} file baseline SHA tr??c/sau kh?ng ??i, 0 missing**, g?m PDF, dataset, extractors,
vector/stats/calibration, mapping, SQLite snapshots/backups, queries v? review ?? c?.
Database hash kh?p nguy?n b?n, kh?ng persist request n?o. Ch? app/ v? b?o c?o n?y l? file m?i.
Hash c?c file m?i ? app/evidence/created_files_manifest.json; manifest kh?ng ch?a ch?nh n?.

??y l? gallery search. Ch?a c? ?nh m?i/upload, extractor, history store, login ho?c tri?n khai Internet.
Kh?ng c? n?t Upload gi?. C1 ROI v0.4 v?n provisional, ch?a anatomy-approved.
Gi?i h?n dataset/mapping/alignment gi? nguy?n; kh?ng suy person_id/tu?i/gi?i ho?c k?t lu?n accuracy
khi thi?u relevance ground truth. PDF quy ??nh c?ng th?c; ki?n tr?c web, cache, HTTP/API v? visual style
l? quy?t ??nh tri?n khai, kh?ng g?n th?nh quy ??nh c?a PDF.
'''
    path=ROOT/'docs/WEB_APPLICATION_IMPLEMENTATION_REPORT.md'
    with path.open('x',encoding='utf8',newline='\n') as stream:stream.write(report)
    for doc in [ROOT/'app/README.md',path]:
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text('utf8')):
            if not link.startswith(('http','<')):assert (doc.parent/link).is_file(),link
    write_json(E/'final_scope.json',dict(status='PASS',date='2026-11-24',protected_files=len(baseline),changed=[],missing=[],
        database_sha256=result['database_sha256'],history_runs=6,history_results=125,sqlite_writes=0,
        extractors_modified=False,vectors_modified=False,calibration_modified=False,
        new_image_support=False,anatomical_approval_claimed=False,accuracy_improvement_claimed=False,
        tests=190,browser_checks=len(browser['checks']),screenshots=5))
    files=[p for p in (ROOT/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[path]
    write_json(E/'created_files_manifest.json',dict(schema_id='PORTRAIT_WEB_CREATED_FILES_v1',self_excluded=True,files=[
        dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=store.digest(p)) for p in sorted(files)]))
    print(store.json_text(dict(status='PASS',protected_files=len(baseline),new_files=len(files),tests=190,
        browser_checks=len(browser['checks']),sqlite_writes=0)))


if __name__=='__main__':main()
