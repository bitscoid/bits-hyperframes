<div align="center">

# 🎬 BITS Motion — HyperFrames

**Turn a single topic into a finished motion-graphics video.**

No storyboard. No editing advice. A rendered MP4 you can publish.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Format](https://img.shields.io/badge/output-MP4%20H.264%20%2B%20AAC-blue)
![Frame rate](https://img.shields.io/badge/fps-30%20CFR-informational)
![Duration](https://img.shields.io/badge/duration-60s%20portrait%20%7C%20300s%20landscape-brightgreen)
![Docs](https://img.shields.io/badge/docs-English%20only-lightgrey)

</div>

---

## ✨ What it does

Give it a topic. It writes the voiceover script, gathers your assets, syncs every word to the picture, renders the video, and proves the result with real numbers.

```
topic ──► script ──► voice ──► word timing ──► scenes ──► MP4 ──► verified
```

The output is an **MP4 (H.264 + AAC, 30 fps, constant frame rate)** whose length is derived from the voiceover, capped by orientation:

| Orientation | Cap | Target |
|---|---|---|
| Portrait `1080×1920` | **60 s** | Reels / TikTok / Shorts |
| Landscape `1920×1080` | **300 s** (5 min) | YouTube explainer |

Longer only when you ask. Orientation is chosen in stage 1, before the script is written, because it sets the cap; a supplied reference must match that orientation and never changes it. Without an answer it asks once, then defaults to **1920×1080** landscape.

---

## 🚀 Quick start

```bash
# 1. install into your agent's skill directory
git clone https://github.com/bitscoid/bits-hyperframes.git \
  ~/.config/opencode/skills/bits-hyperframes

# 2. check the toolchain (node >= 22, ffmpeg, HyperFrames browser)
node -v
ffmpeg -version | head -1
npx hyperframes --version
npx hyperframes browser ensure

# 3. ask for a video
"buatkan motion graphic tentang kenapa kopi bikin ngantuk"
```

That's the whole interface. No config file, no CLI flags, no build step. The full environment probe — ASR, fonts, network, API key — is `references/RENDER.md` §1.

---

## 🧭 Where it runs, and what a full run looks like

### Any directory, one folder per video

Run the agent from whatever directory you want the projects to live in — the skill creates
projects in the **current directory** (flat, no wrapper folder), so the location stays dynamic.
You create nothing first. Stage 1 derives a slug from the topic title, tells you the slug, then
creates that folder right there and works inside it.

```
<current directory>/
├── tiga-mitos-otak/      ← created by run 1
└── kopi-dan-tidur/       ← created by run 2
```

Three rules govern collisions:

| Situation | What happens |
|---|---|
| Same topic again | Continues in the existing folder and overwrites the same file names — a revision, not a copy |
| Different topic, same slug | Stops and asks before touching anything |
| Anything else | Creates a new folder, never `-2`, `-3` or a date suffix |

Nothing is shared between projects: no global config, no state file, no daemon. Two folders can
be rendered side by side and cannot affect each other.

### The run, stage by stage

| Stage | What happens | What you see |
|---|---|---|
| 1 · Script | Orientation and cap decided first, because the cap sets the script length. Script written with `[Hook]`/`[Inti N]`/`[Penutup]` labels | The script in Indonesian, with format and word count |
| 2 · Assets | One message asking for recording, music, reference, images, orientation, captions — **once** | Six numbered questions, all optional except the voice |
| 3 · Readiness | Confirms, or fills gaps from documented defaults | One line, or a single clarifying question |
| 4 · Measure | Real voiceover duration, ASR word timing, reference read, font choice | The style brief and the exact duration |
| 5 · Timeline | One absolute-time table | Nothing — internal planning |
| 6 · Build | Scene code, then render, then one `loudnorm` pass | Progress, then the raw file |
| 7 · QC | Gates measured from the exported file | The delivery numbers and `publish.txt` |

### End to end, with the commands

```bash
cd <your working directory>   # projects are created in the current directory
```

Then ask the agent, in Indonesian:

```
buatkan motion graphic tentang kenapa kopi bikin ngantuk
```

It replies with the script and, in the same message, the six asset questions. Answer them or
say `buat semuanya otomatis`. From there it creates `./kenapa-kopi-bikin-ngantuk/` in the current directory,
fills it, and runs the build:

```bash
cd ./kenapa-kopi-bikin-ngantuk
cp -r <skill>/scaffold/. .        # once per project, before the first render
cp node_modules/gsap/dist/gsap.min.js assets/vendor/   # or drop the vendored file in by hand
npx hyperframes browser ensure
npx hyperframes check                              # must pass
npx hyperframes render --output work/render-raw.mp4 --workers=4
ffmpeg -y -i work/render-raw.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v copy -c:a aac -b:a 192k -ar 48000 output/kenapa-kopi-bikin-ngantuk.mp4
python3 qc/safe_band.py                            # box constants match the sources
python3 qc/make_sync_probe.py && python3 qc/sync_gate.py
```

| Path | What it is |
|---|---|
| `output/<slug>.mp4` | the video |
| `output/publish.txt` | caption, description, hashtags |
| `index.html` | the whole visual design |
| `audio/words.json` | the timing table, durable |
| `qc/` | the sync gate |

Re-rendering in the same folder produces the same video from the same inputs.

## 🧠 Design philosophy

This skill is **rules, not a template.**

| Layer | Divided how |
|---|---|
| 🎯 **Accuracy** | Measurable and reported with numbers — timing follows the spoken word, text stays in the safe area, cap height meets threshold, contrast meets WCAG, no dead air inside the narration, mix loudness in band, frame count is exact. Two are hard requirements: frame count equals duration × 30 in the exported file, and the finished loudness/tail floor |
| 🎨 **Taste** | Entirely yours — palette, scene count, transitions, typeface, mood, motion rhythm |

The test applied to every rule before it entered these documents:

> **① Can it be proven by measurement?** &nbsp;and&nbsp; **② Does it leave creative choice alive?**

A rule that passes ① but fails ② is a restriction, not a standard. Rejected examples that live on as warnings in the docs: *"overshoot must be 1.16"*, *"the hook must be 3 seconds"*, *"scenes must be 2–6 seconds"*.

**One skill, no shared library.** The agent writes the render code and the QC checks per project. Every video gets code shaped to its own content instead of being squeezed into a shared engine.

**Vision routing.** Every image call — asset verification, reference frames, QC contact sheets — is attempted by the main model first. Provider metadata is not trusted: a model that advertises `vision: true` can still return empty content. On a real fail (`content` empty, refusal, or an `[image omitted: ...]` placeholder) that one call goes to the `vision` subagent, which owns a failover chain of models proven to read images. Text, timing, scene code, rendering and every number stay in the main session. Detail in `SKILL.md` → *Vision routing*, probe in `RENDER.md` §1.

---

## 🎯 What it actually enforces

<details open>
<summary><b>⏱ Timing</b></summary>

Word timing comes from **automatic speech recognition with per-word timestamps**, not from counting words. Every text appearance reads from one absolute-time table, and a sync gate proves no text appears before its word.

Word-count estimation is the documented fallback, clearly labelled as approximate.

</details>

<details open>
<summary><b>📐 Typography geometry</b></summary>

- Safe area: **4%** from every edge for anything that carries meaning. Portrait adds one content box: **13% top / 20% bottom / 5% on both sides** — `x 54..1026, y 250..1536` on 1080×1920, 972×1286, **60% of the frame**, horizontally centred. Below **55% of the height** the action rail (like/comment/share) pulls the right edge to **88%** (`x ≤ 950`). Text that must be read stays above **28% from the bottom** (y ≤ 1382). Landscape keeps 4%, with **10%** title-safe for readable text
- **Cap height**, not font size: **4%** of the short side for primary text, **2.5%** for supporting text (1080p landscape → 43 px / 27 px). Measured once per face, never from a string's box
- Centring is measured from the rendered box, never left to `text-align` alone
- Text collision checked by **coverage of the smaller box (< 0.02)**, not IoU — IoU 0.16 lets a 20% line overlap pass

</details>

<details open>
<summary><b>🌗 Contrast</b></summary>

Thresholds are tied to the text's **role**, not its pixel size — small moving text reads far worse than static text of the same size.

- Primary text: **3.0:1**
- Supporting text: **4.5:1**

Measured with the WCAG formula: a light salmon `(238,150,130)` on cream `(245,241,234)` reaches only **2.00:1** — a hard fail; darkening the accent to `(166,82,70)` reaches **4.76:1** and passes for supporting text. The docs ship a `fit_accent()` helper that walks lightness in **both directions** and raises when the target is unreachable, so the palette is chosen by measurement rather than by eye.

</details>

<details open>
<summary><b>🔊 Audio</b></summary>

- Voiceover and music mixed in the composition, then **one** `loudnorm` pass on the export
- Music **ducked under speech** with a fading `volume` curve that returns to its bed level, then faded to a floor at the end
- Audio gate is **windowed**: no dead air inside the speech region, and with music the tail must still carry sound
- Finished mix measured: **I ∈ [−17, −14] LUFS**, true peak ≤ −1 dBTP

Measured trap that produced the loudness rule: HyperFrames mixes but does not master — a sine at 0.8 volume exported at **−34.5 LUFS**, and one `loudnorm` pass on the export brought it to **−16.0**. The video is never re-encoded (`-c:v copy`).

</details>

<details open>
<summary><b>🎞 Motion</b></summary>

Every second of video keeps at least one element moving. Verified with `freezedetect=n=0` — never the default `n=0.001` (about −60 dB), which false-positives on flat graphics. The 1 s lead-in before speech is exempt.

The exported frame count is asserted: it must equal duration × 30. A truncated render passes every visual check and only the metadata shows it.

The lower bound is the encoder, not taste: motion under ~10 px can be quantised away at CRF 18+, leaving identical frames.

</details>

<details>
<summary><b>🔁 Repetition gate (flags, never judges)</b></summary>

Scenes with the same structural signature get flagged so you can decide: *deliberate motif* or *coincidence to fix*. The gate forces that decision to be written down; it never homogenises the output.

Signatures are the `data-qc` boxes: same role, same size, same position on consecutive beats means the layout did not change. No pixels are read, so a dark theme with light text is not a special case.

</details>

---

## 📁 Project output

Each video becomes a self-contained folder:

```
tiga-mitos-otak/
├── script.txt              voiceover script, clean text, no labels
├── index.html              the whole visual design: markup, CSS, timeline
├── compositions/           optional sub-compositions, one scene each
├── qc/
│   ├── make_sync_probe.py  samples the composition
│   ├── sync_gate.py        compares against the word times
│   ├── safe_band.py        asserts the portrait box and action rail
│   └── sync-cases.json     texts the gate proves
├── audio/
│   └── words.json          word-level timing; DURABLE, never deleted
├── assets/
│   ├── voiceover.wav       narration, 48 kHz mono — the timing source
│   ├── music.wav           optional, 48 kHz
│   ├── image-01.png        first supporting image
│   ├── reference.mp4       style reference video
│   └── fonts/              every family the film uses, downloaded from Google Fonts
├── output/
│   ├── tiga-mitos-otak.mp4 deliverable; name equals folder name
│   ├── tiga-mitos-otak.srt subtitle track, optional
│   └── publish.txt         caption, description, hashtags
├── work/                   every intermediate file; safe to delete entirely
│   ├── render-raw.mp4      the render before loudness normalisation
│   ├── check/
│   ├── ref/                contact sheet + motion strips
│   └── voiceover-16k.wav   16 kHz mono, for speech recognition
└── .hyperframes/           engine artifacts: checks, snapshots, state
```

`audio/words.json` sits outside `work/` deliberately: it is the only derived file a revision cannot faithfully recreate (a fresh ASR pass returns ~±0.1 s different timestamps and desyncs a re-render). Everything else in `work/` rebuilds in one command, so `rm -rf work` loses nothing that matters.

`index.html` is the composition and the only entry point.
**Naming rule:** file and directory names are English kebab-case; file contents and every message to the user are Indonesian. The project folder and the video carry the topic slug so they stay meaningful in a file manager.

`rm -rf work` then re-render restores the whole video.

---

## 🛠 Requirements

| Need | Why |
|---|---|
| `ffmpeg` + `ffprobe` | rendering, measuring, verification |
| `node` >= 22 | runs the HyperFrames CLI |
| `hyperframes` 0.9.72 | the renderer and the QC gate |
| HyperFrames browser (685 MB) | `npx hyperframes browser ensure`, once |
| `whisper.cpp` **or** `faster-whisper` | word-level timing (optional, degrades to estimate) |
| `GEMINI_API_KEY` | optional TTS when you have no recording (Interactions endpoint) |
| `yt-dlp` | optional, downloading style references |

Verified on ffmpeg 7.1. Every ffmpeg behaviour cited in the docs was measured on a real render, not copied from documentation.

Frames are HTML, CSS and GSAP. The renderer seeks a paused timeline frame by frame, so a slow machine cannot drop a frame.

Measured on this machine: 60 s portrait takes **19 s**, 300 s landscape **69 s**. Workers past 6 mostly add memory — capture is already parallel inside the engine.

---

## 🧩 How the documents fit together

| File | Role |
|---|---|
| **`SKILL.md`** | the workflow — 7 stages, decision tables, ready-to-print user messages |
| **`references/GUIDE.md`** | creative direction — typography, animation, transitions, turning ideas into visuals |
| **`references/RENDER.md`** | engineering — environment, fonts, ffmpeg, and the QC gates |
| **`references/CRAFT.md`** | craft — the GSAP move vocabulary, curves per role, review flags |

The measured numbers live with the rule they protect; the creative freedoms live in `GUIDE.md`. Neither pretends to be the other.

---

## 🎨 Fonts

HyperFrames bundles 18 families by name (Inter, Montserrat, Poppins, Archivo Black, JetBrains Mono and more). Any other family is added with `@font-face` — the recipe is in `references/RENDER.md` §1:

```bash
curl -sL -o /tmp/font.ttf \
  "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
```

Then verifies it before use — under 10 KB means an HTML error page, not a font.

---

## ⚠️ Honest limits

- Music is **synthesised** unless you supply your own — a generated chord progression (pad, bass, arpeggio), not a composition
- Word timing is **approximate** when ASR is unavailable, and the delivery message says so
- The agent cannot watch the video; visual QC relies on extracted frames, contact sheets, and measured numbers
- Capped at **60 s portrait / 300 s landscape** — a five-minute explainer, not a documentary tool
- A 5-minute landscape render is 9000 frames; expect it to take longer than a short clip, and the script needs ~740 words at ~2.5 words/s
- Captions are **offered, not assumed**; burned-in captions are a separate style decision from kinetic typography
- Loudness of the finished mix is verified, but creative judgements (does the beat land, does the hook grip) stay yours

---

## 📄 License

[MIT](LICENSE) — use it, fork it, ship it.

<div align="center">

**BITS Creative** · built for agents that render, not just describe.

</div>