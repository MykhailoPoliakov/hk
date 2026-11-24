"""Export small, screening-aligned CSV data sources for Looker Studio."""

import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rct import RctEvidence, find_rct_candidates


DASHBOARD_DATA_DIRECTORY = Path("dashboard") / "dashboard_data"
CSV_FILES = (
    "candidates.csv", "visits.csv", "readings.csv", "stages.csv",
    "rejection_evidence.csv", "timing_quality.csv", "firmware_quality.csv",
)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)


def _screen_before_healer(
    final: sqlite3.Connection, *, original_timestamps: bool
) -> dict[str, list[RctEvidence]]:
    discharge = (
        "CASE WHEN v.timestamp_assumption='inferred_discharge_utc' "
        "THEN strftime('%Y-%m-%dT%H:%M:%SZ', v.discharged_at_utc, '-9 hours') "
        "ELSE v.discharged_at_utc END"
        if original_timestamps else "v.discharged_at_utc"
    )
    hours = (
        "CASE WHEN v.timestamp_assumption='inferred_discharge_utc' "
        "THEN v.estimated_recovery_hours-9 ELSE v.estimated_recovery_hours END"
        if original_timestamps else "v.estimated_recovery_hours"
    )
    final.execute(
        "CREATE TEMP VIEW infirmary_visits AS "
        "SELECT v.visit_id, v.sorcerer_id, v.mission_id, v.admitted_at_utc AS admitted_at, "
        f"{discharge} AS discharged_at, CAST(v.severity AS INTEGER) AS severity, "
        f"v.identity_review, {hours} AS recovery_hours "
        "FROM raw.estimated_infirmary_visits v JOIN main.missions m ON m.mission_id=v.mission_id "
        "WHERE v.estimated_timing_status='usable_under_assumption' "
        "AND v.missing_mission=0 AND v.test_code_review=0"
    )
    try:
        return find_rct_candidates(final)
    finally:
        final.execute("DROP VIEW temp.infirmary_visits")


def export_dashboard(database: Path, final_database: Path, output: Path) -> dict[str, int]:
    """Write all CSVs using existing raw and curated databases."""
    output.mkdir(parents=True, exist_ok=True)
    raw_uri = Path(database).resolve().as_uri() + "?mode=ro"
    final_uri = Path(final_database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(raw_uri, uri=True)) as raw, \
            closing(sqlite3.connect(final_uri, uri=True)) as final:
        final.execute("ATTACH DATABASE ? AS raw", (raw_uri,))
        healer_available = bool(raw.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='healer_sessions'"
        ).fetchone())
        candidates = find_rct_candidates(final)
        before_timing = _screen_before_healer(final, original_timestamps=True)
        before_healer = _screen_before_healer(final, original_timestamps=False)
        stages = (
            ("Before inferred timestamp correction", before_timing),
            ("After inferred timestamp correction, before healer filter", before_healer),
            ("After recorded healer filter" if healer_available else "Healer data unavailable", candidates),
        )

        candidate_rows = []
        visit_rows = []
        reading_rows = []
        for sid, evidence in candidates.items():
            roster = final.execute(
                "SELECT name, grade, school, status FROM sorcerers WHERE sorcerer_id=?", (sid,)
            ).fetchone()
            if roster is None:
                raise ValueError(f"Missing roster entry for candidate {sid}")
            name, grade, school, status = roster
            candidate_rows.append((sid, name, grade, school, status, len(evidence)))
            for item in sorted(evidence, key=lambda event: event.visit_id):
                visit = final.execute(
                    "SELECT mission_id, admitted_at, discharged_at, injury_code, timestamp_assumption "
                    "FROM infirmary_visits WHERE visit_id=? AND sorcerer_id=?",
                    (item.visit_id, sid),
                ).fetchone()
                if visit is None:
                    raise ValueError(f"Missing qualifying visit {item.visit_id} for {sid}")
                mission, admitted, discharged, injury, assumption = visit
                healer_status = "no_recorded_overlap" if healer_available else "unknown_no_healer_data"
                visit_rows.append((
                    sid, name, grade, school, item.visit_id, mission, item.severity, injury,
                    admitted, discharged, round(item.recovery_hours, 4), item.positive_readings,
                    item.longest_positive_streak, item.device_id, item.firmware,
                    healer_status, assumption,
                ))
                for device, timestamp, level, firmware in final.execute(
                    "SELECT device_id, ts, ce_level, firmware FROM ce_wearable "
                    "WHERE sorcerer_id=? AND ts>=? AND ts<? ORDER BY ts, device_id",
                    (sid, admitted, discharged),
                ):
                    reading_rows.append((
                        sid, name, grade, school, item.visit_id, device, timestamp,
                        timestamp.replace("T", " ").removesuffix("Z"), level, firmware,
                    ))

        stage_rows = []
        all_ids = sorted(set().union(*(set(screen) for _, screen in stages)))
        for index, (label, screen) in enumerate(stages):
            previous = stages[index - 1][1] if index else {}
            for sid in all_ids:
                present = sid in screen
                was_present = sid in previous
                if index == 0:
                    reason = "Initial diagnostic" if present else "Not in initial diagnostic"
                elif was_present and not present:
                    reason = ("No longer meets screen after inferred timestamp correction"
                              if index == 1 else "No longer meets screen after recorded healer filter")
                elif present and not was_present:
                    reason = "Meets screen at this stage"
                elif present:
                    reason = "Still meets screen"
                else:
                    reason = "Not in this stage"
                stage_rows.append((index + 1, label, sid, int(present), len(screen.get(sid, [])), reason))

        rejection_rows = []
        for index in (1, 2):
            previous = stages[index - 1][1]
            current = stages[index][1]
            for sid in sorted(set(previous) - set(current)):
                for item in sorted(previous[sid], key=lambda event: event.visit_id):
                    corrected = raw.execute(
                        "SELECT estimated_recovery_hours FROM estimated_infirmary_visits WHERE visit_id=?",
                        (item.visit_id,),
                    ).fetchone()
                    if corrected is None:
                        raise ValueError(f"Missing corrected visit {item.visit_id} for {sid}")
                    sessions = []
                    if index == 2 and healer_available:
                        sessions = raw.execute(
                            "SELECT session_id, healer_id, start_ts FROM healer_visit_overlap "
                            "WHERE visit_id=? ORDER BY start_ts, session_id", (item.visit_id,)
                        ).fetchall()
                    rejection_rows.append((
                        index + 1, sid, item.visit_id, round(item.recovery_hours, 4),
                        round(corrected[0], 4) if corrected[0] is not None else "",
                        "; ".join(f"{session} by {healer} at {start}" for session, healer, start in sessions),
                        ("Candidate no longer meets the repeated-visit screen after timestamp correction"
                         if index == 1 else
                         "Candidate no longer meets the repeated-visit screen after the healer filter"),
                    ))

        timing = raw.execute(
            "SELECT SUM(estimated_timing_status!='unresolved' AND timing_status='negative_duration'), "
            "SUM(estimated_timing_status='negative_duration'), "
            "SUM(estimated_timing_status='unresolved') FROM estimated_infirmary_visits"
        ).fetchone()
        if timing is None or any(value is None for value in timing):
            raise ValueError("No visits available for timing quality chart")
        before_negative, after_negative, unresolved = timing
        timing_rows = [
            ("Before inferred timezone correction", before_negative, unresolved),
            ("After inferred timezone correction", after_negative, unresolved),
        ]
        firmware_rows = []
        for firmware, total, positive in raw.execute(
            "SELECT firmware, COUNT(*), SUM(CAST(ce_level AS REAL)>0) "
            "FROM ce_wearable GROUP BY firmware ORDER BY firmware"
        ):
            firmware_rows.append((firmware, total, positive, positive / total))

    tables = (
        ("candidates.csv", ("sorcerer_id", "name", "grade", "school", "status", "qualifying_visits"), candidate_rows),
        ("visits.csv", ("sorcerer_id", "name", "grade", "school", "visit_id", "mission_id",
                        "severity", "injury_code", "admitted_at_utc", "discharged_at_utc",
                        "recovery_hours", "positive_readings", "longest_positive_streak",
                        "first_positive_device", "first_positive_firmware", "healer_status",
                        "timestamp_assumption"), visit_rows),
        ("readings.csv", ("sorcerer_id", "name", "grade", "school", "visit_id", "device_id",
                          "timestamp_utc", "timestamp_display_utc", "ce_level", "firmware"), reading_rows),
        ("stages.csv", ("stage_order", "stage", "sorcerer_id", "included", "qualifying_visits", "reason"), stage_rows),
        ("rejection_evidence.csv", ("stage_order", "sorcerer_id", "visit_id", "before_recovery_hours",
                                    "corrected_recovery_hours", "overlapping_healer_sessions", "reason"), rejection_rows),
        ("timing_quality.csv", ("interpretation", "negative_intervals", "unresolved_intervals"), timing_rows),
        ("firmware_quality.csv", ("firmware", "total_readings", "positive_readings", "positive_rate"), firmware_rows),
    )
    for filename, columns, rows in tables:
        _write_csv(output / filename, columns, rows)
    return {filename: len(rows) for filename, _, rows in tables}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild dashboard CSVs from existing SQLite databases.")
    parser.add_argument("--database", type=Path, default=ROOT / "data.db")
    parser.add_argument("--final-database", type=Path, default=ROOT / "final.db")
    parser.add_argument("--output", type=Path, default=ROOT / DASHBOARD_DATA_DIRECTORY)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dashboard-", dir=args.output) as directory:
        staging = Path(directory)
        counts = export_dashboard(args.database, args.final_database, staging)
        for name in CSV_FILES:
            os.replace(staging / name, args.output / name)
    for name, count in counts.items():
        print(f"{name}: {count:,} rows")


if __name__ == "__main__":
    main()
