// Voice input — adds mic buttons to textareas
(function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    let activeRecognition = null;
    let activeBtn = null;
    let activeInput = null;

    const MIC_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
    </svg>`;

    function showMicHelp(nearEl) {
        const existing = document.getElementById('mic-help');
        if (existing) existing.remove();
        const help = document.createElement('div');
        help.id = 'mic-help';
        help.className = 'mic-help';
        help.innerHTML = `
            <p><strong>Microphone access needed</strong></p>
            <p>Click the icon in your browser's address bar (left side, near the URL) and allow microphone access for this site, then reload the page.</p>
            <button onclick="this.parentElement.remove()" class="btn btn-sm" style="margin-top: 0.5rem;">Got it</button>
        `;
        nearEl.parentElement.insertBefore(help, nearEl);
    }

    function stopCurrent() {
        if (activeRecognition) {
            activeRecognition._listening = false;
            activeRecognition.stop();
            activeRecognition = null;
        }
        if (activeBtn) {
            activeBtn.classList.remove('btn-mic-active');
            activeBtn = null;
        }
        activeInput = null;
    }

    async function toggleMic(btn, textarea) {
        // If this button is already active, stop
        if (activeBtn === btn) {
            stopCurrent();
            return;
        }

        // Stop any other active session
        stopCurrent();

        // Check permission
        try {
            const perm = await navigator.permissions.query({ name: 'microphone' });
            if (perm.state === 'denied') {
                showMicHelp(textarea);
                return;
            }
        } catch (e) {}

        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = 'en-US';
        rec._listening = true;

        let finalTranscript = textarea.value ? textarea.value + ' ' : '';

        rec.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interim += event.results[i][0].transcript;
                }
            }
            textarea.value = finalTranscript + interim;
            // Trigger input event so any listeners (e.g. auto-resize) pick up the change
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        };

        rec.onend = () => {
            if (rec._listening) rec.start();
        };

        rec.onerror = (event) => {
            if (event.error === 'not-allowed') {
                stopCurrent();
                showMicHelp(textarea);
            } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
                stopCurrent();
            }
        };

        activeRecognition = rec;
        activeBtn = btn;
        activeInput = textarea;
        btn.classList.add('btn-mic-active');
        rec.start();
    }

    function attachMicButton(textarea) {
        // Don't double-attach
        if (textarea.dataset.micAttached) return;
        textarea.dataset.micAttached = 'true';

        // Find the right container to place the mic button
        const iconsContainer = textarea.closest('.message-input-bar')?.querySelector('.message-input-icons');
        let wrapper;
        if (iconsContainer) {
            wrapper = iconsContainer;
        } else {
            wrapper = textarea.closest('.form-group');
            if (!wrapper) {
                wrapper = document.createElement('div');
                wrapper.className = 'textarea-mic-wrapper';
                textarea.parentNode.insertBefore(wrapper, textarea);
                wrapper.appendChild(textarea);
            }
        }

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn-mic';
        btn.title = 'Voice input';
        btn.innerHTML = MIC_SVG;
        // Prevent mic button from stealing focus/selection from textarea
        btn.addEventListener('mousedown', (e) => e.preventDefault());
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleMic(btn, textarea);
        });

        // If inside icons container, insert before send button; otherwise append
        const sendBtn = wrapper.querySelector('.send-icon-btn');
        if (sendBtn) {
            wrapper.insertBefore(btn, sendBtn);
        } else {
            wrapper.appendChild(btn);
        }
    }

    // Attach to all textareas on page load
    function attachAll() {
        document.querySelectorAll('textarea').forEach(attachMicButton);
    }

    // Expose for dynamically created textareas (e.g. onboarding steps)
    window.VoiceInput = { attachMicButton, attachAll, stopCurrent };

    // Run on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachAll);
    } else {
        attachAll();
    }
})();
