-- Gate criterion: share of requirements with at least one executed test in a run.
-- Parameter: :run_id

SELECT
    COUNT(DISTINCT r.id)                                   AS requirements_total,
    COUNT(DISTINCT t.requirement_id)                       AS requirements_covered,
    1.0 * COUNT(DISTINCT t.requirement_id) / COUNT(DISTINCT r.id) AS coverage
FROM requirements AS r
LEFT JOIN test_results AS t
    ON  t.requirement_id = r.id
    AND t.run_id = :run_id
    AND t.outcome IN ('pass', 'fail');
