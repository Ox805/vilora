# File Sharing in Sessions

**Created:** April 5, 2026
**Status:** Implemented
**Dependencies:** Session/messages system (implemented), GCP account (existing)
**Priority:** Medium. Enables richer collaboration in brainstorming and mediation sessions where participants need to share supporting documents, images, or reference materials.
**References:** `templates/session.html` (message rendering, input bar), `models/database.py` (Message model), `app.py` (message endpoints), `static/css/style.css`

---

## Problem Statement

Participants in Vilora sessions can only communicate through text. In brainstorming sessions, users often need to share documents, spreadsheets, images, or other files to provide context. In mediation sessions, relevant documents (contracts, emails, photos) could help ground the conversation. Currently, users must share files through external channels (email, text), breaking the flow.

---

## Design Principles

1. **Simple and fast.** Uploading a file should be as easy as sending a message -- tap the attachment icon, pick a file, done.
2. **Secure.** Only session participants can upload or view files. Files are validated for type and size. No executable files allowed.
3. **Non-intrusive.** File messages appear inline in the chat timeline, not in a separate panel. They're part of the conversation.
4. **Mobile-friendly.** The file picker should work with camera, photo library, and document providers on iOS/Android.

---

## Implementation Plan

### 1. Storage: Google Cloud Storage (GCS)

#### 1.1 Bucket Setup

Create a GCS bucket for Vilora file uploads:

- **Bucket name:** `vilora-uploads` (or `vilora-session-files`)
- **Location:** US (multi-region for reliability)
- **Storage class:** Standard
- **Access control:** Uniform (not fine-grained)
- **Public access:** Prevent public access. All files served through signed URLs.

Create via `gcloud`:
```bash
gcloud storage buckets create gs://vilora-uploads \
    --location=US \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access
```

#### 1.2 Service Account

Create a service account for the app to access the bucket:

```bash
gcloud iam service-accounts create vilora-storage \
    --display-name="Vilora Storage Access"

gcloud storage buckets add-iam-policy-binding gs://vilora-uploads \
    --member="serviceAccount:vilora-storage@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud iam service-accounts keys create gcs-key.json \
    --iam-account=vilora-storage@PROJECT_ID.iam.gserviceaccount.com
```

#### 1.3 Environment Variables

Add to Railway:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GCS_BUCKET_NAME` | `vilora-uploads` | Bucket name |
| `GCS_CREDENTIALS_JSON` | `{...}` | Service account key JSON (entire contents) |

The app will parse `GCS_CREDENTIALS_JSON` at startup. Alternative: use `GOOGLE_APPLICATION_CREDENTIALS` pointing to a file path, but inline JSON is easier on Railway.

#### 1.4 Python Client

Add `google-cloud-storage` to `requirements.txt`.

Create `storage.py`:

```python
"""File storage using Google Cloud Storage."""
import os
import sys
import json
from datetime import timedelta


def _get_client():
    """Get GCS client, or None if not configured."""
    creds_json = os.environ.get('GCS_CREDENTIALS_JSON')
    if not creds_json:
        return None
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_data)
        return storage.Client(credentials=credentials)
    except ImportError:
        sys.stderr.write("[Vilora] google-cloud-storage not installed.\n")
        return None
    except Exception as e:
        sys.stderr.write(f"[Vilora] GCS client error: {e}\n")
        return None


def _get_bucket():
    """Get the configured GCS bucket."""
    client = _get_client()
    if not client:
        return None
    bucket_name = os.environ.get('GCS_BUCKET_NAME', 'vilora-uploads')
    return client.bucket(bucket_name)


def upload_file(session_id, file_obj, filename, content_type):
    """Upload a file to GCS. Returns the blob path or None on failure.
    
    Files are stored as: sessions/{session_id}/{uuid}_{filename}
    """
    import uuid
    bucket = _get_bucket()
    if not bucket:
        sys.stderr.write(f"[Vilora] GCS not configured. File upload skipped: {filename}\n")
        return None

    safe_filename = filename.replace('/', '_').replace('\\', '_')
    blob_path = f"sessions/{session_id}/{uuid.uuid4().hex}_{safe_filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_file(file_obj, content_type=content_type)
    sys.stderr.write(f"[Vilora] File uploaded: {blob_path}\n")
    return blob_path


def get_download_url(blob_path, expiry_minutes=60):
    """Generate a signed URL for downloading a file."""
    bucket = _get_bucket()
    if not bucket:
        return None
    blob = bucket.blob(blob_path)
    url = blob.generate_signed_url(
        expiration=timedelta(minutes=expiry_minutes),
        method='GET'
    )
    return url


def delete_file(blob_path):
    """Delete a file from GCS."""
    bucket = _get_bucket()
    if not bucket:
        return False
    blob = bucket.blob(blob_path)
    try:
        blob.delete()
        return True
    except Exception as e:
        sys.stderr.write(f"[Vilora] File delete error: {e}\n")
        return False
```

---

### 2. Database Schema

#### 2.1 File Attachments Table

```sql
CREATE TABLE IF NOT EXISTS file_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    blob_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

PostgreSQL version uses `SERIAL PRIMARY KEY`.

Key points:
- `message_id` links to a message with `msg_type='file'`
- `blob_path` is the GCS object path (e.g., `sessions/5/abc123_contract.pdf`)
- `content_type` is the MIME type (e.g., `image/jpeg`, `application/pdf`)
- `file_size` in bytes, used for display and validation
- `ON DELETE CASCADE` cleans up when a message is deleted

#### 2.2 Message Content for File Messages

When a file is uploaded, create a message with:
- `msg_type = 'file'`
- `content` = JSON string: `{"filename": "contract.pdf", "content_type": "application/pdf", "file_size": 245000, "attachment_id": 7}`

This keeps the message timeline consistent -- file messages appear in order alongside text messages.

---

### 3. API Endpoints

#### 3.1 Upload File

```
POST /api/sessions/<session_id>/files
Content-Type: multipart/form-data
Body: file (the uploaded file)
Response: { "success": true, "message": { ...message dict with file info... } }
```

Server-side:
1. Verify user is session participant
2. Validate file:
   - **Max size:** 10MB (check `Content-Length` header and actual file size)
   - **Allowed types:** Images (jpeg, png, gif, webp), Documents (pdf, doc, docx, xls, xlsx, pptx, txt, csv), Archives (zip)
   - **Blocked types:** Executables (exe, bat, sh, cmd, msi, dmg), Scripts (js, py, rb, php)
   - Validate by both extension and MIME type (don't trust extension alone)
3. Upload to GCS via `storage.upload_file()`
4. Create `file_attachments` row
5. Create message with `msg_type='file'` and JSON content
6. Return the message dict

```python
ALLOWED_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv',
    'application/zip'
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

#### 3.2 Download File

```
GET /api/sessions/<session_id>/files/<attachment_id>
Response: 302 redirect to signed GCS URL
```

Server-side:
1. Verify user is session participant
2. Look up `file_attachments` row
3. Generate signed URL via `storage.get_download_url()` (60-minute expiry)
4. Redirect to the signed URL

This approach means:
- Files are never served through the app server (GCS handles the bandwidth)
- Signed URLs expire, so sharing the URL externally has limited value
- No public access to the bucket

#### 3.3 Delete File (via existing message delete)

The existing `DELETE /api/sessions/<id>/messages/<id>` endpoint already handles message deletion. Add a hook: when deleting a `msg_type='file'` message, also delete the GCS blob and `file_attachments` row. The `ON DELETE CASCADE` handles the DB row; add `storage.delete_file()` to clean up GCS.

---

### 4. Frontend: Upload UI

#### 4.1 Attachment Button in Input Bar

Add a paperclip icon button to `.message-input-icons`, before the send button:

```html
<div class="message-input-icons">
    <label class="input-icon-btn attach-icon-btn" title="Attach a file">
        <input type="file" id="file-input" style="display:none"
            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.pptx,.txt,.csv,.zip"
            onchange="uploadFile(this)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
        </svg>
    </label>
    <!-- existing send button -->
</div>
```

- Uses a `<label>` wrapping a hidden `<input type="file">` so the icon triggers the file picker
- The `accept` attribute hints the OS file picker to show relevant file types
- On mobile, this automatically offers camera, photo library, and file picker options

#### 4.2 Upload Progress

When a file is selected:

```javascript
async function uploadFile(input) {
    const file = input.files[0];
    if (!file) return;

    // Client-side size check
    if (file.size > 10 * 1024 * 1024) {
        alert('File must be under 10MB.');
        input.value = '';
        return;
    }

    // Show uploading state
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;

    // Show inline progress indicator
    const progressEl = document.createElement('div');
    progressEl.className = 'upload-progress';
    progressEl.textContent = `Uploading ${file.name}...`;
    document.querySelector('.message-input-area').prepend(progressEl);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`/api/sessions/${SESSION_ID}/files`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            loadMessages();
        } else {
            alert(data.error || 'Upload failed.');
        }
    } catch (err) {
        alert('Upload failed. Please try again.');
    } finally {
        sendBtn.disabled = false;
        progressEl.remove();
        input.value = '';  // reset so same file can be re-uploaded
    }
}
```

#### 4.3 File Message Rendering

Add a new case in `renderMessages()` for `msg_type === 'file'`:

```javascript
} else if (m.msg_type === 'file') {
    const fileData = JSON.parse(m.content);
    const isImage = fileData.content_type.startsWith('image/');
    const sizeStr = formatFileSize(fileData.file_size);
    const downloadUrl = `/api/sessions/${SESSION_ID}/files/${fileData.attachment_id}`;

    let preview;
    if (isImage) {
        preview = `<a href="${downloadUrl}" target="_blank" class="file-preview-link">
            <img src="${downloadUrl}" class="file-preview-img" alt="${escapeHtml(fileData.filename)}">
        </a>`;
    } else {
        preview = `<a href="${downloadUrl}" target="_blank" class="file-download-link">
            <span class="file-icon">${getFileIcon(fileData.content_type)}</span>
            <span class="file-info">
                <span class="file-name">${escapeHtml(fileData.filename)}</span>
                <span class="file-size">${sizeStr}</span>
            </span>
        </a>`;
    }

    const authorName = m.is_self ? 'You' : escapeHtml(m.display_name || 'Participant');
    return `<div class="message ${m.is_self ? 'message-self' : 'message-other'}" data-message-id="${m.id}">
        <div class="message-author">${authorName}${m.is_self ? deleteBtn : ''}</div>
        ${preview}
        ${reactionBar}
        <div class="message-time">${localTime(m.created_at)}</div>
    </div>`;
}
```

Helper functions:

```javascript
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getFileIcon(contentType) {
    if (contentType.includes('pdf')) return '📄';
    if (contentType.includes('word') || contentType.includes('document')) return '📝';
    if (contentType.includes('sheet') || contentType.includes('excel') || contentType.includes('csv')) return '📊';
    if (contentType.includes('presentation')) return '📑';
    if (contentType.includes('zip')) return '📦';
    if (contentType.includes('text')) return '📃';
    return '📎';
}
```

---

### 5. CSS Styling

```css
/* === File Messages === */
.file-preview-img {
    max-width: 100%;
    max-height: 300px;
    border-radius: var(--radius);
    margin-top: 0.5rem;
    cursor: pointer;
}

.file-download-link {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    margin-top: 0.5rem;
    background: rgba(0, 0, 0, 0.04);
    border-radius: var(--radius);
    text-decoration: none;
    color: var(--text);
    transition: background 0.15s;
}

.file-download-link:hover {
    background: rgba(0, 0, 0, 0.08);
}

.message-self .file-download-link {
    background: rgba(255, 255, 255, 0.15);
    color: white;
}

.message-self .file-download-link:hover {
    background: rgba(255, 255, 255, 0.25);
}

.file-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
}

.file-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.file-name {
    font-weight: 500;
    font-size: 0.9rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.file-size {
    font-size: 0.75rem;
    opacity: 0.7;
}

/* Attachment button */
.attach-icon-btn {
    cursor: pointer;
}

/* Upload progress */
.upload-progress {
    font-size: 0.8rem;
    color: var(--primary);
    padding: 0.25rem 0;
    text-align: center;
}
```

---

### 6. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| **File type spoofing** | Validate both file extension AND MIME type server-side. Use `python-magic` or `mimetypes` for detection |
| **Oversized files** | Check `Content-Length` header AND actual bytes read. Reject > 10MB |
| **Path traversal** | Never use user-provided filenames in blob paths. Prefix with UUID |
| **Unauthorized access** | Signed URLs expire in 60 minutes. Verify session participation before generating URLs |
| **Malware** | Out of scope for MVP. Consider Google Cloud's built-in malware scanning for later |
| **Storage abuse** | Consider per-session or per-user upload limits (e.g., 100MB per session, 500MB per user) |
| **Message deletion** | When a file message is deleted, also delete the GCS blob to avoid orphaned storage |

---

### 7. Mobile Considerations

- `<input type="file" accept="image/*,...">` on iOS gives options: Take Photo, Photo Library, Browse Files
- `capture` attribute can be added for camera-first flows, but `accept="image/*"` is more flexible
- Image previews should be responsive (`max-width: 100%`)
- File download links should be large enough to tap (44px min height)
- Upload progress indicator should be visible above the keyboard

---

### 8. Future Enhancements (Not in MVP)

| Feature | Description |
|---------|-------------|
| **Drag and drop** | Desktop users can drag files into the chat area |
| **Paste images** | Ctrl+V to paste screenshots directly into chat |
| **Image thumbnails** | Generate smaller thumbnails on upload for faster loading |
| **File previews** | Inline PDF viewer, document preview without downloading |
| **Storage quotas** | Per-session and per-user limits with UI showing usage |
| **Virus scanning** | Integrate with Google Cloud's malware scanning API |

---

### 9. Files to Modify

| File | Changes |
|------|---------|
| `models/database.py` | Add `file_attachments` table to `db_init()` |
| `app.py` | Add upload endpoint, download endpoint, hook file deletion into message delete |
| `storage.py` (new) | GCS client: `upload_file()`, `get_download_url()`, `delete_file()` |
| `templates/session.html` | Add attachment button, `uploadFile()` JS, file message rendering in `renderMessages()` |
| `static/css/style.css` | File preview, download link, attachment button, upload progress styles |
| `requirements.txt` | Add `google-cloud-storage` |

### 10. Environment Variables Required

| Variable | Purpose | Required |
|----------|---------|----------|
| `GCS_BUCKET_NAME` | GCS bucket name | Yes |
| `GCS_CREDENTIALS_JSON` | Service account key JSON | Yes |

File sharing degrades gracefully if GCS is not configured (upload button hidden or disabled, error message on attempt).
