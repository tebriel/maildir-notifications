import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

CURRENT_VERSION = 1

class Database:
    DB_ROOT_PATH = Path.home().joinpath('.mnotifications', 'notifications.db')

    @staticmethod
    def delete(root_path: Path=None):
        root_path = root_path or Database.DB_ROOT_PATH
        if str(root_path).endswith('.db') and root_path.exists():
            root_path.unlink()

    def __init__(self, root_path: Path=None):
        self.root_path = root_path or Database.DB_ROOT_PATH

    def connect(self):
        self.root_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.root_path)
        self.migrate_db()

    def migrate_db(self) -> None:
        tables = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        if ('version',) not in tables:
            self.create_version_table()
            self.create_mail_table()
            self.create_updates_table()

    def create_version_table(self):
        self.conn.execute('CREATE TABLE version (version INTEGER)')
        self.conn.execute('INSERT INTO version VALUES (?)', [CURRENT_VERSION])
        self.conn.commit()

    def create_updates_table(self):
        self.conn.execute('CREATE TABLE updates (last_run REAL)')
        self.conn.commit()

    def create_mail_table(self):
        self.conn.execute('''
CREATE TABLE mail
  (id text,
   key text,
   last_updated REAL)
''')
        self.conn.commit()

    def mail_exists(self, m_id: str) -> bool:
        return self.mail_key(m_id) != None

    def mail_key(self, m_id: str) -> str:
        exists = self.conn.execute(
            'SELECT key FROM mail where id=?', (m_id, )
        ).fetchone()
        if exists:
            return exists[0]

    def add(self, message_id: str, key: str, last_updated: datetime) -> None:
        if not self.mail_exists(message_id):
            self.conn.execute(
                'INSERT INTO mail VALUES (?, ?, ?)',
                (message_id, key, last_updated.timestamp(),),
            )
            self.conn.commit()

    def set_last_update(self, run: datetime):
        self.conn.execute(
            'INSERT into updates VALUES (?)',
            (run.timestamp(),),
        )
        self.conn.commit()

    def get_last_update(self) -> datetime:
        result = self.conn.execute(
            'SELECT MAX(last_run) from updates'
        ).fetchone()
        if result[0]:
            return datetime.fromtimestamp(result[0])
