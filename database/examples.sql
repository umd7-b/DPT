-- SQLite is an implementation choice, not a DBMS prescribed by csdldpt.pdf.
PRAGMA foreign_keys = ON;
PRAGMA integrity_check;
PRAGMA foreign_key_check;

-- Metadata by stable image ID; never join A and B by matrix position.
SELECT image_id, filename, image_path, image_hash, width, height, source,
       dataset_version, person_id, catalog_row_index, a_row_index
FROM Images WHERE image_id = 'cfd_final_00001';

-- Explicit missing B: NULL payload, dimension 144, reason retained.
SELECT s.image_id, s.feature_name, s.status, s.missing_reason,
       s.a_row_index, s.feature_row_index, s.dtype, s.dimension,
       length(v.vector_data) AS vector_bytes
FROM ImageFeatureStatus s JOIN FeatureVectors v
  ON s.image_id=v.image_id AND s.feature_version=v.feature_version
WHERE s.image_id IN ('hf_merged_00209','hf_merged_00210')
ORDER BY s.image_id, s.feature_name;

SELECT feature_name, status, count(*) AS images
FROM ImageFeatureStatus GROUP BY feature_name,status ORDER BY feature_name,status;

-- Only three audit remeasurements; missing eye metadata remains NULL.
SELECT i.image_id, e.left_x, e.left_y, e.right_x, e.right_y,
       e.method, e.model_version, e.coordinate_role
FROM Images i LEFT JOIN EyeCoordinates e ON e.image_id=i.image_id
WHERE i.image_id IN ('cfd_final_00001','hf_merged_00209');

SELECT f.logical_group,f.feature_name,f.feature_version,f.dimension,f.dtype,
       s.stage_index,s.stage_name,s.stats_sha256,length(s.stats_data) AS stats_bytes
FROM FeatureVersions f JOIN NormalizationStages s USING(feature_version)
ORDER BY f.feature_name,s.stage_index;

SELECT c.calibration_id,c.epsilon,c.pair_count,cc.feature_version,cc.median
FROM Calibrations c JOIN CalibrationComponents cc USING(calibration_id);

-- Committed Top-5 with run, query, weights, calibration and vector versions.
SELECT r.run_id,r.query_image_id,r.mode,r.weight_a,r.weight_b,
       r.calibration_id,r.feature_version_a,r.feature_version_b,
       t.rank,i.filename,t.dA,t.dB,t.normalized_a,t.normalized_b,t.D_AB,t.score
FROM RetrievalRuns r JOIN RetrievalResults t USING(run_id)
JOIN Images i ON i.image_id=t.image_id
WHERE r.query_image_id='cfd_final_00001' AND r.mode='AB'
ORDER BY r.created_at,r.run_id,t.rank;
