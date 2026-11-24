# C2 Root-HOG324

Fixed technical prototype; crop anatomy/relevance unverified. Spec and arithmetic pinned before trial.
trial100:100 valid,0 missing;full_v1:1438 valid,0 missing (710CFD,728HF).
features_C2.npy float64[N,324];raw_cells.npy[N,4,4,9];raw_blocks.npy/root_blocks.npy[N,9,36].
feature_rows.csv uses image_id and feature_row_index;all inputs have extraction_status.csv.
ROI BGR[32:224,48:208],no new alignment,hard20-degree bins,Root block epsilon1e-8 then exact global L2.
Standalone Euclid324 query only;source A/B/C1/SQLite/PDF/dataset and old outputs remain unchanged.

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c2.py --image cfd_final_00001.png --top-k 5 --output outputs/C2_hog/full_v1/queries/cfd_final_00001_run2
```

Use fresh output paths. Gallery images only;do not assume external images have historical alignment.
See docs/C2_ROOT_HOG_324_SPEC.md,docs/C2_FULL_IMPLEMENTATION_REPORT.md and docs/audits/C2_NUMERICAL_VERIFICATION.md.
