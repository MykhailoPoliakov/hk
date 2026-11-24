import math
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def validate_source(connection: sqlite3.Connection) -> None:
    checks = (
        ("duplicate sorcerer ID", "SELECT sorcerer_id FROM source.sorcerers GROUP BY sorcerer_id HAVING COUNT(*) > 1 LIMIT 1"),
        ("invalid sorcerer", "SELECT sorcerer_id FROM source.sorcerers WHERE sorcerer_id = '' OR "
         "grade NOT IN ('1','2','3','4','Special') OR school NOT IN ('Tokyo','Kyoto') "
         "OR status NOT IN ('active','deceased') OR date(join_date) IS NULL LIMIT 1"),
        ("duplicate ward code", "SELECT ward_code FROM source.wards GROUP BY ward_code HAVING COUNT(*) > 1 LIMIT 1"),
        ("duplicate ward name", "SELECT ward_name FROM source.wards GROUP BY ward_name HAVING COUNT(*) > 1 LIMIT 1"),
        ("invalid ward", "SELECT ward_code FROM source.wards WHERE ward_code = '' OR ward_name = '' "
         "OR city NOT IN ('Tokyo','Kyoto') LIMIT 1"),
        ("invalid mission", "SELECT mission_id FROM source.missions WHERE mission_id = '' "
         "OR datetime(start_ts) IS NULL OR datetime(end_ts) IS NULL "
         "OR substr(start_ts,-1) != 'Z' OR substr(end_ts,-1) != 'Z' "
         "OR datetime(end_ts) < datetime(start_ts) "
         "OR outcome NOT IN ('exorcised','sealed','withdrawn','failed') "
         "OR curse_grade NOT IN ('1','2','3','4','Special') LIMIT 1"),
        ("unknown sensor ward", "SELECT b.ward_code FROM source.barrier_sensors b "
         "LEFT JOIN source.wards w ON w.ward_code=b.ward_code WHERE w.ward_code IS NULL LIMIT 1"),
        ("invalid sensor timestamp", "SELECT rowid FROM source.barrier_sensors "
         "WHERE datetime(ts) IS NULL OR substr(ts,-1) != 'Z' LIMIT 1"),
        ("invalid infirmary severity", "SELECT visit_id, severity FROM source.effective_infirmary_visits "
         "WHERE severity IS NULL OR severity NOT IN ('1','2','3','4','5') LIMIT 1"),
        ("unresolved sorcerer name", "SELECT sorcerer_id, original_name FROM source.clean_sorcerers "
         "WHERE name_status = 'unresolved' LIMIT 1"),
    )
    for label, query in checks:
        problem = connection.execute(query).fetchone()
        if problem is not None:
            raise ValueError(f"{label}: {problem}")

    roster = {row[0] for row in connection.execute("SELECT sorcerer_id FROM source.sorcerers")}
    missions = {}
    for mission, participants, casualties in connection.execute(
        "SELECT mission_id, sorcerer_ids, casualties FROM source.clean_missions WHERE conflicting_mission_id = 0"
    ):
        assigned = [value.strip() for value in participants.split("|") if value.strip()]
        killed = [value.strip() for value in casualties.split("|") if value.strip()]
        if (not assigned or len(set(assigned)) != len(assigned)
                or any(value not in roster for value in assigned)
                or any(value not in assigned for value in killed)):
            raise ValueError(f"Invalid mission participants or casualties: {mission}")
        missions[mission] = set(assigned)
    for visit, sorcerer, mission in connection.execute(
        "SELECT visit_id, sorcerer_id, mission_id FROM source.effective_infirmary_visits"
    ):
        if sorcerer not in roster:
            raise ValueError(f"Unknown sorcerer for visit {visit}: {sorcerer}")
        if mission and (mission not in missions or sorcerer not in missions[mission]):
            raise ValueError(f"Missing or inconsistent mission for visit {visit}: {mission}")

    for table, column in (("ce_wearable", "ce_level"), ("barrier_sensors", "residual_ce")):
        for rowid, value in connection.execute(f"SELECT rowid, {column} FROM source.{table}"):
            if not isinstance(value, str) or not NUMBER.fullmatch(value.strip()):
                raise ValueError(f"Invalid {table}.{column} at source row {rowid}: {value!r}")
            if not math.isfinite(float(value)):
                raise ValueError(f"Non-finite {table}.{column} at source row {rowid}: {value!r}")

    for rowid, timestamp in connection.execute("SELECT rowid, ts FROM source.ce_wearable"):
        try:
            if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
                raise ValueError("UTC Z suffix required")
            datetime.fromisoformat(timestamp[:-1] + "+00:00")
        except ValueError as error:
            raise ValueError(f"Invalid wearable timestamp at source row {rowid}: {timestamp!r}") from error


def create_final_database(raw_database: Path, final_database: Path) -> None:
    """Materialize the analysis tables without changing the raw database."""
    raw_database = Path(raw_database)
    final_database = Path(final_database)
    with final_database.open("xb"):
        pass
    completed = False
    try:
        connection = sqlite3.connect(final_database.as_uri(), uri=True)
        try:
            with connection:
                connection.execute("ATTACH DATABASE ? AS source", (raw_database.resolve().as_uri() + "?mode=ro",))
                validate_source(connection)
                connection.executescript(
                """
                BEGIN;
                CREATE TABLE sorcerers AS
                    SELECT sorcerer_id, name, grade, school, technique, join_date, status,
                           earlier_casualty_records
                    FROM source.reviewed_sorcerers;
                CREATE TABLE wards AS SELECT * FROM source.wards;
                CREATE TABLE missions AS
                    SELECT mission_id, start_ts, end_ts, ward, curse_grade, sorcerer_ids,
                           outcome, casualties, report_text
                    FROM source.clean_missions
                    WHERE ward_status != 'unmatched' AND conflicting_mission_id = 0;
                CREATE TABLE mission_casualties AS
                    SELECT c.* FROM source.mission_casualties c
                    JOIN missions m ON m.mission_id = c.mission_id
                    WHERE c.conflicting_mission_id = 0;
                CREATE TABLE infirmary_visits AS
                    SELECT v.visit_id, v.sorcerer_id, v.mission_id,
                           v.admitted_at_utc AS admitted_at, v.discharged_at_utc AS discharged_at,
                           v.injury_code, CAST(v.severity AS INTEGER) AS severity, v.admitted_from,
                           v.estimated_recovery_hours AS recovery_hours,
                           v.timestamp_assumption, v.identity_review,
                           COALESCE(h.has_healer_overlap, 0) AS has_external_healer
                    FROM source.estimated_infirmary_visits v
                    LEFT JOIN source.visits_with_external_healing h ON h.visit_id = v.visit_id
                    JOIN missions m ON m.mission_id = v.mission_id
                    WHERE v.estimated_timing_status = 'usable_under_assumption'
                      AND v.missing_mission = 0 AND v.test_code_review = 0
                      AND COALESCE(h.has_healer_overlap, 0) = 0;
                CREATE TABLE device_assignments AS
                    SELECT device_id, sorcerer_id, valid_from, valid_to, current_holder_join_date
                    FROM source.reviewed_device_assignments
                    WHERE assignment_review = 'valid';
                CREATE TABLE ce_wearable AS
                    SELECT reading_rowid AS source_rowid, device_id, sorcerer_id, ts,
                           CAST(ce_level AS REAL) AS ce_level, firmware
                    FROM source.attributed_ce_wearable
                    WHERE attribution_review = 'not_before_current_join_date'
                      AND firmware IN ('v2.2', 'v2.4');
                CREATE TABLE barrier_sensors AS
                    SELECT b.ward_code, b.ts, CAST(b.residual_ce AS REAL) AS residual_ce, w.city,
                           CASE WHEN w.city = 'Kyoto' THEN 1 ELSE 0 END AS unit_review_required
                    FROM source.barrier_sensors b JOIN wards w ON w.ward_code = b.ward_code;
                CREATE TABLE data_assumptions (name TEXT NOT NULL, detail TEXT NOT NULL);
                INSERT INTO data_assumptions VALUES
                    ('timestamps', 'Admissions are treated as JST. For missions starting before '
                     || '2026-02-28T00:00:00Z, discharges are treated as JST; after that, '
                     || 'discharges are treated as UTC. The cutoff and change are inferred, not confirmed.'),
                    ('wearables', 'v2.3 and unknown firmware, unmatched or ambiguous assignments, '
                     || 'and readings before or on the current holder join date are excluded.'),
                    ('barrier_units', 'Residual energy remains in recorded units; Kyoto units require review.'),
                    ('names', 'Reversed-looking names are reversed when both resulting name components '
                     || 'occur in normally formatted roster names; the original is preserved in data.db.'),
                    ('missing_technique', 'Blank technique values remain missing; they are not inferred.'),
                    ('severity', 'Severity remains the recorded code; its clinical meaning is unverified.'),
                    ('drop', 'See the source tables for the available drop and correction history.');
                CREATE UNIQUE INDEX missions_id ON missions(mission_id);
                CREATE UNIQUE INDEX infirmary_visit_id ON infirmary_visits(visit_id);
                CREATE UNIQUE INDEX sorcerer_id ON sorcerers(sorcerer_id);
                CREATE UNIQUE INDEX ward_code ON wards(ward_code);
                CREATE INDEX ce_sorcerer_ts ON ce_wearable(sorcerer_id, ts);
                CREATE UNIQUE INDEX ce_device_ts ON ce_wearable(device_id, ts);
                CREATE UNIQUE INDEX barrier_ward_ts ON barrier_sensors(ward_code, ts);
                COMMIT;
                """
            )
        finally:
            connection.close()
        completed = True
    finally:
        if not completed:
            final_database.unlink()
