/**
 * Type presets — the register is chosen from the topic, and the build refuses to
 * run until it is.
 *
 * Why this file exists: the scaffold used to hardcode one pairing, so every film
 * from it used that pairing no matter the topic. A list of options does not
 * change behaviour; a required choice with a failing gate does.
 *
 * Two readers: `qc/type_gate.py`, which also cross-checks this table against the
 * copy in `js/apply-type-preset.js`, and that copy itself, which sets the CSS
 * variables before the timeline is built. `qc/type_gate.py` fails on an unset
 * key and on the same folder repeating its register.
 *
 * Every family name here is the name the font declares, not the file name:
 * 'Baloo 2', not 'Baloo2'; 'Space Grotesk', not 'SpaceGrotesk'. A mismatch loads
 * the file under a name no CSS rule asks for and the film renders in a fallback
 * with no error anywhere.
 */

/**
 * Set this from the topic's register in stage 4. Empty on purpose.
 * Use 'custom' when no register fits the topic: then set
 * window.BITS_TYPE_CUSTOM = {display: '…', meta: '…', accent: '…'} in index.html
 * and declare each face with an @font-face. The gate checks they resolve.
 * @type {'' | 'playful-rounded' | 'playful-bold' | 'poster-display' | 'editorial' | 'archival' | 'kinetic-impact' | 'technical' | 'handwritten'}
 */
export const TYPE_PRESET = '';

export const PRESETS = {
  'playful-rounded': {
    display: 'Fredoka',
    displayWeight: 600,
    meta: 'JetBrains Mono',
    metaWeight: 500,
    accent: 'Caveat',
    accentWeight: 700,
    when: 'a light or friendly topic: food, habits, kids, everyday science',
  },
  'playful-bold': {
    display: 'Baloo 2',
    displayWeight: 700,
    meta: 'Nunito',
    metaWeight: 700,
    accent: 'Patrick Hand',
    accentWeight: 400,
    when: 'an energetic topic that still wants warmth: fitness, productivity, how-to',
  },
  'poster-display': {
    display: 'Shrikhand',
    displayWeight: 400,
    meta: 'Poppins',
    metaWeight: 600,
    accent: 'Caveat',
    accentWeight: 700,
    when: 'a culture, music or opinion piece where the headline is the design',
  },
  editorial: {
    display: 'Fraunces',
    displayWeight: 700,
    meta: 'JetBrains Mono',
    metaWeight: 500,
    accent: 'Caveat',
    accentWeight: 700,
    when: 'an essay, history or analysis: the voice is written, not spoken',
  },
  archival: {
    display: 'Libre Caslon Text',
    displayWeight: 700,
    meta: 'Space Mono',
    metaWeight: 700,
    accent: 'Kalam',
    accentWeight: 700,
    when: 'financial, legal or historical material that must feel sourced',
  },
  'kinetic-impact': {
    display: 'Anton',
    displayWeight: 400,
    meta: 'JetBrains Mono',
    metaWeight: 500,
    accent: 'Caveat',
    accentWeight: 700,
    when: 'a statistic, a record, a hook — the number is the argument',
  },
  technical: {
    display: 'Space Grotesk',
    displayWeight: 700,
    meta: 'IBM Plex Mono',
    metaWeight: 500,
    accent: 'Kalam',
    accentWeight: 700,
    when: 'systems, code, data or infrastructure: precision over warmth',
  },
  handwritten: {
    display: 'Caveat',
    displayWeight: 700,
    meta: 'Nunito',
    metaWeight: 600,
    accent: 'Indie Flower',
    accentWeight: 400,
    when: 'a first-person or reflective piece where the voice is a person, not a brand',
  },
};