#!/usr/bin/env python3
"""Static server for QA that applies site/_headers the way Cloudflare Pages and Netlify do.

    cd site && python3 tools/qa/serve.py 8193

Rules are `path` lines (exact, or ending in `*` for a prefix) followed by indented `Name: value` lines.
Every matching rule applies, in file order. Directory requests serve index.html; unknown paths serve 404.html.
"""
import http.server, os, sys

def rules(path="_headers"):
    out, cur = [], None
    for line in open(path, encoding="utf-8"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] not in " \t":
            cur = (line.strip(), []); out.append(cur)
        else:
            k, v = line.strip().split(":", 1); cur[1].append((k.strip(), v.strip()))
    return out

RULES = rules()

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        p = self.path.split("?", 1)[0]
        for pat, hs in RULES:
            if (pat.endswith("*") and p.startswith(pat[:-1])) or p == pat:
                for k, v in hs:
                    self.send_header(k, v)
        super().end_headers()
    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists("404.html"):
            body = open("404.html", "rb").read()
            self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            super().send_error(code, message, explain)
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("", int(sys.argv[1]) if len(sys.argv) > 1 else 8193), H).serve_forever()
