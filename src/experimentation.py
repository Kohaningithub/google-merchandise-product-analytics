"""Prospective design only; no assigned treatments or outcomes in GA4."""

import math

from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


def power_plan(successes, users, daily_users, relative_mde=0.10):
    if users <= 0 or daily_users <= 0:
        return dict(status="Insufficient eligible traffic")
    p0 = successes / users
    p1 = p0 * (1 + relative_mde)
    if not 0 < p0 < p1 < 1:
        return dict(status="Baseline does not support this relative MDE")
    effect = abs(proportion_effectsize(p0, p1))
    scenarios = []
    for power in [0.8, 0.9]:
        n = math.ceil(
            NormalIndPower().solve_power(
                effect_size=effect, power=power, alpha=0.05, ratio=1, alternative="two-sided"
            )
        )
        days = max(14, math.ceil((2 * n / daily_users) / 7) * 7)
        scenarios.append(dict(power=power, per_arm=n, total=2 * n, duration_days=days))
    return dict(
        status="Prospective design; no experiment was run",
        baseline=p0,
        eligible_users=users,
        daily_eligible_users=daily_users,
        relative_mde=relative_mde,
        absolute_mde=p1 - p0,
        alpha=0.05,
        allocation="50/50",
        scenarios=scenarios,
    )
