DROP VIEW IF EXISTS reviewed_sorcerers;
DROP VIEW IF EXISTS mission_casualties;

CREATE VIEW mission_casualties AS
WITH RECURSIVE split(mission_id, start_ts, end_ts, conflicting_mission_id, remaining, sorcerer_id) AS (
    SELECT mission_id, start_ts, end_ts, conflicting_mission_id, casualties || '|', ''
    FROM clean_missions
    WHERE casualties IS NOT NULL AND casualties != ''
    UNION ALL
    SELECT mission_id, start_ts, end_ts, conflicting_mission_id,
           substr(remaining, instr(remaining, '|') + 1),
           trim(substr(remaining, 1, instr(remaining, '|') - 1))
    FROM split
    WHERE remaining != ''
)
SELECT DISTINCT mission_id, start_ts, end_ts, sorcerer_id, conflicting_mission_id
FROM split
WHERE sorcerer_id != '';

-- A casualty before the current holder joined is evidence of ID reuse or another
-- identity inconsistency. Do not assign the historical casualty to the holder.
CREATE VIEW reviewed_sorcerers AS
SELECT
    s.*,
    (
        SELECT COUNT(*)
        FROM mission_casualties c
        WHERE c.sorcerer_id = s.sorcerer_id
          AND date(c.end_ts) < date(s.join_date)
    ) AS earlier_casualty_records
FROM clean_sorcerers s;
