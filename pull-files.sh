#!/bin/bash

# Here's the 
AA_IP=$(./alchemy-ip.sh)

echo "Connecting to $AA_IP"



#rsync --ignore-existing --dry-run -razv --progress matt@$AA_IP:/media/audioalchemy/logs ./logs
# get the error file
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/logs/* ./logs
echo "Logs copied to local ./logs"


# get the DB-cache
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/dbcache/* ./dbcache
echo "DB cache copied to local ./dbcache"



# get the scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/ckp ./scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/connect ./scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/go ./scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/pss ./scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/sdown ./scripts
rsync -razv --progress matt@$AA_IP:/media/audioalchemy/startAudioAlchemy ./scripts
echo "Scritps copied, one at a time, to local ./scripts"
echo
echo
echo
echo
echo
echo "#############################################"
echo "##                                         ##"
echo "##          Collection Complete            ##"
echo "##                                         ##"
echo "#############################################"
echo
echo
echo "Logs copied to local ./logs"
echo "DB cache copied to local ./dbcache"
echo "Scritps (ckp, connect, go, pss, sdown, startAudioAlchemy) copied to local ./scripts"
echo
echo "File collection from $AA_IP completed."
echo
