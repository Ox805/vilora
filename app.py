import os
import sys
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.database import db_init, get_db, get_worker_db, _exec, _is_postgres, User, MediationSession, Message, MessageReaction
from mediation.engine import MediationEngine
from notifications import send_invite_email, send_password_reset_email, send_nudge_email, send_verification_email, send_activity_email
from sms import send_sms, send_verification_sms, send_activity_sms, generate_verification_code
import storage

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Trust Railway's reverse proxy headers
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Logging setup — ensure output reaches Railway logs
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('vilora')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

mediation_engine = MediationEngine()


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    return User.get_by_id(db, int(user_id))


# --- Auth Routes ---

@app.route('/')
def index():
    return render_template('landing.html')


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    db = get_db()
    user = User.get_by_email(db, email)
    if user and user.check_password(password):
        if not user.email_verified:
            return jsonify({'success': False, 'needs_verification': True, 'email': email,
                           'error': 'Please verify your email first. Check your inbox for a verification link.'}), 401
        login_user(user)
        redirect_url = '/dashboard'
        pending = session.pop('pending_join', None)
        if pending:
            redirect_url = url_for('join_session', code=pending)
        return jsonify({'success': True, 'redirect': redirect_url})
    return jsonify({'success': False, 'error': 'Invalid email or password'}), 401


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    display_name = data.get('display_name', '').strip()
    password = data.get('password', '')

    if not email or not password or not display_name:
        return jsonify({'success': False, 'error': 'All fields required'}), 400

    db = get_db()
    if User.get_by_email(db, email):
        return jsonify({'success': False, 'error': 'Email already registered'}), 400

    # Check if registering via an invite link (auto-verify)
    pending = session.get('pending_join')
    auto_verify = False
    if pending:
        med_session = MediationSession.get_by_invite_code(db, pending)
        if med_session:
            cur = _exec(db, "SELECT id FROM session_invites WHERE session_id = ? AND email = ? AND status = 'pending'",
                        (med_session.id, email))
            if cur.fetchone():
                auto_verify = True

    user = User.create(db, email, display_name, password, email_verified=auto_verify)

    if auto_verify:
        # Invited user: log in directly, skip verification
        login_user(user)
        redirect_url = url_for('join_session', code=session.pop('pending_join'))
        return jsonify({'success': True, 'redirect': redirect_url})
    else:
        # Normal registration: send verification email, don't log in
        token = secrets.token_urlsafe(32)
        _exec(db, "UPDATE users SET verification_token = ?, verification_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
              (token, user.id))
        db.commit()
        verify_link = url_for('verify_email', token=token, _external=True)
        send_verification_email(email, display_name, verify_link)
        return jsonify({'success': True, 'needs_verification': True, 'email': email})


@app.route('/verify-pending')
def verify_pending():
    email = request.args.get('email', '')
    return render_template('verify_pending.html', email=email)


@app.route('/verify-email/<token>')
def verify_email(token):
    db = get_db()
    cur = _exec(db, "SELECT * FROM users WHERE verification_token = ?", (token,))
    row = cur.fetchone()

    if not row:
        return render_template('error.html', message='This verification link is invalid or has already been used.'), 400

    # Check expiry (24 hours)
    sent_at = row.get('verification_sent_at')
    if sent_at:
        from datetime import datetime, timedelta
        sent_time = datetime.fromisoformat(str(sent_at))
        if datetime.utcnow() - sent_time > timedelta(hours=24):
            return render_template('verify_expired.html', email=row['email'])

    # Verify the user
    _exec(db, "UPDATE users SET email_verified = ?, verification_token = NULL WHERE id = ?",
          (True, row['id']))
    db.commit()

    # Auto-login
    user = User.get_by_id(db, row['id'])
    login_user(user)

    return redirect(url_for('dashboard'))


@app.route('/api/resend-verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': True})  # no enumeration

    db = get_db()
    user = User.get_by_email(db, email)

    if not user or user.email_verified:
        return jsonify({'success': True})  # no enumeration

    # Rate limit: once per 5 minutes
    cur = _exec(db, "SELECT verification_sent_at FROM users WHERE id = ?", (user.id,))
    row = cur.fetchone()
    if row and row['verification_sent_at']:
        from datetime import datetime, timedelta
        sent_time = datetime.fromisoformat(str(row['verification_sent_at']))
        if datetime.utcnow() - sent_time < timedelta(minutes=5):
            return jsonify({'success': False, 'error': 'Verification email was sent recently. Please check your inbox or try again in a few minutes.'}), 400

    token = secrets.token_urlsafe(32)
    _exec(db, "UPDATE users SET verification_token = ?, verification_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
          (token, user.id))
    db.commit()

    verify_link = url_for('verify_email', token=token, _external=True)
    send_verification_email(email, user.display_name, verify_link)

    return jsonify({'success': True})


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})


@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    db = get_db()
    user = User.get_by_email(db, email)

    # Always return success to avoid leaking whether an email exists
    if not user:
        return jsonify({'success': True})

    token = secrets.token_urlsafe(32)
    _exec(db,
        "INSERT INTO password_resets (user_id, token) VALUES (?, ?)",
        (user.id, token)
    )
    db.commit()

    reset_link = url_for('reset_password_page', token=token, _external=True)

    send_password_reset_email(email, user.display_name, reset_link)

    return jsonify({'success': True})


@app.route('/reset-password/<token>')
def reset_password_page(token):
    db = get_db()
    cur = _exec(db, "SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,))
    row = cur.fetchone()

    if not row:
        return render_template('error.html', message='This reset link is invalid or has already been used.'), 400

    created_at = datetime.fromisoformat(str(row['created_at']))
    if datetime.utcnow() - created_at > timedelta(hours=1):
        return render_template('error.html', message='This reset link has expired. Please request a new one.'), 400

    return render_template('reset_password.html', token=token)


@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token', '')
    password = data.get('password', '')

    if not password or len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    cur = _exec(db, "SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,))
    row = cur.fetchone()

    if not row:
        return jsonify({'success': False, 'error': 'Invalid or expired reset link'}), 400

    created_at = datetime.fromisoformat(str(row['created_at']))
    if datetime.utcnow() - created_at > timedelta(hours=1):
        return jsonify({'success': False, 'error': 'Reset link has expired'}), 400

    user = User.get_by_id(db, row['user_id'])
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 400

    user.update_password(db, password)
    _exec(db, "UPDATE password_resets SET used = 1 WHERE id = ?", (row['id'],))
    db.commit()

    return jsonify({'success': True})


# --- Dashboard ---

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/sessions', methods=['GET'])
@login_required
def list_sessions():
    db = get_db()
    sessions = MediationSession.get_by_user(db, current_user.id)
    session_list = []
    for s in sessions:
        d = s.to_dict()
        # Get unread count
        cur = _exec(db,
            "SELECT last_seen_at FROM session_last_seen WHERE session_id = ? AND user_id = ?",
            (s.id, current_user.id)
        )
        last_seen = cur.fetchone()
        if last_seen and last_seen['last_seen_at']:
            cur2 = _exec(db,
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ? AND created_at > ?",
                (s.id, last_seen['last_seen_at'])
            )
            unread = cur2.fetchone()['cnt']
        else:
            # Never visited -- count all messages as unread
            cur2 = _exec(db,
                "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
                (s.id,)
            )
            unread = cur2.fetchone()['cnt']
        d['unread_count'] = unread
        d['has_unread'] = unread > 0
        session_list.append(d)
    return jsonify({'sessions': session_list})


# --- Memory Helpers ---

def get_user_memories(db, user_id):
    """Load all active memories for a user as a list of dicts."""
    cur = _exec(db, "SELECT * FROM user_memories WHERE user_id = ? AND active = ? ORDER BY category, created_at", (user_id, True))
    rows = cur.fetchall()
    return [{'id': r['id'], 'category': r['category'], 'content': r['content'],
             'source_type': r['source_type'], 'confidence': r['confidence']} for r in rows]


def save_extracted_memories(db, user_id, session_id, memories):
    """Save AI-extracted memories to the database."""
    for m in memories:
        _exec(db,
            "INSERT INTO user_memories (user_id, category, content, source_type, source_session_id, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, m.get('category', 'profile'), m.get('content', ''),
             'session', session_id, m.get('confidence', 0.8))
        )
    db.commit()


SUMMARY_DELIMITER = '<!--SUMMARY-->'

def create_mediator_message(db, session_id, ai_response, requested_by=None, parent_message_id=None):
    """Create a mediator message with an AI-generated summary prefix.

    requested_by is the user who triggered this Vilora response and is the
    only one (besides legacy creator fallback) allowed to delete it.
    parent_message_id links this reply to the 'ask' message that prompted
    it, when applicable.
    """
    summary = mediation_engine.summarize_response(ai_response)
    if summary:
        content = f"{summary}{SUMMARY_DELIMITER}{ai_response}"
    else:
        content = ai_response
    return Message.create(db, session_id, None, content, msg_type='mediator', requested_by=requested_by, parent_message_id=parent_message_id)


# --- About Me Page ---

@app.route('/about-me')
@login_required
def about_me():
    return render_template('about_me.html')


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@app.route('/api/profile/display-name', methods=['POST'])
@login_required
def update_display_name():
    data = request.get_json()
    new_name = data.get('display_name', '').strip()
    if not new_name:
        return jsonify({'success': False, 'error': 'Display name cannot be empty'}), 400
    if len(new_name) > 50:
        return jsonify({'success': False, 'error': 'Display name must be 50 characters or fewer'}), 400

    db = get_db()
    _exec(db, "UPDATE users SET display_name = ? WHERE id = ?", (new_name, current_user.id))
    db.commit()
    current_user.display_name = new_name
    return jsonify({'success': True})


# --- Notification Preferences API ---

@app.route('/api/user/notification-preferences', methods=['GET'])
@login_required
def get_notification_preferences():
    db = get_db()
    cur = _exec(db, "SELECT * FROM notification_preferences WHERE user_id = ?", (current_user.id,))
    prefs = cur.fetchone()
    if not prefs:
        return jsonify({
            'email_enabled': True,
            'sms_enabled': False,
            'phone_number': None,
            'phone_verified': False
        })
    # Mask phone number for display
    phone = prefs['phone_number']
    masked_phone = None
    if phone and len(phone) >= 4:
        masked_phone = '***' + phone[-4:]
    return jsonify({
        'email_enabled': bool(prefs['email_enabled']),
        'sms_enabled': bool(prefs['sms_enabled']),
        'phone_number': masked_phone,
        'phone_verified': bool(prefs['phone_verified'])
    })


@app.route('/api/user/notification-preferences', methods=['PUT'])
@login_required
def update_notification_preferences():
    db = get_db()
    data = request.get_json()

    # Get or create preferences row
    cur = _exec(db, "SELECT * FROM notification_preferences WHERE user_id = ?", (current_user.id,))
    prefs = cur.fetchone()
    if not prefs:
        _exec(db,
            "INSERT INTO notification_preferences (user_id) VALUES (?)",
            (current_user.id,)
        )
        db.commit()
        cur = _exec(db, "SELECT * FROM notification_preferences WHERE user_id = ?", (current_user.id,))
        prefs = cur.fetchone()

    # Update email preference
    if 'email_enabled' in data:
        _exec(db,
            "UPDATE notification_preferences SET email_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (1 if data['email_enabled'] else 0, current_user.id)
        )
        db.commit()

    # Update phone number (triggers verification)
    if 'phone_number' in data and data['phone_number']:
        import re
        phone = data['phone_number'].strip()
        # Basic E.164 validation
        if not re.match(r'^\+[1-9]\d{6,14}$', phone):
            return jsonify({'success': False, 'error': 'Invalid phone number format. Use E.164 (e.g., +15551234567)'}), 400

        code = generate_verification_code()
        _exec(db,
            """UPDATE notification_preferences
               SET phone_number = ?, phone_verified = 0, sms_enabled = 0,
                   phone_verification_code = ?, phone_verification_sent_at = CURRENT_TIMESTAMP,
                   phone_verification_attempts = 0, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?""",
            (phone, code, current_user.id)
        )
        db.commit()

        send_verification_sms(phone, code)
        return jsonify({'success': True, 'verification_required': True})

    # Update SMS preference (only if phone is verified)
    if 'sms_enabled' in data:
        if data['sms_enabled'] and not prefs['phone_verified']:
            return jsonify({'success': False, 'error': 'Phone number must be verified before enabling SMS'}), 400
        _exec(db,
            "UPDATE notification_preferences SET sms_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (1 if data['sms_enabled'] else 0, current_user.id)
        )
        db.commit()

    return jsonify({'success': True})


@app.route('/api/user/verify-phone', methods=['POST'])
@login_required
def verify_phone():
    db = get_db()
    data = request.get_json()
    code = data.get('code', '').strip()

    cur = _exec(db, "SELECT * FROM notification_preferences WHERE user_id = ?", (current_user.id,))
    prefs = cur.fetchone()
    if not prefs or not prefs['phone_verification_code']:
        return jsonify({'success': False, 'error': 'No verification pending'}), 400

    # Check attempts
    if prefs['phone_verification_attempts'] >= 5:
        return jsonify({'success': False, 'error': 'Too many attempts. Please request a new code.'}), 400

    # Increment attempts
    _exec(db,
        "UPDATE notification_preferences SET phone_verification_attempts = phone_verification_attempts + 1 WHERE user_id = ?",
        (current_user.id,)
    )
    db.commit()

    # Check expiry (10 minutes)
    sent_at = prefs['phone_verification_sent_at']
    if sent_at:
        from datetime import datetime, timedelta
        try:
            if isinstance(sent_at, str):
                sent_at = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            if datetime.utcnow() - sent_at.replace(tzinfo=None) > timedelta(minutes=10):
                return jsonify({'success': False, 'error': 'Code expired. Please request a new one.'}), 400
        except Exception:
            pass  # If we can't parse the timestamp, allow the attempt

    if code != prefs['phone_verification_code']:
        remaining = 5 - (prefs['phone_verification_attempts'] + 1)
        return jsonify({'success': False, 'error': f'Invalid code. {remaining} attempts remaining.'}), 400

    # Success -- verify and enable SMS
    _exec(db,
        """UPDATE notification_preferences
           SET phone_verified = 1, sms_enabled = 1,
               phone_verification_code = NULL, phone_verification_attempts = 0,
               updated_at = CURRENT_TIMESTAMP
           WHERE user_id = ?""",
        (current_user.id,)
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/user/resend-phone-code', methods=['POST'])
@login_required
def resend_phone_code():
    db = get_db()
    cur = _exec(db, "SELECT * FROM notification_preferences WHERE user_id = ?", (current_user.id,))
    prefs = cur.fetchone()
    if not prefs or not prefs['phone_number']:
        return jsonify({'success': False, 'error': 'No phone number on file'}), 400

    # Rate limit: 1 per 60 seconds
    sent_at = prefs['phone_verification_sent_at']
    if sent_at:
        from datetime import datetime, timedelta
        try:
            if isinstance(sent_at, str):
                sent_at = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            if datetime.utcnow() - sent_at.replace(tzinfo=None) < timedelta(seconds=60):
                return jsonify({'success': False, 'error': 'Please wait 60 seconds before requesting a new code.'}), 429
        except Exception:
            pass

    code = generate_verification_code()
    _exec(db,
        """UPDATE notification_preferences
           SET phone_verification_code = ?, phone_verification_sent_at = CURRENT_TIMESTAMP,
               phone_verification_attempts = 0, updated_at = CURRENT_TIMESTAMP
           WHERE user_id = ?""",
        (code, current_user.id)
    )
    db.commit()
    send_verification_sms(prefs['phone_number'], code)
    return jsonify({'success': True})


# --- Memory API ---

@app.route('/api/user/memories', methods=['GET'])
@login_required
def list_memories():
    db = get_db()
    memories = get_user_memories(db, current_user.id)
    return jsonify({'success': True, 'memories': memories})


@app.route('/api/user/memories', methods=['POST'])
@login_required
def add_memory():
    data = request.get_json()
    content = data.get('content', '').strip()
    category = data.get('category', 'profile')

    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    db = get_db()
    _exec(db,
        "INSERT INTO user_memories (user_id, category, content, source_type, confidence) VALUES (?, ?, ?, ?, ?)",
        (current_user.id, category, content, 'explicit', 1.0)
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/user/memories/<int:memory_id>', methods=['PUT'])
@login_required
def edit_memory(memory_id):
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    db = get_db()
    _exec(db,
        "UPDATE user_memories SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (content, memory_id, current_user.id)
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/user/memories/<int:memory_id>', methods=['DELETE'])
@login_required
def delete_memory(memory_id):
    db = get_db()
    _exec(db,
        "UPDATE user_memories SET active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (False, memory_id, current_user.id)
    )
    db.commit()
    return jsonify({'success': True})


# --- Council (async) ---

import threading

_council_jobs = {}  # job_id -> {'status': 'running'|'done'|'error', 'result': ..., 'error': ...}

def _run_council_background(job_id, question, context, user_memories, session_id, user_id):
    try:
        sys.stderr.write(f"[Vilora] Council job {job_id} starting\n")
        result = mediation_engine.run_council(
            question=question,
            context=context,
            user_memories=user_memories
        )

        # Persist the result to the database
        import json
        with app.app_context():
            db = get_db()
            advisors_json = json.dumps(result['advisors'])
            if _is_postgres():
                cur = _exec(db,
                    "INSERT INTO council_results (session_id, requested_by, question, context, advisors, review, synthesis) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
                    (session_id, user_id, question, context, advisors_json, result['review'], result['synthesis'])
                )
                council_result_id = cur.fetchone()['id']
            else:
                cur = _exec(db,
                    "INSERT INTO council_results (session_id, requested_by, question, context, advisors, review, synthesis) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (session_id, user_id, question, context, advisors_json, result['review'], result['synthesis'])
                )
                council_result_id = cur.lastrowid
            db.commit()

            # If within a session, create a council message in the chat timeline
            if session_id:
                council_msg_content = json.dumps({'council_result_id': council_result_id, 'question': question})
                Message.create(db, session_id, user_id, council_msg_content, msg_type='council')
                queue_pending_notifications(db, session_id, user_id)

        result['council_result_id'] = council_result_id
        _council_jobs[job_id] = {'status': 'done', 'result': result}
        sys.stderr.write(f"[Vilora] Council job {job_id} completed, result_id={council_result_id}\n")
    except Exception as e:
        sys.stderr.write(f"[Vilora] Council job {job_id} error: {e}\n")
        _council_jobs[job_id] = {'status': 'error', 'error': str(e)}


@app.route('/api/council', methods=['POST'])
@login_required
def start_council():
    data = request.get_json()
    question = data.get('question', '').strip()
    context = data.get('context', '').strip()
    session_id = data.get('session_id')

    if not question:
        return jsonify({'success': False, 'error': 'Please provide a question'}), 400

    db = get_db()
    memories = get_user_memories(db, current_user.id)

    # If called from within a session, include conversation as context
    session_context = ''
    if session_id:
        med_session = MediationSession.get_by_id(db, session_id)
        if med_session and med_session.is_participant(db, current_user.id):
            messages = Message.get_by_session(db, session_id)
            participants = med_session.get_participants(db)
            participant_names = {p.id: p.display_name for p in participants}

            # Build conversation transcript (limit to last 50 messages to stay reasonable)
            lines = []
            for m in messages[-50:]:
                if m.msg_type == 'mediator':
                    lines.append(f"[Vilora]: {m.content}")
                elif m.msg_type == 'intake':
                    name = participant_names.get(m.user_id, 'Participant')
                    # Strip session tone metadata
                    content = m.content
                    import re
                    content = re.sub(r'\[Session tone:[^\]]*\]\s*', '', content)
                    lines.append(f"[{name}'s initial perspective]: {content}")
                elif m.msg_type == 'user':
                    name = participant_names.get(m.user_id, 'Participant')
                    lines.append(f"[{name}]: {m.content}")

            if lines:
                session_context = (
                    f"Session topic: {med_session.topic}\n\n"
                    f"Conversation so far:\n" + "\n".join(lines)
                )

    # Combine user-provided context with session context
    full_context = ''
    if session_context and context:
        full_context = f"{session_context}\n\nAdditional context from user: {context}"
    elif session_context:
        full_context = session_context
    elif context:
        full_context = context

    job_id = secrets.token_urlsafe(16)
    _council_jobs[job_id] = {'status': 'running'}

    thread = threading.Thread(
        target=_run_council_background,
        args=(job_id, question, full_context or None, memories or None, session_id, current_user.id),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'job_id': job_id})


@app.route('/api/council/<job_id>', methods=['GET'])
@login_required
def poll_council(job_id):
    job = _council_jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    if job['status'] == 'running':
        return jsonify({'success': True, 'status': 'running'})
    elif job['status'] == 'done':
        result = job['result']
        del _council_jobs[job_id]  # clean up
        return jsonify({'success': True, 'status': 'done', 'council': result})
    else:
        error = job.get('error', 'Unknown error')
        del _council_jobs[job_id]
        return jsonify({'success': False, 'status': 'error', 'error': error})


@app.route('/api/council/results/<int:result_id>', methods=['GET'])
@login_required
def get_council_result(result_id):
    import json
    db = get_db()
    cur = _exec(db, "SELECT * FROM council_results WHERE id = ?", (result_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Result not found'}), 404

    # Access check: must be the requester or a session participant
    if row['requested_by'] != current_user.id:
        if row['session_id']:
            med_session = MediationSession.get_by_id(db, row['session_id'])
            if not med_session or not med_session.is_participant(db, current_user.id):
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        else:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

    return jsonify({
        'success': True,
        'council': {
            'advisors': json.loads(row['advisors']),
            'review': row['review'],
            'synthesis': row['synthesis'],
            'question': row['question'],
            'council_result_id': row['id'],
            'created_at': str(row['created_at'])
        }
    })


# --- Feedback ---

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'success': False, 'error': 'Feedback is empty'}), 400

    user_info = ''
    if current_user.is_authenticated:
        user_info = f"From: {current_user.display_name} ({current_user.email})"
    else:
        user_info = "From: Anonymous (not logged in)"

    from notifications import send_email
    success = send_email(
        to_email='support@maiatech.ai',
        subject=f'Vilora Feedback: {text[:50]}',
        html_body=f"""
        <h3>Vilora User Feedback</h3>
        <p><strong>{user_info}</strong></p>
        <p style="white-space: pre-wrap;">{text}</p>
        <hr>
        <p style="color: #888; font-size: 12px;">Sent from the Vilora feedback form</p>
        """,
        text_body=f"Vilora User Feedback\n\n{user_info}\n\n{text}"
    )

    return jsonify({'success': success})


# --- Polish Helper ---

@app.route('/api/polish', methods=['POST'])
@login_required
def polish_text():
    data = request.get_json()
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'success': False, 'error': 'No text to polish'}), 400

    try:
        polished = mediation_engine.polish(text)
        if polished:
            return jsonify({'success': True, 'polished': polished})
        return jsonify({'success': False, 'error': 'Could not polish text'}), 500
    except Exception as e:
        sys.stderr.write(f"[Vilora] Polish error: {e}\n")
        return jsonify({'success': False, 'error': 'Could not polish text. Please try again.'}), 500


# --- Framing Helper ---

@app.route('/api/frame', methods=['POST'])
@login_required
def frame_issue():
    data = request.get_json()
    raw_text = data.get('text', '').strip()

    if not raw_text:
        return jsonify({'success': False, 'error': 'Please describe the issue first'}), 400

    try:
        db = get_db()
        memories = get_user_memories(db, current_user.id)
        result = mediation_engine.frame(raw_text, user_memories=memories or None)
        if not result:
            return jsonify({'success': False, 'error': 'Framing requires API key'}), 500
        import json
        parsed = json.loads(result)
        return jsonify({'success': True, 'framed': parsed})
    except json.JSONDecodeError:
        return jsonify({'success': True, 'framed': {'topic': '', 'type': 'general', 'perspective': raw_text, 'tips': ''}})
    except Exception as e:
        sys.stderr.write(f"[Vilora] Framing error: {e}\n")
        return jsonify({'success': False, 'error': 'Could not generate suggestion. Please try again.'}), 500


# --- Session Management ---

@app.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    data = request.get_json()
    topic = data.get('topic', '').strip()
    session_type = data.get('type', 'general')
    session_mode = data.get('mode', 'mediation')
    perspective = data.get('perspective', '').strip()

    tone = data.get('tone', '').strip()

    # For personal sessions, use the topic as the perspective and generate a short title
    if session_mode == 'personal':
        perspective = topic
        if tone:
            perspective = f"[Session tone: {tone}]\n\n{perspective}"
        try:
            topic = mediation_engine.generate_title(data.get('topic', '').strip())
        except Exception as e:
            print(f"Warning: Could not generate title: {e}")
            # Fallback: truncate
            topic = topic[:60] + ('...' if len(topic) > 60 else '')
    elif tone and perspective:
        perspective = f"[Session tone: {tone}]\n\n{perspective}"

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    db = get_db()
    invite_code = secrets.token_urlsafe(16)
    med_session = MediationSession.create(
        db,
        creator_id=current_user.id,
        topic=topic,
        session_type=session_type,
        invite_code=invite_code,
        session_mode=session_mode
    )

    # Save creator's initial perspective
    if perspective:
        Message.create(db, med_session.id, current_user.id, perspective, msg_type='intake')

        # Generate initial mediator acknowledgment
        try:
            ai_response = mediation_engine.welcome(
                topic=topic,
                session_type=session_type,
                perspective=perspective,
                creator_name=current_user.display_name,
                session_mode=session_mode
            )
            create_mediator_message(db, med_session.id, ai_response, requested_by=current_user.id)
        except Exception as e:
            print(f"Warning: Could not generate welcome message: {e}")

    return jsonify({
        'success': True,
        'session': med_session.to_dict(),
        'invite_link': url_for('join_session', code=invite_code, _external=True)
    })


@app.route('/join/<code>')
def join_session(code):
    db = get_db()
    med_session = MediationSession.get_by_invite_code(db, code)
    if not med_session:
        return render_template('error.html', message='Session not found'), 404

    if not current_user.is_authenticated:
        session['pending_join'] = code
        creator = User.get_by_id(db, med_session.creator_id)
        creator_name = creator.display_name if creator else 'Someone'
        return render_template('invite_landing.html',
                               creator_name=creator_name,
                               topic=med_session.topic,
                               invite_code=code)

    med_session.add_participant(db, current_user.id)

    # Mark any pending invites for this user's email as joined
    _exec(db,
        "UPDATE session_invites SET status = 'joined' WHERE session_id = ? AND email = ? AND status = 'pending'",
        (med_session.id, current_user.email)
    )
    db.commit()

    return redirect(url_for('session_room', session_id=med_session.id))


@app.route('/api/sessions/<int:session_id>/invite', methods=['POST'])
@login_required
def invite_to_session(session_id):
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    personal_message = data.get('message', '').strip()
    cc_me = data.get('cc_me', False)

    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400

    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    if med_session.creator_id != current_user.id:
        return jsonify({'success': False, 'error': 'Only the session creator can send invites'}), 403

    join_link = url_for('join_session', code=med_session.invite_code, _external=True)

    success = send_invite_email(
        to_email=email,
        creator_name=current_user.display_name,
        topic=med_session.topic,
        join_link=join_link,
        personal_message=personal_message or None
    )

    # Send a copy to the inviter if requested
    if success and cc_me:
        send_invite_email(
            to_email=current_user.email,
            creator_name=current_user.display_name,
            topic=med_session.topic,
            join_link=join_link,
            personal_message=personal_message or None
        )

    if success:
        # Track the invite
        _exec(db,
            "INSERT INTO session_invites (session_id, email, status, invited_by) VALUES (?, ?, ?, ?)",
            (session_id, email, 'pending', current_user.id)
        )
        db.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to send invite. Please try again or copy the link instead.'}), 500


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    if med_session.creator_id != current_user.id:
        return jsonify({'success': False, 'error': 'Only the session creator can delete it'}), 403

    # Collect file-attachment blob paths before deleting the rows (messages cascade
    # to file_attachments via ON DELETE CASCADE, but we still need the paths to
    # clean up the GCS objects).
    blob_paths = []
    try:
        cur_blobs = _exec(db, "SELECT blob_path FROM file_attachments WHERE session_id = ?", (session_id,))
        blob_paths = [r['blob_path'] for r in cur_blobs.fetchall()]
    except Exception:
        pass

    try:
        _exec(db, "DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM session_invites WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM user_memories WHERE source_session_id = ?", (session_id,))
        _exec(db, "DELETE FROM council_results WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM nudge_log WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM session_last_seen WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM notification_log WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM pending_notifications WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM file_attachments WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM messages WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM agreements WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM session_participants WHERE session_id = ?", (session_id,))
        _exec(db, "DELETE FROM mediation_sessions WHERE id = ?", (session_id,))
        db.commit()
    except Exception as e:
        db.rollback()
        sys.stderr.write(f"[delete_session] failed for session {session_id}: {e}\n")
        return jsonify({'success': False, 'error': 'Could not delete session.'}), 500

    for path in blob_paths:
        try:
            storage.delete_file(path)
        except Exception as e:
            sys.stderr.write(f"[delete_session] blob cleanup failed for {path}: {e}\n")

    return jsonify({'success': True})


@app.route('/api/sessions/<int:session_id>/join', methods=['POST'])
@login_required
def submit_intake(session_id):
    data = request.get_json()
    perspective = data.get('perspective', '').strip()

    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    med_session.add_participant(db, current_user.id)

    if perspective:
        Message.create(db, session_id, current_user.id, perspective, msg_type='intake')

    return jsonify({'success': True})


# --- Mediation Room ---

@app.route('/session/<int:session_id>')
@login_required
def session_room(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        return render_template('error.html', message='Session not found'), 404

    if not med_session.is_participant(db, current_user.id):
        return render_template('error.html', message='You are not a participant in this session'), 403

    participants = med_session.get_participants(db)
    is_creator = (current_user.id == med_session.creator_id)
    invite_link = url_for('join_session', code=med_session.invite_code, _external=True)
    creator = User.get_by_id(db, med_session.creator_id)
    creator_name = creator.display_name if creator else 'Someone'

    # Show welcome modal only if non-creator has never sent a message in this session
    show_welcome = False
    if not is_creator:
        cur = _exec(db,
            "SELECT 1 FROM messages WHERE session_id = ? AND user_id = ? LIMIT 1",
            (session_id, current_user.id)
        )
        show_welcome = cur.fetchone() is None

    return render_template('session.html', session=med_session,
                           participants=participants, is_creator=is_creator,
                           invite_link=invite_link, creator_name=creator_name,
                           is_personal=(med_session.session_mode == 'personal'),
                           show_welcome=show_welcome)


@app.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)
    name_map = {p.id: p.display_name for p in participants}

    message_ids = [m.id for m in messages]
    all_reactions = MessageReaction.get_for_messages(db, message_ids)

    # Return current last_seen_at to the client (used for scroll-to-first-unread).
    # We intentionally do NOT update it here -- /messages is polled every 5s by the
    # session page, including in background tabs, so updating it as a side effect
    # silently clears the dashboard unread badge even when the user never looked.
    # Clients must call POST /api/sessions/<id>/mark-seen explicitly when the user
    # is actually engaged (tab visible, message sent, etc).
    last_seen_at = None
    try:
        cur_ls = _exec(db,
            "SELECT last_seen_at FROM session_last_seen WHERE session_id = ? AND user_id = ?",
            (session_id, current_user.id)
        )
        row_ls = cur_ls.fetchone()
        if row_ls:
            last_seen_at = str(row_ls['last_seen_at'])
    except Exception:
        pass

    msg_list = []
    for m in messages:
        d = m.to_dict()
        d['display_name'] = name_map.get(m.user_id)
        d['is_self'] = (m.user_id == current_user.id)
        if m.user_id == current_user.id:
            d['can_delete'] = True
        elif m.msg_type == 'mediator' and m.requested_by == current_user.id:
            d['can_delete'] = True
        elif (m.msg_type == 'mediator' and m.requested_by is None
              and med_session.creator_id == current_user.id):
            d['can_delete'] = True
        else:
            d['can_delete'] = False
        msg_reactions = all_reactions.get(m.id, {})
        reactions_out = {}
        for rkey, rdata in msg_reactions.items():
            reactions_out[rkey] = {
                'count': rdata['count'],
                'user_ids': rdata['user_ids'],
                'includes_self': current_user.id in rdata['user_ids'],
                'names': [name_map.get(uid, 'Someone') for uid in rdata['user_ids']]
            }
        d['reactions'] = reactions_out
        msg_list.append(d)

    return jsonify({'messages': msg_list, 'last_seen_at': last_seen_at})


@app.route('/api/sessions/<int:session_id>/mark-seen', methods=['POST'])
@login_required
def mark_session_seen(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    try:
        _exec(db,
            """INSERT INTO session_last_seen (session_id, user_id, last_seen_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(session_id, user_id)
               DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP""",
            (session_id, current_user.id)
        )
        db.commit()
    except Exception:
        db.rollback()
        return jsonify({'success': False, 'error': 'Could not mark seen'}), 500
    return jsonify({'success': True})


@app.route('/api/sessions/<int:session_id>/messages', methods=['POST'])
@login_required
def send_message(session_id):
    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400

    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    # Save the user's message
    user_msg = Message.create(db, session_id, current_user.id, content, msg_type='user')

    # In personal mode, Vilora always responds. In group mode, only when explicitly asked.
    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)

    ai_msg = None
    try:
        if med_session.session_mode == 'personal':
            # Load memories for all participants
            participant_memories = {}
            for p in participants:
                memories = get_user_memories(db, p.id)
                if memories:
                    participant_memories[p.id] = memories

            ai_response = mediation_engine.mediate(
                topic=med_session.topic,
                session_type=med_session.session_type,
                messages=messages,
                participants=participants,
                participant_memories=participant_memories or None,
                session_mode=med_session.session_mode
            )
            ai_msg = create_mediator_message(db, session_id, ai_response, requested_by=current_user.id)
    except Exception as e:
        sys.stderr.write(f"[Vilora] Mediation error: {e}\n")

    # Queue activity notifications for other participants
    queue_pending_notifications(db, session_id, current_user.id)

    result = {'success': True, 'user_message': user_msg.to_dict()}
    if ai_msg:
        result['mediator_message'] = ai_msg.to_dict()
    return jsonify(result)


@app.route('/api/sessions/<int:session_id>/nudge', methods=['POST'])
@login_required
def nudge_participant(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    target_email = data.get('email', '').strip().lower()

    # Determine the nudge target identifier for logging
    if target_email:
        nudge_target = target_email
    elif target_user_id:
        target_user = User.get_by_id(db, target_user_id)
        nudge_target = target_user.email if target_user else str(target_user_id)
    else:
        return jsonify({'success': False, 'error': 'No target specified.'}), 400

    # Check nudge limits: max 4 total, max 1 per 24 hours
    cur = _exec(db,
        "SELECT COUNT(*) as total FROM nudge_log WHERE session_id = ? AND nudger_id = ? AND target = ?",
        (session_id, current_user.id, nudge_target)
    )
    total_nudges = cur.fetchone()['total']
    if total_nudges >= 4:
        return jsonify({'success': False, 'error': 'You\'ve reached the maximum of 4 nudges for this person.'}), 400

    from models.database import _is_postgres
    if _is_postgres():
        time_query = "created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'"
    else:
        time_query = "created_at > datetime('now', '-24 hours')"
    cur = _exec(db,
        f"SELECT COUNT(*) as recent FROM nudge_log WHERE session_id = ? AND nudger_id = ? AND target = ? AND {time_query}",
        (session_id, current_user.id, nudge_target)
    )
    recent_nudges = cur.fetchone()['recent']
    if recent_nudges > 0:
        return jsonify({'success': False, 'error': 'You can only nudge this person once every 24 hours.'}), 400

    session_link = url_for('session_room', session_id=session_id, _external=True)
    join_link = url_for('join_session', code=med_session.invite_code, _external=True)

    success = False

    # Nudge a pending invite by email
    if target_email:
        from notifications import send_invite_email
        success = send_invite_email(
            to_email=target_email,
            creator_name=current_user.display_name,
            topic=med_session.topic,
            join_link=join_link,
            personal_message="Just a friendly reminder that the conversation is waiting for you."
        )

    # Nudge a joined participant
    elif target_user_id:
        target_user = User.get_by_id(db, target_user_id)
        if target_user:
            success = send_nudge_email(
                to_email=target_user.email,
                nudger_name=current_user.display_name,
                recipient_name=target_user.display_name,
                topic=med_session.topic,
                session_link=session_link
            )

    if success:
        # Log the nudge
        _exec(db,
            "INSERT INTO nudge_log (session_id, nudger_id, target) VALUES (?, ?, ?)",
            (session_id, current_user.id, nudge_target)
        )
        db.commit()
        return jsonify({'success': True, 'total_nudges': total_nudges + 1})
    else:
        return jsonify({'success': False, 'error': 'Could not send nudge. Please try again.'}), 500


@app.route('/api/sessions/<int:session_id>/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(session_id, message_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    # Get the message
    cur = _exec(db, "SELECT * FROM messages WHERE id = ? AND session_id = ?", (message_id, session_id))
    msg = cur.fetchone()
    if not msg:
        return jsonify({'success': False, 'error': 'Message not found'}), 404

    # Users can delete their own messages.
    # For mediator messages, the user who requested Vilora's input can delete it.
    # Legacy mediator messages with no recorded requester fall back to creator-delete.
    if msg['user_id'] == current_user.id:
        pass  # allowed
    elif msg['msg_type'] == 'mediator' and msg['requested_by'] == current_user.id:
        pass  # requester can delete the Vilora response they triggered
    elif (msg['msg_type'] == 'mediator' and msg['requested_by'] is None
          and med_session.creator_id == current_user.id):
        pass  # legacy: creator can delete pre-feature mediator messages
    else:
        return jsonify({'success': False, 'error': 'You can only delete your own messages'}), 403

    # If this is a file message, clean up the GCS blob
    if msg['msg_type'] == 'file':
        cur_att = _exec(db, "SELECT blob_path FROM file_attachments WHERE message_id = ?", (message_id,))
        att_row = cur_att.fetchone()
        if att_row:
            storage.delete_file(att_row['blob_path'])

    _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/sessions/<int:session_id>/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def toggle_reaction(session_id, message_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    cur = _exec(db, "SELECT id FROM messages WHERE id = ? AND session_id = ?", (message_id, session_id))
    if not cur.fetchone():
        return jsonify({'success': False, 'error': 'Message not found'}), 404

    data = request.get_json()
    reaction = data.get('reaction', '')
    if reaction not in MessageReaction.VALID_REACTIONS:
        return jsonify({'success': False, 'error': 'Invalid reaction'}), 400

    action = MessageReaction.toggle(db, message_id, current_user.id, reaction)

    participants = med_session.get_participants(db)
    name_map = {p.id: p.display_name for p in participants}
    msg_reactions = MessageReaction.get_for_messages(db, [message_id]).get(message_id, {})
    reactions_out = {}
    for rkey, rdata in msg_reactions.items():
        reactions_out[rkey] = {
            'count': rdata['count'],
            'user_ids': rdata['user_ids'],
            'includes_self': current_user.id in rdata['user_ids'],
            'names': [name_map.get(uid, 'Someone') for uid in rdata['user_ids']]
        }

    return jsonify({'success': True, 'action': action, 'reactions': reactions_out})


# --- File Sharing ---

ALLOWED_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'text/markdown',
    'application/zip'
}

BLOCKED_EXTENSIONS = {'.exe', '.bat', '.sh', '.cmd', '.msi', '.dmg', '.js', '.py', '.rb', '.php'}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@app.route('/api/sessions/<int:session_id>/files', methods=['POST'])
@login_required
def upload_file(session_id):
    logger.info(f"[FileUpload] session={session_id} user={current_user.id}")
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    filename = file.filename
    content_type = file.content_type or 'application/octet-stream'

    # Validate extension
    ext = os.path.splitext(filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return jsonify({'success': False, 'error': 'This file type is not allowed'}), 400

    # Validate MIME type
    if content_type not in ALLOWED_CONTENT_TYPES:
        return jsonify({'success': False, 'error': 'This file type is not allowed'}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        return jsonify({'success': False, 'error': 'File must be under 10MB'}), 400
    if file_size == 0:
        return jsonify({'success': False, 'error': 'File is empty'}), 400

    # Upload to GCS
    blob_path = storage.upload_file(session_id, file, filename, content_type)
    if not blob_path:
        return jsonify({'success': False, 'error': 'File storage is not configured'}), 500

    # Create message
    import json as json_mod
    msg = Message.create(db, session_id, current_user.id, '', msg_type='file')

    # Create file_attachments row
    if _is_postgres():
        cur = _exec(db,
            "INSERT INTO file_attachments (message_id, session_id, user_id, filename, content_type, file_size, blob_path) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (msg.id, session_id, current_user.id, filename, content_type, file_size, blob_path)
        )
        attachment_id = cur.fetchone()['id']
    else:
        cur = _exec(db,
            "INSERT INTO file_attachments (message_id, session_id, user_id, filename, content_type, file_size, blob_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg.id, session_id, current_user.id, filename, content_type, file_size, blob_path)
        )
        attachment_id = cur.lastrowid

    # Update message content with file metadata
    file_content = json_mod.dumps({
        'filename': filename,
        'content_type': content_type,
        'file_size': file_size,
        'attachment_id': attachment_id
    })
    _exec(db, "UPDATE messages SET content = ? WHERE id = ?", (file_content, msg.id))
    db.commit()

    participants = med_session.get_participants(db)
    name_map = {p.id: p.display_name for p in participants}

    return jsonify({
        'success': True,
        'message': {
            'id': msg.id,
            'session_id': session_id,
            'user_id': current_user.id,
            'content': file_content,
            'msg_type': 'file',
            'display_name': name_map.get(current_user.id),
            'is_self': True,
            'reactions': {}
        }
    })


@app.route('/api/sessions/<int:session_id>/files/<int:attachment_id>', methods=['GET'])
@login_required
def download_file(session_id, attachment_id):
    from flask import Response
    import requests as http_requests

    logger.info(f"[FileServe] session={session_id} attachment={attachment_id} user={current_user.id}")

    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        logger.warning(f"[FileServe] session {session_id} not found")
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    if not med_session.is_participant(db, current_user.id):
        logger.warning(f"[FileServe] user {current_user.id} not participant in session {session_id}")
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    try:
        cur = _exec(db, "SELECT * FROM file_attachments WHERE id = ? AND session_id = ?", (attachment_id, session_id))
        att = cur.fetchone()
    except Exception as e:
        logger.error(f"[FileServe] DB query failed: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': 'Database error'}), 500

    if not att:
        logger.warning(f"[FileServe] attachment {attachment_id} not found in session {session_id}")
        return jsonify({'success': False, 'error': 'File not found'}), 404

    logger.info(f"[FileServe] found attachment: {att['filename']} blob={att['blob_path']}")

    url = storage.get_download_url(att['blob_path'])
    if not url:
        logger.error(f"[FileServe] GCS signed URL generation failed for {att['blob_path']}")
        return jsonify({'success': False, 'error': 'Could not generate download URL'}), 500

    logger.info(f"[FileServe] fetching from GCS...")

    # Proxy all files through Flask -- no redirects to signed URLs
    try:
        gcs_resp = http_requests.get(url, stream=True, timeout=30)
        logger.info(f"[FileServe] GCS response: {gcs_resp.status_code} content-type={gcs_resp.headers.get('Content-Type')}")
        if gcs_resp.status_code != 200:
            logger.error(f"[FileServe] GCS returned {gcs_resp.status_code}: {gcs_resp.text[:200]}")
            return jsonify({'success': False, 'error': 'File not available'}), 502

        inline = request.args.get('view') == '1'
        if inline:
            disposition = f'inline; filename="{att["filename"]}"'
        else:
            disposition = f'attachment; filename="{att["filename"]}"'
        return Response(
            gcs_resp.iter_content(chunk_size=8192),
            content_type=att['content_type'],
            headers={
                'Content-Disposition': disposition,
                'Cache-Control': 'private, max-age=300',
            }
        )
    except Exception as e:
        logger.error(f"[FileServe] proxy error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Could not load file'}), 500


@app.route('/api/sessions/<int:session_id>/ask-vilora', methods=['POST'])
@login_required
def ask_vilora(session_id):
    """Explicitly request Vilora's input in a group session.

    Optional JSON body:
        { "question": "..." }   # if present and non-empty, Vilora answers
                                # this specific question rather than reviewing
                                # the whole session.
    """
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    payload = request.get_json(silent=True) or {}
    question = (payload.get('question') or '').strip()

    ask_msg = None
    if question:
        ask_msg = Message.create(db, session_id, current_user.id, question, msg_type='ask')

    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)

    try:
        participant_memories = {}
        for p in participants:
            memories = get_user_memories(db, p.id)
            if memories:
                participant_memories[p.id] = memories

        ai_response = mediation_engine.mediate(
            topic=med_session.topic,
            session_type=med_session.session_type,
            messages=messages,
            participants=participants,
            participant_memories=participant_memories or None,
            session_mode=med_session.session_mode,
            user_question=question or None,
        )
        ai_msg = create_mediator_message(
            db, session_id, ai_response,
            requested_by=current_user.id,
            parent_message_id=(ask_msg.id if ask_msg else None),
        )
        # Queue notifications -- Vilora's response means activity
        queue_pending_notifications(db, session_id, current_user.id)

        result = {'success': True, 'mediator_message': ai_msg.to_dict()}
        if ask_msg:
            result['ask_message'] = ask_msg.to_dict()
        return jsonify(result)
    except Exception as e:
        sys.stderr.write(f"[Vilora] Ask Vilora error: {e}\n")
        # If we already inserted an ask row but mediate() failed, leave it.
        # The user will see their question chip with no reply and can delete it.
        return jsonify({'success': False, 'error': 'Vilora could not respond. Please try again.'}), 500


@app.route('/api/sessions/<int:session_id>/participants', methods=['GET'])
@login_required
def get_participants(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    participants = med_session.get_participants(db)

    # Get nudge counts for this user
    nudge_counts = {}
    cur = _exec(db,
        "SELECT target, COUNT(*) as count FROM nudge_log WHERE session_id = ? AND nudger_id = ? GROUP BY target",
        (session_id, current_user.id)
    )
    for r in cur.fetchall():
        nudge_counts[r['target']] = r['count']

    # Build participant list with nudge info
    participant_list = []
    for p in participants:
        participant_list.append({
            'id': p.id,
            'display_name': p.display_name,
            'nudge_count': nudge_counts.get(p.email, 0)
        })

    # Get pending invites
    cur = _exec(db,
        "SELECT email, created_at FROM session_invites WHERE session_id = ? AND status = 'pending'",
        (session_id,)
    )
    pending_invites = []
    for r in cur.fetchall():
        pending_invites.append({
            'email': r['email'],
            'created_at': str(r['created_at']),
            'nudge_count': nudge_counts.get(r['email'], 0)
        })

    return jsonify({
        'success': True,
        'participants': participant_list,
        'pending_invites': pending_invites
    })


@app.route('/api/sessions/<int:session_id>/summary', methods=['GET'])
@login_required
def get_summary(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    messages = Message.get_by_session(db, session_id)
    message_count = len(messages)

    # Check for cached summary with same message count
    cur = _exec(db,
        "SELECT summary FROM session_summaries WHERE session_id = ? AND message_count = ? ORDER BY created_at DESC",
        (session_id, message_count)
    )
    cached = cur.fetchone()
    if cached:
        return jsonify({'success': True, 'summary': cached['summary']})

    # Generate new summary
    participants = med_session.get_participants(db)
    try:
        summary = mediation_engine.summarize(
            topic=med_session.topic,
            messages=messages,
            participants=participants
        )
    except Exception as e:
        sys.stderr.write(f"[Vilora] Summary error: {e}\n")
        return jsonify({'success': False, 'error': 'Failed to generate summary. Please try again.'}), 500

    # Cache the summary
    _exec(db,
        "INSERT INTO session_summaries (session_id, message_count, summary) VALUES (?, ?, ?)",
        (session_id, message_count, summary)
    )
    db.commit()

    # Extract memories for each participant (runs in background after response)
    try:
        for p in participants:
            existing = get_user_memories(db, p.id)
            new_memories = mediation_engine.extract_memories(
                user_name=p.display_name,
                user_id=p.id,
                topic=med_session.topic,
                messages=messages,
                participants=participants,
                existing_memories=existing
            )
            if new_memories:
                save_extracted_memories(db, p.id, session_id, new_memories)
                sys.stderr.write(f"[Vilora] Extracted {len(new_memories)} memories for {p.display_name}\n")
    except Exception as e:
        sys.stderr.write(f"[Vilora] Memory extraction error: {e}\n")

    return jsonify({'success': True, 'summary': summary})


# --- Notification Diagnostics ---

# Track worker health from the daemon thread
_notification_worker_state = {'cycle': 0, 'last_run': None, 'last_error': None, 'last_result': None}


@app.route('/api/admin/notification-diagnostics')
@login_required
def notification_diagnostics():
    """Diagnostic endpoint to check notification system health."""
    db = get_db()

    # Check pending notifications
    cur = _exec(db, "SELECT * FROM pending_notifications ORDER BY triggered_at DESC")
    pending = [dict(r) for r in cur.fetchall()]
    for p in pending:
        for k, v in p.items():
            if not isinstance(v, (str, int, float, bool, type(None))):
                p[k] = str(v)

    # Check recent notification log
    if _is_postgres():
        cur2 = _exec(db,
            """SELECT nl.*, u.email, u.display_name
               FROM notification_log nl
               JOIN users u ON nl.user_id = u.id
               ORDER BY nl.created_at DESC LIMIT 20"""
        )
    else:
        cur2 = _exec(db,
            """SELECT nl.*, u.email, u.display_name
               FROM notification_log nl
               JOIN users u ON nl.user_id = u.id
               ORDER BY nl.created_at DESC LIMIT 20"""
        )
    recent_logs = [dict(r) for r in cur2.fetchall()]
    for r in recent_logs:
        for k, v in r.items():
            if not isinstance(v, (str, int, float, bool, type(None))):
                r[k] = str(v)

    # Session info (modes, participants, unread counts)
    cur3 = _exec(db, "SELECT id, topic, session_mode, session_type FROM mediation_sessions ORDER BY id")
    sessions_info = []
    for s in cur3.fetchall():
        s_dict = dict(s)
        for k, v in s_dict.items():
            if not isinstance(v, (str, int, float, bool, type(None))):
                s_dict[k] = str(v)
        # Get participant count
        cur4 = _exec(db, "SELECT COUNT(*) as cnt FROM session_participants WHERE session_id = ?", (s['id'],))
        s_dict['participant_count'] = cur4.fetchone()['cnt']
        # Get last_seen_at for current user
        cur5 = _exec(db, "SELECT last_seen_at FROM session_last_seen WHERE session_id = ? AND user_id = ?",
                      (s['id'], current_user.id))
        ls = cur5.fetchone()
        s_dict['my_last_seen_at'] = str(ls['last_seen_at']) if ls else None
        # Get latest message timestamp
        cur6 = _exec(db, "SELECT created_at FROM messages WHERE session_id = ? ORDER BY created_at DESC LIMIT 1", (s['id'],))
        lm = cur6.fetchone()
        s_dict['latest_message_at'] = str(lm['created_at']) if lm else None
        sessions_info.append(s_dict)

    return jsonify({
        'worker_state': _notification_worker_state,
        'pending_notifications': pending,
        'recent_notification_log': recent_logs,
        'sessions': sessions_info,
    })


# --- Notification Helpers ---

def queue_pending_notifications(db, session_id, sender_user_id):
    """Queue notifications for other participants who aren't currently active."""
    try:
        med_session = MediationSession.get_by_id(db, session_id)
        if not med_session:
            logger.warning(f"[Notify] Queue skipped: session {session_id} not found")
            return
        # Only for group sessions
        if med_session.session_mode == 'personal':
            return

        participants = med_session.get_participants(db)
        for p in participants:
            if p.id == sender_user_id:
                continue
            try:
                _exec(db,
                    """INSERT INTO pending_notifications (session_id, target_user_id, triggered_at)
                       VALUES (?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(session_id, target_user_id)
                       DO UPDATE SET triggered_at = CURRENT_TIMESTAMP""",
                    (session_id, p.id)
                )
                db.commit()
                logger.info(f"[Notify] Queued: session={session_id} target_user={p.id} sender={sender_user_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"[Notify] FAILED to queue: session={session_id} target_user={p.id} error={e}")
    except Exception as e:
        logger.error(f"[Notify] Error queuing notifications: {e}")


def process_pending_notifications():
    """Process pending notifications older than 60 minutes. Called by background worker."""
    db = None
    try:
        db = get_worker_db()

        # Find pending notifications older than 60 minutes
        if _is_postgres():
            cur = _exec(db,
                """SELECT pn.id, pn.session_id, pn.target_user_id, pn.triggered_at
                   FROM pending_notifications pn
                   WHERE pn.triggered_at < CURRENT_TIMESTAMP - INTERVAL '60 minutes'"""
            )
        else:
            cur = _exec(db,
                """SELECT pn.id, pn.session_id, pn.target_user_id, pn.triggered_at
                   FROM pending_notifications pn
                   WHERE pn.triggered_at < datetime('now', '-60 minutes')"""
            )

        pending = cur.fetchall()
        if not pending:
            return 0

        logger.info(f"[Notify] Processing {len(pending)} pending notification(s)")

        for row in pending:
            pn_id = row['id']
            session_id = row['session_id']
            target_user_id = row['target_user_id']
            triggered_at = row['triggered_at']

            # Check if user has visited since the notification was triggered
            cur2 = _exec(db,
                """SELECT last_seen_at FROM session_last_seen
                   WHERE session_id = ? AND user_id = ?""",
                (session_id, target_user_id)
            )
            last_seen = cur2.fetchone()
            if last_seen and str(last_seen['last_seen_at']) > str(triggered_at):
                logger.info(f"[Notify] Skipped session={session_id} user={target_user_id}: visited since trigger (last_seen={last_seen['last_seen_at']} > triggered={triggered_at})")
                _exec(db, "DELETE FROM pending_notifications WHERE id = ?", (pn_id,))
                db.commit()
                continue

            # Get notification preferences
            cur3 = _exec(db,
                "SELECT * FROM notification_preferences WHERE user_id = ?",
                (target_user_id,)
            )
            prefs = cur3.fetchone()
            email_enabled = True  # default on
            sms_enabled = False
            phone_number = None
            phone_verified = False
            if prefs:
                email_enabled = bool(prefs['email_enabled'])
                sms_enabled = bool(prefs['sms_enabled'])
                phone_number = prefs['phone_number']
                phone_verified = bool(prefs['phone_verified'])

            # Get session and user details
            med_session = MediationSession.get_by_id(db, session_id)
            target_user = User.get_by_id(db, target_user_id)
            if not med_session or not target_user:
                logger.warning(f"[Notify] Skipped session={session_id} user={target_user_id}: session or user not found")
                _exec(db, "DELETE FROM pending_notifications WHERE id = ?", (pn_id,))
                db.commit()
                continue

            # Find who sent the most recent message (for the email)
            cur4 = _exec(db,
                """SELECT user_id FROM messages
                   WHERE session_id = ? AND user_id IS NOT NULL AND user_id != ?
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id, target_user_id)
            )
            sender_row = cur4.fetchone()
            other_name = 'Someone'
            if sender_row:
                sender = User.get_by_id(db, sender_row['user_id'])
                if sender:
                    other_name = sender.display_name

            base_url = os.environ.get('BASE_URL', 'https://www.vilora.io')
            session_link = f"{base_url}/session/{session_id}"

            # Check email frequency caps: max 1 per 4 hours per session, 6/day total
            if email_enabled:
                if _is_postgres():
                    cur5 = _exec(db,
                        """SELECT COUNT(*) as cnt FROM notification_log
                           WHERE user_id = ? AND session_id = ? AND channel = 'email'
                           AND created_at > CURRENT_TIMESTAMP - INTERVAL '4 hours'""",
                        (target_user_id, session_id)
                    )
                else:
                    cur5 = _exec(db,
                        """SELECT COUNT(*) as cnt FROM notification_log
                           WHERE user_id = ? AND session_id = ? AND channel = 'email'
                           AND created_at > datetime('now', '-4 hours')""",
                        (target_user_id, session_id)
                    )
                session_email_count = cur5.fetchone()['cnt']
                if session_email_count == 0:
                    # Check daily cap
                    if _is_postgres():
                        cur6 = _exec(db,
                            """SELECT COUNT(*) as cnt FROM notification_log
                               WHERE user_id = ? AND channel = 'email'
                               AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'""",
                            (target_user_id,)
                        )
                    else:
                        cur6 = _exec(db,
                            """SELECT COUNT(*) as cnt FROM notification_log
                               WHERE user_id = ? AND channel = 'email'
                               AND created_at > datetime('now', '-24 hours')""",
                            (target_user_id,)
                        )
                    daily_count = cur6.fetchone()['cnt']
                    if daily_count < 6:
                        logger.info(f"[Notify] Sending email: session={session_id} to={target_user.email} from={other_name}")
                        success = send_activity_email(
                            target_user.email,
                            target_user.display_name,
                            other_name,
                            med_session.topic,
                            session_link
                        )
                        if success:
                            _exec(db,
                                "INSERT INTO notification_log (session_id, user_id, channel) VALUES (?, ?, 'email')",
                                (session_id, target_user_id)
                            )
                            db.commit()
                            logger.info(f"[Notify] Email sent successfully: session={session_id} to={target_user.email}")
                        else:
                            logger.error(f"[Notify] Email send FAILED: session={session_id} to={target_user.email}")
                    else:
                        logger.info(f"[Notify] Skipped email: session={session_id} user={target_user_id} daily cap reached ({daily_count}/6)")
                else:
                    logger.info(f"[Notify] Skipped email: session={session_id} user={target_user_id} already emailed this session in past 4h ({session_email_count})")
            else:
                logger.info(f"[Notify] Skipped email: session={session_id} user={target_user_id} email_enabled=False")

            # Check SMS frequency caps: max 1 per 6 hours per session, 4/day total
            if sms_enabled and phone_verified and phone_number:
                if _is_postgres():
                    cur7 = _exec(db,
                        """SELECT COUNT(*) as cnt FROM notification_log
                           WHERE user_id = ? AND session_id = ? AND channel = 'sms'
                           AND created_at > CURRENT_TIMESTAMP - INTERVAL '6 hours'""",
                        (target_user_id, session_id)
                    )
                else:
                    cur7 = _exec(db,
                        """SELECT COUNT(*) as cnt FROM notification_log
                           WHERE user_id = ? AND session_id = ? AND channel = 'sms'
                           AND created_at > datetime('now', '-6 hours')""",
                        (target_user_id, session_id)
                    )
                if cur7.fetchone()['cnt'] == 0:
                    if _is_postgres():
                        cur8 = _exec(db,
                            """SELECT COUNT(*) as cnt FROM notification_log
                               WHERE user_id = ? AND channel = 'sms'
                               AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'""",
                            (target_user_id,)
                        )
                    else:
                        cur8 = _exec(db,
                            """SELECT COUNT(*) as cnt FROM notification_log
                               WHERE user_id = ? AND channel = 'sms'
                               AND created_at > datetime('now', '-24 hours')""",
                            (target_user_id,)
                        )
                    if cur8.fetchone()['cnt'] < 4:
                        success = send_activity_sms(phone_number, med_session.topic, session_link)
                        if success:
                            _exec(db,
                                "INSERT INTO notification_log (session_id, user_id, channel) VALUES (?, ?, 'sms')",
                                (session_id, target_user_id)
                            )
                            db.commit()
                            logger.info(f"[Notify] SMS sent: session={session_id} to={phone_number}")

            # Delete the pending notification
            _exec(db, "DELETE FROM pending_notifications WHERE id = ?", (pn_id,))
            db.commit()

        return len(pending)

    except Exception as e:
        logger.error(f"[Notify] Worker error: {e}")
        return -1
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def start_notification_worker():
    """Start background thread that processes pending notifications every 60 seconds."""
    import threading
    import time

    def worker():
        cycle = 0
        while True:
            time.sleep(60)
            cycle += 1
            try:
                from datetime import datetime
                _notification_worker_state['cycle'] = cycle
                _notification_worker_state['last_run'] = datetime.utcnow().isoformat()
                result = process_pending_notifications()
                _notification_worker_state['last_result'] = result
                _notification_worker_state['last_error'] = None
            except Exception as e:
                _notification_worker_state['last_error'] = str(e)
                logger.error(f"[Notify] Worker crash cycle={cycle}: {e}", exc_info=True)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    logger.info("[Notify] Notification worker started.")


# --- Init ---

with app.app_context():
    db_init()

# Start notification worker (avoid double-start in Flask debug reloader)
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN'):
    start_notification_worker()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fix-titles':
        with app.app_context():
            db = get_db()
            cur = _exec(db, "SELECT id, topic FROM mediation_sessions WHERE session_mode = 'personal'")
            sessions = cur.fetchall()
            print(f"Found {len(sessions)} personal sessions to fix.")
            for s in sessions:
                if len(s['topic']) <= 60:
                    print(f"  Session {s['id']}: already short, skipping.")
                    continue
                try:
                    new_title = mediation_engine.generate_title(s['topic'])
                    _exec(db, "UPDATE mediation_sessions SET topic = ? WHERE id = ?", (new_title, s['id']))
                    db.commit()
                    print(f"  Session {s['id']}: '{new_title}'")
                except Exception as e:
                    print(f"  Session {s['id']}: ERROR — {e}")
            print("Done.")
    else:
        app.run(debug=True, port=int(os.environ.get('PORT', 5001)), host='0.0.0.0')
