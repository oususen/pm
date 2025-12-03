-- expand_line_lt.sql  DAYステップへのLT展開（例）
UPDATE m_routing_step rs
JOIN m_routing r ON r.id=rs.routing_id
LEFT JOIN m_line_product_lt lpl ON lpl.line_id=rs.line_id AND lpl.product_id=r.product_id
LEFT JOIN m_line_default ld ON ld.line_id=rs.line_id
SET rs.lead_time_days = COALESCE(lpl.lt_days, ld.default_lt_days, rs.lead_time_days)
WHERE rs.time_unit='DAY';
