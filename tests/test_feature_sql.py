"""Execute first-view SQL: future events cannot change prediction-time features."""

import duckdb
import sqlglot

from src.extract import render


def test_future_events_ties_and_purchase_exclusions():
    db = duckdb.connect()
    db.execute("""CREATE TABLE stg_events(
      session_id VARCHAR,event_timestamp BIGINT,event_date DATE,event_name VARCHAR,
      device VARCHAR,country VARCHAR,source VARCHAR,medium VARCHAR,ga_session_number BIGINT,
      event_fingerprint VARCHAR, items STRUCT(item_id VARCHAR,item_category VARCHAR)[])""")

    def event(session, seconds, name, day="2021-01-15"):
        db.execute(
            """INSERT INTO stg_events VALUES (?,1600000000000000+?*1000000,?,?,'mobile','US',
                    'google','organic',1,?,[{'item_id':'item','item_category':'category'}])""",
            [session, seconds, day, name, name],
        )

    for session in ["good", "before", "tie", "cross_day", "boundary"]:
        day = "2021-01-31" if session == "boundary" else "2021-01-15"
        event(session, 0, "session_start", day)
        event(session, 5, "page_view", day)
        event(session, 10, "view_item", day)
    event("before", 9, "purchase")
    event("tie", 10, "purchase")
    event("cross_day", 30, "page_view", "2021-01-16")
    # Ambiguous tied non-view events do not count.
    event("good", 10, "search")
    sql = render("mart_conversion_features", "p", "d").replace("`p.d.", "`").replace(" LIMIT 1", "")
    translated = sqlglot.transpile(sql, read="bigquery", write="duckdb")[0]
    before = db.execute(translated).fetchdf()
    assert len(before) == 1
    assert before.iloc[0].early_events == 3
    assert before.iloc[0].early_searches == 0
    assert before.iloc[0].target == 0
    event("good", 11, "view_item")
    event("good", 15, "search")
    event("good", 20, "purchase")
    after = db.execute(translated).fetchdf()
    assert after.iloc[0].target == 1
    assert before.drop(columns="target").equals(after.drop(columns="target"))
