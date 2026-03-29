import os
import secrets
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models.database import db_init, get_db, User, MediationSession, Message
from mediation.engine import MediationEngine

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

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
        return jsonify({'success': True})
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
    return jsonify({'success': True})


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
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

    return render_template('session.html', session=med_session)


@app.route('/api/sessions/<int:session_id>/messages', methods=['GET'])
@login_required
def get_messages(session_id):
    db = get_db()
    med_session = MediationSession.get_by_id(db, session_id)
    if not med_session or not med_session.is_participant(db, current_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    messages = Message.get_by_session(db, session_id)
    return jsonify({'messages': [m.to_dict() for m in messages]})


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

    # Get AI mediator response
    messages = Message.get_by_session(db, session_id)
    participants = med_session.get_participants(db)
    ai_response = mediation_engine.mediate(
        topic=med_session.topic,
        session_type=med_session.session_type,
        messages=messages,
        participants=participants
    )

    ai_msg = Message.create(db, session_id, None, ai_response, msg_type='mediator')

    return jsonify({
        'success': True,
        'user_message': user_msg.to_dict(),
        'mediator_message': ai_msg.to_dict()
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
    summary = mediation_engine.summarize(
        topic=med_session.topic,
        messages=messages,
        participants=participants
    )

    return jsonify({'success': True, 'summary': summary})


# --- Init ---

with app.app_context():
    db_init()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
