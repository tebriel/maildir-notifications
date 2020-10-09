import json
import mailbox
import shutil
import socket
from hashlib import sha256
from datetime import datetime, timezone
from email.mime.text import MIMEText
from getpass import getuser
from pathlib import Path

from github3.notifications import Thread
from mnotifications.db import Database

DATE_FMT = '%a, %d %b %Y %H:%M:%S %z'


class Mail:
    MDIR_PATH = Path.home().joinpath('.mail', 'github-notifications')

    @staticmethod
    def empty(maildir_path: Path=None) -> None:
        """Empty the current maildir to start fresh."""
        maildir_path = maildir_path or Mail.MDIR_PATH
        if maildir_path.exists():
            shutil.rmtree(maildir_path)
        Database.delete()

    @staticmethod
    def get_maildir(maildir_path: Path=None) -> mailbox.Maildir:
        maildir_path = maildir_path or Mail.MDIR_PATH
        m = mailbox.Maildir(maildir_path, create=True)
        if 'INBOX' not in m.list_folders():
            m.add_folder('INBOX')
        return m.get_folder('INBOX')

    def __init__(self, maildir_path: Path=None):
        self.db = Database()
        self.maildir_path = maildir_path or self.MDIR_PATH

    def connect(self):
        self.maildir_path.mkdir(parents=True, exist_ok=True)
        self.maildir = Mail.get_maildir(self.maildir_path)
        self.db.connect()

    def add_notification(self, notification: Thread) -> None:
        text_msg = self.build_from_notification(notification)
        message_id = text_msg.get('Message-ID')
        if self.db.mail_exists(message_id):
            key = self.db.mail_key(message_id)
            mail = self.maildir.get(key)
            if notification.unread:
                mail.set_flags(['S'])
            else:
                mail.remove_flag('S')
            return

        message = mailbox.MaildirMessage(message=text_msg)
        if not notification.unread:
            message.set_flags(['S'])
        key = self.maildir.add(message)
        self.maildir.flush()
        self.db.add(text_msg.get('Message-ID'), key, notification.updated_at)

    def build_from_notification(self, notification: Thread) -> MIMEText:
        text = MIMEText(json.dumps(notification.as_dict(), indent=2))
        text['Date'] = notification.updated_at.strftime(DATE_FMT)
        text['From'] = '{0}/{1}'.format(notification.repository.owner, notification.repository.name)
        text['To'] = getuser()
        text['Subject'] = notification.subject['title']
        text['Received'] = 'from github.com by {0} with maildir-notifications; {1}'.format(
            socket.gethostname(),
            datetime.now(tz=timezone.utc).strftime(DATE_FMT)
        )
        text['Message-ID'] = sha256(notification.url.encode('utf-8')).hexdigest()
        if notification.subject['type'] == 'PullRequest':
            pass

        return text
