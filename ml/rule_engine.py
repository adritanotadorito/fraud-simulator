def calculate_rule_score(transaction):
    score = 0
    if transaction["Amount"] > 500:
        score += 0.2

    if transaction["device_change_flag"] == 1:
        score += 0.25

    if transaction["geo_velocity"] > 0.8:
        score += 0.25

    if transaction["biometric_deviation"] > 0.8:
        score += 0.2

    if transaction["transaction_velocity"] > 0.5:
        score += 0.1

    return min(score, 1.0)