# 📚 Jujutsu High RCT Detection - Complete Learning & Defense Guide

**Last Updated:** Drop 1 (2026-11-24)  
**Status:** ✅ Drop 0 answers validated by Principal  
**Final Candidates:** S-0009, S-0101, S-0533

---

## 🎯 Quick Navigation

| Goal | File | Time |
|------|------|------|
| **I need to defend my project NOW** | 📄 [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) | 5 min read |
| **I want to understand everything** | 📄 [DEFENSE.md](DEFENSE.md) | 30 min read |
| **I need SQL queries to demo** | 📄 [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) | 10 min reference |
| **I want 60-second pitch** | ⬇️ Below | 1 min |
| **I want to run the pipeline** | 💻 `python .\src` | 5–10 min |

---

## 🚀 60-Second Elevator Pitch

```
The Inverter curse corrupted 48 million records in Jujutsu High's database.
We built a rerunnable data pipeline to find sorcerers who can self-heal (RCT).

WHAT WE DID:
1. Cleaned the data (27 reversed names, 2,786 reversed wards, 1,086 negative timestamps)
2. Defined RCT proof: severity 4–5 injury + under 24-hour recovery + consistent positive CE
3. Found 3 candidates: S-0009, S-0101, S-0533 (each with 4+ matching visits)
4. VALIDATED: Drop 0 answers (4 IDs) marked CORRECT by Principal

WHY TRUST US:
- External validation: Principal confirmed our timestamp interpretation
- Multiple evidence per candidate (not cherry-picked)
- Filtered false positives (v2.3 firmware excluded, external healers excluded)
- Fully auditable: 1.34 GB JSON log, deterministic reruns, all SQL logic tracked

BOTTOM LINE:
These 3 candidates have strong RCT signatures. Final proof requires field validation
(can they actually self-heal?), but we're confident in the data shortlist.
```

---

## 📂 Project Structure at a Glance

```
hk/
├── DEFENSE.md ........................... Full jury defense guide (30 min read)
├── JURY_TALKING_POINTS.md .............. Bullet-point talking points (10 min)
├── SQL_DEMO_QUERIES.md ................. Live demo queries (copy/paste ready)
├── README.md ........................... Original project README
├── 
├── initial_data/ ....................... Input CSVs (Drop 0 + Drop 1)
│   ├── sorcerers.csv
│   ├── missions.csv
│   ├── infirmary_visits.csv
│   ├── ce_wearable.csv (5M+ rows)
│   ├── barrier_sensors.csv
│   ├── device_assignments.csv
│   └── healer_sessions.csv (Drop 1)
│
├── src/ ................................ Pipeline source code
│   ├── __main__.py ..................... Entry point: run with `python .\src`
│   ├── create_db.py .................... Load CSVs → data.db
│   ├── fix_db.py ....................... Execute SQL cleaning scripts
│   ├── curate_db.py .................... Materialize final.db (clean only)
│   ├── rct.py .......................... RCT screening algorithm
│   ├── changelog.py .................... JSON logging of all changes
│   ├── answers.py ...................... Generate answers A1–D2
│   │
│   └── sql/ ............................ Cleaning scripts (executed in order)
│       ├── 00_sorcerers.sql ............ Name reversal detection
│       ├── 01_missions.sql ............ Dedup + ward reversal
│       ├── 02_infirmary_visits.sql .... Injury code normalization
│       ├── 03_wearable.sql ............ v2.3 firmware filtering
│       ├── 04_identity.sql ............ Pre-join-date visit detection
│       ├── 05_context.sql ............. Barrier sensor context
│       ├── 06_estimated_timestamps.sql  UTC/JST correction (VALIDATED)
│       └── 07_healer_sessions.sql .... Healer overlap detection (Drop 1)
│
├── target/ ............................. Output files (regenerated each run)
│   ├── answers.txt ..................... Evidence-backed answers A1–D2
│   └── chlogs.txt ...................... 1.34 GB JSON Lines log (every row change)
│
├── data.db ........................... Raw tables + 8 SQL views (source of truth)
├── final.db .......................... Clean tables only (used for analysis)
│
├── tests/ ............................. Unit test suite
│   └── test_review_views.py ............ 7 tests: timezone, boundaries, names, candidates
│
└── brief.pdf, data_dictionary.md .... Original challenge documents
```

---

## 🎓 Learning Path (Recommended Order)

### Level 1: Understand the Mission (5 min)
1. Read [brief.pdf](brief.pdf)
2. Read [data_dictionary.md](data_dictionary.md)
3. skim [target/answers.txt](target/answers.txt) — see all questions answered

### Level 2: Understand the Approach (15 min)
1. Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — "Five Core Arguments"
2. Run the pipeline: `python .\src` (takes 5–10 minutes)
3. Check output: `type target\answers.txt` → see all answers with evidence

### Level 3: Understand the Data (20 min)
1. Open `data.db` in SQLite browser
2. Run these queries:
   ```sql
   -- How many clean sorcerers?
   SELECT COUNT(*) FROM clean_sorcerers;
   
   -- Show a reversed ward example
   SELECT DISTINCT original_ward, ward FROM clean_missions
   WHERE original_ward != ward LIMIT 5;
   
   -- How many negative intervals were fixed?
   SELECT COUNT(*) FROM estimated_infirmary_visits WHERE recovery_hours < 0;
   ```
3. Open `final.db` and check `infirmary_visits` table (the one used for RCT screening)

### Level 4: Understand the Cleaning (30 min)
1. Read [DEFENSE.md](DEFENSE.md) — "Data Quality Fixes (B5 - Curse Log)"
2. For each issue (names, wards, timestamps):
   - Understand the problem
   - Find the detection logic (SQL file listed)
   - Run the SQL query to see before/after
3. Read `src/sql/06_estimated_timestamps.sql` — understand the UTC/JST cutoff

### Level 5: Understand RCT Screening (20 min)
1. Read [DEFENSE.md](DEFENSE.md) — "RCT Screening Logic (C2 Definition)"
2. Read `src/rct.py:45-80` (the core algorithm)
3. Run SQL from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md):
   - Query #6: See severity medians (why 24h is an outlier)
   - Query #7: See all 3 candidates
   - Query #8: Zoom in on S-0009

### Level 6: Understand Validation (15 min)
1. Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — "Argument 2: Drop 0 Validation"
2. Run query #10 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) — see healer filter
3. Run query #12 — verify determinism (same hash on reruns)

### Level 7: Prepare Jury Defense (1 hour)
1. Reread [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — "Five Core Arguments" + "Tough Questions & Answers"
2. Copy [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) queries into SQLite browser (pre-test them all)
3. Practice the "Recommended Jury Presentation Flow" from [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) (use a timer, aim for 15 min)
4. Write speaker notes for each slide
5. Identify 2–3 questions you're weakest on; prepare detailed answers

---

## ✅ Checklist: Before Jury Day

- [ ] Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) (at least twice)
- [ ] Read [DEFENSE.md](DEFENSE.md) (focus on sections D1–D2)
- [ ] Practice running pipeline live: `python .\src` → check output
- [ ] Test all queries from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) in SQLite
- [ ] Create slide deck (8 slides, 15 min total presentation)
- [ ] Memorize "60-Second Elevator Pitch" above
- [ ] Memorize "Key Figures" table from [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)
- [ ] Practice answering "Tough Questions" from [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)
- [ ] Have SQLite browser open with data.db + final.db loaded
- [ ] Have terminal ready to run `python .\src` live (if requested)
- [ ] Print or bookmark this file for quick reference during Q&A

---

## 🎯 Key Facts to Know Cold

### The Problem
- **Inverter curse** corrupted Records Office data 6 months ago
- Sorcerers with **RCT** can self-heal (turn cursed energy positive)
- Need to prove which living sorcerers have this ability **using corrupted data**
- Every number must be defensible; Inverter creates fake miracles

### The Solution
- **Data cleaning:** 10 corruption patterns fixed (27 names, 2,786 wards, 1,086 timestamps, etc.)
- **RCT definition:** Severity 4–5 + <24h recovery + ≥2 consecutive positive CE readings + no external healer
- **Filtering:** 7 → 4 → 3 candidates (dropped S-0663 via Drop 1 healer filter)
- **Validation:** Drop 0 answers (4 IDs) marked CORRECT by Principal ✅

### The Answer
- **S-0009:** 4 visits (5.28–13.83h), all severity 5
- **S-0101:** 4 visits (5.80–11.60h), 3 severity 5 + 1 severity 4
- **S-0533:** 4 visits (6.22–8.52h), 2 severity 4 + 2 severity 5
- **Why strong:** Multiple independent visits, consistent pattern, filtered false positives, external validation

### Key Evidence
- Timestamp interpretation validated by Principal (Drop 0 correct)
- Determinism proven (same hash on reruns)
- Audit trail complete (1.34 GB JSON log, all SQL tracked)
- Filtering conservative (v2.3 excluded, healers excluded, ID reuse flagged)

---

## 🛠️ How to Run the Pipeline

### Standard Run
```bash
cd c:\Users\Michael\projects\hk
python .\src
```

Takes 5–10 minutes. Output:
- `data.db` — raw tables + 8 SQL views
- `final.db` — clean tables (used for analysis)
- `target/answers.txt` — full answers A1–D2
- `target/chlogs.txt` — 1.34 GB JSON log

### For Drop 2 (When Available)
1. Download Drop 2 file(s) to `initial_data/`
2. Edit `src/__main__.py`: change `DROP = 1` to `DROP = 2`
3. Run `python .\src`
4. Check `target/answers.txt` for updated results

### Live Demo for Jury
```bash
# Terminal 1: Run pipeline
python .\src

# Terminal 2 (while running): Open SQLite browser with final.db
# After pipeline finishes: Run queries from SQL_DEMO_QUERIES.md
```

---

## 📊 One-Page Reference: All Answers

| Question | Answer | Evidence |
|----------|--------|----------|
| **A1** - Special file handling? | ce_wearable.csv (5M+ rows streamed), infirmary_visits.csv (CP932 encoding), others standard | `src/create_db.py` |
| **A2** - Unique missions? | 35,000 (from 35,715 rows; 715 exact dupes) | `src/sql/01_missions.sql` |
| **B1** - Wards? | 21 unique wards (after reversing 2,786 corrupted names) | `clean_missions GROUP BY ward` |
| **B2** - Median residual CE? | Tokyo 19.70, Kyoto 16,234.11 (1000x scale unconfirmed) | `barrier_by_ward query` |
| **B3** - Killed in action? | 33 distinct IDs (May 2025–Oct 2026, some ID reuse cases) | `mission_casualties filter` |
| **B4** - Dictionary errors? | 4 major errors (blank mission_id, reversed wards, ID reuse, v2.3 anomaly) | Each documented in DEFENSE.md |
| **B5** - Curse log? | 10+ categories: 27 names, 715 dupes, 2,786 wards, 1,086 timestamps, etc. | `target/chlogs.txt` (1.34 GB) |
| **C1** - Median recovery? | S1=6.93h, S2=17.87h, S3=59.25h, S4=119.42h, S5=224.45h | `final.db infirmary_visits` |
| **C2** - RCT definition? | Severity 4–5 + <24h + ≥2 consecutive positive CE + no healer + v2.2/v2.4 device | `src/rct.py:45-80` |
| **D1** - RCT candidates? | **S-0009, S-0101, S-0533** (Drop 1 final answer) | `target/answers.txt` D1 |
| **D2** - False positives? | S-0663 (healer), S-0034/S-0403/S-0655 (timezone shift) | Query #10 & #11 in SQL_DEMO_QUERIES.md |

---

## 🎓 For Deep Dives

### I want to understand timestamp correction
→ Read [DEFENSE.md](DEFENSE.md) section "4. Timestamp Chaos"  
→ Run Query #4 and #3 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)  
→ Read `src/sql/06_estimated_timestamps.sql`

### I want to understand name reversal detection
→ Read [DEFENSE.md](DEFENSE.md) section "1. Reversed Sorcerer Names"  
→ Run Query #2 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)  
→ Read `src/sql/00_sorcerers.sql`

### I want to understand healer filtering
→ Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) "Argument 4: Filtering Was Rigorous"  
→ Run Query #10 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)  
→ Read `src/sql/07_healer_sessions.sql`

### I want to understand the RCT screening algorithm
→ Read [DEFENSE.md](DEFENSE.md) section "RCT Screening Logic (C2 Definition)"  
→ Read `src/rct.py:45-80`  
→ Run Queries #6–9 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)

### I want to understand why the pipeline is rerunnable
→ Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) "Argument 5: Pipeline Is Rerunnable"  
→ Read `src/__main__.py` (note: temporary directory + atomic os.replace)  
→ Read `src/changelog.py:45` (note: open mode "w" = truncate, not append)

---

## 💪 Confidence Builders

**Before jury, remember:**

1. ✅ **External validation:** Drop 0 answers marked CORRECT by Principal
2. ✅ **Systematic approach:** 10 categories of corruption, each detected and fixed with proof
3. ✅ **Conservative filtering:** Started 420 sorcerers → 3 candidates (not fishing)
4. ✅ **Deterministic:** Same output hash on reruns (not hand-tuned)
5. ✅ **Auditable:** 1.34 GB JSON log records every row change
6. ✅ **Defensible thresholds:** Based on data medians, not arbitrary
7. ✅ **Multiple evidence:** Each candidate has 4+ independent visits, all matching
8. ✅ **False positives filtered:** v2.3 excluded, external healers excluded, ID reuse flagged

You can defend every number. You have proof for every claim. You're ready. 🎯

---

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Pipeline fails to run | Check `initial_data/` has all required CSVs; run `python .\src --help` |
| SQL query times out | Use `LIMIT 1000` or run on `final.db` (smaller, clean only) |
| SQLite browser won't open files | Use SQLiteStudio (free) or VS Code SQLite extension |
| Can't remember query syntax | Copy from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) |
| Jury asks question I don't know | Say "Let me check the data" and use this reference guide to find the answer |

---

## 🏁 Final Words

You've built something rigorous, auditable, and defensible. The Principal's validation of Drop 0 answers proves you're not making this up. The 1.34 GB JSON log proves every transformation is tracked. The deterministic reruns prove it's not cherry-picked.

**Go defend your project. You've got this.** 🎯

---

**Last updated:** 2026-11-24  
**Questions?** Check [DEFENSE.md](DEFENSE.md) for detailed explanations, [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) for talking points, [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) for live demo queries.
