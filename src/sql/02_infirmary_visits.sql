DROP VIEW IF EXISTS clean_infirmary_visits;
CREATE VIEW clean_infirmary_visits AS
WITH normalized AS (
    SELECT
        v.*,
        CASE
            WHEN v.injury_code GLOB '[a-zA-Z][a-zA-Z][a-zA-Z][0-9][0-9]'
                 AND EXISTS (
                     SELECT 1 FROM effective_infirmary_visits reference
                     WHERE reference.injury_code =
                         upper(substr(v.injury_code, 1, 3)) || '-' || substr(v.injury_code, 4, 2)
                 )
            THEN upper(substr(v.injury_code, 1, 3)) || '-' || substr(v.injury_code, 4, 2)
            ELSE v.injury_code
        END AS normalized_injury_code
    FROM effective_infirmary_visits v
)
SELECT
    visit_id,
    sorcerer_id,
    mission_id,
    admitted_at,
    discharged_at,
    normalized_injury_code AS injury_code,
    injury_code AS original_injury_code,
    severity,
    admitted_from,
    CASE
        WHEN datetime(admitted_at) IS NULL OR datetime(discharged_at) IS NULL THEN 'invalid_timestamp'
        WHEN datetime(discharged_at) < datetime(admitted_at) THEN 'negative_duration'
        ELSE 'valid'
    END AS timing_status,
    CASE
        WHEN datetime(admitted_at) IS NOT NULL
             AND datetime(discharged_at) IS NOT NULL
             AND datetime(discharged_at) >= datetime(admitted_at)
        THEN (unixepoch(discharged_at) - unixepoch(admitted_at)) / 3600.0
    END AS recovery_hours
FROM normalized;
