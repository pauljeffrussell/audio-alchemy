#!/bin/bash

ALCHEMY_IP=$(./alchemy-ip.sh)

echo ssh to $ALCHEMY_IP


# Rsync command to sync files
ssh matt@$ALCHEMY_IP

#echo "Rsync operation completed."
