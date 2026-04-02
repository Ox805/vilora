# Vilora Logo Concepts — Design Exploration Addendum

**Created:** April 2, 2026
**Status:** In Progress — Bloom and Spark advancing to refinement
**Appends:** Vilora Logo & Brand Identity (logo_and_brand_identity.md)

---

## Summary

Four logo concept directions were designed and reviewed against the live site (vilora.ai). All concepts retain the Vilora green palette (#1D9E75 / #085041 / #5DCAA5) and Jost Light wordmark. Each mark includes a subtle "quantum orbital" field — very thin elliptical arcs at low opacity with small particle nodes — suggesting ideas in circulation, drawn toward the focal point of the mark.

**Top picks advancing to refinement:** Conversation Bloom, The Spark

---

## Concept 01 — Conversation Bloom ★ ADVANCING

Two organic leaf shapes cross at the center to form a 4-petal mark. Two perspectives intersecting to create something entirely new. The orbital field aligns with the 4-petal axes.

**Strengths:**
- Reads as expansive and generative, not convergent and closed
- Strong favicon: center dot dominates at 16px
- All three greens work in the mark (primary / accent / dark)
- Works on light and dark backgrounds without modification

**SVG Mark (60×60 viewBox):**

```svg
<!-- Light background version -->
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Orbital field — adjust opacity for desired subtlety -->
  <g fill="none" stroke="#5DCAA5" opacity="0.12">
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(25,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(-25,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="16" ry="6.5" transform="rotate(80,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.22">
    <circle cx="7.5" cy="19.5" r="1.1"/>
    <circle cx="52.5" cy="40.5" r="1.1"/>
    <circle cx="52.5" cy="19.5" r="1"/>
    <circle cx="7.5" cy="40.5" r="1"/>
    <circle cx="27" cy="14" r="0.9"/>
    <circle cx="33" cy="46" r="0.9"/>
  </g>
  <!-- Main mark -->
  <path d="M12,12 C12,24 24,48 48,48 C48,36 36,12 12,12Z" fill="#1D9E75"/>
  <path d="M48,12 C48,24 36,48 12,48 C12,36 24,12 48,12Z" fill="#085041"/>
  <circle cx="30" cy="30" r="7" fill="#5DCAA5"/>
</svg>
```

```svg
<!-- Dark background version — swap #085041 leaf to #5DCAA5, center dot to white -->
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#5DCAA5" opacity="0.20">
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(25,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(-25,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="16" ry="6.5" transform="rotate(80,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.32">
    <circle cx="7.5" cy="19.5" r="1.1"/>
    <circle cx="52.5" cy="40.5" r="1.1"/>
    <circle cx="52.5" cy="19.5" r="1"/>
    <circle cx="7.5" cy="40.5" r="1"/>
    <circle cx="27" cy="14" r="0.9"/>
    <circle cx="33" cy="46" r="0.9"/>
  </g>
  <path d="M12,12 C12,24 24,48 48,48 C48,36 36,12 12,12Z" fill="#1D9E75"/>
  <path d="M48,12 C48,24 36,48 12,48 C12,36 24,12 48,12Z" fill="#5DCAA5"/>
  <circle cx="30" cy="30" r="7" fill="white"/>
</svg>
```

**Monochrome fallback (single color):**
```svg
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12,12 C12,24 24,48 48,48 C48,36 36,12 12,12Z" fill="#1D9E75"/>
  <path d="M48,12 C48,24 36,48 12,48 C12,36 24,12 48,12Z" fill="#1D9E75" opacity="0.6"/>
  <circle cx="30" cy="30" r="7" fill="white"/>
</svg>
```

**Implementation files:**
- `static/img/favicon.svg` — use viewBox="0 0 60 60" version above
- `templates/base.html` lines 22–26 — inline SVG at width="28" height="28" viewBox="0 0 60 60"
- `templates/invite_landing.html` — same inline SVG

---

## Concept 02 — The Spark ★ ADVANCING

Two arms sweep upward from below, converging at a central starburst. Dialogue as ignition — perspectives meeting and generating light. The orbital field creates a broad energy corona.

**Strengths:**
- Energetic, optimistic, forward-looking
- Favicon simplifies cleanly: two arms + circle dot, rays drop out at 16px
- Strong on dark backgrounds

**SVG Mark (60×60 viewBox):**

```svg
<!-- Light background version -->
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#5DCAA5" opacity="0.12">
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(30,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(-30,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="22" ry="5" transform="rotate(5,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.22">
    <circle cx="8" cy="17.5" r="1.1"/>
    <circle cx="52" cy="42.5" r="1.1"/>
    <circle cx="52" cy="17.5" r="1"/>
    <circle cx="8" cy="42.5" r="1"/>
    <circle cx="55" cy="31" r="0.9"/>
    <circle cx="5" cy="29" r="0.9"/>
  </g>
  <!-- Arms -->
  <path d="M6,52 C12,38 20,33 27,30.5" stroke="#085041" stroke-width="4.5" stroke-linecap="round"/>
  <path d="M54,52 C48,38 40,33 33,30.5" stroke="#1D9E75" stroke-width="4.5" stroke-linecap="round"/>
  <!-- Center spark -->
  <circle cx="30" cy="30" r="5" fill="#1D9E75"/>
  <!-- Rays -->
  <g stroke="#5DCAA5" stroke-width="1.6" stroke-linecap="round">
    <line x1="30" y1="22.5" x2="30" y2="20"/>
    <line x1="36" y1="25" x2="37.8" y2="23.4"/>
    <line x1="38.5" y1="30" x2="41" y2="30"/>
    <line x1="36" y1="35" x2="37.8" y2="36.6"/>
    <line x1="30" y1="37.5" x2="30" y2="40"/>
    <line x1="24" y1="35" x2="22.2" y2="36.6"/>
    <line x1="21.5" y1="30" x2="19" y2="30"/>
    <line x1="24" y1="25" x2="22.2" y2="23.4"/>
  </g>
</svg>
```

```svg
<!-- Dark background version -->
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#5DCAA5" opacity="0.20">
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(30,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(-30,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="22" ry="5" transform="rotate(5,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.32">
    <circle cx="8" cy="17.5" r="1.1"/>
    <circle cx="52" cy="42.5" r="1.1"/>
    <circle cx="52" cy="17.5" r="1"/>
    <circle cx="8" cy="42.5" r="1"/>
    <circle cx="55" cy="31" r="0.9"/>
    <circle cx="5" cy="29" r="0.9"/>
  </g>
  <path d="M6,52 C12,38 20,33 27,30.5" stroke="#5DCAA5" stroke-width="4.5" stroke-linecap="round"/>
  <path d="M54,52 C48,38 40,33 33,30.5" stroke="#1D9E75" stroke-width="4.5" stroke-linecap="round"/>
  <circle cx="30" cy="30" r="5" fill="#5DCAA5"/>
  <g stroke="rgba(255,255,255,0.5)" stroke-width="1.6" stroke-linecap="round">
    <line x1="30" y1="22.5" x2="30" y2="20"/>
    <line x1="36" y1="25" x2="37.8" y2="23.4"/>
    <line x1="38.5" y1="30" x2="41" y2="30"/>
    <line x1="36" y1="35" x2="37.8" y2="36.6"/>
    <line x1="30" y1="37.5" x2="30" y2="40"/>
    <line x1="24" y1="35" x2="22.2" y2="36.6"/>
    <line x1="21.5" y1="30" x2="19" y2="30"/>
    <line x1="24" y1="25" x2="22.2" y2="23.4"/>
  </g>
</svg>
```

**Favicon simplification (16px — drop rays, scale dot up):**
```svg
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6,52 C12,38 20,33 27,30.5" stroke="#085041" stroke-width="5" stroke-linecap="round"/>
  <path d="M54,52 C48,38 40,33 33,30.5" stroke="#1D9E75" stroke-width="5" stroke-linecap="round"/>
  <circle cx="30" cy="30" r="7" fill="#1D9E75"/>
</svg>
```

---

## Concept 03 — Confluence

Two streams enter from the top, merge at center, and continue forward. Shared momentum after dialogue. A vertical orbital adds depth.

**Status:** Hold — evaluate after Bloom/Spark refinement

**SVG Mark (60×60 viewBox):**

```svg
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <g fill="none" stroke="#5DCAA5" opacity="0.12">
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(20,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="25" ry="10" transform="rotate(-20,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="16" ry="6" transform="rotate(90,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.22">
    <circle cx="6.5" cy="21.5" r="1.1"/>
    <circle cx="53.5" cy="38.5" r="1.1"/>
    <circle cx="53.5" cy="21.5" r="1"/>
    <circle cx="6.5" cy="38.5" r="1"/>
    <circle cx="30" cy="14.5" r="0.9"/>
    <circle cx="30" cy="45.5" r="0.9"/>
  </g>
  <path d="M14,5 C17,17 22,25 28.5,31" stroke="#1D9E75" stroke-width="5" stroke-linecap="round"/>
  <path d="M46,5 C43,17 38,25 31.5,31" stroke="#085041" stroke-width="5" stroke-linecap="round"/>
  <circle cx="30" cy="32" r="5.5" fill="#5DCAA5"/>
  <path d="M30,37.5 L30,54" stroke="#5DCAA5" stroke-width="5" stroke-linecap="round"/>
</svg>
```

---

## Concept 04 — Resonance

Two overlapping rings — the intersection is the hero. Orbital planes at offset angles add dimensionality.

**Status:** Hold — evaluate after Bloom/Spark refinement

**SVG Mark (60×60 viewBox):**

```svg
<svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="resonance-clip">
      <circle cx="22" cy="30" r="15"/>
    </clipPath>
  </defs>
  <g fill="none" stroke="#5DCAA5" opacity="0.12">
    <ellipse cx="30" cy="30" rx="22" ry="9" transform="rotate(40,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="22" ry="9" transform="rotate(-10,30,30)" stroke-width="0.6"/>
    <ellipse cx="30" cy="30" rx="14" ry="5.5" transform="rotate(70,30,30)" stroke-width="0.5"/>
  </g>
  <g fill="#5DCAA5" opacity="0.22">
    <circle cx="13" cy="16" r="1.1"/>
    <circle cx="47" cy="44" r="1.1"/>
    <circle cx="52" cy="26" r="1"/>
    <circle cx="8" cy="34" r="1"/>
    <circle cx="25" cy="16" r="0.9"/>
    <circle cx="35" cy="44" r="0.9"/>
  </g>
  <circle cx="22" cy="30" r="15" stroke="#1D9E75" stroke-width="2.5"/>
  <circle cx="38" cy="30" r="15" stroke="#085041" stroke-width="2.5"/>
  <circle cx="38" cy="30" r="15" fill="#1D9E75" fill-opacity="0.18" clip-path="url(#resonance-clip)"/>
  <circle cx="30" cy="30" r="4.5" fill="#1D9E75"/>
</svg>
```

---

## Orbital Circulation Treatment

All concepts include a "quantum orbital" field rendered behind the main mark. This adds a sense of ideas in circulation — concepts, perspectives, and energy orbiting around and flowing into the mark's focal point.

### Technical parameters

| Element | Light bg | Dark bg |
|---|---|---|
| Orbital stroke-width | 0.5–0.6px | 0.5–0.6px |
| Orbital opacity | 0.12 | 0.20 |
| Particle dot opacity | 0.22 | 0.32 |
| Particle dot radius | 0.9–1.1 | 0.9–1.1 |

### Orbital geometry

Each concept uses three ellipses centered on the mark's focal point (30,30 in a 60×60 viewBox):

| Concept | Orbit A | Orbit B | Orbit C |
|---|---|---|---|
| Bloom | rotate(25°) rx=25 ry=10 | rotate(−25°) rx=25 ry=10 | rotate(80°) rx=16 ry=6.5 |
| Spark | rotate(30°) rx=25 ry=10 | rotate(−30°) rx=25 ry=10 | rotate(5°) rx=22 ry=5 |
| Confluence | rotate(20°) rx=25 ry=10 | rotate(−20°) rx=25 ry=10 | rotate(90°) rx=16 ry=6 |
| Resonance | rotate(40°) rx=22 ry=9 | rotate(−10°) rx=22 ry=9 | rotate(70°) rx=14 ry=5.5 |

### Scaling behavior

- **42–48px (navbar):** Full effect visible — three orbits + all particle nodes
- **36px:** Orbits and particles present but finer; same SVG scales naturally
- **16px (favicon):** Orbitals effectively invisible (stroke renders < 0.2px) — correct behavior, mark reads clean

---

## Color Reference

| Token | Hex | Usage |
|---|---|---|
| Primary green | #1D9E75 | Primary mark element, orbital strokes |
| Dark accent | #085041 | Secondary mark element (light bg), deep shadows |
| Light green | #5DCAA5 | Center accent, orbital particles, dark bg secondary |
| Background | #FAFAF7 | Site warm off-white |
| Text | #2C2C28 | Body copy |
| Dark bg | #0b1e1a | Dark preview panel |

---

## Wordmark Specification

- Font: Jost Light (weight 300)
- Case: ALL CAPS — `VILORA`
- Letter-spacing: 0.17–0.18em
- Font size in navbar context: 16–18px
- CDN: `https://cdn.jsdelivr.net/npm/@fontsource/jost@5/300.css`

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial concept exploration — 4 directions, orbital treatment added, Bloom and Spark advancing |
