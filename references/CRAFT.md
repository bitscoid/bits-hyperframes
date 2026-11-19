# Craft — kinetic type, curves, and what makes a frame read

Read this before scene code, and again when the result looks like a slideshow.

Adapted from `PHANTOMTONYT/motion-design-skills` → `kinetic-typography` (MIT) and
`Tarquished/motioner` (MIT, © 2026 Motioner contributors). Both are written for their own
engines; the numbers here are converted to this workflow: **30 fps**, **voiceover-led**,
**HyperFrames + GSAP**, and the platform safe band enforced by `check`.

## 1. The move vocabulary

Exact GSAP parameters. These are the moves that make type read as *design* rather than as
captions.

| Move | GSAP | Use for | Source |
|---|---|---|---|
| **Slam** | `from {scale: 2.6, opacity: 0}`, `expo.out`, 0.22 s, plus a ~6 px shake for 0.1 s | hero words | kinetic-typography |
| **Slide stack** | lines `from {yPercent: 110}` inside `overflow:hidden` masks, stagger 0.06 s, `power4.out` 0.35 s | lists, two-line phrases | kinetic-typography |
| **Stretch** | `scaleY: 1.6 → 1`, `transformOrigin: bottom`, `back.out(3)` 0.3 s | emphasis, verbs | kinetic-typography |
| **Letter cascade** | letters `from {y: -120, rotation: -20, opacity: 0}`, stagger 0.025 s, `back.out(2)` | names, titles | kinetic-typography |
| **Flip swap** | old word `rotationX: 90` out (0.12 s), new word `rotationX: -90 → 0` in (0.18 s) | X becomes Y | kinetic-typography |
| **Split** | word halves slide apart `x: ±140`, revealing a smaller word between | contrasts | kinetic-typography |
| **Exit** | `yPercent: -110` or `scale: 0.7, opacity: 0`, 0.15 s, `power2.in` | every phrase leaving | kinetic-typography |

Exits are fast (0.12–0.18 s); entrances are snappier than instinct suggests (0.18–0.35 s).
Hold each phrase at least 0.35 s after it lands so it can be read.

## 2. Curves by role

Halved to 30 fps from the motioner curve table.

| Role | Cubic bezier | Note |
|---|---|---|
| Something arrives | `(0.16, 1, 0.3, 1)` | fast start, long settle — the default |
| Object travels A to B, camera move | `(0.65, 0, 0.35, 1)` | symmetric |
| Morph carrier, shared element | `(0.45, 0, 0.15, 1)` | decisive middle, gentle landing |
| Reveal growing from an element | `(0.5, 0, 0.15, 1)` | leaves gently, fills fast |
| Whip, zoom-through | `(0.77, 0, 0.175, 1)` | violent middle |
| Exit that leaves the frame | `power2.in` | only when it really leaves |

Never `linear` for visible motion except a constant drift or a progress rule.

## 3. Style rules that make type read as design

These are what separate a postable frame from a test render.

1. **Type fills 50–80% of the frame width.** Small text reads as a caption, not as the visual.
   Size to the frame, never to a comfortable font size.
2. **One idea on screen at a time**: 1–4 words, at most 3 lines.
3. **Every word arrives with a move.** Nothing simply fades in.
4. **Changes land on a rhythm**: a new word or move every 0.25–0.7 s, keywords on the spoken
   word.
5. **Contrast is extreme**: near-black on off-white or the reverse, plus one accent colour for
   the key word only.
6. **Each phrase gets one hero word**: biggest, accent-coloured, or moving differently.

## 4. Velocity continuity — the cause of "choppy"

The eye sees acceleration, not position. At 30 fps a velocity break is twice as visible as at
60, because each frame is a bigger step.

- **Passing through a key:** do not chain two tweens; each eases to zero at the key.
- **One curve per gesture.** Never splice a fast part and a slow part.
- **Start from rest.** Over a 15-frame, 700 px move, `(0.45, 0, 0.15, 1)` travels roughly
  3, 9, 17, 28, 40 px/frame; `(0.2, 0, 0, 1)` travels 16, 64, 140, which reads as a teleport.
- **Idle motion must meet a handoff at zero speed.** A bob drawn with `sin` is at full speed
  when it crosses zero; use `sin²`, or fade the amplitude out first.
- **Pulses need an attack**: ramp over 2 frames, decay over 8–12. A one-frame jump reads as a
  glitch.
- **Never round transforms to integers** during motion.

## 5. Text in motion

- **Lock the layout.** A line's breaks and width are final from its first frame. Per-letter
  reveals must reserve final glyph widths, or the line reflows mid-animation.
- **Measure once, after fonts load.** `document.fonts.ready` then measure; a measurement
  taken before the webfont arrives is wrong by exactly the fallback's metrics.
- **Never scale text past ~1.2 with a CSS transform** on an element that also has
  `will-change: transform`: the bitmap stays at its first size and blurs. Re-set the font
  size each frame instead, or keep the scale below 1.2.
- **Slow group scaling shimmers.** A 1.00 → 1.04 push-in over seconds makes Chrome
  re-rasterise glyphs at stepped sizes; put `will-change: transform` on that group.

## 6. Timing at 30 fps

| Action | Frames |
|---|---|
| Chip, badge, pop | 5–8 |
| Card or panel entrance | 9–14 |
| Large shared-element morph | 15–20 |
| Flood, full-screen reveal | 20–25 |
| Camera push (subtle) | 30–75 |
| Stagger between siblings | 2–4 |
| Readable hold for a line | 24 + 8 per word |

Every landing goes on the **spoken word**, from `audio/words.json` — never on a music beat.
The narration leads.

## 7. Review flags

Render a draft, cut a contact sheet, look at consecutive frames.

| Flag | Means | Usual cause |
|---|---|---|
| **POP** | one frame changes far more than its neighbours | a mismatched layer swap, an off-by-one `data-start` |
| **STUTTER** | a frame repeats while its neighbours move | a hold key mid-travel, a rounded position |
| **HITCH** | speed collapses for 1–2 frames | chained eases through a key |
| **FLASH** | brightness spikes and returns | a layer missing for one frame |
| **BLANK** | a nearly uniform frame | a gap between two scenes — the most common defect here |
| **COLORJUMP** | mean colour jumps in one frame | an unmotivated hue switch |
| **GHOST** | a region loses detail while barely moving | `autoAlpha` tweened on a `.clip`, a double exposure |
| **MUDDY** | contrast sags mid-window | an accent close to the background |
| **HANDOFF-JUMP** | a small region jumps on the first or last frame of a handoff | content frozen during the move |
| **TELEPORT** | a small region changes in one frame | an object jump; also legitimate glyph pops |
| **JERK** | a still region goes to full speed in one frame | a move without ease-in on something visible |

Expected, not defects: COLORJUMP on the middle of a deliberate flood; BLANK on the frames
before a film's seed appears.

**What `hyperframes check` already covers**: it flags `dead_stretch` (nothing changes for
seconds) and `motion` problems on its own. The flags above are the ones it does *not* catch,
so they are what you look for on the sheet.

## 8. Where this fits the workflow

- Stage 5 (timeline): choose the move per phrase here. The move is a timeline decision.
- Stage 6 (build): the GSAP parameters above, inside the registered timeline.
- Stage 7 (QC): the flags are advisory. Write a verdict per boundary
  (`name (frames): GOOD/WEAK/BROKEN — what you saw, cause, fix`).

Nothing here overrides the hard requirements in `RENDER.md` §7, and nothing here overrides
the platform safe band that `check` enforces.