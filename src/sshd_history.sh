#!/bin/bash

# Yes, this was written by ChatGPT
LOG_FILE="/var/log/auth.log"
STATE_FILE="/var/log/auth_grep_state"
OUTPUT_DIR="/sftp/eehunt/FromHuntHome"

# Get the current timestamp
HOSTNAME=$(hostname)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${OUTPUT_DIR}/${HOSTNAME}_sshd_grep_${TIMESTAMP}.txt"

# Get the last processed line number from the state file
if [ ! -f "$STATE_FILE" ]; then
    echo "0" > "$STATE_FILE"
fi
LAST_PROCESSED=$(cat "$STATE_FILE")

# Get the current total line count of the log file
CURRENT_LINE_COUNT=$(wc -l < "$LOG_FILE")

# Function to process log file
process_log_file() {
    local file=$1
    local start_line=$2
    sudo tail -n +"$start_line" "$file" | grep sshd >> "$OUTPUT_FILE"
}

# Check if log rotation has occurred
if [ "$CURRENT_LINE_COUNT" -lt "$LAST_PROCESSED" ]; then
    # Process the remaining part of the rotated log files
    for rotated_log in /var/log/auth.log.*.gz; do
        if [ -f "$rotated_log" ]; then
            zcat "$rotated_log" | grep sshd >> "$OUTPUT_FILE"
        fi
    done
    # Reset last processed line number for the new log file
    LAST_PROCESSED=0
fi

# Process the current log file from the last processed line
if [ "$LAST_PROCESSED" -lt "$CURRENT_LINE_COUNT" ]; then
    process_log_file "$LOG_FILE" $((LAST_PROCESSED + 1))
fi

# Update the state file with the new last processed line number
echo "$CURRENT_LINE_COUNT" > "$STATE_FILE"

# Check if the output file is empty and delete it if it is
if [ ! -s "$OUTPUT_FILE" ]; then
    rm "$OUTPUT_FILE"
else
    # Update the permissions of the output file to 666
    chmod 666 "$OUTPUT_FILE"
fi
