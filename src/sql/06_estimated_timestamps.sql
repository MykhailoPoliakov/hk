DROP VIEW IF EXISTS estimated_infirmary_visits;
CREATE VIEW estimated_infirmary_visits AS
WITH converted AS (
    SELECT
        v.*,
        m.start_ts AS mission_start_ts,
        strftime('%Y-%m-%dT%H:%M:%SZ', v.admitted_at, '-9 hours') AS admitted_at_utc,
        CASE
            WHEN m.mission_id IS NULL OR m.conflicting_mission_id OR m.start_ts IS NULL THEN NULL
            WHEN m.start_ts >= '2026-02-28T00:00:00Z'
            THEN strftime('%Y-%m-%dT%H:%M:%SZ', v.discharged_at)
            ELSE strftime('%Y-%m-%dT%H:%M:%SZ', v.discharged_at, '-9 hours')
        END AS discharged_at_utc,
        CASE
            WHEN m.mission_id IS NULL OR m.conflicting_mission_id OR m.start_ts IS NULL
            THEN 'unresolved_mission'
            WHEN m.start_ts >= '2026-02-28T00:00:00Z'
            THEN 'inferred_discharge_utc'
            ELSE 'dictionary_jst'
        END AS timestamp_assumption
    FROM reviewed_infirmary_visits v
    LEFT JOIN clean_missions m ON m.mission_id = v.mission_id
)
SELECT *,
    CASE
        WHEN admitted_at_utc IS NULL OR discharged_at_utc IS NULL THEN 'unresolved'
        WHEN unixepoch(discharged_at_utc) < unixepoch(admitted_at_utc) THEN 'negative_duration'
        ELSE 'usable_under_assumption'
    END AS estimated_timing_status,
    CASE
        WHEN admitted_at_utc IS NOT NULL AND discharged_at_utc IS NOT NULL
             AND unixepoch(discharged_at_utc) >= unixepoch(admitted_at_utc)
        THEN (unixepoch(discharged_at_utc) - unixepoch(admitted_at_utc)) / 3600.0
    END AS estimated_recovery_hours
FROM converted;
