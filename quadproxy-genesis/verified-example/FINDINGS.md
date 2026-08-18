# Verified end-to-end findings — Qt 6.11.0 / PyQt 6.11.0

Produced by `e2e_proxy_test.py`, which stands up a real origin server and a real
Basic-auth-requiring forward proxy and drives an actual `QWebEngineView` offscreen.
Nothing is mocked. Reproduce with:

    python3 e2e_proxy_test.py                 # non-loopback origin
    E2E_HOST=127.0.0.1 python3 e2e_proxy_test.py   # loopback origin

## Finding 1 — a page can load perfectly while the proxy is never contacted

With a loopback origin:

    load ok              : True
    body received        : 'ORIGIN-REACHED-THROUGH-PROXY'
    proxy saw requests   : 0

`loadFinished(True)`, correct content, no error of any kind — and the configured proxy
handled **zero** requests. Chromium bypasses proxies for loopback destinations, and in this
test it did so even with `--proxy-bypass-list=<-loopback>` set.

Any developer testing against a local server would conclude their proxy configuration works.
It does not. This is the silent failure, reproduced deliberately.

## Finding 2 — proxyAuthenticationRequired did NOT fire, yet auth succeeded

With a non-loopback origin and credentials set on `QNetworkProxy` before `QApplication`:

    proxy saw requests   : 2
    407 challenges issued: 1
    authenticated through: 1
    auth callback fired  : 0 time(s)

The proxy challenged once; the retry carried valid credentials; the page loaded. But
`QWebEnginePage.proxyAuthenticationRequired` **never fired**.

This contradicts the widely repeated advice that you must connect that signal for
authenticated proxies to work. On Qt 6.11.0, credentials set on `QNetworkProxy` before
`QApplication` are answered by Chromium automatically.

## Finding 3 — therefore: behaviour is version-dependent, so verify empirically

Finding 2 sits directly against field reports on Qt 6.5.3 where the `Proxy-Authorization`
header is reportedly never sent at all (forum.qt.io topic 150315). Both cannot be universally
true, which means this behaviour changes across Qt versions.

The practical consequence, and the honest positioning for the product:

> Do not trust the documentation, a tutorial, or a rendered page. The only reliable
> approach is to verify empirically on the Qt version you actually ship.

Keep connecting `proxyAuthenticationRequired` — it is harmless when unused and essential on
versions that need it. But treat a loaded page as evidence of nothing.

## Caveats, stated plainly
- Single environment: Qt 6.11.0 / PyQt 6.11.0, Linux, offscreen platform.
- Not tested on Windows or macOS, nor on PyQt5/PySide6, nor against a real upstream proxy
  vendor. Those would strengthen or complicate findings 2 and 3.
- Finding 1's loopback bypass is documented Chromium behaviour; the notable part is that it
  persisted despite the bypass-list flag.
