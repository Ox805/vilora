import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import g, current_app
from flask_login import UserMixin


def _is_postgres():
    db_url = os.environ.get('DATABASE_URL')
    return bool(db_url and db_url.startswith('postgres'))


def get_db():
    if 'db' not in g:
        if _is_postgres():
            import psycopg2
            import psycopg2.extras
            db_url = os.environ.get('DATABASE_URL')
            g.db = psycopg2.connect(db_url)
            g.db.autocommit = False
        else:
            db_path = os.path.join(current_app.root_path, 'vilora.db')
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def _cursor(db):
    """Get a cursor that returns dict-like rows for both SQLite and PostgreSQL."""
    if _is_postgres():
        import psycopg2.extras
        return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return db.cursor()


def _exec(db, sql, params=None):
    """Execute a query, adapting placeholders for the database type."""
    if _is_postgres():
        sql = sql.replace('?', '%s')
    cur = _cursor(db)
    cur.execute(sql, params or ())
    return cur


def db_init():
    db = get_db()

    if _is_postgres():
        cur = db.cursor()
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                email_verified BOOLEAN DEFAULT FALSE,
                verification_token TEXT,
                verification_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS mediation_sessions (
                id SERIAL PRIMARY KEY,
                creator_id INTEGER NOT NULL REFERENCES users(id),
                topic TEXT NOT NULL,
                session_type TEXT DEFAULT 'general',
                session_mode TEXT DEFAULT 'mediation',
                invite_code TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS session_participants (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                user_id INTEGER REFERENCES users(id),
                content TEXT NOT NULL,
                msg_type TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS agreements (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                content TEXT NOT NULL,
                accepted_by TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS session_summaries (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                message_count INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS session_invites (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                email TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                invited_by INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS council_results (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES mediation_sessions(id),
                requested_by INTEGER NOT NULL REFERENCES users(id),
                question TEXT NOT NULL,
                context TEXT,
                advisors TEXT NOT NULL,
                review TEXT NOT NULL,
                synthesis TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS nudge_log (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES mediation_sessions(id),
                nudger_id INTEGER NOT NULL REFERENCES users(id),
                target TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_memories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_session_id INTEGER REFERENCES mediation_sessions(id),
                confidence REAL DEFAULT 1.0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories(user_id, active)",
            """CREATE TABLE IF NOT EXISTS message_reactions (
                id SERIAL PRIMARY KEY,
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                reaction TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, user_id, reaction)
            )""",
        ]
        for stmt in statements:
            try:
                cur.execute(stmt)
                db.commit()
            except Exception:
                db.rollback()

        # Migrations for existing tables
        migrations = [
            "ALTER TABLE mediation_sessions ADD COLUMN session_mode TEXT DEFAULT 'mediation'",
            "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN verification_token TEXT",
            "ALTER TABLE users ADD COLUMN verification_sent_at TIMESTAMP",
            "UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL OR email_verified = FALSE",
        ]
        for migration in migrations:
            try:
                cur.execute(migration)
                db.commit()
            except Exception:
                db.rollback()
    else:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                email_verified INTEGER DEFAULT 0,
                verification_token TEXT,
                verification_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mediation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                session_type TEXT DEFAULT 'general',
                session_mode TEXT DEFAULT 'mediation',
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

            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS session_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                message_count INTEGER NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES mediation_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS session_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                invited_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
                FOREIGN KEY (invited_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS council_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                requested_by INTEGER NOT NULL,
                question TEXT NOT NULL,
                context TEXT,
                advisors TEXT NOT NULL,
                review TEXT NOT NULL,
                synthesis TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
                FOREIGN KEY (requested_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS nudge_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                nudger_id INTEGER NOT NULL,
                target TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES mediation_sessions(id),
                FOREIGN KEY (nudger_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_session_id INTEGER,
                confidence REAL DEFAULT 1.0,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (source_session_id) REFERENCES mediation_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS message_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(message_id, user_id, reaction)
            );
        """)
        db.commit()


class User(UserMixin):
    def __init__(self, id, email, display_name, password_hash, created_at=None, email_verified=True):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.password_hash = password_hash
        self.created_at = created_at
        self.email_verified = bool(email_verified)

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
    def _from_row(row):
        return User(
            row['id'], row['email'], row['display_name'], row['password_hash'],
            row.get('created_at'), row.get('email_verified', True)
        )

    @staticmethod
    def create(db, email, display_name, password, email_verified=False):
        password_hash = generate_password_hash(password)
        if _is_postgres():
            cur = _exec(db,
                "INSERT INTO users (email, display_name, password_hash, email_verified) VALUES (?, ?, ?, ?) RETURNING id",
                (email, display_name, password_hash, email_verified)
            )
            user_id = cur.fetchone()['id']
        else:
            cur = _exec(db,
                "INSERT INTO users (email, display_name, password_hash, email_verified) VALUES (?, ?, ?, ?)",
                (email, display_name, password_hash, email_verified)
            )
            user_id = cur.lastrowid
        db.commit()
        return User(user_id, email, display_name, password_hash, email_verified=email_verified)

    @staticmethod
    def get_by_id(db, user_id):
        cur = _exec(db, "SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return User._from_row(row) if row else None

    @staticmethod
    def get_by_email(db, email):
        cur = _exec(db, "SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return User._from_row(row) if row else None

    def update_password(self, db, new_password):
        self.password_hash = generate_password_hash(new_password)
        _exec(db, "UPDATE users SET password_hash = ? WHERE id = ?", (self.password_hash, self.id))
        db.commit()


class MediationSession:
    def __init__(self, id, creator_id, topic, session_type, invite_code, status, created_at=None, session_mode='mediation'):
        self.id = id
        self.creator_id = creator_id
        self.topic = topic
        self.session_type = session_type
        self.session_mode = session_mode or 'mediation'
        self.invite_code = invite_code
        self.status = status
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'topic': self.topic,
            'session_type': self.session_type,
            'session_mode': self.session_mode,
            'invite_code': self.invite_code,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None
        }

    def is_participant(self, db, user_id):
        cur = _exec(db,
            "SELECT id FROM session_participants WHERE session_id = ? AND user_id = ?",
            (self.id, user_id)
        )
        return cur.fetchone() is not None

    def add_participant(self, db, user_id):
        try:
            _exec(db,
                "INSERT INTO session_participants (session_id, user_id) VALUES (?, ?)",
                (self.id, user_id)
            )
            db.commit()
        except Exception:
            db.rollback()

    def get_participants(self, db):
        cur = _exec(db,
            """SELECT u.* FROM users u
               JOIN session_participants sp ON u.id = sp.user_id
               WHERE sp.session_id = ?""",
            (self.id,)
        )
        rows = cur.fetchall()
        return [User(r['id'], r['email'], r['display_name'], r['password_hash'], r['created_at']) for r in rows]

    @staticmethod
    def create(db, creator_id, topic, session_type, invite_code, session_mode='mediation'):
        if _is_postgres():
            cur = _exec(db,
                "INSERT INTO mediation_sessions (creator_id, topic, session_type, session_mode, invite_code) VALUES (?, ?, ?, ?, ?) RETURNING id",
                (creator_id, topic, session_type, session_mode, invite_code)
            )
            session_id = cur.fetchone()['id']
        else:
            cur = _exec(db,
                "INSERT INTO mediation_sessions (creator_id, topic, session_type, session_mode, invite_code) VALUES (?, ?, ?, ?, ?)",
                (creator_id, topic, session_type, session_mode, invite_code)
            )
            session_id = cur.lastrowid
        db.commit()
        session = MediationSession(session_id, creator_id, topic, session_type, invite_code, 'active', session_mode=session_mode)
        session.add_participant(db, creator_id)
        return session

    @staticmethod
    def _from_row(row):
        return MediationSession(
            row['id'], row['creator_id'], row['topic'], row['session_type'],
            row['invite_code'], row['status'], row['created_at'],
            session_mode=row['session_mode'] if 'session_mode' in row.keys() else 'mediation'
        )

    @staticmethod
    def get_by_id(db, session_id):
        cur = _exec(db, "SELECT * FROM mediation_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        return MediationSession._from_row(row) if row else None

    @staticmethod
    def get_by_invite_code(db, code):
        cur = _exec(db, "SELECT * FROM mediation_sessions WHERE invite_code = ?", (code,))
        row = cur.fetchone()
        return MediationSession._from_row(row) if row else None

    @staticmethod
    def get_by_user(db, user_id):
        cur = _exec(db,
            """SELECT ms.* FROM mediation_sessions ms
               JOIN session_participants sp ON ms.id = sp.session_id
               WHERE sp.user_id = ? ORDER BY ms.created_at DESC""",
            (user_id,)
        )
        return [MediationSession._from_row(r) for r in cur.fetchall()]


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
        if _is_postgres():
            cur = _exec(db,
                "INSERT INTO messages (session_id, user_id, content, msg_type) VALUES (?, ?, ?, ?) RETURNING id",
                (session_id, user_id, content, msg_type)
            )
            msg_id = cur.fetchone()['id']
        else:
            cur = _exec(db,
                "INSERT INTO messages (session_id, user_id, content, msg_type) VALUES (?, ?, ?, ?)",
                (session_id, user_id, content, msg_type)
            )
            msg_id = cur.lastrowid
        db.commit()
        return Message(msg_id, session_id, user_id, content, msg_type)

    @staticmethod
    def get_by_session(db, session_id):
        cur = _exec(db,
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = cur.fetchall()
        return [
            Message(r['id'], r['session_id'], r['user_id'], r['content'], r['msg_type'], r['created_at'])
            for r in rows
        ]


class MessageReaction:
    VALID_REACTIONS = {'like', 'dislike', 'love', 'laugh', 'surprised', 'sad', 'haha', 'emphasis'}

    EMOJI_MAP = {
        'like': '\U0001f44d',
        'dislike': '\U0001f44e',
        'love': '\u2764\ufe0f',
        'laugh': '\U0001f602',
        'surprised': '\U0001f62e',
        'sad': '\U0001f622',
        'haha': '\U0001f923',
        'emphasis': '\u2757',
    }

    @classmethod
    def toggle(cls, db, message_id, user_id, reaction):
        if reaction not in cls.VALID_REACTIONS:
            raise ValueError(f"Invalid reaction: {reaction}")
        cur = _exec(db,
            "SELECT id FROM message_reactions WHERE message_id = ? AND user_id = ? AND reaction = ?",
            (message_id, user_id, reaction)
        )
        existing = cur.fetchone()
        if existing:
            _exec(db, "DELETE FROM message_reactions WHERE id = ?", (existing['id'],))
            db.commit()
            return 'removed'
        else:
            _exec(db,
                "INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, ?)",
                (message_id, user_id, reaction)
            )
            db.commit()
            return 'added'

    @classmethod
    def get_for_messages(cls, db, message_ids):
        if not message_ids:
            return {}
        placeholders = ','.join(['?'] * len(message_ids))
        cur = _exec(db,
            f"SELECT message_id, reaction, user_id FROM message_reactions WHERE message_id IN ({placeholders})",
            tuple(message_ids)
        )
        result = {}
        for row in cur.fetchall():
            mid = row['message_id']
            r = row['reaction']
            if mid not in result:
                result[mid] = {}
            if r not in result[mid]:
                result[mid][r] = {'count': 0, 'user_ids': []}
            result[mid][r]['count'] += 1
            result[mid][r]['user_ids'].append(row['user_id'])
        return result
