#!/usr/bin/env python3
"""
End-to-end proof that the documented fix actually works.

Stands up a real origin server and a real Basic-auth-requiring HTTP proxy, drives a
real QWebEngineView through them offscreen, then asserts on what the proxy actually
observed. Nothing here is mocked: if the credentials do not cross the wire, this fails.

Run: QT_QPA_PLATFORM=offscreen python3 e2e_proxy_test.py
"""
import base64, os, sys, threading, http.server, socketserver, urllib.request

HOST = os.environ.get("E2E_HOST", "192.0.2.2")  # non-loopback: Chromium bypasses proxies for loopback
ORIGIN_PORT, PROXY_PORT = 8901, 8902
USER, PASSWORD = "demo_user", "demo_pass"
BODY = b"ORIGIN-REACHED-THROUGH-PROXY"

seen = {"requests": 0, "authed": 0, "anonymous_challenged": 0}


class Origin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)

    def log_message(self, *a):
        pass


class Proxy(http.server.BaseHTTPRequestHandler):
    """Minimal forward proxy that demands Basic auth, exactly like a real one."""

    protocol_version = "HTTP/1.1"

    def do_GET(self):
        seen["requests"] += 1
        auth = self.headers.get("Proxy-Authorization")
        expected = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        if auth != expected:
            # This is the 407 that Qt WebEngine silently fails to answer.
            seen["anonymous_challenged"] += 1
            self.send_response(407)
            self.send_header("Proxy-Authenticate", 'Basic realm="proxy"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        seen["authed"] += 1
        with urllib.request.urlopen(self.path, timeout=10) as r:
            data = r.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def serve(handler, port):
    class S(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    srv = S((HOST, port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    # Chromium bypasses proxies for loopback by default; disable that so the test is real.
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--proxy-bypass-list=<-loopback> --no-sandbox"
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    serve(Origin, ORIGIN_PORT)
    serve(Proxy, PROXY_PORT)

    from PyQt6.QtCore import QUrl, QTimer
    from PyQt6.QtNetwork import QNetworkProxy
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    # --- THE FIX, PART 1: install the proxy BEFORE QApplication exists. ---
    proxy = QNetworkProxy()
    proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
    proxy.setHostName(HOST)
    proxy.setPort(PROXY_PORT)
    proxy.setUser(USER)
    proxy.setPassword(PASSWORD)
    QNetworkProxy.setApplicationProxy(proxy)

    app = QApplication(sys.argv)
    view = QWebEngineView()

    # --- THE FIX, PART 2: answer the 407 explicitly, or requests die in silence. ---
    auth_calls = []

    def on_proxy_auth(url, authenticator):
        auth_calls.append(str(url))
        authenticator.setUser(USER)
        authenticator.setPassword(PASSWORD)

    view.page().proxyAuthenticationRequired.connect(on_proxy_auth)

    result = {}

    def finished(ok):
        result["ok"] = ok
        view.page().toPlainText(lambda t: (result.__setitem__("text", t), app.quit()))

    view.loadFinished.connect(finished)
    view.load(QUrl(f"http://{HOST}:{ORIGIN_PORT}/"))
    QTimer.singleShot(25000, app.quit)
    app.exec()

    body = result.get("text", "")
    print("=" * 60)
    print(f" load ok              : {result.get('ok')}")
    print(f" body received        : {body.strip()[:40]!r}")
    print(f" proxy saw requests   : {seen['requests']}")
    print(f" 407 challenges issued: {seen['anonymous_challenged']}")
    print(f" authenticated through: {seen['authed']}")
    print(f" auth callback fired  : {len(auth_calls)} time(s)")
    print("=" * 60)

    checks = [
        ("page loaded successfully", result.get("ok") is True),
        # Deliberately NOT called "via proxy": content arriving proves nothing about
# the path it took. That conflation is the exact bug this whole test exists for.
        ("origin content arrived (path unproven)", BODY.decode() in body),
        ("proxy actually handled the request", seen["requests"] > 0),
        ("credentials reached the proxy", seen["authed"] > 0),
    ]
    bad = 0
    for label, passed in checks:
        print(f" [{'ok' if passed else '!!'}] {label}")
        bad += not passed
    print("\n" + ("VERIFIED: the documented fix works end to end."
                  if not bad else f"{bad} CHECK(S) FAILED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
