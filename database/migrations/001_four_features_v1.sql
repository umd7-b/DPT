-- Additive extension: base PRAGMA user_version=1 is intentionally preserved.
CREATE TABLE FourFeatureMigrations (
    extension_version TEXT NOT NULL PRIMARY KEY,
    migration_sha256 TEXT NOT NULL CHECK(length(migration_sha256)=64),
    source_database_sha256 TEXT NOT NULL CHECK(length(source_database_sha256)=64),
    authority_data BLOB NOT NULL,
    authority_sha256 TEXT NOT NULL CHECK(length(authority_sha256)=64),
    policy_data BLOB NOT NULL,
    policy_sha256 TEXT NOT NULL CHECK(length(policy_sha256)=64),
    created_at TEXT NOT NULL
);
CREATE TABLE FourFeatureVersionLocks (
    kind TEXT NOT NULL PRIMARY KEY CHECK(kind IN ('a','b','c1','c2')),
    feature_version TEXT NOT NULL UNIQUE REFERENCES FeatureVersions(feature_version),
    version_record_sha256 TEXT NOT NULL CHECK(length(version_record_sha256)=64),
    vector_artifact_sha256 TEXT NOT NULL CHECK(length(vector_artifact_sha256)=64),
    UNIQUE(kind,feature_version)
);
CREATE TABLE FourFeatureVectorBindings (
    image_id TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    source_row_index INTEGER NOT NULL CHECK(source_row_index>=0),
    source_vector_sha256 TEXT NOT NULL CHECK(length(source_vector_sha256)=64),
    source_image_sha256 TEXT NOT NULL CHECK(length(source_image_sha256)=64),
    PRIMARY KEY(image_id,feature_version),
    UNIQUE(feature_version,source_row_index),
    FOREIGN KEY(image_id,feature_version) REFERENCES FeatureVectors(image_id,feature_version)
);
CREATE TABLE FourFeatureArtifacts (
    feature_version TEXT NOT NULL REFERENCES FeatureVersions(feature_version),
    artifact_name TEXT NOT NULL,
    artifact_data BLOB NOT NULL,
    artifact_sha256 TEXT NOT NULL CHECK(length(artifact_sha256)=64),
    source_path TEXT NOT NULL,
    PRIMARY KEY(feature_version,artifact_name)
);
CREATE TABLE FourFeatureCalibrations (
    calibration_id TEXT NOT NULL PRIMARY KEY REFERENCES Calibrations(calibration_id),
    policy_sha256 TEXT NOT NULL CHECK(length(policy_sha256)=64),
    epsilon_c1 REAL NOT NULL CHECK(epsilon_c1>0 AND epsilon_c1<1),
    params_sha256 TEXT NOT NULL CHECK(length(params_sha256)=64),
    pairs_sha256 TEXT NOT NULL CHECK(length(pairs_sha256)=64),
    feature_versions_json TEXT NOT NULL,
    configuration TEXT NOT NULL
);
CREATE TABLE FourFeatureRuns (
    run_id TEXT NOT NULL PRIMARY KEY,
    created_at TEXT NOT NULL,
    query_image_id TEXT NOT NULL REFERENCES Images(image_id),
    query_path TEXT NOT NULL,
    query_sha256 TEXT NOT NULL CHECK(length(query_sha256)=64),
    calibration_id TEXT NOT NULL REFERENCES FourFeatureCalibrations(calibration_id),
    weight_a REAL NOT NULL CHECK(weight_a>=0 AND weight_a<=1.000000000001),
    weight_b REAL NOT NULL CHECK(weight_b>=0 AND weight_b<=1.000000000001),
    weight_c1 REAL NOT NULL CHECK(weight_c1>=0 AND weight_c1<=1.000000000001),
    weight_c2 REAL NOT NULL CHECK(weight_c2>=0 AND weight_c2<=1.000000000001),
    top_k INTEGER NOT NULL CHECK(top_k>0),
    status TEXT NOT NULL CHECK(status IN ('ok','fusion_unavailable')),
    missing_reason TEXT,
    gallery_intersection_count INTEGER NOT NULL CHECK(gallery_intersection_count=1437),
    candidate_count INTEGER NOT NULL CHECK(candidate_count>=0),
    self_exclusion_count INTEGER NOT NULL CHECK(self_exclusion_count IN (0,1)),
    ranked_candidate_count INTEGER NOT NULL CHECK(ranked_candidate_count>=0),
    provenance_json TEXT NOT NULL,
    UNIQUE(run_id,calibration_id),
    CHECK(abs(weight_a+weight_b+weight_c1+weight_c2-1)<=1e-12),
    CHECK(candidate_count=gallery_intersection_count-self_exclusion_count),
    CHECK((status='ok' AND missing_reason IS NULL AND ranked_candidate_count=candidate_count)
       OR (status='fusion_unavailable' AND missing_reason IS NOT NULL AND ranked_candidate_count=0))
);
CREATE TABLE FourFeatureRunComponents (
    run_id TEXT NOT NULL,
    calibration_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    weight REAL NOT NULL CHECK(weight>=0 AND weight<=1.000000000001),
    median REAL NOT NULL CHECK(median>=0 AND median<1e308),
    PRIMARY KEY(run_id,kind),
    UNIQUE(run_id,feature_version),
    FOREIGN KEY(run_id,calibration_id) REFERENCES FourFeatureRuns(run_id,calibration_id),
    FOREIGN KEY(kind,feature_version) REFERENCES FourFeatureVersionLocks(kind,feature_version),
    FOREIGN KEY(calibration_id,feature_version) REFERENCES CalibrationComponents(calibration_id,feature_version)
);
CREATE TABLE FourFeatureResults (
    run_id TEXT NOT NULL REFERENCES FourFeatureRuns(run_id),
    mode TEXT NOT NULL CHECK(mode IN ('a','b','c1','c2','fusion')),
    rank INTEGER NOT NULL CHECK(rank>0),
    image_id TEXT NOT NULL REFERENCES Images(image_id),
    dA REAL NOT NULL CHECK(dA>=0 AND dA<1e308),
    dB REAL NOT NULL CHECK(dB>=0 AND dB<1e308),
    dC1 REAL NOT NULL CHECK(dC1>=0 AND dC1<1e308),
    dC2 REAL NOT NULL CHECK(dC2>=0 AND dC2<1e308),
    normalized_a REAL NOT NULL CHECK(normalized_a>=0 AND normalized_a<1e308),
    normalized_b REAL NOT NULL CHECK(normalized_b>=0 AND normalized_b<1e308),
    normalized_c1 REAL NOT NULL CHECK(normalized_c1>=0 AND normalized_c1<1e308),
    normalized_c2 REAL NOT NULL CHECK(normalized_c2>=0 AND normalized_c2<1e308),
    D REAL NOT NULL CHECK(D>=0 AND D<1e308),
    score REAL NOT NULL CHECK(score>=0 AND score<1e308),
    PRIMARY KEY(run_id,mode,rank),
    UNIQUE(run_id,mode,image_id)
);
CREATE INDEX FourFeatureVectors_lookup ON FeatureVectors(feature_version,status,image_id);
CREATE INDEX FourFeatureRuns_query ON FourFeatureRuns(query_image_id,created_at);
CREATE INDEX FourFeatureResults_image ON FourFeatureResults(image_id,mode);
CREATE TRIGGER FourFeatureResult_contract BEFORE INSERT ON FourFeatureResults BEGIN
    SELECT CASE WHEN (SELECT status FROM FourFeatureRuns WHERE run_id=NEW.run_id)!='ok'
        THEN RAISE(ABORT,'unavailable query cannot produce results') END;
    SELECT CASE WHEN NEW.rank>(SELECT top_k FROM FourFeatureRuns WHERE run_id=NEW.run_id)
        THEN RAISE(ABORT,'rank exceeds top_k') END;
    SELECT CASE WHEN NEW.image_id=(SELECT query_image_id FROM FourFeatureRuns WHERE run_id=NEW.run_id)
        THEN RAISE(ABORT,'self match is excluded') END;
    SELECT CASE WHEN (SELECT count(*) FROM FourFeatureRunComponents WHERE run_id=NEW.run_id)!=4
        THEN RAISE(ABORT,'four versioned components required') END;
    SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM FourFeatureRuns r JOIN CalibrationCandidates c
        ON c.calibration_id=r.calibration_id WHERE r.run_id=NEW.run_id AND c.image_id=NEW.image_id)
        THEN RAISE(ABORT,'candidate outside calibrated four-way pool') END;
END;
CREATE VIEW FourFeatureCoverage AS
SELECT f.feature_name,v.feature_version,v.status,count(*) AS record_count
FROM FeatureVectors v JOIN FeatureVersions f USING(feature_version)
GROUP BY v.feature_version,v.status;
