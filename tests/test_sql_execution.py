"""Execute canonical session SQL on synthetic edge cases via DuckDB translation.

This verifies relational logic, not BigQuery compatibility or real source results.
ARRAY_AGG LIMIT 1 is removed for DuckDB; the subsequent [first] keeps its semantics.
"""

import duckdb
import sqlglot

from src.extract import render


def test_actual_session_sql_handles_order_ties_repeats_and_missing_keys():
    db = duckdb.connect()
    db.execute("""CREATE TABLE stg_events (
      session_id VARCHAR, user_pseudo_id VARCHAR, event_timestamp BIGINT,
      event_date DATE, device VARCHAR, country VARCHAR, source VARCHAR, medium VARCHAR,
      ga_session_number BIGINT, event_fingerprint VARCHAR, event_name VARCHAR)""")
    events = [
        ("ordered", 1, "view_item"),
        ("ordered", 2, "add_to_cart"),
        ("ordered", 3, "begin_checkout"),
        ("ordered", 4, "purchase"),
        ("repeated", 1, "add_to_cart"),
        ("repeated", 2, "view_item"),
        ("repeated", 3, "add_to_cart"),
        ("repeated", 4, "begin_checkout"),
        ("repeated", 5, "purchase"),
        ("tied", 1, "view_item"),
        ("tied", 1, "add_to_cart"),
        ("tied", 2, "begin_checkout"),
        ("tied", 3, "purchase"),
        (None, 1, "purchase"),
    ]
    for session, ts, name in events:
        db.execute(
            "INSERT INTO stg_events VALUES (?, 'u', ?, DATE '2020-11-01', 'mobile', 'US', 'google', 'organic', 1, ?, ?)",
            [session, ts, name, name],
        )
    db.execute("CREATE TABLE fct_purchases(session_id VARCHAR, revenue_usd DOUBLE)")
    db.execute("INSERT INTO fct_purchases VALUES ('ordered',10), ('repeated',NULL)")
    sql = render("int_sessions", "p", "d").replace("`p.d.", "`").replace(" LIMIT 1", "")
    sql = sqlglot.transpile(sql, read="bigquery", write="duckdb")[0]
    records = db.execute(sql).fetchdf().set_index("session_id")
    assert len(records) == 3
    assert records.loc["ordered", "purchase_ts"] == 4
    assert records.loc["repeated", "cart_ts"] == 3
    assert records.loc["repeated", "purchase_ts"] == 5
    assert records.loc["tied", "purchase_event"]
    import pandas as pd

    assert pd.isna(records.loc["tied", "cart_ts"])
    assert pd.isna(records.loc["tied", "purchase_ts"])
    assert records.loc["repeated", "missing_revenue_transactions"] == 1
    assert records.events.sum() == len(events) - 1


def test_purchase_sql_quarantines_conflicts_and_deduplicates_consistent_ids():
    db = duckdb.connect()
    db.execute("""CREATE TABLE stg_events (
      transaction_id VARCHAR,event_date DATE,event_timestamp BIGINT,user_pseudo_id VARCHAR,
      session_id VARCHAR,revenue_usd DOUBLE,currency VARCHAR,items VARCHAR,
      event_fingerprint VARCHAR,event_name VARCHAR)""")
    rows = [
        ("clean", "u1", 10, 1),
        ("clean", "u1", 10, 2),
        ("owner_conflict", "u1", 20, 3),
        ("owner_conflict", "u2", 20, 4),
        ("value_conflict", "u1", 20, 5),
        ("value_conflict", "u1", 30, 6),
        ("<Other>", "u1", 40, 7),
        (None, "u1", 50, 8),
    ]
    for transaction, user, revenue, ts in rows:
        db.execute(
            "INSERT INTO stg_events VALUES (?, DATE '2020-11-01', ?, ?, 'session', ?, 'USD', '[]', ?, 'purchase')",
            [transaction, ts, user, revenue, str(ts)],
        )
    sql = render("fct_purchases", "p", "d").replace("`p.d.", "`")
    result = db.execute(sqlglot.transpile(sql, read="bigquery", write="duckdb")[0]).fetchdf()
    assert result.transaction_id.tolist() == ["clean"]
    assert result.revenue_usd.tolist() == [10]
    assert result.event_timestamp.tolist() == [1]
