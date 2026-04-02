# Vilora Logo & Brand Identity

**Created:** April 2, 2026
**Status:** Exploration
**Priority:** Medium

---

## Brand Evolution

Vilora started as an AI mediation platform focused on conflict resolution. The brand is now broadening to represent **facilitating productive dialogue** in all its forms: mediation, brainstorming, decision-making, planning, and one-on-one conversations.

The logo and visual identity should reflect this broader mission while keeping mediation as a key use case.

---

## What Vilora Does

Vilora is an AI facilitator that helps people think together. It creates a space where:

- Two or more people can work through a disagreement constructively
- Someone can brainstorm or think through a decision with AI as a sounding board
- A group can plan, strategize, or make decisions with structured facilitation
- Individuals can talk things out one-on-one with a thoughtful, personalized AI advisor

The common thread: **productive dialogue that leads to better outcomes.**

---

## Brand Attributes

**Core qualities the logo should convey:**
- Constructive, not confrontational
- Warm but professional
- Intelligent without being cold or clinical
- Approachable and human-feeling
- Neutral and trustworthy
- Forward momentum (not static)

**What the logo should NOT feel like:**
- Corporate or enterprise software
- Therapy or mental health clinic
- Legal mediation or arbitration
- Generic chat/messaging app
- Conflict or tension

---

## Current Logo

The current mark is two leaf/branch shapes curving inward and meeting at a single point at the bottom, with a small filled circle at the convergence. It uses two shades of green (#1D9E75 primary, #085041 accent).

**What works:** Simple, clean, distinctive silhouette. Green palette feels calming and trustworthy. Works at small sizes (favicon).

**What to improve:** The two-sides-converging visual ties too closely to "two parties in conflict." It does not communicate brainstorming, planning, group discussion, or individual reflection. The mark should feel more expansive.

---

## Current Brand Colors

- Primary green: #1D9E75
- Dark accent: #085041
- Light green: #5DCAA5
- Background: #FAFAF7 (warm off-white)
- Text: #2C2C28

The green palette is a strong brand asset and should be retained. New logo concepts should work within this palette.

---

## Logo Concept Directions

### 1. Conversation Bloom
Two speech-bubble or petal shapes that overlap, forming a third shape (like a flower or spark) at the intersection. Represents dialogue that creates something new: ideas, decisions, understanding, resolution.

**Why it works:** Visually communicates "something emerges when people connect." Scales from 1-on-1 to group. Not tied to conflict.

### 2. Confluence
Two flowing lines or streams that merge into one and continue forward together. Unlike the current mark (which converges to a single point and stops), this conveys shared momentum and forward progress.

**Why it works:** Suggests movement, progress, and collaboration. Works for both conflict resolution (coming together) and brainstorming (ideas flowing together).

### 3. Resonance Circles
Two overlapping circles (Venn diagram-inspired) with a subtle glow, mark, or emphasis at the intersection. The overlap is the productive space where understanding, ideas, and decisions emerge.

**Why it works:** Universal symbol for shared ground. The intersection is the hero. Simple and iconic at any size.

### 4. The Prism
A simple geometric shape (triangle or prism) with light entering from one side and multiple lines or colors emerging. Represents Vilora helping people see a situation from multiple angles.

**Why it works:** Communicates perspective-shifting, which is core to both mediation and brainstorming. Distinctive and memorable.

### 5. Connected Nodes
Two or three dots connected by curved, organic lines (not rigid or corporate). Represents people thinking together, connected through dialogue. Visually scales from 1-on-1 to group naturally.

**Why it works:** Flexible, modern, and warm. The organic curves prevent it from feeling like a tech/network diagram.

### 6. The Spark
Two minimal lines or shapes approaching each other with a small starburst or spark between them. Represents the productive energy that happens when perspectives meet constructively.

**Why it works:** Simple, energetic, optimistic. Communicates that dialogue creates something. Works great at small sizes (favicon).

---

## Top Recommendations

**Conversation Bloom** and **The Spark** are the strongest candidates because:

- Both are simple enough for a favicon and work at all sizes
- Both communicate "something good happens when people connect" without being tied to conflict
- Both feel warm and human, not corporate
- Both leave room for the broader mission (brainstorming, decisions, planning)

---

## Technical Requirements

- Multi-color marks are welcome and encouraged (does not need to be monochrome, but should have a monochrome fallback for single-color contexts)
- Must be legible at 16x16px (favicon) and 36x36px (navbar)
- Must work on both light and dark backgrounds
- Should be implementable as inline SVG for fast loading
- Should pair well with the "VILORA" wordmark in Jost font
- Current favicon is SVG at static/img/favicon.svg
- Current inline SVG appears in templates/base.html (navbar) and templates/invite_landing.html

---

## Implementation Notes

When a new logo is selected, update these locations:
- `static/img/favicon.svg` (browser tab icon)
- `templates/base.html` line 22-26 (navbar logo SVG)
- Any other templates with inline SVG logo marks
- Email templates if applicable (notifications.py)
- Open Graph / social meta images if created

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial creation with 6 concept directions |
