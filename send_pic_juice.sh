#!/bin/bash

#ffmpeg -hide_banner -f v4l2 -list_formats all -i /dev/video0
#v4l2-ctl --all
#v4l2-ctl --list-devices
#v4l2-ctl --list-ctrls
#v4l2-ctl --set-ctrl=gain=00
#v4l2-ctl --set-ctrl=exposure_auto=1
#v4l2-ctl --set-ctrl=exposure_absolute=10

# fswebcam --list-controls to get all setable params

echo "BASH send picture"

d=$(date)
tag=$(date +"%Y-%m-%d_%H%M")
file="J_"$tag.jpg
temp="/home/pi/ramdisk"
echo "filename" $file

echo "take pic"
# horizontal flip.  view upside down to have witty on top 
#raspistill -vf  -w 640 -h 480 -o $temp/$file
# 1280 720  320x240 640x480  480x360


# endoscope
# brigthness 0 255
# contrast, saturation 0 127  100 78%
# sharpness 0 15   14 93%

# microscope
# brigthness 0 96
# contrast 0 64
# saturation 0 128


# logitech 720p
# brigthness 0 255 70
# contrast 0 255 60
# saturation 0 255 100
# sharpness 0 255 24

#fswebcam -S 3 -D 1 -s brigthness=30 -s contrast=50 -s saturation=80 -r 1280x720 $temp/$file
#fswebcam -S 3 -D 1 -r 320x240 $temp/$file
#fswebcam -S 3 -D 1 -r 640x480 $temp/$file
fswebcam -S 3 -D 1 -r 1280x720 $temp/$file
#fswebcam -S 3 -D 1 -s sharpness=14  -s contrast=100 -s saturation=70 -r 640x480 $temp/$file
#fswebcam -S 3 -D 1 -s brightness=70  -s contrast=60 -s saturation=100 -r 640x480 $temp/$file


retry=1
# first try count 1 , exit
echo "number of retry " $retry

cd $temp
count=1

ssid=`/sbin/iwgetid -r`
echo $ssid

echo "trying scp for first time"

# wildcard in double brakets
# space after [[
if [[ $ssid == Apple* ]];  then
echo "from rudlap"
scp $file root@dnsname:/var/www/meaudre 
else
echo "NOT from rudla"
scp $file root@192.168.1.206:/var/www/meaudre 
fi

while [ $? -ne 0 ]; do
echo "scp failed"
echo "count,  retry " $count $retry

# count 10 high. each timeout
  if [ "$count" -gt $retry ]; then
    echo "======== BASH too many scp retries , exit 1"
    exit 1
  fi

  echo "retrying scp after sleep"
  sleep 2
  count=$((count+1))

	# retry
	if [[ $ssid == Apple* ]];  then
	echo "retry from rudlap"
	scp $file root@dnsname:/var/www/meaudre 
	else
	echo "retry NOT from rudla"
	scp $file root@192.168.1.206:/var/www/meaudre 
	fi
done
echo 'bash, exit'
exit 0
