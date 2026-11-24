import sqlite3
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RctEvidence:
    sorcerer_id: str
    visit_id: str
    severity: int
    recovery_hours: float
    positive_readings: int
    longest_positive_streak: int
    first_positive_utc: str
    device_id: str
    firmware: str


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Expected a timezone-aware UTC timestamp: {value}")
    return parsed.astimezone(timezone.utc)


def find_rct_candidates(connection: sqlite3.Connection) -> dict[str, list[RctEvidence]]:
    """Screen curated data for repeated fast visits with sustained positive readings."""
    readings: dict[str, list[tuple[datetime, str, float, str]]] = defaultdict(list)
    for sorcerer, device, timestamp, level, firmware in connection.execute(
        "SELECT sorcerer_id, device_id, ts, ce_level, firmware FROM ce_wearable "
        "WHERE CAST(ce_level AS REAL) > 0"
    ):
        readings[sorcerer].append((_utc(timestamp), device, float(level), firmware))
    for values in readings.values():
        values.sort()

    evidence: dict[str, list[RctEvidence]] = defaultdict(list)
    
    # Load healer sessions to exclude visits with external healing
    healed_visits: set[str] = set()
    try:
        for (visit_id,) in connection.execute(
            "SELECT DISTINCT visit_id FROM visits_with_external_healing WHERE has_healer_overlap > 0"
        ):
            healed_visits.add(visit_id)
    except sqlite3.OperationalError:
        # Drop 0: healer_sessions table doesn't exist yet
        pass
    
    visits = connection.execute(
        "SELECT v.sorcerer_id, v.visit_id, v.severity, v.admitted_at, v.discharged_at, "
        "v.recovery_hours FROM infirmary_visits v "
        "JOIN sorcerers s ON s.sorcerer_id = v.sorcerer_id "
        "WHERE s.status = 'active' AND v.identity_review = 'not_before_current_join_date' "
        "AND date(v.admitted_at) > date(s.join_date) AND v.severity IN (4, 5) "
        "AND v.recovery_hours >= 0 AND v.recovery_hours < 24"
    )
    for sorcerer, visit, severity, admitted, discharged, hours in visits:
        if visit in healed_visits:
            continue
        start = _utc(admitted)
        end = _utc(discharged)
        patient_readings = readings[sorcerer]
        first = bisect_left(patient_readings, (start,))
        last = bisect_left(patient_readings, (end,))
        matches = patient_readings[first:last]
        longest = streak = 0
        previous: tuple[datetime, str] | None = None
        for timestamp, device, _, _ in matches:
            if previous and device == previous[1] and timestamp - previous[0] == timedelta(hours=1):
                streak += 1
            else:
                streak = 1
            longest = max(longest, streak)
            previous = (timestamp, device)
        if longest >= 2:
            first_timestamp, first_device, _, first_firmware = matches[0]
            evidence[sorcerer].append(
                RctEvidence(
                    sorcerer, visit, severity, hours, len(matches), longest,
                    first_timestamp.isoformat().replace("+00:00", "Z"), first_device, first_firmware,
                )
            )
    return {
        sorcerer: visits for sorcerer, visits in sorted(evidence.items())
        if len({visit.visit_id for visit in visits}) >= 2
    }
