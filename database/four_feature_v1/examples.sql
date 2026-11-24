-- Metadata and per-version status; no implicit vector row order.
SELECT i.image_id,i.filename,v.feature_version,v.status,v.dimension,v.dtype,v.missing_reason
FROM Images i JOIN FeatureVectors v USING(image_id)
WHERE i.image_id='hf_merged_00209' ORDER BY v.feature_version;

SELECT * FROM FourFeatureCoverage ORDER BY feature_name,status;

-- Both historical AB and four-way calibrations coexist.
SELECT c.calibration_id,c.pair_count,c.epsilon,k.feature_version,k.median
FROM Calibrations c JOIN CalibrationComponents k USING(calibration_id)
ORDER BY c.calibration_id,k.feature_version;

SELECT r.query_image_id,r.status,r.candidate_count,r.self_exclusion_count,r.ranked_candidate_count,
       r.weight_a,r.weight_b,r.weight_c1,r.weight_c2,count(x.image_id) AS stored_result_rows
FROM FourFeatureRuns r LEFT JOIN FourFeatureResults x USING(run_id)
GROUP BY r.run_id ORDER BY r.query_image_id;

SELECT r.query_image_id,x.mode,x.rank,i.filename,x.dA,x.dB,x.dC1,x.dC2,
       x.normalized_a,x.normalized_b,x.normalized_c1,x.normalized_c2,x.D,x.score
FROM FourFeatureRuns r JOIN FourFeatureResults x USING(run_id) JOIN Images i ON i.image_id=x.image_id
WHERE r.query_image_id='cfd_final_00001' AND x.mode='fusion' ORDER BY x.rank;

SELECT name,type,tbl_name FROM sqlite_master WHERE name LIKE 'FourFeature%' ORDER BY type,name;
