# Mobile Responsiveness Audit

Run a comprehensive mobile responsiveness and layout audit of the Vilora application. Review every page and component for mobile optimization issues and fix them.

## Trigger Conditions

Run this audit:
- After significant UI changes
- Before major deployments
- When new pages or modals are added
- When users report mobile issues

## Audit Reference

Read `developer-guides/prompts/MOBILE_UI_OPTIMIZATION_PROMPT.md` for the full audit scope, known issues, implementation plan, and success criteria. Use it as your checklist.

## Step 1: Prerequisites Check

Before anything else, verify the foundation:

1. **Viewport meta tag:** Confirm every base template has `<meta name="viewport" content="width=device-width, initial-scale=1.0">`. Check:
   - `templates/base.html` (covers most pages)
   - `templates/invite_landing.html` (standalone page, own `<head>`)
   - Any other templates with their own `<head>` block

   If missing, add it. Nothing else in this audit matters without it.

2. **iOS text zoom prevention:** Check for `body { -webkit-text-size-adjust: 100%; }` in `static/css/style.css`. Add if missing.

## Step 2: Automated CSS Audit

Scan the CSS for mobile issues:

1. **Find all breakpoints:** Search `static/css/style.css` for `@media` queries. Verify breakpoints exist for 480px (small phones) and 768px (tablets). Flag any missing breakpoints.

2. **Find fixed widths:** Search CSS for any `width:` declarations with pixel values (not max-width, not 100%). Each one is a potential overflow on 375px screens. Check: summary panel, council panel, modals, cards.

3. **Find small touch targets:** Search for `padding: 0.2` through `padding: 0.35` on interactive elements (buttons, links, chips). Any button/link with total height below 44px fails accessibility. Check: `.btn-sm`, `.input-icon-btn`, `.btn-mic`, `.tone-chip`, `.med-tone-chip`, `.settings-chip`, `.password-toggle`, `.btn-delete`, `.btn-polish`.

4. **Find horizontal overflow risks:** Search for elements without `word-break: break-word` or `overflow-wrap: break-word` that contain user-generated text (messages, topics, perspectives).

5. **Check font sizes:** Search for `font-size` values below 0.8rem (12.8px). These may be unreadable on mobile. Flag any that appear on primary content (not just metadata).

## Step 3: Template-by-Template Review

For each template, read the file and check:

### Critical Pages (review these first)
- `templates/session.html` -- Chat interface, input bar, header buttons, invite banner, summary/council panels, welcome modal
- `templates/dashboard.html` -- Session cards, new session modals, tone chips, chooser options
- `templates/landing.html` -- Hero section, feature grid, steps, CTAs

### Important Pages
- `templates/about_me.html` -- Memory cards, onboarding flow, progress buttons
- `templates/settings.html` -- Preference chips, textarea
- `templates/invite_landing.html` -- Auth form, topic card, what to expect

### Auth Pages
- `templates/login.html` -- Form inputs, password toggle, forgot password link
- `templates/register.html` -- Same as login
- `templates/forgot_password.html` -- Simple form
- `templates/reset_password.html` -- Password fields

### For each page, check:
- [ ] Does it fit within 375px width without horizontal scroll?
- [ ] Are all interactive elements at least 44px tall?
- [ ] Is all text readable without zooming (min 14px body, 12px metadata)?
- [ ] Do modals display properly (full-width with padding, scrollable)?
- [ ] Does the layout adapt sensibly (stacking, wrapping)?
- [ ] Is there adequate spacing between tappable elements?
- [ ] On session page: does the input bar work with on-screen keyboard?

## Step 4: JavaScript Component Audit

Check these JS files for specific mobile-breaking patterns:

### `static/js/voice.js`
- Search for `insertBefore`, `appendChild`, `createElement('div')` -- does the mic button wrapper break `.form-group` positioning?
- Search for `position: absolute` or `position: static` -- is the mic button correctly positioned inside both `.message-input-icons` (session input bar) and `.form-group` (modal textareas)?
- Search for `closest('.message-input-bar')` -- does the fallback path correctly handle textareas NOT inside the input bar?
- Check: does `attachMicButton` create a `textarea-mic-wrapper` div that pulls the textarea out of its `.form-group`, breaking `position: relative` ancestry?

### `static/js/polish.js`
- Search for `insertBefore`, `after`, `appendChild` -- where does the polish bar end up relative to the textarea?
- Check: does `polishBar` have `position: absolute` CSS in `.form-group` context, or does it render as a block element below the textarea?
- Check: in `.message-input-icons`, is `polishBtn` inserted directly (no wrapper div) so flex layout works?
- Verify polish and mic buttons don't overlap at narrow widths.

### `static/js/api.js`
- Search for `modal-open`, `position: fixed`, `window.scrollY` -- does the scroll lock save/restore scroll position correctly?
- Check: does `position: fixed` on body work on iOS Safari? (iOS requires both `overflow: hidden` AND `position: fixed` with `top: -scrollY` to prevent background scroll.)
- Search for `MutationObserver` -- does it correctly detect modal open/close via style attribute changes?

## Step 5: Visual Verification via Chrome Remote Control

**IMPORTANT: Do NOT use Puppeteer or headless Chrome. Puppeteer does not work in this WSL environment and will hang indefinitely.**

Use the VS Code Chrome remote control (`/chrome`) to visually verify mobile layout:

1. **Open Chrome** using `/chrome` and navigate to `https://www.vilora.ai`

2. **Set mobile viewport** using Chrome DevTools device emulation:
   - Open DevTools (F12 or Ctrl+Shift+I)
   - Click the device toggle toolbar (phone/tablet icon) or Ctrl+Shift+M
   - Set viewport to iPhone SE (375x667) or iPhone 14 (390x844)

3. **Screenshot each page** at mobile viewport:
   - Landing page (`/`)
   - Login page (`/login`)
   - Dashboard (`/dashboard`) -- requires login
   - Session room (`/session/{id}`) -- open most recent session
   - About Me (`/about-me`)
   - Settings (`/settings`)

4. **For each page, check:**
   - Any horizontal scrollbar or content cut off on the right
   - Elements overlapping or misaligned
   - Text too small to read
   - Buttons/links that look too small to tap
   - Modals or panels that overflow the viewport

5. **Test interactions at mobile viewport:**
   - Open the "New Session" chooser and check layout
   - Open a tone chips section and verify wrapping
   - Open the participants panel
   - Click "Get Summary" or "Council" and check panel display

6. **Also verify via code analysis:**
   - Search templates for `style="max-width:` -- inline max-widths override CSS media queries at 480px
   - Calculate widths at 375px: container padding 16px*2 = 343px usable
   - Check that no elements exceed 343px without wrapping

## Step 6: Fix Issues

For each issue found:

1. **CSS fixes go in `static/css/style.css`** -- Add to existing `@media (max-width: 768px)` block or create `@media (max-width: 480px)` block for phone-specific fixes.

2. **Common fixes needed:**
   - Touch targets: increase padding to `0.5rem 1rem` minimum on buttons
   - Fixed-width panels: add `width: 100%` at mobile breakpoint
   - Modals: add `max-width: calc(100vw - 2rem)` and `max-height: 90vh; overflow-y: auto` at mobile
   - Text overflow: add `word-break: break-word` to user content containers
   - Input keyboard: consider `position: sticky; bottom: 0` for chat input on mobile
   - Font sizes: ensure minimum 14px for body text, 12px for metadata

3. **Do NOT change desktop layout** -- All mobile fixes should be inside media queries.

## Step 7: Update Audit Document

After fixing issues, update `developer-guides/prompts/MOBILE_UI_OPTIMIZATION_PROMPT.md`:
- Mark fixed items in the audit findings
- Add any new issues discovered
- Update the changelog

## Key Measurements Reference

```
iPhone SE:        375 x 667
iPhone 14:        390 x 844
iPhone 14 Pro Max: 430 x 932
Pixel 7:          412 x 915
Min touch target: 44 x 44 px (Apple HIG)
Min body text:    14px (0.875rem)
Min meta text:    12px (0.75rem)
```
