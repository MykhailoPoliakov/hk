DROP VIEW IF EXISTS clean_sorcerers;
CREATE VIEW clean_sorcerers AS
WITH RECURSIVE
normal_names AS (
    SELECT name, instr(name, ' ') AS separator
    FROM sorcerers
    WHERE substr(name, 1, 1) GLOB '[A-Z]'
      AND instr(name, ' ') > 1
      AND substr(name, instr(name, ' ') + 1, 1) GLOB '[A-Z]'
),
given_names AS (
    SELECT DISTINCT substr(name, 1, separator - 1) AS value FROM normal_names
),
family_names AS (
    SELECT DISTINCT substr(name, separator + 1) AS value FROM normal_names
),
reversed(source_rowid, position, name) AS (
    SELECT rowid, length(name), '' FROM sorcerers
    UNION ALL
    SELECT r.source_rowid, r.position - 1, r.name || substr(s.name, r.position, 1)
    FROM reversed r
    JOIN sorcerers s ON s.rowid = r.source_rowid
    WHERE position > 0
),
name_candidates AS (
    SELECT source_rowid, name, instr(name, ' ') AS separator
    FROM reversed WHERE position = 0
)
SELECT
    s.sorcerer_id,
    CASE
        WHEN substr(s.name, 1, 1) GLOB '[a-z]' AND substr(s.name, -1, 1) GLOB '[A-Z]'
             AND c.separator > 1
             AND EXISTS (SELECT 1 FROM given_names WHERE value = substr(c.name, 1, c.separator - 1))
             AND EXISTS (SELECT 1 FROM family_names WHERE value = substr(c.name, c.separator + 1))
        THEN c.name
        ELSE s.name
    END AS name,
    s.grade, s.school, s.technique, s.join_date, s.status,
    s.name AS original_name,
    CASE
        WHEN substr(s.name, 1, 1) GLOB '[a-z]' AND substr(s.name, -1, 1) GLOB '[A-Z]'
             AND c.separator > 1
             AND EXISTS (SELECT 1 FROM given_names WHERE value = substr(c.name, 1, c.separator - 1))
             AND EXISTS (SELECT 1 FROM family_names WHERE value = substr(c.name, c.separator + 1))
        THEN 'reversed'
        WHEN substr(s.name, 1, 1) GLOB '[a-z]' AND substr(s.name, -1, 1) GLOB '[A-Z]'
        THEN 'unresolved'
        ELSE 'original'
    END AS name_status
FROM sorcerers s
JOIN name_candidates c ON c.source_rowid = s.rowid;
