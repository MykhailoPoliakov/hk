# Jury defense

Start with the [README](../README.md) and generated [answers](../target/answers.txt).

## Data lineage

The original CSV rows are preserved in `data.db`. Drop 2's ordered change
feed is replayed onto an effective visit snapshot; `correction_history` and
the JSON Lines log preserve each before/after change. From 7,825 original
visits, 322 insert and 22 delete events yield 8,125 effective visits; 900
update events change values but not the row count. The feed contains two
insert-then-delete visits, which makes sequencing essential.

Mission deduplication removes 715 exact duplicates; 2,786 mission ward
spellings are repaired against the ward reference. The 27 suspected reversed
names are changed only when both name components exist in the roster. See
`target\chlogs.txt` and the SQL views for individual records.

## Main answer

Drop 2's provisional D1 shortlist is **S-0009, S-0101, S-0533**. Each has
four qualifying visits. Each visit is mission-linked, has recorded severity
4 or 5, an estimated stay under 24 hours, at least two consecutive positive
hourly readings from an attributed v2.2/v2.4 device, and no recorded
overlapping healer session. The roster marks all three active.

The user reports that the earlier four-ID Drop 0 and three-ID Drop 1
submissions were marked correct. S-0663's two qualifying visits overlap
healer sessions HS-01200 and HS-01518. This explains those episodes but does
not, by itself, prove S-0663 lacks the ability.

## Bonus: host

**S-0033, Itsuki Minase**, is the strongest host candidate. The account
`hlr.minase.i` matches the roster name and its medical-support role; S-0033
appears as a healer in 690 sessions. That account pushed v2.3 to 40 devices,
edited the severity description (A-019523), changed the discharge terminal
clock source (A-028981), and reassigned eight IDs (e.g. A-020538). These
events align with observed data anomalies. The log does not independently
prove account ownership, intent or the contents of the old configuration.

## What not to overclaim

The discharge-time cutoff and timezone are inferred, not proven by a correct
submission or by the clock-change entry. The 24-hour threshold is a screening
choice, and a high v2.3 positive rate demonstrates an anomaly, not its exact
cause. The severity dictionary edit does not show the old scale. Recovery
medians must include healer-assisted stays; RCT screening excludes those stays.
External healer records can be incomplete. The records alone do not rule out
fabricated values or prove a negative RCT capability.

The notebook, Looker Studio report and public dashboard link remain separate
deliverables. See [task3](../tasks/task3.txt).
