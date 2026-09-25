QA scripts for the public site (Playwright, Chromium). Serve site/ first:
  cd site && python3 -m http.server 8192
Then run with PLAYWRIGHT=/path/to/playwright/index.mjs if playwright is not resolvable:
  node tools/qa/crawl.mjs 8192        every route at 390x844 and 1280x800: 404s, errors, tiny text, contrast
  node tools/qa/glossary.mjs          filter, count, "/", Esc, ?q=, deep links, A–Z
  node tools/qa/desk-views.mjs        desk audit: 4 views x iPhone portrait/landscape
  node tools/qa/offline.mjs           stops the server (port 8192) and checks offline routing
