"""Symmetric Kitagawa decomposition: exact mix + within-rate identity."""

import pandas as pd


def decompose(before, after, numerator="purchase_sessions", denominator="sessions"):
    a = before.set_index("segment")[[numerator, denominator]]
    b = after.set_index("segment")[[numerator, denominator]]
    index = a.index.union(b.index)
    a, b = a.reindex(index, fill_value=0), b.reindex(index, fill_value=0)
    if a[denominator].sum() <= 0 or b[denominator].sum() <= 0:
        raise ValueError("Both periods need a positive denominator")
    wa, wb = a[denominator] / a[denominator].sum(), b[denominator] / b[denominator].sum()
    ra = a[numerator].div(a[denominator].replace(0, float("nan")))
    rb = b[numerator].div(b[denominator].replace(0, float("nan")))
    # Entering/exiting segment: carry the observed rate into the unobserved period.
    # This explicit convention attributes its contribution to composition.
    ra, rb = ra.fillna(rb).fillna(0), rb.fillna(ra).fillna(0)
    result = pd.DataFrame(
        {
            "segment": index,
            "mix_effect": ((wb - wa) * (ra + rb) / 2).values,
            "within_effect": ((rb - ra) * (wa + wb) / 2).values,
        }
    )
    delta = float((wb * rb).sum() - (wa * ra).sum())
    return dict(
        delta=delta,
        mix=float(result.mix_effect.sum()),
        within=float(result.within_effect.sum()),
        contributions=result.to_dict("records"),
    )


def investigate(rows, alerts):
    frame = pd.DataFrame(rows)
    frame["metric_date"] = pd.to_datetime(frame.metric_date)
    candidates = [a for a in alerts if a["metric"] in ["session_conversion", "revenue_usd"]]
    if not candidates:
        candidates = alerts
    if not candidates:
        return dict(status="No flags under the configured rule; no incident asserted.", cases=[])
    alert = max(candidates, key=lambda x: abs(x["score"]))
    day = pd.Timestamp(alert["date"])
    # Compare with four matched weekdays; rates use pooled denominators.
    matched = [day - pd.Timedelta(days=7 * i) for i in range(1, 5)]
    cases = []
    for dimension in frame.dimension.unique():
        subset = frame[frame.dimension == dimension]
        columns = ["sessions", "purchase_sessions", "viewed", "cart", "checkout", "purchased", "revenue_usd"]
        before = subset[subset.metric_date.isin(matched)].groupby("segment")[columns].sum().reset_index()
        after = subset[subset.metric_date == day].groupby("segment")[columns].sum().reset_index()
        if before.sessions.sum() and after.sessions.sum():
            result = dict(dimension=dimension, **decompose(before, after))
            result["funnel_transitions"] = []
            for numerator, denominator in [
                ("cart", "viewed"),
                ("checkout", "cart"),
                ("purchased", "checkout"),
            ]:
                if before[denominator].sum() and after[denominator].sum():
                    result["funnel_transitions"].append(
                        dict(
                            transition=f"{denominator} to {numerator}",
                            **decompose(before, after, numerator, denominator),
                        )
                    )
            result["session_revenue_rate"] = decompose(before, after, "revenue_usd", "sessions")
            # Exact two-factor symmetric identity for daily session-linked observed revenue.
            days = max(1, subset[subset.metric_date.isin(matched)].metric_date.nunique())
            n0, n1 = before.sessions.sum() / days, after.sessions.sum()
            r0 = before.revenue_usd.sum() / before.sessions.sum()
            r1 = after.revenue_usd.sum() / after.sessions.sum()
            result["daily_revenue"] = dict(
                delta=float(n1 * r1 - n0 * r0),
                volume_effect=float((n1 - n0) * (r0 + r1) / 2),
                revenue_per_session_effect=float((r1 - r0) * (n0 + n1) / 2),
                caveat="Session-linked observed USD only; missing USD and unlinked transactions limit interpretation.",
            )
            cases.append(result)
    return dict(
        status="Descriptive investigation; neither cause nor outage established.",
        trigger_metric=alert["metric"],
        date=alert["date"],
        baseline_dates=[d.date().isoformat() for d in matched],
        cases=cases,
    )
