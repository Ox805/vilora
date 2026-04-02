import os
import sys
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.database import db_init, get_db, _exec, User, MediationSession, Message
from mediation.engine import MediationEngine
from notifications import send_invite_email, send_password_reset_email, send_nudge_email

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

    user = User.create(db, email, display_name, password)
    login_user(user)
    redirect_url = '/dashboard'
    pending = session.pop('pending_join', None)
    if pending:
        redirect_url = url_for('join_session', code=pending)
    return jsonify({'success': True, 'redirect': redirect_url})


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
    return jsonify({'sessions': [s.to_dict() for s in sessions]})


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


# --- About Me Page ---

@app.route('/about-me')
@login_required
def about_me():
    return render_template('about_me.html')


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


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

def _run_council_background(job_id, question, context, user_memories):
    try:
        sys.stderr.write(f"[Vilora] Council job {job_id} starting\n")
        result = mediation_engine.run_council(
            question=question,
            context=context,
            user_memories=user_memories
        )
        _council_jobs[job_id] = {'status': 'done', 'result': result}
        sys.stderr.write(f"[Vilora] Council job {job_id} completed\n")
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
        args=(job_id, question, full_context or None, memories or None),
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
            Message.create(db, med_session.id, None, ai_response, msg_type='mediator')
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

    _exec(db, "DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
    _exec(db, "DELETE FROM session_invites WHERE session_id = ?", (session_id,))
    _exec(db, "DELETE FROM user_memories WHERE source_session_id = ?", (session_id,))
    _exec(db, "DELETE FROM messages WHERE session_id = ?", (session_id,))
    _exec(db, "DELETE FROM agreements WHERE session_id = ?", (session_id,))
    _exec(db, "DELETE FROM session_participants WHERE session_id = ?", (session_id,))
    _exec(db, "DELETE FROM mediation_sessions WHERE id = ?", (session_id,))
    db.commit()
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

    return render_template('session.html', session=med_session,
                           participants=participants, is_creator=is_creator,
                           invite_link=invite_link, creator_name=creator_name,
                           is_personal=(med_session.session_mode == 'personal'))


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
    msg_list = []
    for m in messages:
        d = m.to_dict()
        d['display_name'] = name_map.get(m.user_id)
        d['is_self'] = (m.user_id == current_user.id)
        msg_list.append(d)
    return jsonify({'messages': msg_list})


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
            ai_msg = Message.create(db, session_id, None, ai_response, msg_type='mediator')
    except Exception as e:
        sys.stderr.write(f"[Vilora] Mediation error: {e}\n")

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

    # Users can delete their own messages
    # Session creator can also delete mediator messages
    if msg['user_id'] == current_user.id:
        pass  # allowed
    elif msg['msg_type'] == 'mediator' and med_session.creator_id == current_user.id:
        pass  # creator can delete Vilora messages
    else:
        return jsonify({'success': False, 'error': 'You can only delete your own messages'}), 403

    _exec(db, "DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/sessions/<int:session_id>/ask-vilora', methods=['POST'])
@login_required
def ask_vilora(session_id):
    """Explicitly request Vilora's input in a group session."""
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

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
            session_mode=med_session.session_mode
        )
        ai_msg = Message.create(db, session_id, None, ai_response, msg_type='mediator')
        return jsonify({'success': True, 'mediator_message': ai_msg.to_dict()})
    except Exception as e:
        sys.stderr.write(f"[Vilora] Ask Vilora error: {e}\n")
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


# --- Init ---

with app.app_context():
    db_init()

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
