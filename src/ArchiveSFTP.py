import datetime as dt
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback


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
    ftp_archive_root = get_config('archiveRootDir')
    exclude_dirs = get_config('skipDirs')
    archive_days = get_config('archiveAfterDays')
    dir_list = [f for f in os.listdir(ftp_root) if os.path.isdir(os.path.join(ftp_root, f)) and f not in exclude_dirs]

    for ftp_user in dir_list:
        user_dir = os.path.join(ftp_root, ftp_user)
        archive_user_dir = os.path.join(ftp_archive_root, ftp_user)
        robo_cmd = f'robocopy {user_dir} {archive_user_dir} /A-:SH /E /MOV /MINAGE:{archive_days}'

        _ = subprocess.run(robo_cmd, shell=True, capture_output=True, text=True)


if __name__ == '__main__':
    main()
