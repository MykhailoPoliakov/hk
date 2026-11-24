# 🎯 START HERE - Jujutsu High RCT Detection Complete Guide

**Welcome!** This project identifies sorcerers who can perform Reverse Cursed Technique (RCT) using data corrupted by "the Inverter" curse. This document helps you navigate all materials for learning and jury defense.

---

## ⏱️ Time-Based Guide

### I Have 5 Minutes
→ **Read:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- 60-second pitch
- 3 candidates + evidence
- Key facts to know
- Tough questions & answers

### I Have 15 Minutes
→ **Read:** [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)
- Five core arguments
- Evidence per candidate
- Presentation flow (8 slides)
- Confidence builders

### I Have 30 Minutes
→ **Read:** [VISUAL_SUMMARY.md](VISUAL_SUMMARY.md)
- Complete filtering funnel
- Each candidate's 4 visits (detailed)
- Excluded candidates & why
- Key metrics at a glance

### I Have 1 Hour
→ **Read:** [DEFENSE.md](DEFENSE.md)
- Full problem statement
- 10 corruption patterns (detailed explanations)
- RCT screening logic
- Drop 0 → Drop 1 progression
- Complete answers A1–D2

### I Have 2+ Hours
→ **Read:** Everything in order:
1. [INDEX.md](INDEX.md) — Project overview & learning path
2. [DEFENSE.md](DEFENSE.md) — Detailed technical explanations
3. [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — Talking points
4. [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) — Live demo queries
5. Source code: `src/rct.py:45-80` (RCT algorithm)

---

## 🎯 Goal-Based Guide

### I Need to Defend My Project to Jury
→ **Start here:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (print it!)
→ **Then read:** [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)
→ **Practice with:** [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)
→ **Backup reference:** [DEFENSE.md](DEFENSE.md)

### I Want to Understand the Data
→ **Start here:** [INDEX.md](INDEX.md) — "Learning Path"
→ **Then read:** [DEFENSE.md](DEFENSE.md) — "Data Quality Fixes"
→ **Then practice:** Run `python .\src` and examine `final.db`

### I Want to Understand the Algorithm
→ **Start here:** [DEFENSE.md](DEFENSE.md) — "RCT Screening Logic (C2)"
→ **Then read:** `src/rct.py:45-80`
→ **Then practice:** Run [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) queries #6–9

### I Want to Understand Why Results Are Correct
→ **Start here:** [VISUAL_SUMMARY.md](VISUAL_SUMMARY.md) — "Evidence Per Candidate"
→ **Then read:** [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — "Argument 2: Validation"
→ **Key fact:** Drop 0 D1 answers (4 IDs) marked CORRECT by Principal ✅

### I Want to Explain the Timestamp Correction
→ **Start here:** [DEFENSE.md](DEFENSE.md) — "4. Timestamp Chaos" section
→ **Then read:** [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) — "Argument 2: Drop 0 Validation"
→ **Then show:** Query #4 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)

### I Want to Live-Demo to Jury
→ **Prepare queries:** Copy all from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) into SQLite
→ **Prepare pipeline:** Verify `python .\src` works (5–10 min)
→ **Backup:** Have [DEFENSE.md](DEFENSE.md) open for quick facts

---

## 📚 Document Map

| Document | Purpose | Audience | Time | Use When |
|----------|---------|----------|------|----------|
| **[START_HERE.md](START_HERE.md)** | Navigation | Anyone | 5 min | You're lost and need direction |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Cheat sheet | Jury | 5 min | Jury day: print and carry |
| **[JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)** | Talking points | Jury | 15 min | Before jury: memorize & practice |
| **[VISUAL_SUMMARY.md](VISUAL_SUMMARY.md)** | Diagrams & charts | Jury | 20 min | For visual learners |
| **[SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)** | Demo queries | Jury | 10 min reference | Running live queries for jury |
| **[DEFENSE.md](DEFENSE.md)** | Deep dive | Learners | 30 min | Understanding every detail |
| **[INDEX.md](INDEX.md)** | Master guide | Learners | 20 min | Complete learning path |

---

## 📊 The Answer (Drop 1 Final)

**Question:** Which living sorcerers can perform RCT?

**Answer:** 
```
S-0009
S-0101
S-0533
```

**Evidence:** Each has 4 high-severity visits (<24h recovery, positive CE readings, no healer). Drop 0 answers were validated by Principal.

**Where to find:** [target/answers.txt](target/answers.txt) (full evidence-backed answers A1–D2)

---

## 🛠️ How to Run the Pipeline

```bash
# Navigate to project root
cd c:\Users\Michael\projects\hk

# Run the pipeline (takes 5–10 minutes)
python .\src

# Outputs:
# - data.db (raw tables + SQL views)
# - final.db (clean tables only)
# - target/answers.txt (all question answers)
# - target/chlogs.txt (1.34 GB JSON log of all changes)
```

**For jury:** You can run this live. Same output hash every time (deterministic).

---

## 🎓 Quick Learning Checklist

- [ ] Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (5 min)
- [ ] Read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) (15 min)
- [ ] Run pipeline: `python .\src` (10 min)
- [ ] Read [target/answers.txt](target/answers.txt) (5 min)
- [ ] Practice SQL queries from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) (10 min)
- [ ] Read [DEFENSE.md](DEFENSE.md) (30 min)
- [ ] Practice jury presentation (15 min with timer)

**Total: ~90 minutes to be fully prepared**

---

## ✅ Jury Defense Checklist

Before jury day, make sure you can:

- [ ] **60-second pitch:** Explain mission, approach, 3 candidates, validation
- [ ] **Data fixes:** Name 3+ corruption patterns and how you fixed them
- [ ] **Timestamp:** Explain UTC/JST correction and Principal validation
- [ ] **RCT definition:** Explain 5 criteria and why 24-hour threshold
- [ ] **v2.3 exclusion:** Explain firmware anomaly (99.80% positive)
- [ ] **Candidates:** Describe each candidate's 4 visits and evidence
- [ ] **Filtering:** Explain 420 → 3 progression (why conservative)
- [ ] **Validation:** Explain Drop 0 proof + determinism proof + audit trail
- [ ] **Live demo:** Run `python .\src` and show queries from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)
- [ ] **Tough questions:** Answer 5 hardest questions from [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)

---

## 🎯 Key Confidence Builders

| Fact | Why Important | Where to Find |
|------|--------------|---|
| Drop 0 answers marked CORRECT ✅ | External validation | [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) Argument 2 |
| Deterministic reruns (hash match) | Fully auditable, not cherry-picked | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) or run `python .\src` twice |
| 10 corruption categories documented | Systematic approach, not luck | [DEFENSE.md](DEFENSE.md) section B5 |
| 1.34 GB JSON audit trail | Every row change logged | `target/chlogs.txt` (first 100 lines) |
| 24-hour threshold data-driven | Not arbitrary | [DEFENSE.md](DEFENSE.md) C1 (severity medians) |
| v2.3 firmware 99.80% positive | Broken instrument, clearly excluded | Query #5 from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) |

---

## 🚨 Jury Questions You'll Likely Get

| Question | Quick Answer | Full Answer | Demo |
|----------|-------------|-------------|------|
| "How do you know your data is clean?" | "10 corruption patterns found & fixed with proof" | [DEFENSE.md](DEFENSE.md) B5 | Query #1–#4 |
| "Why trust the timestamp correction?" | "Drop 0 answers marked correct by Principal" | [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) Arg 2 | Show query #4 |
| "Only 3 candidates? Why so few?" | "Conservative filtering, 420 → 3" | [VISUAL_SUMMARY.md](VISUAL_SUMMARY.md) funnel | Query #7 |
| "How do you know it's not v2.3 noise?" | "v2.3 is 99.80% positive baseline (broken)" | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) or [DEFENSE.md](DEFENSE.md) B4 | Query #5 |
| "Can you rerun live?" | "Yes, `python .\src` (5–10 min)" | Run it live if asked | Terminal |

---

## 📞 "I'm Stuck" Quick Help

| Problem | Solution |
|---------|----------|
| "I don't understand the whole project" | Start with [INDEX.md](INDEX.md) learning path |
| "I need to present in 5 minutes" | Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (print it) |
| "I need to present in 15 minutes" | Use [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) + [VISUAL_SUMMARY.md](VISUAL_SUMMARY.md) |
| "I don't understand timestamp correction" | Read [DEFENSE.md](DEFENSE.md) section 4, then run Query #4 |
| "I don't understand RCT screening" | Read [DEFENSE.md](DEFENSE.md) C2, then read `src/rct.py:45-80` |
| "I can't explain why S-0663 was excluded" | Show Query #10 (healer filter) from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) |
| "I forgot the 3 candidates" | They're: **S-0009, S-0101, S-0533** (see [QUICK_REFERENCE.md](QUICK_REFERENCE.md)) |
| "I need to prove determinism" | Run pipeline twice, show hash match from [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) |

---

## 📋 Jury Day Timeline

| Time | Action |
|------|--------|
| **1 day before** | Print [QUICK_REFERENCE.md](QUICK_REFERENCE.md), read [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md) twice |
| **Morning of** | Re-read [QUICK_REFERENCE.md](QUICK_REFERENCE.md), practice 60-second pitch |
| **1 hour before** | Test all queries from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) |
| **At jury** | Open [QUICK_REFERENCE.md](QUICK_REFERENCE.md), have SQLite ready, have terminal ready |
| **If asked for proof** | Show queries from [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md) in order |
| **If asked for live demo** | Run `python .\src` (5–10 min) and show output |

---

## 💪 You've Got This

You've built:
✅ Rerunnable pipeline (proven deterministic)
✅ Systematic data cleaning (10 categories, each documented)
✅ Defensible screening rule (data-driven thresholds)
✅ Conservative filtering (420 → 3 candidates)
✅ Full audit trail (1.34 GB JSON log)
✅ External validation (Principal confirmed Drop 0 answers)

**That's not luck. That's rigor. Go defend it.** 🎯

---

## 📞 Document Cross-References

Need something specific? Here are all documents and their sections:

**[START_HERE.md](START_HERE.md)** ← You are here
**[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — 60-sec pitch, 3 candidates, key facts, tough questions
**[JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)** — 5 arguments, evidence, presentation flow, Q&A
**[VISUAL_SUMMARY.md](VISUAL_SUMMARY.md)** — Funnel diagram, candidate evidence, exclusion reasons, metrics
**[DEFENSE.md](DEFENSE.md)** — Problem statement, 10 data fixes, RCT logic, all question answers
**[SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)** — 12 queries copy/paste ready for live demo
**[INDEX.md](INDEX.md)** — Master guide, learning paths, project structure, checkpoint list

---

**What would you like to focus on next?**
- 📖 Learn everything → [INDEX.md](INDEX.md)
- 🎤 Prepare presentation → [JURY_TALKING_POINTS.md](JURY_TALKING_POINTS.md)
- 📊 Understand data → [DEFENSE.md](DEFENSE.md)
- 🔍 See visual overview → [VISUAL_SUMMARY.md](VISUAL_SUMMARY.md)
- ⚡ Quick facts → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- 💻 Run demo queries → [SQL_DEMO_QUERIES.md](SQL_DEMO_QUERIES.md)

---

**Last updated:** 2026-11-24 | **Status:** ✅ Drop 1 complete, 3 candidates identified | **Next:** Await Drop 2
