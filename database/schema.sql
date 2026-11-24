PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE SchemaInfo (
    version INTEGER PRIMARY KEY CHECK (version = 1),
    report_sha256 TEXT NOT NULL CHECK (length(report_sha256) = 64),
    created_at TEXT NOT NULL,
    implementation_decisions TEXT NOT NULL
);
CREATE TABLE DatasetVersions (
    dataset_version TEXT NOT NULL PRIMARY KEY,
    metadata_sha256 TEXT NOT NULL CHECK (length(metadata_sha256) = 64),
    provenance_json TEXT NOT NULL
);
CREATE TABLE Persons (
    person_id TEXT NOT NULL PRIMARY KEY,
    source_namespace TEXT NOT NULL,
    source_person_id TEXT NOT NULL CHECK (length(source_person_id) > 0),
    evidence_json TEXT NOT NULL,
    UNIQUE (source_namespace, source_person_id)
);
CREATE TABLE Images (
    image_id TEXT NOT NULL PRIMARY KEY,
    filename TEXT NOT NULL,
    image_path TEXT NOT NULL,
    source TEXT NOT NULL,
    image_hash TEXT NOT NULL CHECK (length(image_hash) = 64),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    dataset_version TEXT NOT NULL REFERENCES DatasetVersions(dataset_version),
    person_id TEXT REFERENCES Persons(person_id),
    catalog_row_index INTEGER NOT NULL CHECK (catalog_row_index >= 0),
    a_row_index INTEGER NOT NULL CHECK (a_row_index >= 0),
    metadata_json TEXT NOT NULL,
    UNIQUE (dataset_version, filename),
    UNIQUE (dataset_version, catalog_row_index),
    UNIQUE (dataset_version, a_row_index),
    UNIQUE (image_id, a_row_index)
);
CREATE INDEX Images_hash ON Images(image_hash);
CREATE TABLE EyeCoordinates (
    image_id TEXT NOT NULL REFERENCES Images(image_id),
    method TEXT NOT NULL,
    model_version TEXT NOT NULL,
    coordinate_role TEXT NOT NULL CHECK (coordinate_role IN ('audit_remeasurement', 'original_preprocessing')),
    left_x REAL NOT NULL, left_y REAL NOT NULL,
    right_x REAL NOT NULL, right_y REAL NOT NULL,
    coordinate_frame TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    PRIMARY KEY (image_id, method, model_version, coordinate_role)
);
CREATE TABLE FeatureVersions (
    feature_version TEXT NOT NULL PRIMARY KEY,
    logical_group TEXT NOT NULL CHECK (logical_group IN ('A', 'B', 'C')),
    feature_name TEXT NOT NULL CHECK (feature_name IN ('A', 'B', 'C1', 'C2')),
    schema_json TEXT NOT NULL,
    schema_hash TEXT NOT NULL CHECK (length(schema_hash) = 64),
    dimension INTEGER NOT NULL CHECK (dimension > 0),
    dtype TEXT NOT NULL CHECK (dtype IN ('<f4', '<f8', '>f4', '>f8')),
    normalization_version TEXT NOT NULL,
    stats_hash TEXT NOT NULL CHECK (length(stats_hash) = 64),
    status TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    CHECK ((logical_group IN ('A', 'B') AND feature_name = logical_group)
        OR (logical_group = 'C' AND feature_name IN ('C1', 'C2'))),
    UNIQUE (feature_version, dtype, dimension)
);
CREATE TABLE NormalizationStages (
    feature_version TEXT NOT NULL REFERENCES FeatureVersions(feature_version),
    stage_index INTEGER NOT NULL CHECK (stage_index > 0),
    stage_name TEXT NOT NULL,
    stats_data BLOB NOT NULL,
    stats_sha256 TEXT NOT NULL CHECK (length(stats_sha256) = 64),
    source_path TEXT NOT NULL,
    PRIMARY KEY (feature_version, stage_index),
    UNIQUE (feature_version, stage_name)
);
CREATE TABLE FeatureVectors (
    image_id TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    vector_data BLOB,
    dtype TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('valid', 'missing')),
    missing_reason TEXT,
    vector_sha256 TEXT,
    a_row_index INTEGER NOT NULL,
    feature_row_index INTEGER CHECK (feature_row_index >= 0),
    provenance_json TEXT NOT NULL,
    PRIMARY KEY (image_id, feature_version),
    FOREIGN KEY (image_id, a_row_index) REFERENCES Images(image_id, a_row_index),
    FOREIGN KEY (feature_version, dtype, dimension) REFERENCES FeatureVersions(feature_version, dtype, dimension),
    UNIQUE (feature_version, feature_row_index),
    CHECK ((status = 'valid' AND vector_data IS NOT NULL AND feature_row_index IS NOT NULL
            AND missing_reason IS NULL AND vector_sha256 IS NOT NULL AND length(vector_sha256) = 64
            AND length(vector_data) = dimension * CASE WHEN dtype IN ('<f4', '>f4') THEN 4 ELSE 8 END)
        OR (status = 'missing' AND vector_data IS NULL AND vector_sha256 IS NULL
            AND feature_row_index IS NULL AND missing_reason IS NOT NULL AND length(missing_reason) > 0))
);
CREATE TABLE Calibrations (
    calibration_id TEXT NOT NULL PRIMARY KEY,
    schema_version TEXT NOT NULL,
    epsilon REAL NOT NULL CHECK (epsilon > 0),
    pair_count INTEGER NOT NULL CHECK (pair_count > 0),
    pair_ids_sha256 TEXT NOT NULL CHECK (length(pair_ids_sha256) = 64),
    params_data BLOB NOT NULL,
    params_sha256 TEXT NOT NULL CHECK (length(params_sha256) = 64),
    pairs_csv_data BLOB NOT NULL,
    pairs_csv_sha256 TEXT NOT NULL CHECK (length(pairs_csv_sha256) = 64),
    fingerprint_json TEXT NOT NULL,
    experiment TEXT NOT NULL
);
CREATE TABLE CalibrationComponents (
    calibration_id TEXT NOT NULL REFERENCES Calibrations(calibration_id),
    feature_version TEXT NOT NULL REFERENCES FeatureVersions(feature_version),
    median REAL NOT NULL CHECK (median >= 0),
    PRIMARY KEY (calibration_id, feature_version)
);
CREATE TABLE CalibrationCandidates (
    calibration_id TEXT NOT NULL REFERENCES Calibrations(calibration_id),
    candidate_index INTEGER NOT NULL CHECK (candidate_index >= 0),
    image_id TEXT NOT NULL REFERENCES Images(image_id),
    PRIMARY KEY (calibration_id, candidate_index),
    UNIQUE (calibration_id, image_id)
);
CREATE TABLE CalibrationPairs (
    calibration_id TEXT NOT NULL REFERENCES Calibrations(calibration_id),
    pair_index INTEGER NOT NULL CHECK (pair_index >= 0),
    image_id_1 TEXT NOT NULL REFERENCES Images(image_id),
    image_id_2 TEXT NOT NULL REFERENCES Images(image_id),
    PRIMARY KEY (calibration_id, pair_index),
    UNIQUE (calibration_id, image_id_1, image_id_2),
    CHECK (image_id_1 < image_id_2)
);
CREATE TABLE CalibrationPairDistances (
    calibration_id TEXT NOT NULL,
    pair_index INTEGER NOT NULL,
    feature_version TEXT NOT NULL,
    distance REAL NOT NULL CHECK (distance >= 0),
    PRIMARY KEY (calibration_id, pair_index, feature_version),
    FOREIGN KEY (calibration_id, pair_index) REFERENCES CalibrationPairs(calibration_id, pair_index),
    FOREIGN KEY (calibration_id, feature_version) REFERENCES CalibrationComponents(calibration_id, feature_version)
);
CREATE TABLE RetrievalRuns (
    run_id TEXT NOT NULL PRIMARY KEY,
    created_at TEXT NOT NULL,
    query_image_id TEXT REFERENCES Images(image_id),
    query_path TEXT NOT NULL,
    query_hash TEXT NOT NULL CHECK (length(query_hash) = 64),
    mode TEXT NOT NULL CHECK (mode IN ('A', 'B', 'AB')),
    weight_a REAL NOT NULL CHECK (weight_a >= 0),
    weight_b REAL NOT NULL CHECK (weight_b >= 0),
    calibration_id TEXT NOT NULL REFERENCES Calibrations(calibration_id),
    feature_version_a TEXT NOT NULL,
    feature_version_b TEXT NOT NULL,
    top_k INTEGER NOT NULL CHECK (top_k > 0),
    status TEXT NOT NULL CHECK (status IN ('valid', 'missing_B')),
    missing_reason TEXT,
    excluded_ids_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    CHECK (abs(weight_a + weight_b - 1.0) < 1e-12),
    CHECK ((status = 'valid' AND missing_reason IS NULL) OR
           (status = 'missing_B' AND missing_reason IS NOT NULL)),
    FOREIGN KEY (calibration_id, feature_version_a) REFERENCES CalibrationComponents(calibration_id, feature_version),
    FOREIGN KEY (calibration_id, feature_version_b) REFERENCES CalibrationComponents(calibration_id, feature_version)
);
CREATE TABLE QueryVectors (
    run_id TEXT NOT NULL REFERENCES RetrievalRuns(run_id),
    feature_version TEXT NOT NULL,
    vector_data BLOB,
    dtype TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    vector_sha256 TEXT,
    status TEXT NOT NULL CHECK (status IN ('valid', 'missing')),
    missing_reason TEXT,
    PRIMARY KEY (run_id, feature_version),
    FOREIGN KEY (feature_version, dtype, dimension) REFERENCES FeatureVersions(feature_version, dtype, dimension),
    CHECK ((status = 'valid' AND vector_data IS NOT NULL AND vector_sha256 IS NOT NULL
            AND length(vector_sha256) = 64 AND missing_reason IS NULL
            AND length(vector_data) = dimension * CASE WHEN dtype IN ('<f4', '>f4') THEN 4 ELSE 8 END)
        OR (status = 'missing' AND vector_data IS NULL AND vector_sha256 IS NULL
            AND missing_reason IS NOT NULL AND length(missing_reason) > 0))
);
CREATE TABLE RetrievalResults (
    run_id TEXT NOT NULL REFERENCES RetrievalRuns(run_id),
    rank INTEGER NOT NULL CHECK (rank > 0),
    image_id TEXT NOT NULL REFERENCES Images(image_id),
    dA REAL NOT NULL CHECK (dA >= 0),
    dB REAL CHECK (dB >= 0),
    normalized_a REAL NOT NULL CHECK (normalized_a >= 0),
    normalized_b REAL CHECK (normalized_b >= 0),
    D_AB REAL CHECK (D_AB >= 0),
    score REAL NOT NULL CHECK (score >= 0),
    PRIMARY KEY (run_id, rank),
    UNIQUE (run_id, image_id),
    CHECK ((dB IS NULL AND normalized_b IS NULL AND D_AB IS NULL)
        OR (dB IS NOT NULL AND normalized_b IS NOT NULL AND D_AB IS NOT NULL))
);
CREATE TRIGGER Result_contract BEFORE INSERT ON RetrievalResults BEGIN
    SELECT CASE WHEN NEW.rank > (SELECT top_k FROM RetrievalRuns WHERE run_id = NEW.run_id)
        THEN RAISE(ABORT, 'rank exceeds top_k') END;
    SELECT CASE WHEN (SELECT mode FROM RetrievalRuns WHERE run_id = NEW.run_id) IN ('B','AB')
        AND (SELECT status FROM RetrievalRuns WHERE run_id = NEW.run_id) = 'missing_B'
        THEN RAISE(ABORT, 'missing B cannot produce B/AB results') END;
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM RetrievalRuns r JOIN CalibrationCandidates c ON c.calibration_id=r.calibration_id
        WHERE r.run_id=NEW.run_id AND c.image_id=NEW.image_id)
        THEN RAISE(ABORT, 'result outside calibrated candidate set') END;
END;
CREATE VIEW ImageFeatureStatus AS
SELECT i.image_id, i.filename, i.person_id, v.feature_version, f.feature_name,
       v.status, v.missing_reason, v.a_row_index, v.feature_row_index, v.dtype, v.dimension
FROM Images i JOIN FeatureVectors v USING(image_id)
JOIN FeatureVersions f USING(feature_version);
