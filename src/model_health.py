"""Historical health replay with a fixed training reference; no live-source claims."""

from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .modeling import CATEGORICAL, NUMERIC, load_run, metrics, predict


def drift(reference, current):
    rows = []
    for column in NUMERIC:
        # Infinite end bins retain out-of-training-range values; smoothing avoids log(0).
        edges = np.unique(np.quantile(reference[column], np.linspace(0, 1, 11)))
        edges = np.r_[-np.inf, edges, np.inf]
        a = np.histogram(reference[column], bins=edges)[0].astype(float) + 0.5
        b = np.histogram(current[column], bins=edges)[0].astype(float) + 0.5
        a, b = a / a.sum(), b / b.sum()
        rows.append(
            dict(
                feature=column,
                statistic="psi",
                value=float(np.sum((b - a) * np.log(b / a))),
                unseen_rate=None,
            )
        )
    for column in CATEGORICAL:
        a = reference[column].value_counts(normalize=True)
        b = current[column].value_counts(normalize=True)
        index = a.index.union(b.index)
        rows.append(
            dict(
                feature=column,
                statistic="total_variation",
                value=float(
                    (a.reindex(index, fill_value=0) - b.reindex(index, fill_value=0)).abs().sum() / 2
                ),
                unseen_rate=float((~current[column].isin(a.index)).mean()),
            )
        )
    return rows


@threadpool_limits.wrap(limits=2)
def health(feature_path, output):
    output = Path(output)
    bundle, parts = load_run(feature_path, output)
    test = parts["test"].copy()
    test["prediction"] = predict(bundle, bundle["selected"], test)
    test["week"] = pd.to_datetime(test.session_date).dt.to_period("W-SUN").astype(str)
    rows, shifts = [], []
    for week, group in test.groupby("week", sort=True):
        end = group.session_date.max()
        rows.append(
            dict(
                run_date=end,
                model_version=bundle["version"],
                model=bundle["selected"],
                evaluation_window=week,
                window_start=group.session_date.min(),
                window_end=end,
                **metrics(group.target, group.prediction, minimum=200),
            )
        )
        shifts.extend(
            dict(evaluation_window=week, model_version=bundle["version"], **r)
            for r in drift(parts["train"], group)
        )
    pd.DataFrame(rows).to_csv(output / "model_health.csv", index=False)
    pd.DataFrame(shifts).to_csv(output / "model_drift.csv", index=False)
