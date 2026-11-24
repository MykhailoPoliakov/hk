import json
import sqlite3
from datetime import datetime


VISIT_COLUMNS = (
    "visit_id", "sorcerer_id", "mission_id", "admitted_at", "discharged_at",
    "injury_code", "severity", "admitted_from",
)


def apply_corrections(connection: sqlite3.Connection) -> None:
    """Replay the ordered change feed while preserving source tables and history."""
    connection.execute("CREATE TABLE effective_infirmary_visits AS SELECT * FROM infirmary_visits")
    connection.execute("CREATE UNIQUE INDEX effective_visit_id ON effective_infirmary_visits(visit_id)")
    connection.execute(
        "CREATE TABLE correction_history (source_rowid INTEGER, seq INTEGER PRIMARY KEY, "
        "op TEXT, op_ts TEXT, visit_id TEXT, before_json TEXT, after_json TEXT)"
    )
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='infirmary_corrections'"
    ).fetchone():
        return
    columns = ", ".join(VISIT_COLUMNS)
    feed = connection.execute(
        f"SELECT rowid, seq, op, op_ts, {columns} FROM infirmary_corrections"
    ).fetchall()
    parsed = []
    seen = set()
    for row in feed:
        rowid, seq, op, op_ts, *values = row
        if not seq.isascii() or not seq.isdigit() or int(seq) in seen:
            raise ValueError(f"Invalid or duplicate correction sequence: {seq!r}")
        seen.add(int(seq))
        try:
            if not op_ts.endswith("Z"):
                raise ValueError("UTC Z suffix required")
            datetime.fromisoformat(op_ts[:-1] + "+00:00")
        except ValueError as error:
            raise ValueError(f"Invalid correction timestamp at sequence {seq}: {op_ts!r}") from error
        if op not in ("I", "U", "D") or not values[0]:
            raise ValueError(f"Invalid correction at sequence {seq}: {op!r}, {values[0]!r}")
        parsed.append((int(seq), rowid, op, op_ts, values))
    for seq, rowid, op, op_ts, values in sorted(parsed):
        visit_id = values[0]
        previous = connection.execute(
            f"SELECT {columns} FROM effective_infirmary_visits WHERE visit_id=?", (visit_id,)
        ).fetchone()
        if (op == "I") == (previous is not None):
            raise ValueError(f"Correction {seq}: {op} has unexpected existing state for {visit_id}")
        if op != "D" and any(not values[i] for i in (0, 1, 3, 4, 5, 6)):
            raise ValueError(f"Correction {seq}: incomplete visit {visit_id}")
        if op == "D":
            connection.execute("DELETE FROM effective_infirmary_visits WHERE visit_id=?", (visit_id,))
            after = None
        else:
            if op == "U":
                connection.execute("DELETE FROM effective_infirmary_visits WHERE visit_id=?", (visit_id,))
            connection.execute(
                "INSERT INTO effective_infirmary_visits VALUES (?,?,?,?,?,?,?,?)", values
            )
            after = dict(zip(VISIT_COLUMNS, values))
        before = dict(zip(VISIT_COLUMNS, previous)) if previous is not None else None
        connection.execute(
            "INSERT INTO correction_history VALUES (?,?,?,?,?,?,?)",
            (rowid, seq, op, op_ts, visit_id,
             json.dumps(before, ensure_ascii=False) if before else None,
             json.dumps(after, ensure_ascii=False) if after else None),
        )
