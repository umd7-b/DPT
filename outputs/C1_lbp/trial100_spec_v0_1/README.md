# C1 trial100

EXPERIMENTAL_TECHNICAL_TRIAL — ROI_ANATOMY_STATUS=PROVISIONAL.

100 image records;96 vectors;4 missing. See [report](../../../docs/C1_LBP_TRIAL100_REPORT.md).
`gallery_vectors.npy`: float64[96,236], `counts.npy`: uint64[96,4,59], `histograms.npy`: float64[96,4,59].
Join `manifest.json` by image_id and feature_row_index (missing=null), never by row position in a source catalog.
Per-image JSON in images/ preserves both hashes, measurements, counts/histograms/vector or null and missing reasons.
`contract_lock.json` pins semantics/environment. Negative masks are diagnostic only, no LBP or partial vectors.
`evidence/` holds independent checks, tests, hand calculation, original hash baseline, integrity and new files manifest.
Do not import into production SQLite. Old historical specs/README remain frozen; this directory records the authorized new trial.

Read-only usage from repository root:

```python
from features.C1_lbp.src.gallery import TrialGallery
g = TrialGallery('outputs/C1_lbp/trial100_spec_v0_1')
vector = g.vector('cfd_final_00001')
# g.vector('hf_merged_00069') raises KeyError, no zero-fill.
# g.extract_query(bgr256_uint8, pixel_landmarks478_float32, image_id='query')
# Caller must supply aligned image and authenticated landmark provenance.
```

The trial runner/test logger/verifier refuse overwrite. Preserve this completed version.
