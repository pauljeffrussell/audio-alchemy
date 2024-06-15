#!/bin/bash

# Check if a command line argument is provided
if [ "$1" != "3" ] && [ "$1" != "4" ]; then
  echo "Device ID Required."
  exit 1
fi

# Return the appropriate IP based on the provided argument
if [ "$1" == "3" ]; then
  # Return alternate IP if '3' is provided
  #echo "192.168.4.21"
  echo "192.168.1.97"
else
  # Return default IP if '4' is provided
  echo "192.168.4.147"
fi
