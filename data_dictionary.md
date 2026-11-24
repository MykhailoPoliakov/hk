# Jujutsu Records Office: data dictionary

Maintained by the Records Office. Last revised 20 November 2025.

## Drops

| Drop | Released | Files |
| --- | --- | --- |
| 0 | Start of challenge | sorcerers, wards, missions, infirmary_visits, device_assignments, ce_wearable, barrier_sensors |
| 1 | Announced on the day | healer_sessions |
| 2 | Announced on the day | infirmary_corrections, audit_log |

## sorcerers.csv
One row per sorcerer. `sorcerer_id` is unique and permanent: an ID is never reused.

| Column | Description |
| --- | --- |
| sorcerer_id | Permanent ID, format S-0000 |
| name | Full name |
| grade | Special, 1, 2, 3 or 4 (Special is the strongest, 4 the weakest) |
| school | Tokyo or Kyoto |
| technique | Innate technique |
| join_date | Date the sorcerer joined Jujutsu High |
| status | active or deceased |

## wards.csv
| Column | Description |
| --- | --- |
| ward_code | Code used by the barrier sensors |
| ward_name | Ward name (romaji) |
| city | Tokyo or Kyoto |

## missions.csv
| Column | Description |
| --- | --- |
| mission_id | Mission ID |
| start_ts, end_ts | Mission start and end (UTC) |
| ward | Ward name (romaji) |
| curse_grade | Estimated grade of the target curse |
| sorcerer_ids | Assigned sorcerers, separated by `\|` |
| outcome | exorcised, sealed, withdrawn or failed |
| casualties | Sorcerers killed in action, separated by `\|` |
| report_text | Free-text mission report |

## infirmary_visits.csv
Exported from the infirmary system (Japanese locale). All timestamps are Japan Standard Time (JST).

| Column | Description |
| --- | --- |
| visit_id | Visit ID |
| sorcerer_id | Patient |
| mission_id | Mission where the injury happened |
| admitted_at | Admission time (JST) |
| discharged_at | Discharge time (JST) |
| injury_code | Injury code (see the injury code reference at the infirmary) |
| severity | 1 = critical, 2 = severe, 3 = moderate, 4 = light, 5 = minor |
| admitted_from | Ward the patient came from |

## device_assignments.csv
Which cursed energy wearable each sorcerer carried, and when.

| Column | Description |
| --- | --- |
| device_id | Wearable ID |
| sorcerer_id | Wearer |
| valid_from, valid_to | Assignment period (UTC); empty `valid_to` = still assigned |

## ce_wearable.csv
Hourly cursed energy readings from each sorcerer's wearable.

| Column | Description |
| --- | --- |
| device_id | Wearable ID |
| ts | Reading time (UTC) |
| ce_level | Cursed energy level. Cursed energy is negative energy, so normal readings are negative. Positive readings mean positive energy, as produced by the Reverse Cursed Technique |
| firmware | Firmware version at the time of the reading |

## barrier_sensors.csv
| Column | Description |
| --- | --- |
| ward_code | Ward |
| ts | Reading time (UTC) |
| residual_ce | Residual cursed energy in the ward, in CE units |

## healer_sessions.csv (drop 1)
| Column | Description |
| --- | --- |
| session_id | Session ID |
| healer_id | Healer (a sorcerer ID) |
| patient_id | Patient (a sorcerer ID) |
| start_ts | Session start (UTC) |
| duration_min | Session length in minutes |

## infirmary_corrections.csv (drop 2)
Change feed from the infirmary system. Same columns as infirmary_visits, plus:

| Column | Description |
| --- | --- |
| seq | Order in which the changes happened |
| op | I = insert, U = update, D = delete |
| op_ts | Time of the change (UTC) |

## audit_log.csv (drop 2)
| Column | Description |
| --- | --- |
| audit_id | Audit ID |
| ts | Time of the action (UTC) |
| account | Account that performed the action |
| object | Table or system that was changed |
| record_id | Affected record, when applicable |
| action | Type of action |
| detail | Description |
