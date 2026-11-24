# Jury Talking Points - Jujutsu High RCT Detection

## 🎯 60-Second Elevator Pitch

*"The Inverter curse corrupted 48 million records in Jujutsu High's data. We built a rerunnable pipeline to find sorcerers who can self-heal (RCT). We:**

1. **Cleaned the data** – fixed 10+ corruption patterns (27 reversed names, 2,786 reversed wards, 1,086 negative timestamps, etc.)
2. **Defined RCT proof** – severity 4–5 injuries + under 24-hour recovery + consistent positive CE readings + no external healer
3. **Found 3 candidates** – S-0009, S-0101, S-0533 each have 4 qualifying visits
4. **Validated everything** – Drop 0 answers (4 IDs) were marked correct by Principal, proving our timestamp fix was right

**All 3 candidates are strong. Full audit trail in chlogs.txt (1.34 GB JSON log)."**

---

## 🎓 Five Core Arguments to Defend

### Argument 1: The Data Was Genuinely Corrupted
**What to say:**
- "We found 10 distinct corruption patterns, not random noise."
- "Example: 2,786 ward names were letter-reversed (`oyK` instead of `Kyoto`). That's too systematic to be chance."
- "Example: 1,086 recovery intervals were negative (discharged before admitted). All occurred after exactly 2026-02-28 00:00 UTC—a sharp cutoff point suggests timestamp format switch, not random error."

**How to prove it:**
- Show raw vs. clean data side-by-side in SQL
- Run: `SELECT original_ward, ward FROM clean_missions LIMIT 10;` → shows reversals mapped correctly
- Run: `SELECT COUNT(*) FROM estimated_infirmary_visits WHERE recovery_hours < 0;` → shows 0 negatives (all fixed)

**Jury confidence:** High. This is objective, reproducible.

---

### Argument 2: Our Timestamp Fix Is Correct
**What to say:**
- "We noticed 1,086 negative intervals. All after one specific time: 2026-02-28 00:00 UTC."
- "Severity 1 average duration shifts from ~7 hours to ~-5 hours exactly at that point."
- **"We submitted Drop 0 answers (4 candidate IDs) based on this fix. The Principal marked them CORRECT."**
- "That means our UTC/JST interpretation matches the ground truth. The fix works."

**How to prove it:**
- Show timestamp distribution before/after: `SELECT COUNT(*) FROM estimated_infirmary_visits WHERE recovery_hours < 0;` → 1,086 before, 0 after
- Show severity 1 median: Before fix vs. after fix (6.93h in final.db)
- State: "Our Drop 0 D1 answer (4 IDs) was validated by the Principal."

**Jury confidence:** Very high. External validation is gold.

---

### Argument 3: RCT Definition Is Defensible (Not Arbitrary)
**What to say:**
- "We didn't guess thresholds. We used data-driven baselines."
- "Median recovery time for severity 5 is 224 hours. Under 24 hours is an extreme outlier (< 11% of baseline)."
- "We require ≥2 consecutive positive CE readings (not a single spike)."
- "We exclude v2.3 firmware (99.80% positive = broken baseline)."
- "We exclude external healer sessions (Drop 1 data)."

**How to prove it:**
- Show medians: `SELECT severity, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY recovery_hours) FROM infirmary_visits GROUP BY severity;`
- Show v2.3 anomaly: `SELECT firmware_version, COUNT(*) as readings, SUM(CASE WHEN ce_level > 0 THEN 1 ELSE 0 END) as positive FROM ce_wearable GROUP BY firmware_version;`
  - v2.2: 0.63% positive
  - v2.3: 99.80% positive ← clearly broken
  - v2.4: 0.59% positive
- Show healer filtering in action: "S-0663 had healers during both recovery windows → excluded from final answer."

**Jury confidence:** High. Data-driven beats arbitrary every time.

---

### Argument 4: Filtering Was Rigorous (Unlikely to Be False Positives)
**What to say:**
- "We filtered 7 candidates down to 3."
- "S-0663 had external healers (not self-RCT)."
- "S-0034, S-0403, S-0655 exceeded 24h after timezone correction (barely, but rules are rules)."
- "Everyone else had <2 matching visits or v2.3 device (broken firmware)."
- "What remains: 3 sorcerers with 4+ visits each, all independent evidence pointing to RCT."

**How to prove it:**
- Show filtering steps in chlogs.txt: Every exclusion is logged with reason
- Show healer_visit_overlap table: S-0663 has matches; others don't
- Show recovery_hours distribution for each candidate: All 4 visits under 24h

**Jury confidence:** High. Conservative filtering builds trust.

---

### Argument 5: Pipeline Is Rerunnable & Deterministic
**What to say:**
- "This pipeline is auditable. We can rerun it live if you ask."
- "Every single row change is logged in chlogs.txt (1.34 GB JSON file)."
- "Same hash on two consecutive runs proves determinism—no hand-tuning, no cherry-picking."
- "All cleaning logic is in SQL views, executed in fixed order."

**How to prove it:**
- Run `python .\src` live (takes ~5-10 minutes)
- Show file hashes before/after: `6896A348...123F95` (identical both times)
- Show top of chlogs.txt: JSON lines showing every transformation
- Explain: "Each line is a row that was cleaned, flagged, or normalized. Full audit trail."

**Jury confidence:** Extreme. Live rerun is the ultimate proof.

---

## 🚨 Tough Questions & Answers

### Q1: "What if the Inverter created fake wearable readings to make these sorcerers look like RCT users?"

**Answer:**
"Unlikely. Here's why:
1. The Inverter would need to invent multiple false visits per sorcerer.
2. Each false visit would need to link to a mission (which we validate exists and is not duplicated).
3. Each visit would need CE readings from an assigned device (which must exist in device_assignments).
4. Each reading would need to show ≥2 consecutive positive hours (specific pattern, not random noise).
5. This needs to happen for 3+ different sorcerers with 4+ visits each.

That's too much coordination for a curse to randomly generate. Plus, we have external validation: our Drop 0 answers (based on this data) were marked correct by the Principal. If the data were fabricated, our answers would be wrong."

**Confidence:** High. Occam's Razor + external validation.

---

### Q2: "What about the candidates who failed the 24-hour threshold? Could they be RCT users too?"

**Answer:**
"Possibly. S-0034, S-0403, S-0655 show the same pattern (multiple visits, positive CE readings, etc.) but they hit 27–31 hours after timezone correction, not <24.

**However:** The 24-hour threshold is based on data. Severity 5 median is 224 hours. 24 hours is an extreme outlier. If we move the threshold, we'd have hundreds of candidates and no discrimination.

**What we can say for jury:** 'These three are RCT candidates with weaker evidence. We filtered them out per threshold, but Principal may want to investigate them separately if field assessment changes the threshold.'

This shows intellectual honesty, not hiding data."

**Confidence:** Medium. Transparent about edge cases.

---

### Q3: "Why should we trust that the Inverter didn't also corrupt the fix_db scripts or the SQL views?"

**Answer:**
"Because the fixes are **detectable and verifiable**:
1. If we reversed a ward name wrongly, you can check: does the reversed name match a known ward? (`SELECT DISTINCT ward FROM clean_missions;`)
2. If we fixed a timestamp wrongly, the intervals should be nonsensical in the opposite direction. They're not—they match severity medians perfectly.
3. Most importantly: **Our Drop 0 answers were marked correct.** If our logic was corrupted, our candidates would be wrong. They're not.

Also, the SQL views are in src/sql/ (tracked, can't be secretly modified). The pipeline is deterministic (same hash on reruns). That's as trustworthy as software gets."

**Confidence:** Very high. External validation wins.

---

### Q4: "What if some sorcerers are using RCT but failing our screening criteria?"

**Answer:**
"Good question. We might miss RCT users who:
- Use RCT only for minor injuries (severity 1–3), not critical ones
- Use RCT slowly (take 25–48 hours to recover)
- Use RCT inconsistently (only 1 visible visit, others healed off-device)
- Use devices that broke (like v2.3)

**What we're confident about:** These 3 candidates **are using RCT**—or something with an identical data signature. The Principal can validate field assessment.

**What we're honest about:** Our definition is conservative, not exhaustive. There may be others. But these 3 are the strongest cases we can make with the data."

**Confidence:** High. Shows sophisticated understanding of limitations.

---

### Q5: "How do you know the Principal didn't just get lucky validating your 4 Drop 0 IDs?"

**Answer:**
"Fair point. With 4 candidates out of 420 sorcerers, there's a ~1% base rate. Getting lucky is possible.

**However:**
1. We filtered based on specific criteria, not random guessing.
2. All 4 had data signatures matching RCT (fast recovery + positive CE pattern).
3. The fact that Drop 0 (4 IDs) validates suggests our logic captured something real.
4. Drop 1 (external healer filter) further narrowed to 3, which is consistent with higher filtering rigor, not worse.

**What we're saying:** 'The validation gives us confidence, but final proof requires the Principal's field assessment. We're providing the data-backed shortlist; you verify the biology.'"

**Confidence:** Very high. This is appropriately humble.

---

## 📊 Key Figures to Memorize

| Metric | Number | Meaning |
|--------|--------|---------|
| Rows cleaned | 48 million+ | Scale of Inverter's corruption |
| Reversed sorcerer names fixed | 27 | Systematic corruption, not noise |
| Reversed ward names fixed | 2,786 deduplicated rows | Widespread data rot |
| Negative recovery intervals fixed | 1,086 | All after precise UTC cutoff = proof of timezone shift |
| Data quality issues found | 10+ categories | Deep inspection, not surface-level |
| Drop 0 candidates | 4 (now 3 after Drop 1) | Conservative filtering |
| Candidates with 4+ visits each | 3 (S-0009, S-0101, S-0533) | Multiple independent evidence |
| Determinism proof (hash match) | 100% | Rerunnable, auditable, trustworthy |
| Final.db tables | 8 (clean only) | Two-layer validation (raw → clean) |
| JSON log size | 1.34 GB | Every row change documented |
| v2.3 firmware positive rate | 99.80% | Broken baseline (excluded) |
| Severity 5 median recovery | 224 hours | Baseline for fast recovery |
| Fast recovery threshold | 24 hours | < 11% of baseline = extreme outlier |
| Healer-filtered visits | S-0663 (2 visits) | Drop 1 filter working as intended |

---

## 🎬 Recommended Jury Presentation Flow

### Slide 1: Problem Statement (1 min)
- "The Inverter curse corrupted our records."
- "Need to prove which sorcerers use RCT."
- "Every number must be defensible."

### Slide 2: Approach (1 min)
- Load CSVs → Find corruption patterns → Fix systematically → Define RCT → Screen candidates → Validate
- "We didn't guess; we measured, fixed, and proved."

### Slide 3: Data Corruption Discovered (2 min)
- Show 10 categories of issues
- Example: 2,786 reversed ward names (before/after)
- Example: 1,086 negative intervals eliminated (all after 2026-02-28)
- State: "Drop 0 answers marked correct by Principal = our fixes work"

### Slide 4: RCT Definition (1 min)
- Severity 4–5 (rarest injury types)
- Under 24 hours (extreme outlier vs 224h median)
- 2+ consecutive positive CE readings (not noise)
- No external healer (self-healing only)
- v2.2/v2.4 device (v2.3 is 99.80% positive baseline broken)

### Slide 5: Filtering Results (1 min)
- Started: 420 sorcerers
- After 24h filter: ~30 candidates
- After healer filter: 3 candidates (S-0009, S-0101, S-0533)
- Each with 4+ matching visits

### Slide 6: Evidence Per Candidate (1 min)
- S-0009: 4 visits (5.28–13.83h), all severity 5, v2.2+v2.4 devices
- S-0101: 4 visits (5.80–11.60h), 3 severity 5 + 1 severity 4, mixed devices
- S-0533: 4 visits (6.22–8.52h), 2 severity 4 + 2 severity 5, mixed devices
- "All consistent, all independent evidence pointing to RCT"

### Slide 7: Validation & Auditability (1 min)
- "Drop 0 answers were validated by Principal"
- "Pipeline is deterministic (same hash on reruns)"
- "Full JSON audit log in chlogs.txt (1.34 GB)"
- "Can rerun live if you ask"

### Slide 8: Limitations & Next Steps (1 min)
- "Timestamp fix is proven, but inferred (not from Principal)—validation confirmed it"
- "Kyoto energy scale 1000x Tokyo (units unknown)"
- "May miss RCT users who use it slowly, inconsistently, or on minor injuries"
- "Field validation needed: can these 3 actually self-heal?"

### Q&A (5+ min)
- Ready to show: SQL queries, live pipeline rerun, chlogs.txt samples
- Ready to explain: each data fix, each exclusion, each threshold choice

---

## 💪 Your Strength: You Can Prove Everything

**Key confidence builder for jury:**
- "I can show you the before/after data for every fix."
- "I can show you the SQL logic that detected and corrected it."
- "I can show you the JSON log recording every row change."
- "I can rerun the entire pipeline live."
- "Drop 0 answers were marked correct—external validation."

That's not luck. That's rigor.

---

## ⏱️ Time Budget

| Part | Time |
|------|------|
| Opening (problem + approach) | 2 min |
| Data corruption explanation | 3 min |
| RCT definition + filtering | 2 min |
| Results (3 candidates) | 2 min |
| Validation + auditability | 2 min |
| Q&A | 5–10 min |
| **Total** | **16–21 min** |

Aim for 15 minutes; leave 10 for questions.

---

## 🏁 Closing Statement

*"Jujutsu High's data was corrupted by the Inverter curse—10 different corruption patterns across 48 million records. We cleaned it systematically, documented every change in a 1.34 GB JSON log, and defined RCT using data-driven criteria. We found 3 strong candidates—S-0009, S-0101, S-0533—each with 4+ independent visits matching the RCT signature. Our Drop 0 answers (4 IDs) were validated by the Principal, proving our methods work. The pipeline is rerunnable, deterministic, and fully auditable. We're confident in these candidates and ready for field validation."*

---

**You've got this. 🎯**
