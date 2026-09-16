import pandas as pd
from statsmodels.stats.proportion import proportion_confint


def interval(successes, trials):
    if trials <= 0:
        return [None, None]
    return list(map(float, proportion_confint(successes, trials, method="wilson")))


def segments(rows, minimum=100):
    frame = pd.DataFrame(rows)
    totals = (
        frame.groupby(["dimension", "segment"])[
            ["sessions", "purchase_sessions", "viewed", "cart", "checkout", "purchased"]
        ]
        .sum()
        .reset_index()
    )
    out = []
    for row in totals.to_dict("records"):
        row["eligible_for_comparison"] = row["checkout"] >= minimum
        row["checkout_completion"] = row["purchased"] / row["checkout"] if row["checkout"] else None
        row["interval"] = interval(row["purchased"], row["checkout"])
        out.append(row)
    return out
