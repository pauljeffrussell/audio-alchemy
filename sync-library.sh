#!/bin/bash

ALCHEMY_IP=$(./alchemy-ip.sh)

echo "Connecting to $ALCHEMY_IP"


# Rsync command to sync files
rsync --ignore-existing  --force --delete --delete-excluded -razv  --progress ./library/ matt@$ALCHEMY_IP:/media/audioalchemy/library/

echo "Rsync operation completed."
