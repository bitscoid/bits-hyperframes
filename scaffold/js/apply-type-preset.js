/**
 * Applies the chosen type preset to the DOM before the timeline is built.
 *
 * Writes the three CSS variables and declares the fonts the preset names, so
 * index.html carries no hardcoded family. Runs as a classic script (no module
 * loader) because the render contract forbids waiting on anything but the
 * registered timeline.
 *
 * Measured: a font declared but not preloaded lets the first frames render in
 * the fallback, and the contact sheet then shows two faces in one film. The
 * `font-display: block` plus the explicit document.fonts.load below prevents it.
 */
(function () {
  // Mirrors js/type-presets.mjs — kept inline so this file works without a
  // bundler. If you add a preset, add it here too.
  var PRESETS = {
    'playful-rounded': {display: 'Fredoka', meta: 'JetBrains Mono', accent: 'Caveat', dw: 600, mw: 500, aw: 700},
    'playful-bold': {display: 'Baloo2', meta: 'Nunito', accent: 'PatrickHand', dw: 700, mw: 700, aw: 400},
    'poster-display': {display: 'Shrikhand', meta: 'Poppins', accent: 'Caveat', dw: 400, mw: 600, aw: 700},
    editorial: {display: 'Fraunces', meta: 'JetBrains Mono', accent: 'Caveat', dw: 700, mw: 500, aw: 700},
    archival: {display: 'LibreCaslonText', meta: 'SpaceMono', accent: 'Kalam', dw: 700, mw: 700, aw: 700},
    'kinetic-impact': {display: 'Anton', meta: 'JetBrains Mono', accent: 'Caveat', dw: 400, mw: 500, aw: 700},
    technical: {display: 'SpaceGrotesk', meta: 'IBMPlexMono', accent: 'Kalam', dw: 700, mw: 500, aw: 700},
    handwritten: {display: 'Caveat', meta: 'Nunito', accent: 'IndieFlower', dw: 700, mw: 600, aw: 400},
  };

  // The file names shipped in assets/fonts/. A preset whose face is not here
  // falls back to the nearest bundled family; `check` does not catch that, so
  // keep this list in step with the folder.
  var FILES = {
    Fredoka: 'Fredoka.ttf',
    Baloo2: 'Baloo2.ttf',
    Shrikhand: 'Shrikhand.ttf',
    Caveat: 'Caveat.ttf',
    PatrickHand: 'PatrickHand.ttf',
  };

  // Families HyperFrames bundles by name — no @font-face needed.
  var BUNDLED = {
    Inter: 1, Montserrat: 1, Outfit: 1, Nunito: 1, Oswald: 1, 'League Gothic': 1,
    'Archivo Black': 1, 'Space Mono': 1, 'IBM Plex Mono': 1, 'JetBrains Mono': 1,
    'EB Garamond': 1, 'Playfair Display': 1, 'Source Code Pro': 1, 'Noto Sans JP': 1,
    Roboto: 1, 'Open Sans': 1, Lato: 1, Poppins: 1,
  };

  var key = window.BITS_TYPE_PRESET || '';
  var preset = PRESETS[key];

  if (!preset) {
    // Leave the CSS defaults in place; qc/type_gate.py is the thing that fails.
    console.warn('[type] BITS_TYPE_PRESET is not set; using the CSS defaults. Run qc/type_gate.py.');
    return;
  }

  var root = document.documentElement;
  root.style.setProperty('--font-display', "'" + preset.display + "', sans-serif");
  root.style.setProperty('--font-meta', "'" + preset.meta + "', monospace");
  root.style.setProperty('--font-accent', "'" + preset.accent + "', cursive");

  var families = [preset.display, preset.meta, preset.accent];
  var faces = '';
  families.forEach(function (fam) {
    if (BUNDLED[fam] || !FILES[fam]) return; // bundled, or shipped nowhere
    faces +=
      "@font-face{font-family:'" + fam + "';src:url('assets/fonts/" + FILES[fam] +
      "') format('truetype');font-display:block}\n";
  });
  if (faces) {
    var style = document.createElement('style');
    style.textContent = faces;
    document.head.appendChild(style);
  }
})();