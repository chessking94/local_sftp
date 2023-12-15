from collections import defaultdict
import csv
import datetime as dt
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import traceback

import requests


def get_config(key):
    filename = os.path.join(Path(__file__).parents[1], 'config.json')
    with open(filename, 'r') as t:
        key_data = json.load(t)
    val = key_data.get(key)
    return val


def log_exception(exctype, value, tb):
    write_val = {
        'type': re.sub(r'<|>', '', str(exctype)),  # remove < and > since it messes up converting to HTML for potential email notifications
        'description': str(value),
        'traceback': str(traceback.format_tb(tb, 10))
    }
    logging.critical(str(write_val))


def get_last_reviewed_timestamp(last_reviewed_filename, ftp_user, date_format):
    # convert csv to a possibly nested dictionary where the first column is the key
    nested_dict = defaultdict(dict)
    key_set = set()

    if os.path.isfile(last_reviewed_filename):
        with open(last_reviewed_filename, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=',', quoting=csv.QUOTE_ALL)
            headers = next(reader)  # Read the header row

            for row in reader:
                key = row[0]  # Use the first column as the key
                if key in key_set:
                    raise ValueError(f"duplicate key '{key}' present")
                key_set.add(key)

                inner_dict = {header: value for header, value in zip(headers[1:], row[1:])}
                nested_dict[key] = inner_dict

    user_info = nested_dict.get(ftp_user)
    date_val = user_info.get('Last_Reviewed_Timestamp')
    if date_val is None:
        archive_days = get_config('archiveAfterDays')
        date_val = dt.datetime.now() - dt.timedelta(days=archive_days)  # default to number of days files can live on SFTP
    else:
        date_val = dt.datetime.strptime(date_val, date_format)

    return date_val


def main():
    script_name = Path(__file__).stem
    log_root = get_config('logRoot')

    dte = dt.datetime.now().strftime('%Y%m%d%H%M%S')
    log_name = f'{script_name}_{dte}.log'
    log_file = os.path.join(log_root, log_name)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s\t%(funcName)s\t%(levelname)s\t%(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    sys.excepthook = log_exception  # force unhandled exceptions to write to the log file

    ftp_root = get_config('rootDir')
    exclude_dirs = get_config('skipDirs')
    dir_list = [f for f in os.listdir(ftp_root) if os.path.isdir(os.path.join(ftp_root, f)) and f not in exclude_dirs]
    last_reviewed_filename = os.path.join(Path(__file__).parents[1], get_config('userLastReviewedName'))
    incoming_name = get_config('incomingDir')
    outgoing_name = get_config('outgoingDir')
    tg_api_key = get_config('telegramAPIKey')
    tg_id = get_config('telegramID')
    archive_days = get_config('archiveAfterDays')
    date_format = '%m/%d/%Y %H:%M'

    # create temp file; this will be a two column csv with the SFTP username and when the directory was last checked for files
    temp_file = tempfile.NamedTemporaryFile(delete=False).name
    with open(temp_file, mode='w', newline='', encoding='utf-8') as lr:
        lr.write('"SFTP_User","Last_Reviewed_Timestamp"\n')

    for ftp_user in dir_list:
        user_dir = os.path.join(ftp_root, ftp_user)
        last_reviewed = get_last_reviewed_timestamp(last_reviewed_filename, ftp_user, date_format)

        # incoming files to the SFTP server
        incoming_dir = os.path.join(user_dir, incoming_name)
        incoming_files = [
            f for f in os.listdir(incoming_dir)
            if os.path.isfile(os.path.join(incoming_dir, f))
            and dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(incoming_dir, f))) > last_reviewed
        ]
        incoming_file_ct = len(incoming_files)
        if incoming_file_ct > 0:
            msg = f'A total of {incoming_file_ct} new file(s) have been uploaded to the HuntHome SFTP by user {ftp_user}'
            url = f'https://api.telegram.org/bot{tg_api_key}'
            params = {'chat_id': tg_id, 'text': msg}
            with requests.post(url + '/sendMessage', params=params) as resp:
                cde = resp.status_code
                if cde == 200:
                    for f in incoming_files:
                        logging.info(f'{incoming_name}|{ftp_user}|{f}')
                else:
                    logging.error(f'Incoming File Telegram Notification Failed: Response Code {cde}')

        # outgoing files to the SFTP server
        outgoing_dir = os.path.join(user_dir, outgoing_name)
        outgoing_files = [
            f for f in os.listdir(outgoing_dir)
            if os.path.isfile(os.path.join(outgoing_dir, f))
            and dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(outgoing_dir, f))) > last_reviewed
        ]
        outgoing_file_ct = len(outgoing_files)
        if outgoing_file_ct > 0:
            send_outgoing_tg = False
            if send_outgoing_tg:
                msg = f'A total of {outgoing_file_ct} new file(s) are available for download on the HuntHome SFTP and will accessible for {archive_days} days'
                url = f'https://api.telegram.org/bot{tg_api_key}'
                params = {'chat_id': '', 'text': msg}  # TODO: End user would need to provide their own Telegram chat_id and it gets logged somewher
                with requests.post(url + '/sendMessage', params=params) as resp:
                    cde = resp.status_code
                    if cde == 200:
                        for f in outgoing_files:
                            logging.info(f'{outgoing_name}|{ftp_user}|{f}')
                    else:
                        logging.error(f'Outgoing File Telegram Notification Failed: Response Code {cde}')
            else:
                for f in outgoing_files:
                    logging.info(f'{outgoing_name}|{ftp_user}|{f}')

        # update temp file
        with open(temp_file, mode='a', newline='', encoding='utf-8') as lr:
            lr.write(f'"{ftp_user}","{dt.datetime.strftime(last_reviewed, date_format)}"\n')

    # replace original user_last_reviewed.csv with temp file
    shutil.move(temp_file, last_reviewed_filename)


if __name__ == '__main__':
    main()
