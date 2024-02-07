#!/bin/bash

ALCHEMY_IP=$(./alchemy-ip.sh)

echo "Connecting to $ALCHEMY_IP"


# Rsync command to sync files
rsync --ignore-existing --delete -razv --progress ./library matt@$ALCHEMY_IP:/media/audioalchemy

echo "Rsync operation completed."
