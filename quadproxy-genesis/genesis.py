#!/usr/bin/env python3
"""
genesis.py - the self-feeding control loop for QuadProxy customer acquisition.

The problem this solves: command sessions are ephemeral and start blind. State
lives here, in the repo, versioned. Each run ingests observations, re-derives the
bottleneck from EVIDENCE ONLY, and emits the next self-contained prompt.

    observe -> record -> re-derive bottleneck -> emit next prompt -> observe ...

Core rule, inherited from qt_proxy_doctor: never assert what has not been observed.
A fact with no evidence is UNKNOWN, and an UNKNOWN blocks any conclusion that
depends on it. Stale facts expire and stop counting as evidence.

    python3 genesis.py show                     # showroom deck
    python3 genesis.py bottleneck               # classification + reasoning
    python3 genesis.py next                     # the next prompt, self-contained
    python3 genesis.py record <id> <value> --how verified --src "url or cmd"
    python3 genesis.py stale                    # what needs re-measuring
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "STATE.json")
UNKNOWN = "UNKNOWN"

# Evidence quality. Only VERIFIED and REPORTED count toward confident conclusions.
VERIFIED = "verified"   # directly observed by a tool or command
REPORTED = "reported"   # human-relayed from a real system (e.g. pasted VM output)
INDEXED  = "indexed"    # search-index summary; suggestive, not proof
INFERRED = "inferred"   # reasoning only; never sufficient alone
RANK = {VERIFIED: 3, REPORTED: 3, INDEXED: 1, INFERRED: 0}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load() -> dict:
    if not os.path.exists(STATE):
        return {"facts": {}, "log": []}
    with open(STATE) as f:
        return json.load(f)


def save(s: dict) -> None:
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2, sort_keys=True)
        f.write("\n")


# id -> (question, ttl_days). ttl expresses how fast reality changes underneath a fact.
FACTS = {
    "storefront_http":     ("Does https://quadproxy.com return 200?", 1),
    "storefront_indexed":  ("Does quadproxy.com appear in web search results?", 30),
    "repo_stars":          ("Stars on the public starter-kit repo", 14),
    "repo_releases":       ("Number of published GitHub releases", 14),
    "visitors_30d":        ("Unique visitors to the storefront, last 30d (nginx logs)", 7),
    "buy_clicks_30d":      ("Clicks on the buy/checkout CTA, last 30d", 7),
    "checkouts_30d":       ("Stripe checkout sessions created, last 30d", 7),
    "payments_30d":        ("Successful real payments, last 30d", 7),
    "deliveries_ok":       ("Did fulfilment deliver on every paid order?", 7),
    "first_customer":      ("Genuine external paying customer exists? (yes/no)", 3650),
    "free_tool_published": ("Is the free diagnostic tool publicly published?", 30),
    "helpful_posts_live":  ("Count of live public posts genuinely helping a real thread", 14),
}


def get(s: dict, fid: str):
    """Return (value, how, age_days, stale). Expired facts are surfaced as UNKNOWN."""
    f = s["facts"].get(fid)
    if not f:
        return UNKNOWN, None, None, False
    ttl = FACTS.get(fid, ("", 30))[1]
    try:
        seen = dt.datetime.strptime(f["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        age = (dt.datetime.now(dt.timezone.utc) - seen).days
    except Exception:
        age = None
    stale = age is not None and age > ttl
    return (UNKNOWN if stale else f["value"]), f.get("how"), age, stale


def num(v):
    """Coerce to a number, or None when the value is unknown/non-numeric."""
    if v is UNKNOWN or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def truthy(v) -> bool:
    return str(v).strip().lower() in {"yes", "true", "1", "ok"}


# --------------------------- bottleneck engine ---------------------------
# Each rule: (name, requires, test, classification, action). Rules are evaluated
# in funnel order; the FIRST rule whose requirements are met and whose test fires
# wins. A rule whose requirements are UNKNOWN cannot fire — it becomes a
# measurement instruction instead. This is what stops the loop from confidently
# attacking an imagined bottleneck.

def classify(s: dict) -> dict:
    v30   = num(get(s, "visitors_30d")[0])
    clicks= num(get(s, "buy_clicks_30d")[0])
    chk   = num(get(s, "checkouts_30d")[0])
    pay   = num(get(s, "payments_30d")[0])
    deliv = get(s, "deliveries_ok")[0]
    first = get(s, "first_customer")[0]
    indexed = get(s, "storefront_indexed")[0]
    stars = num(get(s, "repo_stars")[0])

    if truthy(first):
        return dict(code="REPEATABLE_ACQUISITION", conf="high",
                    why="A genuine external customer exists. The mission moves to repeatability.",
                    action="Identify the exact channel that produced the sale and run it again deliberately.",
                    missing=[])

    if pay is not None and pay > 0 and deliv is not UNKNOWN and not truthy(deliv):
        return dict(code="FULFILLMENT", conf="high",
                    why=f"{int(pay)} payment(s) succeeded but delivery did not complete.",
                    action="Fix fulfilment before any further traffic work. A paid, undelivered customer is worse than no customer.",
                    missing=[])

    if chk is not None and pay is not None and chk > 0 and pay == 0:
        return dict(code="CHECKOUT", conf="high",
                    why=f"{int(chk)} checkout session(s) created, 0 completed.",
                    action="Instrument the Stripe session drop-off; test the full purchase path on mobile.",
                    missing=[])

    if clicks is not None and chk is not None and clicks > 0 and chk == 0:
        return dict(code="CTA", conf="high",
                    why=f"{int(clicks)} buy click(s) produced no checkout session.",
                    action="The buy button is not reaching Stripe. Test it end to end before anything else.",
                    missing=[])

    if v30 is not None and clicks is not None and v30 > 30 and clicks == 0:
        return dict(code="POSITIONING", conf="high",
                    why=f"{int(v30)} visitors in 30d, zero buy clicks. They arrive and leave.",
                    action="Rewrite the headline to sell VERIFICATION, not configuration. Configuration has a free answer.",
                    missing=[])

    if v30 is not None and v30 <= 30:
        return dict(code="NO_QUALIFIED_TRAFFIC", conf="high",
                    why=f"Measured {int(v30)} visitors in 30d. Nothing downstream can be diagnosed.",
                    action="Publish the free tool and post genuinely useful answers on real threads.",
                    missing=[])

    # No funnel telemetry. Fall back to discovery-surface evidence, and say so.
    surface = []
    if indexed is not UNKNOWN and not truthy(indexed):
        surface.append("storefront absent from search index")
    if stars is not None and stars == 0:
        surface.append("repo has 0 stars")
    if surface:
        return dict(code="NO_QUALIFIED_TRAFFIC", conf="medium",
                    why="No funnel telemetry yet, but the discovery surface is empty: " + "; ".join(surface) + ".",
                    action="Build discovery. Re-measure visitors_30d from nginx logs to raise confidence to high.",
                    missing=["visitors_30d"])

    return dict(code="UNKNOWN", conf="none",
                why="Insufficient evidence. Refusing to guess a bottleneck.",
                action="Measure the funnel before acting.",
                missing=["visitors_30d", "storefront_indexed"])


# ------------------------------- rendering -------------------------------
W = 52  # narrow enough for an iPhone SSH terminal


def rule(ch="-"):
    return ch * W


def show(s: dict) -> None:
    b = classify(s)
    print(rule("="))
    print(" QUADPROXY GENESIS".ljust(W))
    print(f" {now()}".ljust(W))
    print(rule("="))
    for fid, (q, _) in FACTS.items():
        val, how, age, stale = get(s, fid)
        shown = "?" if val is UNKNOWN else str(val)[:16]
        tag = "" if val is UNKNOWN else {VERIFIED: "V", REPORTED: "R", INDEXED: "i", INFERRED: "~"}.get(how, "?")
        agestr = "" if age is None else (f" {age}d" + ("!" if stale else ""))
        print(f" {fid[:20]:<20} {shown:>16} {tag}{agestr}")
    print(rule())
    print(f" BOTTLENECK : {b['code']}")
    print(f" CONFIDENCE : {b['conf']}")
    print(rule())
    for line in textwrap.wrap(b["why"], W - 2):
        print(f" {line}")
    print(rule())
    print(" NEXT:")
    for line in textwrap.wrap(b["action"], W - 3):
        print(f"  {line}")
    if b["missing"]:
        print(rule())
        print(" UNMEASURED: " + ", ".join(b["missing"]))
    print(rule("="))
    print(" V=verified R=reported i=indexed ~=inferred !=stale")


def next_prompt(s: dict) -> None:
    """Emit a self-contained prompt that reconstructs this epoch in a cold session."""
    b = classify(s)
    known, unknown = [], []
    for fid, (q, _) in FACTS.items():
        val, how, age, stale = get(s, fid)
        (unknown if val is UNKNOWN else known).append(
            f"- {fid} = {val}  [{how}, {age}d old]" if val is not UNKNOWN else f"- {fid}: {q}")
    print(f"""QUADPROXY GENESIS - EPOCH PROMPT (generated {now()})

GOAL: first genuine external paying customer, then repeatable acquisition.

ESTABLISHED FACTS (do not re-derive these):
{chr(10).join(known) if known else "- none recorded yet"}

UNMEASURED (treat as UNKNOWN; do not assume):
{chr(10).join(unknown) if unknown else "- none"}

CURRENT BOTTLENECK: {b['code']} (confidence: {b['conf']})
REASONING: {b['why']}
PRESCRIBED ACTION: {b['action']}

RULES:
- Never assert what has not been observed. Mark every claim verified/reported/indexed/inferred.
- Do not optimise for commits, agents, posts or reports. Optimise for a real customer.
- Never fabricate a lead, a quote, a date or a customer.
- Any outreach must genuinely help the person first, with commercial affiliation disclosed.

WHEN YOU LEARN SOMETHING, WRITE IT BACK:
  python3 genesis.py record <fact_id> <value> --how verified --src "<url or command>"
Then re-run `python3 genesis.py next` to regenerate this prompt from the new state.""")


def main() -> int:
    ap = argparse.ArgumentParser(description="QuadProxy Genesis self-feeding loop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show"); sub.add_parser("next"); sub.add_parser("stale")
    sub.add_parser("bottleneck")
    rec = sub.add_parser("record")
    rec.add_argument("fact"); rec.add_argument("value")
    rec.add_argument("--how", default=VERIFIED, choices=[VERIFIED, REPORTED, INDEXED, INFERRED])
    rec.add_argument("--src", default="")
    a = ap.parse_args()
    s = load()

    if a.cmd == "show":
        show(s)
    elif a.cmd == "next":
        next_prompt(s)
    elif a.cmd == "bottleneck":
        b = classify(s)
        print(f"{b['code']} (confidence: {b['conf']})\n{b['why']}\n-> {b['action']}")
        if b["missing"]:
            print(f"unmeasured: {', '.join(b['missing'])}")
    elif a.cmd == "stale":
        any_stale = False
        for fid in FACTS:
            val, how, age, stale = get(s, fid)
            if stale or (val is UNKNOWN and fid not in s["facts"]):
                any_stale = True
                print(f"{fid:<22} {'STALE' if stale else 'NEVER MEASURED':<15} {FACTS[fid][0]}")
        if not any_stale:
            print("all facts fresh")
    elif a.cmd == "record":
        if a.fact not in FACTS:
            print(f"unknown fact id {a.fact!r}. valid: {', '.join(FACTS)}", file=sys.stderr)
            return 2
        before = classify(s)["code"]
        s["facts"][a.fact] = {"value": a.value, "how": a.how, "src": a.src, "at": now()}
        after_state = dict(s)
        after = classify(after_state)["code"]
        s["log"].append({"at": now(), "fact": a.fact, "value": a.value, "how": a.how, "src": a.src})
        save(s)
        print(f"recorded {a.fact}={a.value} ({a.how})")
        if before != after:
            print(f"BOTTLENECK CHANGED: {before} -> {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
