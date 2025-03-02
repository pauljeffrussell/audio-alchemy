#!/bin/bash

# Default values
RSYNC_USER="paul"
RSYNC_DEST="/mnt/audioalchemy"
ALCHEMY_IP_SCRIPT="./alchemy-ip.sh"

# Set argument to '4' if no argument is provided
ARG="${1:-4}"

# Check if the argument is '3'
if [ "$ARG" == "3" ]; then
  # Use alternate values if '3' is provided
  RSYNC_USER="matt"
  RSYNC_DEST="/media/audioalchemy"
fi

# Call alchemy-ip.sh with the argument
ALCHEMY_IP=$($ALCHEMY_IP_SCRIPT $ARG)

echo $ALCHEMY_IP

# Rsync command to sync files
#rsync -razv --progress ./streamer.py $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST
rsync -razv --progress ./*.py $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST
#rsync -razv --progress ./aotd_send_now $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST



#rsync -razv --progress ./*.py $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST

#rsync -razv --progress ./html/* $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST/html
#rsync -razv --progress ./*.txt $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST
#rsync -razv --progress ./keys $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST
#rsync -razv --progress ./scripts/* $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST
#rsync -razv --progress ./dbcache/aotdcache.csv $RSYNC_USER@$ALCHEMY_IP:$RSYNC_DEST

echo "Rsync operation completed."
