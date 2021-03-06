#!/usr/bin/python3

# run time halt 20,24 sec

# PiJuice sw 1.4 is installed for Python 3
# sudo find / -name "pijuice.py"   /usr/lib/python3.5/dist-packages/pijuice.py

#https://feeding.cloud.geek.nz/posts/time-synchronization-with-ntp-and-systemd/

# on systemd apt-get purge ntp to use only systemd-timesyncd.service 
# edit /etc/systemd/timesyncd.conf
# systemctl restart systemd-timesyncd.service  


# timedatectl status
#to enable NTP synchronized
# timedatectl set-ntp true

#The system is configured to read the RTC time in the local time zone.
#This mode can not be fully supported. It will create various problems
#with time zone changes and daylight saving time adjustments. The RTC
#time is never updated, it relies on external facilities to maintain it.
#If at all possible, use RTC in UTC by calling
#'timedatectl set-local-rtc 0'.

# timedatectl set-local-rtc 0

# to set date
#sudo date -s 16:31

# read hwclock
# sudo hwclock -r

# set hwclock with system time 
# sudo hwclock -w --systohc  same time, not utc vs local

# set hwclock with date
# sudo hwclock --set --date --localtime "1/4/2013 23:10:45" 4 jan

#set system time from hwclock
# sudo hwclock -s --hctosys

# use --debug
# use --utc or --localtime when setting hwclock



"""
# juice internal led 2
juice ok. blink blue 2x. else solid red
ntp ok. blink green 1x, 100ms, intensity 50 . else use hwclock blink red 
pic sent. blink green 2x, 100ms, intensity 200 else fails blink red . else nigth blink blue 
halt. blink blue 2x. else stay on blink red 2x
"""


# After the initial set of system time using the Linux date command  and the copy to PiJuice RTC sudo hwclock -w, you simply just need to run at system startup do a 'sudo hwclock -s' to copy the time from the RTC to the system clock e.g. in /etc/rc.local. This is also assuming that your ID EEPROM is set to 0x50 in which case the RTC driver is loaded at boot. 
# lsmod to check module  Force loading the module by adding the following line to /boot/config.txt:
# dtoverlay=i2c-rtc,ds1339
# i2cdetect must shows UU instead of 68 https://github.com/PiSupply/PiJuice/issues/186
 
# hwclock -r read hwckock to stdout  -w date to hw  -s hw to date
#sudo ntpd -gq force ntp update

from __future__ import print_function
import RPi.GPIO as GPIO
import os
import time

# python2
#import httplib, urllib

import http.client, urllib

import datetime

# python 2
#import thread
import _thread

#https://github.com/vshymanskyy/blynk-library-python
#pip install blynk-library-python
import BlynkLib

# sudo apt-get install ntp
#  systemctl
# sudo apt-get install ntpdate (client)

#pip install ntplib
import ntplib



#sudo pip install thingspeak
#https://thingspeak.readthedocs.io/en/latest/


import thingspeak 

import pijuice
import subprocess
import sys
import logging
import subprocess

print('juice camera v2.1')


# wakeup every x mn
DELTA_MIN=20 # mn

limit_soc=15 # limit send pushover .  a bit higher than the HALT_POWER_OFF in juice config
#Low values should be typically between 5-10%
# in juice config, minimum charge is 10%, min voltage 3.2V. wakeup on charge 70%
print ('send pushover when soc is below %d' %(limit_soc))

pin_halt=26
pin_led=16 # not used anymore

# Blynk Terminal V8, button V18
bbutton=18 # halt or tun
bterminal=8

bsoc=20
bsleep=21 #programmable sleep time
btemp=22 # of bat
bvbat=23 # of pijuice
bcount=24 # increment at each run

# use external led
led = False

#button value 2 un-initialized
button="2"
# THIS IS A string

count = 0
sleep_time=60

print ("STARTING. set system time from hwclock: ")
subprocess.call(["sudo", "hwclock", "--hctosys"])
# --systohc to set hwclock

# to measure execution time
start_time=datetime.datetime.now()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_led,GPIO.OUT) # external led

# on at start, while running
GPIO.output(pin_led, GPIO.HIGH)

# connect to ground to keep running
GPIO.setup(pin_halt,GPIO.IN,pull_up_down=GPIO.PUD_UP)

t=20
print ("sleep to make sure boot is over and juice started:", t,  ' sec')
time.sleep(t)

halt = GPIO.input(pin_halt)
print ("state of keep running pin is (pullup, no jumper = HIGH = HALT)", halt)
if halt ==0:
	print("		WARNING: will keep running!!!!")

if led: # led is false. could use external led blink.  use internal led instead
	# flash led to signal start
	print ("flash external led")
	flash(5,0.2)

# debug, info, warning, error, critical
log_file = "/home/pi/beecamjuice/log.log"
print ("logging to:  " , log_file)
logging.basicConfig(filename=log_file,level=logging.INFO)
logging.info(str(datetime.datetime.now())+ '\n-------------- beecamjuice starting ...' )

s = os.popen('date').read()
print ("system date: ", s)
logging.info(str(datetime.datetime.now())+ ' system date at start: ' + s )

s = os.popen('sudo hwclock -r').read()
logging.info(str(datetime.datetime.now())+ ' read hw clock at start: ' + s )
print ("read hw clock: " , s)



# cycle , delay  .  flash external led if present
def flash(c,d): # external led
	for i in range(0,c):
		GPIO.output(pin_led, GPIO.HIGH)
		time.sleep(d)
		GPIO.output(pin_led, GPIO.LOW)
		time.sleep(d)

# python3
def send_pushover(s):
# P2	conn = http.HTTPSConnection("api.pushover.net:443")
	conn = http.client.HTTPSConnection("api.pushover.net:443")
	conn.request("POST", "/1/messages.json",

#urllib has been split up in Python 3. The urllib.urlencode() function is now urllib.parse.urlencode(), and the urllib.urlopen() function is now urllib.request.urlopen(). 
# P2 	urllib.urlencode({
 	urllib.parse.urlencode({
    	"token": "your token",
    	"user": "your token",
   	 "message": s,
  	}), { "Content-type": "application/x-www-form-urlencoded" })
	conn.getresponse()
	logging.info(str(datetime.datetime.now())+ ' send pushover ...' + s )


#https://github.com/PiSupply/PiJuice/issues/91
# Record start time for testing
#txt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' -- Started\n'
#with open('/home/pi/beecamjuice/test.log','a') as f:
#    f.write(txt)

while not os.path.exists('/dev/i2c-1'):
	time.sleep(0.1)

try:
	pj = pijuice.PiJuice(1, 0x14)
except:
	# cannot use internal led to signal error. pj not created
	print("Cannot create pijuice object")
	logging.error(str(datetime.datetime.now())+ '!!!!  cannot create pijuice object, exit and keep running  ...' )
	send_pushover("PiJuice: cannot create PiJuice object. will exit")
	sys.exit()

status = pj.status.GetStatus()
print ('juice object created:', status )
status = status ['error']

if status == 'NO_ERROR':
	print ("PiJuice Status OK")
	# internal led 2 'D2'. blue [r,g,b] range 0-255
	#pj.SetLedState('D2', [0, 0 , 200])

	# blink x times, Blue 500 ms, off 500 ms
	pj.status.SetLedBlink('D2',2, [0,0,200], 500, [0, 0, 0], 500)
	# executed on juice microcontroler. if next set led too quick, will overwrite

else:
	# internal led. solid red RGB
	pj.status.SetLedState('D2', [200, 0 ,0])

	print ("PiJuice Status ERROR")
	logging.error(str(datetime.datetime.now())+ ' PiJuice status ERROR' )
	enable_wakeup(pj) # in case
	shut(pj) # otherwize was staying on, sucking power. sucker

print ("juice firmware version: ", pj.config.GetFirmwareVersion()['data']['version'])


# dict
soc = pj.status.GetChargeLevel()
soc = "%0.0f" %(soc['data'])
print ("soc ", soc)
logging.info(str(datetime.datetime.now())+ ' soc: ' + str(soc)  )
soc = int(soc)
if soc < limit_soc:
	logging.info(str(datetime.datetime.now())+ ' soc too low: ' + str(soc)  )

time.sleep(0.4)
vbat = pj.status.GetBatteryVoltage()
vbat = "%0.1f" %(vbat['data']/1000.0)
print ("vbat on board battery voltage", vbat)
logging.info(str(datetime.datetime.now())+ ' vbat: ' + str(vbat)  )

time.sleep(0.4)
ibat = pj.status.GetBatteryCurrent()
time.sleep(0.4)
ibat = pj.status.GetBatteryCurrent() # false read  ?
ibat = ibat['data']
print ("ibat current supplied from the battery", ibat)
logging.debug(str(datetime.datetime.now())+ ' ibat: ' + str(ibat)  )

# iio 200 ma, Vio 5V  ibat 300 ma when not charging,  -2000 when charging
# Vbat is the on-board battery voltage and ibat is the current that is being supplied from the battery. 


time.sleep(0.4)
temp=pj.status.GetBatteryTemperature()
temp = "%0.0f" %(temp['data'])
print ("temp ", temp)
logging.debug(str(datetime.datetime.now())+ ' temp: ' + str(temp)  )


# vio is the voltage that is on the IO pin weather this is input or output and the iio is the current being provided or drawn. 
# When reading analog read on IO1 it will output the same as vio.

time.sleep(0.4)
vio=pj.status.GetIoVoltage()
vio = vio['data']
print ("vio voltage on IO, input or output", vio)
logging.debug(str(datetime.datetime.now())+ ' vio: ' + str(vio)  )

time.sleep(0.4)
iio=pj.status.GetIoCurrent()
iio = iio['data']
print ("iio current drawn or supplied on IO", iio)
logging.debug(str(datetime.datetime.now())+ ' iio: ' + str(iio)  )


"""
time.sleep(0.4)
print ("reading analog in")
lipovbat=pj.status.GetIoAnalogInput(1)
print (lipovbat)
lipovbat= "%0.1f" %(2.0 * lipovbat['data']/1000.0) # pont diviseur. 3.3v  logic max 3.6
print ("lipo vbat Volt", lipovbat)
logging.info(str(datetime.datetime.now())+ ' lipo bat Volt: ' + str(lipovbat)  )
"""

print ("reset fault flag")
pj.status.ResetFaultFlags(['powerOffFlag', 'sysPowerOffFlag'])

# thinkspeak
print ( "publish to thinkspeak" )
try:
	thing = thingspeak.Channel(285664, api_key="W07V0W2KV85W55XY", \
	  write_key="7N95KJW5N76L4JWZ", fmt='json', timeout=None)
	response = thing.update({1:vbat,2:soc,3:temp})
	print (response)
except:
	print("Thingspeak failed")


# program alarm 
def set_alarm(sleep_tile,pj):
	# Set RTC alarm x minutes from now
	# RTC is kept in UTC or localtime
	a={}
	a['year'] = 'EVERY_YEAR'
	a['month'] = 'EVERY_MONTH'
	a['day'] = 'EVERY_DAY'
	a['hour'] = 'EVERY_HOUR'
	t = datetime.datetime.utcnow()
	#a['minute'] = (t.minute + DELTA_MIN) % 60
	a['minute'] = (t.minute + sleep_time) % 60
	a['second'] = 0
	try:
		print ("setting RTC alarm " , a['minute'] )
		status = pj.rtcAlarm.SetAlarm(a)
		print ("rtc Set alarm status: " + str(status)) # if not str exception cannot concatenate str and dict
		logging.info(str(datetime.datetime.now())+ ' rtc Set alarm status: ' + str(status) )

		if status['error'] != 'NO_ERROR':
			print('Cannot set RTC alarm')
			logging.error(str(datetime.datetime.now())+ ' Cannot set RTC alarm; will exit and keep running  ' )
			blynk.virtual_write(bterminal, 'cannot set RTC. RUN')
			send_pushover("PiJuice: cannot set RTC alarm. will exit and keep running")
			time.sleep(5)
			sys.exit()
		else:
			print('RTC Get Alarm: ' + str(pj.rtcAlarm.GetAlarm()))
			logging.info(str(datetime.datetime.now())+ ' RTC Get Alarm:  ' + str(pj.rtcAlarm.GetAlarm()) )


	except Exception as e:

		logging.info(str(datetime.datetime.now())+ ' !!! EXCEPTION in enable wakeup' + str(e))
		blynk.virtual_write(bterminal, 'Exception Wakeup\n')
		send_pushover("PiJuice: Exception Wakeupup enable")

def enable_wakeup(pj):
		# Enable wakeup, otherwise power to the RPi will not be applied when the RTC alarm goes off
		s= pj.rtcAlarm.SetWakeupEnabled(True)
		print ("enable wakeup to power PI on RTC alarm " + str(s))
		logging.info(str(datetime.datetime.now())+ ' enable wakeup: ' + str(s) )
		time.sleep(0.4)

# set power off
def power_off(delay,pj):
	try:
		# remove 5V power to PI
		pj.power.SetPowerOff(delay)
		logging.info(str(datetime.datetime.now())+ ' setpoweroff after ' + str(delay))
	except Exception as e:
		print ("exception in setpoweroff: ", str(e))
		logging.error(str(datetime.datetime.now())+ ' exception in setpoweroff ' + str(e) )

# blynk
def blynk_thread(now):
	# remove first word dow so that it fits in android screen
	print (now)
	n=now.split()
	del n[0]
	now=""
	for i in n:
		now=now+i+' '
	print (now)

	print("     BLYNK_START blynk thread started "), now

	def blynk_connected():
		print("     BLYNK_CONNECTED Blynk has connected. Synching button...")
		logging.info(str(datetime.datetime.now())+ ' Blynk connected. string:   ' + now)
		#blynk.sync_all()
		blynk.sync_virtual(bbutton)
		blynk.sync_virtual(bcount)
		blynk.sync_virtual(bsleep)

		print("     BLYNK_WRITE write date to blynk: "), now
		#blynk.virtual_write(bterminal, now.isoformat()+'\n')
		# use ntp time , already a string
		# value already formatted, rounded
		blynk.virtual_write(bterminal, now + '\n')
		blynk.virtual_write(btemp, temp)
		blynk.virtual_write(bsoc, soc)
		blynk.virtual_write(bvbat, vbat)
		#blynk.virtual_write(blipovbat, lipovbat)
		#blynk.virtual_write(bibat, ibat)

	@blynk.VIRTUAL_WRITE(bbutton)
	def button_write_button(value):
		global button
		print('     BLYNK_SYNCHED button handler: Current button value: {}'.format(value))
		button=value

	# will not sync if value is empty (just created)
	@blynk.VIRTUAL_WRITE(bcount)
	def button_write_count(value):
		global count
		print('     BLYNK_SYNCHED count handler: Current count value: {}'.format(value))
		# value str
		count=int(value)
		if count < 1000:
			count = count + 1
		else:
			count =1

	@blynk.VIRTUAL_WRITE(bsleep)
	def button_write_sleep(value):
		global sleep_time
		print('     BLYNK_SYNCHED sleep handler: Current sleep value: {}'.format(value))
		# value str
		if sleep_time >=5 and sleep_time <=120:
			sleep_time=int(value)
		else:
			sleep_time=60
		logging.info(str(datetime.datetime.now())+ ' sleep time ' + str(sleep_time) )

	# .py will not run long enough ?
	@blynk.VIRTUAL_WRITE(bterminal)
	def v8_write_handler(value):
        	print ("     blynk handler: read terminal")
        	print (value)
	        blynk.virtual_write(bterminal, 'Command: ' + value + '\n')

	blynk.on_connect(blynk_connected)

	try:
		blynk.run()
		#never returns
		# thread.exit()
	except Exception as e:
		print ("exception in Blynk.run. Blynk thread exit ") , e

	print("blynk thread exit")


# use ntp , if fails used hwclock 

def get_time_and_file_hwclock():
	now = datetime.datetime.now()
	year = int(datetime.datetime.now().year)
	month = int(datetime.datetime.now().month)
	day = int(datetime.datetime.now().day)
	hour = int(datetime.datetime.now().hour)
	mn = int(datetime.datetime.now().minute)

	file_name = str(month) + "_" + str(day) + "_" + str(hour) + "_" \
	+ str(mn)  + ".jpg"

	# set timestring to send to blynk
	# Y year, m month, d day, H hour, M minute, S sec 
	# I hour 12 padded, p AM PM; A weekday, a weekday abbrev, B,b month
	# 10:32PM September 23 1st word removed before sending to blynk (dow is returned by google NTP)
	time_string = now.strftime("holder %b %d %H:%M")
	# fist field removed. from ntp

	return(time_string,file_name,hour,month)


############ try this first. if exception, use hwclock  

def get_time_and_file_ntp():

# to get correct time stamp in log. for pic filename, we could only get it from google ntp
	#print("synching NTP")
	#os.system("sudo ntpdate -u pool.ntp.org")

# even if off, we only care about the delta
# not true. ntp can set time while we run
	#start_time=datetime.datetime.now()

	# use NTP directly to test for nigth and file name
	print ("call google time server")

	# string send thru blynk
	time_string = ("will ask google")
	file_name = "uninitialized" # in case, to avoid exception not assigned

# set time_string and file_name

	try:
		c=ntplib.NTPClient()
		response = c.request('time.google.com', version=3)
		# sec to string
		# time string formatted there
		time_string =  time.ctime(response.tx_time)
		print ("time from google ntp: ", time_string)

		hour = datetime.datetime.fromtimestamp(response.tx_time).hour
		month =  datetime.datetime.fromtimestamp(response.tx_time).month
		year = datetime.datetime.fromtimestamp(response.tx_time).year
		mn = datetime.datetime.fromtimestamp(response.tx_time).minute
		day = datetime.datetime.fromtimestamp(response.tx_time).day
		file_name = str(month) + "_" + str(day) + "_" + str(hour) + "_" \
		+ str(mn) +  ".jpg"
		logging.info(str(datetime.datetime.now())+ ' Google NTP responded '  + time_string  )
		pj.status.SetLedBlink('D2', 1, [0,50,0], 100, [0, 0, 0], 100)


	except Exception as e:
		print ("NTPlib error, use hw clock ", str(e))
		# python 3 ?
		#AttributeError: 'NTPException' object has no attribute 'message'
		#print (e.message, e.args)
		logging.error(str(datetime.datetime.now())+ ' NTP lib exception, will use hwclock '  + str(e)  )
		(time_string,file_name,hour,month) = get_time_and_file_hwclock() 
		pj.status.SetLedBlink('D2', 1, [50,0,0], 100, [0, 0, 0], 100)

	finally:
		return(time_string,file_name,hour,month)


# which wifi
# also iwgetid
s1="/home/pi/beecamjuice/get_wifi.sh"
try:
	s = subprocess.check_output([s1])
except Exception as e:
	print ("exception iwconfig ", str(e))
	s= "exception getting wifi"

# python3 'wifi' is str   s is bytes. cannot concatenate
print ("wifi being used: ", s)
logging.info(str(datetime.datetime.now())+ ' wifi: ' + s.decode('utf-8') )


# get time stamp for blynk, filename for pic and hour for day nigth
# hwclock or ntp
print ("get time from NTP and backup to hwclock if fails")
#(time_string,file_name,hour,month) = get_time_and_file_hwclock()
(time_string,file_name,hour,month) = get_time_and_file_ntp()

print ("picture filename: " , file_name)
print ("time string for blynk: " , time_string)
logging.info(str(datetime.datetime.now())+ ' ' + time_string + ' ' + file_name) 

# sunrise and sunset per month
#sun = [8,17,8,18,7,19,7,20,6,21,6,21,6,21,7,20,7,19,7,17,7,18,7,17]
sun = [7,18,6,18,6,19,7,20,6,21,6,21,6,21,5,21,5,21,6,20,6,18,7,18]

# to take and send pic to cloud
script = "/home/pi/beecamjuice/send_pic_juice.sh"

# send log to cloud. not used
script_log = "/home/pi/beecamjuice/send_log.sh"

# send pic during day
print ("hour is" , hour, "month is ", month)
sunrise= sun[(month-1)*2]
sunset= sun[(month-1)*2+1]
print ("sun rise ", sunrise, "sunset ", sunset)

if soc < limit_soc: # quiet at nite
	logging.info(str(datetime.datetime.now())+ ' soc below limit: ' +str(soc) )

if (hour >= sunrise) and (hour <= sunset):
	logging.info(str(datetime.datetime.now())+ ' check sun: DAY ' )
	print ("apres lever et avant coucher , push pic")

	if soc < limit_soc: # quiet at nite
		# P3  Can't convert 'int' object to str implicitly < str(limit)
		send_pushover("PiJuice: soc %d < limit %d. Config: shutdown at 10%, wakeup at 70%" %(soc,limit_soc) )

	# in foreground ?
 	#file_name = file_name + "  &"
	print ("call script: " , script, " " , file_name)
	ret_code=666
	try:

	#	process = subprocess.Popen([script,file_name], stdout=subprocess.PIPE)
	#	print (" ")
	#	print (process.communicate())
	#	print (" ")
	#	ret_code = process.wait()

		s= script + " " + file_name
		ret_code = os.system(s)
		print ("script :" , s ,  "ret code: " , ret_code)

	except Exception as e:
		logging.info(str(datetime.datetime.now())+ ' Exception in script ' + str(e) )
		print ("exception in script: " , str(e))

	#logging.info(str(datetime.datetime.now())+ ' send picture script returned: (0=OK) ' + str(ret_code) )

	if ret_code == 0:
		logging.info(str(datetime.datetime.now())+ ' picture sent OK  '  + file_name  )
		print ("pic script return 0, ie OK")
		if led:
			flash(3,0.1)
		# blink green
		# if 500ms, will be overwriten by further set led
		pj.status.SetLedBlink('D2', 2, [0,200,0], 100, [0, 0,0], 100)

	else :
		logging.error(str(datetime.datetime.now())+ ' picture NOT sent. ret code:  '  + str(ret_code)  )
		print ("ERROR in pic script " , ret_code)
		send_pushover("PiJuice: picture not sent %d" %(ret_code) )
		flash(3,1)
		#blink red
		pj.status.SetLedBlink('D2', 2, [200,0,0], 100, [0, 0,0], 100)

else:

	print ("nigth. no pic")
	logging.info(str(datetime.datetime.now())+ ' Check sun: NIGTH  '  )
	if led:
		flash(1,0.1)
	time_string = time_string + " N"
	# string send to blynk shows no pic
	# blynk blue
	pj.status.SetLedBlink('D2', 2, [0,0,200], 100, [0, 0,0], 100)

# will not run until script has ran
# after blynk connected and synch
print ("BASH script has run or nigth. waiting for Blynk synch ..")

# create blynk there so that it is available in main thread as well
print ("starting blynk thread")
blynk = BlynkLib.Blynk('your token')

print ("time string to be sent blynk terminal", time_string)
# _  for python3
_thread.start_new_thread(blynk_thread, (time_string,))

print ("wait for blynk to run and synch button")
c=1
while (button == "2"):
	time.sleep(1)
	c=c+1
	if c==30:
		print ("!!!!!!!!! button could not synch. assume OFF , ie string 0")
		logging.error(str(datetime.datetime.now())+ ' stay on button did not synch. assumes OFF  '  )
		button="0"
		break
print ("button has synched or timeout on synch")

blynk.virtual_write(bcount, count)

# halt or stay on ?
# STAY ON if either pin to ground (jumper), or stay on button == "1"
# SHUTDOWN if pin high (no jumper) and stay on button == "0"
# pin: default PULLUP , no jumper = HIGH
# halt is int, button UNICODE !!!!!!!
print ("halt pin: " , halt , "stay on button: " , button)
print ("keep running if halt = LOW (jumper to ground) or stay on button = ON ie string 1")
print ("shutdown if halt = HIGH (No jumper to ground, PULLUP) and  stay on button = OFF ie string 0")

logging.info(str(datetime.datetime.now())+ ' Blynk synched: halt pin: ' + str(halt) + ' button: ' + button  )

# HALT
if (halt==1) and (button=="0"): # default pullup shutdown
	print ("halt pin jumper to HIGH and button OFF. HALTING")

	end_time=datetime.datetime.now()
	print ("start time: ", start_time)
	print ("end time:   ", end_time)

        # flash led to signal end
	if led:
	        flash(10,0.1)

	#blink ligth green RGB
	pj.status.SetLedBlink('D2', 2, [0,0,200], 100, [0, 0,0], 100)

	# set alarm , done in GUI or here
	print ("set sleep time: %d" %(sleep_time))
	set_alarm(sleep_time,pj)

	print ("enable wakeup")
	enable_wakeup(pj)

	print ("cut MCU power switch")
	pj.power.SetSystemPowerSwitch(0) # pi supply recommended

	delay=20
	print ("PI power down in %d sec" %(delay))
	#set poweroff done in gui or here
	power_off(delay,pj)

	logging.info(str(datetime.datetime.now())+ ' halt' )

	# send log to cloud
	#ret_code = os.system(script_log)
	#print ("send log script :" , script_log ,  "ret code: " , ret_code)

	# clear led
	pj.status.SetLedState('D2', [0, 0,0])


	print ("halt")
	subprocess.call(["sudo", "halt"])
	time.sleep(600)


# keep running
if ((halt==0) or (button=="1")):
	print ("halt pin jumper to LOW or button ON. RUNNING\n\n")
	if button == "1":
		# blynk button stay on
		send_pushover("PiJuice: stay on button")

	end_time=datetime.datetime.now()
	print ("start time: ", start_time)
	print ("end time:   ", end_time)

	#SetLedBlink(led, count, rgb1, period1, rgb2, period2)
	# count = 255 infinite  period 10 2550 ms RGB 0 255
	# if 255 will keep bliking even if python has exited (stm32 does it)
	# blink red
	pj.status.SetLedBlink('D2', 2, [200,0,0], 100, [0,0,0], 100)

        # flash led to signal end
	if led:
		flash(5,1)

	blynk.virtual_write(bterminal, 'KEEP RUNNING\n')
	logging.info(str(datetime.datetime.now())+ ' Exit. KEEP RUNNING' )

	# send log to cloud
	#ret_code = os.system(script_log)
	#print ("send log script :" , script_log ,  "ret code: " , ret_code)

	# clear led
	pj.status.SetLedState('D2', [0, 0,0])

	print ("exit and keep PI running")
	# cleanup turn running led ofr
	#GPIO.cleanup()
	exit(0)
