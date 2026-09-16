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
