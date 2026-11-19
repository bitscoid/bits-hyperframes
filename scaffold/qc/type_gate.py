#!/usr/bin/env python3
"""
The type gate for HyperFrames. Fails until a preset is chosen.

    python3 qc/type_gate.py

Why this exists: the scaffold used to hardcode one pairing, so every film from it
used that pairing regardless of topic. Options do not change behaviour; a
required choice with a failing gate does.

Fails on:
  1. window.BITS_TYPE_PRESET in index.html is unset, or is not a known key
  2. the chosen preset puts one family in more than one role
  3. a family the preset names is neither declared by an @font-face in
     index.html nor bundled by HyperFrames — it would render in a fallback and
     nothing else would catch it
  4. the table in js/type-presets.mjs and the copy in js/apply-type-preset.js
     disagree, about a key, a family or a weight. The copy is what the page
     actually applies, so a drift means the preset you chose is not the preset
     that renders.

Warns, never fails, on repeating the previous run's preset in this folder: a
rerun is the normal case, and "this series is repeating itself" is a judgement
about a series, which one folder cannot see.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
PRESETS_MJS = ROOT / "js" / "type-presets.mjs"
PRESETS_JS = ROOT / "js" / "apply-type-preset.js"
RECORD = ROOT / "work" / "type-used.json"

# Families HyperFrames ships by name, so they need no @font-face of their own.
# Everything else the presets name must be declared in index.html.
BUNDLED = {
    "Inter",
    "Montserrat",
    "Outfit",
    "Nunito",
    "Oswald",
    "League Gothic",
    "Archivo Black",
    "Space Mono",
    "IBM Plex Mono",
    "JetBrains Mono",
    "EB Garamond",
    "Playfair Display",
    "Source Code Pro",
    "Noto Sans JP",
    "Roboto",
    "Open Sans",
    "Lato",
    "Poppins",
}

findings = []
warnings = []

for path in (INDEX, PRESETS_MJS, PRESETS_JS):
    if not path.exists():
        sys.exit(f"missing {path.relative_to(ROOT)}")

index = INDEX.read_text()
mjs = PRESETS_MJS.read_text()
js = PRESETS_JS.read_text()

# --- the table in js/type-presets.mjs ------------------------------------------
# Blocks start at `  key: {` / `  'key': {` and run to the closing `  },`.
blocks = re.split(r"^  '?([a-z-]+)'?: \{\n", mjs, flags=re.M)
table = {}
for name, body in zip(blocks[1::2], blocks[2::2]):
    body = body.split("\n  },")[0]
    fams = dict(re.findall(r"^(?:    )(display|meta|accent):\s*'([^']+)'", body, re.M))
    weights = dict(
        re.findall(
            r"^(?:    )(displayWeight|metaWeight|accentWeight):\s*(\d+)", body, re.M
        )
    )
    table[name] = {
        "families": [fams.get("display"), fams.get("meta"), fams.get("accent")],
        "weights": [
            weights.get("displayWeight"),
            weights.get("metaWeight"),
            weights.get("accentWeight"),
        ],
    }

if not table:
    findings.append("js/type-presets.mjs declares no presets.")
    print("\n".join(findings))
    sys.exit(1)

# --- the copy the page actually applies ---------------------------------------
applied = {}
for line in js.splitlines():
    m = re.match(
        r"\s*'?([a-z-]+)'?:\s*\{\s*display:\s*'([^']+)',\s*dw:\s*(\d+),"
        r"\s*meta:\s*'([^']+)',\s*mw:\s*(\d+),\s*accent:\s*'([^']+)',\s*aw:\s*(\d+)",
        line,
    )
    if m:
        key, disp, dw, meta, mw, accent, aw = m.groups()
        applied[key] = {"families": [disp, meta, accent], "weights": [dw, mw, aw]}

for key in sorted(set(table) | set(applied)):
    if key not in applied:
        findings.append(
            f'"{key}" is in js/type-presets.mjs but not applied by js/apply-type-preset.js.'
        )
    elif key not in table:
        findings.append(
            f'"{key}" is applied by js/apply-type-preset.js but not declared in js/type-presets.mjs.'
        )
    elif table[key] != applied[key]:
        findings.append(
            f'"{key}" differs between the two tables.\n'
            f"    js/type-presets.mjs    : {table[key]}\n"
            f"    js/apply-type-preset.js: {applied[key]}"
        )

# --- the chosen key -----------------------------------------------------------
m = re.search(r"window\.BITS_TYPE_PRESET\s*=\s*['\"]([^'\"]*)['\"]", index)
chosen = m.group(1) if m else ""

if not m:
    findings.append("window.BITS_TYPE_PRESET is not set in index.html.")
elif not chosen:
    findings.append(
        "window.BITS_TYPE_PRESET is empty. Pick the topic's register in stage 4:\n    "
        + "\n    ".join(sorted(table))
    )
elif chosen not in table:
    findings.append(
        f'window.BITS_TYPE_PRESET "{chosen}" is not a preset. Valid keys:\n    '
        + "\n    ".join(sorted(table))
    )

# --- the three roles, and whether their faces resolve -------------------------
declared = set(re.findall(r"@font-face\s*\{[^}]*font-family:\s*'([^']+)'", index))

if chosen in table:
    fams = table[chosen]["families"]
    if len(set(fams)) < 3:
        findings.append(
            f'preset "{chosen}" reuses a family across roles ({", ".join(fams)}).'
        )
    for fam in fams:
        if fam and fam not in BUNDLED and fam not in declared:
            findings.append(
                f'preset "{chosen}" names "{fam}", which is neither bundled nor declared by an\n'
                f"    @font-face in index.html — it would render in the fallback. Declare it, or\n"
                f"    correct the name to what the font itself declares."
            )

# --- repeating the previous run, advisory only --------------------------------
previous = None
if RECORD.exists():
    try:
        previous = json.loads(RECORD.read_text()).get("preset")
    except Exception:
        previous = None
if previous and previous == chosen:
    warnings.append(
        f'this folder already ran with "{chosen}". Reruns are fine; a new film in the\n'
        "    same series should pick a different register."
    )

if warnings:
    for w in warnings:
        print(f"note: {w}")

if findings:
    print("\n".join(findings))
    sys.exit(1)

RECORD.parent.mkdir(parents=True, exist_ok=True)
RECORD.write_text(json.dumps({"preset": chosen}, indent=1))
print(f"type gate OK: {chosen}")
