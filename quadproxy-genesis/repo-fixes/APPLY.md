# Fix pack for ILL3NITVM/qt-webengine-proxy-starter

Prepared from a verified audit. This session's GitHub scope covers only
`ILL3NITVM/Questlords-GAME`, so these files could not be pushed to the product repo directly.
Apply them there manually.

Two items marked `CONFIRM` in `README.replacement.md` are **business commitments, not copy** —
a refund window and a support response time. Do not publish either until you intend to honour it.
An unhonoured refund promise is worse than none.

## Order of application (highest impact first)

### 1. README — symptom-first rewrite
`cp README.replacement.md ../README.md`, resolve the two CONFIRM markers, then commit.
Rationale: the current README's first ~80 words are a price and two disclaimers, and it contains
none of the strings a suffering developer actually types (`blank page`, `white screen`,
`direct IP`, `ERR_TUNNEL_CONNECTION_FAILED`, `PySide` — all verified absent). A developer
arriving mid-panic sees "$29.00" before any evidence the thing works.

### 2. Version reconciliation — cheapest credibility repair available
Four files, three different answers (all verified):
    VERSION               = 1.1.0
    release_metadata.json = 1.1.0
    pyproject.toml        = 1.0.0
    CHANGELOG.md top      = 1.0.0
    GitHub release tag    = v1.0.0
Pick 1.1.0, set it everywhere, add a real changelog entry listing the eight example files that
actually ship (the changelog currently lists five, under names that mostly do not exist).

### 3. Remove committed build noise and the internal marketing doc
    git rm -r --cached __pycache__ examples/__pycache__
    cp .gitignore.replacement ../.gitignore
    git rm docs/KILLER_DEMO_PLAN.md     # KEEP IT LOCALLY - it is the shooting script for step 5
`docs/KILLER_DEMO_PLAN.md` is publicly readable and opens by describing itself as a
"high-converting technical demonstration". That is an internal conversion-planning document
sitting in a repo you are asking strangers to trust with $29.

### 4. Licence the snippet so people can legally cite you
`LICENSE.txt` currently forbids redistribution while the README calls the repo "a free technical
reference". On a strict reading the fix snippet cannot be copied into an answer or blog post —
which forecloses the exact inbound-link mechanism this project needs. Add `LICENSE-SNIPPET.txt`
(MIT) covering the README code block and `examples/`. The README replacement already states this.

### 5. Shoot the demo GIF
The script already exists in `KILLER_DEMO_PLAN.md`: broken run -> white screen -> `doctor` FAIL ->
two-line fix -> `doctor` PASS with the egress IP visibly changing -> page loads. Record with
`vhs` or `asciinema`, commit to `docs/media/doctor-demo.gif`, embed at the ANCHOR comment in the
README replacement. Redact the real proxy IP. This is the single artifact that converts
"unknown seller, 0 stars" into "I can see it work".

### 6. Fix the topic spelling
The repo sits in topic `qt-webengine` (4 repos, dead) and is absent from `qtwebengine`
(89 repos, the live one, headed by qutebrowser at 11.6k stars). Set topics to:
qtwebengine, qwebengineview, pyqt5, pyqt6, pyqt, python, proxy, http-proxy,
proxy-authentication, authenticated-proxy, qnetworkproxy, browser-automation, web-scraping
Honest expectation: modest. Topic pages sort by stars, so at 0 stars you rank last regardless.
Two minutes of effort; do not expect it to move the needle alone.

### 7. Resolve the SOCKS5 contradiction
README's "What QuadProxy Does Not Provide" says SOCKS5 is unsupported, while
`examples/07_socks5_and_http_proxies.py` ships. Either remove the example or amend the claim.
The buyer can see both.

### 8. Downgrade unearned claims
`pyproject.toml` declares `Development Status :: 5 - Production/Stable` on 8 commits with no CI
and no users. Set `4 - Beta` until CI is green. "Production-grade" in prose has the same problem.
