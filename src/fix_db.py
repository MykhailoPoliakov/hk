import sqlite3
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data.db"
SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"


def fill_db(database: Path = DATABASE, sql_directory: Path = SQL_DIRECTORY) -> list[str]:
    """Execute SQL files in filename order, committing them together."""
    sql_directory = Path(sql_directory)
    if not sql_directory.is_dir():
        raise NotADirectoryError(f"SQL folder does not exist: {sql_directory}")
    sql_files = sorted(sql_directory.glob("*.sql"))
    if not sql_files:
        raise ValueError(f"No SQL files found in {sql_directory}")

    scripts = [path.read_text(encoding="utf-8-sig") for path in sql_files]
    database_uri = Path(database).resolve().as_uri() + "?mode=rw"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection, connection:
        connection.executescript("BEGIN;\n" + "\n;\n".join(scripts) + "\n;\nCOMMIT;")
    return [path.name for path in sql_files]


if __name__ == "__main__":
    for filename in fill_db():
        print(f"Executed {filename}")