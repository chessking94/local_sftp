import datetime as dt
import logging
import os
from pathlib import Path

import pandas as pd
import requests
import sqlalchemy as sa
from Utilities_Python import misc, notifications

CONFIG_FILE = os.path.join(Path(__file__).parents[1], 'config.json')


def get_last_reviewed_timestamp(engine, ftp_user):
    date_val = None
    qry = f"SELECT Active, LastMonitored FROM HuntHome.sftp.Logins WHERE Username = '{ftp_user}'"
    logging.debug(qry)
    df = pd.read_sql(qry, engine)
    if len(df) == 0:
        logging.critical(f"unable to locate sftp.Logins record for login '{ftp_user}'")
    else:
        if df.values[0][0]:
            dte = df.values[0][1]
            date_val = pd.to_datetime(dte).to_pydatetime()

    return date_val


def set_last_reviewed_timestamp(engine, ftp_user, dte):
    dtefmt = dte.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    conn = engine.connect().connection
    csr = conn.cursor()
    insert_qry = f"UPDATE HuntHome.sftp.Logins SET LastMonitored = '{dtefmt}' WHERE Username = '{ftp_user}'"
    logging.debug(insert_qry)
    csr.execute(insert_qry)
    conn.commit()
    conn.close()


def insert_sftpfiles(engine, username, directory, filename):
    directory = directory.replace('\\', '/')  # ensure there's no Windows path separators, only *nix
    id_qry = f"SELECT DirectoryID FROM HuntHome.sftp.Directories WHERE DirectoryPath = '/{directory}'"
    logging.debug(id_qry)
    df = pd.read_sql(id_qry, engine)
    idval = None
    if len(df) == 0:
        logging.critical(f"unable to locate sftp.Directories record for directory '{directory}'")
    else:
        idval = int(df.values[0][0])

    if idval is not None:
        conn = engine.connect().connection
        csr = conn.cursor()
        insert_qry = f"INSERT INTO HuntHome.sftp.Files (Username, DirectoryID, Filename) VALUES ('{username}', '{idval}', '{filename}')"
        logging.debug(insert_qry)
        csr.execute(insert_qry)
        conn.commit()
        conn.close()

        logging.debug(f'{username}|{directory}|{filename}')


def get_telegramid(engine, username):
    id_qry = f"SELECT TelegramChatID FROM HuntHome.sftp.Logins WHERE Username = '{username}'"
    logging.debug(id_qry)
    df = pd.read_sql(id_qry, engine)
    rtn = None
    if len(df) == 0:
        logging.critical(f"unable to locate sftp.Logins record for username '{username}'")
    else:
        rtn = df.values[0][0]

    return rtn


def main():
    script_name = Path(__file__).stem
    _ = misc.initiate_logging(script_name, CONFIG_FILE)

    ftp_root = misc.get_config('rootDir', CONFIG_FILE)
    exclude_dirs = misc.get_config('skipDirs', CONFIG_FILE)
    dir_list = [f for f in os.listdir(ftp_root) if os.path.isdir(os.path.join(ftp_root, f)) and f not in exclude_dirs]
    incoming_name = misc.get_config('incomingDir', CONFIG_FILE)
    outgoing_name = misc.get_config('outgoingDir', CONFIG_FILE)
    archive_days = misc.get_config('archiveAfterDays', CONFIG_FILE)

    conn_str = os.getenv('ConnectionStringOdbcRelease')
    connection_url = sa.engine.URL.create(
        drivername='mssql+pyodbc',
        query={'odbc_connect': conn_str}
    )
    engine = sa.create_engine(connection_url)

    for ftp_user in dir_list:
        user_dir = os.path.join(ftp_root, ftp_user)
        last_reviewed = get_last_reviewed_timestamp(engine, ftp_user)
        if last_reviewed is None:
            pass  # user is inactive, do not need to check
        else:
            new_reviewed = dt.datetime.now()

            # incoming files to the SFTP server
            incoming_dir = os.path.join(user_dir, incoming_name)
            incoming_files = [
                f for f in os.listdir(incoming_dir)
                if os.path.isfile(os.path.join(incoming_dir, f))
                and dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(incoming_dir, f))) > last_reviewed
            ]
            incoming_file_ct = len(incoming_files)
            if incoming_file_ct > 0:
                for f in incoming_files:
                    insert_sftpfiles(engine=engine, username=ftp_user, directory=incoming_name, filename=f)

                msg = f'New SFTP Files: A total of {incoming_file_ct} new file(s) have been uploaded to the HuntHome SFTP by user {ftp_user}'
                notifications.SendTelegramMessage(msg)

            # outgoing files to the SFTP server
            outgoing_dir = os.path.join(user_dir, outgoing_name)
            outgoing_files = [
                f for f in os.listdir(outgoing_dir)
                if os.path.isfile(os.path.join(outgoing_dir, f))
                and dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(outgoing_dir, f))) > last_reviewed
            ]
            outgoing_file_ct = len(outgoing_files)
            if outgoing_file_ct > 0:
                for f in outgoing_files:
                    insert_sftpfiles(engine=engine, username=ftp_user, directory=outgoing_name, filename=f)

                user_chat_id = get_telegramid(engine=engine, username=ftp_user)
                if user_chat_id is not None:
                    tg_api_key = os.getenv('TelegramAPIKeyRelease')
                    if tg_api_key is None:
                        logging.error('Missing TelegramAPIKey environment variable')
                    else:
                        # TODO: replace this with something in Utilities when it is built out
                        msg = f'SFTP Files: A total of {outgoing_file_ct} new file(s) are available for download on the HuntHome SFTP and will accessible for {archive_days} days'
                        url = f'https://api.telegram.org/bot{tg_api_key}'
                        params = {'chat_id': user_chat_id, 'text': msg}
                        with requests.post(url + '/sendMessage', params=params) as resp:
                            cde = resp.status_code
                            if cde != 200:
                                logging.error(f'Outgoing File Telegram Notification Failed: Response Code {cde}')

            # update database
            set_last_reviewed_timestamp(engine, ftp_user, new_reviewed)

    engine.dispose()


if __name__ == '__main__':
    main()
