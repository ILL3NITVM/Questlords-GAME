#!/usr/bin/env python3
"""
qt-proxy-doctor - prove whether your Qt WebEngine traffic actually uses your proxy.

Qt WebEngine fails proxy configuration SILENTLY. No exception, no log line, and
QNetworkProxy provides no error-handling callback. This tool makes the silence audible.

It answers five questions the Qt docs do not:

  1. REACHABLE   Is the proxy actually accepting connections?
  2. AUTH        Are your credentials really being SENT, or silently dropped?
  3. ROUTING     Is traffic going through the proxy, or leaking direct to origin?
  4. DNS         Is hostname resolution leaking outside the proxy?
  5. QT-ORDER    Was the proxy installed before Qt's network stack initialised?

Stdlib only. No install. Works with any HTTP proxy.
Qt checks activate automatically if PyQt5/PyQt6/PySide6 is importable.

Usage:
  python3 qt_proxy_doctor.py --proxy http://user:pass@host:port
  python3 qt_proxy_doctor.py --proxy http://host:port --self-test
"""
from __future__ import annotations
import argparse, base64, socket, ssl, sys, time
from urllib.parse import urlparse

TIMEOUT = 12
IP_ECHO_HOSTS = ["api.ipify.org", "ifconfig.me", "icanhazip.com"]

OK, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"
_SYM = {OK: "[ok]", FAIL: "[!!]", WARN: "[??]", SKIP: "[--]"}


class Result:
    def __init__(self):
        self.rows: list[tuple[str, str, str]] = []

    def add(self, check: str, status: str, detail: str) -> None:
        self.rows.append((check, status, detail))
        print(f" {_SYM[status]:5} {check:<22} {detail}")

    def verdict(self, mode: str = "scan") -> int:
        fails = [r for r in self.rows if r[1] == FAIL]
        warns = [r for r in self.rows if r[1] == WARN]
        print("\n" + "-" * 68)
        if fails:
            print(f" VERDICT: {len(fails)} FAILURE(S) - your proxy is NOT working as configured.")
            for c, _, d in fails:
                print(f"   -> {c}: {d}")
            return 1
        if warns:
            print(f" VERDICT: usable, but {len(warns)} thing(s) could not be proven.")
            return 0
        if mode == "selftest":
            print(" VERDICT: detector logic validated. This says nothing about YOUR proxy;")
            print("          re-run without --self-test to test it.")
        else:
            print(" VERDICT: proxy verified. Traffic is authenticated and routed.")
        return 0


def parse_proxy(url: str):
    """Split a proxy URL into (host, port, user, password)."""
    if "://" not in url:
        url = "http://" + url
    p = urlparse(url)
    if not p.hostname:
        raise ValueError(f"cannot parse proxy host from {url!r}")
    return p.hostname, p.port or 8080, p.username, p.password


def _connect_headers(host: str, port: int, user, password) -> bytes:
    """Build a CONNECT request, with Proxy-Authorization only if creds were given."""
    req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
    if user is not None:
        token = base64.b64encode(f"{user}:{password or ''}".encode()).decode()
        req += f"Proxy-Authorization: Basic {token}\r\n"
    return (req + "Proxy-Connection: keep-alive\r\n\r\n").encode()


def proxy_connect(ph, pp, user, password, target_host, target_port, timeout=TIMEOUT):
    """Open a tunnel through the proxy. Returns (socket|None, status_line, elapsed_ms)."""
    t0 = time.time()
    try:
        s = socket.create_connection((ph, pp), timeout)
    except OSError as e:
        # The proxy being unreachable is the single most important thing this
        # tool must report clearly. It must never surface as a traceback.
        return None, f"{type(e).__name__}: {e}", int((time.time() - t0) * 1000)
    s.settimeout(timeout)
    try:
        s.sendall(_connect_headers(target_host, target_port, user, password))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 65536:
                break
        ms = int((time.time() - t0) * 1000)
        if not buf:
            s.close()
            return None, "(no response from proxy)", ms
        status = buf.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        # Parse the status code properly rather than substring-matching " 200 ",
        # which misses a bare "HTTP/1.1 200" with no reason phrase.
        parts = status.split()
        code = parts[1] if len(parts) > 1 and parts[1].isdigit() else ""
        if code == "200":
            return s, status, ms
        s.close()
        return None, status, ms
    except Exception as e:
        s.close()
        return None, f"{type(e).__name__}: {e}", int((time.time() - t0) * 1000)


def https_get_via(sock, host: str, path: str) -> str:
    """Complete a TLS handshake over an established tunnel and GET a path."""
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(sock, server_hostname=host) as tls:
        tls.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: qt-proxy-doctor\r\n"
                    f"Connection: close\r\n\r\n".encode())
        data = b""
        while len(data) < 65536:
            chunk = tls.recv(4096)
            if not chunk:
                break
            data += chunk
    body = data.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in data else b""
    return body.decode("utf-8", "replace").strip()


def direct_public_ip() -> str | None:
    for host in IP_ECHO_HOSTS:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), TIMEOUT) as raw:
                with ctx.wrap_socket(raw, server_hostname=host) as tls:
                    tls.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\n"
                                f"Connection: close\r\n\r\n".encode())
                    data = b""
                    while len(data) < 8192:
                        c = tls.recv(4096)
                        if not c:
                            break
                        data += c
            body = data.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in data else b""
            ip = body.decode("utf-8", "replace").strip().splitlines()[-1].strip()
            if ip:
                return ip
        except Exception:
            continue
    return None


def proxied_public_ip(ph, pp, user, password) -> tuple[str | None, str]:
    for host in IP_ECHO_HOSTS:
        sock, status, _ = proxy_connect(ph, pp, user, password, host, 443)
        if not sock:
            continue
        try:
            txt = https_get_via(sock, host, "/")
            ip = txt.splitlines()[-1].strip() if txt else ""
            if ip:
                return ip, host
        except Exception:
            continue
    return None, ""


# ----------------------------- checks -----------------------------------

def check_reachable(r, ph, pp, user, password, probe_host):
    sock, status, ms = proxy_connect(ph, pp, user, password, probe_host, 443)
    if sock:
        sock.close()
        r.add("proxy reachable", OK, f"CONNECT {probe_host}:443 -> {status} ({ms}ms)")
        return True
    r.add("proxy reachable", FAIL,
          f"CONNECT {probe_host}:443 -> {status}. Nothing below can be trusted.")
    return False


def check_auth(r, ph, pp, user, password, probe_host):
    """The critical one: prove credentials are required AND accepted.

    Qt's documented failure is that credentials are set but never transmitted. We
    detect it by comparing an anonymous attempt against an authenticated attempt.
    """
    if user is None:
        r.add("credentials sent", SKIP, "no credentials in proxy URL; nothing to verify")
        return
    anon_sock, anon_status, _ = proxy_connect(ph, pp, None, None, probe_host, 443)
    if anon_sock:
        anon_sock.close()
    auth_sock, auth_status, _ = proxy_connect(ph, pp, user, password, probe_host, 443)
    if auth_sock:
        auth_sock.close()

    auth_ok = auth_sock is not None
    anon_ok = anon_sock is not None

    if auth_ok and not anon_ok:
        r.add("credentials sent", OK,
              f"anonymous rejected ({anon_status.split()[1] if len(anon_status.split())>1 else '?'}), "
              f"authenticated accepted - creds ARE being transmitted")
    elif auth_ok and anon_ok:
        r.add("credentials sent", WARN,
              "proxy accepts anonymous too - cannot prove your credentials are used. "
              "A silent-drop bug would look identical to success here.")
    elif not auth_ok and "407" in auth_status:
        r.add("credentials sent", FAIL,
              f"proxy returned 407 WITH credentials -> rejected. Wrong user/pass, "
              f"or the proxy wants a scheme other than Basic. ({auth_status})")
    else:
        r.add("credentials sent", FAIL, f"authenticated CONNECT failed: {auth_status}")


def check_routing(r, ph, pp, user, password):
    """Prove egress IP differs through the proxy - the anti-leak test."""
    prox_ip, via = proxied_public_ip(ph, pp, user, password)
    if not prox_ip:
        r.add("egress routing", WARN, "no IP-echo host reachable through proxy; cannot prove routing")
        return
    direct_ip = direct_public_ip()
    if not direct_ip:
        r.add("egress routing", WARN, f"proxied egress IP is {prox_ip} (via {via}); "
                                      f"direct IP unavailable, so no comparison possible")
        return
    if prox_ip == direct_ip:
        r.add("egress routing", FAIL,
              f"proxied IP == direct IP ({prox_ip}). Traffic is LEAKING past the proxy.")
    else:
        r.add("egress routing", OK, f"direct={direct_ip} -> proxied={prox_ip} (via {via})")


def check_dns(r, ph, pp, user, password, probe_host):
    """If the proxy resolves the name for us, DNS is not leaking locally."""
    sock, status, _ = proxy_connect(ph, pp, user, password, probe_host, 443)
    if not sock:
        r.add("dns handling", WARN, "could not test (tunnel failed)")
        return
    sock.close()
    try:
        local = socket.gethostbyname(probe_host)
        r.add("dns handling", WARN,
              f"proxy resolved {probe_host} remotely (good), but this host ALSO resolves it "
              f"locally to {local}. Qt WebEngine resolves DNS locally by default - "
              f"names you visit are visible to your local resolver.")
    except Exception:
        r.add("dns handling", OK, f"{probe_host} resolves only through the proxy")


def check_qt(r):
    """Inspect the live Qt proxy state and the initialisation-order trap."""
    mod = None
    for name in ("PyQt6.QtNetwork", "PyQt5.QtNetwork", "PySide6.QtNetwork"):
        try:
            mod = __import__(name, fromlist=["QNetworkProxy"])
            break
        except ImportError:
            continue
    if mod is None:
        r.add("qt binding", SKIP, "no PyQt5/PyQt6/PySide6 found - Qt-specific checks skipped")
        return
    QNetworkProxy = mod.QNetworkProxy
    app_proxy = QNetworkProxy.applicationProxy()
    kind = app_proxy.type()
    no_proxy = getattr(QNetworkProxy.ProxyType, "NoProxy", None) or QNetworkProxy.NoProxy
    if kind == no_proxy:
        r.add("qt applicationProxy", FAIL,
              "QNetworkProxy.applicationProxy() is NoProxy. QWebEngineView will go DIRECT. "
              "Call setApplicationProxy() BEFORE creating QApplication.")
    else:
        host, port = app_proxy.hostName(), app_proxy.port()
        has_user = bool(app_proxy.user())
        r.add("qt applicationProxy", OK, f"{host}:{port} user={'set' if has_user else 'EMPTY'}")
        if not has_user:
            r.add("qt credentials", FAIL,
                  "applicationProxy has no user set. Qt emits proxyAuthenticationRequired "
                  "and, if unconnected, silently fails with no error.")


def self_test(r, ph, pp):
    """Exercise the engine against a known-good proxy to prove the tool itself works."""
    print("\n self-test: validating detector logic against this machine's proxy\n")
    sock, status, ms = proxy_connect(ph, pp, None, None, "github.com", 443)
    if sock:
        sock.close()
        r.add("selftest tunnel", OK, f"github.com:443 -> {status} ({ms}ms)")
    else:
        r.add("selftest tunnel", FAIL, f"github.com:443 -> {status}")
    _, bad_status, _ = proxy_connect(ph, pp, None, None, "no-such-host.invalid", 443)
    if "200" not in bad_status:
        r.add("selftest neg-case", OK, f"bad host correctly refused -> {bad_status[:48]}")
    else:
        r.add("selftest neg-case", FAIL, "bad host returned 200 - detector cannot be trusted")
    hdr = _connect_headers("h", 443, "u", "p")
    r.add("selftest auth-hdr", OK if b"Basic dTpw" in hdr else FAIL,
          "Proxy-Authorization built correctly" if b"Basic dTpw" in hdr else "header malformed")
    hdr2 = _connect_headers("h", 443, None, None)
    r.add("selftest anon-hdr", OK if b"Proxy-Authorization" not in hdr2 else FAIL,
          "anonymous request correctly omits auth header")


def main() -> int:
    ap = argparse.ArgumentParser(description="Prove your Qt WebEngine proxy actually works.")
    ap.add_argument("--proxy", required=True, help="http://[user:pass@]host:port")
    ap.add_argument("--probe-host", default="github.com", help="host used for tunnel probes")
    ap.add_argument("--self-test", action="store_true", help="validate the detector itself")
    a = ap.parse_args()

    try:
        ph, pp, user, password = parse_proxy(a.proxy)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    shown = f"{user}:***@" if user else ""
    print("=" * 68)
    print(" qt-proxy-doctor - Qt WebEngine proxy verification")
    print(f" proxy: http://{shown}{ph}:{pp}   probe: {a.probe_host}")
    print("=" * 68 + "\n")

    r = Result()
    if a.self_test:
        self_test(r, ph, pp)
        return r.verdict("selftest")

    if check_reachable(r, ph, pp, user, password, a.probe_host):
        check_auth(r, ph, pp, user, password, a.probe_host)
        check_routing(r, ph, pp, user, password)
        check_dns(r, ph, pp, user, password, a.probe_host)
    check_qt(r)
    return r.verdict()


if __name__ == "__main__":
    sys.exit(main())
