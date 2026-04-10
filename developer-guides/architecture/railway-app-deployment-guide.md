# Railway App Deployment & Auth System Guide

**Last Updated:** 2026-04-10

A systematic roadmap for setting up a new Flask web app on Railway with PostgreSQL, user registration, login, password reset (email), optional 2FA, and password visibility toggles.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Dependencies](#2-dependencies)
3. [Database Setup (SQLite + PostgreSQL)](#3-database-setup-sqlite--postgresql)
4. [User Model & Password Hashing](#4-user-model--password-hashing)
5. [Flask App Configuration](#5-flask-app-configuration)
6. [Auth Routes (API)](#6-auth-routes-api)
7. [Auth Templates & Frontend](#7-auth-templates--frontend)
8. [Password Visibility Toggle](#8-password-visibility-toggle)
9. [Password Reset (Email Flow)](#9-password-reset-email-flow)
10. [Optional: Two-Factor Authentication (TOTP)](#10-optional-two-factor-authentication-totp)
11. [Railway Deployment](#11-railway-deployment)
12. [Railway CLI Reference](#12-railway-cli-reference)
13. [Environment Variables Reference](#13-environment-variables-reference)
14. [Security Checklist](#14-security-checklist)

---

## 1. Project Structure

```
my-app/
├── app.py                  # Flask app, routes, config
├── models/
│   └── database.py         # Database class, User model, migrations
├── templates/
│   ├── login.html          # Login + Register (tabbed)
│   ├── forgot_password.html
│   └── reset_password.html
├── static/                 # CSS, JS, images
├── requirements.txt
├── Procfile                # Railway/Gunicorn entry point
├── .env                    # Local secrets (never committed)
└── .gitignore
```

---

## 2. Dependencies

**requirements.txt:**

```
Flask>=2.3.0
Flask-Login>=0.6.0
Flask-Mail>=0.10.0
gunicorn>=21.0.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
```

Add these only if using optional 2FA:

```
pyotp>=2.9.0
qrcode[pil]>=7.4.0
```

**Procfile:**

```
web: gunicorn app:app
```

---

## 3. Database Setup (SQLite + PostgreSQL)

The app should auto-detect which database to use based on the `DATABASE_URL` env var. SQLite for local dev, PostgreSQL on Railway.

### 3.1 Database Class Init

```python
import os
import sqlite3
from urllib.parse import urlparse

class Database:
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            self._init_postgres(database_url)
        else:
            self._init_sqlite()
```

### 3.2 SQLite Init (Local Development)

```python
def _init_sqlite(self):
    self.is_postgres = False
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self.conn.row_factory = sqlite3.Row

    self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
            ON password_reset_tokens(token);
    ''')
    self.conn.commit()
```

### 3.3 PostgreSQL Init (Railway Production)

```python
def _init_postgres(self, database_url):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    self.is_postgres = True
    url = urlparse(database_url)
    self.conn = psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.path[1:],
        cursor_factory=RealDictCursor
    )
    self.conn.autocommit = False

    cursor = self.conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
            ON password_reset_tokens(token)
    ''')
    self.conn.commit()
```

### 3.4 Helper: Execute Queries

Handle the parameter style difference (`?` for SQLite, `%s` for PostgreSQL):

```python
def _execute(self, query, params=None):
    if self.is_postgres:
        query = query.replace('?', '%s')
    cursor = self.conn.cursor()
    cursor.execute(query, params or ())
    return cursor

def _row_to_dict(self, row):
    if self.is_postgres:
        return dict(row)
    return dict(row)
```

---

## 4. User Model & Password Hashing

```python
from dataclasses import dataclass
from typing import Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@dataclass
class User(UserMixin):
    id: Optional[int] = None
    username: str = ''
    email: str = ''
    password_hash: str = ''
    totp_secret: Optional[str] = None
    totp_enabled: bool = False
    created_at: str = ''

    def get_id(self):
        return str(self.id)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
```

### Database Methods for Users

```python
def create_user(self, username, email, password):
    user = User(username=username, email=email)
    user.set_password(password)
    now = datetime.now().isoformat()
    cursor = self._execute(
        'INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
        (username, email, user.password_hash, now)
    )
    self.conn.commit()
    user.id = cursor.lastrowid if not self.is_postgres else self._get_last_id(cursor)
    user.created_at = now
    return user

def get_user_by_email(self, email):
    cursor = self._execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    if not row:
        return None
    d = self._row_to_dict(row)
    return User(**{k: v for k, v in d.items() if k in User.__dataclass_fields__})

def get_user_by_id(self, user_id):
    cursor = self._execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if not row:
        return None
    d = self._row_to_dict(row)
    return User(**{k: v for k, v in d.items() if k in User.__dataclass_fields__})

def update_user_password(self, user_id, new_password):
    user = User()
    user.set_password(new_password)
    self._execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (user.password_hash, user_id)
    )
    self.conn.commit()
    return True
```

---

## 5. Flask App Configuration

```python
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Email config for password reset
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
    'MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')
)
mail = Mail(app)

# Trust Railway's reverse proxy (fixes HTTPS detection, host headers)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = Database('app.db')

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(int(user_id))
```

---

## 6. Auth Routes (API)

### 6.1 Page Routes

```python
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>')
def reset_password_page(token):
    user = db.validate_reset_token(token)
    if not user:
        return render_template('reset_password.html', valid=False)
    return render_template('reset_password.html', valid=True, token=token)
```

### 6.2 Registration

```python
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    # Validation
    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': 'Username must be at least 3 characters'})
    if not username.isalnum():
        return jsonify({'success': False, 'error': 'Username must be alphanumeric'})
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'success': False, 'error': 'Invalid email address'})
    if not password or len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})

    # Duplicate checks
    if db.get_user_by_email(email):
        return jsonify({'success': False, 'error': 'Email already registered'})
    if db.get_user_by_username(username):
        return jsonify({'success': False, 'error': 'Username already taken'})

    user = db.create_user(username, email, password)
    if not user:
        return jsonify({'success': False, 'error': 'Failed to create account'})

    login_user(user)
    return jsonify({
        'success': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email}
    })
```

### 6.3 Login

```python
@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password required'})

    user = db.get_user_by_email(email)
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid email or password'})

    # If 2FA is enabled, don't log in yet -- return a prompt for the TOTP code
    if user.totp_enabled:
        session['pending_2fa_user_id'] = user.id
        return jsonify({'success': True, 'requires_2fa': True})

    login_user(user)
    return jsonify({
        'success': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email}
    })
```

### 6.4 2FA Verification (if enabled)

```python
@app.route('/api/auth/verify-2fa', methods=['POST'])
def verify_2fa():
    data = request.json or {}
    code = data.get('code', '').strip()
    user_id = session.get('pending_2fa_user_id')

    if not user_id:
        return jsonify({'success': False, 'error': 'No pending 2FA session'})

    user = db.get_user_by_id(user_id)
    if not user or not user.totp_enabled:
        return jsonify({'success': False, 'error': 'Invalid session'})

    import pyotp
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code, valid_window=1):
        return jsonify({'success': False, 'error': 'Invalid code'})

    session.pop('pending_2fa_user_id', None)
    login_user(user)
    return jsonify({
        'success': True,
        'user': {'id': user.id, 'username': user.username, 'email': user.email}
    })
```

### 6.5 Logout

```python
@app.route('/api/auth/logout', methods=['POST'])
@login_required
def auth_logout():
    logout_user()
    return jsonify({'success': True})
```

### 6.6 Current User

```python
@app.route('/api/auth/user')
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            }
        })
    return jsonify({'authenticated': False})
```

---

## 7. Auth Templates & Frontend

### 7.1 login.html (Tabbed Login + Register)

Key structure:

```html
<!-- Tab buttons -->
<div class="auth-tabs">
    <button class="tab-btn active" onclick="switchTab('login')">Login</button>
    <button class="tab-btn" onclick="switchTab('register')">Register</button>
</div>

<!-- Login form -->
<form id="login-form">
    <input type="email" id="login-email" required placeholder="Email">
    <div class="password-wrapper">
        <input type="password" id="login-password" required placeholder="Password">
        <button type="button" class="toggle-password" onclick="togglePassword('login-password', this)">
            <svg><!-- eye icon --></svg>
        </button>
    </div>
    <a href="/forgot-password">Forgot password?</a>
    <button type="submit">Login</button>
</form>

<!-- Register form (hidden by default) -->
<form id="register-form" class="hidden">
    <input type="text" id="reg-username" required minlength="3" pattern="[a-zA-Z0-9]+"
           placeholder="Username">
    <p class="hint">3+ alphanumeric characters</p>

    <input type="email" id="reg-email" required placeholder="Email">

    <div class="password-wrapper">
        <input type="password" id="reg-password" required minlength="6" placeholder="Password">
        <button type="button" class="toggle-password" onclick="togglePassword('reg-password', this)">
            <svg><!-- eye icon --></svg>
        </button>
    </div>
    <p class="hint">At least 6 characters</p>

    <div class="password-wrapper">
        <input type="password" id="reg-confirm" required placeholder="Confirm Password">
        <button type="button" class="toggle-password" onclick="togglePassword('reg-confirm', this)">
            <svg><!-- eye icon --></svg>
        </button>
    </div>
    <button type="submit">Create Account</button>
</form>

<!-- 2FA verification (hidden, shown when login returns requires_2fa) -->
<div id="2fa-section" class="hidden">
    <p>Enter the 6-digit code from your authenticator app:</p>
    <input type="text" id="2fa-code" maxlength="6" pattern="[0-9]{6}"
           placeholder="000000" inputmode="numeric" autocomplete="one-time-code">
    <button onclick="verify2FA()">Verify</button>
</div>
```

### 7.2 forgot_password.html

```html
<h2>Reset Password</h2>
<form id="forgot-form">
    <p>Enter your email and we'll send a reset link.</p>
    <input type="email" id="email" required placeholder="Email">
    <button type="submit" id="submit-btn">Send Reset Link</button>
</form>
<div id="success-msg" class="hidden">Check your email for a reset link.</div>
<div id="error-msg" class="hidden"></div>
<a href="/login">Back to Login</a>
```

### 7.3 reset_password.html

```html
{% if valid %}
<form id="reset-form">
    <input type="hidden" id="reset-token" value="{{ token }}">
    <div class="password-wrapper">
        <input type="password" id="new-password" required minlength="6"
               placeholder="New Password">
        <button type="button" class="toggle-password"
                onclick="togglePassword('new-password', this)">
            <svg><!-- eye icon --></svg>
        </button>
    </div>
    <div class="password-wrapper">
        <input type="password" id="confirm-password" required
               placeholder="Confirm Password">
        <button type="button" class="toggle-password"
                onclick="togglePassword('confirm-password', this)">
            <svg><!-- eye icon --></svg>
        </button>
    </div>
    <button type="submit">Reset Password</button>
</form>
{% else %}
<p>This reset link is invalid or expired.</p>
<a href="/forgot-password">Request a new one</a>
{% endif %}
```

---

## 8. Password Visibility Toggle

### CSS

```css
.password-wrapper {
    position: relative;
}
.password-wrapper input {
    width: 100%;
    padding-right: 40px;  /* room for the eye icon */
}
.toggle-password {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    cursor: pointer;
    padding: 4px;
    color: #888;
}
.toggle-password:hover {
    color: #fff;
}
```

### JavaScript

```javascript
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = /* eye-off SVG icon */;
    } else {
        input.type = 'password';
        btn.innerHTML = /* eye SVG icon */;
    }
}
```

### SVG Icons

**Eye (password hidden -- click to show):**
```html
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
     fill="none" stroke="currentColor" stroke-width="2">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
</svg>
```

**Eye-off (password visible -- click to hide):**
```html
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
     fill="none" stroke="currentColor" stroke-width="2">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
</svg>
```

---

## 9. Password Reset (Email Flow)

### 9.1 Database Methods

```python
import secrets
from datetime import datetime, timedelta

def create_password_reset_token(self, user_id):
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires_at = (now + timedelta(hours=1)).isoformat()

    # Invalidate any existing tokens for this user
    self._execute(
        'UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0',
        (user_id,)
    )

    self._execute('''
        INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at)
        VALUES (?, ?, ?, 0, ?)
    ''', (user_id, token, expires_at, now.isoformat()))
    self.conn.commit()
    return token

def validate_reset_token(self, token):
    cursor = self._execute(
        'SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0',
        (token,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    d = self._row_to_dict(row)
    if datetime.now() > datetime.fromisoformat(d['expires_at']):
        return None
    return self.get_user_by_id(d['user_id'])

def consume_reset_token(self, token):
    self._execute(
        'UPDATE password_reset_tokens SET used = 1 WHERE token = ?',
        (token,)
    )
    self.conn.commit()
```

### 9.2 API Route

```python
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'})

    user = db.get_user_by_email(email)

    # Always return same message (prevents email enumeration)
    if not user:
        return jsonify({'success': True,
            'message': 'If an account exists with that email, a reset link has been sent.'})

    token = db.create_password_reset_token(user.id)
    reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"

    if app.config['MAIL_USERNAME']:
        try:
            msg = Message('Password Reset - My App', recipients=[email])
            msg.html = f"""
            <h2>Password Reset</h2>
            <p>Hi {user.username},</p>
            <p>You requested a password reset.</p>
            <p><a href="{reset_url}"
                  style="display:inline-block;padding:12px 24px;
                         background:#d4a843;color:#000;text-decoration:none;
                         border-radius:4px;font-weight:bold;">
                Reset Password
            </a></p>
            <p>Or copy this link: {reset_url}</p>
            <p>This link expires in 1 hour.</p>
            <p>If you didn't request this, ignore this email.</p>
            """
            mail.send(msg)
        except Exception as e:
            app.logger.warning(f"Failed to send reset email: {e}")
            app.logger.info(f"Reset URL for {email}: {reset_url}")
    else:
        app.logger.info(f"Mail not configured. Reset URL for {email}: {reset_url}")

    return jsonify({'success': True,
        'message': 'If an account exists with that email, a reset link has been sent.'})
```

### 9.3 Reset Submission Route

```python
@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    token = data.get('token', '')
    password = data.get('password', '')

    if not token or not password:
        return jsonify({'success': False, 'error': 'Token and password are required'})
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})

    user = db.validate_reset_token(token)
    if not user:
        return jsonify({'success': False,
            'error': 'Invalid or expired reset link. Please request a new one.'})

    db.update_user_password(user.id, password)
    db.consume_reset_token(token)
    return jsonify({'success': True, 'message': 'Password has been reset. You can now log in.'})
```

### 9.4 Gmail App Password Setup

To send emails via Gmail:

1. Enable **2-Step Verification** on the Google account
2. Go to **Google Account > Security > App Passwords**
3. Generate a new app password (select "Mail" / "Other")
4. Use that 16-character password as `MAIL_PASSWORD`

---

## 10. Optional: Two-Factor Authentication (TOTP)

### 10.1 Additional Dependencies

```
pyotp>=2.9.0
qrcode[pil]>=7.4.0
```

### 10.2 Database Columns

Already included in the schema above:

- `totp_secret TEXT` -- stores the TOTP secret key
- `totp_enabled INTEGER/BOOLEAN DEFAULT 0/FALSE`

### 10.3 Enable 2FA Route

```python
import pyotp
import qrcode
import io
import base64

@app.route('/api/auth/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    """Generate a TOTP secret and QR code for the user."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="My App"
    )

    # Generate QR code as base64 image
    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Store secret temporarily in session until user confirms
    session['pending_totp_secret'] = secret

    return jsonify({
        'success': True,
        'qr_code': f'data:image/png;base64,{qr_base64}',
        'secret': secret  # manual entry fallback
    })

@app.route('/api/auth/2fa/confirm', methods=['POST'])
@login_required
def confirm_2fa():
    """Verify the user's first TOTP code and enable 2FA."""
    data = request.json or {}
    code = data.get('code', '').strip()
    secret = session.get('pending_totp_secret')

    if not secret:
        return jsonify({'success': False, 'error': 'No pending 2FA setup'})

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        return jsonify({'success': False, 'error': 'Invalid code. Try again.'})

    db.enable_2fa(current_user.id, secret)
    session.pop('pending_totp_secret', None)
    return jsonify({'success': True, 'message': '2FA enabled successfully'})

@app.route('/api/auth/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for the user."""
    data = request.json or {}
    password = data.get('password', '')

    if not current_user.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid password'})

    db.disable_2fa(current_user.id)
    return jsonify({'success': True, 'message': '2FA disabled'})
```

### 10.4 Database Methods for 2FA

```python
def enable_2fa(self, user_id, totp_secret):
    self._execute(
        'UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?',
        (totp_secret, user_id)
    )
    self.conn.commit()

def disable_2fa(self, user_id):
    self._execute(
        'UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE id = ?',
        (user_id,)
    )
    self.conn.commit()
```

### 10.5 Login Flow with 2FA

The login route (Section 6.3) already handles this:

1. User submits email + password
2. If credentials valid AND `user.totp_enabled`:
   - Store `user.id` in `session['pending_2fa_user_id']`
   - Return `{'success': True, 'requires_2fa': True}`
   - Frontend shows the 6-digit code input
3. User submits TOTP code to `/api/auth/verify-2fa`
4. If valid, `login_user(user)` completes the login

### 10.6 Frontend: 2FA Code Input

```javascript
// In the login form handler:
const resp = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password})
});
const data = await resp.json();

if (data.success && data.requires_2fa) {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('2fa-section').classList.remove('hidden');
    document.getElementById('2fa-code').focus();
    return;
}

// 2FA verification
async function verify2FA() {
    const code = document.getElementById('2fa-code').value.trim();
    const resp = await fetch('/api/auth/verify-2fa', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code})
    });
    const data = await resp.json();
    if (data.success) {
        window.location.href = '/';
    } else {
        showError(data.error);
    }
}
```

---

## 11. Railway Deployment

### 11.1 Prerequisites

- GitHub repo with the app code
- Railway account (https://railway.com)

### 11.2 Step-by-Step: New Project

1. **Create project on Railway:**
   - Go to Railway dashboard > "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account and select the repo

2. **Add PostgreSQL:**
   - In your project, click "+ New" > "Database" > "PostgreSQL"
   - Railway auto-sets `DATABASE_URL` as a shared variable
   - **Important:** Link the `DATABASE_URL` variable to your web service:
     - Go to your web service > Variables
     - Add: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`

3. **Set environment variables on the web service:**
   ```
   SECRET_KEY=<generate-a-random-string>
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=<your-gmail>
   MAIL_PASSWORD=<your-gmail-app-password>
   MAIL_DEFAULT_SENDER=<sender-email>
   ```

4. **Deploy:**
   - Railway auto-detects Python + `Procfile` and deploys
   - Each `git push` to main triggers a redeploy

5. **Generate a public domain:**
   - Go to your web service > Settings > Networking
   - Click "Generate Domain" for a `*.up.railway.app` URL
   - Or add a custom domain

### 11.3 Step-by-Step: Railway CLI Setup

```bash
# Install CLI
curl -fsSL https://raw.githubusercontent.com/railwayapp/cli/master/install.sh | sh

# Login (opens browser)
railway login

# Link to existing project (interactive -- select project + service)
railway link

# Set variables
railway variables set KEY=value KEY2=value2

# View variables
railway variables

# View logs
railway logs

# Check status
railway status
```

---

## 12. Railway CLI Reference

| Command | Description |
|---------|-------------|
| `railway login` | Authenticate (opens browser) |
| `railway link` | Link current directory to a Railway project/service |
| `railway status` | Show linked project, environment, service |
| `railway variables` | List all env vars for the linked service |
| `railway variables set K=V` | Set one or more env vars (triggers redeploy) |
| `railway logs` | Stream deploy/runtime logs |
| `railway up` | Deploy current directory (without git push) |
| `railway open` | Open the Railway dashboard for this project |

---

## 13. Environment Variables Reference

### Required for Production

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string (set via Railway Postgres plugin) | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Flask session encryption key | Any long random string |

### Required for Password Reset Emails

| Variable | Description | Default |
|----------|-------------|---------|
| `MAIL_SERVER` | SMTP server | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USE_TLS` | Enable TLS | `true` |
| `MAIL_USERNAME` | SMTP login email | *(none)* |
| `MAIL_PASSWORD` | SMTP password (Gmail app password) | *(none)* |
| `MAIL_DEFAULT_SENDER` | "From" address on emails | Falls back to `MAIL_USERNAME` |

### Local Development (.env)

```env
SECRET_KEY=dev-secret-key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=support@yourdomain.com
```

---

## 14. Security Checklist

- [ ] `.env` is in `.gitignore` (never commit secrets)
- [ ] `*.db` is in `.gitignore` (don't commit SQLite files)
- [ ] Passwords hashed with `werkzeug.security.generate_password_hash` (PBKDF2)
- [ ] Login errors use generic message ("Invalid email or password") to prevent enumeration
- [ ] Forgot-password always returns same message regardless of email existence
- [ ] Reset tokens expire after 1 hour
- [ ] Reset tokens are single-use (consumed after password change)
- [ ] Previous unused tokens invalidated when new one is created
- [ ] `ProxyFix` middleware enabled for Railway's reverse proxy
- [ ] `SECRET_KEY` set to a strong random value in production (not the default `os.urandom`)
- [ ] 2FA secret stored server-side, never exposed after initial QR setup
- [ ] 2FA disable requires password confirmation
