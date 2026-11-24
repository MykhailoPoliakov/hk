import sqlite3
import statistics
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

from rct import find_rct_candidates


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data.db"
FINAL_DATABASE = ROOT / "final.db"
OUTPUT = ROOT / "target" / "answers.txt"
SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"


def load_temporary_views(connection: sqlite3.Connection, filename: str, names: tuple[str, ...]) -> None:
    """Reuse the cleaning SQL without changing the source database."""
    script = (SQL_DIRECTORY / filename).read_text(encoding="utf-8")
    for name in names:
        drop = f"DROP VIEW IF EXISTS {name};"
        create = f"CREATE VIEW {name} AS"
        if script.count(drop) != 1 or script.count(create) != 1:
            raise ValueError(f"Unexpected view definition in {filename}: {name}")
        script = script.replace(drop, f"DROP VIEW IF EXISTS temp.{name};", 1)
        script = script.replace(create, f"CREATE TEMP VIEW {name} AS", 1)
    connection.executescript(script)


def generate_answers(
    database: Path = DATABASE, output: Path = OUTPUT, final_database: Path = FINAL_DATABASE,
) -> None:
    database_uri = Path(database).resolve().as_uri() + "?mode=ro"
    final_uri = Path(final_database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection, \
            closing(sqlite3.connect(final_uri, uri=True)) as final:
        load_temporary_views(connection, "00_sorcerers.sql", ("clean_sorcerers",))
        load_temporary_views(connection, "01_missions.sql", ("clean_missions",))
        load_temporary_views(connection, "02_infirmary_visits.sql", ("clean_infirmary_visits",))
        load_temporary_views(connection, "04_identity.sql", ("mission_casualties", "reviewed_sorcerers"))
        load_temporary_views(
            connection,
            "05_context.sql",
            ("reviewed_infirmary_visits", "reviewed_device_assignments", "attributed_ce_wearable"),
        )
        load_temporary_views(connection, "06_estimated_timestamps.sql", ("estimated_infirmary_visits",))
        has_healer_data = bool(connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='healer_sessions'"
        ).fetchone())
        has_corrections = bool(connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='infirmary_corrections'"
        ).fetchone())
        if has_healer_data:
            load_temporary_views(connection, "07_healer_sessions.sql", ("healer_visit_overlap", "visits_with_external_healing"))
        drop = 2 if has_corrections else 1 if has_healer_data else 0
        correction_lines = []
        audit_lines = []
        bonus_lines = []
        if has_corrections:
            correction_counts = dict(connection.execute(
                "SELECT op, COUNT(*) FROM correction_history GROUP BY op"
            ))
            correction_lines = [
                f"Drop 2 correction feed: {correction_counts.get('I', 0):,} inserts, "
                f"{correction_counts.get('U', 0):,} updates, {correction_counts.get('D', 0):,} deletes; "
                "applied in sequence to the visit snapshot, with before/after history retained."
            ]
            audit_lines = [
                f"  Audit {audit_id} at {timestamp}: {account}, {object_name}, {record_id}, {action}, {detail}."
                for audit_id, timestamp, account, object_name, record_id, action, detail in connection.execute(
                    "SELECT audit_id, ts, account, object, record_id, action, detail FROM audit_log "
                    "WHERE object IN ('data_dictionary', 'infirmary_config') OR action='reassign_id' "
                    "ORDER BY ts, audit_id"
                )
            ]
            suspects = connection.execute(
                "SELECT account, SUM(object='device_firmware' AND detail LIKE '%v2.3%'), "
                "SUM(object='data_dictionary' AND record_id='infirmary_visits.severity'), "
                "SUM(object='infirmary_config' AND record_id='discharge_terminal'), "
                "SUM(action='reassign_id') FROM audit_log GROUP BY account "
                "HAVING SUM(object='device_firmware' AND detail LIKE '%v2.3%') > 0 "
                "AND SUM(object='data_dictionary' AND record_id='infirmary_visits.severity') > 0 "
                "AND SUM(object='infirmary_config' AND record_id='discharge_terminal') > 0 "
                "AND SUM(action='reassign_id') > 0"
            ).fetchall()
            bonus_lines.append("Bonus - Host: inference from audit account and roster, not direct proof of account ownership.")
            if not suspects:
                bonus_lines.append("  No account matches all four observed audit patterns; investigate manually.")
            for account, firmware_pushes, dictionary_edits, clock_changes, reassignments in suspects:
                parts = account.split(".")
                matches = []
                if len(parts) == 3 and parts[0] == "hlr" and len(parts[2]) == 1:
                    for sid, name in connection.execute("SELECT sorcerer_id, name FROM clean_sorcerers"):
                        names = name.split()
                        if len(names) == 2 and names[1].casefold() == parts[1].casefold() and names[0][0].casefold() == parts[2].casefold():
                            sessions = connection.execute(
                                "SELECT COUNT(*) FROM healer_sessions WHERE healer_id=?", (sid,)
                            ).fetchone()[0]
                            matches.append((sid, name, sessions))
                bonus_lines.append(
                    f"  Account {account}: {firmware_pushes} v2.3 pushes, {dictionary_edits} severity-dictionary edit(s), "
                    f"{clock_changes} discharge-clock change(s), {reassignments} ID reassignment(s)."
                )
                bonus_lines.extend(
                    f"  Matching roster: {sid}, {name}; {sessions} recorded sessions as healer."
                    for sid, name, sessions in matches
                )
                if len(matches) != 1:
                    bonus_lines.append(f"  Account-to-roster mapping is ambiguous ({len(matches)} matches).")

        def scalar(query: str) -> int:
            return connection.execute(query).fetchone()[0]

        mission_rows = scalar("SELECT COUNT(*) FROM missions")
        distinct_missions = scalar("SELECT COUNT(DISTINCT mission_id) FROM missions")
        deduplicated_rows = scalar("SELECT COUNT(*) FROM clean_missions")
        conflicts = scalar("SELECT COUNT(DISTINCT mission_id) FROM clean_missions WHERE conflicting_mission_id")
        reversed_names = scalar("SELECT COUNT(*) FROM clean_sorcerers WHERE name_status = 'reversed'")
        reversed_wards = scalar("SELECT COUNT(*) FROM clean_missions WHERE ward_status = 'reversed'")
        unmatched_wards = scalar("SELECT COUNT(*) FROM clean_missions WHERE ward_status = 'unmatched'")
        ward_count = final.execute("SELECT COUNT(DISTINCT ward) FROM missions").fetchone()[0]
        final_missions = final.execute("SELECT COUNT(DISTINCT mission_id) FROM missions").fetchone()[0]

        residuals: dict[str, list[float]] = defaultdict(list)
        unmatched_sensors = scalar(
            "SELECT COUNT(*) FROM barrier_sensors b LEFT JOIN wards w USING (ward_code) "
            "WHERE w.ward_code IS NULL"
        )
        for city, value in final.execute("SELECT city, residual_ce FROM barrier_sensors"):
            residuals[city].append(float(value))
        if unmatched_sensors or not all(residuals.get(city) for city in ("Tokyo", "Kyoto")):
            raise ValueError("Barrier sensor rows have unmatched wards or a city has no readings")

        casualties: set[str] = set()
        for (sorcerer_id,) in final.execute(
            "SELECT sorcerer_id FROM mission_casualties "
            "WHERE datetime(start_ts) >= '2025-05-01 00:00:00' "
            "AND datetime(start_ts) < '2026-11-01 00:00:00'"
        ):
            casualties.add(sorcerer_id)
        statuses = dict(connection.execute("SELECT sorcerer_id, status FROM sorcerers"))
        active_casualties = sorted(sid for sid in casualties if statuses.get(sid) == "active")
        unknown_casualties = sorted(sid for sid in casualties if sid not in statuses)
        reused_id_evidence = connection.execute(
            "SELECT s.sorcerer_id, s.join_date, MIN(c.end_ts) "
            "FROM reviewed_sorcerers s JOIN mission_casualties c USING (sorcerer_id) "
            "WHERE date(c.end_ts) < date(s.join_date) GROUP BY s.sorcerer_id, s.join_date "
            "ORDER BY s.sorcerer_id"
        ).fetchall()
        pre_join_visits = scalar(
            "SELECT COUNT(*) FROM reviewed_infirmary_visits "
            "WHERE identity_review = 'before_current_join_date'"
        )

        recovery: dict[int, list[float]] = defaultdict(list)
        timing_counts: Counter[str] = Counter()
        normalized_codes = 0
        missing_mission = 0
        test_code_count = 0
        for severity, hours, status, code, original_code, mission_id in connection.execute(
            "SELECT severity, recovery_hours, timing_status, injury_code, "
            "original_injury_code, mission_id FROM clean_infirmary_visits"
        ):
            timing_counts[status] += 1
            normalized_codes += code != original_code
            missing_mission += not mission_id
            test_code_count += code == "TST-00"
        for severity, hours in connection.execute(
            "SELECT v.severity, v.estimated_recovery_hours FROM estimated_infirmary_visits v "
            "JOIN clean_missions m ON m.mission_id=v.mission_id "
            "WHERE v.estimated_timing_status='usable_under_assumption' "
            "AND v.missing_mission=0 AND v.test_code_review=0 "
            "AND m.ward_status!='unmatched' AND m.conflicting_mission_id=0"
        ):
            recovery[int(severity)].append(hours)
        recovery_visits = sum(len(values) for values in recovery.values())
        raw_missing = scalar("SELECT COUNT(*) FROM infirmary_visits WHERE mission_id IS NULL OR mission_id=''")
        raw_test_codes = scalar("SELECT COUNT(*) FROM infirmary_visits WHERE injury_code='TST-00'")
        original_code_variants = scalar(
            "SELECT COUNT(*) FROM infirmary_visits v "
            "WHERE v.injury_code GLOB '[a-zA-Z][a-zA-Z][a-zA-Z][0-9][0-9]' "
            "AND EXISTS (SELECT 1 FROM infirmary_visits r WHERE r.injury_code = "
            "upper(substr(v.injury_code, 1, 3)) || '-' || substr(v.injury_code, 4, 2))"
        )

        inferred_times = scalar(
            "SELECT COUNT(*) FROM estimated_infirmary_visits "
            "WHERE timestamp_assumption = 'inferred_discharge_utc'"
        )
        remaining_negative = scalar(
            "SELECT COUNT(*) FROM estimated_infirmary_visits "
            "WHERE estimated_timing_status = 'negative_duration'"
        )
        firmware = {
            version: (total, positives)
            for version, total, positives in connection.execute(
                "SELECT firmware, COUNT(*), SUM(CAST(ce_level AS REAL) > 0) "
                "FROM ce_wearable GROUP BY firmware"
            )
        }
        firmware_lines = [
            f"  {version}: {positive:,} / {total:,} positive ({positive / total:.2%})"
            for version, (total, positive) in sorted(firmware.items())
        ]
        medians = [
            f"  Recorded severity {severity}: {statistics.median(values):.2f} hours "
            f"({len(values):,} included visits)"
            for severity, values in sorted(recovery.items())
        ]
        if not medians:
            raise ValueError("No valid recovery intervals found")
        negative = timing_counts["negative_duration"]
        invalid = timing_counts["invalid_timestamp"]
        tokyo = statistics.median(residuals["Tokyo"])
        kyoto = statistics.median(residuals["Kyoto"])
        candidates = find_rct_candidates(final)
        healer_removed_details = []
        if has_healer_data:
            final.execute("ATTACH DATABASE ? AS raw", (database_uri,))
            final.execute(
                "CREATE TEMP VIEW infirmary_visits AS "
                "SELECT v.visit_id, v.sorcerer_id, v.mission_id, v.admitted_at_utc AS admitted_at, "
                "v.discharged_at_utc AS discharged_at, CAST(v.severity AS INTEGER) AS severity, "
                "v.identity_review, v.estimated_recovery_hours AS recovery_hours "
                "FROM raw.estimated_infirmary_visits v JOIN main.missions m ON m.mission_id=v.mission_id "
                "WHERE v.estimated_timing_status='usable_under_assumption' "
                "AND v.missing_mission=0 AND v.test_code_review=0"
            )
            try:
                before_healer_filter = find_rct_candidates(final)
            finally:
                final.execute("DROP VIEW temp.infirmary_visits")
            for sid in sorted(set(before_healer_filter) - set(candidates)):
                for item in before_healer_filter[sid]:
                    sessions = connection.execute(
                        "SELECT session_id, healer_id, start_ts FROM healer_visit_overlap "
                        "WHERE visit_id=? ORDER BY start_ts", (item.visit_id,)
                    ).fetchall()
                    if sessions:
                        healer_removed_details.append(
                            f"  {sid}, {item.visit_id}: "
                            + "; ".join(f"{session} by {healer} at {start}" for session, healer, start in sessions)
                        )
        final.execute(
            "CREATE TEMP VIEW infirmary_visits AS "
            "SELECT visit_id, sorcerer_id, mission_id, admitted_at, "
            "CASE WHEN timestamp_assumption='inferred_discharge_utc' "
            "THEN strftime('%Y-%m-%dT%H:%M:%SZ', discharged_at, '-9 hours') "
            "ELSE discharged_at END AS discharged_at, severity, identity_review, "
            "CASE WHEN timestamp_assumption='inferred_discharge_utc' "
            "THEN recovery_hours - 9 ELSE recovery_hours END AS recovery_hours "
            "FROM main.infirmary_visits"
        )
        try:
            uncorrected_candidates = find_rct_candidates(final)
        finally:
            final.execute("DROP VIEW temp.infirmary_visits")
        removed_candidates = sorted(set(uncorrected_candidates) - set(candidates))
        removed_details = []
        for sorcerer_id in removed_candidates:
            for item in uncorrected_candidates[sorcerer_id]:
                corrected = final.execute(
                    "SELECT recovery_hours FROM infirmary_visits WHERE visit_id = ?", (item.visit_id,)
                ).fetchone()
                if corrected is None:
                    raise ValueError(f"Missing corrected visit {item.visit_id}")
                removed_details.append(
                    f"  {sorcerer_id}, {item.visit_id}: {item.recovery_hours:.2f}h "
                    f"before and {corrected[0]:.2f}h after the inferred correction."
                )
        candidate_ids = ", ".join(candidates) if candidates else "none"
        candidate_details = [
            f"  {sorcerer_id}: "
            + "; ".join(
                f"{item.visit_id} (severity {item.severity}, estimated interval "
                f"{item.recovery_hours:.2f}h, {item.positive_readings} positive readings, "
                f"longest hourly streak {item.longest_positive_streak}, "
                f"first {item.first_positive_utc} on {item.device_id}, {item.firmware})"
                for item in events
            )
            for sorcerer_id, events in candidates.items()
        ]

        lines = [
            f"DROP {drop} ANSWERS - PROVISIONAL",
            f"This report analyzes drops 0 through {drop}.",
            "",
            "A1 - Ingest",
            f"The source CSVs are in SQLite, not yet in a notebook. " +
            (f"healer_sessions.csv contains {scalar('SELECT COUNT(*) FROM healer_sessions'):,} healer-patient-time records (drop 1); " if has_healer_data else "") +
            ("infirmary_corrections.csv also requires CP932 decoding; " if has_corrections else "") +
            "infirmary_visits.csv requires CP932 decoding; the wearable file is streamed "
            "in batches because it has over five million rows. The PDF and dictionary "
            "are separate documents and have not been loaded into a notebook.",
            "",
            f"A2 - Unique missions: {final_missions:,} in final.db.",
            f"Evidence: {mission_rows:,} source rows and {deduplicated_rows:,} distinct full rows; "
            f"{distinct_missions:,} unique raw IDs; {conflicts:,} IDs have conflicting non-identical rows.",
            "",
            f"B1 - Wards: {ward_count:,} matched ward names after normalizing reversals.",
            f"Evidence: {reversed_wards:,} deduplicated mission rows had reversed ward names; "
            f"{unmatched_wards:,} remain unmatched. A nonzero unmatched count makes this a lower bound.",
            "",
            "B2 - Median residual cursed energy, raw sensor units:",
            f"  Tokyo: {tokyo:,.2f} ({len(residuals['Tokyo']):,} readings)",
            f"  Kyoto: {kyoto:,.2f} ({len(residuals['Kyoto']):,} readings)",
            "Evidence: sensor rows joined to wards by ward_code; no unit conversion or outlier removal. "
            "Kyoto's unit scale is unverified, so these are recorded-unit medians, not confirmed comparable values.",
            "",
            f"B3 - Reported killed in action: {len(casualties):,} distinct IDs.",
            "Evidence: split mission casualties on '|', deduplicate IDs, and filter mission start "
            "from 2025-05-01 inclusive to 2026-11-01 exclusive (UTC).",
            f"  IDs also marked active in the roster: {', '.join(active_casualties) or 'none'}.",
            f"  IDs absent from the roster: {', '.join(unknown_casualties) or 'none'}.",
            "Distinct IDs are not necessarily distinct people: some IDs appear to have been reused. "
            "This is a reported-casualty count, not a fully verified death count.",
            "",
            "B4 - Dictionary statements challenged by the data:",
            f"  The visit mission_id is described as the mission where the injury happened, "
            f"but {raw_missing:,} original visits have a blank mission_id "
            f"({missing_mission:,} remain after corrections).",
            f"  Mission ward is described as a romaji name, but {reversed_wards:,} deduplicated "
            "mission rows contain reversed names.",
            f"  The dictionary says sorcerer IDs are never reused, but {len(reused_id_evidence):,} "
            "current roster holders have a casualty record ending before their join date. "
            "This is strong evidence of reuse or an identity-record inconsistency:",
            *[
                f"    {sid}: previous casualty mission ended {end_ts}; current join date {join_date}."
                for sid, join_date, end_ts in reused_id_evidence
            ],
            "  The dictionary says positive readings mean positive energy. That interpretation "
            "needs investigation: the positive rate changes sharply with firmware, "
            "so a positive value alone is not reliable proof of RCT.",
            *firmware_lines,
            "  Severity descriptions and the statement that all infirmary times are JST require "
            "further verification; negative intervals alone do not prove the correct interpretation.",
            *audit_lines,
            "",
            "B5 - Curse log (issues observed so far):",
            f"  Reversed sorcerer names: {reversed_names:,} rows normalized after validating "
            "the reversed given and family names against other roster entries.",
            f"  Mission duplicates: {mission_rows - deduplicated_rows:,} exact duplicate rows; "
            "clean_missions removes exact duplicates while retaining and flagging conflicts.",
            f"  Reversed ward spellings: {reversed_wards:,} deduplicated rows; "
            f"map unique reversals to reference wards and flag {unmatched_wards:,} unmatched rows.",
            f"  Injury-code variants: {original_code_variants:,} in original visits; "
            f"{normalized_codes:,} effective visits normalized by the review view after applying corrections.",
            *correction_lines,
            f"  Visit timing: {negative:,} negative and {invalid:,} unparseable intervals "
            "in effective visits before timezone interpretation. "
            f"For {inferred_times:,} visits, discharge is provisionally interpreted as UTC after "
            "a mission-start cutoff of 2026-02-28 00:00 UTC; admissions remain JST. "
            f"{remaining_negative:,} negative intervals remain under this assumption.",
            f"  Original missing visit missions: {raw_missing:,}; original TST-00 visits: {raw_test_codes:,}. "
            f"After corrections: {missing_mission:,} and {test_code_count:,}, respectively. "
            "Raw rows are preserved; ineligible visits are excluded from final.db.",
            f"  Casualties versus status: {len(active_casualties):,} reported casualty IDs are marked active; "
            "retain both sources; check historical identity against the current join date.",
            f"  Identity ambiguity: {pre_join_visits:,} visits predate the current holder's join date. "
            "The review views flag these records and wearable assignments without reassigning them.",
            "  Firmware v2.3 has an anomalous positive rate; flag readings for review, not sign reversal.",
            "  Kyoto residual values have a much larger raw scale than Tokyo; retain raw units pending evidence.",
            "  Source tables remain unchanged. final.db excludes test/missing-mission visits and "
            "uncertain wearable attribution"
            + (", as well as visits flagged for healer overlap" if has_healer_data else "")
            + "; target/chlogs.txt records row-level changes and flags.",
            "",
            "C1 - Recovery time: normalized UTC discharge minus normalized UTC admission, in hours.",
            f"Medians use {recovery_visits:,} mission-linked non-test visits with usable intervals, "
            "including healer-assisted visits. "
            "The inferred timezone cutoff is unconfirmed, so these are provisional.",
            *medians,
            "",
            "C2 - Provisional screen: an active current ID has at least two mission-linked "
            "recorded severity 4/5 visits under 24 hours, each with at least two consecutive "
            "positive hourly readings from an assigned v2.2/v2.4 device during the recorded visit"
            + (" and no recorded overlapping healer session." if has_healer_data else "."),
            "This is a screening rule, not proof of self-healing: the thresholds, severity "
            "interpretation, and discharge-time cutoff are assumptions; "
            + ("healer records may be incomplete." if has_healer_data
               else "healer assistance cannot be checked without drop 1.")
            + " Firmware v2.3 is excluded.",
            "",
            f"D1 - Provisional candidates based on drops 0 through {drop}: {candidate_ids}.",
            *candidate_details,
            "These are candidates, not confirmed RCT users or a recommendation to submit: "
            "positive readings may have other causes, the timestamps may be inconsistent, "
            + ("and healer records may be incomplete."
               if has_corrections else "healer records may be incomplete, and later corrections have not been checked."
               if has_healer_data else "and external healing and later corrections have not been checked."),
            "D2 - The following previous screen candidates no longer satisfy the 24-hour "
            f"rule after the inferred timezone correction: {', '.join(removed_candidates) or 'none'}.",
            *removed_details,
            *(
                ["  Previously qualifying visits with recorded healer overlap:", *healer_removed_details]
                if healer_removed_details else []
            ),
            "This does not prove they cannot use RCT. Other false positives remain possible, "
            "including healer assistance. Firmware v2.3 has a near-universal positive sign "
            "and must not be classified as RCT from that sign alone.",
            "",
            *bonus_lines,
        ]

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate_answers()
    print(f"Answers written to {OUTPUT}")