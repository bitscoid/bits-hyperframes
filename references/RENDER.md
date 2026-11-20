# Render and Verification — HyperFrames

Read this before building and rendering. All commands are examples — adapt filenames to the assets you actually have. Never run a command that depends on a tool you have not checked exists.

Everything here was measured on hyperframes 0.9.68, @hyperframes/engine 0.9.69, Chrome 158.0.8127.36, ffmpeg 7.1.5, 34 vCPU, 24 GB RAM.

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

### Fonts

**A film has three type roles, and they should not all share a family.** The pairing is
the design; one family for all three is what makes a video read as a template.

| Role | Carries | Typical register | CSS variable |
|---|---|---|---|
| **display** | the keyword, the number, the verdict | impact, or rounded for a light topic | `--font-display` |
| **meta** | labels, indices, chips, footnotes | mono, or small-caps serif | `--font-meta` |
| **accent** | an annotation, a scribble | handwriting, sparingly, never body | `--font-accent` |

**The bundled families cover only the first two registers.** HyperFrames bundles 18
families **by name**: Inter, Montserrat, Outfit, Nunito, Oswald, League Gothic, Archivo
Black, Space Mono, IBM Plex Mono, JetBrains Mono, EB Garamond, Playfair Display, Source Code
Pro, Noto Sans JP, Roboto, Open Sans, Lato, Poppins.

None of them is handwriting, doodle or rounded *display*. That is not a gap in the tool — it
means the playful registers must be shipped in `assets/fonts/` and declared. The scaffold
does this already, with five families ready to swap in:

| Family | Register | Use for |
|---|---|---|
| `Fredoka` | rounded, friendly, geometric | display for a light or playful topic |
| `Baloo 2` | rounded, heavier, warmer | display when Fredoka is too soft |
| `Shrikhand` | heavy display, high personality | a title, once per film |
| `Caveat` | handwriting, natural | the accent role — annotations |
| `Patrick Hand` | handwriting, blockier | the accent role when Caveat is too cursive |

Delete the ones a film does not use; each is 100–680 KB and they are shipped per project.

**The register is a required choice, not a default.** `js/type-presets.mjs` holds eight, each a
display + meta + accent triple with the reason it suits a topic:

| Preset | Display | Meta | Accent | When |
|---|---|---|---|---|
| `playful-rounded` | Fredoka | JetBrains Mono | Caveat | food, habits, kids, everyday science |
| `playful-bold` | Baloo 2 | Nunito | Patrick Hand | fitness, productivity, how-to |
| `poster-display` | Shrikhand | Poppins | Caveat | culture, music, opinion |
| `editorial` | Fraunces | JetBrains Mono | Caveat | essay, history, analysis |
| `archival` | Libre Caslon | Space Mono | Kalam | financial, legal, historical |
| `kinetic-impact` | Anton | JetBrains Mono | Caveat | statistics, records, hooks |
| `technical` | Space Grotesk | IBM Plex Mono | Kalam | systems, code, data |
| `handwritten` | Caveat | Nunito | Indie Flower | first-person, reflective |

Set `window.BITS_TYPE_PRESET` in the `<head>` of `index.html`, above the script tag that reads
it. `python3 qc/type_gate.py` fails on an empty key, on one family carrying all three roles, on a
family that is neither bundled nor declared by an `@font-face`, and on the table disagreeing with
the copy in `js/apply-type-preset.js`; repeating the previous run's preset is only a note.

Two measured traps, both silent before they were fixed:

- **Order.** The apply script was loaded before the inline assignment, read `undefined`, took the
  "fall back to the CSS defaults" path and returned. Every film rendered the same pairing while
  the gate — which reads the text of the file, not the live DOM — reported OK. The key is now
  assigned in its own `<script>` above it, and the script throws instead of falling back.
- **The name.** A family is matched by the name the font declares, not the file or module name:
  `Baloo 2`, not `Baloo2`; `Space Grotesk`, not `SpaceGrotesk`. Declaring the file under the
  wrong name loads it and then renders the fallback with no error anywhere.

`js/apply-type-preset.js` reads the key and writes `--font-{display,meta,accent}` and their
weights. It declares no `@font-face`: injecting the rules from script fails
`font_family_without_font_face`, because `check` lints the static file, not the DOM.

The bundle has Latin at a few weights per family. Other weights and scripts are fetched from
Google Fonts and cached in `~/.cache/hyperframes/fonts`.

Any other family needs an explicit face, or lint fails `font_family_without_font_face`:

```html
<style>
  @font-face {
    font-family: 'Fraunces';
    src: url('assets/fonts/Fraunces.ttf') format('truetype');
  }
</style>
```

Measured: a local `Fraunces.ttf` loaded correctly (`document.fonts.check` true; 286 px wide
for "KATA" against 295 px for the DejaVu fallback). A `local()`-only face works on this
machine and fails in the cloud, where lint warns `font_face_local_only`.

## 2. The render contract

HyperFrames seeks a paused timeline frame by frame. Nothing plays in real time, so a slow
machine cannot drop frames.

```
index.html              the root composition and its data-* timing attributes
compositions/           optional sub-compositions, one scene each
assets/                 voiceover.wav, music.wav, images, fonts
renders/                output of `hyperframes render`
.hyperframes/           artifacts: checks, snapshots, state
```

```bash
npx hyperframes init <dir> --non-interactive --skip-skills --resolution portrait
npx hyperframes check          # lint + runtime + layout + motion + contrast + craft + audio
npx hyperframes render --output renders/<slug>.mp4 --workers=4
```

**Measured render times** on a scene with 7 timed elements, 1080×1920:

| Duration | Frames | Workers | Wall |
|---|---|---|---|
| 3 s minimal | 90 | 3 | 8 s |
| 9.6 s scaffold | 288 | 4 | **8 s** |
| 60 s | 1800 | 1 | 25 s |
| 60 s | 1800 | 6 | **19 s** |
| 300 s landscape | 9000 | 6 | **69 s** |

Worker scaling is flat (1→25 s, 6→19 s): capture is already parallel inside the engine, so
raising `--workers` past 6 mostly adds memory. Each worker is a separate Chrome (~256 MB).

Quality presets on a 60 s film, 4 workers: `draft` 16.9 s / 721 KB, `looks` 18.4 s / 784 KB,
`delivery` 18.6 s / 801 KB. `looks` is the default; use `delivery` only for the final file
when quality matters more than a few seconds.

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

1. **Gemini TTS** (needs `GEMINI_API_KEY`). Models `gemini-3.8-flash-tts` and
   `gemini-3.8-flash-lite-tts` (separate quota). Endpoint `POST /v1beta/interactions`,
   style in `input[].content[].annotations[].style`, audio in `steps[].content[].data`.
   Build the payload with `json.dumps`, and strip `[Hook]` / `[Inti N]` / `[Penutup]`
   labels — the model reads text verbatim.
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
  renders/<slug>.mp4
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
  -show_entries stream=nb_read_frames,width,height,r_frame_rate -of csv=p=0 renders/<slug>.mp4
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
ffmpeg -i renders/<slug>.mp4 -vf "freezedetect=n=0:d=1.0" -an -f null - 2>&1 | grep freeze_
ffmpeg -i renders/<slug>.mp4 -vf "blackdetect=d=0.5:pix_th=0.02" -an -f null - 2>&1 | grep black_
```

`freezedetect` needs `n=0`: the default `n=0.001` (about −60 dB) false-positives on flat
graphics, and `n` is a linear 0–1 ratio, not a dB value. `blackdetect` needs `pix_th=0.02`:
a `0x0B0B0F` background reads as black from `0.05` up.

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
ffmpeg -i renders/<slug>.mp4 -vf "fps=1/3,scale=240:-1,tile=${GRID}x${GRID}" \
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
python3 <skill>/scripts/make_music.py --duration 52 --out assets/music.wav --tempo 84 --mood warm
```

`<skill>` is this skill's own directory; the generator ships with the skill, so the
project folder stays free of build tooling. Run it from the project folder.

It writes 48 kHz stereo 16-bit WAV at exactly `--duration` (never loop a short bed), peak
−6 dBFS, 1.2 s fade-in, and a fade-out that lands on a floor rather than absolute zero.

What it plays: a four-chord progression (two bars per chord), each chord carrying a detuned
two-voice pad, a root bass on beats 1 and 3, a plucked arpeggio on eighths alternating pan,
and a soft noise breath at every chord change.

| Flag | Values | Choose by |
|---|---|---|
| `--mood` | `warm` (Am–F–C–G) · `dark` (Dm–B♭–F–C) · `bright` (C–Em–Am–F) | the topic's tone; `dark` for history/analysis, `bright` for light explainers |
| `--tempo` | 60–100, default 84 | the film's cut rhythm; faster film, faster bed. Keep it under the cut rate so it never fights the narration |

Add it with an `<audio>` tag and `data-volume` around 0.22. Re-run the same command with a
different `--mood`/`--tempo` per film rather than reusing one bed across a series.

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

## 9. Common traps

- **`window.__hf` instead of `window.__timelines`.** Renders a **static video with no error**.
  Measured: the test element sat at x=319 px in every frame. Register a paused GSAP timeline
  under the composition id.
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
| `renders/<slug>.mp4` | the deliverable |
| `renders/<slug>.srt` | subtitle track, when generated |
| `renders/publish.txt` | caption, description, hashtags |

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