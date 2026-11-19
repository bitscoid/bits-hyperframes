#!/usr/bin/env python3
"""
Samples the composition for the sync gate. Companion to sync_gate.py.

Two layers decide whether a text is on screen, and the probe must apply both:

1. **Clip gating** — the engine shows a `.clip` only inside
   `[data-start, data-start + data-duration)`. GSAP does not do this; the
   runtime does. A probe that only seeks GSAP sees every text at every time.
2. **The timeline** — opacity, scale and transforms set by `seek(t)`.

Measured failure of skipping layer 1: the probe reported all four texts present
before the first word, and the gate failed on a correct composition.

    python3 qc/make_sync_probe.py     -> writes work/sync-probe.json
    python3 qc/sync_gate.py           -> compares against the word times
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "qc" / "sync-cases.json"
WORDS = ROOT / "audio" / "words.json"
OUT = ROOT / "work" / "sync-probe.json"

for p in (CASES, WORDS):
    if not p.exists():
        sys.exit(f"missing {p.relative_to(ROOT)}")

vo_delay = json.loads(WORDS.read_text())["vo_delay"]
cases = json.loads(CASES.read_text())

times = []
for c in cases:
    t = vo_delay + c["t_vo"]
    times.append(
        {"label": c["text"], "before": round(t - 0.15, 3), "after": round(t + 0.10, 3)}
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
request = json.dumps({"composition": str(ROOT / "index.html"), "times": times}).encode()

script = r"""
const fs = require('node:fs');
const path = require('node:path');

function findChrome() {
  if (process.env.HYPERFRAMES_BROWSER_PATH) return process.env.HYPERFRAMES_BROWSER_PATH;
  const root = path.join(process.env.HOME, '.cache/hyperframes/chrome');
  if (!fs.existsSync(root)) return null;
  const stack = [root];
  while (stack.length) {
    const dir = stack.pop();
    for (const e of fs.readdirSync(dir, {withFileTypes: true})) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) stack.push(p);
      else if (e.name === 'chrome-headless-shell' && fs.statSync(p).size > 1e6) return p;
    }
  }
  return null;
}

const exe = findChrome();
if (!exe) { console.error('no browser; run: npx hyperframes browser ensure'); process.exit(2); }

let puppeteer;
for (const base of [
  path.join(process.env.HOME, 'Motion-Skills/_install/node_modules'),
  path.join(process.cwd(), 'node_modules'),
]) {
  try { puppeteer = require(require.resolve('puppeteer-core', {paths: [base]})); break; } catch (e) {}
}
if (!puppeteer) { console.error('puppeteer-core not found'); process.exit(2); }

(async () => {
  const req = JSON.parse(fs.readFileSync(0, 'utf8'));
  const browser = await puppeteer.launch({
    executablePath: exe,
    args: ['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files'],
    headless: true,
  });
  const page = await browser.newPage();
  await page.setViewport({width: 1080, height: 1920});
  await page.goto('file://' + req.composition, {waitUntil: 'networkidle0'});
  await page.waitForFunction(
    () => window.__timelines && Object.keys(window.__timelines).length > 0,
    {timeout: 20000},
  );

  const visibleAt = (seconds) => page.evaluate((t) => {
    // 1) drive every registered timeline
    Object.keys(window.__timelines).forEach((n) => {
      window.__timelines[n].totalTime(t, false);
    });

    // 2) apply the engine's clip gating, which GSAP does not do
    const inWindow = (el) => {
      let node = el;
      while (node && node !== document.body) {
        const ds = node.dataset?.start;
        const dd = node.dataset?.duration;
        if (dd !== undefined) {
          const start = ds === undefined ? 0 : parseFloat(ds);
          const end = start + parseFloat(dd);
          if (!(t >= start && t < end)) return false;
        }
        node = node.parentElement;
      }
      return true;
    };

    const seen = [];
    document.querySelectorAll('*').forEach((el) => {
      if (el.children.length) return;
      const text = (el.textContent || '').trim();
      if (!text || text.length > 80) return;
      if (!inWindow(el)) return;
      let opacity = 1;
      let node = el;
      while (node && node !== document.body) {
        const cs = getComputedStyle(node);
        opacity *= parseFloat(cs.opacity || '1');
        if (cs.visibility === 'hidden' || cs.display === 'none') opacity = 0;
        node = node.parentElement;
      }
      const r = el.getBoundingClientRect();
      if (opacity > 0.05 && r.width > 0 && r.height > 0) seen.push(text);
    });
    return [...new Set(seen)];
  }, seconds);

  const out = [];
  for (const item of req.times) {
    out.push({
      label: item.label,
      before: await visibleAt(item.before),
      after: await visibleAt(item.after),
    });
  }
  await browser.close();
  console.log(JSON.stringify(out));
})();
"""

result = subprocess.run(
    ["node", "-e", script], input=request, capture_output=True, cwd=ROOT
)
if result.returncode != 0:
    sys.exit(result.stderr.decode() or "probe failed")

data = json.loads(result.stdout.decode())
OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
print(f"wrote {OUT.relative_to(ROOT)}: {len(data)} cases")
