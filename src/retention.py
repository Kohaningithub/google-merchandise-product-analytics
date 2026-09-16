from datetime import date, timedelta


def eligible(cohort, horizon, end=date(2021, 1, 31)):
    return cohort + timedelta(days=horizon) <= end


def summarize(rows, minimum=100):
    return [dict(row, publishable=row["eligible_users"] >= minimum) for row in rows]
