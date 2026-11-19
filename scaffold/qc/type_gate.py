#!/usr/bin/env python3
"""
The type gate for HyperFrames. Fails until a preset is chosen.

    python3 qc/type_gate.py

Why this exists: the scaffold used to hardcode one pairing, so every film from it
used that pairing regardless of topic. Options do not change behaviour; a
required choice with a failing gate does.

Checks:
  1. BITS_TYPE_PRESET in index.html is set and is a real key
  2. the three roles are three different families
  3. this folder did not already use the same preset (unless BITS_REUSE_TYPE=1)
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
PRESETS_JS = ROOT / "js" / "type-presets.mjs"
RECORD = ROOT / "work" / "type-used.json"

findings = []

if not INDEX.exists():
    sys.exit("missing index.html")
if not PRESETS_JS.exists():
    sys.exit("missing js/type-presets.mjs")

src = PRESETS_JS.read_text()

# valid keys, from the PRESETS object
keys = re.findall(r"^  '?([a-z-]+)'?: \{", src, re.M)

# the chosen key, from index.html
m = re.search(r"window\.BITS_TYPE_PRESET\s*=\s*['\"]([^'\"]*)['\"]", INDEX.read_text())
chosen = m.group(1) if m else ""

if not m:
    findings.append("BITS_TYPE_PRESET is not set in index.html.")
elif not chosen:
    findings.append(
        "BITS_TYPE_PRESET is empty. Pick the topic's register in stage 4:\n    "
        + "\n    ".join(keys)
    )
elif chosen not in keys:
    findings.append(
        f'BITS_TYPE_PRESET "{chosen}" is not a preset. Valid keys:\n    '
        + "\n    ".join(keys)
    )

# the three roles must differ
if chosen in keys:
    block = src[
        src.index(f"'{chosen}': {{")
        if f"'{chosen}': {{" in src
        else src.index(f"{chosen}: {{") :
    ]
    body = block[: block.index("when:")]
    fams = re.findall(r"(?:display|meta|accent):\s*'([^']+)'", body)
    if len(fams) == 3:
        if len(set(fams)) == 1:
            findings.append(
                f'preset "{chosen}" uses one family for all three roles ({fams[0]}).'
            )
        elif len(set(fams)) == 2:
            findings.append(
                f'preset "{chosen}" reuses a family across roles ({", ".join(fams)}).'
            )

# no repeat inside one folder
previous = None
if RECORD.exists():
    try:
        previous = json.loads(RECORD.read_text()).get("preset")
    except Exception:
        previous = None

if previous and previous == chosen and os.environ.get("BITS_REUSE_TYPE") != "1":
    findings.append(
        f'this folder already used "{chosen}". A series should not repeat its register:\n'
        "    pick a different preset, or set BITS_REUSE_TYPE=1 if repeating is deliberate."
    )

if findings:
    print("\n".join(findings))
    sys.exit(1)

RECORD.parent.mkdir(parents=True, exist_ok=True)
RECORD.write_text(json.dumps({"preset": chosen}, indent=1))
print(f"type gate OK: {chosen}")
