#!/bin/bash

# 16 jan 2019  dual location, add domoticz password 
# 22 sept 2024. S
# 23 sept 2024. $2 used to configure save locally. if true save all pic, else only if scp fails

########################
# send pic using bash script
# params: unique file name, 0/1 to save locally, dir to save locally

# return 1 if scp fails (after retries)
# return 0 if scp ok
# called as:  /home/pi/beecamjuice/send_pic_juice.sh  9_22_12_19.jpg
########################

#ffmpeg -hide_banner -f v4l2 -list_formats all -i /dev/video0


# NOTE v4 elle 2

#v4l2-ctl --all
#   lof of info , including resolution, User Controls (ie settable parameters)


#v4l2-ctl --list-devices
# USB camera (usb-20980000.usb-1):
#        /dev/video0


#v4l2-ctl --list-ctrls
#User Controls
#
#                     brightness (int)    : min=0 max=255 step=1 default=128 value=128 flags=slider
#                       contrast (int)    : min=0 max=127 step=1 default=20 value=20 flags=slider
#                     saturation (int)    : min=0 max=40 step=1 default=25 value=25 flags=slider
#                    red_balance (int)    : min=24 max=40 step=1 default=32 value=32 flags=slider
#                   blue_balance (int)    : min=24 max=40 step=1 default=32 value=32 flags=slider
#                          gamma (int)    : min=0 max=40 step=1 default=20 value=20 flags=slider
#                 gain_automatic (bool)   : default=1 value=1
#                      sharpness (int)    : min=0 max=255 step=1 default=90 value=90 flags=slider


#v4l2-ctl --set-ctrl=gain=00
#v4l2-ctl --set-ctrl=exposure_auto=1


# fswebcam --list-controls
# to get all setable params, same info as --list-controls 


echo "BASH send picture"


echo "params:"
echo $1
echo $2
echo $3


# python pass str(bool) to make sure
# echo WTF, print either True or 0
# anyway, assumes $2 is a str and test againts "True"
#params:
#9_23_8_28.jpg
#True or 0
#local_pic

# log failed scp
scp_fails="/home/pi/beecamjuice/logs/scp_fails.log"

# even if filename passed as $1, filename created here. I do not remember why 
d=$(date)
tag=$(date +"%Y-%m-%d_%H%M")

file="J_"$tag.jpg
temp="/home/pi/ramdisk"

echo "pic file stored locally as:" $file $temp
echo "take pic"

##############
# resolution
##############
# see v4l2-ctl --all for capabilities
# 1280x720  320x240 640x480  480x360

# fish eye:
#Driver Info (not using libv4l2):
#        Driver name   : uvcvideo
#        Card type     : USB 2.0 PC Camera: PC Camera
# Width/Height      : 640/480


# cam 2024: 
#Driver Info (not using libv4l2):
#        Driver name   : uvcvideo
#        Card type     : FHD Camera: FHD Camera
# Width/Height      : 1920/1080

##################
##################
# need mmal. use fswebcal rather
#raspistill -vf  -w 640 -h 480 -o $temp/$file
##################

###############
# fswebcam
###############
# https://manpages.ubuntu.com/manpages/bionic/man1/fswebcam.1.html

#fswebcam -S 3 -D 1 -s brigthness=30 -s contrast=50 -s saturation=80 -r 1280x720 $temp/$file

# S skip 3 frame, F capture 5 frame (less noise, but blur) , D delay 1sec
# MAKE SURE camera support resolution
# -p palette
# --flip v

fswebcam -S 3 -D 1 -F 2 -p MJPEG --flip v --title "PIJuice" --subtitle "meaudre" --info "Pabou"  -r 1920x1080 $temp/$file

# save pic in ftp. deprecated
#wput  $temp/$file ftp://pascal.boudal:zero00@ftpperso.free.fr/meaudre/$file


# send temp to domoticz. deprecated
# echo "send temp"
# DOMOTICZ w/ password
#/usr/bin/curl -s "paboupicloud.zapto.org:13880/json.htm?username=bWVhdWRyZQ==&password=YXV0cmFucw==&type=command&param=udevice&idx=54&nvalue=0&svalue=$a" ;



######################
# save pic locally to persistent file system (vs ramdisk)
######################

# beware file system full, use with care
# run cp as background, to avoid this script from failing if file system full
# $3 is name of directory

if [ "$2" == "True" ]; then 
 echo "saving ALL picture locally" $temp/$file  $3/$file
 cp $temp/$file  $3/$file & 
else
 echo "NOT saving ALL pic locally. only if scp fails" 
fi


######################
# send pic to web server using scp (beware of keys)
######################

# nb of retry
retry=2
# nb of attemps
count=1

# first try count 1 , exit
echo "number of retry " $retry

cd $temp

# get ssid to see if local or remote
ssid=`/sbin/iwgetid -r`
echo $ssid

echo "trying scp for first time"

# wildcard in double brakets
# space after [[

#if [[ $ssid == Apple* ]];  then
if [[ $ssid == Freebox* ]];  then
 echo "from rudlap ; immeuble en S. use dns"
 scp $file root@paboupicloud.zapto.org:/var/www/meaudre

else
 echo "NOT from rudla; immeuble en S. use local IP"
 scp $file root@192.168.1.206:/var/www/meaudre 
fi

# test if scp OK
while [ $? -ne 0 ]; do
 echo "scp failed" "count" $count "retries" $retry

# log fails to file 
 echo $(date) "scp failed" "count" $count "retries" $retry >> $scp_fails
 

# count 10 high. each timeout
  if [ "$count" -gt $retry ]; then
    echo "======== BASH too many failed scp retries , exit 1"
    # save pic locally 
    echo "saving picture locally" $temp/$file  $3/$file
    echo $(date) "failed scp. saving picture locally" $temp/$file  $3/$file >> $scp_fails

    # the cp will fail if usb cam is disconnected, as the file in ramdisk does not exist. 
    cp $temp/$file  $3/$file & 

    exit 1
  fi

  echo "retrying scp after sleep"
  sleep 2
  count=$((count+1))

	# retry
#	if [[ $ssid == Apple* ]];  then
	if [[ $ssid == Freebox* ]];  then
	echo "retry from rudlap; immeuble en S"
	scp $file root@paboupicloud.zapto.org:/var/www/meaudre 
	else
	echo "retry NOT from rudla; immeuble en S"
	scp $file root@192.168.1.206:/var/www/meaudre 
	fi
done

# end while. if there, scp is OK


echo 'bash, exit 0'
exit 0
