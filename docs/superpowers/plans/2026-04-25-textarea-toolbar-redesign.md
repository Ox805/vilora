# Textarea Toolbar Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the message-input compose area and the four Council question/context boxes to match the reference layout: 4-row default textarea with vertical drag-resize, a formatting toolbar (Polish, B, U, attach, bullet, mic) on a row beneath the textarea, and a tall blue vertical send bar on the right side of `message-input` only.

**Architecture:** Additive CSS classes (`.compose-bar`, `.compose-toolbar`, `.compose-send`) wrap each affected textarea in a new structure. JS hooks (`polish.js`, `voice.js`, inline session.html JS) detect the new toolbar and insert their buttons into it; existing fallback paths preserve current behavior for textareas outside the redesign scope. New `toggleBulletList` JS function performs markdown line-prefix toggling. `formatText()` rendering gets a regex pass that converts blocks of `- ` lines into `<ul><li>` HTML.

**Tech Stack:** Flask + Jinja2 templates, vanilla JavaScript, plain CSS (no preprocessor or framework). No JS unit-test framework in this repo; verification is manual smoke testing in the browser plus DevTools console assertions for pure-function logic.

**Spec:** See `docs/superpowers/specs/2026-04-25-textarea-toolbar-redesign-design.md`.

---

## Task 1: Add `.compose-bar` CSS foundation

**Files:**
- Modify: `static/css/style.css` (append a new section near the existing `/* === Message Input === */` block at line ~885)

This task is additive only. The new classes are not yet used by any HTML, so the page should look unchanged after this task lands. We're laying the foundation for Task 6 onward.

- [ ] **Step 1: Append new compose-bar CSS block**

Open `static/css/style.css` and insert this block immediately after the existing `.textarea-mic-wrapper .btn-mic { ... }` rule (around line 1004):

```css
/* === Compose Bar (textarea + toolbar + optional send column) === */
.compose-bar {
    display: flex;
    flex-direction: row;
    align-items: stretch;
    border: 1px solid var(--border);
    border-radius: 1.5rem;
    background: var(--bg-card);
    overflow: hidden;
    transition: border-color 0.2s;
    margin-top: 0.5rem;
}

.compose-bar:focus-within {
    border-color: var(--primary);
}

.compose-bar-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.compose-bar textarea {
    width: 100%;
    border: none;
    outline: none;
    padding: 0.75rem 1rem;
    font-family: inherit;
    font-size: 0.95rem;
    line-height: 1.4;
    background: transparent;
    resize: vertical;
    min-height: 110px;
    max-height: 400px;
    box-sizing: border-box;
}

.compose-toolbar {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.4rem 0.75rem 0.4rem 0.75rem;
    flex-shrink: 0;
}

.compose-toolbar .btn-polish {
    font-size: 0.75rem;
    padding: 0.3rem 0.6rem;
    border-radius: 1rem;
    opacity: 0.5;
    border: 1px solid var(--border);
    background: none;
    cursor: pointer;
    color: var(--text-light);
    transition: all 0.15s;
}

.compose-toolbar .btn-polish:hover {
    opacity: 1;
    border-color: var(--primary);
    color: var(--primary);
}

.compose-send {
    flex-shrink: 0;
    width: 3rem;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
    align-self: stretch;
}

.compose-send:hover {
    background: var(--primary-dark, var(--primary));
    filter: brightness(0.92);
}

.compose-send svg {
    width: 22px;
    height: 22px;
}
```

- [ ] **Step 2: Append mobile breakpoint rules**

Find the existing mobile breakpoint block in `style.css` (search for `.message-input-area { margin-top: 0.25rem; }` near line 2525). Append these rules inside the same `@media` block:

```css
.compose-bar { border-radius: 1.25rem; }
.compose-bar textarea { min-height: 80px; padding: 0.6rem 0.85rem; font-size: 0.9rem; }
.compose-toolbar { padding: 0.3rem 0.5rem; }
.compose-send { width: 2.5rem; }
.compose-send svg { width: 18px; height: 18px; }
```

- [ ] **Step 3: Verify the page still renders unchanged**

Run the Flask app locally and load any page that has the existing message-input bar (e.g. an active session). The layout should look identical to before this task — these classes are not yet used by any HTML.

```bash
cd /home/tim/dev/vilora && source venv/bin/activate && python app.py
```

Open the app in a browser and confirm: existing message-input pill bar still renders normally, no console errors, no visual regression on dashboard or session pages.

- [ ] **Step 4: Commit**

```bash
git add static/css/style.css
git commit -m "Add compose-bar CSS foundation for textarea toolbar redesign"
```

---

## Task 2: Generalize `wrapSelection` and add `toggleBulletList` (session.html JS)

**Files:**
- Modify: `templates/session.html` lines 1340-1351 (existing `wrapSelection` function) and append a new `toggleBulletList` function immediately after.

Today `wrapSelection` is hardcoded to operate on `message-input`. We're making it accept a textarea-id parameter so the same function can serve B/U buttons for the Council boxes too. We're also adding `toggleBulletList` for the new bullet button.

- [ ] **Step 1: Replace `wrapSelection` and add `toggleBulletList`**

Find this block in `templates/session.html` (around lines 1340-1351):

```javascript
function wrapSelection(marker) {
    const ta = document.getElementById('message-input');
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = ta.value;
    if (start === end) return; // nothing selected
    const selected = text.substring(start, end);
    ta.value = text.substring(0, start) + marker + selected + marker + text.substring(end);
    ta.selectionStart = start + marker.length;
    ta.selectionEnd = end + marker.length;
    ta.focus();
}
```

Replace it with:

```javascript
function wrapSelection(textareaId, marker) {
    const ta = document.getElementById(textareaId);
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = ta.value;
    if (start === end) return; // nothing selected
    const selected = text.substring(start, end);
    ta.value = text.substring(0, start) + marker + selected + marker + text.substring(end);
    ta.selectionStart = start + marker.length;
    ta.selectionEnd = end + marker.length;
    ta.focus();
}

function toggleBulletList(textareaId) {
    const ta = document.getElementById(textareaId);
    if (!ta) return;
    const text = ta.value;
    const selStart = ta.selectionStart;
    const selEnd = ta.selectionEnd;

    // Expand selection to full-line boundaries
    let lineStart = text.lastIndexOf('\n', selStart - 1) + 1;
    let lineEnd = text.indexOf('\n', selEnd);
    if (lineEnd === -1) lineEnd = text.length;

    const before = text.substring(0, lineStart);
    const block = text.substring(lineStart, lineEnd);
    const after = text.substring(lineEnd);

    // Empty textarea or empty line: insert "- " at cursor
    if (block === '') {
        ta.value = before + '- ' + after;
        ta.selectionStart = ta.selectionEnd = lineStart + 2;
        ta.focus();
        return;
    }

    const lines = block.split('\n');
    const allBulleted = lines.every(l => /^\s*[-*]\s/.test(l));

    let newLines;
    if (allBulleted) {
        // Toggle off: strip leading "- " or "* " (preserving any leading whitespace)
        newLines = lines.map(l => l.replace(/^(\s*)[-*]\s/, '$1'));
    } else {
        // Toggle on: prefix every non-empty line with "- "
        newLines = lines.map(l => l === '' ? l : '- ' + l);
    }

    const newBlock = newLines.join('\n');
    ta.value = before + newBlock + after;
    ta.selectionStart = lineStart;
    ta.selectionEnd = lineStart + newBlock.length;
    ta.focus();
}
```

- [ ] **Step 2: Update existing Bold/Underline onclick handlers in session.html**

Find these two lines (around 100-101):

```html
<button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('**')" title="Bold (wrap with **)"><strong>B</strong></button>
<button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('__')" title="Underline (wrap with __)"><u>U</u></button>
```

Update them to pass the textarea ID explicitly:

```html
<button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
<button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '__')" title="Underline (wrap with __)"><u>U</u></button>
```

- [ ] **Step 3: Verify Bold/Underline still work on `message-input`**

Reload the app, open a session, type `hello world` in the message input, select `world`, click the B button. Verify the textarea now contains `hello **world**`. Click U after selecting `hello`, verify result is `__hello__ **world**`. No JS console errors.

- [ ] **Step 4: Verify `toggleBulletList` logic in DevTools console**

Open the session page in the browser, open DevTools, switch to Console, paste this assertion script:

```javascript
(function () {
    const ta = document.getElementById('message-input');
    if (!ta) { console.log('FAIL: message-input not found'); return; }

    function reset(v, s, e) {
        ta.value = v;
        ta.selectionStart = s;
        ta.selectionEnd = e;
    }

    // Case 1: three lines, all selected, none bulleted -> all get "- "
    reset('a\nb\nc', 0, 5);
    toggleBulletList('message-input');
    console.log('Case 1:', ta.value === '- a\n- b\n- c' ? 'PASS' : 'FAIL ' + JSON.stringify(ta.value));

    // Case 2: same input now bulleted, toggle again -> bullets removed
    toggleBulletList('message-input');
    console.log('Case 2:', ta.value === 'a\nb\nc' ? 'PASS' : 'FAIL ' + JSON.stringify(ta.value));

    // Case 3: cursor on a single line, no selection -> only that line toggles
    reset('a\nb\nc', 2, 2); // cursor on line "b"
    toggleBulletList('message-input');
    console.log('Case 3:', ta.value === 'a\n- b\nc' ? 'PASS' : 'FAIL ' + JSON.stringify(ta.value));

    // Case 4: empty textarea -> inserts "- " at cursor
    reset('', 0, 0);
    toggleBulletList('message-input');
    console.log('Case 4:', ta.value === '- ' ? 'PASS' : 'FAIL ' + JSON.stringify(ta.value));

    // Case 5: mixed lines (some bulleted, some not) -> all get bulleted
    reset('- a\nb\n- c', 0, 8);
    toggleBulletList('message-input');
    console.log('Case 5:', ta.value === '- - a\n- b\n- - c' ? 'PASS' : 'FAIL ' + JSON.stringify(ta.value));

    ta.value = ''; // clean up
})();
```

Expected output: five PASS lines. If any FAIL appears, fix `toggleBulletList` before continuing.

- [ ] **Step 5: Commit**

```bash
git add templates/session.html
git commit -m "Generalize wrapSelection and add toggleBulletList for bullet toolbar button"
```

---

## Task 3: Extend `formatText()` to render bullet lists

**Files:**
- Modify: `templates/session.html` lines 1353-1360 (existing `formatText` function).

Today `formatText()` converts `**bold**` and `__underline__` to HTML. We add a step that wraps consecutive `- ` lines in `<ul><li>` blocks. This affects how user messages display in the conversation bubble.

- [ ] **Step 1: Replace `formatText`**

Find this block (around lines 1353-1360):

```javascript
function formatText(text) {
    let html = escapeHtml(text);
    // **bold** -> <strong>bold</strong>
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // __underline__ -> <u>underline</u>
    html = html.replace(/__(.+?)__/g, '<u>$1</u>');
    return html;
}
```

Replace it with:

```javascript
function formatText(text) {
    let html = escapeHtml(text);
    // **bold** -> <strong>bold</strong>
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // __underline__ -> <u>underline</u>
    html = html.replace(/__(.+?)__/g, '<u>$1</u>');

    // Wrap consecutive lines starting with "- " or "* " into <ul><li> blocks.
    // Apply after inline rules so bold/underline inside a bullet item still render.
    const lines = html.split('\n');
    const out = [];
    let bulletBuffer = [];
    const flush = () => {
        if (bulletBuffer.length === 0) return;
        out.push('<ul>' + bulletBuffer.map(l => '<li>' + l + '</li>').join('') + '</ul>');
        bulletBuffer = [];
    };
    for (const line of lines) {
        const m = /^[-*]\s+(.*)$/.exec(line);
        if (m) {
            bulletBuffer.push(m[1]);
        } else {
            flush();
            out.push(line);
        }
    }
    flush();
    return out.join('\n');
}
```

- [ ] **Step 2: Verify rendering with DevTools console**

Open a session page, open DevTools Console, paste:

```javascript
(function () {
    const cases = [
        // [input, expected]
        ['hello', 'hello'],
        ['**bold**', '<strong>bold</strong>'],
        ['- one\n- two', '<ul><li>one</li><li>two</li></ul>'],
        ['intro\n- one\n- two\noutro',
         'intro\n<ul><li>one</li><li>two</li></ul>\noutro'],
        ['- **important** thing',
         '<ul><li><strong>important</strong> thing</li></ul>'],
        ['no bullets here', 'no bullets here'],
        ['* alt marker', '<ul><li>alt marker</li></ul>'],
    ];
    for (const [input, expected] of cases) {
        const got = formatText(input);
        console.log(got === expected ? 'PASS' : 'FAIL', JSON.stringify(input), '->', JSON.stringify(got));
    }
})();
```

Expected output: all PASS. If any FAIL appears, fix the regex before continuing.

- [ ] **Step 3: Verify in a real conversation**

In the browser, open a session, type:

```
Here are my points:
- first point
- second with **bold** inside
- third
That's all.
```

Send the message. Verify the rendered message bubble shows a real `<ul>` with three `<li>` items, the bold renders inside the second item, and the surrounding lines ("Here are my points:" and "That's all.") render as normal text outside the list. Inspect via DevTools Elements panel to confirm the actual HTML.

- [ ] **Step 4: Verify backward compat**

Scroll back to older messages in the session that don't contain `- ` lines. Confirm they render exactly as before (no spurious `<ul>` insertion, no broken layout).

- [ ] **Step 5: Commit**

```bash
git add templates/session.html
git commit -m "Render markdown bullet lines as ul/li in message formatter"
```

---

## Task 4: Update `polish.js` to target `.compose-toolbar`

**Files:**
- Modify: `static/js/polish.js` lines 41-56 (the insertion logic in `attachPolish`).

Today `attachPolish` inserts the Polish button into either an `.message-input-icons` container or a fallback `.polish-bar` after the textarea. After the redesign, the in-scope textareas live inside `.compose-bar` with a `.compose-toolbar` row. Update the insertion logic to prefer `.compose-toolbar` when available, while preserving the existing fallback paths so out-of-scope textareas keep working.

- [ ] **Step 1: Update `attachPolish` insertion logic**

In `static/js/polish.js`, find this exact block (lines 41-57):

```javascript
    // Insert polish into icons area if in input bar, otherwise after textarea/mic-wrapper
    if (inputBar) {
        const iconsContainer = inputBar.querySelector('.message-input-icons');
        if (iconsContainer) {
            iconsContainer.insertBefore(polishBtn, iconsContainer.firstChild);
        } else {
            wrapper.appendChild(polishBar);
        }
        inputBar.after(preview);
    } else {
        // Place polish bar AFTER the textarea (or its mic wrapper if it exists)
        // This keeps it independent of the mic button
        const micWrapper = textarea.closest('.textarea-mic-wrapper');
        const insertAfter = micWrapper || textarea;
        insertAfter.after(preview);
        insertAfter.after(polishBar);
    }
```

Replace with:

```javascript
    // Preferred: place inside .compose-toolbar (new redesigned layout)
    const composeBar = textarea.closest('.compose-bar');
    if (composeBar) {
        const toolbar = composeBar.querySelector('.compose-toolbar');
        if (toolbar) {
            toolbar.insertBefore(polishBtn, toolbar.firstChild);
            composeBar.after(preview);
            polishBtn.id = textareaId + '-polish-btn';
            return;
        }
    }

    // Fallback: legacy .message-input-bar layout
    if (inputBar) {
        const iconsContainer = inputBar.querySelector('.message-input-icons');
        if (iconsContainer) {
            iconsContainer.insertBefore(polishBtn, iconsContainer.firstChild);
        } else {
            wrapper.appendChild(polishBar);
        }
        inputBar.after(preview);
    } else {
        // Place polish bar AFTER the textarea (or its mic wrapper if it exists)
        // This keeps it independent of the mic button
        const micWrapper = textarea.closest('.textarea-mic-wrapper');
        const insertAfter = micWrapper || textarea;
        insertAfter.after(preview);
        insertAfter.after(polishBar);
    }
```

The `return;` on the compose-bar branch ensures the fallback paths don't run when the new layout is detected. The line `polishBtn.id = textareaId + '-polish-btn';` already runs at line 60 of the existing file for non-compose paths; the new branch sets the same ID before returning so the rest of the file (event handlers that reference `textareaId + '-polish-btn'`) keeps working.

- [ ] **Step 2: Read the actual file and verify your edit**

Run a quick grep to confirm both the new compose-bar branch and the legacy fallbacks are present:

```bash
grep -n "compose-toolbar\|compose-bar\|message-input-bar\|textarea-mic-wrapper" static/js/polish.js
```

Expected: at least one match for each class string.

- [ ] **Step 3: Smoke test with current HTML**

Reload the app. The HTML hasn't changed yet, so all textareas still use legacy classes (`.message-input-bar` or no wrapper). Verify the Polish button still appears and works on:

- `message-input` in a session
- `council-question` in a session
- `council-context` in a session
- `dash-council-question` and `dash-council-context` on the dashboard

If any Polish button is missing or misplaced, the fallback paths regressed — fix before continuing.

- [ ] **Step 4: Commit**

```bash
git add static/js/polish.js
git commit -m "Polish.js: insert into compose-toolbar when present, keep legacy fallbacks"
```

---

## Task 5: Update `voice.js` to target `.compose-toolbar`

**Files:**
- Modify: `static/js/voice.js` lines 121-146 (the insertion logic in `attachMicButton`).

Today `attachMicButton` checks for `.message-input-bar` (and inserts before `.send-icon-btn`); otherwise it wraps the textarea in a `.textarea-mic-wrapper`. Update to prefer `.compose-toolbar`, preserving the legacy paths.

- [ ] **Step 1: Update `attachMicButton` insertion logic**

In `static/js/voice.js`, find the block (around lines 121-146):

```javascript
        // For session message input bar, use the icons container
        const iconsContainer = textarea.closest('.message-input-bar')?.querySelector('.message-input-icons');
        if (iconsContainer) {
            const sendBtn = iconsContainer.querySelector('.send-icon-btn');
            if (sendBtn) {
                iconsContainer.insertBefore(btn, sendBtn);
            } else {
                iconsContainer.appendChild(btn);
            }
            return;
        }

        // For all other textareas: wrap in a textarea-mic-wrapper
        const existing = textarea.closest('.textarea-mic-wrapper');
        if (existing) {
            existing.appendChild(btn);
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'textarea-mic-wrapper';
        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(textarea);
        wrapper.appendChild(btn);
```

Replace it with:

```javascript
        // Preferred: place inside .compose-toolbar (new redesigned layout)
        const composeBar = textarea.closest('.compose-bar');
        if (composeBar) {
            const toolbar = composeBar.querySelector('.compose-toolbar');
            if (toolbar) {
                toolbar.appendChild(btn); // mic always goes at the end of the toolbar
                return;
            }
        }

        // Fallback: legacy session message input bar with icons container
        const iconsContainer = textarea.closest('.message-input-bar')?.querySelector('.message-input-icons');
        if (iconsContainer) {
            const sendBtn = iconsContainer.querySelector('.send-icon-btn');
            if (sendBtn) {
                iconsContainer.insertBefore(btn, sendBtn);
            } else {
                iconsContainer.appendChild(btn);
            }
            return;
        }

        // Fallback: wrap textarea in a textarea-mic-wrapper for absolute positioning
        const existing = textarea.closest('.textarea-mic-wrapper');
        if (existing) {
            existing.appendChild(btn);
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'textarea-mic-wrapper';
        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(textarea);
        wrapper.appendChild(btn);
```

- [ ] **Step 2: Smoke test mic on all five in-scope textareas (still legacy HTML)**

Reload the app. Open a session. Verify the mic button appears on each of the five in-scope textareas. Click each mic to confirm it activates (browser will prompt for mic permission if not already granted). The mic itself does not need to record successfully — confirming it appears and toggles its active state is enough at this stage.

- [ ] **Step 3: Commit**

```bash
git add static/js/voice.js
git commit -m "Voice.js: insert mic into compose-toolbar when present, keep legacy fallbacks"
```

---

## Task 6: Migrate `message-input` to compose-bar layout

**Files:**
- Modify: `templates/session.html` lines 92-116 (the `.message-input-area` block).

This is the user-visible layout change. After this task, `message-input` should match the reference screenshot (4-row default, toolbar below, vertical blue send bar on the right, drag handle).

- [ ] **Step 1: Replace the message-input HTML block**

Find this block (around lines 92-116):

```html
    <div class="message-input-area">
        <form id="message-form" onsubmit="sendMessage(event)">
            <div class="message-input-bar">
                <textarea id="message-input" rows="1"
                    placeholder="Share your thoughts..."
                    onkeydown="if(event.key==='Enter' && event.ctrlKey){event.preventDefault();sendMessage(event)}"
                    oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,120)+'px'"></textarea>
                <div class="message-input-icons">
                    <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                    <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '__')" title="Underline (wrap with __)"><u>U</u></button>
                    <label class="input-icon-btn attach-icon-btn" title="Attach a file">
                        <input type="file" id="file-input" style="display:none"
                            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.pptx,.txt,.csv,.zip,.md"
                            onchange="uploadFile(this)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
                        </svg>
                    </label>
                    <button type="submit" class="input-icon-btn send-icon-btn" id="send-btn" title="Send (Ctrl+Enter)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z"/></svg>
                    </button>
                </div>
            </div>
        </form>
```

Replace with:

```html
    <div class="message-input-area">
        <form id="message-form" onsubmit="sendMessage(event)">
            <div class="compose-bar">
                <div class="compose-bar-main">
                    <textarea id="message-input" rows="4"
                        placeholder="Share your thoughts..."
                        onkeydown="if(event.key==='Enter' && event.ctrlKey){event.preventDefault();sendMessage(event)}"></textarea>
                    <div class="compose-toolbar">
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('message-input', '__')" title="Underline (wrap with __)"><u>U</u></button>
                        <label class="input-icon-btn attach-icon-btn" title="Attach a file">
                            <input type="file" id="file-input" style="display:none"
                                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.pptx,.txt,.csv,.zip,.md"
                                onchange="uploadFile(this)">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
                            </svg>
                        </label>
                        <button type="button" class="input-icon-btn format-btn" onclick="toggleBulletList('message-input')" title="Bullet list">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="8" y1="6" x2="21" y2="6"></line>
                                <line x1="8" y1="12" x2="21" y2="12"></line>
                                <line x1="8" y1="18" x2="21" y2="18"></line>
                                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                <line x1="3" y1="18" x2="3.01" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                </div>
                <button type="submit" class="compose-send" id="send-btn" title="Send (Ctrl+Enter)">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z"/></svg>
                </button>
            </div>
        </form>
```

Note: Polish and Mic buttons are NOT in the HTML — they get inserted at runtime by `polish.js` (Polish goes to the start of `.compose-toolbar`) and `voice.js` (Mic goes to the end). The toolbar order at runtime is: Polish, B, U, attach, bullet, mic — matching the screenshot.

- [ ] **Step 2: Smoke test the layout**

Reload the app, open a session. Verify:

1. The textarea shows ~4 rows tall by default (the placeholder "Share your thoughts..." is visible at the top of a clearly multi-line box).
2. Below the textarea, the toolbar shows Polish (pill), B, U, attach, bullet (icon), mic — in that order.
3. To the right of the textarea+toolbar, a tall blue rectangle with a white paper-plane icon spans the full height.
4. Drag the bottom-right corner of the textarea downward — the textarea should grow vertically; the blue send bar should stretch with it. Drag horizontally — should not resize horizontally.
5. Click the send button — sending a message still works.
6. Click Bold and Underline — wrapping still works.
7. Click the new bullet button — `- ` prefix gets toggled on the current line/selection.
8. No JS console errors.

- [ ] **Step 3: Smoke test rendered bullet message end-to-end**

Type a message in `message-input`:

```
Here is my list:
- alpha
- beta
- gamma
End.
```

Send it. Verify the rendered message bubble shows a real `<ul>` list (use DevTools Elements to confirm).

- [ ] **Step 4: Commit**

```bash
git add templates/session.html
git commit -m "Migrate message-input to compose-bar layout with bullet button and vertical send"
```

---

## Task 7: Migrate session.html Council boxes to compose-bar layout

**Files:**
- Modify: `templates/session.html` around lines 158-166 (the `council-question` and `council-context` textareas inside the Council modal/form).

Apply the same compose-bar wrapper to both Council textareas, with B/U/attach/bullet toolbars but no vertical send column. The existing "Ask the Council" submit button below the form stays unchanged.

Note: `attach-icon-btn` on Council boxes was not present originally. The spec shows a paperclip in the toolbar across all in-scope boxes per the reference screenshot. However, the Council boxes do not currently have file-attach functionality wired through `uploadFile`. We have two reasonable options:

- **Option A (recommended):** Omit the attach button on Council toolbars. Toolbar shows Polish, B, U, bullet, mic only.
- **Option B:** Add the attach button visually but wire it to the same `uploadFile` path as message-input. This is a behavior change beyond the spec, so default to Option A.

The steps below use Option A. If you want Option B, adjust the toolbar HTML to include the attach `<label>` and ensure the `<input type="file">` has a unique ID per textarea.

- [ ] **Step 1: Locate and replace `council-question`**

Find this block in `templates/session.html` (around lines 158-160):

```html
            <label for="council-question">What do you want the Council's take on?</label>
            <textarea id="council-question" rows="3"
                placeholder="e.g., Should I accept this job offer? Is our product pricing strategy right? How should I handle this situation with my manager?"></textarea>
```

Replace with:

```html
            <label for="council-question">What do you want the Council's take on?</label>
            <div class="compose-bar">
                <div class="compose-bar-main">
                    <textarea id="council-question" rows="4"
                        placeholder="e.g., Should I accept this job offer? Is our product pricing strategy right? How should I handle this situation with my manager?"></textarea>
                    <div class="compose-toolbar">
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('council-question', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('council-question', '__')" title="Underline (wrap with __)"><u>U</u></button>
                        <button type="button" class="input-icon-btn format-btn" onclick="toggleBulletList('council-question')" title="Bullet list">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="8" y1="6" x2="21" y2="6"></line>
                                <line x1="8" y1="12" x2="21" y2="12"></line>
                                <line x1="8" y1="18" x2="21" y2="18"></line>
                                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                <line x1="3" y1="18" x2="3.01" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
```

- [ ] **Step 2: Locate and replace `council-context`**

Find this block (around lines 163-165):

```html
            <label for="council-context">Additional context (optional)</label>
            <textarea id="council-context" rows="2"
                placeholder="Any background that would help the advisors give better analysis."></textarea>
```

Replace with:

```html
            <label for="council-context">Additional context (optional)</label>
            <div class="compose-bar">
                <div class="compose-bar-main">
                    <textarea id="council-context" rows="4"
                        placeholder="Any background that would help the advisors give better analysis."></textarea>
                    <div class="compose-toolbar">
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('council-context', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                        <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('council-context', '__')" title="Underline (wrap with __)"><u>U</u></button>
                        <button type="button" class="input-icon-btn format-btn" onclick="toggleBulletList('council-context')" title="Bullet list">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="8" y1="6" x2="21" y2="6"></line>
                                <line x1="8" y1="12" x2="21" y2="12"></line>
                                <line x1="8" y1="18" x2="21" y2="18"></line>
                                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                <line x1="3" y1="18" x2="3.01" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
```

- [ ] **Step 3: Smoke test in browser**

Reload the app. Open the Council modal/form (in a session, click "Ask the Council to weigh in"). Verify:

1. Both textareas show as 4-row compose-bars with toolbars beneath.
2. No vertical blue send bar on either Council textarea.
3. Polish button appears on both (inserted by `polish.js`).
4. Mic button appears on both at the end of the toolbar (inserted by `voice.js`).
5. B, U, bullet buttons all work on both textareas.
6. The "Ask the Council" submit button still appears below the form and still submits the question to the Council endpoint.
7. No JS console errors.

- [ ] **Step 4: Commit**

```bash
git add templates/session.html
git commit -m "Migrate session.html Council boxes to compose-bar layout with formatting toolbar"
```

---

## Task 8: Migrate dashboard.html Council boxes to compose-bar layout

**Files:**
- Modify: `templates/dashboard.html` (the `dash-council-question` and `dash-council-context` textareas; their exact line numbers can be found via grep).

Mirror the changes from Task 7 for the dashboard's Council form.

- [ ] **Step 1: Replace `dash-council-question`**

In `templates/dashboard.html` find this block (lines 192-193):

```html
                <textarea id="dash-council-question" rows="4"
                    placeholder="e.g., Should I accept this job offer? Is our product pricing strategy right? How should I handle this situation with my manager?"></textarea>
```

Replace with:

```html
                <div class="compose-bar">
                    <div class="compose-bar-main">
                        <textarea id="dash-council-question" rows="4"
                            placeholder="e.g., Should I accept this job offer? Is our product pricing strategy right? How should I handle this situation with my manager?"></textarea>
                        <div class="compose-toolbar">
                            <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('dash-council-question', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                            <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('dash-council-question', '__')" title="Underline (wrap with __)"><u>U</u></button>
                            <button type="button" class="input-icon-btn format-btn" onclick="toggleBulletList('dash-council-question')" title="Bullet list">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <line x1="8" y1="6" x2="21" y2="6"></line>
                                    <line x1="8" y1="12" x2="21" y2="12"></line>
                                    <line x1="8" y1="18" x2="21" y2="18"></line>
                                    <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                    <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                    <line x1="3" y1="18" x2="3.01" y2="18"></line>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
```

- [ ] **Step 2: Replace `dash-council-context`**

Find this block (lines 197-198):

```html
                <textarea id="dash-council-context" rows="3"
                    placeholder="Any background information that would help the advisors give better analysis."></textarea>
```

Replace with:

```html
                <div class="compose-bar">
                    <div class="compose-bar-main">
                        <textarea id="dash-council-context" rows="4"
                            placeholder="Any background information that would help the advisors give better analysis."></textarea>
                        <div class="compose-toolbar">
                            <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('dash-council-context', '**')" title="Bold (wrap with **)"><strong>B</strong></button>
                            <button type="button" class="input-icon-btn format-btn" onclick="wrapSelection('dash-council-context', '__')" title="Underline (wrap with __)"><u>U</u></button>
                            <button type="button" class="input-icon-btn format-btn" onclick="toggleBulletList('dash-council-context')" title="Bullet list">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <line x1="8" y1="6" x2="21" y2="6"></line>
                                    <line x1="8" y1="12" x2="21" y2="12"></line>
                                    <line x1="8" y1="18" x2="21" y2="18"></line>
                                    <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                    <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                    <line x1="3" y1="18" x2="3.01" y2="18"></line>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
```

Note: row count changes from `3` to `4` to match the spec's default; placeholder text and surrounding `<div class="form-group">` wrapper are preserved.

- [ ] **Step 3: Verify `wrapSelection` and `toggleBulletList` are accessible from dashboard.html**

These functions are defined inline in `templates/session.html`. They are NOT in `static/js/polish.js`. Check whether dashboard.html includes these functions via a shared script or inline:

```bash
grep -n "wrapSelection\|toggleBulletList\|formatText" templates/dashboard.html static/js/*.js
```

If dashboard.html does not have these functions defined or imported, you have two options:

- **Option A (recommended):** Move `wrapSelection`, `toggleBulletList`, and (optionally) `formatText` from `session.html` into a new shared script `static/js/compose.js`, include it via `templates/base.html`. This is a small refactor and is the right place for these to live.
- **Option B (quicker but worse):** Duplicate the function definitions inline in `dashboard.html`.

If you choose Option A, do this sub-task before continuing:

  1. Create `static/js/compose.js` with the `wrapSelection` and `toggleBulletList` function bodies (copy from session.html).
  2. Remove those two functions from session.html.
  3. Add `<script src="{{ url_for('static', filename='js/compose.js') }}"></script>` to `templates/base.html` (find the existing `polish.js` include around line 126 and add the new include adjacent to it).
  4. Verify both session.html and dashboard.html now have access to the functions.

For `formatText`, leave it in `session.html` since it's only used by the message-render path which lives there.

- [ ] **Step 4: Smoke test dashboard Council form**

Reload the app, navigate to the dashboard, open the Council form. Verify:

1. Both `dash-council-question` and `dash-council-context` show the new compose-bar layout.
2. B, U, bullet buttons work.
3. Polish and mic buttons appear.
4. The dashboard's existing "Ask the Council" submit still works.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html templates/base.html static/js/compose.js templates/session.html
git commit -m "Migrate dashboard Council boxes to compose-bar; extract shared compose JS"
```

(Adjust the staged file list to match what actually changed in your branch.)

---

## Task 9: Mobile breakpoint cleanup and visual polish pass

**Files:**
- Modify: `static/css/style.css` mobile breakpoint section (already touched in Task 1 Step 2; revisit for any final adjustments).
- Modify: `templates/session.html` if any layout regression appears in the message-input area when viewed on mobile.

Goal: confirm the new layout works on phone-width viewports and tighten any rough edges.

- [ ] **Step 1: Test on phone-width viewport**

Open the browser DevTools, switch to a mobile viewport (e.g. iPhone 12, 390x844). Load a session page.

Verify:

1. The compose-bar fits within the viewport width (no horizontal scroll).
2. The textarea default height is reduced (~80px / 3 rows).
3. The toolbar buttons remain reachable (44x44px tap targets per existing `.input-icon-btn` mobile rule at line 2447).
4. The vertical send bar is narrower (~2.5rem) but still clearly tappable.
5. The drag-resize handle still functions.

- [ ] **Step 2: Adjust if anything overflows or is unreadable**

If the toolbar overflows horizontally on small screens, reduce gap or padding:

```css
@media (max-width: 480px) {
    .compose-toolbar { gap: 0.15rem; padding: 0.3rem 0.4rem; }
}
```

(Add this to the existing mobile breakpoint block.) Use this only if needed.

- [ ] **Step 3: Test a Council form on mobile**

Open the dashboard on the same mobile viewport, open the Council form, verify both Council compose-bars fit and are usable.

- [ ] **Step 4: Test on desktop one more time**

Resize back to desktop. Verify nothing regressed: messages still render correctly, send button still works, drag-resize still works, no console errors.

- [ ] **Step 5: Commit any final polish**

If any CSS adjustments were made:

```bash
git add static/css/style.css
git commit -m "Mobile polish for compose-bar layout"
```

If no further changes were needed, skip the commit.

---

## Final Verification

Before declaring the feature done, run through this end-to-end checklist on a fresh page load:

- [ ] **End-to-end smoke test**

1. Open a session. `message-input` shows 4-row compose-bar with vertical blue send bar.
2. Type a multi-line message with bullet points using the bullet button. Send. Rendered message has real `<ul>` list.
3. Use Bold and Underline. Verify markdown wrapping in textarea, rendered formatting in message bubble.
4. Drag the textarea taller. Send bar stretches with it. Drag back smaller.
5. Click Polish. Polish flow still works (returns a polished version, Accept replaces textarea content, Revert restores original).
6. Attach a file. File upload still works.
7. Click mic. Mic toggle still works.
8. Open Council form (in session). Both `council-question` and `council-context` show new layout. No vertical send bar on these. "Ask the Council" submits successfully.
9. Open dashboard Council form. Same checks as #8 for `dash-council-question` and `dash-council-context`.
10. Verify out-of-scope textareas (`invite-message`, dashboard `perspective`, `raw-input`, `personal-topic`) STILL look and work as they did before.
11. Mobile viewport: layout is usable, no horizontal scroll, drag still works.
12. Browser console: no JS errors at any point.

- [ ] **Optional final commit and push**

If you want to push to Railway for production deploy:

```bash
git push origin main
```

(This will trigger an auto-deploy to Railway. If you'd rather review the change in a feature branch first, push to a branch instead and merge after review.)
