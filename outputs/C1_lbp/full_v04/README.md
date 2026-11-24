# C1 full_v04

Project-selected ROI v0.4 / ANATOMY_PROVISIONAL.1438 vectors,710 CFD+728 HF,0 missing.
Read [implementation report](../../../docs/C1_FULL_IMPLEMENTATION_REPORT.md) and feature_schema.json.
features_C1.npy float64[1438,236];counts.npy uint64[1438,4,59];eligible_centres.npy uint64[1438,4].
feature_rows.csv maps explicit image_id to feature_row_index;extraction_status.csv contains all1438 inputs.
The original LBP spec's ROI v0.2 dependency remains unchanged; a new implementation binding selects v0.4.
No source image,PDF,previous database/vector/stats/calibration/review was modified.

Query from repository root (use a fresh output folder):

```powershell
.\.venv311\Scripts\python.exe -X utf8 -B retrieval/search_c1.py --image cfd_final_00001.png --top-k 5 --output outputs/C1_lbp/full_v04/queries/cfd_final_00001_run2
```

Query supports gallery IDs/filenames/matching files only; no unaligned external-image adapter.
Distance =0.5*sum((a-b)^2/(a+b+1e-8)); self-ID excluded; ties sort by image_id.
Existing extraction/query outputs refuse overwrite. No C2 or fusion is included.
