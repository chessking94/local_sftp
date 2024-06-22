#!/bin/bash

# Function to disable user login
disable_user() {
    local username=$1
    sudo passwd -l "$username"
    echo "User '$username' has been disabled from login."
    python3 SftpUserLinux.py --process "DISABLE" --username "$username"
}

# Function to re-enable user login
enable_user() {
    local username=$1
    sudo passwd -u "$username"
    echo "User '$username' has been re-enabled for login."
    python3 SftpUserLinux.py --process "ENABLE" --username "$username"
}

# Prompt for the username
read -p "Enter the username you want to manage: " username

# Check if the username provided is empty
if [ -z "$username" ]; then
    echo "Username cannot be empty."
    exit 1
fi

# Check if the user exists
if id "$username" &>/dev/null; then
    # Prompt to disable or re-enable the user
    read -p "Do you want to disable or re-enable the user '$username'? (disable/enable): " action

    # ensure PWD is the directory of this file, in case of symlinks
    BASE_FILE="$(readlink -f "$0")"
    SCRIPT_DIR="$(dirname "$BASE_FILE")"
    if [ "$PWD" != "$SCRIPT_DIR" ]; then
        cd "$SCRIPT_DIR"
    fi

    case "$action" in
        "disable")
            disable_user "$username"
            ;;
        "enable")
            enable_user "$username"
            ;;
        *)
            echo "Invalid action. Please choose 'disable' or 'enable'."
            exit 1
            ;;
    esac
else
    echo "User '$username' does not exist."
fi
