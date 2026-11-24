-- Additive extension on a NEW backup of the accepted schema-1 database.
-- Keep PRAGMA user_version=1 for the unchanged A/B loader; track extension here.
CREATE TABLE EyeMeasurementBatches (
    batch_id TEXT NOT NULL PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_database_sha256 TEXT NOT NULL CHECK(length(source_database_sha256)=64),
    source_archive_sha256 TEXT NOT NULL CHECK(length(source_archive_sha256)=64),
    eye_center_method TEXT NOT NULL,
    model_version TEXT NOT NULL,
    coordinate_system TEXT NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TABLE EyeCoordinateSources (
    image_id TEXT NOT NULL,
    batch_id TEXT NOT NULL REFERENCES EyeMeasurementBatches(batch_id),
    eye_center_method TEXT NOT NULL,
    model_version TEXT NOT NULL,
    measurement_role TEXT NOT NULL CHECK(measurement_role='audit_remeasurement'),
    coordinate_system TEXT NOT NULL,
    source_landmark_hash TEXT NOT NULL CHECK(length(source_landmark_hash)=64),
    archive_row_index INTEGER NOT NULL CHECK(archive_row_index>=0),
    provenance TEXT NOT NULL,
    PRIMARY KEY(image_id,batch_id),
    UNIQUE(batch_id,archive_row_index),
    FOREIGN KEY(image_id,eye_center_method,model_version,measurement_role)
        REFERENCES EyeCoordinates(image_id,method,model_version,coordinate_role)
);
CREATE TABLE EyeMeasurementAttempts (
    batch_id TEXT NOT NULL REFERENCES EyeMeasurementBatches(batch_id),
    image_id TEXT NOT NULL REFERENCES Images(image_id),
    status TEXT NOT NULL CHECK(status IN ('measured','unmeasurable')),
    reason TEXT,
    PRIMARY KEY(batch_id,image_id),
    CHECK((status='measured' AND reason IS NULL) OR (status='unmeasurable' AND reason IS NOT NULL))
);
CREATE VIEW EyeMetadataAuditV1 AS
SELECT e.image_id,e.left_x,e.left_y,e.right_x,e.right_y,
       s.coordinate_system,s.eye_center_method,e.model_version,s.source_landmark_hash,
       s.provenance,s.measurement_role,s.batch_id,s.archive_row_index
FROM EyeCoordinateSources s JOIN EyeCoordinates e
 ON e.image_id=s.image_id AND e.method=s.eye_center_method
 AND e.model_version=s.model_version AND e.coordinate_role=s.measurement_role
WHERE s.batch_id='eye_mean6_saved478_v1';
