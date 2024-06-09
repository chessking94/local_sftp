#!/bin/bash

# Function to check if a user exists
user_exists() {
    id "$1" &>/dev/null
}

# Function to generate a random password
generate_password() {
    < /dev/urandom tr -dc A-Za-z0-9 | head -c8
}

# Check if 'sftp_users' group exists and create new user
if grep -q '^sftp_users:' /etc/group; then
    # Prompt for username
    read -p "Enter username: " username

    # Check if the username provided is empty
    if [ -z "$username" ]; then
        echo "Username cannot be empty."
        exit 1
    fi

    # Check if the username already exists
    if user_exists "$username"; then
        echo "User '$username' already exists."
        exit 1
    else
        # Prompt for first and last names
        read -p "Enter first name: " firstname
        read -p "Enter last name: " lastname
        read -p "Enter Telegram Chat ID: " telegramid

        # Create user and add to 'sftp_users' group
        sudo useradd -m -s /bin/bash -G sftp_users "$username"
        echo "User '$username' created and added to 'sftp_users' group."
		
		# Generate random password
        password=$(generate_password)

        # Set the generated password for the user
        echo "$username:$password" | sudo chpasswd

        echo "Password for '$username' set to: $password"
    fi
else
    echo "Group 'sftp_users' does not exist."
    exit 1
fi

# Check if /sftp directory exists
if [ -d "/sftp" ]; then
    # Create user directory and subdirectories
    sudo mkdir -p "/sftp/$username/ToHuntHome"
    sudo mkdir -p "/sftp/$username/FromHuntHome"
    echo "Directories created for user '$username'."

    # set admin permissions
    sudo chown -R root:ftp_admin "/sftp/$username"
    sudo chmod 775 "/sftp/$username"

    # Set permissions for the directories; this will only allow user to interact with files in the To and From directories
	sudo chmod 777 "/sftp/$username/ToHuntHome"
	sudo chmod 777 "/sftp/$username/FromHuntHome"
    echo "Permissions set for directories."
else
    echo "/sftp directory does not exist."
    exit 1
fi

# Restart SSH service
sudo service ssh restart
echo "SSH service restarted."

python3 SftpUserLinux.py --process "CREATE" --username "$username" --firstname "$firstname" --lastname "$lastname" --telegramid "$telegramid"
