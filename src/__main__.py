import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from answers import generate_answers
from changelog import write_changelog
from create_db import create_database
from corrections import apply_corrections
from curate_db import create_final_database
from fix_db import fill_db


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dashboard.export import CSV_FILES, DASHBOARD_DATA_DIRECTORY, export_dashboard

DROP = 2
REQUIRED_CSVS = {
    "barrier_sensors.csv", "ce_wearable.csv", "device_assignments.csv",
    "infirmary_visits.csv", "missions.csv", "sorcerers.csv", "wards.csv",
}
DROP_CSVS = {1: {"healer_sessions.csv"}, 2: {"infirmary_corrections.csv", "audit_log.csv"}}


def run_pipeline(root: Path = ROOT, drop: int = DROP) -> None:
    """Rebuild drop N outputs from CSVs, replacing them only after a successful run."""
    root = Path(root)
    if drop not in (0, 1, 2):
        raise ValueError(f"Unsupported drop: {drop}")
    source = root / "initial_data"
    selected = REQUIRED_CSVS | {name for level, names in DROP_CSVS.items() if level <= drop for name in names}
    missing = sorted(name for name in selected if not (source / name).is_file())
    if missing:
        raise FileNotFoundError(f"Missing source CSVs: {', '.join(missing)}")

    target = root / "target"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pipeline-", dir=target) as staging:
        staging_path = Path(staging)
        database = staging_path / "data.db"
        final_database = staging_path / "final.db"
        counts = create_database(source, database, selected)
        with closing(sqlite3.connect(database)) as connection, connection:
            apply_corrections(connection)
            if drop >= 1:
                connection.execute("CREATE INDEX healer_patient_time ON healer_sessions(patient_id, start_ts)")
        scripts = fill_db(database)
        create_final_database(database, final_database)
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            log_counts = write_changelog(connection, staging_path / "chlogs.txt")
        generate_answers(database, staging_path / "answers.txt", final_database)
        dashboard_path = staging_path / "dashboard"
        dashboard_counts = export_dashboard(database, final_database, dashboard_path)

        dashboard_output = root / DASHBOARD_DATA_DIRECTORY
        dashboard_output.mkdir(parents=True, exist_ok=True)
        os.replace(database, root / "data.db")
        os.replace(final_database, root / "final.db")
        os.replace(staging_path / "chlogs.txt", target / "chlogs.txt")
        os.replace(staging_path / "answers.txt", target / "answers.txt")
        for name in CSV_FILES:
            os.replace(dashboard_path / name, dashboard_output / name)

    for name, count in counts.items():
        print(f"Imported {name}: {count:,} rows")
    print(f"Executed {len(scripts)} SQL scripts")
    print("Logged row events: " + ", ".join(f"{name}={count:,}" for name, count in sorted(log_counts.items())))
    print("Dashboard CSV rows: " + ", ".join(f"{name}={count:,}" for name, count in dashboard_counts.items()))
    print(f"Generated {root / 'data.db'}, {root / 'final.db'}, {target / 'chlogs.txt'}, and {target / 'answers.txt'}")


if __name__ == "__main__":
    run_pipeline()