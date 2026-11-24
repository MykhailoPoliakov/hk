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
        WHEN h.start_ts >= v.admitted_at_utc AND h.start_ts < v.discharged_at_utc THEN 'during_visit'
        WHEN datetime(h.start_ts, '+' || CAST(h.duration_min AS TEXT) || ' minutes') > v.admitted_at_utc
         AND h.start_ts <= v.discharged_at_utc THEN 'overlaps'
        WHEN h.start_ts < v.discharged_at_utc AND h.start_ts >= datetime(v.discharged_at_utc, '-6 hours') THEN 'within_6h_after'
        ELSE NULL
    END AS overlap_type
FROM healer_sessions h
CROSS JOIN estimated_infirmary_visits v
WHERE v.sorcerer_id = h.patient_id
  AND h.start_ts IS NOT NULL AND v.admitted_at_utc IS NOT NULL AND v.discharged_at_utc IS NOT NULL
  AND CASE
      WHEN h.start_ts >= v.admitted_at_utc AND h.start_ts < v.discharged_at_utc THEN 1
      WHEN datetime(h.start_ts, '+' || CAST(h.duration_min AS TEXT) || ' minutes') > v.admitted_at_utc
       AND h.start_ts <= v.discharged_at_utc THEN 1
      WHEN h.start_ts < v.discharged_at_utc AND h.start_ts >= datetime(v.discharged_at_utc, '-6 hours') THEN 1
      ELSE 0
  END = 1;

DROP VIEW IF EXISTS visits_with_external_healing;
CREATE VIEW visits_with_external_healing AS
SELECT DISTINCT v.visit_id, v.sorcerer_id, 1 as has_healer_overlap
FROM estimated_infirmary_visits v
WHERE EXISTS (SELECT 1 FROM healer_visit_overlap h WHERE h.visit_id = v.visit_id);
