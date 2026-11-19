#!/usr/bin/env python3
"""
The sync gate for HyperFrames (RENDER.md §7).

Proves, for each case in qc/sync-cases.json, that a text is visible at its word
time and is not visible before it. Asymmetry is deliberate: 0.1 s late is
invisible, appearing early is a visible defect.

    python3 qc/make_sync_probe.py    # samples the composition -> work/sync-probe.json
    python3 qc/sync_gate.py          # compares

Why not read `hyperframes check --json`: it reports only *findings*. A clean
composition returns none, so `firstSeen` does not exist for text that behaves
correctly — and a gate that only works on broken films is useless.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "work" / "sync-probe.json"

if not PROBE.exists():
    sys.exit("missing work/sync-probe.json — run: python3 qc/make_sync_probe.py")

probe = json.loads(PROBE.read_text())
findings = []

for case in probe:
    text = case["label"]
    before, after = case.get("before", []), case.get("after", [])
    if text not in after:
        findings.append(f'missing or late: "{text}"')
    if text in before:
        findings.append(f'appears too early: "{text}"')

if findings:
    print("\n".join(findings))
    sys.exit(1)

print(f"sync gate OK: {len(probe)} texts")
