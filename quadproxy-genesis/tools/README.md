# qt-proxy-doctor

Prove whether your Qt WebEngine traffic actually goes through your proxy.

```
python3 qt_proxy_doctor.py --proxy http://user:pass@host:port
```

Qt WebEngine fails proxy configuration **silently** — no exception, no log line, and
`QNetworkProxy` offers no error-handling callback. This tool makes that silence audible.

| Check | Catches |
|---|---|
| proxy reachable | proxy down / wrong port |
| credentials sent | creds set but never transmitted (Qt's documented silent failure) |
| egress routing | traffic leaking direct to origin despite a configured proxy |
| dns handling | hostnames resolving outside the tunnel |
| qt applicationProxy | `NoProxy` at runtime — WebEngine going direct |
| qt credentials | proxy set with empty user; `proxyAuthenticationRequired` never handled |

Stdlib only, no install. Qt checks activate automatically if PyQt5/PyQt6/PySide6 is importable.
Run `--self-test` to validate the detector itself before trusting a verdict.

## Design rule

It reports **WARN, not PASS**, whenever it cannot *prove* a claim. A tool that sells
verification must never assert what it did not observe — an over-confident green here would
be the same silent lie the product exists to eliminate.

## Verification performed

Every path below was executed, not assumed:

- self-test against a live HTTP proxy — 4/4 checks pass, negative case correctly refused
- unreachable proxy — reports FAIL cleanly, exit 1, no traceback
- ambiguous auth (proxy accepts anonymous) — correctly downgrades to WARN rather than PASS
- Qt case A: no `applicationProxy` — FAIL "will go DIRECT" (real PyQt6)
- Qt case B: proxy set, empty user — FAIL on silent-auth trap (real PyQt6)
- Qt case C: fully configured — PASS (real PyQt6)

## Why this exists commercially

Configuring a Qt proxy has a free six-line answer that search engines print directly in
results. *Verifying* one does not. This tool is the free, honest wedge: it makes the silent
failure visible, and the paid starter kit at https://quadproxy.com is what fixes it properly.
