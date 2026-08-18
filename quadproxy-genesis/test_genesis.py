#!/usr/bin/env python3
"""Tests for the bottleneck engine. Run: python3 test_genesis.py"""
import importlib.util, datetime as dt, os, sys

spec = importlib.util.spec_from_file_location("g", os.path.join(os.path.dirname(os.path.abspath(__file__)), "genesis.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)


def st(**kw):
    return {"facts": {k: {"value": v, "how": "verified", "at": g.now()} for k, v in kw.items()}, "log": []}


CASES = [
    ("zero traffic measured", st(visitors_30d=5), "NO_QUALIFIED_TRAFFIC"),
    ("traffic, no clicks", st(visitors_30d=500, buy_clicks_30d=0), "POSITIONING"),
    ("clicks, no checkout", st(visitors_30d=500, buy_clicks_30d=20, checkouts_30d=0), "CTA"),
    ("checkout, no payment", st(checkouts_30d=10, payments_30d=0), "CHECKOUT"),
    ("paid, not delivered", st(payments_30d=3, deliveries_ok="no"), "FULFILLMENT"),
    ("customer exists", st(first_customer="yes"), "REPEATABLE_ACQUISITION"),
    ("no evidence at all", st(), "UNKNOWN"),
    ("discovery empty only", st(storefront_indexed="no", repo_stars=0), "NO_QUALIFIED_TRAFFIC"),
]


def main():
    fails = 0
    for name, s, expect in CASES:
        got = g.classify(s)["code"]
        ok = got == expect
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL':4}  {name:<24} expected={expect:<22} got={got}")

    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=99)).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = {"facts": {"visitors_30d": {"value": 500, "how": "verified", "at": old}}, "log": []}
    val, _, age, stale = g.get(s, "visitors_30d")
    ok = stale and val is g.UNKNOWN
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL':4}  {'stale fact expires':<24} age={age}d value={val}")

    ok = g.classify(s)["conf"] in ("none", "medium")
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL':4}  {'stale drives no verdict':<24} conf={g.classify(s)['conf']}")

    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
