#!/bin/bash

# Default values
RSYNC_USER="paul"
ALCHEMY_IP_SCRIPT="./alchemy-ip.sh"

# Set argument to '4' if no argument is provided
ARG="${1:-4}"

# Check if the argument is '3'
if [ "$ARG" == "3" ]; then
  # Use alternate user if '3' is provided
  RSYNC_USER="matt"
fi

# Call alchemy-ip.sh with the argument
ALCHEMY_IP=$($ALCHEMY_IP_SCRIPT $ARG)

if [ $? -ne 0 ]; then
  echo "Failed to retrieve IP address using $ALCHEMY_IP_SCRIPT with argument $ARG."
  exit 1
fi

echo "ssh to $ALCHEMY_IP"

# SSH command
ssh $RSYNC_USER@$ALCHEMY_IP

#echo "SSH operation completed."
