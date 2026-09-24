// Bundles the desk into one self-contained HTML file: sandevistan.html
import { build } from "esbuild";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const tmp = mkdtempSync(join(tmpdir(), "sandevistan-"));

const js = await build({
  entryPoints: [join(root, "single/main.tsx")],
  bundle: true,
  minify: true,
  format: "iife",
  write: false,
  jsx: "automatic",
  target: "es2020",
  define: { "process.env.NODE_ENV": '"production"' },
  alias: { "@/lib/market": join(root, "single/market.ts"), "@": join(root, "src") },
});

const cssOut = join(tmp, "out.css");
execFileSync(join(root, "node_modules/.bin/tailwindcss"), ["-i", join(root, "single/styles.css"), "-o", cssOut, "--minify"], {
  cwd: root,
  stdio: "inherit",
});

const favicon = readFileSync(join(root, "public/favicon.svg"), "utf8");
const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SANDEVISTAN</title>
<meta name="description" content="Autonomous fly desk. The cyberroach opens demo Bitcoin tickets with a take profit and a stop.">
<meta name="theme-color" content="#070809">
<link rel="icon" href="data:image/svg+xml,${encodeURIComponent(favicon)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@400;500;600;700&display=swap">
<style>${readFileSync(cssOut, "utf8")}</style>
</head>
<body class="bg-bg text-fg antialiased">
<div id="app"></div>
<script>${js.outputFiles[0].text.replace(/<\/script/gi, "<\\/script")}</script>
</body>
</html>
`;
writeFileSync(join(root, "sandevistan.html"), html);
console.log(`sandevistan.html ${(html.length / 1024).toFixed(0)} KB`);
