# Looker Studio report: complete build guide

This guide is for building the report manually in Looker Studio. It describes
the current Drop 2 exports; the project does **not** create or publish the
report for you.

## 1. The story

The Principal should be able to follow this sequence without a presenter:

1. **Answer:** three active sorcerers meet our RCT screening rule.
2. **Evidence:** inspect each person's four severe, fast recoveries and the
   wearable readings during each stay.
3. **Road to the answer:** show how the current diagnostic screen changes
   as we interpret timestamps and filter recorded healer overlaps.
4. **Data quality:** show the impossible negative recovery intervals before
   and after our inferred timestamp interpretation.

The report should call these people **candidates supported by evidence**, not
proven RCT users. An absent healer record is not proof of no assistance.

## 2. Prepare and connect the data

The flow is:

`initial_data` -> SQLite import and correction feed -> `data.db` review views
and `final.db` curated tables -> shared RCT screen -> dashboard CSVs -> Looker
Studio report.

1. Make sure `DROP` in [`src\__main__.py`](../src/__main__.py) is `2` and
   the required input files are present.
2. From the project root, run `python -B .\src` to rebuild the databases,
   answers and dashboard CSVs. This replaces generated outputs. To regenerate
   only dashboard CSVs from the existing databases, run
   `python -B .\dashboard\export.py`.
3. In Looker Studio, create a report and add each CSV in
   [`dashboard_data`](dashboard_data) as a **separate CSV upload data source**:

| Data source | One row means | Current rows | Used on |
|---|---|---:|---|
| `candidates.csv` | One shortlisted sorcerer | 3 | Answer |
| `visits.csv` | One qualifying visit | 12 | Evidence |
| `readings.csv` | One attributed reading during a qualifying visit | 99 | Evidence |
| `stages.csv` | One candidate at one diagnostic stage | 21 | Road |
| `rejection_evidence.csv` | One visit from a candidate dropped by a stage | 9 | Road |
| `timing_quality.csv` | One timestamp interpretation | 2 | Data quality |
| `firmware_quality.csv` | One firmware version | 3 | Data quality |

4. Check field types when connecting: IDs and labels are text; counts,
   `included`, hours, `ce_level` and `positive_rate` are numeric. Format
   `positive_rate` as a percentage: the CSV contains fractions, not numbers
   already multiplied by 100. Keep IDs as text.
5. For the readings chart, create a date-time field from
   `timestamp_display_utc`:

   ```text
   PARSE_DATETIME("%Y-%m-%d %H:%M:%S", timestamp_display_utc)
   ```

   Name it `reading_datetime_utc` and check its date-time type. The source
   values are UTC; label them as UTC. Avoid changing their interpretation to
   local time. If the chart groups readings by day, choose a date-time
   granularity that preserves individual hours. If that is not available,
   show an ascending timestamp and CE table for each visit instead of
   presenting daily averages as hourly readings.

**Important:** uploading a new CSV to an existing upload dataset can append
rows. Replace or recreate the data source rather than blindly adding the
same CSV again. Verify row counts and reconnect affected charts after any
replacement. The exact menus can change; see the
[Google CSV upload guide](https://docs.cloud.google.com/looker/docs/studio/upload-csv-files-to-looker-studio).

## 3. Report layout

Use six pages: an answer, one evidence page per candidate, a road-to-answer
page and a data-quality page. Add page navigation buttons, readable titles,
data labels and a short explanatory caption on every page. Colors should
identify meaning consistently, such as green for retained candidates,
orange for assumptions and red for rejected evidence.

### Page 1: The answer

**Title:** `Three active sorcerers meet the RCT evidence screen`

Add a table using `candidates.csv`:

| Field | Role |
|---|---|
| `sorcerer_id` | Dimension |
| `name` | Dimension |
| `grade` | Dimension |
| `school` | Dimension |
| `qualifying_visits` | Metric; use MAX per sorcerer |

Expected output:

| ID | Name | Grade | School | Qualifying visits |
|---|---|---|---|---:|
| S-0009 | Jin Hirose | 1 | Kyoto | 4 |
| S-0101 | Yui Tsukishima | Special | Tokyo | 4 |
| S-0533 | Saki Enomoto | Special | Kyoto | 4 |

Add scorecards for **3 candidates** (`COUNT_DISTINCT(sorcerer_id)` from
`candidates.csv`), **12 qualifying visits** (`COUNT_DISTINCT(visit_id)` from
`visits.csv`) and **99 readings** (row count from `readings.csv`). Do not
sum a visit count after joining to readings: each visit has multiple readings.

**Copy for the page:**

> These three active sorcerers each have four qualifying visits. We look for
> repeated severe, fast recoveries with sustained positive wearable readings
> and no recorded overlapping healer session. This is a screening result,
> not proof of self-healing.

**Rule, in one sentence:**

> An active current ID qualifies if it has at least two mission-linked,
> recorded severity 4 or 5 visits lasting under 24 hours, each with at least
> two consecutive positive hourly readings from an attributed v2.2/v2.4
> device during the stay and no recorded overlapping healer session.

The code applies identity and timing eligibility checks too. The severity
interpretation, 24-hour limit, consecutive-reading requirement and minimum
number of visits are screening choices, not validated biological thresholds.

### Pages 2-4: Evidence, one page per candidate

Create one page for each ID. Use the same layout on each page so comparisons
are easy. Add the candidate name, ID, grade and school in the title.

| Page | Candidate | Visits to show |
|---|---|---|
| 2 | Jin Hirose, S-0009, grade 1, Kyoto | V-001882, V-003415, V-004873, V-006739 |
| 3 | Yui Tsukishima, S-0101, Special, Tokyo | V-003938, V-004231, V-005861, V-006940 |
| 4 | Saki Enomoto, S-0533, Special, Kyoto | V-000754, V-003540, V-005347, V-007114 |

**A. Recovery chart**

1. Add a bar chart using `visits.csv`.
2. Filter the chart to include `sorcerer_id` equal to the page's candidate.
3. Dimension: `visit_id`. Metric: `recovery_hours`, aggregated with **MAX**
   per visit. Label the axis `Estimated recovery time (hours)`.
4. Add a reference line at 24 hours if available; otherwise add a visible
   note: `The screen requires recovery under 24 hours`.
5. Check that the chart shows four distinct visit IDs.

**B. Visit evidence table**

Use `visits.csv`, filtered to the same candidate. Show `visit_id`, `severity`,
`admitted_at_utc`, `discharged_at_utc`, `recovery_hours`,
`positive_readings`, `longest_positive_streak`, `first_positive_device`,
`first_positive_firmware` and `healer_status`. Add `timestamp_assumption`
if there is room. Each row is one qualifying visit. The first positive device
and firmware are not necessarily the only device and firmware in a stay.

**C. Four wearable charts**

For each of that candidate's four visits:

1. Add a time-series/line chart using `readings.csv`.
2. Add a chart filter: `visit_id` equals that visit's ID. Use the exact IDs
   in the table above. Title the chart with the ID.
3. Dimension: `reading_datetime_utc`; metric: `ce_level`, using AVG if a
   numeric aggregation is required. Sort timestamp ascending, preserve
   hourly detail, and add a zero reference line if available.
4. Check the chart or its underlying table shows the individual readings,
   not a daily total. Do not join separate visits into one continuous line.
   The current data has no repeated timestamp within a visit, so AVG does not
   combine current readings. If this changes in a future export, inspect
   readings by device and timestamp rather than hiding them with an average.
5. Repeat for all four visits; duplicate a chart and change its filter to
   save time. Test all 12 visit filters across the three pages.

If there is not enough room, use separate visit-filtered timestamp/CE tables
or a working single-visit selector instead. Confirm that a selector actually
filters the readings chart and only one visit is selected. Controls using
different uploaded sources may not automatically filter one another; this
guide deliberately uses chart-specific filters instead of assuming they do.

**Copy for each evidence page:**

> Four recorded severe visits recovered in less than 24 hours under our
> timestamp interpretation. The readings shown were attributed to the
> candidate's device during each stay. No overlapping healer session is
> recorded; an incomplete healer record remains possible.

Across all three candidates, the current 12 stays contain 99 attributed
readings in the exported curated data, all positive. Readings are selected
from admission inclusive to discharge exclusive. The chart should still
show zero or negative readings if a future export contains them.

### Page 5: Road to the answer

**Title:** `How the current diagnostic shortlist changed`

**A. Stage chart**

1. Use `stages.csv` in a bar chart.
2. Dimension: `stage`. Metric: `SUM(included)`. Each `included` value is
   1 or 0 for one candidate at one stage; summing it counts candidates.
3. Sort by `stage_order` ascending where supported. If necessary, display
   the three stages in a small ordered table instead.
4. Check the bars read **7 -> 4 -> 3**:

| Diagnostic stage on the current Drop 2 data | Candidates |
|---|---:|
| Before inferred timestamp correction | 7 |
| After inferred timestamp correction, before healer filter | 4 |
| After recorded healer filter | 3 |

**Caption:**

> These are retrospective diagnostic stages rerun on the current Drop 2
> data, not historical Drop 0 and Drop 1 snapshots.

**B. Why candidates dropped out**

Add a table using `rejection_evidence.csv`. Show `sorcerer_id`, `visit_id`,
`before_recovery_hours`, `corrected_recovery_hours`,
`overlapping_healer_sessions` and `reason`. Filter or split by `stage_order`
if the table is too wide.

Add this explanation beside it:

| Candidate | Reason for dropping from the diagnostic |
|---|---|
| S-0034 | Two previously qualifying stays become 27.42 h and 29.20 h after the inferred correction. |
| S-0403 | Three previously qualifying stays become 30.75 h, 29.43 h and 31.10 h. |
| S-0655 | Two previously qualifying stays become 30.87 h and 31.77 h. |
| S-0663 | Both qualifying stays overlap recorded healer sessions: V-001738 / HS-01200 and V-002196 / HS-01518. |

These are reasons the candidates **no longer meet the screen**, not proof
that they cannot use RCT. A healer session explains evidence for that visit,
not the sorcerer's capabilities.

**C. Historical submission context**

If desired, add a separate text box, clearly distinguished from the
diagnostic chart:

> The team reports that its Drop 0 submission of four IDs was marked
> correct. The Drop 1 submission of S-0009, S-0101 and S-0533 was also
> marked correct. The Drop 2 screen retains those three IDs.

The historical submission results come from team feedback, not from
`stages.csv`.

### Page 6: Data quality

**Title:** `The curse in the data: before and after`

**A. Required before/after chart: negative recovery intervals**

1. Add a bar chart from `timing_quality.csv`.
2. Dimension: `interpretation`. Metric: `SUM(negative_intervals)`.
3. Label the two bars and check the values:

| Timestamp interpretation | Negative intervals |
|---|---:|
| Before inferred timezone correction | 1,135 |
| After inferred timezone correction | 0 |

4. Also show `unresolved_intervals`, currently 0, as a small table or note.

**Copy beside the chart:**

> Some visits appeared to end before admission. We interpreted admissions
> as JST and discharges as JST before an inferred mission-start cutoff and
> UTC afterward. On the same effective Drop 2 visits with resolvable timing,
> the count of negative intervals changed from 1,135 to 0.

**Caveat:** the discharge timezone and cutoff are inferred. An audit entry
records a discharge-terminal clock change on 2026-02-28 but does not state
the timezone or exact effective cutoff. Removing negative intervals is
evidence of internal consistency, not proof the interpretation is correct.
Counts are visits, not distinct people.

**B. Additional chart: suspicious firmware**

1. Use `firmware_quality.csv` for a bar chart.
2. Dimension: `firmware`. Metric: `MAX(positive_rate)`, formatted as a
   percentage. The CSV has one row per firmware.
3. Show a table with `positive_readings` and `total_readings` alongside it.

| Firmware | Positive / total | Positive rate |
|---|---:|---:|
| v2.2 | 18,997 / 2,996,234 | 0.63% |
| v2.3 | 130,582 / 130,840 | 99.80% |
| v2.4 | 11,950 / 2,009,323 | 0.59% |

**Caption:** `v2.3 is anomalous and excluded from the screen; the rate alone
does not establish the cause.` This compares firmware versions; it is **not**
itself a before/after fix chart. Chart A meets that requirement.

## 4. Final checks and publishing

- Check the report answers all four requirements: candidate names/grades/
  schools; each candidate's recoveries and in-stay readings; progression and
  rejection evidence; and an explicit before/after quality chart.
- Check IDs, 3 / 12 / 99 totals, 7 -> 4 -> 3 stages and 1,135 -> 0 intervals
  against the current CSVs. Check all 12 visit filters and hourly timestamps.
- The displayed numbers and pasted text are snapshots. After a rerun, inspect
  the new CSVs, update the data sources and revise static copy, IDs and
  captions if results changed. Avoid duplicate uploads.
- Use [`target\answers.txt`](../target/answers.txt) for the full latest
  evidence and [`dashboard\README.md`](README.md) for the concise overview.
  The report is focused on the dashboard requirements; other challenge
  answers and the bonus need additional content and data if included.
- Share the report with **anyone with the link** only if these data may be
  published. Open the link in a private browser window and verify every
  page, chart and filter without signing in. Submit the report link to the
  jury; creating the CSVs alone does not submit a dashboard.
