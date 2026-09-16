"""Reject incomplete exports before deriving or publishing claims."""

import hashlib
import json

from .config import EXPORTS, ROOT


def load(name):
    return json.loads((ROOT / "data/processed" / f"{name}.json").read_text(encoding="utf-8"))


def validate_exports():
    quality = load("quality")
    if len(quality) < 10 or any(x["failures"] for x in quality):
        raise ValueError("Missing or failed warehouse quality checks")
    for name in EXPORTS:
        if not load(name):
            raise ValueError(f"Empty required export: {name}")
    daily = load("mart_daily_product_metrics")
    dates = [row["metric_date"] for row in daily]
    if len(set(dates)) != 92 or min(dates) != "2020-11-01" or max(dates) != "2021-01-31":
        raise ValueError("Daily calendar must contain all 92 source dates")
    for row in daily:
        for numerator, denominator in [
            ("purchase_users", "users"),
            ("purchase_sessions", "sessions"),
            ("ordered_purchase_sessions", "ordered_checkout_sessions"),
        ]:
            if (
                row[numerator] is None
                or row[denominator] is None
                or not 0 <= row[numerator] <= row[denominator]
            ):
                raise ValueError(f"Invalid daily denominator: {row}")
    funnel = load("mart_funnel")
    ordered = sorted([r for r in funnel if r["grain"] == "ordered_sessions"], key=lambda r: r["stage"])
    if len(ordered) != 4 or any(a["reached"] < b["reached"] for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Invalid sequential funnel")
    audit = load("audit")
    coverage = {
        r["label"]: json.loads(r["detail"])["events"] for r in audit if r["section"] == "ecommerce_coverage"
    }
    missing = [e for e in ["view_item", "add_to_cart", "begin_checkout", "purchase"] if not coverage.get(e)]
    if missing:
        raise ValueError(f"Proposed funnel is unsupported; revise stages before publication: {missing}")


def provenance():
    files = sorted((ROOT / "data/processed").glob("*.json"))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
