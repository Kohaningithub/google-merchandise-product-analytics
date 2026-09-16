"""Past-only robust surveillance; flags are investigation prompts, not incidents."""

import numpy as np
import pandas as pd

MONITORS = ["users", "sessions", "session_conversion", "transactions", "revenue_usd", "checkout_completion"]


def detect(rows, window=28, minimum=21, threshold=3.5):
    frame = pd.DataFrame(rows).sort_values("metric_date").reset_index(drop=True)
    alerts = []
    for metric in MONITORS:
        values = pd.to_numeric(frame[metric], errors="coerce")
        if metric == "revenue_usd" and "missing_revenue_transactions" in frame:
            values = values.mask(frame.missing_revenue_transactions > 0)
        denominator = {
            "session_conversion": "sessions",
            "checkout_completion": "ordered_checkout_sessions",
        }.get(metric)
        if denominator:
            values = values.mask(frame[denominator] < 100)
        for i, value in enumerate(values):
            history = values.iloc[max(0, i - window) : i].dropna()
            if len(history) < minimum or not np.isfinite(value):
                continue
            median = float(history.median())
            mad = float((history - median).abs().median())
            if mad == 0:
                # Constant histories need a separate rule; no division by zero / invented score.
                continue
            score = (value - median) / (1.4826 * mad)
            if abs(score) >= threshold:
                alerts.append(
                    dict(
                        date=str(frame.iloc[i]["metric_date"]),
                        metric=metric,
                        observed=float(value),
                        baseline=median,
                        score=float(score),
                        window=window,
                    )
                )
    return alerts
