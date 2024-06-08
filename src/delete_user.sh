#!/bin/bash

# Prompt for the username
read -p "Enter the username you want to delete: " username

# Check if the username provided is empty
if [ -z "$username" ]; then
    echo "Username cannot be empty."
    exit 1
fi

# Check if the user exists
if id "$username" &>/dev/null; then
    # Delete the directory tree if it exists
    if [ -d "/sftp/$username" ]; then
        sudo rm -rf "/sftp/$username"
        echo "Directory tree '/sftp/$username' has been deleted."
    else
        echo "Directory tree '/sftp/$username' does not exist."
    fi

    # Delete the user; for some reason the second command is needed to clear the mail spool
    sudo deluser -r --remove-home "$username"
	sudo deluser -r "$username"
    echo "User '$username' has been deleted."

    python3 SftpUserLinux.py --process "DELETE" --username "$username"
else
    echo "User '$username' does not exist."
fi
