import argparse
import json
import os
from pathlib import Path

import pyodbc

CONFIG_FILE = os.path.join(Path(__file__).parents[1], 'config.json')
PROCESS_TYPES = ['CREATE', 'DELETE', 'ENABLE', 'DISABLE']


class sftp:
    def __init__(self, args):
        with open(CONFIG_FILE, 'r') as cf:
            key_data = json.load(cf)
            self.conn_str = key_data.get('connectionString_domainDB')
            self.root_dir = key_data.get('rootDir')

        self.processtype = args['process']
        self.username = args['username']
        self.firstname = None if args['firstname'] == '' else args['firstname']
        self.lastname = None if args['lastname'] == '' else args['lastname']
        self.logintypid = 1  # hard-coding password for now, can enhance to include public key later
        self.home_dir = os.path.join(self.root_dir, self.username).replace('\\', '/')  # always want *nix paths
        self.telegramid = None if args['telegramid'] == '' else args['telegramid']

        self.conn = pyodbc.connect(self.conn_str)
        self.cursor = self.conn.cursor()

        self.query = None
        self.params = None

        match self.processtype:
            case 'CREATE':
                self.__create()
            case 'DELETE':
                self.__delete()
            case 'ENABLE':
                self.__toggle_user(True)
            case 'DISABLE':
                self.__toggle_user(False)
            case _:
                raise NotImplementedError(f"invalid process type '{self.processtype}'")

        self.cursor.execute(self.query, self.params)
        self.cursor.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.conn:
            self.conn.close()

    def __create(self):
        self.params = [self.username, self.firstname, self.lastname, self.logintypid, self.home_dir, self.telegramid]
        self.query = 'INSERT INTO sftp.Logins (Username, FirstName, LastName, LoginTypeID, HomeDirectory, TelegramChatID) VALUES (?, ?, ?, ?, ?, ?)'

    def __delete(self):
        self.params = [self.username]
        self.query = 'DELETE FROM sftp.Logins WHERE Username = ?'

    def __toggle_user(self, active: bool):
        if isinstance(active, bool):
            active_bit = 1 if active else 0
        else:
            active_bit = 1

        self.params = [active_bit, self.username]
        self.query = 'UPDATE sftp.Logins SET Active = ? WHERE Username = ?'


def main():
    vrs_num = '1.0'
    parser = argparse.ArgumentParser(
        description='SFTP User Modification',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=argparse.SUPPRESS
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s ' + vrs_num
    )
    parser.add_argument(
        '-p', '--process',
        choices=PROCESS_TYPES,
        help='Process Type'
    )
    parser.add_argument(
        '-u', '--username',
        help='User name'
    )
    parser.add_argument(
        '-f', '--firstname',
        default=None,
        nargs='?',
        help='First name of user'
    )
    parser.add_argument(
        '-l', '--lastname',
        default=None,
        nargs='?',
        help='Last name of user'
    )
    parser.add_argument(
        '-t', '--telegramid',
        default=None,
        nargs='?',
        help='Telegram chat ID of user'
    )
    args = parser.parse_args()
    config = vars(args)

    proc = sftp(config)
    proc.close()


if __name__ == '__main__':
    main()
