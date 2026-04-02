/**
 * Reusable "Polish" component for any textarea.
 *
 * Usage:
 *   attachPolish('my-textarea-id')
 *
 * This adds a small "Polish" button below the textarea. When clicked:
 * 1. Sends the text to /api/polish
 * 2. Shows the polished version with Accept / Edit / Revert options
 * 3. User can accept (replaces textarea), edit (focus textarea with polished text), or revert
 */

function attachPolish(textareaId, options = {}) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;

    const wrapper = textarea.parentElement;

    // Create the polish button
    const polishBtn = document.createElement('button');
    polishBtn.type = 'button';
    polishBtn.className = 'btn btn-sm btn-polish';
    polishBtn.textContent = 'Polish';
    polishBtn.title = 'Clean up spelling, punctuation, and clarity';
    polishBtn.onclick = () => doPolish(textareaId);

    // Create the polish bar (button container)
    const polishBar = document.createElement('div');
    polishBar.className = 'polish-bar';
    polishBar.appendChild(polishBtn);

    // Create the preview area (hidden initially)
    const preview = document.createElement('div');
    preview.id = textareaId + '-polish-preview';
    preview.className = 'polish-preview';
    preview.style.display = 'none';

    // Insert after textarea
    textarea.after(polishBar);
    polishBar.after(preview);

    // Store reference
    polishBtn.id = textareaId + '-polish-btn';
}

async function doPolish(textareaId) {
    const textarea = document.getElementById(textareaId);
    const btn = document.getElementById(textareaId + '-polish-btn');
    const preview = document.getElementById(textareaId + '-polish-preview');
    const text = textarea.value.trim();

    if (!text) return;

    // Save original
    const original = textarea.value;

    btn.disabled = true;
    btn.textContent = 'Polishing...';

    try {
        const res = await fetch('/api/polish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await res.json();

        if (data.success && data.polished) {
            // Check if anything actually changed
            if (data.polished.trim() === text) {
                btn.textContent = 'Looks good!';
                setTimeout(() => { btn.textContent = 'Polish'; btn.disabled = false; }, 2000);
                return;
            }

            // Show preview with diff highlighting
            showPolishPreview(textareaId, original, data.polished);
        } else {
            btn.textContent = 'Try again';
            setTimeout(() => { btn.textContent = 'Polish'; btn.disabled = false; }, 2000);
        }
    } catch (err) {
        btn.textContent = 'Try again';
        setTimeout(() => { btn.textContent = 'Polish'; btn.disabled = false; }, 2000);
    }
}

function showPolishPreview(textareaId, original, polished) {
    const textarea = document.getElementById(textareaId);
    const btn = document.getElementById(textareaId + '-polish-btn');
    const preview = document.getElementById(textareaId + '-polish-preview');

    // Build the preview
    preview.innerHTML = `
        <div class="polish-preview-header">
            <span class="polish-preview-label">Polished version</span>
        </div>
        <div class="polish-preview-text">${escapePolishHtml(polished)}</div>
        <div class="polish-preview-actions">
            <button type="button" class="btn btn-primary btn-sm" onclick="acceptPolish('${textareaId}')">Accept</button>
            <button type="button" class="btn btn-sm" onclick="editPolish('${textareaId}')">Edit</button>
            <button type="button" class="btn btn-sm" onclick="revertPolish('${textareaId}')">Revert</button>
        </div>
    `;

    // Store original and polished on the preview element
    preview.dataset.original = original;
    preview.dataset.polished = polished;

    // Show preview, dim textarea
    preview.style.display = 'block';
    textarea.style.opacity = '0.4';
    textarea.style.pointerEvents = 'none';
    btn.style.display = 'none';
}

function acceptPolish(textareaId) {
    const textarea = document.getElementById(textareaId);
    const btn = document.getElementById(textareaId + '-polish-btn');
    const preview = document.getElementById(textareaId + '-polish-preview');

    textarea.value = preview.dataset.polished;
    textarea.style.opacity = '';
    textarea.style.pointerEvents = '';
    preview.style.display = 'none';
    btn.style.display = '';
    btn.disabled = false;
    btn.textContent = 'Polish';
    textarea.focus();
}

function editPolish(textareaId) {
    const textarea = document.getElementById(textareaId);
    const btn = document.getElementById(textareaId + '-polish-btn');
    const preview = document.getElementById(textareaId + '-polish-preview');

    // Put polished text in textarea for manual editing
    textarea.value = preview.dataset.polished;
    textarea.style.opacity = '';
    textarea.style.pointerEvents = '';
    preview.style.display = 'none';
    btn.style.display = '';
    btn.disabled = false;
    btn.textContent = 'Polish';
    textarea.focus();
}

function revertPolish(textareaId) {
    const textarea = document.getElementById(textareaId);
    const btn = document.getElementById(textareaId + '-polish-btn');
    const preview = document.getElementById(textareaId + '-polish-preview');

    textarea.value = preview.dataset.original;
    textarea.style.opacity = '';
    textarea.style.pointerEvents = '';
    preview.style.display = 'none';
    btn.style.display = '';
    btn.disabled = false;
    btn.textContent = 'Polish';
    textarea.focus();
}

function escapePolishHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}
