SELECT setval('metric_info_id_seq', COALESCE((SELECT MAX(id) FROM metric_info), 0) + 1, false);
SELECT setval('metric_data_id_seq', COALESCE((SELECT MAX(id) FROM metric_data), 0) + 1, false);
SELECT setval('metric_period_id_seq', COALESCE((SELECT MAX(id) FROM metric_period), 0) + 1, false);
SELECT setval('metric_series_id_seq', COALESCE((SELECT MAX(id) FROM metric_series), 0) + 1, false);
SELECT setval('metric_series_attribute_id_seq', COALESCE((SELECT MAX(id) FROM metric_series_attribute), 0) + 1, false);
SELECT setval('metriс_attribute_type_id_seq', COALESCE((SELECT MAX(id) FROM metriс_attribute_type), 0) + 1, false);
SELECT setval('metriс_attribute_value_id_seq', COALESCE((SELECT MAX(id) FROM metriс_attribute_value), 0) + 1, false);