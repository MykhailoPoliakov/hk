# SQLite demo queries for the jury

Run these against `data.db`. It retains the imported raw tables, ordered
correction history and SQL review views.

```sql
-- Change-feed operations and resulting count.
SELECT op, COUNT(*) AS events FROM correction_history GROUP BY op;
SELECT COUNT(*) AS original_visits FROM infirmary_visits;
SELECT COUNT(*) AS effective_visits FROM effective_infirmary_visits;

-- Audit actions connecting the host candidate's account to the anomalies.
SELECT audit_id, ts, account, object, record_id, action, detail
FROM audit_log
WHERE account = 'hlr.minase.i'
  AND (object IN ('data_dictionary', 'infirmary_config')
       OR action = 'reassign_id'
       OR (object = 'device_firmware' AND detail LIKE '%v2.3%'))
ORDER BY ts, audit_id;

-- Roster and healer evidence behind the inferred account match.
SELECT sorcerer_id, name, technique, status
FROM clean_sorcerers WHERE sorcerer_id = 'S-0033';
SELECT COUNT(*) AS healer_sessions
FROM healer_sessions WHERE healer_id = 'S-0033';

-- A Drop 1 false-positive explanation.
SELECT visit_id, session_id, healer_id, start_ts, overlap_type
FROM healer_visit_overlap
WHERE sorcerer_id = 'S-0663'
  AND visit_id IN ('V-001738', 'V-002196')
ORDER BY visit_id, start_ts;

-- Device anomaly, raw readings, without guessing its cause.
SELECT firmware, COUNT(*) AS readings,
       SUM(CAST(ce_level AS REAL) > 0) AS positive,
       ROUND(100.0 * SUM(CAST(ce_level AS REAL) > 0) / COUNT(*), 2) AS positive_pct
FROM ce_wearable GROUP BY firmware;
```

Recovery medians and visit-level candidate evidence are computed in
`target\answers.txt`; SQLite installations need not support percentile
functions.
