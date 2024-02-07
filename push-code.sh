#!/bin/bash

ALCHEMY_IP=$(./alchemy-ip.sh)

echo $ALCHEMY_IP


# Rsync command to sync files
rsync -razv --progress ./*.py matt@$ALCHEMY_IP:/media/audioalchemy

echo "Rsync operation completed."
