from analytics.tonnage import get_current_and_previous_strength_windows
from analytics.exposure import get_current_balance_snapshot, get_current_exposure_snapshot


def analyze_training_signals(days: int = 7) -> list:
    strength = get_current_and_previous_strength_windows(days)
    balance = get_current_balance_snapshot(days)
    exposure = get_current_exposure_snapshot(days)

    signals = []

    current_tonnage = strength.get("current_total_tonnage", 0.0)
    previous_tonnage = strength.get("previous_total_tonnage", 0.0)

    if previous_tonnage > 0:
        change_pct = ((current_tonnage - previous_tonnage) / previous_tonnage) * 100.0
        if change_pct > 30:
            signals.append({
                "name": "workload_spike",
                "severity": "warning",
                "message": f"Total workload increased by {change_pct:.1f}%.",
                "details": {
                    "current_total_tonnage": round(current_tonnage, 1),
                    "previous_total_tonnage": round(previous_tonnage, 1),
                    "change_pct": round(change_pct, 1),
                },
            })
    else:
        signals.append({
            "name": "no_prior_workload_window",
            "severity": "warning",
            "message": "No prior workload window available for comparison.",
            "details": {},
        })

    push_sets = balance.get("push_sets", 0)
    pull_sets = balance.get("pull_sets", 0)

    if pull_sets > 0:
        ratio = push_sets / pull_sets
        if ratio > 2.0:
            signals.append({
                "name": "push_pull_imbalance",
                "severity": "warning",
                "message": f"Push volume exceeds pull volume by {ratio:.2f}x.",
                "details": {"push_sets": push_sets, "pull_sets": pull_sets, "ratio": round(ratio, 2)},
            })
    elif push_sets > 0:
        signals.append({
            "name": "push_pull_imbalance",
            "severity": "warning",
            "message": "Push volume is present but no pulling volume was recorded.",
            "details": {"push_sets": push_sets, "pull_sets": pull_sets},
        })

    extension_score = exposure.get("elbow_extension_score", 0)
    flexion_pull_score = exposure.get("elbow_flexion_pull_score", 0)

    if extension_score >= 8:
        if flexion_pull_score > 0 and (extension_score / flexion_pull_score) > 2.0:
            signals.append({
                "name": "elbow_extension_overload",
                "severity": "warning",
                "message": "Elbow extension stress is elevated relative to pulling/flexion work.",
                "details": {"extension_score": extension_score, "flexion_pull_score": flexion_pull_score},
            })
        elif flexion_pull_score == 0:
            signals.append({
                "name": "elbow_extension_overload",
                "severity": "warning",
                "message": "Elbow extension stress is elevated with little or no balancing pull/flexion work.",
                "details": {"extension_score": extension_score, "flexion_pull_score": 0},
            })

    forearm_total = exposure.get("forearm_total_score", 0)
    forearm_max_day = exposure.get("forearm_max_day_score", 0)

    if forearm_total >= 8 and forearm_total > 0:
        cluster_ratio = forearm_max_day / forearm_total
        if cluster_ratio >= 0.6:
            signals.append({
                "name": "forearm_density",
                "severity": "warning",
                "message": "Forearm exposure is highly concentrated.",
                "details": {
                    "forearm_total_score": forearm_total,
                    "forearm_max_day_score": forearm_max_day,
                    "cluster_ratio": round(cluster_ratio, 2),
                },
            })

    return signals[:5]


def generate_signal_recommendations(signals: list) -> list:
    recommendations = []
    names = {s["name"] for s in signals}

    if "workload_spike" in names:
        recommendations.append("Consider holding or slightly reducing total workload next week.")
    if "push_pull_imbalance" in names:
        recommendations.append("Add more rowing, rear-delt, or other pulling volume to improve balance.")
    if "elbow_extension_overload" in names:
        recommendations.append("Reduce triceps isolation or pressing accessories if elbow irritation rises.")
    if "forearm_density" in names:
        recommendations.append("Spread grip and forearm work across more sessions to improve recovery.")
    if "no_prior_workload_window" in names and not recommendations:
        recommendations.append("Log another full week so workload comparison can begin.")
    if not recommendations:
        recommendations.append("No major fatigue or balance flags detected in this window.")

    return recommendations[:5]


def show_fatigue_analysis(days: int = 7) -> None:
    strength = get_current_and_previous_strength_windows(days)
    signals = analyze_training_signals(days)
    recommendations = generate_signal_recommendations(signals)

    print("\n+++ FATIGUE ANALYSIS +++")
    start_date = strength.get("current_start")
    end_date = strength.get("current_end")
    if start_date and end_date:
        print(f"Window: {start_date} to {end_date}")

    print("\nSignals:")
    if signals:
        for s in signals:
            print(f"- {s['severity'].capitalize()}: {s['message']}")
    else:
        print("- No major warning signals detected.")

    print("\nRecommendations:")
    for rec in recommendations:
        print(f"- {rec}")
    print()