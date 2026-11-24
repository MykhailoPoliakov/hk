DROP VIEW IF EXISTS attributed_ce_wearable;
DROP VIEW IF EXISTS reviewed_device_assignments;
DROP VIEW IF EXISTS reviewed_infirmary_visits;

CREATE VIEW reviewed_infirmary_visits AS
SELECT
    v.*,
    s.join_date AS current_holder_join_date,
    CASE
        WHEN s.sorcerer_id IS NULL THEN 'unknown_sorcerer'
        WHEN date(s.join_date) IS NULL OR date(v.admitted_at) IS NULL THEN 'invalid_date'
        WHEN date(v.admitted_at) < date(s.join_date) THEN 'before_current_join_date'
        ELSE 'not_before_current_join_date'
    END AS identity_review,
    CASE WHEN v.mission_id IS NULL OR v.mission_id = '' THEN 1 ELSE 0 END AS missing_mission,
    CASE WHEN v.injury_code = 'TST-00' THEN 1 ELSE 0 END AS test_code_review,
    CASE
        WHEN v.timing_status = 'valid' THEN 'chronology_only_unverified'
        ELSE v.timing_status
    END AS recovery_review
FROM clean_infirmary_visits v
LEFT JOIN sorcerers s ON s.sorcerer_id = v.sorcerer_id;

-- Assignment periods are treated as half-open: [valid_from, valid_to).
CREATE VIEW reviewed_device_assignments AS
SELECT
    d.rowid AS assignment_rowid,
    d.*,
    s.join_date AS current_holder_join_date,
    CASE
        WHEN s.sorcerer_id IS NULL THEN 'unknown_sorcerer'
        WHEN julianday(d.valid_from) IS NULL
             OR (d.valid_to IS NOT NULL AND d.valid_to != ''
                 AND (julianday(d.valid_to) IS NULL
                      OR julianday(d.valid_to) <= julianday(d.valid_from)))
        THEN 'invalid_interval'
        WHEN EXISTS (
            SELECT 1
            FROM device_assignments other
            WHERE other.device_id = d.device_id
              AND other.rowid != d.rowid
              AND julianday(d.valid_from) < COALESCE(julianday(NULLIF(other.valid_to, '')), 1e99)
              AND julianday(other.valid_from) < COALESCE(julianday(NULLIF(d.valid_to, '')), 1e99)
        ) THEN 'overlapping_device_assignment'
        WHEN EXISTS (
            SELECT 1
            FROM device_assignments other
            WHERE other.sorcerer_id = d.sorcerer_id
              AND other.rowid != d.rowid
              AND julianday(d.valid_from) < COALESCE(julianday(NULLIF(other.valid_to, '')), 1e99)
              AND julianday(other.valid_from) < COALESCE(julianday(NULLIF(d.valid_to, '')), 1e99)
        ) THEN 'overlapping_sorcerer_assignment'
        ELSE 'valid'
    END AS assignment_review
FROM device_assignments d
LEFT JOIN sorcerers s ON s.sorcerer_id = d.sorcerer_id;

CREATE VIEW attributed_ce_wearable AS
WITH assignments AS MATERIALIZED (
    SELECT * FROM reviewed_device_assignments
)
SELECT
    c.rowid AS reading_rowid,
    c.device_id,
    c.ts,
    c.ce_level,
    c.firmware,
    CASE WHEN c.firmware = 'v2.3' THEN 1 ELSE 0 END AS firmware_review_required,
    d.sorcerer_id,
    d.valid_from,
    d.valid_to,
    d.current_holder_join_date,
    CASE
        WHEN d.assignment_rowid IS NULL THEN 'unmatched_assignment'
        WHEN d.assignment_review != 'valid' THEN d.assignment_review
        WHEN date(d.current_holder_join_date) IS NULL OR date(c.ts) IS NULL THEN 'invalid_date'
        WHEN date(c.ts) < date(d.current_holder_join_date) THEN 'before_current_join_date_utc'
        WHEN date(c.ts) = date(d.current_holder_join_date) THEN 'join_date_boundary'
        ELSE 'not_before_current_join_date'
    END AS attribution_review
FROM ce_wearable c
LEFT JOIN assignments d
    ON d.device_id = c.device_id
   AND julianday(c.ts) >= julianday(d.valid_from)
   AND (d.valid_to IS NULL OR d.valid_to = '' OR julianday(c.ts) < julianday(d.valid_to));
