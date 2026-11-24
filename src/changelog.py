import json
import sqlite3
from collections import Counter
from pathlib import Path


def write_changelog(connection: sqlite3.Connection, output: Path) -> Counter[str]:
    """Write one JSON line per corrected, removed, or review-flagged source row."""
    counts: Counter[str] = Counter()
    mission_columns = (
        "mission_id", "start_ts", "end_ts", "ward", "curse_grade",
        "sorcerer_ids", "outcome", "casualties", "report_text",
    )
    visit_columns = (
        "visit_id", "sorcerer_id", "mission_id", "admitted_at", "discharged_at",
        "injury_code", "severity", "admitted_from",
    )
    missions = {}
    for row in connection.execute(
        "SELECT mission_id, start_ts, end_ts, original_ward, curse_grade, sorcerer_ids, "
        "outcome, casualties, report_text, ward, ward_status, conflicting_mission_id "
        "FROM clean_missions"
    ):
        missions[tuple(row[:9])] = row[9:]
    visits = {}
    for row in connection.execute(
        "SELECT visit_id, sorcerer_id, mission_id, admitted_at, discharged_at, "
        "original_injury_code, severity, admitted_from, injury_code, timing_status, "
        "identity_review, missing_mission, test_code_review, admitted_at_utc, "
        "discharged_at_utc, timestamp_assumption, estimated_timing_status "
        "FROM estimated_infirmary_visits"
    ):
        visits[tuple(row[:8])] = row[8:]

    with Path(output).open("w", encoding="utf-8", newline="\n") as log:
        def emit(table: str, rowid: int, source: dict, changes: dict, flags: list[str]) -> None:
            if not changes and not flags:
                return
            counts[table] += 1
            log.write(json.dumps(
                {"table": table, "source_rowid": rowid, "source": source, "changes": changes, "flags": flags},
                ensure_ascii=False,
            ) + "\n")

        seen: set[tuple] = set()
        for row in connection.execute("SELECT rowid, * FROM missions ORDER BY rowid"):
            rowid, *values = row
            key = tuple(values)
            ward, ward_status, conflict = missions[key]
            changes = {}
            flags = []
            if key in seen:
                changes["duplicate"] = {"before": dict(zip(mission_columns, values)), "after": None}
            else:
                seen.add(key)
                if ward != values[3]:
                    changes["ward"] = {"before": values[3], "after": ward}
                if ward_status == "unmatched":
                    flags.extend(["unmatched_ward", "excluded_from_final"])
                if conflict:
                    flags.extend(["conflicting_mission_id", "excluded_from_final"])
            emit("missions", rowid, dict(zip(mission_columns, values)), changes, flags)

        for row in connection.execute("SELECT rowid, * FROM infirmary_visits ORDER BY rowid"):
            rowid, *values = row
            (
                injury, timing, identity, missing_mission, test_code,
                admitted_utc, discharged_utc, assumption, estimated_status,
            ) = visits[tuple(values)]
            changes = {}
            flags = []
            if injury != values[5]:
                changes["injury_code"] = {"before": values[5], "after": injury}
            if admitted_utc is not None:
                changes["admitted_at_utc"] = {"before": values[3], "after": admitted_utc}
            if discharged_utc is not None:
                changes["discharged_at_utc"] = {
                    "before": values[4], "after": discharged_utc, "assumption": assumption,
                }
            if timing != "valid":
                flags.append("raw_" + timing)
            if identity != "not_before_current_join_date":
                flags.append(identity)
            if missing_mission:
                flags.append("missing_mission")
            if test_code:
                flags.append("test_code_review")
            if missing_mission or test_code or estimated_status != "usable_under_assumption":
                flags.append("excluded_from_final")
            else:
                changes["severity"] = {"before": values[6], "after": int(values[6])}
            if assumption == "inferred_discharge_utc":
                flags.append("inferred_timestamp_rule")
            emit("infirmary_visits", rowid, dict(zip(visit_columns, values)), changes, flags)

        for row in connection.execute(
            "SELECT s.rowid, s.sorcerer_id, s.name, s.join_date, s.status, "
            "r.earlier_casualty_records, r.name, r.name_status "
            "FROM sorcerers s JOIN reviewed_sorcerers r ON r.sorcerer_id = s.sorcerer_id "
            "WHERE r.earlier_casualty_records > 0 OR r.name_status != 'original'"
        ):
            rowid, sorcerer, name, join_date, status, earlier_casualties, clean_name, name_status = row
            changes = {}
            flags = []
            if name_status == "reversed":
                changes["name"] = {"before": name, "after": clean_name}
            elif name_status == "unresolved":
                flags.append("unresolved_name")
            if earlier_casualties:
                flags.append("earlier_casualty_records")
            emit("sorcerers", rowid, {
                "sorcerer_id": sorcerer, "name": name, "join_date": join_date,
                "status": status, "earlier_casualty_records": earlier_casualties,
            }, changes, flags)

        for row in connection.execute(
            "SELECT assignment_rowid, device_id, sorcerer_id, valid_from, valid_to, assignment_review "
            "FROM reviewed_device_assignments WHERE assignment_review != 'valid'"
        ):
            rowid, device, sorcerer, valid_from, valid_to, review = row
            emit("device_assignments", rowid, {
                "device_id": device, "sorcerer_id": sorcerer,
                "valid_from": valid_from, "valid_to": valid_to,
            }, {}, [review, "excluded_from_final"])

        for row in connection.execute(
            "SELECT reading_rowid, device_id, ts, ce_level, firmware, sorcerer_id, "
            "firmware_review_required, attribution_review FROM attributed_ce_wearable"
        ):
            rowid, device, timestamp, level, firmware, sorcerer, firmware_review, attribution = row
            flags = []
            if firmware_review:
                flags.append("firmware_review_required")
            elif firmware not in ("v2.2", "v2.4"):
                flags.append("unknown_firmware")
            if attribution != "not_before_current_join_date":
                flags.append(attribution)
            changes = {}
            if flags:
                flags.append("excluded_from_final")
            else:
                changes["ce_level"] = {"before": level, "after": float(level)}
            emit("ce_wearable", rowid, {
                "device_id": device, "ts": timestamp, "ce_level": level,
                "firmware": firmware, "matched_sorcerer_id": sorcerer,
            }, changes, flags)
        for row in connection.execute(
            "SELECT b.rowid, b.ward_code, b.ts, b.residual_ce, w.city FROM barrier_sensors b "
            "JOIN wards w ON w.ward_code = b.ward_code"
        ):
            rowid, ward_code, timestamp, residual_ce, city = row
            emit("barrier_sensors", rowid, {
                "ward_code": ward_code, "ts": timestamp, "residual_ce": residual_ce,
            }, {"residual_ce": {"before": residual_ce, "after": float(residual_ce)}},
                ["unit_review_required"] if city == "Kyoto" else [])
        
        # Drop 1: Log healer sessions and their overlap with visits
        try:
            for row in connection.execute(
                "SELECT h.session_id, h.healer_id, h.patient_id, h.start_ts, "
                "GROUP_CONCAT(DISTINCT CASE WHEN v.visit_id IS NOT NULL THEN v.visit_id END, '|') "
                "FROM (SELECT rowid, session_id, healer_id, patient_id, start_ts FROM healer_sessions) h "
                "LEFT JOIN visits_with_external_healing v ON v.healer_ids LIKE '%' || h.healer_id || '%' "
                "AND v.sorcerer_id = h.patient_id GROUP BY h.session_id"
            ):
                session_id, healer_id, patient_id, start_ts, visit_ids = row
                if visit_ids:
                    flags = ["healer_session", "affected_visits"]
                    emit("healer_sessions", 0, {
                        "session_id": session_id, "healer_id": healer_id,
                        "patient_id": patient_id, "start_ts": start_ts,
                        "overlapping_visits": visit_ids,
                    }, {}, flags)
        except sqlite3.OperationalError:
            pass
    return counts
