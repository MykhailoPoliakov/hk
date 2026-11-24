import csv
import io
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dashboard import export
from dashboard.export import CSV_FILES, export_dashboard
from src import __main__ as pipeline


class DashboardExportTest(unittest.TestCase):
    def test_cli_writes_default_exports_to_dashboard_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def fake_export(_database: Path, _final_database: Path, output: Path) -> dict[str, int]:
                for name in CSV_FILES:
                    (output / name).write_text("header\n", encoding="utf-8")
                return dict.fromkeys(CSV_FILES, 0)

            with patch.object(export, "ROOT", root), \
                    patch.object(export, "export_dashboard", side_effect=fake_export), \
                    patch("sys.argv", ["export.py"]):
                export.main()

            output = root / "dashboard" / "dashboard_data"
            self.assertEqual({path.name for path in output.iterdir()}, set(CSV_FILES))
            self.assertFalse((root / "dashboard" / "candidates.csv").exists())

    def test_pipeline_publishes_exports_to_dashboard_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "initial_data"
            source.mkdir()
            for name in pipeline.REQUIRED_CSVS:
                (source / name).touch()

            def create_database(_folder: Path, database: Path, _selected: set[str]) -> dict[str, int]:
                with closing(sqlite3.connect(database)):
                    pass
                return {}

            def create_final(_raw: Path, final: Path) -> None:
                final.touch()

            def write_log(_connection: sqlite3.Connection, output: Path) -> dict[str, int]:
                output.write_text("", encoding="utf-8")
                return {}

            def write_answers(_raw: Path, output: Path, _final: Path) -> None:
                output.write_text("", encoding="utf-8")

            def write_dashboard(_raw: Path, _final: Path, output: Path) -> dict[str, int]:
                output.mkdir()
                for name in CSV_FILES:
                    (output / name).write_text("header\n", encoding="utf-8")
                return dict.fromkeys(CSV_FILES, 0)

            replacements = {
                "create_database": create_database,
                "apply_corrections": lambda _connection: None,
                "fill_db": lambda _database: [],
                "create_final_database": create_final,
                "write_changelog": write_log,
                "generate_answers": write_answers,
                "export_dashboard": write_dashboard,
            }
            with ExitStack() as stack:
                for name, replacement in replacements.items():
                    stack.enter_context(patch.object(pipeline, name, side_effect=replacement))
                stack.enter_context(redirect_stdout(io.StringIO()))
                pipeline.run_pipeline(root=root, drop=0)

            output = root / "dashboard" / "dashboard_data"
            self.assertEqual({path.name for path in output.iterdir()}, set(CSV_FILES))
            self.assertFalse((root / "dashboard" / "candidates.csv").exists())

    def test_exports_only_qualifying_stays_and_all_readings_within_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.db"
            final_path = root / "final.db"
            with closing(sqlite3.connect(raw_path)) as raw:
                raw.executescript("""
                    CREATE TABLE ce_wearable (device_id TEXT, ts TEXT, ce_level TEXT, firmware TEXT);
                    INSERT INTO ce_wearable VALUES ('D','2025-01-03T01:00:00Z','1','v2.2');
                    INSERT INTO ce_wearable VALUES ('D','2025-01-03T02:00:00Z','-1','v2.2');
                    CREATE TABLE estimated_infirmary_visits (
                        visit_id TEXT, sorcerer_id TEXT, mission_id TEXT, admitted_at_utc TEXT,
                        discharged_at_utc TEXT, severity TEXT, identity_review TEXT,
                        estimated_recovery_hours REAL, timestamp_assumption TEXT,
                        estimated_timing_status TEXT, timing_status TEXT, missing_mission INTEGER,
                        test_code_review INTEGER
                    );
                    INSERT INTO estimated_infirmary_visits VALUES
                        ('V1','S','M','2025-01-03T00:00:00Z','2025-01-03T05:00:00Z','5',
                         'not_before_current_join_date',5,'dictionary_jst','usable_under_assumption','valid',0,0),
                        ('V2','S','M','2025-01-04T00:00:00Z','2025-01-04T05:00:00Z','5',
                         'not_before_current_join_date',5,'dictionary_jst','usable_under_assumption','valid',0,0);
                """)
                raw.commit()
            with closing(sqlite3.connect(final_path)) as final:
                final.executescript("""
                    CREATE TABLE sorcerers (sorcerer_id TEXT, name TEXT, grade TEXT,
                        school TEXT, status TEXT, join_date TEXT);
                    INSERT INTO sorcerers VALUES ('S','Test Name','1','Tokyo','active','2024-01-01');
                    CREATE TABLE missions (mission_id TEXT);
                    INSERT INTO missions VALUES ('M');
                    CREATE TABLE infirmary_visits (
                        visit_id TEXT, sorcerer_id TEXT, mission_id TEXT, admitted_at TEXT,
                        discharged_at TEXT, severity INTEGER, identity_review TEXT, recovery_hours REAL,
                        injury_code TEXT, timestamp_assumption TEXT
                    );
                    INSERT INTO infirmary_visits VALUES
                        ('V1','S','M','2025-01-03T00:00:00Z','2025-01-03T05:00:00Z',5,
                         'not_before_current_join_date',5,'X','dictionary_jst'),
                        ('V2','S','M','2025-01-04T00:00:00Z','2025-01-04T05:00:00Z',5,
                         'not_before_current_join_date',5,'X','dictionary_jst');
                    CREATE TABLE ce_wearable (
                        sorcerer_id TEXT, device_id TEXT, ts TEXT, ce_level REAL, firmware TEXT
                    );
                    INSERT INTO ce_wearable VALUES
                        ('S','D','2025-01-03T01:00:00Z',1,'v2.2'),
                        ('S','D','2025-01-03T02:00:00Z',1,'v2.2'),
                        ('S','D','2025-01-03T02:30:00Z',-1,'v2.2'),
                        ('S','D','2025-01-03T05:00:00Z',99,'v2.2'),
                        ('S','D','2025-01-04T01:00:00Z',1,'v2.2'),
                        ('S','D','2025-01-04T02:00:00Z',1,'v2.2'),
                        ('S','D','2025-01-04T02:30:00Z',0,'v2.2');
                """)
                final.commit()

            output = root / "output"
            counts = export_dashboard(raw_path, final_path, output)
            self.assertEqual(set(counts), set(CSV_FILES))
            self.assertEqual((counts["candidates.csv"], counts["visits.csv"], counts["readings.csv"]), (1, 2, 6))
            with (output / "readings.csv").open(encoding="utf-8", newline="") as file:
                readings = list(csv.DictReader(file))
            self.assertEqual({row["ce_level"] for row in readings}, {"-1.0", "0.0", "1.0"})
            self.assertNotIn("2025-01-03T05:00:00Z", [row["timestamp_utc"] for row in readings])
            with (output / "visits.csv").open(encoding="utf-8", newline="") as file:
                visits = list(csv.DictReader(file))
            self.assertTrue(all(row["healer_status"] == "unknown_no_healer_data" for row in visits))


if __name__ == "__main__":
    unittest.main()
