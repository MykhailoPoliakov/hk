# Jujutsu data pipeline

Run from the project folder:

```powershell
python -B .\src
```

The run rebuilds the databases and reports in a temporary directory, then replaces
the generated outputs. It does not modify the source CSVs. Only drop 0 is
implemented; changing `DROP` to a later drop currently raises an error.

## Files

- `initial_data\`: original CSVs.
- `data.db`: raw CSV tables and SQL review views.
- `final.db`: materialized analysis tables, with UTC visit timestamps.
- `target\answers.txt`: provisional answers and their evidence.
- `target\chlogs.txt`: one JSON object per changed or flagged source row.
- `src\`: pipeline and analysis code; `src\sql\` contains the review views.
- `tests\`: focused tests.

`final.db` is a curated dataset, not a guarantee of ground truth. Its
`data_assumptions` table documents the decisions. In particular, admission times
are treated as JST; discharge times for missions starting on or after
2026-02-28 00:00 UTC are treated as UTC. This cutoff is inferred from the data
and is **not confirmed**. Rows with ambiguous timestamps or test/missing mission
records are excluded; historical IDs remain flagged.

Wearable readings with v2.3 or unknown firmware and uncertain current-holder
attribution are excluded. Kyoto barrier values remain in recorded units and
are flagged for unit review. The D1 list is a candidate screen, not proof of
self-healing: healer sessions and later corrections are not yet available.

Names that appear fully reversed are corrected only when both resulting name
components occur in normally formatted roster entries. This is an inference,
not independent proof of a person's identity. Unresolved reversed-looking names,
invalid numeric values and inconsistent mission references stop the build.
Missing technique values remain blank. The row log includes numeric type
conversions, so it contains millions of entries and can be large.
