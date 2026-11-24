import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


SOURCE = Path(__file__).resolve().parent.parent / "src"
SQL_DIRECTORY = SOURCE / "sql"
sys.path.insert(0, str(SOURCE))
from changelog import write_changelog
from curate_db import create_final_database
from rct import find_rct_candidates


class ReviewViewsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript(
            """
            CREATE TABLE wards (ward_code TEXT, ward_name TEXT, city TEXT);
            CREATE TABLE missions (mission_id TEXT, start_ts TEXT, end_ts TEXT, ward TEXT,
                curse_grade TEXT, sorcerer_ids TEXT, outcome TEXT, casualties TEXT, report_text TEXT);
            CREATE TABLE infirmary_visits (visit_id TEXT, sorcerer_id TEXT, mission_id TEXT,
                admitted_at TEXT, discharged_at TEXT, injury_code TEXT, severity TEXT, admitted_from TEXT);
            CREATE TABLE sorcerers (sorcerer_id TEXT, name TEXT, grade TEXT, school TEXT,
                technique TEXT, join_date TEXT, status TEXT);
            CREATE TABLE device_assignments (device_id TEXT, sorcerer_id TEXT, valid_from TEXT, valid_to TEXT);
            CREATE TABLE ce_wearable (device_id TEXT, ts TEXT, ce_level TEXT, firmware TEXT);
            CREATE TABLE barrier_sensors (ward_code TEXT, ts TEXT, residual_ce TEXT);
            INSERT INTO wards VALUES ('W', 'Kita', 'Kyoto');
            INSERT INTO missions VALUES ('M1', '2025-01-01T10:00:00Z', '2025-01-01T11:00:00Z',
                'atiK', '1', 'S1|S2', 'failed', 'S1|S2', '');
            INSERT INTO sorcerers VALUES ('S1', 'Current', '1', 'Tokyo', '', '2025-02-01', 'active');
            INSERT INTO sorcerers VALUES ('S2', 'Other', '1', 'Tokyo', '', '2024-01-01', 'deceased');
            INSERT INTO sorcerers VALUES ('S3', 'Third', '1', 'Tokyo', '', '2024-01-01', 'active');
            INSERT INTO sorcerers VALUES ('S4', 'Fourth', '1', 'Tokyo', '', '2024-01-01', 'active');
            INSERT INTO infirmary_visits VALUES ('V1', 'S1', 'M1', '2025-01-02 09:00',
                '2025-01-02 08:00', 'TST-00', '1', 'ward');
            INSERT INTO device_assignments VALUES ('D1', 'S1', '2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z');
            INSERT INTO device_assignments VALUES ('D1', 'S1', '2025-02-01T00:00:00Z', '');
            INSERT INTO device_assignments VALUES ('D2', 'S2', '2025-01-01T00:00:00Z', '');
            INSERT INTO device_assignments VALUES ('D2', 'S3', '2025-02-01T00:00:00Z', '');
            INSERT INTO device_assignments VALUES ('D3', 'S4', '2025-01-01T00:00:00Z', '');
            INSERT INTO device_assignments VALUES ('D4', 'S4', '2025-02-01T00:00:00Z', '');
            INSERT INTO ce_wearable VALUES ('D1', '2025-01-31T23:00:00Z', '10', 'v2.3');
            INSERT INTO ce_wearable VALUES ('D1', '2025-02-01T00:00:00Z', '-10', 'v2.2');
            INSERT INTO ce_wearable VALUES ('D1', '2025-02-02T00:00:00Z', '-10', 'v2.2');
            INSERT INTO ce_wearable VALUES ('D2', '2025-02-02T00:00:00Z', '-10', 'v2.2');
            INSERT INTO ce_wearable VALUES ('D3', '2025-02-02T00:00:00Z', '-10', 'v2.2');
            INSERT INTO ce_wearable VALUES ('unknown', '2025-02-02T00:00:00Z', '-10', 'v2.2');
            """
        )
        for path in sorted(SQL_DIRECTORY.glob("*.sql")):
            self.db.executescript(path.read_text(encoding="utf-8"))

    def test_historical_casualties_and_visits_are_flagged(self) -> None:
        casualties = self.db.execute(
            "SELECT sorcerer_id FROM mission_casualties ORDER BY sorcerer_id"
        ).fetchall()
        self.assertEqual(casualties, [("S1",), ("S2",)])
        self.assertEqual(
            self.db.execute(
                "SELECT earlier_casualty_records FROM reviewed_sorcerers WHERE sorcerer_id='S1'"
            ).fetchone(),
            (1,),
        )
        self.assertEqual(
            self.db.execute(
                "SELECT identity_review, test_code_review, recovery_review FROM reviewed_infirmary_visits"
            ).fetchone(),
            ("before_current_join_date", 1, "negative_duration"),
        )

    def test_wearable_attribution_boundaries_and_conflicts(self) -> None:
        readings = self.db.execute(
            "SELECT attribution_review, firmware_review_required FROM attributed_ce_wearable "
            "WHERE device_id='D1' ORDER BY ts"
        ).fetchall()
        self.assertEqual(
            readings,
            [
                ("before_current_join_date_utc", 1),
                ("join_date_boundary", 0),
                ("not_before_current_join_date", 0),
            ],
        )
        self.assertEqual(
            self.db.execute(
                "SELECT attribution_review FROM attributed_ce_wearable WHERE device_id='D2'"
            ).fetchall(),
            [("overlapping_device_assignment",), ("overlapping_device_assignment",)],
        )
        self.assertEqual(
            self.db.execute(
                "SELECT attribution_review FROM attributed_ce_wearable WHERE device_id='D3'"
            ).fetchone(),
            ("overlapping_sorcerer_assignment",),
        )
        self.assertEqual(
            self.db.execute(
                "SELECT attribution_review FROM attributed_ce_wearable WHERE device_id='unknown'"
            ).fetchone(),
            ("unmatched_assignment",),
        )

    def test_changelog_records_changes_and_review_flags(self) -> None:
        self.db.execute("INSERT INTO missions SELECT * FROM missions WHERE mission_id='M1'")
        self.db.execute(
            "INSERT INTO sorcerers VALUES ('S7', 'Hina Takeda', '1', 'Tokyo', '', '2024-01-01', 'active')"
        )
        self.db.execute(
            "INSERT INTO sorcerers VALUES ('S8', 'adekaT aniH', '1', 'Tokyo', '', '2024-01-01', 'active')"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chlogs.txt"
            write_changelog(self.db, path)
            entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            mission_entries = [entry for entry in entries if entry["table"] == "missions"]
            self.assertEqual(len(mission_entries), 2)
            self.assertEqual(mission_entries[0]["changes"]["ward"], {"before": "atiK", "after": "Kita"})
            self.assertIsNone(mission_entries[1]["changes"]["duplicate"]["after"])
            visit = next(entry for entry in entries if entry["table"] == "infirmary_visits")
            self.assertIn("raw_negative_duration", visit["flags"])
            self.assertIn("before_current_join_date", visit["flags"])
            self.assertTrue(any("firmware_review_required" in entry["flags"] for entry in entries))
            self.assertTrue(any("earlier_casualty_records" in entry["flags"] for entry in entries))
            corrected_name = next(
                entry for entry in entries
                if entry["table"] == "sorcerers" and entry["source"]["sorcerer_id"] == "S8"
            )
            self.assertEqual(
                corrected_name["changes"]["name"], {"before": "adekaT aniH", "after": "Hina Takeda"}
            )
            path.write_text("stale data", encoding="utf-8")
            write_changelog(self.db, path)
            self.assertNotIn("stale data", path.read_text(encoding="utf-8"))

    def test_rct_screen_requires_repeated_visits_and_reliable_firmware(self) -> None:
        self.db.executescript(
            """
            INSERT INTO sorcerers VALUES ('S5', 'Fifth', '1', 'Tokyo', '', '2024-01-01', 'active');
            INSERT INTO sorcerers VALUES ('S6', 'Sixth', '1', 'Tokyo', '', '2024-01-01', 'active');
            UPDATE missions SET sorcerer_ids = 'S1|S2|S5|S6' WHERE mission_id = 'M1';
            INSERT INTO device_assignments VALUES ('D5', 'S5', '2025-01-01T00:00:00Z', '');
            INSERT INTO device_assignments VALUES ('D6', 'S6', '2025-01-01T00:00:00Z', '');
            INSERT INTO infirmary_visits VALUES ('V5a', 'S5', 'M1', '2025-01-03 09:00',
                '2025-01-03 14:00', 'CEX-05', '5', 'ward');
            INSERT INTO infirmary_visits VALUES ('V5b', 'S5', 'M1', '2025-01-04 09:00',
                '2025-01-04 14:00', 'CEX-05', '5', 'ward');
            INSERT INTO infirmary_visits VALUES ('V6a', 'S6', 'M1', '2025-01-03 09:00',
                '2025-01-03 14:00', 'CEX-05', '5', 'ward');
            INSERT INTO infirmary_visits VALUES ('V6b', 'S6', 'M1', '2025-01-04 09:00',
                '2025-01-04 14:00', 'CEX-05', '5', 'ward');
            INSERT INTO ce_wearable VALUES ('D5', '2025-01-03T01:00:00Z', '20', 'v2.2');
            INSERT INTO ce_wearable VALUES ('D5', '2025-01-03T02:00:00Z', '20', 'v2.2');
            INSERT INTO ce_wearable VALUES ('D5', '2025-01-04T01:00:00Z', '20', 'v2.4');
            INSERT INTO ce_wearable VALUES ('D5', '2025-01-04T02:00:00Z', '20', 'v2.4');
            INSERT INTO ce_wearable VALUES ('D6', '2025-01-03T01:00:00Z', '20', 'v2.3');
            INSERT INTO ce_wearable VALUES ('D6', '2025-01-03T02:00:00Z', '20', 'v2.3');
            INSERT INTO ce_wearable VALUES ('D6', '2025-01-04T01:00:00Z', '20', 'v2.3');
            INSERT INTO ce_wearable VALUES ('D6', '2025-01-04T02:00:00Z', '20', 'v2.3');
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.db"
            final_path = Path(directory) / "final.db"
            self.db.commit()
            with closing(sqlite3.connect(raw_path)) as raw:
                self.db.backup(raw)
            create_final_database(raw_path, final_path)
            with closing(sqlite3.connect(final_path)) as final:
                candidates = find_rct_candidates(final)
                self.assertEqual(list(candidates), ["S5"])
                self.assertEqual(final.execute("SELECT typeof(severity) FROM infirmary_visits LIMIT 1").fetchone()[0], "integer")
                self.assertEqual(final.execute("SELECT typeof(ce_level) FROM ce_wearable LIMIT 1").fetchone()[0], "real")
                self.assertEqual([item.visit_id for item in candidates["S5"]], ["V5a", "V5b"])
                final.execute("DELETE FROM ce_wearable WHERE device_id='D5' AND ts='2025-01-04T02:00:00Z'")
                self.assertEqual(find_rct_candidates(final), {})

    def test_sorcerer_name_requires_both_supported_components(self) -> None:
        self.db.executescript(
            """
            INSERT INTO sorcerers VALUES ('S7', 'Hina Takeda', '1', 'Tokyo', '', '2024-01-01', 'active');
            INSERT INTO sorcerers VALUES ('S8', 'adekaT aniH', '1', 'Tokyo', '', '2024-01-01', 'active');
            INSERT INTO sorcerers VALUES ('S9', 'nwonknU aniH', '1', 'Tokyo', '', '2024-01-01', 'active');
            """
        )
        self.assertEqual(
            self.db.execute("SELECT name, name_status FROM clean_sorcerers WHERE sorcerer_id='S8'").fetchone(),
            ("Hina Takeda", "reversed"),
        )
        self.assertEqual(
            self.db.execute("SELECT name, name_status FROM clean_sorcerers WHERE sorcerer_id='S9'").fetchone(),
            ("nwonknU aniH", "unresolved"),
        )
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.db"
            self.db.commit()
            with closing(sqlite3.connect(raw_path)) as raw:
                self.db.backup(raw)
            with self.assertRaisesRegex(ValueError, "unresolved sorcerer name"):
                create_final_database(raw_path, Path(directory) / "final.db")

    def test_invalid_numeric_values_stop_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.db"
            self.db.commit()
            with closing(sqlite3.connect(raw_path)) as raw:
                self.db.backup(raw)
                for value in ("nan", "1_2", "1e999"):
                    raw.execute("UPDATE ce_wearable SET ce_level = ? WHERE rowid = 1", (value,))
                    raw.commit()
                    with self.subTest(value=value), self.assertRaisesRegex(ValueError, "ce_wearable.ce_level"):
                        create_final_database(raw_path, Path(directory) / "final.db")

    def test_timezone_hypothesis_preserves_dates_and_repairs_negative_interval(self) -> None:
        self.db.executescript(
            """
            INSERT INTO missions VALUES ('before', '2026-02-27T23:54:00Z', '2026-02-28T03:02:00Z',
                'Kita', '1', 'S1', 'failed', '', '');
            INSERT INTO missions VALUES ('after', '2026-02-28T05:41:00Z', '2026-02-28T08:25:00Z',
                'Kita', '1', 'S1', 'failed', '', '');
            INSERT INTO infirmary_visits VALUES ('before-visit', 'S1', 'before', '2026-02-28 13:51',
                '2026-02-28 21:31', 'BRN-02', '2', 'ward');
            INSERT INTO infirmary_visits VALUES ('after-visit', 'S1', 'after', '2026-02-28 19:14',
                '2026-02-28 17:25', 'ABR-01', '1', 'ward');
            INSERT INTO infirmary_visits VALUES ('no-mission', 'S1', '', '2026-02-28 19:14',
                '2026-02-28 17:25', 'TST-00', '1', 'ward');
            """
        )
        before = self.db.execute(
            "SELECT admitted_at_utc, discharged_at_utc, timestamp_assumption, estimated_recovery_hours "
            "FROM estimated_infirmary_visits WHERE visit_id='before-visit'"
        ).fetchone()
        after = self.db.execute(
            "SELECT admitted_at_utc, discharged_at_utc, timestamp_assumption, estimated_recovery_hours "
            "FROM estimated_infirmary_visits WHERE visit_id='after-visit'"
        ).fetchone()
        self.assertEqual(before[:3], ("2026-02-28T04:51:00Z", "2026-02-28T12:31:00Z", "dictionary_jst"))
        self.assertAlmostEqual(before[3], 7 + 40 / 60)
        self.assertEqual(after[:3], ("2026-02-28T10:14:00Z", "2026-02-28T17:25:00Z", "inferred_discharge_utc"))
        self.assertAlmostEqual(after[3], 7 + 11 / 60)
        self.assertEqual(
            self.db.execute(
                "SELECT timestamp_assumption, discharged_at_utc FROM estimated_infirmary_visits "
                "WHERE visit_id='no-mission'"
            ).fetchone(),
            ("unresolved_mission", None),
        )


if __name__ == "__main__":
    unittest.main()
