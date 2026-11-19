/**
 * Type presets — the register is chosen from the topic, and the build refuses to
 * run until it is.
 *
 * Why this file exists: the scaffold used to hardcode one pairing, so every film
 * from it used that pairing no matter the topic. A list of options does not
 * change behaviour; a required choice with a failing gate does.
 *
 * The HTML reads it through `js/type-preset.js`, which writes the three CSS
 * variables and the @font-face block. `qc/type_gate.py` fails until the key is
 * set, and fails again if the same folder already used it.
 */

/**
 * Set this from the topic's register in stage 4. Empty on purpose.
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
    display: 'Baloo2',
    displayWeight: 700,
    meta: 'Nunito',
    metaWeight: 700,
    accent: 'PatrickHand',
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
    display: 'LibreCaslonText',
    displayWeight: 700,
    meta: 'SpaceMono',
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
    display: 'SpaceGrotesk',
    displayWeight: 700,
    meta: 'IBMPlexMono',
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
    accent: 'IndieFlower',
    accentWeight: 400,
    when: 'a first-person or reflective piece where the voice is a person, not a brand',
  },
};