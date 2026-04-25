# Textarea Toolbar Redesign — Design Spec

**Date:** 2026-04-25
**Status:** Approved by user, awaiting implementation plan
**Reference image:** `C:\Users\grayt\Desktop\screenshots\Screenshot 2026-04-25 093147.png`

## Summary

Redesign the "compose" area used by the message-input box and the Council question/context boxes to match a new layout: taller default textarea, formatting toolbar on a row below the textarea, a tall blue vertical send button on the right (for `message-input` only), a new bullet-list formatting button, and user-draggable vertical resizing.

## Background

The current `message-input` bar in `templates/session.html` (lines 92-116) uses a horizontal pill layout with the textarea on the left and small icon buttons (Bold, Underline, attach, send) inline on the right. The Polish button is added by `attachPolish()` in `static/js/polish.js`. The mic button is added by `static/js/voice.js`. The Council question/context boxes share the Polish button but lack Bold/Underline.

The user wants a more "writing-friendly" compose area, modeled on a layout used in another project (the reference screenshot above): textarea takes more vertical space, formatting toolbar lives below the textarea, and the send action is a tall blue bar pinned to the right of the textarea.

## Scope

Five textareas, in two templates:

| Textarea | Template | Send bar? | Has B/U today? | Has B/U after? |
|----------|----------|-----------|----------------|----------------|
| `message-input` | `templates/session.html` | Yes | Yes | Yes |
| `council-question` | `templates/session.html` | No | No | Yes (added) |
| `council-context` | `templates/session.html` | No | No | Yes (added) |
| `dash-council-question` | `templates/dashboard.html` | No | No | Yes (added) |
| `dash-council-context` | `templates/dashboard.html` | No | No | Yes (added) |

Out of scope (no change): `invite-message` and the dashboard short-form fields `perspective`, `raw-input`, `personal-topic`.

## Layout

```
┌────────────────────────────────────────────┬──────┐
│                                            │      │
│   textarea (rows="4", ~110px default,      │      │
│   resize: vertical, drag handle visible    │ Send │   ← message-input only
│   bottom-right)                            │      │
│                                            │      │
├────────────────────────────────────────────┤      │
│  [Polish] [B] [U] [📎] [• ≡] [🎤]            │      │
└────────────────────────────────────────────┴──────┘
```

Council boxes use the same layout minus the right-side Send column. The Send column on `message-input` fills the full height of the wrapper, including any extra height the user adds by dragging the textarea taller.

Toolbar order, left to right: Polish (pill button), Bold, Underline, Attach (paperclip), Bullet list (NEW), Mic.

## HTML changes

For each affected textarea, replace the existing inline-icons structure with a new `.compose-bar` container holding three children:

- `.compose-textarea-row` — contains the textarea.
- `.compose-toolbar` — flex row containing Polish, B, U, attach, bullet, mic.
- `.compose-send` — vertical column containing the submit button (`message-input` only; omitted on Council boxes).

Set `rows="4"` on the affected textareas. Add B and U buttons to the four Council toolbars (they don't have them today). Add a new bullet-list button to all three toolbars between attach and mic.

The existing `.message-input-bar` and `.message-input-icons` classes can be retired for these five textareas. Before removing them globally, verify nothing else in `style.css` or the templates depends on them.

## JS changes

### Generalize `wrapSelection`

Current implementation in `templates/session.html` line 1340-1351 is hardcoded to `message-input`. Rewrite to `wrapSelection(textareaId, marker)` so the same function can serve all three boxes' B and U buttons. Update the Bold/Underline `onclick` handlers to pass the appropriate textarea ID.

### Add `toggleBulletList(textareaId)`

Behavior:

1. Determine the line range covered by the current selection. If no text is selected, use the line containing the cursor.
2. Examine the prefix of every line in that range.
3. If every line in the range already starts with `- ` (or `* `), remove the prefix from each (toggle off).
4. Otherwise, prepend `- ` to each line in the range (toggle on).
5. Restore selection to span the modified lines so the user can keep typing or click again to toggle off.

Edge cases:

- Empty textarea: insert `- ` at cursor position.
- Selection spans partial lines: extend to full-line boundaries before evaluating.
- Mixed lines (some bulleted, some not): treat as "toggle on" — prefix every line.

### Extend `formatText()` for bullet rendering

`formatText()` in `templates/session.html` (line 1353-1360) currently handles `**bold**` and `__underline__`. Add a step that detects blocks of consecutive lines starting with `- ` and wraps them in `<ul><li>` HTML.

Implementation approach: split the escaped HTML on newlines, walk the lines, and replace runs of lines matching `^- (.*)` with a single `<ul><li>line1</li><li>line2</li></ul>` block. Non-bullet lines pass through untouched. Apply bullet wrapping AFTER the existing bold/underline replacements so inline formatting inside a bullet item still works.

This affects how user messages display in the conversation. Council question/context content is sent to the LLM as plain text with `- ` prefixes (the LLM handles bullet semantics natively); the Council display path (line 1191, `escapeHtml(question)`) does not get bullet rendering in this change.

### Polish.js insertion logic

`polish.js` currently inserts the Polish button into either an icons container or a fallback `.polish-bar` after the textarea, depending on layout (see lines 41-56 of `polish.js`). Update `attachPolish()` to target the new `.compose-toolbar` row when present, and fall back to current behavior elsewhere so any textarea using `attachPolish` outside the redesign scope keeps working.

### Voice.js mic placement

`voice.js` positions the mic button. For some textareas it currently places the mic absolute-positioned inside a `.textarea-mic-wrapper`. With the redesign, the mic should live as a normal flex child inside `.compose-toolbar` for the 5 in-scope textareas. Verify the mic event listeners and recording state still work correctly with the new DOM placement; do not break voice.js for textareas outside the redesign scope.

## CSS changes

In `static/css/style.css`:

- `.compose-bar` — rounded border (1.5rem matching current `.message-input-bar`), background `var(--bg-card)`, border color animates to `var(--primary)` on `:focus-within`. Display flex, direction row (textarea+toolbar column on the left, send column on the right). The send column uses `align-self: stretch` so it fills the full height even when the textarea is dragged taller.
- The textarea + toolbar inside the left column live in their own flex column.
- Textarea inside `.compose-bar` — `resize: vertical`, default min-height enough for 4 rows (~110px), max-height raised significantly (suggested 400px) so drag-resize is meaningful. Width 100% of parent. Remove the existing `oninput` auto-grow handler since the user now controls height via the drag handle.
- `.compose-toolbar` — flex row, gap consistent with current `.message-input-icons`, padding consistent with the wrapper. Inherits the existing `.input-icon-btn` button styles for B, U, attach, bullet, mic.
- `.compose-send` — full-height vertical strip pinned to the right side of `.compose-bar`. Background `var(--primary)` (blue), white paper-plane icon centered. Width ~3rem. Right corners rounded to match the wrapper's `border-radius`. Hover state slightly darker primary or subtle elevation.
- Mobile breakpoint (existing breakpoints in style.css): the toolbar stays stacked below the textarea (do not reflow inline). Default height drops to ~3 rows on small screens. Send column width may need a small reduction. Drag handle still works.

## Out of scope

- Rich-text contenteditable editor (option C from brainstorm Q3). Kept as future possibility only.
- Rendering bullet lists inside the displayed Council question header at session.html line 1191 (currently uses `escapeHtml`). Council question/context content goes to the LLM as plain text with `- ` prefixes; the LLM handles bullet semantics. If desired later, the Council display can be extended to use `formatText()`.
- Other textareas: `invite-message`, `perspective`, `raw-input`, `personal-topic`.

## Testing

Manual smoke test on each of the 5 affected textareas:

- Layout visually matches the reference screenshot.
- Default height is ~4 lines.
- Drag the bottom-right corner downward, textarea grows; drag up, textarea shrinks. No horizontal resize.
- For `message-input`: vertical send bar fills the full height of the wrapper, including after the textarea is dragged taller.
- Bullet toggle: type three lines, select all, click bullet, all three lines get `- ` prefix. Click bullet again, prefixes removed. Click bullet with cursor in one line, only that line toggles.
- B/U: select text, click B, text gets wrapped in `**`. Click U, wrapped in `__`.
- Polish, attach file, mic, send all still work in their current behavior.
- "Ask the Council" submit button still works for the Council form.

Render verification:

- Send a message from `message-input` containing `- item one\n- item two\n- item three`. The rendered message bubble shows a real `<ul>` with three `<li>` items.
- Bold and underline inside a bullet item render correctly (e.g. `- **important** thing`).

Mobile verification:

- On a phone-width viewport, layout doesn't overflow horizontally; default height is reduced; toolbar still readable; drag-to-resize still works.

## Files expected to change

- `templates/session.html` — replace `message-input` compose markup; add new toolbars to `council-question` and `council-context`; generalize `wrapSelection` and add `toggleBulletList`; extend `formatText()`.
- `templates/dashboard.html` — add new toolbars to `dash-council-question` and `dash-council-context`.
- `static/css/style.css` — new `.compose-bar` / `.compose-toolbar` / `.compose-send` styles; mobile breakpoint adjustments; optional cleanup of `.message-input-bar` / `.message-input-icons` if unused after the change.
- `static/js/polish.js` — update `attachPolish` insertion logic to target `.compose-toolbar`.
- `static/js/voice.js` — verify mic placement works in the new toolbar; adjust if needed.
