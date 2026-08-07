def calculate_final_risk(
    xgb_score,
    isolation_score,
    rule_score,
    threat_score=0
):

    return (
        0.55 * xgb_score +
        0.20 * isolation_score +
        0.15 * rule_score +
        0.10 * threat_score
    )