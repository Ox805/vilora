# Mobile UI Optimization

**Created:** April 2, 2026
**Last Updated:** April 4, 2026
**Status:** In Progress (audit findings partially fixed, Phase 2 redesign pending implementation)
**Dependencies:** None (can begin independently)
**Priority:** High. Majority of consumer app usage happens on mobile. Current UI is desktop-first.
**Design Reference:** `developer-guides/architecture/design-reference.md`

---

## Problem Statement

Vilora was built desktop-first. While the CSS includes some `@media (max-width: 768px)` breakpoints, the mobile experience has not been systematically reviewed or optimized. For a consumer app focused on personal conversations, mediation, and brainstorming, mobile is likely the primary device for most users. Key issues include:

- Touch targets may be too small for comfortable mobile use
- Modals may not display well on small screens
- The session chat interface needs to work well with on-screen keyboards
- Navigation may be cluttered on narrow screens
- The Council results panel needs a mobile-friendly layout
- Voice input and Polish buttons need mobile-appropriate placement
- Text input areas need to work well with mobile keyboards
- Session creation flows (chooser, framing, tone chips) need to fit mobile screens

---

## Audit Scope

Every page and component needs to be reviewed on mobile viewports (375px, 414px, 390px widths). The audit should cover:

### Pages to Review

| Page | File | Key Concerns |
|------|------|-------------|
| Landing | `templates/landing.html` | Hero layout, feature grid, steps grid, CTA button sizing |
| Login/Register | `templates/login.html` | Form layout, password toggle touch target, auth toggle |
| Invite Landing | `templates/invite_landing.html` | Topic card, auth form, "What to expect" section |
| Dashboard | `templates/dashboard.html` | Session cards, delete button, new session button |
| Session Chooser | `templates/dashboard.html` | Chooser options stacking, tone chips wrapping |
| Framing Modal | `templates/dashboard.html` | Textarea sizing, "Help me frame this" button |
| Personal Session Modal | `templates/dashboard.html` | Textarea, tone chips |
| Direct Form Modal | `templates/dashboard.html` | Select dropdown, perspective textarea, tone chips |
| Council Modal | `templates/dashboard.html` + `session.html` | Question/context textareas, results display |
| Session Room | `templates/session.html` | Message list, input area, header actions, invite banner |
| Summary Panel | `templates/session.html` | Side panel on desktop becomes full-screen overlay on mobile |
| Council Panel | `templates/session.html` | Same as summary panel |
| Invite Modal | `templates/session.html` | Email input, personal note, success banner |
| Welcome Modal | `templates/session.html` | Welcome content, tips, "Got it" button |
| About Me | `templates/about_me.html` | Memory cards, onboarding flow, action buttons |
| Settings | `templates/settings.html` | Settings chips, preference layout |
| Forgot Password | `templates/forgot_password.html` | Simple form, should work but verify |
| Reset Password | `templates/reset_password.html` | Password fields, toggle buttons |

### Components to Review

| Component | File | Key Concerns |
|-----------|------|-------------|
| Navbar | `templates/base.html` | Logo + wordmark + nav links may overflow on mobile |
| Footer | `templates/base.html` | Should be simple, verify spacing |
| Modals | `static/css/style.css` | Should be full-width on mobile, scrollable if tall |
| Tone Chips | `static/css/style.css` | Need to wrap properly, touch-friendly sizing |
| Polish Button | `static/js/polish.js` | Position relative to textarea on mobile |
| Voice Button | `static/js/voice.js` | Touch target size, position inside textarea |
| Message Bubbles | `static/css/style.css` | Max-width on mobile, readable font size |
| Invite Banner | `static/css/style.css` | Link input + copy button + send invite layout |
| Session Cards | `static/css/style.css` | Card layout, delete button, date display |
| Onboarding Steps | `templates/about_me.html` | Step navigation, field layout, progress bar |
| Emoji Reactions | `templates/session.html` + `static/css/style.css` | Reaction picker positions as bottom sheet on mobile, pill touch targets, add-reaction button visibility |

---

## Implementation Plan

### Phase 1: Foundation (Viewport, Navbar, Base Layout)

#### 1.1 Viewport and Base

- Verify `<meta name="viewport" content="width=device-width, initial-scale=1.0">` on all pages (already in base.html, verify invite_landing.html)
- Set `body { -webkit-text-size-adjust: 100%; }` to prevent iOS text zoom
- Ensure no horizontal scroll on any page

#### 1.2 Navbar

Mobile navbar should:
- Keep logo (mark only, hide wordmark on very small screens)
- Collapse nav links into a hamburger menu or simplify to essential links
- Options:
  - **Simple:** Hide "About Me" and "Settings" links on mobile, keep "Dashboard" and "Logout"
  - **Hamburger:** Collapse all links behind a menu icon
  - Recommendation: Start with simple approach, add hamburger if needed

```css
@media (max-width: 480px) {
    .nav-wordmark { display: none; }
    .nav-links { gap: 0.5rem; }
    .nav-links a, .nav-user { font-size: 0.8rem; }
}
```

#### 1.3 Container

- Reduce padding on mobile: `padding: 1rem` (already exists, verify)
- Ensure max-width doesn't cause issues

### Phase 2: Session Room (Most Critical -- Maximize Chat Space)

The session room is where users spend the most time. The #1 goal on mobile is **maximizing vertical space for the chat messages** while keeping actions accessible. Follow the design principle used by ChatGPT and other leading chat UIs: every pixel not devoted to messages needs to justify its existence.

#### 2.1 Header: Single-Row, Compact

The current mobile header stacks the title and actions into two rows, wasting ~40px of vertical space. Redesign to a single compact row:

- **Topic title:** Truncate with ellipsis on one line. Keep the session type badge inline (e.g., "Apartment noise is... `General`"). CSS: `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`
- **Action links:** Replace "Participants", "Council", and "Summary" outlined `btn-sm` buttons with plain text links in green (`color: var(--primary); background: none; border: none; padding: 0; font-size: 0.8rem;`). These are secondary actions and do not need button chrome on mobile. Place them on the same line as the title, right-aligned.
- **Result:** The entire header fits in one ~36px row instead of two rows at ~70px total.

```css
@media (max-width: 480px) {
    .room-header {
        flex-direction: row;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .room-header h2 {
        flex: 1;
        min-width: 0;  /* allows ellipsis to work in flex */
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 1rem;
    }
    .room-actions .btn {
        background: none;
        border: none;
        padding: 0;
        color: var(--primary);
        font-size: 0.8rem;
        min-height: auto;
    }
}
```

#### 2.2 Message List: Edge-to-Edge, Maximum Width

Remove visual chrome from the message list to maximize space, following ChatGPT's mobile pattern:

- Remove `border` and `border-radius` from `.message-list` on mobile (the container doesn't need a visible box)
- Reduce padding from `1rem` to `0.5rem`
- Increase message `max-width` to `90-95%` on mobile
- Ensure `word-break: break-word` on all message content

```css
@media (max-width: 480px) {
    .message-list {
        border: none;
        border-radius: 0;
        padding: 0.5rem;
    }
    .message, .message-mediator, .message-intake {
        max-width: 95%;
    }
}
```

#### 2.3 Message Input Area: Flush Bottom, Minimal Chrome

- Remove `margin-top` on `.message-input-area` on mobile (no gap between messages and input)
- Reduce `border-radius` on `.message-input-bar` (less pill-shaped, more flush)
- Input bar sits flush at the bottom of the screen
- "Ask Vilora to weigh in" should be a **plain text link** on mobile, not a bordered button. Remove the button styling (`background`, `border`, `padding`) and render as a small green text link below the input, left-aligned. This saves ~12px of vertical space.

```css
@media (max-width: 480px) {
    .message-input-area {
        margin-top: 0.25rem;
    }
    .btn-ask-vilora {
        background: none;
        border: none;
        padding: 0.25rem 0;
        font-size: 0.75rem;
    }
}
```

#### 2.4 Emoji Reactions on Mobile

- Reaction picker renders as a fixed bottom sheet (`position: fixed; bottom: 0;`) -- already implemented
- Reaction pills need adequate touch targets (min 32px height, 44px preferred)
- Add-reaction button (smiley) is always visible on touch devices (no hover) -- already implemented
- Verify picker doesn't overlap the input area or get hidden behind the keyboard

#### 2.5 Invite Banner

- The link input + Copy + Send Invite row needs to stack on mobile
- Recommendation: Stack vertically (full-width input, buttons below)

#### 2.6 Summary and Council Panels

- Already has `width: 100%` on mobile (existing CSS, fixed April 4)
- Verify the panel fills the screen properly
- Ensure close button is easily tappable
- Council advisor details should be easy to expand/collapse with touch

#### 2.7 Overall Space Budget at 375px (Target)

```
Screen height:         667px (iPhone SE) / 844px (iPhone 14)

CURRENT (from iPhone 12 screenshot):
  Navbar:              ~44px
  Header (2 rows):     ~70px
  Message list border: ~2px + 32px padding
  Input area:          ~48px
  Ask Vilora button:   ~36px
  Footer:              ~60px
  Total chrome:        ~292px

TARGET (after Phase 2 changes):
  Navbar:              ~44px
  Header (single row): ~36px
  Message list:        no border, 16px padding
  Input area:          ~48px
  Ask Vilora text:     ~20px
  Footer:              HIDDEN on session page
  Total chrome:        ~164px

  Space savings:       ~128px more for chat messages
  Chat space:          ~503px (SE) / ~680px (14)
```

#### 2.8 Reference: Design Patterns from Leading Chat UIs

These patterns from ChatGPT, iMessage, and WhatsApp informed the recommendations above:

| Pattern | Description | Apply to Vilora |
|---------|-------------|-----------------|
| Minimal header | Single line, no outlined buttons, back arrow + title only | Compact single-row header with text-link actions |
| Edge-to-edge messages | No border/padding on chat container, messages use full width | Remove message-list border, reduce padding |
| Flush input bar | Input sits at true screen bottom with no margin/gap | Reduce margin, tighten input area |
| Progressive disclosure | Secondary actions hidden behind menus or smaller affordances | Actions as text links, not buttons |
| No visual containers | Chat area has no visible box/border, blends with background | Remove border-radius and border on mobile |

### Phase 3: Session Creation Flows

#### 3.1 Chooser Modal

- Options should stack vertically (likely already do)
- Each option needs adequate padding for touch
- Descriptions should remain readable

#### 3.2 Tone Chips

- Chips need to wrap properly on narrow screens
- Each chip needs min touch target (44px height recommended)
- Consider 2-column grid on mobile instead of flex-wrap
- Selected state should be clearly visible (not just border change)

#### 3.3 Form Modals

- All modals should be full-width on mobile with edge-to-edge padding
- Select dropdowns should use native mobile selectors
- Textareas should be comfortably sized

### Phase 4: Dashboard

#### 4.1 Session Cards

- Cards should be full-width on mobile
- Delete button should be always visible (not hover-only, since no hover on touch)
- Date/time display should be compact
- Session type badge and status should wrap if needed

#### 4.2 Dashboard Header

- "Your Sessions" + "New Session" button should stack if needed on very narrow screens

### Phase 5: Auth and Onboarding

#### 5.1 Login/Register

- Auth card should be nearly full-width on mobile
- Password toggle touch target needs to be adequate
- "Forgot password?" and auth toggle links need spacing for touch

#### 5.2 Invite Landing

- Topic card, auth form, and "What to expect" should flow naturally
- Register/login form should be easy to complete on mobile

#### 5.3 About Me Onboarding

- Each onboarding step should fit on one screen without excessive scrolling
- Progress bar should be visible
- Navigation buttons (Back/Next/Skip) should be fixed at the bottom or clearly visible
- Memory cards should stack and be easily editable

### Phase 6: Polish and Details

#### 6.1 Touch Targets

All interactive elements should have a minimum touch target of 44x44px (Apple HIG recommendation):
- Buttons
- Links
- Tone chips
- Voice mic button
- Polish button
- Copy button
- Delete buttons
- Expand/collapse triggers (Council advisor details)

#### 6.2 Spacing

- Increase vertical spacing between form elements on mobile
- Ensure modals have enough internal padding
- Bottom padding on pages to avoid content being hidden behind fixed elements

#### 6.3 Font Sizes

- Body text: min 14px on mobile (already using 0.95rem which is ~15px)
- Small text (timestamps, hints, badges): min 12px
- Headings: scale down proportionally but remain prominent

#### 6.4 Scroll Behavior

- Prevent body scroll when modals are open (already implemented for summary)
- Ensure session chat scrolls properly with on-screen keyboard
- Council/summary panels should scroll independently

#### 6.5 Orientation

- Test both portrait and landscape
- Landscape on phones: session room should still be usable (input area visible)

---

## Testing Approach

### Devices / Viewports to Test

| Device | Viewport | Priority |
|--------|----------|----------|
| iPhone SE | 375x667 | High (smallest common phone) |
| iPhone 14 | 390x844 | High (most common) |
| iPhone 14 Pro Max | 430x932 | Medium (large phone) |
| Pixel 7 | 412x915 | Medium (common Android) |
| iPad Mini | 744x1133 | Low (tablet) |
| iPad | 820x1180 | Low (tablet) |

### Testing Method

1. Use Chrome DevTools device emulation for initial development
2. Test on actual iOS device (Safari) for keyboard behavior and touch accuracy
3. Test on actual Android device for Chrome mobile behavior
4. Screenshot each page at 375px and 414px widths for review

### Key Scenarios to Test

- [ ] Complete registration flow on mobile
- [ ] Create a session using "help me frame it" flow on mobile
- [ ] Create a personal session on mobile
- [ ] Send messages in session room with on-screen keyboard
- [ ] Use voice input on mobile
- [ ] Use Polish on mobile
- [ ] View and dismiss summary panel on mobile
- [ ] Run Council on mobile
- [ ] Send an email invite on mobile
- [ ] Complete About Me onboarding on mobile
- [ ] Click invite link on mobile, register, and join session
- [ ] Delete a session on mobile
- [ ] Use forgot password flow on mobile

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| No horizontal scroll on any page | Visual inspection at 375px width |
| All touch targets are 44px+ | Measured in DevTools |
| Text is readable without zooming | Min 14px body text, 12px small text |
| Modals are usable on mobile | Full-width, scrollable, dismissable |
| Session room works with keyboard | Input stays visible when keyboard opens |
| Tone chips are tappable | 44px min height, adequate spacing |
| Navigation is usable | Essential links accessible, no overflow |
| Forms are completable | Inputs properly sized, labels visible |
| Council results are readable | Synthesis visible, advisors expandable |
| Page loads feel fast | No layout shift, images sized properly |

---

## CSS Architecture Notes

The current CSS uses a single breakpoint at `768px`. Consider adding:
- `480px` for small phones (navbar simplification)
- `768px` for tablets (current breakpoint)
- Use `min-width` for tablet/desktop enhancements rather than `max-width` for mobile fixes (mobile-first approach for new CSS)

All mobile CSS should be added to the existing `@media (max-width: 768px)` block in `style.css` or a new `@media (max-width: 480px)` block below it.

---

## References

- **Design Reference:** `developer-guides/architecture/design-reference.md`
- **Application Architecture:** `developer-guides/architecture/application-architecture.md`
- **Apple HIG Touch Targets:** 44x44pt minimum
- **Google Material Design:** 48x48dp recommended touch target

### Competitor Mobile Screenshots (iPhone 12, April 4, 2026)

These screenshots were captured on a real iPhone 12 and serve as reference for mobile design decisions. Saved in `developer-guides/references/mobile-screenshots/`.

| Screenshot | File | Key Observations |
|------------|------|-----------------|
| **Vilora session** | `vilora-session-iphone12.png` | Footer visible in chat view (~60px wasted). Three outlined action buttons take full row. Topic wraps to 2 lines. "Ask Vilora to weigh in" is a bordered pill button. Message list has visible border/padding. Emoji reaction smiley is visible below messages. |
| **ChatGPT chat** | `chatgpt-chat-iphone12.png` | Input bar flush at bottom, no footer, no extra buttons. Messages edge-to-edge with minimal padding. Header is one thin row. "Ask anything" input is clean with just mic and voice icons. No visible container borders. Disclaimer text is tiny and unobtrusive. |
| **Claude home** | `claude-home-iphone12.png` | Extremely clean and spacious. Minimal navigation chrome. Large greeting text, single input area. Action chips below input are compact text with small icons. No borders, no outlines on secondary actions. Warm background with no visual noise. |

**Key design principles observed in competitors:**
1. Chat views have zero footer -- every pixel goes to conversation
2. Action buttons are text/icon-only, never outlined buttons
3. Message containers have no visible borders or box styling
4. Input bar sits flush at screen bottom with no margin
5. Secondary actions (attachments, tools) are small icons or text links
6. Headers are single-line, minimal height
7. Overall aesthetic: content-first, chrome-last

---

## Code Audit Findings (April 2, 2026)

### CRITICAL Issues (Breaks Functionality on Mobile)

| Issue | Location | Status | Detail |
|-------|----------|--------|--------|
| ~~Summary panel overflow~~ | style.css | **FIXED 2026-04-03** | Added `width: 100%` at 480px breakpoint |
| Keyboard hides input | session.html | MITIGATED | Changed to `calc(100dvh - 120px)`. Needs real-device testing on iOS Safari |
| ~~Council panel overflow~~ | session.html | **FIXED 2026-04-03** | Same fix as summary panel |

### HIGH Issues (Accessibility/Usability)

| Issue | Location | Status | Detail |
|-------|----------|--------|--------|
| ~~Touch targets too small~~ | `.input-icon-btn` | **FIXED 2026-04-03** | Added 44px touch targets at 480px breakpoint |
| ~~Form inputs too short~~ | `.form-group input` | **FIXED 2026-04-03** | Addressed in 480px breakpoint |
| ~~`.btn-sm` too small~~ | style.css | **FIXED 2026-04-03** | Addressed in 480px breakpoint |
| ~~Settings/tone chips~~ | style.css | **FIXED 2026-04-03** | Addressed in 480px breakpoint |
| ~~Password toggle tiny~~ | `.password-toggle` | **FIXED 2026-04-03** | Addressed in 480px breakpoint |
| ~~Modal too wide~~ | `.modal-content` | **FIXED 2026-04-04** | Added `!important` to mobile max-width overrides |
| ~~Only one breakpoint~~ | style.css | **FIXED 2026-04-03** | 480px breakpoint now exists |
| Tone chips don't reflow | dashboard.html | OPEN | Chips are 140-200px wide. On 375px minus padding = 343px. Chips wrap unpredictably |
| ~~No word-break on messages~~ | `.message` | **FIXED 2026-04-03** | Added `word-break: break-word` |
| Footer visible in session chat | base.html / style.css | OPEN | Footer ("Vilora \| Strength through dialogue" + tagline) is visible in the session page on mobile, wasting ~60px. ChatGPT and Claude hide footers entirely in chat views. Should be hidden on session page on mobile. See competitor screenshots. |
| Session header wastes space | session.html | OPEN | Header stacks to 2 rows on mobile (~70px). Should be single compact row (~36px). See Phase 2.1 |
| Action buttons too heavy | session.html | OPEN | "Participants", "Council", "Summary" use outlined `btn-sm` on mobile. Should be plain text links. See Phase 2.1 |
| "Ask Vilora" button too heavy | session.html | OPEN | Bordered pill button wastes space. Should be plain text link on mobile. See Phase 2.3 |
| Message list has unnecessary chrome | style.css | OPEN | Border, border-radius, and 1rem padding on `.message-list` waste space on mobile. See Phase 2.2 |

### MEDIUM Issues (Polish)

| Issue | Location | Status | Detail |
|-------|----------|--------|--------|
| Hero text too large | style.css | OPEN | h1 stays 1.8rem down to 320px. Should be 1.4rem on phones |
| Onboarding buttons cramped | about_me.html | OPEN | "Skip for now" + "Back" + "Next" nearly touch on 360px |
| Delete button hard to tap | dashboard.html | OPEN | Session card delete button is ~32px. Below 44px target |
| Invite banner doesn't stack | session.html | OPEN | Link input + Copy + Send row stays horizontal on mobile |
| Settings saved toast | `.settings-saved` | OPEN | `position: fixed; right: 2rem` might overlap on small screens |
| ~~Navbar padding excessive~~ | style.css | **FIXED 2026-04-03** | Reduced at 480px breakpoint |
| No mobile font scaling | style.css | OPEN | All text sizes stay same from 320px to 767px |

### Specific Component Measurements at 375px

```
Available width: 375px
- Container padding (1rem each): 375 - 32 = 343px usable
- Modal (max-width 500px): constrained to 343px, edge-to-edge [FIXED]
- Summary panel: 100% width on mobile [FIXED]
- Tone chip (~150px): 2 per row max [OPEN]
- Session header: currently 2 rows (~70px), target 1 row (~36px) [OPEN]
- Message list padding: 1rem = 32px wasted, target 0.5rem [OPEN]
- Ask Vilora button: ~32px tall, target ~20px as text link [OPEN]
- Estimated space savings from Phase 2 changes: ~60px more chat space
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial creation. Comprehensive mobile audit scope and implementation plan |
| 2026-04-02 | Added code audit findings with specific measurements and severity ratings |
| 2026-04-03 | Audit run: Fixed .message-content, .welcome-topic, .invite-landing-topic word-break. Added 44px touch targets for .input-icon-btn, .btn-polish at 480px. Bumped .session-type-badge to 0.7rem. Fixed message-input-bar mobile override. Existing 480px breakpoint already covers: summary/council panels (100% width), btn-sm, btn-mic, tone/settings chips, password-toggle, form inputs, modals, invite banner stacking, onboarding buttons. Remaining: keyboard-hides-input (uses dvh but needs real device testing), .btn-polish still below 44px (36px, acceptable for secondary action) |
| 2026-04-04 | Added emoji reaction picker to component audit scope |
| 2026-04-04 | Added real-device screenshots (iPhone 12): Vilora session, ChatGPT chat, Claude home. Saved to `developer-guides/references/mobile-screenshots/`. Added competitor design principles reference table. Discovered footer visible in session chat (~60px wasted), added as HIGH issue. Updated space budget: 128px of savings identified |
| 2026-04-04 | Major rewrite of Phase 2 (Session Room): new "maximize chat space" direction. Single-row header with ellipsis title + text-link actions. Edge-to-edge message list (no border/padding). "Ask Vilora" as text link not button. Space budget analysis. Reference table of ChatGPT/iMessage/WhatsApp mobile patterns. Updated all audit findings with fix status and dates. Added new HIGH issues for header/button/message-list space waste |
| 2026-04-04 | Audit run: **Fixed** inline max-width styles on modals overriding mobile CSS (added `!important` to `.modal-content` max-width at both 768px and 480px breakpoints — inline styles like `max-width: 460px/480px/500px` on session.html, dashboard.html, about_me.html, base.html modals were defeating responsive overrides). **Fixed** iOS Safari scroll lock — added `html.modal-open { overflow: hidden }` in CSS and `document.documentElement.classList` toggle in api.js (iOS Safari requires overflow hidden on both html and body). Added `left: 0; right: 0` to `body.modal-open` for full iOS position anchoring. Added `.council-modal-content { max-width: 100% !important }` at 480px. **Puppeteer visual verification (375px + 1280px):** All 6 pages pass — landing, login, dashboard, session, about-me, settings. No horizontal overflow, no cut-off content, no overlapping elements, text readable on all pages. Screenshots saved to `/tmp/mobile-screenshots/`. **Remaining:** real-device testing on iOS Safari (scroll lock, keyboard behavior with dvh) and Android Chrome recommended. |
