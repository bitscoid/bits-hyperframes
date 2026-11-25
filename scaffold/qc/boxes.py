#!/usr/bin/env python3
"""Sweep every text box at fine time steps and report the two layout defects
`hyperframes check` samples too sparsely to catch.

Copy into the project as qc/boxes.py and run from the project root:

    python3 qc/boxes.py [step_seconds]      # default 0.2

Why this exists: `check`'s layout section takes a handful of samples (~9 on a
60 s film), so a real overlap between two beats can sit between two samples and
ship. Measured on a 47 s portrait film: `check` returned 0 errors while a 0.1 s
sweep found three lasting collisions — two display lines that wrapped onto a
second line covering the beat below, and a 230 px number sitting on the line
above it.

Two measurement rules, both learned the hard way:

  * Read the GLYPH box, not the element box. A left-aligned block with
    `width: 900px` holding 700 px of ink reports a 900 px box and looks like a
    violation while the ink is comfortably inside. `Range.selectNodeContents`
    gives the ink extent, and it is what `check` reports too. Using the element
    box produces a page of false findings and hides the real one.
  * A finding lasting one sample is an entrance tween (a `scale: 2.4` slam grows
    the glyph box for ~0.1 s). The report separates lasting from momentary rows;
    judge the lasting ones.

A text whose `width` is smaller than its string wraps to a second line at any
font size, and that is the most common cause of this defect. Fix it by sizing the
line to fit — fewer px, or the string cut — not by nudging the neighbour.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2

# Same constants as qc/safe_band.py — GUIDE.md §2. Portrait only; a landscape
# film keeps the plain 4% edge and title-safe 10% instead.
BOX = dict(x0=54, x1=1026, y0=250, y1=1536, rail_y=1056, rail_x=950, read_y1=1382)

html = INDEX.read_text()
m = re.search(r'data-duration="([0-9.]+)"', html)
if not m:
    sys.exit("index.html has no root data-duration")
DUR = float(m.group(1))
times = [round(i * STEP, 2) for i in range(int(DUR / STEP) + 1)]

SCRIPT = r"""
const fs = require('node:fs');
const {execSync} = require('node:child_process');
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
const bases = [path.join(process.cwd(), 'node_modules')];
try { bases.push(execSync('npm root -g', {encoding: 'utf8'}).trim()); } catch (e) {}
for (const base of bases) {
  try { puppeteer = require(require.resolve('puppeteer-core', {paths: [base]})); break; } catch (e) {}
}
if (!puppeteer) {
  console.error('puppeteer-core not found. Symlink it from the npx cache:\n' +
    '  ln -sfn $(dirname $(find ~/.npm/_npx -maxdepth 6 -type d -name puppeteer-core | head -1)) node_modules');
  process.exit(2);
}
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
    {timeout: 20000});
  await page.evaluate(() => document.fonts.ready);
  const out = [];
  for (const t of req.times) {
    const boxes = await page.evaluate((tt) => {
      Object.keys(window.__timelines).forEach((n) => window.__timelines[n].totalTime(tt, false));
      const inWindow = (el) => {
        let node = el;
        while (node && node !== document.body) {
          const dd = node.dataset && node.dataset.duration;
          if (dd !== undefined) {
            const start = node.dataset.start === undefined ? 0 : parseFloat(node.dataset.start);
            if (!(tt >= start && tt < start + parseFloat(dd))) return false;
          }
          node = node.parentElement;
        }
        return true;
      };
      const res = [];
      document.querySelectorAll('[data-qc]').forEach((el) => {
        if (el.children.length) return;
        const text = (el.textContent || '').trim();
        if (!text) return;
        if (!inWindow(el)) return;
        let op = 1;
        let node = el;
        while (node && node !== document.body) {
          const cs = getComputedStyle(node);
          op *= parseFloat(cs.opacity || '1');
          if (cs.visibility === 'hidden' || cs.display === 'none') op = 0;
          node = node.parentElement;
        }
        if (op <= 0.05) return;
        let g = el.getBoundingClientRect();
        try {
          const range = document.createRange();
          range.selectNodeContents(el);
          const rb = range.getBoundingClientRect();
          if (rb.width) g = rb;
        } catch (e) {}
        res.push({text, role: el.dataset.qc, x: g.left, y: g.top, w: g.width, h: g.height});
      });
      return res;
    }, t);
    out.push({t, boxes});
  }
  await browser.close();
  console.log(JSON.stringify(out));
})();
"""

request = json.dumps({"composition": str(INDEX), "times": times}).encode()
result = subprocess.run(["node", "-e", SCRIPT], input=request, capture_output=True, cwd=ROOT)
if result.returncode != 0:
    sys.exit(result.stderr.decode()[:2000])
data = json.loads(result.stdout.decode())

safe, over = [], []
for frame in data:
    t = frame["t"]
    boxes = [b for b in frame["boxes"] if b["w"] and b["h"]]
    for b in boxes:
        x2, y2 = b["x"] + b["w"], b["y"] + b["h"]
        why = []
        if b["x"] < BOX["x0"] - 1 or x2 > BOX["x1"] + 1:
            why.append("x %.0f..%.0f" % (b["x"], x2))
        if b["y"] < BOX["y0"] - 1 or y2 > BOX["y1"] + 1:
            why.append("y %.0f..%.0f" % (b["y"], y2))
        if y2 > BOX["rail_y"] and x2 > BOX["rail_x"] + 1:
            why.append("right edge %.0f below the rail line" % x2)
        if b["role"] in ("display", "readable", "caption") and y2 > BOX["read_y1"] + 1:
            why.append("below the read line: y2 %.0f" % y2)
        if why:
            safe.append((t, b["text"], "; ".join(why)))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, c = boxes[i], boxes[j]
            ox = min(a["x"] + a["w"], c["x"] + c["w"]) - max(a["x"], c["x"])
            oy = min(a["y"] + a["h"], c["y"] + c["h"]) - max(a["y"], c["y"])
            if ox > 2 and oy > 2:
                over.append((t, a["text"], c["text"], round(ox), round(oy)))


def group(rows, extra_index):
    agg = {}
    for row in rows:
        key = (row[1], row[2])
        e = agg.setdefault(key, [row[0], row[0], 0, row[extra_index:]])
        e[0] = min(e[0], row[0])
        e[1] = max(e[1], row[0])
        e[2] += 1
    return agg


print("samples: %d times, step %ss" % (len(times), STEP))
for label, rows, extra_index in (("outside the safe box", safe, 2), ("text over text", over, 3)):
    agg = group(rows, extra_index)
    print("%s: %d findings, %d distinct" % (label, len(rows), len(agg)))
    for key, (t0, t1, n, extra) in sorted(agg.items(), key=lambda kv: -kv[1][2]):
        tag = "LASTING" if n >= 3 else "momentary (entrance/exit)"
        tail = " (%sx%s px)" % (extra[0], extra[1]) if len(extra) == 2 else " -> " + extra[0]
        print('  [%s, %d samples, t=%s..%ss] "%s"%s' % (tag, n, t0, t1, key[0], tail))
print("judge only the LASTING rows: fix them, or write the reason beside the beat.")
