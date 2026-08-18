# QWebEngineView ignoring your authenticated proxy? Here's the fix.

**Symptoms this solves:** blank or white page in `QWebEngineView` · your real IP still shows
despite the proxy · `407 Proxy Authentication Required` with no Python traceback ·
`ERR_TUNNEL_CONNECTION_FAILED` · the proxy works in `requests` but Qt WebEngine ignores it ·
`QNetworkProxy.setApplicationProxy` appears to do nothing · works on Windows, silently fails on
Linux · PySide6 and PyQt6 behaving differently.

<!-- ANCHOR: embed docs/media/doctor-demo.gif here once shot. This is the single highest-impact
     addition to this file. Script already written in KILLER_DEMO_PLAN.md (keep that file LOCAL). -->

## Two Qt WebEngine behaviours cause nearly all of it

**1. Initialisation order.** `QNetworkProxy.setApplicationProxy(proxy)` must run **before**
`QApplication(sys.argv)`. Called afterwards, Chromium's network process never sees it and every
request goes out direct — with no error of any kind.

**2. Unhandled 407.** Chromium does not reuse `QNetworkProxy` credentials for render-process
requests. Unless you connect `QWebEnginePage.proxyAuthenticationRequired`, the request is
cancelled silently. No exception. No log line. Qt provides no error callback here at all.

That silence is the whole problem: both failures look identical to "the page just didn't load."

## The complete working fix

```python
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtNetwork import QNetworkProxy
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView

PROXY_HOST, PROXY_PORT = "proxy.example.com", 8080
PROXY_USER, PROXY_PASS = "username", "password"

# --- 1. Install the proxy BEFORE QApplication is constructed. Order is load-bearing. ---
proxy = QNetworkProxy()
proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
proxy.setHostName(PROXY_HOST)
proxy.setPort(PROXY_PORT)
proxy.setUser(PROXY_USER)
proxy.setPassword(PROXY_PASS)
QNetworkProxy.setApplicationProxy(proxy)

app = QApplication(sys.argv)
view = QWebEngineView()

# --- 2. Handle the 407 explicitly. Without this, requests are cancelled in silence. ---
def on_proxy_auth(url, authenticator):
    authenticator.setUser(PROXY_USER)
    authenticator.setPassword(PROXY_PASS)

view.page().proxyAuthenticationRequired.connect(on_proxy_auth)

# --- 3. Verify. Never trust a page that merely loaded — check the egress IP. ---
view.load(QUrl("https://api.ipify.org"))
view.show()
sys.exit(app.exec())
```

If the IP shown is your own, the proxy is not being used — regardless of the page rendering fine.

> **The fix above and everything in `examples/` is MIT-licensed** — copy it into your project,
> your Stack Overflow answer, or your blog post. No attribution required. Only the packaged
> commercial kit under `quadproxy/` uses the single-customer licence in `LICENSE.txt`.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install PyQt6 PyQt6-WebEngine
python examples/02_authenticated_proxy.py
```

## Still failing? Diagnose it

Configuration has a free answer — the code above. *Verification* does not. If traffic is still
leaking, DNS is escaping the tunnel, or credentials are being dropped, run the diagnostic:

```bash
python -m quadproxy doctor --proxy http://user:pass@host:port
```

It reports WARN rather than PASS whenever it cannot *prove* a claim, so a green result means
something.

## Who built this, and what happens if it doesn't work

Built and maintained by Duncan Mutinelli (Dml Software) — [@ILL3NITVM](https://github.com/ILL3NITVM).
One person, not a team. Written after losing days to the init-order bug above.

- **Support:** email support@quadproxy.com. <!-- CONFIRM: state a real response time you will meet -->
- **Refund:** <!-- CONFIRM BEFORE PUBLISHING: this is a business commitment, not boilerplate.
     Recommended: full refund within 30 days, no questions asked, buyer keeps the files. -->

## Get the packaged kit

Everything above is free and complete. The **$29 one-time** kit at https://quadproxy.com adds the
packaged `quadproxy` module, the diagnostics CLI, the setup wizard, eight integration examples,
and 1.x updates.

**It is not a proxy service.** No proxy IPs, no bandwidth, no subscription. Bring credentials from
your own provider.

## Documentation

See `docs/` for quickstart, lifecycle, integration and troubleshooting guides.
