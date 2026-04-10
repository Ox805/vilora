# Vilora Design Reference

**Last Updated:** 2026-04-10

## Brand Identity

**Tagline:** Strength through dialogue
**Subtitle:** AI-Powered Mediation

---

## Logo Variants

The Vilora mark is an abstract symbol of two paths converging to a shared point, representing dialogue leading to resolution.

| Variant | Use Case | File |
|---------|----------|------|
| **Primary Mark** | Landing page hero, centered/standalone use. Stacked: icon above, wordmark + tagline below | Inline SVG |
| **Horizontal Lockup** | Navbar/header. Icon mark + "VILORA" wordmark side by side | Inline SVG in `base.html` |
| **Icon Mark** | Favicon, app icon, small UI contexts | `static/img/favicon.svg` |

### Icon Mark Geometry

ViewBox: `0 0 58 58`

The icon consists of:
- **Left arm:** `M 8 9 C 6 26,23 43,29 47 M 18 9 C 17 28,25 44,29 47 M 8 9 L 18 9`
- **Right arm:** `M 50 9 C 52 26,35 43,29 47 M 40 9 C 41 28,33 44,29 47 M 40 9 L 50 9`
- **Dot:** `cx=29 cy=47 r=3`
- All strokes: `stroke-width="1.8" stroke-linecap="round"`
- Stroke on light bg: `#1D9E75` / Dot fill: `#085041`
- Stroke on dark bg: `#5DCAA5` / Dot fill: `#9FE1CB`
- Stroke on teal bg: `rgba(255,255,255,0.92)` / Dot fill: `white`

### Wordmark

- Text: `VILORA` (all caps)
- Font: Jost, weight 300 (light)
- Letter-spacing: 0.25em (nav), ~9px (primary mark)
- Color: `#2C2C2A` (near-black)

### Tagline

- Text: `AI-POWERED MEDIATION` (all caps)
- Font: Jost, weight 400
- Letter-spacing: ~3px
- Color: `#888780` (muted)

---

## Color Palette

| Name | Hex | CSS Variable | Usage |
|------|-----|-------------|-------|
| **Teal** | `#1D9E75` | `--primary` | Primary brand color, buttons, links, icon strokes |
| **Deep Teal** | `#0F6E56` | `--primary-dark` | Button hover, dark accents |
| **Dark** | `#085041` | `--accent` | Icon fill dot, self-message bubbles, feature headings |
| **Light Teal** | `#5DCAA5` | `--primary-light` | Light accent, icon on dark backgrounds |
| **Pale** | `#E1F5EE` | `--pale`, `--mediator-bg` | Mediator message background, subtle highlights |
| **Background** | `#F7F8F7` | `--bg` | Page background |
| **Card** | `#FFFFFF` | `--bg-card` | Card surfaces |
| **Text** | `#2C2C2A` | `--text` | Primary text |
| **Text Light** | `#555550` | `--text-light` | Secondary text |
| **Text Muted** | `#888780` | `--text-muted` | Tertiary text, timestamps |
| **Border** | `#E2E0D8` | `--border` | Borders, dividers |
| **Error** | `#E53E3E` | `--error` | Error states, delete buttons |

### Icon Mark on Different Backgrounds

| Background | Strokes | Dot |
|------------|---------|-----|
| Light/white | `#1D9E75` | `#085041` |
| Dark (`#04342C`) | `#5DCAA5` | `#9FE1CB` |
| Teal (`#1D9E75`) | `rgba(255,255,255,0.92)` | `#FFFFFF` |

---

## Typography

**Primary Font:** [Jost](https://fonts.google.com/specimen/Jost) (Google Fonts)

| Weight | Use |
|--------|-----|
| 300 (Light) | Wordmark, headings |
| 400 (Regular) | Body text, tagline, UI elements |
| 500 (Medium) | Labels, form field labels |

**Fallback Stack:** `'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`

---

## UI Components

### Buttons

- **Primary:** Background `--primary` (#1D9E75), white text. Hover: `--primary-dark`
- **Default:** White background, `--border` border, `--text` color
- **Delete:** `--error` border and text, appears on hover

### Message Bubbles

| Type | Alignment | Background | Text Color |
|------|-----------|------------|------------|
| Self (current user) | Right | `--accent` (#085041) | White |
| Other participant | Left | `#E6F4F1` | Dark, with name in `#2B7A6B` |
| Mediator (Vilora) | Left | `--mediator-bg` (#E1F5EE) | Dark |
| Intake | Left | `--intake-bg` (#F0FFF4), dashed border | Dark |

### Cards

- Background: `--bg-card`
- Border-radius: 8px (`--radius`)
- Shadow: `0 1px 3px rgba(0,0,0,0.08)`

---

## Meta / SEO

- **Page title format:** `{Page Name} — Vilora`
- **Favicon:** SVG icon mark at `static/img/favicon.svg`
- **OG tags:** Set in `base.html` with title, description, type, url

---

## Brand Source File

The complete brand sheet (primary mark, horizontal lockup, icon variants, and color swatches) is at:
`C:\Users\grayt\My Drive\projects\vilora\vilora-brand.svg`
