import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import g, current_app
from flask_login import UserMixin


def get_db():
    if 'db' not in g:
        db_url = os.environ.get('DATABASE_URL')
        if db_url and db_url.startswith('postgres'):
            import psycopg2
            g.db = psycopg2.connect(db_url)
        else:
            db_path = os.path.join(current_app.root_path, 'vilora.db')
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def db_init():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mediation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            session_type TEXT DEFAULT 'general',
            invite_code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS session_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(session_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            accepted_by TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES mediation_sessions(id)
        );
    """)
    db.commit()


class User(UserMixin):
    def __init__(self, id, email, display_name, password_hash, created_at=None):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.password_hash = password_hash
        self.created_at = created_at

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @staticmethod
    def create(db, email, display_name, password):
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (email, display_name, password_hash) VALUES (?, ?, ?)",
            (email, display_name, password_hash)
        )
        db.commit()
        return User(cursor.lastrowid, email, display_name, password_hash)

    @staticmethod
    def get_by_id(db, user_id):
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return User(row['id'], row['email'], row['display_name'], row['password_hash'], row['created_at'])
        return None

    @staticmethod
    def get_by_email(db, email):
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            return User(row['id'], row['email'], row['display_name'], row['password_hash'], row['created_at'])
        return None


class MediationSession:
    def __init__(self, id, creator_id, topic, session_type, invite_code, status, created_at=None):
        self.id = id
        self.creator_id = creator_id
        self.topic = topic
        self.session_type = session_type
        self.invite_code = invite_code
        self.status = status
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'topic': self.topic,
            'session_type': self.session_type,
            'invite_code': self.invite_code,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None
        }

    def is_participant(self, db, user_id):
        row = db.execute(
            "SELECT id FROM session_participants WHERE session_id = ? AND user_id = ?",
            (self.id, user_id)
        ).fetchone()
        return row is not None

    def add_participant(self, db, user_id):
        try:
            db.execute(
                "INSERT INTO session_participants (session_id, user_id) VALUES (?, ?)",
                (self.id, user_id)
            )
            db.commit()
        except (sqlite3.IntegrityError, Exception):
            pass  # Already a participant

    def get_participants(self, db):
        rows = db.execute(
            """SELECT u.* FROM users u
               JOIN session_participants sp ON u.id = sp.user_id
               WHERE sp.session_id = ?""",
            (self.id,)
        ).fetchall()
        return [User(r['id'], r['email'], r['display_name'], r['password_hash'], r['created_at']) for r in rows]

    @staticmethod
    def create(db, creator_id, topic, session_type, invite_code):
        cursor = db.execute(
            "INSERT INTO mediation_sessions (creator_id, topic, session_type, invite_code) VALUES (?, ?, ?, ?)",
            (creator_id, topic, session_type, invite_code)
        )
        db.commit()
        session = MediationSession(cursor.lastrowid, creator_id, topic, session_type, invite_code, 'active')
        session.add_participant(db, creator_id)
        return session

    @staticmethod
    def get_by_id(db, session_id):
        row = db.execute("SELECT * FROM mediation_sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            return MediationSession(
                row['id'], row['creator_id'], row['topic'], row['session_type'],
                row['invite_code'], row['status'], row['created_at']
            )
        return None

    @staticmethod
    def get_by_invite_code(db, code):
        row = db.execute("SELECT * FROM mediation_sessions WHERE invite_code = ?", (code,)).fetchone()
        if row:
            return MediationSession(
                row['id'], row['creator_id'], row['topic'], row['session_type'],
                row['invite_code'], row['status'], row['created_at']
            )
        return None

    @staticmethod
    def get_by_user(db, user_id):
        rows = db.execute(
            """SELECT ms.* FROM mediation_sessions ms
               JOIN session_participants sp ON ms.id = sp.session_id
               WHERE sp.user_id = ? ORDER BY ms.created_at DESC""",
            (user_id,)
        ).fetchall()
        return [
            MediationSession(r['id'], r['creator_id'], r['topic'], r['session_type'],
                             r['invite_code'], r['status'], r['created_at'])
            for r in rows
        ]


class Message:
    def __init__(self, id, session_id, user_id, content, msg_type, created_at=None):
        self.id = id
        self.session_id = session_id
        self.user_id = user_id
        self.content = content
        self.msg_type = msg_type
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'content': self.content,
            'msg_type': self.msg_type,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @staticmethod
    def create(db, session_id, user_id, content, msg_type='user'):
        cursor = db.execute(
            "INSERT INTO messages (session_id, user_id, content, msg_type) VALUES (?, ?, ?, ?)",
            (session_id, user_id, content, msg_type)
        )
        db.commit()
        return Message(cursor.lastrowid, session_id, user_id, content, msg_type)

    @staticmethod
    def get_by_session(db, session_id):
        rows = db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        ).fetchall()
        return [
            Message(r['id'], r['session_id'], r['user_id'], r['content'], r['msg_type'], r['created_at'])
            for r in rows
        ]
