-- The v2.3 readings are anomalous; do not infer their correct sign.
DROP VIEW IF EXISTS reviewed_ce_wearable;
CREATE VIEW reviewed_ce_wearable AS
SELECT
    device_id,
    ts,
    ce_level,
    firmware,
    CASE WHEN firmware = 'v2.3' THEN 1 ELSE 0 END AS firmware_review_required
FROM ce_wearable;
