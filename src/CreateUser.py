import logging
import os
from pathlib import Path
import warnings

from Utilities_Python import misc
import pandas as pd
import sqlalchemy as sa

CONFIG_FILE = os.path.join(Path(__file__).parents[1], 'config.json')


def list_logintypes(engine):
    logintype_ids = []
    prompt = 'Please choose a LoginTypeID. Accepted values are:'
    qry = "SELECT LoginTypeID, LoginType FROM sftp.LoginTypes ORDER BY LoginTypeID"
    logging.debug(qry)
    df = pd.read_sql(qry, engine)
    for _, data in df.iterrows():
        prompt = f"{prompt}\n{data['LoginTypeID']} ({data['LoginType']})"
        logintype_ids.append(str(data['LoginTypeID']))

    prompt = f'{prompt}\nYour choice: '
    user_input = ''
    while True:
        user_input = input(prompt)
        if user_input not in logintype_ids:
            print(f"The value '{user_input}' is invalid, please try again")
        else:
            break

    return user_input


def insert_user(engine, username, firstname, lastname, logintypid, telegramchatid):
    result_msg = None

    # verify 'username' doesn't already exist
    qry = f"SELECT COUNT(Username) FROM sftp.Logins WHERE Username = '{username}'"
    logging.debug(qry)
    user_ct = pd.read_sql(qry, engine).values[0][0]
    if user_ct != 0:
        result_msg = f"Username '{username}' already exists"

    if result_msg is None:
        home_dir = f"{misc.get_config('rootDir', CONFIG_FILE)}/{username}"
        telegramchatid = f"'{telegramchatid}'" if telegramchatid != '' else 'NULL'  # convert blank telegramchatid's to null

        # do the insert
        insert_qry = 'INSERT INTO sftp.Logins (Username, FirstName, LastName, LoginTypeID, HomeDirectory, TelegramChatID) '
        insert_qry = insert_qry + f"VALUES ('{username}', '{firstname}', '{lastname}', {logintypid}, '{home_dir}', {telegramchatid})"

        conn = engine.connect().connection
        csr = conn.cursor()
        logging.debug(insert_qry)
        csr.execute(insert_qry)
        conn.commit()
        conn.close()
        result_msg = f"User '{username}' added successfully"
        logging.info(result_msg)
    else:
        logging.error(result_msg)


def main():
    script_name = Path(__file__).stem
    _ = misc.initiate_logging(script_name, CONFIG_FILE)

    warnings.simplefilter('ignore')
    conn_str = misc.get_config('connectionString_domainDB', CONFIG_FILE)  # TODO: want to get rid of this but it's on an Ubuntu box...
    connection_url = sa.engine.URL.create(
        drivername='mssql+pyodbc',
        query={'odbc_connect': conn_str}
    )
    engine = sa.create_engine(connection_url)

    username = input('Please enter a username: ')
    firstname = input("Please enter the new user's first name: ")
    lastname = input("Please enter the new user's last name: ")
    logintypeid = list_logintypes(engine)
    telegramchatid = input('If applicable, please enter the Telegram Chat ID provided by the user: ')

    insert_user(engine, username, firstname, lastname, logintypeid, telegramchatid)
    engine.dispose()

    # create root user directory
    user_root = f"{misc.get_config('rootDir', CONFIG_FILE)}/{username}"
    os.mkdir(user_root)

    # incoming directory
    inc_dir_archive = os.path.join(user_root, misc.get_config('incomingDir', CONFIG_FILE), 'Archive')
    os.makedirs(inc_dir_archive)

    # outgoing directory
    out_dir_archive = os.path.join(user_root, misc.get_config('outgoingDir', CONFIG_FILE), 'Archive')
    os.makedirs(out_dir_archive)


if __name__ == '__main__':
    main()
