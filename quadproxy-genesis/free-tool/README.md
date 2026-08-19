# qwebengine-proxy-doctor

**Prove whether your Qt WebEngine traffic actually goes through your proxy.**

```bash
pip install qwebengine-proxy-doctor
qwebengine-proxy-doctor --proxy http://user:pass@host:port
```

Qt WebEngine fails proxy configuration **silently**. No exception, no log line, and
`QNetworkProxy` gives you no error callback. A page that renders fine may be loading
straight past your proxy. This tool makes that silence audible.

```
 [ok]  proxy reachable        CONNECT github.com:443 -> HTTP/1.1 200 (186ms)
 [!!]  egress routing         proxied IP == direct IP (203.0.113.7). Traffic is LEAKING.
 [!!]  qt applicationProxy    applicationProxy() is NoProxy. QWebEngineView will go DIRECT.
```

| Check | Catches |
|---|---|
| proxy reachable | proxy down, wrong port, firewalled |
| credentials sent | credentials set but never transmitted — Qt's documented silent failure |
| egress routing | traffic leaking direct to origin despite a configured proxy |
| dns handling | hostnames resolving outside the tunnel |
| qt applicationProxy | `NoProxy` at runtime — WebEngine going direct |
| qt credentials | proxy set with empty user; `proxyAuthenticationRequired` never handled |

Zero dependencies, stdlib only. Qt checks activate automatically if PyQt5, PyQt6 or PySide6
is importable, and are skipped cleanly otherwise.

## It refuses to lie to you

The tool reports **WARN, never PASS**, whenever it cannot *prove* a claim. If your proxy also
accepts anonymous connections, it will tell you it cannot distinguish a working credential from
a silently-dropped one, rather than showing you a green tick. A tool that sells verification
must not commit the same silent failure it exists to detect.

Run `--self-test` to validate the detector itself before trusting any verdict.

## The two bugs behind most of this

1. **Init order.** `QNetworkProxy.setApplicationProxy(proxy)` must run **before**
   `QApplication(sys.argv)`. Afterwards, Chromium's network process never sees it.
2. **Unhandled 407.** Chromium does not reuse `QNetworkProxy` credentials for render-process
   requests. Connect `QWebEnginePage.proxyAuthenticationRequired` or requests are cancelled
   in silence.

## Licence

MIT. Copy it, ship it, paste it into your Stack Overflow answer. No attribution required.

*Built by [Duncan Mutinelli](https://github.com/ILL3NITVM). A packaged PyQt starter kit with
eight integration examples is sold separately at https://quadproxy.com — this diagnostic is
free and always will be.*
