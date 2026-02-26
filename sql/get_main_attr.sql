WITH target_series AS (
    SELECT id AS series_id
    FROM metric_series
    WHERE metric_id = :metric_id   -- подставьте нужный id
      AND is_active = true
)
SELECT
    at.code AS type_code,
    at.name AS type_name,
    av.code AS value_code,
    av.name AS value_name,
    COUNT(DISTINCT ts.series_id) AS series_count
FROM target_series ts
JOIN metric_series_attribute msa ON ts.series_id = msa.series_id
JOIN metric_attribute_type at ON msa.attribute_type_id = at.id AND at.is_active = true
JOIN metric_attribute_value av ON msa.attribute_value_id = av.id AND av.is_active = true
GROUP BY at.code, at.name, av.code, av.name
HAVING COUNT(DISTINCT ts.series_id) > 1
ORDER BY series_count DESC;