# Render and Verification — HyperFrames

Read this before building and rendering. All commands are examples — adapt filenames to the assets you actually have. Never run a command that depends on a tool you have not checked exists.

Everything here was verified against hyperframes 0.9.72, @hyperframes/engine 0.9.72, Chrome 158.0.8127.36 (`npx hyperframes browser ensure`), ffmpeg 7.1.5, Node 26, 34 vCPU, 24 GB RAM.

## Contents
1. Environment check
2. The render contract
3. Measuring and analysing the voiceover
4. Analysing a reference video
5. Building frames deterministically
6. Audio mixing and export
7. Verifying the exported file (sync, geometry, audio, loudness)
8. Self-made background music
9. Common traps
10. Cleanup after delivery

## 1. Environment check

Run this first and plan around the result:

```bash
node -v                                  # need >= 22
ffmpeg -version | head -1; ffprobe -version | head -1
npx hyperframes --version
npx hyperframes browser ensure           # once, downloads chrome-headless-shell
python3 -c "import faster_whisper; print('word-level ASR: available')" 2>/dev/null || echo "ASR: unavailable"
fc-list | head -20
[ -n "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY: present" || echo "GEMINI_API_KEY: absent"
which curl yt-dlp
```

The browser lives in `~/.cache/hyperframes/chrome/` (685 MB) and is separate from the npm
package. Without it every render fails at capture time.

### Vision capability (measured, never assumed)

Stages 4 and 7 need the model to open an image. Provider metadata is not evidence: on one
measured gateway, 15 of 72 models advertising `vision: true` returned an empty `content`
because the router stripped the image. Probe with one real image before relying on it:

```bash
mkdir -p work
ffmpeg -y -v error -f lavfi -i "color=c=white:s=800x400:d=1" \
  -vf "drawbox=x=40:y=40:w=200:h=200:color=blue:t=fill,drawbox=x=280:y=40:w=200:h=200:color=red:t=80,drawtext=text=X7-KILO:x=60:y=300:fontsize=48:fontcolor=black" \
  -frames:v 1 work/vision-probe.png
```

Pass = the model names `X7-KILO`, a blue square and a red ring. Fail = empty reply, a
refusal, or `[image omitted: ...]`.

- **Pass** → keep every image call in the main session.
- **Fail** → delegate that one call to the `vision` subagent.
- **Both fail** → say so and ask the user for a text description.

### Fonts — always downloaded into the project

**A film has three type roles, and they should not all share a family.** The pairing is
the design; one family for all three is what makes a video read as a template.

| Role | Carries | Typical register | CSS variable |
|---|---|---|---|
| **display** | the keyword, the number, the verdict | impact, or rounded for a light topic | `--font-display` |
| **meta** | labels, indices, chips, footnotes | mono, or small-caps serif | `--font-meta` |
| **accent** | an annotation, a scribble | handwriting, sparingly, never body | `--font-accent` |

**No font ships with this skill and no font is read from the machine.** There is no
bundled family list and no font cache: a film that resolves a font from the system
renders differently on another machine, after a rebuild, or in the cloud — and the
failure is silent, because the browser substitutes a fallback and reports nothing.

**One route only: download from Google Fonts into `assets/fonts/`, then declare it.**

```bash
mkdir -p assets/fonts
curl -sL -o assets/fonts/Fraunces.ttf \
  "https://github.com/google/fonts/raw/main/ofl/fraunces/Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf"
```

```html
<style>
  @font-face {
    font-family: 'Fraunces';
    src: url('assets/fonts/Fraunces.ttf') format('truetype');
  }
</style>
```

Rules that the gates enforce:

- **Every family in the chosen preset needs its own `@font-face` and its file in
  `assets/fonts/`.** `qc/type_gate.py` fails otherwise; `npx hyperframes check` fails with
  `font_family_without_font_face`.
- **Name the family exactly as the font declares it** — `Baloo 2`, not `Baloo2`. A wrong
  name loads the file and renders the fallback in silence.
- **Never use `src: local(...)`.** It works on the machine that has the font and fails
  everywhere else; lint reports `font_face_local_only`.
- **Verify the download before building.** Under 10 KB on disk is an HTML error page, not a
  font. `document.fonts.check('700 96px Fraunces')` must return true in the render browser.

**Pick the family from the topic, not from what is easy to fetch.** Read the reference's
type register first, match a family to the topic's character, and state the choice and
reason in one sentence. If the family you want is not on Google Fonts, choose another that
is. Do not start building with a font that merely exists and then bend the design toward
it; that order produces generic work.

## 2. The render contract

HyperFrames seeks a paused timeline frame by frame. Nothing plays in real time, so a slow
machine cannot drop frames.

```
index.html              the root composition and its data-* timing attributes
compositions/           optional sub-compositions, one scene each
assets/                 voiceover.wav, music.wav, images, fonts
output/                output of `hyperframes render`
.hyperframes/           artifacts: checks, snapshots, state
```

```bash
npx hyperframes init <dir> --non-interactive --skip-skills --resolution portrait
npx hyperframes check          # lint + runtime + layout + motion + contrast + craft + audio
npx hyperframes render --output output/<slug>.mp4 --workers=4
```

**Choosing `--workers`.** Start at `4`. Capture is already parallel inside the engine, so
returns diminish fast: measured on a 60 s 1080×1920 film, 4→8 workers cut wall time by roughly
a quarter (33 s → 24 s), while 1 worker took nearly twice as long as 4 (61 s vs 33 s) and 2.5×
as long as 8. Past 8 the gain is noise. Every worker is a separate Chrome at roughly 256 MB, so
size the count against free RAM before you size it against vCPU: 6 on a 24 GB box is safe, 8 is
fine when little else is running. Expect ±20% run to run — repeat timings before you draw a
conclusion from one, and never benchmark on a loaded box.

Quality presets: `looks` is the default and is right for everything except the final file, where
`delivery` costs a few extra seconds for a slightly larger output. `draft` exists for checking
timing, not for delivery.

## 3. Measuring and analysing the voiceover

Duration:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "assets/voiceover.wav"
```

Word timing: **speech recognition first, word-count estimation last.** ~2.5 words/second
exists only to sanity-check script length, never to place text.

**A. whisper.cpp** — fastest on CPU, no Python. Install once per machine, outside the project,
so the binary and the 488 MB model are not copied per video:

```bash
# once
WHISPER_DIR="$HOME/.local/share/whisper.cpp"
git clone --depth 1 https://github.com/ggml-org/whisper.cpp "$WHISPER_DIR"
cmake -S "$WHISPER_DIR" -B "$WHISPER_DIR/build" && cmake --build "$WHISPER_DIR/build" -j
"$WHISPER_DIR"/models/download-ggml-model.sh small

# per video
"$WHISPER_DIR/build/bin/whisper-cli" \
  -m "$WHISPER_DIR/models/ggml-small.bin" \
  -f work/voiceover-16k.wav -l id -oj -of work/words
```

`-oj` writes `work/words.json`, which `work/` is deleted in §10. Copy it to the durable path
before anything else, converting whisper.cpp's millisecond offsets:

```bash
python3 - <<'PY'
import json
raw = json.load(open("work/words.json"))
segs = []
for t in raw["transcription"]:
    segs.append({
        "start": t["offsets"]["from"] / 1000,
        "end": t["offsets"]["to"] / 1000,
        "text": t["text"].strip(),
        "words": [{"word": w["text"].strip(),
                   "start": w["offsets"]["from"] / 1000,
                   "end": w["offsets"]["to"] / 1000}
                  for w in t.get("tokens", []) if w["text"].strip()],
    })
json.dump({"vo_delay": 1.0, "segments": segs},
          open("audio/words.json", "w"), ensure_ascii=False, indent=1)
print("wrote audio/words.json:", len(segs), "segments")
PY
```

Measured: 3 s of audio in 14.9 s, CPU only, `small` model.

**B. faster-whisper** (Python 1.2.1)

```bash
ffmpeg -v error -y -i "assets/voiceover.wav" -ar 16000 -ac 1 work/voiceover-16k.wav
```

```python
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe("work/voiceover-16k.wav", language=None, word_timestamps=True)
```

Take ASR output as-is even when the transcription is wrong — you need the word boundaries,
not the spelling. ASR error of ±0.1 s is invisible; word-count estimation can be off by 2 s.

Write to `audio/words.json`, the one artifact every later stage reads:

```python
import json
json.dump({
    "vo_delay": 1.0,
    "segments": [{"start": s.start, "end": s.end, "text": s.text,
                  "text_display": align_from_script(s),
                  "words": [{"word": w.word, "start": w.start, "end": w.end}
                            for w in s.words]} for s in segs]
}, open("audio/words.json", "w"), ensure_ascii=False, indent=1)
```

`text_display` is the sentence as `script.txt` spells it; the ASR `text` stays as recognised
because only its boundaries matter, and it must never reach a subtitle.

If the computed total exceeds the cap — **60 s portrait, 300 s landscape** — stop and ask.

### When there is no voiceover

1. **Gemini TTS** (needs a Gemini key). Models `gemini-3.8-flash-tts` and
   `gemini-3.8-flash-lite-tts` (separate quota). Endpoint `POST /v1beta/interactions`,
   style in `input[].content[].annotations[].style`, audio in `steps[].content[].data`.
   Build the payload with `json.dumps`, and strip `[Hook]` / `[Inti N]` / `[Penutup]`
   labels — the model reads text verbatim.

   **Keys rotate automatically — never hardcode one key.** Quota is per key *per
   model* (free tier ≈10 TTS requests/day). The shared helper returns every key in
   priority order — `$GEMINI_API_KEY`, then each `/root/.hermes/keys/*.key`, then
   `GEMINI_API_KEY` in `/root/.hermes/.env` — and the same set serves bits-affiliate,
   bits-motion, bits-hyperframes and bits-bang-motion:

   ```bash
   python3 /root/.hermes/keys/gemini_key.py     # how many keys are ready
   ```

   ```python
   import sys; sys.path.insert(0, "/root/.hermes/keys")
   from gemini_key import keys
   ```

   On `429` / `RESOURCE_EXHAUSTED` / `API_KEY_INVALID`, mark that key spent and try
   the next one before giving up. Add capacity by dropping `/root/.hermes/keys/<name>.key`
   (chmod 600). Never print a key value into logs — `key#N` is enough.
2. **No key / failure:** never fabricate a voice. Ask the user to record it.

## 4. Analysing a reference video

The reference comes from the user (file or URL) or from Pinterest. For a URL, download with
`yt-dlp "<url>" -o "assets/reference.mp4"`. Read it in four steps: a **contact sheet** for the
design layers, **motion strips** for the temporal ones, an eight-layer read, and a brief
written into `index.html`'s CSS custom properties.

A still cannot show easing, entry duration or text granularity.

```bash
REF="assets/reference.mp4"
RDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$REF")
DIMS=$(python3 -c "import math; d=max(float('$RDUR'),1); f=min(2.0, 60/d); c=max(1, round(d*f)); print(f'{f:.3f} {math.ceil(math.sqrt(c))}')")
FPS=${DIMS% *}; GRID=${DIMS#* }
mkdir -p work/ref
ffmpeg -i "$REF" -vf "fps=$FPS,scale=240:-1,tile=${GRID}x${GRID}" -frames:v 1 -update 1 work/ref/contact.png
```

A fixed `tile=6x5` at `fps=2` covers only the first **15 s** of any clip and then fails on the
remaining tiles. Size the grid from the duration.

### Motion strips around three cuts

```bash
ffmpeg -i "$REF" -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | cut -d: -f2 > work/ref/cuts.txt

awk 'NR==1{f=$1} {a[NR]=$1; n=NR}
     END{if(!n){print "no cuts found" > "/dev/stderr"; exit}
         printf "%s\n", f
         if(n>2) printf "%s\n", a[int((n+1)/2)]
         if(n>1) printf "%s\n", a[n]}' work/ref/cuts.txt > work/ref/pick.txt

while read -r T; do
  S=$(awk -v t="$T" 'BEGIN{x=t-0.5; if(x<0)x=0; printf "%.3f", x}')
  ffmpeg -ss "$S" -i "$REF" -t 1.5 -vf "fps=30,scale=200:-1,tile=15x3" \
    -frames:v 1 -update 1 "work/ref/strip-$T.png"
done < work/ref/pick.txt
```

`showinfo` writes at info level — `-v error` silences the very lines this pipeline greps.

### The eight-layer read

| Layer | What to read | Where it lands |
|---|---|---|
| **Palette** | roles, share of frame each holds, whether the accent marks one word or a field, shifts between chapters, texture | `:root` custom properties |
| **Typography** | title-to-meta ratio, families, tracking on caps, type used as an image | `.title`, `.word` rules |
| **Composition** | empty-space ratio, where the mass sits, layer count, full-bleed vs card | `left`/`top` values |
| **Graphic language** | shape vocabulary, corner radius, stroke weight, icon grid, texture | border-radius, borders |
| **Motion** | entry duration, easing shape, overshoot, what moves, text granularity | the GSAP timeline |
| **Rhythm** | cut distribution, event density per second, whether cuts land on speech | `data-start`/`data-duration` |
| **Sound** | whoosh / impact / riser vocabulary, silence as punctuation | `<audio>` tracks |
| **Attention** | what is on screen at 1.5 s, chapter system, withholding, callbacks | the beat list |

Two closing reads, both required:

- **Signature device.** The one or two things that are the reference's fingerprint. Write the
  principle, then use it differently.
- **Weakness.** What the reference does badly, so the build beats it.

The reference is a **floor, not a ceiling**: at least one decision must come from the topic.

### Finding a reference on Pinterest (when the user gives none)

If the user supplies none, searching is **mandatory before self-design** — the budget and
failure modes are in `SKILL.md` stage 3: ≥5 pin candidates across ≥2 searches as the floor,
~8 as the working target, one download attempt at a time, one line per failure.

Search `https://id.pinterest.com/search/pins/?rs=typed&q=motion+graphics+<topik>`, judge fit
not relevance, fall back to something loosely related, and only then design it yourself — and
say so. Filter: under 5 s or over 180 s, wrong aspect, no video stream.

**Aspect ratio, not resolution.** 720×1280 is a valid reference for 1080×1920; orientation
must match, aspect within ±2%, resolution irrelevant.

**When the user supplies the Pinterest URL themselves**, skip the search entirely.

### Sourcing images

Three sources: user images, found-and-downloaded, code-drawn. Put files the composition
reads in `assets/` and reference them by relative path — never a leading `/`.

Verify before use: subject matches the script, resolution at least the output size, no
watermark, licence permits use. Record every source URL for the delivery message.

## 5. Building frames deterministically

HyperFrames gives determinism for free — the renderer calls `seek(t)` and never `play()`.
What still has to be enforced:

- **Register the timeline.** `window.__timelines['<data-composition-id>'] = gsap.timeline({paused: true})`.
  **Measured trap:** `window.__hf = {duration, seek(t)}` renders a **static video with no
  error at all**. The test element sat at x=319 px in every frame until this was corrected;
  after registering a real paused timeline it moved 319→659 px.
- **No clock, no unseeded randomness.** No `Date.now()`, `Math.random()`, network fetches,
  timers or `repeat: -1`. Everything visible is a function of timeline time.
- **Never tween `display`, `visibility` or `autoAlpha` on a `.clip`.** Animate a child.
- **No CSS `transform` on an element GSAP transforms.** Animate `x`/`y`/`scale`, not
  `left`/`top`/`width`/`height`.
- **Every timed element needs `class="clip"`, `data-start`, `data-duration`.**
  `data-track-index` is a Studio lane only; paint order is `z-index`.
- **The film's length is the root's `data-duration`.** An overrun is cut; an early end holds
  the last frame. Derive it from the last beat, never from the orientation cap.

**Measured failures of getting that last point wrong**, all from this scaffold:

- `data-duration="60"` against a 9 s script: 87% of the video was one still frame, and the
  contact sheet came back with nine near-identical thumbnails.
- `data-duration="10.5"` against a last beat ending at 9.6 s: **0.9 s of empty frame**, which
  the contact sheet showed as two blank thumbnails at the end.
- The rule that follows: **the root's duration is the last clip's end**, not the cap and not
  the last clip plus a tail that no clip fills. A tail only exists if something occupies it.

```bash
# last beat end, from the composition itself
grep -oE 'data-start="[0-9.]+" data-duration="[0-9.]+"' index.html \
  | awk -F'"' '{e=$2+$4; if (e>m) m=e} END {print "root data-duration should be", m}'
```

**Drift must last the whole beat.** A drift that stops after one second leaves identical
frames, and the encoder reports a freeze. Animate `x`/`y` over the full `data-duration`.

**Move vocabulary and curves.** `CRAFT.md` §1 gives the exact GSAP parameters for slam, slide
stack, stretch, letter cascade, flip swap, split and exit — the moves that make type read as
design instead of as captions. §2 is the curve per role, §3 the style rules that keep a frame
from looking like a slideshow, §4 why a spliced curve reads as choppy at 30 fps, and §5 how to
animate text without reflowing or blurring it.

**A reveal scheduled at the word leaves a hole at the cut.** The card appears only at
`wordAt`, so the ~0.4 s between the cut and the word can show one small label and nothing else —
a near-empty thumbnail. The defect is real; a progress bar across the bottom is one answer, not
the answer. Fill the gap with whatever the beat's idea wants — a drifting shape, a breathing
field, a camera push, a shape that is already on its way — and prove it with
`freezedetect=n=0:d=1.0` returning nothing. A bar pinned to the same y in every film is a
template; if a film wants one, add it and say why.

**Text belongs to one element.** A word inside an accent card is one element with
`background`, `color` and `padding` — not a block with a text sibling on top. Measured: with
the block as a sibling, the contrast gate read the page background and reported 1.01:1 for
text that is plainly legible.

### Safe area — one box for organic short-form

On `1080×1920`: **13% top, 20% bottom, 5% left and right** — `x 54..1026, y 250..1536`, a
972×1286 box covering **60% of the frame**, centre x 540 / y 893. The sides are symmetric, so
the horizontal centre is the frame centre; only the vertical centre sits 67 px high.

```css
.content { position: absolute; inset: 13% 5% 20% 5%; }
```

One asymmetry survives, and it is not a margin — it is the **action rail**. TikTok and Shorts
draw like / comment / share / audio down the lower right, so below **55% of the height**
(`y > 1056`) the right edge pulls in to **88%** (`x ≤ 950`). Above that line the full 5% applies,
so a headline across the top half can use the whole width.

The bottom margin is the largest because that is where every vertical platform stacks its UI —
caption, username, audio ticker, progress bar, OS gesture bar — while the top carries only a
header. The numbers match two other installed skills that describe organic short-form:
`~/.agents/skills/iart-wrapped-video/references/scene-grammar.md` (top 12%,
bottom 18%, sides 5%) and `~/.agents/skills/motioner/references/typography.md` (top 250 px, bottom
400 px on a 1080-wide frame). Top is 13% to clear the taller of the two.

Anything that must be read sits above **28% from the bottom** (y ≤ 1382), clear of a two-line
caption.

**`check` reports the ad box, not this one.** `@hyperframes/core/dist/safeAreas.js` is titled
*"Vertical-ad guides"*: its 35% bottom reserves a CTA button, legal line and shop card for a
paid in-feed ad. Treat a `check` finding outside its box as **advisory** — it is not the target,
and designing to it empties the lower third of an organic frame.

The box binds **content**. Backgrounds, gradients, grain and shapes that carry no meaning may
bleed past it — they still obey the 4% edge.

**Landscape is different: there is no box.** No feed UI overlays a 16:9 player, so a
`1920×1080` film keeps the plain 4% edge on every side and nothing else. Anything that must be
read — a keyword, a number, a verdict, **and every burned-in caption** — sits inside **10%**
(Adobe title-safe: `x 192..1728, y 108..972`). Fitting the portrait box to a landscape frame
would waste half the width for UI that never appears.

A caption near the bottom edge is the trap: the common 80–120 px floor lands at `y 960..1000`,
crossing the title-safe line at `y 972`. Put it inside the box — a baseline at `y 972` reads as
108 px from the bottom and costs nothing an audience notices.

Tag text so a gate can find it: `data-qc="display"` or `"readable"` for anything that must be
read, `data-qc="caption"` for burned-in subtitles, `data-qc="deco"` for paint that may be
cropped. Captions and readable text are held to the read line in portrait and to title-safe in
landscape; `deco` is held only to the 4% edge.

## 6. Audio mixing and export

Duration follows the voiceover, and the root's `data-duration` is **the last clip's end** —
not the voiceover plus a tail, and not the cap (§5 has the three measured failures of getting
this wrong).

```bash
ORIENT=portrait
case "$ORIENT" in
  portrait)  MAX_DUR=60 ;;
  landscape) MAX_DUR=300 ;;
esac

# the answer: the last clip's end, read from the composition itself
DUR=$(grep -oE 'data-start="[0-9.]+" data-duration="[0-9.]+"' index.html \
  | awk -F'"' '{e=$2+$4; if (e>m) m=e} END {print m}')

# the constraint it must satisfy
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 assets/voiceover.wav)
awk -v vo="$VO_DUR" -v d="$DUR" -v cap="$MAX_DUR" -v o="$ORIENT" 'BEGIN{
  if (d < vo)       print "FAIL: clips end at " d "s but the voiceover runs " vo "s — add a beat"
  else if (d > cap) print "OVER CAP " cap " s for " o ": stop and ask the user"
  else              print "ok: " d " s, " d*30 " frames, voiceover " vo " s, cap " cap " s"
}'
```

Whatever `DUR` is, every `<audio data-duration>` must equal the media length, or lint warns
`clip_media_fit` and the audio is silently truncated.

**Audio is placed by tags, then normalised after export.** HyperFrames mixes `<audio>`
elements and does **not** normalise loudness — measured −34.5 LUFS for a sine at 0.8 volume.
One ffmpeg pass fixes it:

```bash
ffmpeg -y -i work/render-raw.mp4 \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v copy -c:a aac -b:a 192k -ar 48000 \
  output/<slug>.mp4
```

`-c:v copy` never re-encodes the video. Measured: −34.5 → **−16.0 LUFS**.

Ducking is done with `data-volume` plus `data-fade-in` / `data-fade-out`, or a
`data-automation` envelope. Do not stack the three-step ffmpeg chain from the drawing skill:
HyperFrames already mixes, and the only pass needed is the loudness line.

Output is H.264 + AAC 48 kHz stereo. Transparent WebM and ProRes are available with
`--format webm` / `--format mov` when the film needs alpha.

## 7. Verifying the exported file

```bash
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames,width,height,r_frame_rate -of csv=p=0 output/<slug>.mp4
```

Target: `FRAMES = DUR × 30`, 30 fps, H.264 + AAC, resolution as planned.

### `hyperframes check` is the gate

The gate is built in and returns machine-readable geometry, which is the main reason this
engine is worth its heavier setup.

```bash
npx hyperframes check --json
```

Sections: `lint`, `runtime`, `layout`, `motion`, `contrast`, `craft`, `audio`, `snapshots`.
Measured cost: **7.7 s** for a 60 s composition (9 layout samples, 80 craft checks, contrast,
motion, audio).

Each finding carries what a sync gate needs:

```json
{"selector": "#w", "bbox": {"x": 80, "y": 180, "width": 307.83, "height": 134},
 "time": 3.333, "code": "outside_safe_zone", "severity": "warning",
 "text": "harga", "firstSeen": 3.333, "lastSeen": 56.667, "occurrences": 6,
 "fixHint": "Move the text inside the safe area, or ..."}
```

- **`layout`** — safe area and overflow, with `bbox` and `time` per finding.
- **`contrast`** — WCAG against the pixels actually behind the text, per sample.
- **`motion`** — freeze and dead-stretch detection.
- **`craft`** — reading time per line: 0.5 s + 0.3 s per word, minimum 2 s for a closing line.
- **`audio`** — clipping, silence, loudness.
- **`runtime`** — JS errors, missing assets, media fit.

`check` passing is necessary, not sufficient — it does not judge whether the composition is
good. Read the contact sheet too, against the review flags in `CRAFT.md` §7: STUTTER, HITCH,
GHOST, HANDOFF-JUMP, MUDDY and the rest. `check` catches `dead_stretch`; it does not catch a
choppy handoff.

**Report only problems.** A clean composition returns **zero findings**, so `firstSeen` is not
available for text that behaves correctly. Do not build a gate that reads only `findings`; it
will pass every broken film and fail nothing, which is worse than no gate.

### Sync gate

Two scripts, because the answer needs the DOM and the word times:

```bash
python3 qc/make_sync_probe.py    # samples the composition, writes work/sync-probe.json
python3 qc/sync_gate.py          # compares, exits 1 on a finding
```

`make_sync_probe.py` loads `index.html` in headless Chrome, seeks the registered timeline to
`word - 0.15 s` and `word + 0.10 s` for each case, and records which texts are visible.

Two layers decide visibility, and the probe must apply **both**:

1. **Clip gating** — the engine shows a `.clip` only inside
   `[data-start, data-start + data-duration)`. GSAP does not do this; the runtime does.
   A probe that only seeks GSAP sees every text at every time. Measured failure: it reported
   all four texts present before the first word and failed a correct composition.
2. **The timeline** — opacity, scale and transform set by `seek(t)`. An element with
   `opacity: 0` still has `textContent`, so read computed opacity, not text.

`qc/sync-cases.json` holds `{text, t_vo}` in **voiceover** seconds; the probe converts with
`vo_delay`. The asymmetry is deliberate: 0.1 s late is invisible, appearing early is a defect.

### Picture gates

```bash
ffmpeg -i output/<slug>.mp4 -vf "freezedetect=n=0:d=1.0" -an -f null - 2>&1 | grep freeze_
ffmpeg -i output/<slug>.mp4 -vf "blackdetect=d=0.5:pix_th=0.02" -an -f null - 2>&1 | grep black_
```

`freezedetect` needs `n=0`: the default `n=0.001` (about −60 dB) false-positives on flat
graphics, and `n` is a linear 0–1 ratio, not a dB value. `blackdetect` needs `pix_th=0.02`:
a `0x0B0B0F` background reads as black from `0.05` up.

### Text inside a frame — centring gate

A chip, badge, tag, button, sticker or card holds its text **centred both ways**:
horizontally *and* vertically against its frame. Horizontal-only centring leaves
the text floating high or low and reads as misplacement, however good the copy is.

- **Browser (DOM/HTML):** let the frame centre its own content —
  `display:flex; align-items:center; justify-content:center` — instead of nudging
  the text with `transform`, `padding-top` or a hand-tuned offset. Then prove it:
  `Range.getClientRects()` for the line count (one rect = one line) plus
  `getBoundingClientRect()` of frame and text; centre-to-centre gap ≤ 2 px, and
  top/bottom gaps equal within 3 px.
- **PIL/skia (`render.py`):** never place text with a fixed nudge such as
  `y + font.size * 0.34` — it is a guess that breaks at every new size or family.
  Size the frame from the **glyph ink box** and centre the ink itself:

  ```python
  def ink_box(font, s, tracking=0.0):
      """Real ink box of a string, relative to a text drawn at anchor 'lm'."""
      x, xs, ys = 0.0, [], []
      for ch in s:
          b = font.getbbox(ch, anchor="lm")
          xs += [x + b[0], x + b[2]]
          ys += [b[1], b[3]]
          x += font.getlength(ch) + tracking
      return min(xs), min(ys), max(xs), max(ys)

  ix0, iy0, ix1, iy1 = ink_box(font, label, tracking)
  w = (ix1 - ix0) + 2 * pad_x          # frame from ink + symmetric padding
  h = (iy1 - iy0) + 2 * pad_y
  d.text((cx - (ix0 + ix1) / 2, cy - (iy0 + iy1) / 2),
         label, font=font, anchor="lm")   # centre of ink on centre of frame
  ```

- **Prove it from pixels, not from the code that drew it.** Record each frame box
  as it is drawn, then measure the rendered frame: ink bbox against frame bbox,
  centre-to-centre ≤ 2 px and left/right, top/bottom gaps equal within 4 px.
  Drop the rounded corners and a 4 px border before measuring, otherwise the
  outline itself is counted as ink and every chip looks off-centre. Vision is not
  a substitute — it calls a 12 px misalignment "centred".
- A finding here is a defect, not taste: fix the geometry and re-render.
- Ready-made checker for PIL/skia frames: `/root/Motion-Skills/bits-bang-motion/scripts/chip-centring.py <frame.png> x0 y0 x1 y1` — also exports `ink_box()` for drawing; exit 1 when gaps differ beyond tolerance.

### Repetition gate

`check` does not compare beats to each other. Do it yourself, from the same DOM the sync gate
already reads:

```bash
python3 qc/make_sync_probe.py     # writes work/sync-probe.json with boxes per sample
```

For every pair of consecutive beats, compare the `data-qc` boxes: same role, same size, same
position means the layout did not change. A deliberate pair is legitimate — a before/after, a
repeated motif. **Three in a row is the signature of a template.** When it is deliberate, write
the reason beside the beat so the next revision does not "fix" it.

No pixels are read, so a dark theme with light text is not a special case.

### Contact sheet

`hyperframes snapshot` writes frames and a grid for review:

```bash
npx hyperframes snapshot --frames 12
```

Or from the render:

```bash
mkdir -p work/check
CELLS=$(( (DUR + 2) / 3 ))
GRID=$(python3 -c "import math; print(max(1, math.ceil(math.sqrt($CELLS))))")
ffmpeg -i output/<slug>.mp4 -vf "fps=1/3,scale=240:-1,tile=${GRID}x${GRID}" \
  -frames:v 1 work/check/sheet.png
```

**Read the sheet; do not only count cells.** Two defects reached a render while building this
scaffold and passed every numeric gate:

- a large word straddling the edge of its card, half on black and unreadable;
- rows of identical thumbnails, because the drift stopped after one second.

If the main model cannot see the sheet, hand it to the `vision` subagent in one call.

### What is a hard requirement

Two checks protect the file itself:

- **frame count equals `DUR × 30`** — a truncated render passes every visual check;
- **loudness and tail floor** — a quiet mix plays badly on every platform.

Everything else is reported with its number and a decision.

## 8. Self-made background music

Only when the user supplies none. Use the bundled generator — a one-chord pad is what made
every film from these skills sound the same:

```bash
python3 <skill>/scripts/make_music.py --duration 52 --out assets/music.wav \
    --brief "pasar subuh, hangat, akustik, tenang, sedikit melankolis"
```

**Write the brief from the topic — never leave it empty and never reuse the previous film's brief.** The brief is the creative act: it decides key, chord quality, timbre, bass motion, arpeggio density, texture depth, and tempo. Two films that get the same brief get the same music, so a copied brief is the one way to make this generator sound monotonous again.

`--brief` is free text. Words are scored, not matched to a fixed list: `tenang` / `sedih` / `tegang` / `ceria` / `megah` / `akustik` / `urban` / `malam` all pull the parameters, and unrecognised words still change the seed. Use `--tempo` to force BPM when the topic has a natural pace, and `--seed` to force a different take from the same brief.

When the topic deserves music this synthetic bed cannot give — a hummed melody, a specific regional instrument, a real song — supply `audio/music.wav` yourself (royalty-free, licence recorded in the delivery message). The project always prefers a user file over the generator.

`<skill>` is this skill's own directory; the generator ships with the skill, so the
project folder stays free of build tooling. Run it from the project folder.

It writes 48 kHz stereo 16-bit WAV at exactly `--duration` (never loop a short bed), peak
−6 dBFS, 1.2 s fade-in, and a fade-out that lands on a floor rather than absolute zero.

What it plays is derived from the brief: a four-chord functional progression in a scale
chosen from the brief's mood (minor / dorian / major / lydian / phrygian / mixolydian),
with a timbre family per topic (chalk / wood / glass / metal — each a different harmonic
stack and attack), bass motion (root / octave / walking), arpeggio density, and a texture
layer. The seed comes from the brief text, so the same brief always renders identically —
a re-render never shifts music away from the already-synced picture.

| Flag | Values | Choose by |
|---|---|---|
| `--brief` | free text (required) | the topic's mood and material — this is the creative decision, write it fresh per film |
| `--tempo` | 60–120 | the film's cut rhythm; omit to let the brief decide. Keep it under the cut rate so it never fights the narration |
| `--seed` | integer | force a different take from the same brief; omit to derive from the brief text |

Add it with an `<audio>` tag and `data-volume` around 0.22. Each film gets its own brief —
reusing one bed, or one brief, across a series is what made every film sound alike.

Tell the user plainly that this is synthesised music — a progression and a pulse generated in
code, not a composed track — and suggest royalty-free music when they want more.

Optional synthetic SFX:

```bash
ffmpeg -f lavfi -i "anoisesrc=d=0.4:c=pink:a=0.5" \
  -af "afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2,volume=0.3" -ar 48000 assets/whoosh.wav
```

HyperFrames also ships `npx hyperframes audio` (onsets, hits, loudness, silence in film time)
and `npx hyperframes beats` (writes `beats/<audio>.json`). Use them to check the mix; do not
require scenes to start on beats.

- **`assets/voiceover.wav` vs the BITS folder standard.** The skill's tree lists the narration under `assets/`, but
  `/root/BITS/company/workflows/struktur-proyek-video.md` puts it in `audio/`. Declare `<audio src="…">` where the file
  actually is: a mismatch is a lint **error** (`audio_src_not_found`, plus `http_error` and `clip_media_fit` in `runtime`)
  and the render comes out silent. On a BITS project the source is `audio/voiceover.wav` and `audio/music.wav`.
- **A music bed that ends exactly with the film doubles the fade.** `make_music.py` already fades its own tail to a floor;
  a `data-fade-out` on the same element stacks on top of it and the last 0.5 s lands near −60 dB, which reads as the music
  having died. Measured: a 60 s bed with `data-fade-out="1.2"` gave −63 dB in the final 0.5 s; the same bed generated at
  **63 s** and cut to 60 by the element's `data-duration` with `data-fade-out="0.6"` gave −38.7 dB. **Generate the bed
  2–4 s longer than the film.**
- **Anchor graphics must enter at the clip's own start.** Reveals tied to spoken words land 0.5–1.0 s after the cut, so the
  beat's shapes — the panel, the cabinet, the socket, the meter rails — have to be already on their way at `data-start`,
  with a short entrance (0.26–0.3 s). Measured on a 60 s portrait film: seven beats read as "hampir kosong" on the contact
  sheet until every anchor was moved to the cut and its tween shortened; the same frames then read as full.
- **`data-qc` on the text, not on the clip.** `qc/boxes.py` measures `data-qc` leaf elements, and the scaffold's
  `qc/repetition.py` only reads `.clip` elements that carry `data-qc`. On a project that tags the text elements instead,
  the repetition gate reports "0 texts" — a gate that checks nothing. Point it at the text elements (class
  `display`/`meta`/`hand` + `data-qc`) and give each one its owning clip, taken from the nearest preceding `data-start`.

## 9. Common traps

- **`window.__hf` instead of `window.__timelines`.** Renders a **static video with no error**.
  Measured: the test element sat at x=319 px in every frame. Register a paused GSAP timeline
  under the composition id.
- **Repeated `fromTo()` on the same target property has no stable baseline.** Lint says it
  (`gsap_repeated_fromto_without_baseline`) and it is a real defect, not advice: the **last**
  authored `from` values become the element's resting state for any seek before the first
  tween, so a fade-in written as `fromTo(opacity 0→1)` followed later by `fromTo(opacity 1→0)`
  is **visible from the start** and pops to 0 when its own tween begins. Measured on a 48 s
  portrait film: a sentence meant to appear at its spoken word would have shipped early. Write
  each initial state once with `gsap.set()` and animate with `tl.to()`, so a property has
  exactly one writer per phase.
- **A negative timeline position is clamped to 0.** `tl.to(el, {...}, -0.32)` does not start the
  tween before the film's first frame — measured, the target was still `opacity: 0` at t=0 and
  only reached 0.47 at t=0.05. To have content on frame 0 (the thumbnail every platform shows),
  leave one element out of the entrance stagger: a resting-visible element with only a drift
  tween is what makes `craft` stop reporting `first_frame_empty`.
- **`<Series>`-style thinking.** HyperFrames is not Remotion: there is no frame function, and
  every visible property must be reachable from `seek(t)`. A property you set imperatively
  will not survive a seek.
- **Only one root composition.** Two HTML files with `data-composition-id` fail
  `multiple_root_compositions`. Scenes go in `compositions/`.
- **An audio file without an `<audio>` element** triggers
  `audio_file_without_element` and the render is silent.
- **`data-duration` shorter than the media** triggers `clip_media_fit` and the slot is
  shortened. Match the tag to the file.
- **`check` fails but `render` still writes a file.** `check` is the gate; a successful
  render is not a pass.
- **A word over a coloured block as two elements.** The contrast gate reads the page
  background and reports 1.01:1 for legible text. One element with background and padding.
- **A drift that stops early** leaves identical frames; the encoder reports a freeze and the
  contact sheet shows duplicates. Animate over the full duration.
- **`data-duration` copied from the orientation cap** instead of the script. A 9 s script in
  a 60 s composition is 87% dead. Derive the number from the last beat.
- **Text outside the content box.** Content needs x 54..1026, y 250..1536 on 1080×1920, with the
  right edge pulled to x 950 below y 1056. `check` reports the TikTok ad box (x 120..780,
  y 240..1260) instead — a `check` finding there is not a defect for organic work.
- **Font not declared.** Lint fails `font_family_without_font_face`; a `local()`-only face
  works here and fails in the cloud (`font_face_local_only`).
- **`timeline_track_too_dense`** is advice, not a defect: past ~10 timed elements, split into
  sub-compositions so the timeline stays readable.
- **`faster_whisper` when `av` predates 13:** `decode_audio` calls
  `av.open(..., metadata_errors="ignore")` and dies with `TypeError: open() got an unexpected
  keyword argument`. Pass samples, not a path: decode the 16 kHz mono WAV with `wave` + `numpy`
  and hand `model.transcribe()` a float32 array. No rebuild needed.
- **Long-form whisper timestamps can come back out of order** even when the text is right:
  measured on a 51 s Indonesian VO, the opening sentence was timestamped at 47 s. Run with
  `vad_filter=True`, `condition_on_previous_text=False`, `temperature=0` — and prove the order
  independently before trusting any time (transcribe fixed 5 s chunks and read the lines).
- **Never align script sentences to ASR *segments*.** One segment spans several script
  sentences and vice versa, so a per-segment match hands a sentence the wrong audio. Align the
  two **word streams** with `difflib.SequenceMatcher`, then take each sentence's span from its
  first and last word.
- **`text-transform: uppercase` does not change `textContent`.** `qc/sync-cases.json` matches
  `textContent`, so a label styled uppercase but written lowercase fails the gate as "missing or
  late" for every case at once. Write the caps in the markup.
- **`qc/make_sync_probe.py` needs `puppeteer-core`**, and searches only `./node_modules` and
  `npm root -g`. When the engine runs from the npx cache, symlink it for the run and delete it
  at cleanup:
  `ln -sfn $(dirname $(find ~/.npm/_npx -maxdepth 6 -type d -name puppeteer-core | head -1)) node_modules`
- **On an unattended host, `python3 -c`, heredocs and `rm -rf` are refused before they run.**
  Write the script to a file and run it; clean up with `shutil.rmtree` or `rmdir`.

## 10. Cleanup after delivery

`.hyperframes/artifacts/` holds checks, snapshots and state; it grows every run. `work/` holds
bundles, `ref/`, `check/`, `voiceover-16k.wav`, the raw render. Delete both once the video is
verified and delivered.

**Keep — everything a later revision needs:**

| Path | Why it must survive |
|---|---|
| `script.txt` | the narration source |
| `index.html` | the whole visual design: markup, CSS, timeline |
| `compositions/` | the scenes, when a project has them |
| `assets/voiceover.wav` | timing source; the composition plays it |
| `audio/words.json` | **the only non-reproducible derived file** — a fresh ASR pass returns ±0.1 s different timestamps and desyncs a re-render |
| `assets/` | images, fonts, music |
| `qc/sync-cases.json` | the texts the sync gate proves, with their word times |
| `output/<slug>.mp4` | the deliverable |
| `output/<slug>.srt` | subtitle track, when generated |
| `output/publish.txt` | caption, description, hashtags |

Before deleting, confirm the required checks passed — duration, frame count, loudness, tail
floor, black/freeze — measured from the exported MP4, never from the timeline.

**Verify the kept set is self-sufficient:**

```bash
grep -oE '(src|href)="assets/[^"]+"' index.html | sed 's/.*="//;s/"//' | sort -u | while read p; do
  [ -e "$p" ] || echo "MISSING for re-render: $p"
done
```

An empty result means deleting `work/` cost nothing that matters: the composition is the
source of truth, and a re-render restores the same video.