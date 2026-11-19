/**
 * Applies the chosen type preset to the DOM before the timeline is built.
 *
 * Writes the three family variables and the three weight variables, and nothing
 * else. Every @font-face stays declared statically in index.html: `hyperframes
 * check` lints that file, not the DOM, so a face injected here is invisible to
 * it and fails `font_family_without_font_face`.
 *
 * Loaded AFTER the inline `window.BITS_TYPE_PRESET = ...` in <head>. It used to
 * run first, read an unset key and quietly fall back to the CSS defaults, which
 * is how every film ended up on the same pairing while the gate reported OK.
 *
 * An unset or unknown key throws, so the composition stops instead of rendering
 * in a family nobody chose. `qc/type_gate.py` reports the same thing earlier,
 * with the list of valid keys.
 */
(function () {
  // Mirrors js/type-presets.mjs. Both are read by qc/type_gate.py, which fails
  // when the two disagree, so this copy cannot drift unnoticed.
  var PRESETS = {
    'playful-rounded': {display: 'Fredoka', dw: 600, meta: 'JetBrains Mono', mw: 500, accent: 'Caveat', aw: 700},
    'playful-bold': {display: 'Baloo 2', dw: 700, meta: 'Nunito', mw: 700, accent: 'Patrick Hand', aw: 400},
    'poster-display': {display: 'Shrikhand', dw: 400, meta: 'Poppins', mw: 600, accent: 'Caveat', aw: 700},
    editorial: {display: 'Fraunces', dw: 700, meta: 'JetBrains Mono', mw: 500, accent: 'Caveat', aw: 700},
    archival: {display: 'Libre Caslon Text', dw: 700, meta: 'Space Mono', mw: 700, accent: 'Kalam', aw: 700},
    'kinetic-impact': {display: 'Anton', dw: 400, meta: 'JetBrains Mono', mw: 500, accent: 'Caveat', aw: 700},
    technical: {display: 'Space Grotesk', dw: 700, meta: 'IBM Plex Mono', mw: 500, accent: 'Kalam', aw: 700},
    handwritten: {display: 'Caveat', dw: 700, meta: 'Nunito', mw: 600, accent: 'Indie Flower', aw: 400},
  };

  var key = window.BITS_TYPE_PRESET || '';

  // 'custom' names its three families directly in index.html, right below the
  // preset key: {display: 'Family', meta: 'Family', accent: 'Family'}. The
  // eight presets are a starting point, not the allowed set.
  if (key === 'custom') {
    var c = window.BITS_TYPE_CUSTOM;
    if (!c || !c.display || !c.meta || !c.accent) {
      throw new Error('[type] BITS_TYPE_PRESET is "custom" but BITS_TYPE_CUSTOM is missing display/meta/accent.');
    }
    var apply = function (f, w, m, a) {
      var r = document.documentElement.style;
      r.setProperty('--font-display', "'" + f + "', sans-serif");
      r.setProperty('--font-meta', "'" + m + "', monospace");
      r.setProperty('--font-accent', "'" + a + "', cursive");
      r.setProperty('--font-display-weight', String(w || 400));
      r.setProperty('--font-meta-weight', String(w || 400));
      r.setProperty('--font-accent-weight', '700');
    };
    apply(c.display, c.displayWeight, c.meta, c.accent);
    return;
  }

  var preset = PRESETS[key];

  if (!preset) {
    throw new Error(
      '[type] window.BITS_TYPE_PRESET is ' +
        (key ? '"' + key + '" (not a preset)' : 'not set') +
        '. Pick the topic\'s register in stage 4: ' +
        Object.keys(PRESETS).join(', ')
    );
  }

  var root = document.documentElement;
  var set = function (name, value) {
    root.style.setProperty(name, value);
  };

  set('--font-display', "'" + preset.display + "', sans-serif");
  set('--font-meta', "'" + preset.meta + "', monospace");
  set('--font-accent', "'" + preset.accent + "', cursive");
  set('--font-display-weight', String(preset.dw));
  set('--font-meta-weight', String(preset.mw));
  set('--font-accent-weight', String(preset.aw));
})();