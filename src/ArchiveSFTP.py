import os
from pathlib import Path
import subprocess

from Utilities_Python import misc

CONFIG_FILE = os.path.join(Path(__file__).parents[1], 'config.json')


def main():
    script_name = Path(__file__).stem
    _ = misc.initiate_logging(script_name, CONFIG_FILE)

    ftp_root = misc.get_config('rootDir', CONFIG_FILE)
    ftp_archive_root = misc.get_config('archiveRootDir', CONFIG_FILE)
    exclude_dirs = misc.get_config('skipDirs', CONFIG_FILE)
    archive_days = misc.get_config('archiveAfterDays', CONFIG_FILE)
    dir_list = [f for f in os.listdir(ftp_root) if os.path.isdir(os.path.join(ftp_root, f)) and f not in exclude_dirs]

    for ftp_user in dir_list:
        user_dir = os.path.join(ftp_root, ftp_user)
        archive_user_dir = os.path.join(ftp_archive_root, ftp_user)
        robo_cmd = f'robocopy {user_dir} {archive_user_dir} /A-:SH /E /MOV /MINAGE:{archive_days}'

        _ = subprocess.run(robo_cmd, shell=True, capture_output=True, text=True)


if __name__ == '__main__':
    main()
