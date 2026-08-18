# QuadProxy — Buyer Signal Sheet (Epoch 1)

Compiled 2026-08-18 by the Claude command layer.
No VM access this session (SSH structurally blocked); no storefront access (egress-blocked).
All findings below come from public web search + fetch only.

## Verification legend
- **VERIFIED** — I fetched the page and read it directly.
- **INDEXED** — URL returned by search engine; content summarised by the search index, NOT fetched by me
  (forum.qt.io, stackoverflow.com and wiki.qt.io are blocked from this container).
- Nothing here is invented. Anything I could not confirm is marked INDEXED, not asserted as fact.

---

## A. The chronic-pain evidence (product rationale is sound)

| # | Platform | URL | Problem | Date | Status |
|---|---|---|---|---|---|
| A1 | GitHub | https://github.com/qutebrowser/qutebrowser/issues/2492 | No PAC / proper proxy support in QtWebEngine | opened 2017-03-31 | **VERIFIED — still OPEN after 9 years** |
| A2 | GitHub | https://github.com/qutebrowser/qutebrowser/issues/4041 | WebEngine makes **direct connections despite proxy rules**; traffic leaked past proxy, caught by iptables | INDEXED | INDEXED |
| A3 | GitHub | https://github.com/qutebrowser/qutebrowser/issues/5731 | **DNS requests do not go over the proxy** by default | INDEXED | INDEXED |
| A4 | Qt Forum | https://forum.qt.io/topic/150315/can-t-setup-proxy-credentials | Cannot set proxy credentials | INDEXED | INDEXED |
| A5 | Qt Forum | https://forum.qt.io/topic/87441/setting-user-and-password-for-qt-webview-webengine-diectly | Proxy connects but **username/password are never sent** | reported ~2023-10-04 (INDEXED) | INDEXED |
| A6 | Qt Forum | https://forum.qt.io/topic/75058/different-proxy-for-each-qwebengineview-instance | Per-instance proxy impossible — applicationProxy is global | INDEXED | INDEXED |
| A7 | Qt Forum | https://forum.qt.io/topic/79395/qwebengineview-with-proxy-on-linux | Linux: WebEngine ignores GNOME system proxy settings | INDEXED | INDEXED |
| A8 | Qt Forum | https://forum.qt.io/topic/53430/http-proxy-problem-of-qwebengineview | HTTP proxy problem with QWebEngineView | INDEXED | INDEXED |
| A9 | qtcentre | https://www.qtcentre.org/threads/68308-Qt-WebEngine-and-Proxies | Qt WebEngine and proxies; NetworkAccessManager not used | INDEXED | INDEXED |

**Read:** the same failure modes recur from ~2015 through 2023+ and remain open. The friction is
chronic and structural, not a version bug that will be patched away. Product rationale: SOUND.

---

## B. The threat finding (this is the important one)

The **naive** question — "how do I set a proxy with username and password in QWebEngineView?" —
now has a **free, correct, 6-line answer that search engines emit directly in the results page.**
I watched it happen: my own searches returned complete working code (QNetworkProxy with
setUser/setPassword/setApplicationProxy, plus the proxyAuthenticationRequired signal handler)
without me opening a single page.

**Implication:** any positioning that reads as "we show you how to configure an authenticated
proxy" is selling something the search engine gives away above the fold. That is a $0 product.

## C. Where the money actually is — the unanswered half

None of the free answers address these, and all are evidenced in section A:

1. Credentials are set but **silently not sent** (A5) — and Qt provides **no error-handling callback**,
   so the developer has no way to tell.
2. Traffic **leaks direct to the origin IP despite a configured proxy** (A2) — silent, and in
   scraping/geo/compliance work this is the failure that costs real money.
3. **DNS escapes the proxy** (A3) — invisible deanonymisation.
4. **Per-instance / per-session proxies are impossible** (A6) — applicationProxy is process-global.
5. **Platform-inconsistent pickup** (A7) — works on one OS, silently not on another.

The common thread is **silence**. Every one of these fails without an exception, without a log line,
without a callback. That is why "diagnostics" and "public-IP verification" are the real product,
not the proxy setup code.

Encouraging datapoint: search already surfaces the kit described as
*"PyQt5/PyQt6 QWebEngineView authenticated HTTP proxy starter kit with QNetworkProxy diagnostics
and public-IP verification"* — the differentiating words are already in the indexed metadata.

---

## D. Bottleneck classification

**PRIMARY: POSITIONING.**
Not traffic, not price, not checkout — on current evidence the offer is framed around the half of
the problem that is free. The buyer's actual felt pain is *"my proxy silently isn't working and I
cannot prove why."*

**UNMEASURED: NO_QUALIFIED_TRAFFIC.** Cannot be confirmed or ruled out until nginx access logs are
read from wd1. Do not act on this classification until section 9 of the recon block is returned.

Message test — replace:
  "Authenticated proxy support for Qt WebEngine"
with:
  "Prove your Qt WebEngine traffic is actually going through your proxy — in 60 seconds."

The second sells verification. Verification has no free one-liner answer.

---

## E. Outreach rules (binding)

- Answer the person's actual question **in full, in the post**, with working code, whether or not
  they ever buy.
- Disclose commercial affiliation plainly whenever the kit is mentioned.
- Never post the same text twice across platforms.
- A thread already correctly answered is not a lead — skip it.
- Ten excellent leads beat a thousand impressions.
