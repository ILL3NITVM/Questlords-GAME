#!/usr/bin/env python3
from __future__ import annotations
import argparse, errno, json, os, socket, subprocess, sys, threading, time, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
HOST="0.0.0.0"
PORT=8181
URL=f"http://127.0.0.1:{PORT}/"
BUILD="V44"
HEALTH="/__quadcom__/health"
SHUTDOWN="/__quadcom__/shutdown"

class QuadCOMHTTP(ThreadingHTTPServer):
    allow_reuse_address=True
    daemon_threads=True

class Handler(SimpleHTTPRequestHandler):
    server_version="QuadCOMLocal/44"
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy","same-origin")
        self.send_header("Cross-Origin-Embedder-Policy","require-corp")
        self.send_header("Cross-Origin-Resource-Policy","same-origin")
        p=urlparse(self.path).path
        self.send_header("Cache-Control","no-store" if p in ("/","/index.html","/glimmer.js","/sw.js","/manifest.json") or p.startswith("/__quadcom__/") else "no-cache")
        super().end_headers()
    def _json(self,obj,code=200):
        body=json.dumps(obj,separators=(",",":")).encode()
        self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if urlparse(self.path).path==HEALTH:
            return self._json({"product":"QuadCOM","build":BUILD,"port":PORT,"root":str(ROOT),"pid":os.getpid()})
        return super().do_GET()
    def do_POST(self):
        if urlparse(self.path).path==SHUTDOWN and self.client_address[0] in ("127.0.0.1","::1"):
            self._json({"status":"stopping","build":BUILD},202)
            threading.Thread(target=self.server.shutdown,daemon=True).start();return
        self.send_error(404)

def probe(timeout=.35):
    try:
        with urllib.request.urlopen(URL.rstrip("/")+HEALTH,timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def retire_supervised():
    info=probe()
    if not info or info.get("product")!="QuadCOM": return False
    try:
        req=urllib.request.Request(URL.rstrip("/")+SHUTDOWN,data=b"{}",method="POST",headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req,timeout=.5).read()
    except Exception: pass
    for _ in range(20):
        time.sleep(.1)
        with socket.socket() as s:
            s.settimeout(.08)
            if s.connect_ex(("127.0.0.1",PORT))!=0:return True
    return False

def open_browser():
    try: subprocess.Popen(["open",URL],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception: pass

def main():
    ap=argparse.ArgumentParser(add_help=True)
    ap.add_argument("--open",action="store_true",help="open the fixed QuadCOM URL after the server is healthy")
    args=ap.parse_args()
    os.chdir(ROOT)
    if probe(): retire_supervised()
    try:
        httpd=QuadCOMHTTP((HOST,PORT),Handler)
    except OSError as e:
        if e.errno in (errno.EADDRINUSE,48,98):
            print("QuadCOM: port 8181 is occupied by an older/non-supervised server.")
            print("Stop that one once (Ctrl-C), then rerun: python3 quadcom.py")
            raise SystemExit(2)
        raise
    print("QuadCOM ❖ V44 GLIMMER")
    print("FIXED HOME-APP ORIGIN:",URL)
    print("Port hopping: DISABLED · 8181 is permanent")
    print("Tap the existing ❖ Home Screen app. Ctrl-C stops the local bridge.")
    if args.open: threading.Timer(.35,open_browser).start()
    try:httpd.serve_forever()
    except KeyboardInterrupt:pass
    finally:httpd.server_close()

if __name__=="__main__":main()
