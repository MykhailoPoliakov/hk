-- Drop 1: Link healer sessions to infirmary visits to identify external healing
DROP VIEW IF EXISTS healer_visit_overlap;
CREATE VIEW healer_visit_overlap AS
SELECT
    h.session_id,
    h.healer_id,
    h.patient_id,
    h.start_ts,
    datetime(h.start_ts, '+' || CAST(h.duration_min AS TEXT) || ' minutes') AS end_ts,
    v.visit_id,
    v.sorcerer_id,
    v.admitted_at_utc,
    v.discharged_at_utc,
    CASE
        WHEN unixepoch(h.start_ts) >= unixepoch(v.admitted_at_utc) THEN 'during_visit'
        ELSE 'overlaps'
    END AS overlap_type
FROM healer_sessions h
CROSS JOIN estimated_infirmary_visits v
WHERE v.sorcerer_id = h.patient_id
  AND h.start_ts IS NOT NULL AND v.admitted_at_utc IS NOT NULL AND v.discharged_at_utc IS NOT NULL
  AND unixepoch(h.start_ts) < unixepoch(v.discharged_at_utc)
  AND unixepoch(h.start_ts, '+' || CAST(h.duration_min AS TEXT) || ' minutes') > unixepoch(v.admitted_at_utc);

DROP VIEW IF EXISTS visits_with_external_healing;
CREATE VIEW visits_with_external_healing AS
SELECT DISTINCT v.visit_id, v.sorcerer_id, 1 as has_healer_overlap
FROM estimated_infirmary_visits v
WHERE EXISTS (SELECT 1 FROM healer_visit_overlap h WHERE h.visit_id = v.visit_id);
