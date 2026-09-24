// Browser smoke for the desk. Usage:
//   node scripts/browser-smoke.mjs [url]            real Coinbase tape
//   SMOKE_FIXTURE=1 node scripts/browser-smoke.mjs  synthetic Coinbase tape (offline / blocked networks)
//   SMOKE_IGNORE_TLS=1                              behind a TLS-intercepting proxy (fonts)
// Checks desktop and mobile: title, live price, >1 ticket, backtest result or refusal,
// sleep while hidden, no horizontal overflow, zero console errors.
import { chromium } from "playwright";

const url = process.argv[2] ?? "http://127.0.0.1:8080/";
const fixture = process.env.SMOKE_FIXTURE === "1";
// Optional: point at a specific Chromium when Playwright's own download is missing.
const executablePath = process.env.SMOKE_CHROME || undefined;

/** A choppy uptrend so the fly has something to smell and some glare. */
function makeTape() {
  let px = 100000;
  let t = Math.floor(Date.now() / 60000) * 60 - 300 * 60;
  const rows = [];
  let n = 0;
  for (let i = 0; i < 300; i++) {
    px *= 1 + 0.0008 + Math.sin(i * 1.7) * 0.0035;
    rows.push([t, px * 0.999, px * 1.001, px, px, 1]);
    t += 60;
  }
  return {
    rows,
    // One ticker poll is ~4s of tape: small moves, a new 1m candle every few polls.
    step() {
      n++;
      px *= 1 + 0.00004 + Math.sin(n * 0.9) * 0.00012;
      if (n % 3 === 0) {
        t += 60;
        rows.push([t, px * 0.999, px * 1.001, px, px, 1]);
      }
    },
    get price() {
      return px;
    },
  };
}

async function run(viewport, label) {
  const browser = await chromium.launch({ executablePath });
  const page = await browser.newPage({ viewport, ignoreHTTPSErrors: !!process.env.SMOKE_IGNORE_TLS });
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("requestfailed", (r) => console.log(`  [${label}] request failed: ${r.url().slice(0, 100)} ${r.failure()?.errorText ?? ""}`));

  let polls = 0;
  if (fixture) {
    const tape = makeTape();
    await page.route("https://api.exchange.coinbase.com/**", async (route) => {
      const u = route.request().url();
      const json = (body) =>
        route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(body) });
      if (u.includes("/ticker")) {
        polls++;
        tape.step();
        return json({ price: String(tape.price) });
      }
      if (u.includes("/stats")) return json({ open: String(tape.rows[0][4]) });
      if (u.includes("/candles")) return json([...tape.rows.slice(-300)].reverse());
      return route.abort();
    });
    // Offline means offline: fonts fall back to the system stack.
    await page.route(/fonts\.(googleapis|gstatic)\.com/, (route) =>
      route.fulfill({ status: 200, contentType: "text/css", body: "" }),
    );
  } else {
    page.on("request", (r) => r.url().includes("_serverFn") && polls++);
  }

  await page.goto(url, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "SANDEVISTAN" }).waitFor();
  await page.waitForFunction(() => /\$\d{2,3},\d{3}/.test(document.querySelector("main")?.textContent ?? ""), null, { timeout: 20000 });

  // Let the fly work: cooldown is 12s, so two tickets needs ~15-30s of tape.
  let most = 0;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(2000);
    const live = await page.locator("text=/\\d \\/ 4 live/").textContent();
    most = Math.max(most, Number(live?.trim()[0] ?? 0));
    if (most > 1) break;
  }

  const bt = (await page.getByRole("region", { name: "Backtest" }).textContent()) ?? "";
  const backtestOk = /WIN RATE|Mushroom body is full|Backtest failed/.test(bt);
  if (!/WIN RATE|Mushroom body is full/.test(bt)) {
    await page.getByRole("button", { name: "Let the fly backtest" }).click();
    await page.waitForTimeout(1500);
  }
  const btAfter = (await page.getByRole("region", { name: "Backtest" }).textContent()) ?? "";

  // Hide the tab: polling must stop.
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const before = polls;
  await page.waitForTimeout(9000);
  const hiddenPolls = polls - before;
  const asleep = await page.locator("text=asleep").count();
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const woke = await page
    .locator("text=TAB WAS SHUT · BOOK UNCHANGED")
    .waitFor({ timeout: 8000 })
    .then(() => true)
    .catch(() => false);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  await page.screenshot({ path: `smoke-${label}.png`, fullPage: true });
  await browser.close();

  const checks = {
    "live price": true,
    "more than one ticket": most > 1,
    "backtest result or refusal": backtestOk || /WIN RATE|Mushroom body is full/.test(btAfter),
    "no polls while hidden": hiddenPolls === 0,
    "status shows asleep": asleep > 0,
    "wake banner": woke,
    "no horizontal overflow": !overflow,
    "zero console errors": errors.length === 0,
  };
  console.log(`\n[${label}] max open ${most}, backtest: ${btAfter.replace(/\s+/g, " ").slice(0, 160)}`);
  for (const [k, v] of Object.entries(checks)) console.log(`  ${v ? "ok  " : "FAIL"} ${k}`);
  if (errors.length) console.log("  console errors:", errors);
  return Object.values(checks).every(Boolean);
}

const results = [
  await run({ width: 1280, height: 900 }, "desktop"),
  await run({ width: 390, height: 844 }, "mobile"),
];
process.exit(results.every(Boolean) ? 0 : 1);
