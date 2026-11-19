# Scaffold

Copied into a new project folder, then edited in place.

```bash
cp -r <skill>/scaffold/. ./tiga-mitos-otak/
cd tiga-mitos-otak
mkdir -p assets audio renders work   # only what you will fill
npx hyperframes browser ensure   # once per machine, 685 MB
npx hyperframes check            # must pass before any render
npx hyperframes render --output work/render-raw.mp4 --workers=4
```

What each file is:

| File | Role |
|---|---|
| `index.html` | the composition: markup, CSS custom properties, the GSAP timeline |
| `compositions/` | optional sub-compositions, one scene each |
| `qc/make_sync_probe.py` | samples the composition, writes `work/sync-probe.json` |
| `qc/sync_gate.py` | compares the probe against the word times, exits 1 on a finding |
| `qc/sync-cases.json` | `{text, t_vo}` pairs the gate checks, in voiceover seconds |

`qc/sync-cases.json` is the **only** source of sync cases here — this engine has no
`cue.ts`, so the gate cannot derive them. Every keyword the film shows needs an entry, or
nothing proves it lands after its word.

```json
[{"text": "ngantuk", "t_vo": 0.55}, {"text": "6 jam", "t_vo": 6.46}]
```

`t_vo` is seconds into the voiceover; the probe adds `vo_delay` and samples at -0.15 s and
+0.10 s around it.

## The three rules this scaffold follows

1. **One paused timeline, registered.** `window.__timelines['main'] = gsap.timeline({paused: true})`.
   `window.__hf = {seek(t)}` renders a **static video with no error** — measured: the test
   element sat at x=319 px in every frame.

2. **The safe band is the TikTok band.** On 1080×1920 that is x 120..780, y 240..1260,
   derived from `@hyperframes/core/dist/safeAreas.js`. Measured: left 110 flagged, left 130
   clean; top 240 flagged, top 300 clean; bottom 1240 flagged, bottom 1200 clean.
   It is the strictest of the three platforms, so fitting it fits Reels and Shorts.

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
3. The beats in the `<script>` — `start`, `wordAt`, `duration` per beat.
4. The card text and the meta labels.
5. `<audio src="assets/voiceover.wav">` — the narration you actually have.

Then:

```bash
npx hyperframes check                  # lint, runtime, layout, motion, contrast, craft, audio
python3 qc/make_sync_probe.py          # needs audio/words.json
python3 qc/sync_gate.py
```

`check` reports every out-of-band text with its exact bbox and the platform that flagged it.
The sync gate proves each keyword appears at its spoken word and not before.

## Files the scaffold does not create

`assets/`, `audio/`, `renders/`, `work/` are created when there is something to put in them.
An empty `assets/` is a lie about the project's contents.

The narration and the ASR output are yours to supply:

- `assets/voiceover.wav` — the recording, or the TTS output
- `audio/words.json` — `{vo_delay, segments}`; the sync gate needs it
