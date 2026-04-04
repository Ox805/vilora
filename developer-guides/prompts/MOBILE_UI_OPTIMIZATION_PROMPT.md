# Mobile UI Optimization

**Created:** April 2, 2026
**Status:** Planning
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

### Phase 2: Session Room (Most Critical)

The session room is where users spend the most time. It must work perfectly on mobile.

#### 2.1 Message Input Area

- Textarea should be full-width
- Send button should be easily tappable (min 44x44px touch target)
- Voice mic button needs adequate touch target
- Polish button should not overlap other elements
- On-screen keyboard consideration: when keyboard opens, the input area should remain visible and not be hidden behind the keyboard
- Consider: `position: sticky` for the input area at the bottom

#### 2.2 Message List

- Messages should use more width on mobile (max-width: 95% instead of 80%)
- Font size should remain readable (min 14px)
- Timestamps should be smaller but still readable
- Mediator messages should be clearly distinguished

#### 2.3 Header Actions

- "Council" and "Get Summary" buttons may overflow the header on narrow screens
- Options:
  - Stack vertically below the topic
  - Use icon-only buttons on mobile
  - Move to a "more actions" dropdown
  - Recommendation: Use a compact layout with smaller buttons

#### 2.4 Invite Banner

- The link input + Copy + Send Invite row needs to stack on mobile
- Recommendation: Stack vertically (full-width input, buttons below)

#### 2.5 Summary and Council Panels

- Already has `width: 100%` on mobile (existing CSS)
- Verify the panel fills the screen properly
- Ensure close button is easily tappable
- Council advisor details should be easy to expand/collapse with touch

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

---

## Code Audit Findings (April 2, 2026)

### CRITICAL Issues (Breaks Functionality on Mobile)

| Issue | Location | Detail |
|-------|----------|--------|
| Summary panel overflow | style.css line ~946 | `.summary-panel` is 480px fixed width. On 375px screen = 105px horizontal overflow. The 768px media query sets `width: 100%` but does not cover screens below 768px properly |
| Keyboard hides input | session.html | `.mediation-room` uses `height: calc(100vh - 140px)`. When mobile keyboard opens (50-60% of screen), input bar scrolls out of view. User types blind |
| Council panel same issue | session.html | Same 480px fixed width as summary panel |

### HIGH Issues (Accessibility/Usability)

| Issue | Location | Detail |
|-------|----------|--------|
| Touch targets too small | All `.input-icon-btn` | Send/mic buttons are ~29px (padding 0.35rem + 18px icon). Minimum should be 44px |
| Form inputs too short | style.css `.form-group input` | `padding: 0.6rem 0.75rem` = ~27px height. Below 44px touch target |
| `.btn-sm` too small | style.css | `padding: 0.25rem 0.75rem` = ~24px height |
| Settings/tone chips | style.css | `padding: 0.5rem 1rem` / `0.35rem 0.75rem` = ~28px height. Below 44px |
| Password toggle tiny | style.css `.password-toggle` | `padding: 0.25rem` + 20px SVG = ~28px. Hard to tap |
| ~~Modal too wide~~ | style.css `.modal-content` | **FIXED 2026-04-04:** Added `!important` to mobile max-width overrides at 768px and 480px breakpoints. Inline max-width styles on modals no longer defeat responsive CSS |
| Only one breakpoint | style.css | Single `@media (max-width: 768px)` breakpoint. Missing 480px for phones, 360px for small phones |
| Tone chips don't reflow | dashboard.html | Chips are 140-200px wide. On 375px minus padding = 343px. Chips wrap unpredictably |
| No word-break on messages | style.css `.message` | Long words in messages can cause horizontal overflow. Missing `word-break: break-word` |

### MEDIUM Issues (Polish)

| Issue | Location | Detail |
|-------|----------|--------|
| Hero text too large | style.css | h1 reduces to 1.8rem at 768px but stays 1.8rem down to 320px. Should be 1.4rem on phones |
| Onboarding buttons cramped | about_me.html | "Skip for now" + "Back" + "Next" use `justify-content: space-between`. On 360px screens buttons nearly touch |
| Delete button hard to tap | dashboard.html | Session card delete button is ~32px with `position: absolute`. Below 44px target |
| Invite banner doesn't stack | session.html | Link input + Copy + Send Invite row stays horizontal on mobile. Should stack vertically |
| Settings saved toast | style.css `.settings-saved` | `position: fixed; right: 2rem` might overlap content on small screens |
| Navbar padding excessive | style.css | `padding: 1rem 2rem`. 32px each side on 375px screen = 64px lost to padding |
| No mobile font scaling | style.css | All text sizes stay same from 320px to 767px. No progressive reduction |

### Specific Component Measurements at 375px

```
Available width: 375px
- Container padding (1rem each): 375 - 32 = 343px usable
- Modal (max-width 500px): constrained to 343px, edge-to-edge
- Summary panel (480px): OVERFLOWS by 105px
- Tone chip (~150px): 2 per row max
- Session type badge + Council btn + Summary btn: ~300px needed, barely fits
- Invite link input + Copy + Send: ~400px needed, OVERFLOWS
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-02 | Initial creation. Comprehensive mobile audit scope and implementation plan |
| 2026-04-02 | Added code audit findings with specific measurements and severity ratings |
| 2026-04-03 | Audit run: Fixed .message-content, .welcome-topic, .invite-landing-topic word-break. Added 44px touch targets for .input-icon-btn, .btn-polish at 480px. Bumped .session-type-badge to 0.7rem. Fixed message-input-bar mobile override. Existing 480px breakpoint already covers: summary/council panels (100% width), btn-sm, btn-mic, tone/settings chips, password-toggle, form inputs, modals, invite banner stacking, onboarding buttons. Remaining: keyboard-hides-input (uses dvh but needs real device testing), .btn-polish still below 44px (36px, acceptable for secondary action) |
| 2026-04-04 | Audit run: **Fixed** inline max-width styles on modals overriding mobile CSS (added `!important` to `.modal-content` max-width at both 768px and 480px breakpoints — inline styles like `max-width: 460px/480px/500px` on session.html, dashboard.html, about_me.html, base.html modals were defeating responsive overrides). **Fixed** iOS Safari scroll lock — added `html.modal-open { overflow: hidden }` in CSS and `document.documentElement.classList` toggle in api.js (iOS Safari requires overflow hidden on both html and body). Added `left: 0; right: 0` to `body.modal-open` for full iOS position anchoring. Added `.council-modal-content { max-width: 100% !important }` at 480px. **Verified OK:** viewport meta on all pages, touch targets at 480px, word-break on user content, summary/council panels 100% width, invite banner stacking, tone chip wrapping, font sizes (metadata 0.7-0.75rem acceptable). **Remaining:** Puppeteer visual testing blocked (browser launch hangs in WSL); recommend real-device testing on iOS Safari and Android Chrome. |
