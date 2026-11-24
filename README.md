# Jujutsu Records: RCT investigation

This project imports the challenge CSVs into SQLite, preserves the source data,
replays the Drop 2 infirmary change feed, and screens for evidence of
unassisted fast recovery. The full generated numbers and visit-level evidence
are in `target\answers.txt`. See [DEFENSE.md](info/DEFENSE.md) for a jury guide.

## Run

In PowerShell, from the project root:

```powershell
python -B .\src
python -B -m unittest discover -s tests -v
```

Set `DROP` in `src\__main__.py` to 0, 1 or 2. Later-drop files are ignored
when an earlier drop is selected; files required for the selected drop must
exist. The default is Drop 2. Builds use a temporary directory, then replace
`data.db`, `final.db`, `target\chlogs.txt` and `target\answers.txt` after
the analysis succeeds. The replacement of the four individual outputs is not
a single atomic transaction. Keep enough free disk space for both generations
of the large databases and log.

## Files and data flow

| Location | Role |
|---|---|
| `tasks\` | Challenge statements, including Drop 2 bonus and dashboard requirements. |
| `info\` | Jury preparation and explanatory guides. |
| `dashboard\` | Dashboard instructions and export script. |
| `dashboard\dashboard_data\` | Regenerated CSV data sources for Looker Studio. |
| `initial_data\` | Original CSVs: seven Drop 0 tables, `healer_sessions.csv` from Drop 1, and `infirmary_corrections.csv` and `audit_log.csv` from Drop 2. |
| `data_dictionary.md`, `brief.pdf` | Original reference documents; dictionary claims must be checked against the data. |
| `src\create_db.py` | Imports one raw table per selected CSV. Wearables are streamed in batches. The two infirmary CSVs use CP932; other files use UTF-8. |
| `src\corrections.py` | Replays ordered inserts, updates and deletes to `effective_infirmary_visits` and stores before/after `correction_history`; raw tables are untouched. |
| `src\sql\` | Cleaning, attribution, timestamp and healer-overlap views. |
| `src\curate_db.py`, `src\rct.py` | Materialize the analysis database and apply one repeated-visit RCT screening rule. |
| `src\changelog.py`, `src\answers.py` | Write row-level JSON Lines and the evidence report. The log is replaced, not appended, and can exceed 1 GB. |
| `data.db` | Original imported tables, effective visits, correction history and review views. Audit and healer records are retained here. |
| `final.db` | Curated analysis tables. Its infirmary table excludes recorded healer-overlap visits, so it is **not** the population for general recovery medians. |
| `tests\` | Unit tests for normalization, change replay, healer overlap and screening. |

## Current Drop 2 results

The user reports the Drop 0 and Drop 1 submissions were marked correct.
Drop 0's list was `S-0009, S-0101, S-0533, S-0663`; Drop 1's list was
`S-0009, S-0101, S-0533`. Applying Drop 2 corrections leaves the current
screening shortlist unchanged: **S-0009, S-0101, S-0533**. Each has four
qualifying visits with no recorded overlapping healer session. This is a
screening result, not a medical proof of ability.

Bonus host candidate: **S-0033, Itsuki Minase**. Audit account
`hlr.minase.i` performed 40 v2.3 firmware pushes, the severity-dictionary
edit, a discharge-clock change, and eight ID reassignments. The account name
matches Itsuki Minase, whose roster technique is Medical Support and who
appears as a healer in 690 sessions. Account ownership and intent are inferred,
not directly proven by the log.

The correction feed has 322 inserts, 900 updates and 22 deletes, applied in
sequence. There are 8,125 effective visits. For C1, use all eligible
mission-linked visits, including healer-assisted visits: severity 1: 6.95 h;
2: 18.13 h; 3: 59.25 h; 4: 128.06 h; 5: 245.73 h. Values depend on the
timestamp assumption below.

## Assumptions and limitations

* Admission times are interpreted as JST; discharge times are interpreted as
  JST before the inferred mission-start cutoff `2026-02-28T00:00:00Z`, and
  as UTC after it. Audit A-028981 records a discharge-terminal clock change
  on that day, but does not state its timezone or exact effective cutoff.
  Correct challenge submissions do not prove this interpretation.
* Recorded severity 4/5 is used as the severe end of the screen because
  observed durations rise with the code. The dictionary says the reverse;
  audit A-019523 records an edit, not the original scale.
* The 24-hour limit, two positive hourly readings and two visits are
  screening choices, not validated biological thresholds. The dictionary's
  positive-energy claim may not hold for firmware v2.3, which is excluded.
* No recorded healer overlap does not prove no assistance. Likewise, an
  overlapping healer explains a visit but does not prove a person cannot
  perform RCT.
* Kyoto sensor readings are kept in recorded units; their much larger scale
  is unverified. Casualty IDs can be reused. Roster matching and name reversal
  are documented in the report and remain subject to review.
* The challenge asks for a notebook and a Looker Studio dashboard. This
  repository provides a Python/SQLite pipeline and dashboard CSV exports;
  the notebook, dashboard report and public link are not yet provided.

## Jury preparation

[QUICK_REFERENCE.md](info/QUICK_REFERENCE.md) summarizes results;
[SQL_DEMO_QUERIES.md](info/SQL_DEMO_QUERIES.md) contains SQLite queries;
[dashboard/README.md](dashboard/README.md) describes the Looker Studio report.
Use [target/answers.txt](target/answers.txt) for the latest generated report.
