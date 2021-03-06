#!/usr/bin/env bash

xhost local:autoware

docker run -it --runtime=nvidia \
-e DISPLAY=$DISPLAY \
-u mad-autoware \
-v /tmp/.X11-unix/:/tmp/.X11-unix/ \
-v /run/udev/:/run/udev/ \
-v /home/kuriatsu/Program/Docker/autoware-16.04-1.12.0:/home/mad-autoware/sharedFiles \
-v /media/kuriatsu/SamsungKURI1/:/media/ssd/ \
--hostname="autoware" \
mad/autoware:16.04-1.12.0
