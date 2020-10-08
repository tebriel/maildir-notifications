#!/usr/bin/env python3
import json
import sys
import argparse
import mailbox
import email
from email.mime.text import MIMEText
from pathlib import Path
from getpass import getuser, getpass
import keyring
from github3 import authorize, login, notifications

APP_NAME = 'mnotifications'

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fetch github notifications and store them in a maildir format')
    parser.add_argument('--clean', help='Remove your credentials', action=argparse.BooleanOptionalAction)
    parser.add_argument('--echo-token', help='Echo your token to the cli', action=argparse.BooleanOptionalAction)
    return parser.parse_args()

def echo_token() -> None:
    print(keyring.get_credential(APP_NAME, getuser()).password)

def auth() -> str:
    user = getuser()
    password = getpass('Password for {0}: '.format(user))
    if password is None:
        print('Did not get a password')
        sys.exit(1)
    note = 'maildir-notifications'
    note_url = 'http://github.com'
    scopes = ['user', 'notifications', 'repo', 'read:discussion']

    auth_result = authorize(user, password, scopes, note, note_url, two_factor_callback=get_2fa)
    return '{0}:{1}'.format(auth_result.id, auth_result.token)


def clean() -> None:
    keyring.delete_password(APP_NAME, getuser())


def main():
    args = parse_args()
    if args.clean:
        clean()
    elif args.echo_token:
        echo_token()
    else:
        user: str = getuser()
        cred = keyring.get_credential(APP_NAME, user)
        if cred is None:
            token = auth()
            keyring.set_password(APP_NAME, user, token)
            cred = keyring.get_credential(APP_NAME, user)

        [auth_id, token] = cred.password.split(':')
        gh = login(token=token)
        print(gh.user('tebriel').id)
        maildir = get_maildir()
        maildir = maildir.get_folder('INBOX')
        for n in gh.notifications():
            print(n)
            add_notification(maildir, n)


def get_maildir() -> mailbox.Maildir:
    m = mailbox.Maildir(Path.home().joinpath('.mail', 'github-notifications'), create=True)
    if 'INBOX' not in m.list_folders():
        print('Creating INBOX folder')
        m.add_folder('INBOX')
    return m

def add_notification(m: mailbox.Maildir, notification: notifications.Thread) -> None:
    text = MIMEText(json.dumps(notification.as_dict(), indent=2))
    text['From'] = '{0}/{1}'.format(notification.repository.owner, notification.repository.name)
    text['Subject'] = notification.subject['title']
    text['Date'] = notification.updated_at.isoformat()
    if notification.subject['type'] == 'PullRequest':
        pass


    message = mailbox.MaildirMessage(message=text)
    m.add(message)
    m.flush()


def get_2fa() -> str:
    return getpass('2FA token for {0}: '.format(getuser()))


if __name__ == '__main__':
    main()
