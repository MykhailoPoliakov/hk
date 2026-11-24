import csv
import sqlite3
from contextlib import closing
from itertools import islice
from pathlib import Path




def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def create_database(
    data_folder: Path = Path(__file__).resolve().parent.parent / "initial_data",
    database_path: Path = Path(__file__).resolve().parent.parent / "data.db",
) -> dict[str, int]:
    """Create a SQLite database with one raw text table per CSV file."""
    data_folder = Path(data_folder)
    database_path = Path(database_path)
    if not data_folder.is_dir():
        raise NotADirectoryError(f"Data folder does not exist: {data_folder}")

    csv_files = sorted(data_folder.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in {data_folder}")

    # Sort to ensure consistent order: required first, then optional
    csv_files = sorted(csv_files, key=lambda f: (f.name not in ("barrier_sensors.csv", "ce_wearable.csv", "device_assignments.csv", "infirmary_visits.csv", "missions.csv", "sorcerers.csv", "wards.csv"), f.name))

    # Exclusive creation prevents accidentally overwriting an existing database.
    with database_path.open("xb"):
        pass

    counts: dict[str, int] = {}
    completed = False
    try:
        with closing(sqlite3.connect(database_path)) as connection, connection:
            connection.execute("BEGIN")
            for csv_file in csv_files:
                encoding = "cp932" if csv_file.name == "infirmary_visits.csv" else "utf-8-sig"
                with csv_file.open(encoding=encoding, newline="") as source:
                    reader = csv.reader(source, strict=True)
                    headers = next(reader, None)
                    if not headers or any(not header for header in headers):
                        raise ValueError(f"Missing or empty CSV header in {csv_file}")

                    table = quote_identifier(csv_file.stem)
                    columns = ", ".join(f"{quote_identifier(header)} TEXT" for header in headers)
                    placeholders = ", ".join("?" for _ in headers)
                    connection.execute(f"CREATE TABLE {table} ({columns})")
                    insert = f"INSERT INTO {table} VALUES ({placeholders})"
                    count = 0
                    while batch := list(islice(reader, 10_000)):
                        connection.executemany(insert, batch)
                        count += len(batch)
                    counts[csv_file.stem] = count
        completed = True
    finally:
        if not completed:
            database_path.unlink()
    return counts