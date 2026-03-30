import os
import sys
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message as MailMessage
from models.database import db_init, get_db, _exec, User, MediationSession, Message
from mediation.engine import MediationEngine

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Flask-Mail setup
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
mail = Mail(app)

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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
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

    sys.stderr.write(f"[Vilora] Password reset requested for {email}, user found: {user.display_name}\n")
    sys.stderr.write(f"[Vilora] MAIL_USERNAME={app.config.get('MAIL_USERNAME')}, MAIL_SERVER={app.config.get('MAIL_SERVER')}\n")
    sys.stderr.flush()

    if app.config['MAIL_USERNAME']:
        try:
            msg = MailMessage(
                subject='Password Reset - Vilora',
                recipients=[email]
            )
            msg.html = f"""
            <h2>Password Reset</h2>
            <p>Hi {user.display_name},</p>
            <p>You requested a password reset for your Vilora account.</p>
            <p><a href="{reset_link}" style="display:inline-block;padding:12px 24px;background:#4A6FA5;color:#fff;text-decoration:none;border-radius:4px;font-weight:bold;">Reset Password</a></p>
            <p>Or copy this link: {reset_link}</p>
            <p>This link expires in 1 hour.</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            """
            mail.send(msg)
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send reset email: {e}", exc_info=True)
            logger.info(f"Reset URL for {email}: {reset_link}")
    else:
        logger.warning(f"Mail not configured. Reset URL for {email}: {reset_link}")

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


# --- Session Management ---

@app.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    data = request.get_json()
    topic = data.get('topic', '').strip()
    session_type = data.get('type', 'general')
    perspective = data.get('perspective', '').strip()

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    db = get_db()
    invite_code = secrets.token_urlsafe(16)
    med_session = MediationSession.create(
        db,
        creator_id=current_user.id,
        topic=topic,
        session_type=session_type,
        invite_code=invite_code
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
                creator_name=current_user.display_name
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
        return redirect(url_for('login_page'))

    med_session.add_participant(db, current_user.id)
    return redirect(url_for('session_room', session_id=med_session.id))


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    if med_session.creator_id != current_user.id:
        return jsonify({'success': False, 'error': 'Only the session creator can delete it'}), 403

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
                           invite_link=invite_link, creator_name=creator_name)


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

    # Check if Vilora should chime in
    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)

    ai_msg = None
    try:
        if mediation_engine.should_respond(med_session.topic, messages, participants):
            ai_response = mediation_engine.mediate(
                topic=med_session.topic,
                session_type=med_session.session_type,
                messages=messages,
                participants=participants
            )
            ai_msg = Message.create(db, session_id, None, ai_response, msg_type='mediator')
    except Exception as e:
        sys.stderr.write(f"[Vilora] Mediation error: {e}\n")

    result = {'success': True, 'user_message': user_msg.to_dict()}
    if ai_msg:
        result['mediator_message'] = ai_msg.to_dict()
    return jsonify(result)


@app.route('/api/sessions/<int:session_id>/participants', methods=['GET'])
@login_required
def get_participants(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    participants = med_session.get_participants(db)
    return jsonify({
        'success': True,
        'participants': [{'id': p.id, 'display_name': p.display_name} for p in participants]
    })


@app.route('/api/sessions/<int:session_id>/summary', methods=['GET'])
@login_required
def get_summary(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    messages = Message.get_by_session(db, session_id)
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

    return jsonify({'success': True, 'summary': summary})


# --- Init ---

with app.app_context():
    db_init()

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5001)), host='0.0.0.0')
