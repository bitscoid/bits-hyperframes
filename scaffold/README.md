# Scaffold

Copied into a new project folder, then edited in place.

```bash
cp -r <skill>/scaffold/. ./tiga-mitos-otak/
cd tiga-mitos-otak
mkdir -p assets audio renders work   # only what you will fill
npx hyperframes browser ensure   # once per machine, 685 MB
python3 qc/type_gate.py          # fails until a type register is set
npx hyperframes check            # must pass before any render
npx hyperframes render --output work/render-raw.mp4 --workers=4
```

What each file is:

| File | Role |
|---|---|
| `index.html` | the composition: markup, CSS custom properties, the GSAP timeline |
| `compositions/` | optional sub-compositions, one scene each |
| `js/type-presets.mjs` | the eight registers; the chosen key lives in `index.html` |
| `js/apply-type-preset.js` | reads `window.BITS_TYPE_PRESET`, sets the font variables |
| `qc/make_sync_probe.py` | samples the composition, writes `work/sync-probe.json` |
| `qc/sync_gate.py` | compares the probe against the word times, exits 1 on a finding |
| `qc/type_gate.py` | fails until a register is chosen, resolvable, and consistent |
| `qc/sync-cases.json` | `{text, t_vo}` pairs the gate checks; ships empty, must be filled per film |
| `qc/safe_band.py` | asserts the portrait content box and action rail in `GUIDE.md` §2; runs in ms, no browser |

`qc/sync-cases.json` is the **only** source of sync cases here — this engine has no
`cue.ts`, so the gate cannot derive them. It ships empty on purpose: every keyword the film
shows needs an entry, and `qc/sync_gate.py` **refuses an empty probe** rather than report a
green run that checked nothing.

```json
[{"text": "ngantuk", "t_vo": 0.55}, {"text": "6 jam", "t_vo": 6.46}]
```

`t_vo` is seconds into the voiceover; the probe adds `vo_delay` and samples at -0.15 s and
+0.10 s around it.

## The type register

`index.html` sets `window.BITS_TYPE_PRESET` in its `<head>`, above `js/apply-type-preset.js`,
which reads it and writes `--font-display`, `--font-meta`, `--font-accent` and their weights.
It ships empty: the apply script throws on an empty key, and `qc/type_gate.py` reports the same
thing earlier with the list of valid keys. Set it once per film from the topic's register.

Every family the presets name is declared statically with `@font-face` in `index.html`, under
the name the font declares — `Baloo 2`, not `Baloo2`. `check` lints that file and not the DOM,
which is why the declarations are there and not in the script.

## What this scaffold does NOT decide

There is no progress bar, no card position, no corner label, no fixed beat count
and no type preset. Each of those was a default here once, and each one made every
film from this scaffold look like the last. They are now decisions you make per
film, with the reasons in `references/GUIDE.md` §6.

## The three rules this scaffold follows

1. **One paused timeline, registered.** `window.__timelines['main'] = gsap.timeline({paused: true})`.
   `window.__hf = {seek(t)}` renders a **static video with no error** — measured: the test
   element sat at x=319 px in every frame.

2. **Content sits in one organic box, and the sides are symmetric.** On 1080×1920 that is
   **x 54..1026, y 250..1536** — 13% top, 20% bottom, 5% on both sides. 972×1286, **60% of the
   frame**, centre x 540 / y 893: horizontally the frame centre, so ordinary centring works;
   vertically 67 px high because the platforms stack their UI at the bottom.

   The bottom is the widest margin because that is where every vertical platform puts its UI —
   caption, username, audio ticker, progress bar, OS gesture bar — while the top carries only a
   header.

   One asymmetry survives, and it is not a margin: the **action rail** (like / comment / share /
   audio) sits down the lower right. Below **55% of the height** (`y > 1056`) the right edge
   pulls in to **88%** (`x ≤ 950`). Above that line the full width is free, so a headline across
   the top half can run edge to edge. Anything that must be read stays above y 1382 (28% from
   the bottom, clear of a two-line caption).

   `npx hyperframes check` reports a different box (`x 120..780, y 240..1260`):
   `@hyperframes/core/dist/safeAreas.js` is titled *"Vertical-ad guides"*, and its 35% bottom is
   a CTA button, legal line and shop card that an organic post never draws. Treat `check`
   findings outside the organic box as **advisory**.

   Backgrounds and meaningless shapes may bleed past the box, but keep the 4% edge.

3. **One element per word, not a block behind it.** A word over an accent card is a single
   element with `background`, `color` and `padding`. Measured: with the card as a sibling,
   the contrast gate read the page background and reported 1.01:1 for legible text.

Two more, from the render:

- **Drift must last the whole beat.** A drift that stops after 1 s leaves identical frames;
  the encoder reports a freeze and the contact sheet shows duplicates.
- **`data-duration` comes from the script, not the cap.** A 9 s script in a 60 s composition
  is 87% dead.

## Before the first render

Replace, in this order:

1. `:root` custom properties — the palette, the two font families.
2. `data-duration` on the root — from `audio/words.json`, last word + lead-in + 1.5 s tail.
3. The beat in the `<script>` — `start`, `wordAt`, `duration`. There is **one**
   demo beat, not a loop: write each beat for its own content.
4. Where its elements sit. Positions in the scaffold are placeholders — vary the
   zone between neighbours (left / centre / right / edge / full). And there is no
   meta label unless you add one: a label in the same corner of every beat is one
   of the three template tells in `references/GUIDE.md` §6.
5. `<audio src="assets/voiceover.wav">` — the narration you actually have.

Then:

```bash
npx hyperframes check                  # lint, runtime, layout, motion, contrast, craft, audio
python3 qc/make_sync_probe.py          # needs audio/words.json
python3 qc/sync_gate.py
python3 qc/safe_band.py                # box constants still match the sources
```

`check` enforces the *ad* box, which is not the box this scaffold designs to. To enforce the
organic box as well, pass it as a caption zone — the zone is the **forbidden** area, so use the
margins, not the box: 13% top, 20% bottom, and the rail column on the right below 55%.

```bash
npx hyperframes check --caption-zone "x0=0;y0=0;x1=1;y1=.13;severity=error"
npx hyperframes check --caption-zone "x0=0;y0=.80;x1=1;y1=1;severity=error"
npx hyperframes check --caption-zone "x0=.88;y0=.55;x1=1;y1=1;severity=error"
```

`check` reports every text with its exact bbox and the platform that flagged it — against the
**ad** box, which is not the box this scaffold designs to. A finding there is not a defect for
organic work; check the bbox against `x 54..1026, y 250..1536` (right edge `x ≤ 950` below
`y 1056`) before changing anything. The sync gate proves each keyword appears at its spoken
word and not before.

## Files the scaffold does not create

`assets/`, `audio/`, `renders/`, `work/` are created when there is something to put in them.
An empty `assets/` is a lie about the project's contents.

The narration and the ASR output are yours to supply:

- `assets/voiceover.wav` — the recording, or the TTS output
- `audio/words.json` — `{vo_delay, segments}`; the sync gate needs it
