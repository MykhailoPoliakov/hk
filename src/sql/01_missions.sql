-- Exact duplicate rows are removed; conflicting rows for the same ID remain.
DROP VIEW IF EXISTS clean_missions;
CREATE VIEW clean_missions AS
WITH RECURSIVE
distinct_missions AS (
    SELECT DISTINCT * FROM missions
),
mission_counts AS (
    SELECT mission_id, COUNT(*) AS distinct_row_count
    FROM distinct_missions
    GROUP BY mission_id
),
reversed_wards(ward_name, position, reversed_name) AS (
    SELECT ward_name, length(ward_name), '' FROM wards
    UNION ALL
    SELECT ward_name, position - 1, reversed_name || substr(ward_name, position, 1)
    FROM reversed_wards
    WHERE position > 0
),
reverse_matches AS (
    SELECT reversed_name, MIN(ward_name) AS ward_name, COUNT(DISTINCT ward_name) AS matches
    FROM reversed_wards
    WHERE position = 0
    GROUP BY reversed_name
)
SELECT
    m.mission_id,
    m.start_ts,
    m.end_ts,
    CASE
        WHEN EXISTS (SELECT 1 FROM wards w WHERE w.ward_name = m.ward) THEN m.ward
        WHEN r.matches = 1 THEN r.ward_name
        ELSE m.ward
    END AS ward,
    m.ward AS original_ward,
    CASE
        WHEN EXISTS (SELECT 1 FROM wards w WHERE w.ward_name = m.ward) THEN 'original'
        WHEN r.matches = 1 THEN 'reversed'
        ELSE 'unmatched'
    END AS ward_status,
    m.curse_grade,
    m.sorcerer_ids,
    m.outcome,
    m.casualties,
    m.report_text,
    c.distinct_row_count > 1 AS conflicting_mission_id
FROM distinct_missions m
JOIN mission_counts c ON c.mission_id = m.mission_id
LEFT JOIN reverse_matches r ON r.reversed_name = m.ward;
