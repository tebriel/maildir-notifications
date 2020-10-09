#!/usr/bin/env python3
import json
import sys
import argparse
import socket
from datetime import datetime, timezone
from email.mime.text import MIMEText
from getpass import getuser, getpass
import keyring
from github3 import authorize, login, notifications

from mnotifications.mail import Mail

APP_NAME = 'mnotifications'

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fetch github notifications and store them in a maildir format')
    parser.add_argument('--clean', help='Remove your credentials', action='store_true')
    parser.add_argument('--empty', help='Remove your credentials', action='store_true')
    parser.add_argument('--echo-token', help='Echo your token to the cli', action='store_true')
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
    if args.empty:
        Mail.empty()

    if args.clean:
        clean()
    elif args.echo_token:
        echo_token()
    else:
        mail = Mail()
        mail.connect()
        user: str = getuser()
        cred = keyring.get_credential(APP_NAME, user)
        if cred is None:
            token = auth()
            keyring.set_password(APP_NAME, user, token)
            cred = keyring.get_credential(APP_NAME, user)

        [_, token] = cred.password.split(':')
        start = datetime.now(tz=timezone.utc)
        gh = login(token=token)

        params = {"all": "true"}

        last_run = mail.db.get_last_update()
        if last_run:
            params["since"] = last_run.isoformat()
        print(params)

        url = gh._build_url("notifications")
        for n in gh._iter(
            int(-1), url, notifications.Thread, params, etag=None
        ):
            print(n)
            mail.add_notification(n)
        mail.db.set_last_update(start)


def get_2fa() -> str:
    return getpass('2FA token for {0}: '.format(getuser()))


if __name__ == '__main__':
    main()
