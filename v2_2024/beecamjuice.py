#!/usr/bin/python3

# 14 fev 2017.  Blynk python
# 18 rev: add lipo gauge, ntp
# 11 mars: script in foreground. retry count
# 27 09: juice, led 2
# 01 10: dweet, thingspeak, event, pushover 
# 10 10 hwclock
# 29 dec 2019 refactor internal led
# 10 avril 2023 move to private server


version = 2.2  # 2 sept 2024. long time no see. add soc, OK to blynk terminal
# lost source. 
version = 2.3 # 26 sept 2024 local pic, S, utils, logs, juice API 
version = 2.32 # 29 sept 2024. no NTP
version = 2.33 # 20 sept 2024. do not use pj as parameter, ntp optional
version = 2.34 # 3 oct 2024. wait juice for status ok. long juice watchdog. sleep 0.4. reboot, poweroff
version = 2.36 # 6 oct 2024. ret_code at nite. use ntp again
version = 2.37 # 7 oct 2024. fatal()
version = 2.38 # 9 oct 2024. disable no power and sys start/stop event. cause in keep running pushover
version = 2.39 # 10 oct 2024. add time to run on battery

#################
# NTP
#################

#https://feeding.cloud.geek.nz/posts/time-synchronization-with-ntp-and-systemd/

# on systemd apt-get purge ntp to use only systemd-timesyncd.service 
# edit /etc/systemd/timesyncd.conf
# systemctl restart systemd-timesyncd.service  

#sudo ntpd -gq force ntp update

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

#################
# RTC, hwclock
#################
# sudo hwclock -r  read hwclock

# set hwclock with system time 
# sudo hwclock -w OR --systohc  same time, not utc vs local

# set hwclock with date
# sudo hwclock --set --date --localtime "1/4/2013 23:10:45" 4 jan

#set system time from hwclock
# sudo hwclock -s OR --hctosys

# use --debug
# use --utc or --localtime when setting hwclock


import RPi.GPIO as GPIO
import os
import time
import sys
import logging
import subprocess
import ntplib
import http.client, urllib
import _thread
import datetime

#https://github.com/vshymanskyy/blynk-library-python
#pip install blynk-library-python
import BlynkLib

# sudo apt-get install ntp
# sudo apt-get install ntpdate (client)

#sudo pip install thingspeak
import thingspeak 
import pijuice


###########
# app modules
###########

import my_arg

sys.path.append("../all_secret")
sys.path.append("../my_modules")

import my_utils
import my_log
import my_juice
from pushover import send_pushover
import my_secret


############
# config
############
# will overwriten by GPIO read and blynk callback
go_to_sleep = None

# GPIO
pin_halt=26
pin_led=16 # not used anymore

# Blynk vpin
bbutton=18 # halt or tun
bterminal=8

bsoc=20
bsleep=21 #programmable sleep time
btemp=22 # of bat
bvbat=23 # of pijuice
bcount=24 # increment at each run

# use PI led
led = False

#button value 2 un-initialized. THIS IS A string
button="2"

# incremented at each wakeup. kept in blynk server
count = 0

#RTC sleep in mn
sleep_time=30 # normal operation, overwritten by Blynk
sleep_time_nite = 55 # longer at nite
sleep_time_fatal = 10 # retry after fatal error

# my watchdog thread will sleep for this; and if still active, there is a problem. 
#  should be larger than any normal processing, incl timeout 
watchdog_sleep_sec = 60*3


limit_soc=13 # limit to send pushover .  a bit higher than the HALT_POWER_OFF in juice config

# Juice HAT parameters
poweroff_delay = 25 # sec
wakeup_oncharge = 20 # % not used (disabled in GUI)
juice_watchdog  = 4 # mn  not used (set in GUI)


# sleep at start. sec. allows PI to boot completely. NOTE: sucks power. could rather used systemd or cron
sleep_rc = 30

################
# fatal error behavior
################
# reboot. can create infinite loop of reboot and SUCK power
# sys.exit(). can log on immediatly but SUCK power
# ===> sleep and wake up to retry later. use remote halt to keep running and log on to pi 
# no need for configuration, this is the best option

# NOTE: above if for when juice already initialized. before, can only do reboot or exit
# go for reboot. dangerous but hopefull it may fix the problem
reboot_on_early_error = True

# dir to save picture locally
# create here, passed as argument to bash script
local_pic = "local_pic"
if not os.path.exists(local_pic):
	os.mkdir(local_pic)

##############
# logging
##############
# debug, info, warning, error, critical
log_file = "beecamjuice.log"
root_log = "logs"

my_log.get_log(log_file, root= root_log)

s = "=====> beecamjuice v%0.2f starting" %version 
print(s)
logging.info(s)



# to measure execution time
# can use time.time() float, minus is sec in float
# or datetime.datetime , minus returns timedelta , 0:00:37.666-, ie 37sec
# do it after time synched. 
start_time=datetime.datetime.now()

# to set RTC alarm
current_mn = start_time.minute
print("start time (before rc sleep) %s, start mn %d" %(start_time, current_mn))

# get system date at boot. should be un init (ntp had no time to run)
# same as .now()
s1 = os.popen('date').read()
print("date:", s1)

# rc.local vs systemctl
# saw unstability with systemctl. did not wake up after a while.  
# need to make sure networking, pijuice daemon , etc .. started
print ("sleep to make sure boot is over and juice started: %d sec" %sleep_rc)
time.sleep(sleep_rc)



##################
# GPIO
##################
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(pin_led,GPIO.OUT) # external led

# on at start, while running
GPIO.output(pin_led, GPIO.HIGH)

# connect to ground to keep running
GPIO.setup(pin_halt,GPIO.IN,pull_up_down=GPIO.PUD_UP)


# halt pin
halt = GPIO.input(pin_halt)
print ("HALT pin: (pullup, no jumper = HIGH = HALT = go_to_sleep)", halt)

# init as soon as possible, to make available to my_watchdog
go_to_sleep = (halt == 1)

if halt == 0:
	print("WARNING: will keep running!!!!")


if led: # led is false. could use external led blink.  use internal led instead
	# flash led to signal start
	print ("flash external led")
	flash(5,0.2)



###############
# clock
# https://github.com/PiSupply/PiJuice/tree/master/Software#pijuice-rtc
###############
# -w, --systohc Set the Hardware Clock to the current System Time.
# -s, --hctosys Set the System Time from the Hardware Clock.


# SET RTC from known source  SYS -> HW
# set the date and time using the Linux date command. This sets the system clock
# Copy the date and time to the RTC: sudo hwclock --systohc or -w
# Remarquez que si vous utilisez NTP, l'horloge matérielle est automatiquement synchronisée à l'horloge système toutes les 11 minutes, et cette commande n'est utile que pendant le démarrage pour obtenir une heure système initiale raisonnable.

# On subsequent reboots  HW -> SYS
# the system clock has to be initialised from the RTC: sudo hwclock --hctosys or -s
# test for the availability of I2C
# You probably want to remove the fake-hwclock package just to be sure

# https://www.softprayog.in/tutorials/hwclock-the-hardware-clock-query-and-set-program
# hwclock -D  debug


# get hwclock. maintained by battery (should be init once)
while not os.path.exists('/dev/i2c-1'):
	time.sleep(0.1)
time.sleep (0.5)

try:
	s2 = os.popen('sudo hwclock -r').read()
	print("read hwclock", s2)
except Exception as e:
	s2 = "cannot read hwclock %s" %str(e)
	print(s2)
	logging.error(s2)

#################
# PIJuice init
################
#https://github.com/PiSupply/PiJuice/issues/91
# wait for status to be OK (saw 4 retry)

# succeed even if no HAT present
pj = my_juice.get_juice()

if pj is None:

	if reboot_on_early_error:
		s= "cannot create pijuice. reboot"
	else:
		s= "cannot create pijuice. exit. WARNING. PI still on"

	print(s)
	logging.error(s)
	send_pushover(s, priority=1, title = "PIJuice")

	if reboot_on_early_error:
		subprocess.call(["sudo", "reboot"])
	else:
		sys.exit()
else:
	print("PIJuice created")


#################
# wait for status OK to proceed
################
retry = 0
while pj.status.GetStatus()['error'] != 'NO_ERROR':

	retry = retry  + 1


	###################
	# cannot talk to juice
	# reboot or exit
	# both will suck power
	####################
	if retry == 10:
		if reboot_on_early_error:
			s = "!!!! PIJuice status not ok after %d retry. REBOOT" %(retry)
		else:
			s = "!!!! PIJuice status not ok after %d retry. exit. WARNING: PI still running" %(retry)

		print(s)
		logging.error(s)
		pushover.send_pushover(s)

		if reboot_on_early_error:
			subprocess.call(["sudo", "reboot"])
		else:
			sys.exit(1)

	else:
		s = "status not ok. retry: %d" %(retry)
		print(s)
		logging.error(s)
		time.sleep(1)

####################
# status OK. ready to proceed
####################
s = "PIJuice status OK. %s retries. ready to proceed" %retry
print(s)
logging.info(s)

#####################
# safety. reenable alarm immediatly
#####################
#should not be needed. but will at least wakeup same mn, h+1
# if set alarm fails, but still going to powerdown. this case does not seem to be there. antway ..
status = pj.rtcAlarm.SetWakeupEnabled(True)

#################
# guess time to run on battery based on soc
#################
#12000 mah  / 400ma = 30h!!
def get_ttr_h(soc):
	battery_mah = 12000 # mah
	power_drain = 400 # ma
	ttr = (soc/100) * battery_mah/power_drain # h fractional
	return(ttr)

##################
# program RTC alarm, next mn = now + sleep_time (mn) modulo 60
# enable RTC wakeup
##################
# defined before my_watchdog (which uses it)

def set_alarm(sleep_time, current_mn, pj):
	# Set RTC alarm x minutes from now
	# RTC is kept in UTC or localtime
	# sleep_time in mn

	a={}
	a['year'] = 'EVERY_YEAR'
	a['month'] = 'EVERY_MONTH'
	a['day'] = 'EVERY_DAY'
	a['hour'] = 'EVERY_HOUR'
	#t = datetime.datetime.utcnow()
	a['minute'] = (current_mn + sleep_time) % 60
	a['second'] = 0


	try:

		# set alarm
		# use pj here, vs as param to function in another module
		status = pj.rtcAlarm.SetAlarm(a)
		time.sleep(0.4)

		if status['error'] == 'NO_ERROR': 
			s = "current mn %d. just set RTC alarm next mn: %d" %(current_mn,a['minute'])
			print(s)
			logging.info(s)


			# NEEDED ???????? in test example
			# https://github.com/PiSupply/PiJuice/issues/378
			# Move the SetWakeup(True) after the 60 seconds sleep to just before the shutdown. This to avoid timesyncd resetting the wakeup flag during the 60 seconds sleep.
			# Also add a call to ClearAlarmflag() just before the shutdown. The flag gets set when the alarm triggers but only if previously cleared.
			#pj.rtcAlarm.ClearAlarmFlag()

			# Enable wakeup, otherwise power to the RPi will not be applied when the RTC alarm goes off
			status = pj.rtcAlarm.SetWakeupEnabled(True)
			time.sleep(0.4)


			# checks to see if wakeup has been enabled and if the wakeup alarm flag has been set.
			ret = pj.rtcAlarm.GetControlStatus()
			s = "alarm getcontrolstatus after setting alarm: %s" % str(ret)
			print(s)
			logging.info(s)

			# read back alarm
			ret = pj.rtcAlarm.GetAlarm()
			s = "alarm after set: %s" % str(ret)
			print(s)
			logging.info(s)


		else:
			s= 'Cannot set RTC alarm; exit & keep running'
			print(s)
			logging.error(s)

			s = "Error set alarm. RUNNING"
			blynk.virtual_write(bterminal, '%s\n'%s)
			send_pushover(s, priority=1, title = "PIJuice")

			time.sleep(5)
			sys.exit()


	except Exception as e:

		s= 'EXCEPTION in setting alarm: %s. exit and keep running' %str(e)
		print(s)
		logging.error(s)

		s = "Exception set alarm. exit and RUNNING"

		blynk.virtual_write(bterminal, '%s\n' %s)
		send_pushover(s, priority=1, title = "PIJuice")

		time.sleep(5)
		sys.exit()


################
# halting after RTC set
# poweroff
###############
def halting(pj, delay):

	s = "manage power and sudo poweroff"
	logging.info(s)
	print(s)

	print ("cut MCU power switch")
	pj.power.SetSystemPowerSwitch(0) # pi supply recommended
	time.sleep(0.4)

	# send log to cloud
	#ret_code = os.system(script_log)
	#print ("send log script :" , script_log ,  "ret code: " , ret_code)

	# clear led
	pj.status.SetLedState('D2', [0, 0, 0])
	time.sleep(0.4)

	"""
	# to make sure. on board led configured in boot/config.txt
	# no power led for zero. used for Bplus
	# instability with Bplus ? too much power hungry ?
	print ("clear PI onboard led ")
	try:
		subprocess.call(["sudo", "/home/pi/beecamjuice/turn_led_off.sh"])
	except:
		print('exception turn on board led')
	time.sleep(3)
	"""

	# do I need to do this each time, or rely on GUI ?
	# do I need to do before halting or anytime ? SEEMS FROM NOW
	#  "PiJuice shuts down power to Rpi after 20 sec from now"

	#my_juice.set_poweroff(pj,delay)
	pj.power.SetPowerOff(delay)
	time.sleep(0.4)
	#print("power off delay: " , my_juice.get_poweroff(pj))

	# datetime.timedelta
	e = datetime.datetime.now() - start_time
	s = "=====> sudo poweroff. elapse: %s" %e
	print(s)
	logging.info(s)


	subprocess.call(["sudo", "poweroff"])

	time.sleep(600)



#################
# my_watchdog popped
#################
def fatal(s):
	s = "FATAL error: %s. sleep %dmn and retry" %(s, sleep_time_fatal)
	print(s)
	logging.error(s)

	# send push
	try:
		send_pushover(s, priority=1, title="PIJuice FATAL")
	except:
		pass

	set_alarm(sleep_time_fatal,current_mn, pj)

	halting(pj,poweroff_delay)


#######################
# watchdog thread
#######################
# set alarm and halt, ie be hopefull and restart. so need juice to run
# look at go_to_sleep
# sleep_time may not be init from blynk yet

def my_watchdog_thread(x):


	s = "start my_watchdog thread: sleep %d sec. param: %s" %(watchdog_sleep_sec,x)
	print(s)
	logging.info(s)

	time.sleep(watchdog_sleep_sec)


	# add test go_to_sleep is None , ie still uninit. ie watchdog popped before camera script and blynk connect/synch happened
	if not go_to_sleep and go_to_sleep is not None:
		# this is normal
		s = "my_watchdog thread still alive after %d sec, but go_to_sleep FALSE: %s. Normal" %(watchdog_sleep_sec, go_to_sleep)
		print(s)
		logging.info(s)

	else:
		# true or none
		s = "my_watchdog thread still alive after %d sec, and go_to_sleep: %s. This is not normal" %(watchdog_sleep_sec, go_to_sleep)

		# use global
		s1 = "set RTC alarm %d mn from now and powerdown" %(sleep_time_fatal)
		print(s+s1)
		logging.error(s+s1)

		fatal(s+s1)




######################
# start watchdog thread as soon as possible
######################
# as soon as juice OK (because this will set alarm and halt
_thread.start_new_thread(my_watchdog_thread, ("pabou",))


#print("simulate hang")
#time.sleep(500)


###############################
# copy hw clock to system clock
###############################
# NTP will later update systemtime and hwclock
# NOTE: if fails, absolute time is wrong, but RTC delay is OK 

#subprocess.call(["sudo", "hwclock", "--hctosys"])
# error only seen in stderr (if redirected to file)

try:
	data = subprocess.check_output(['sudo', 'hwclock', "--hctosys"])
	data = data.decode('utf-8')
	# empty if OK
	s = "hctosys: %s" %data
	print(s)
	logging.info(s)

except Exception as e:
	s = "Exception setting hwclock: %s" %str(e)
	print(s)
	logging.error(s)


# get updated system date
s3 = os.popen('date').read()

s = "DATE. at boot:%s. hw/RTC clock:%s. after sync with hw/RTC:%s" %(s1,s2, s3)
print(s)
logging.info(s)


###############
# local or remote ?
###############
ssid = my_utils.get_ssid()
s = "ssid %s" %ssid
print(s)
logging.info(s)


##############
# blynk server
##############
# in app: project setting -> devices -> raspberry (friendly name), hardware = PI 2

if "Freebox" in ssid:
	blynk_server = "paboupicloud.zapto.org"
	blynk_port = 13809
	print("Blynk server is remote")
else:
	blynk_server = "192.168.1.206"
	blynk_port = 8089
	print("Blynk server is local")

blynk_ssl = False
blynk_token = my_secret.blynk_juice


#############
# store pic locally ?
#############
# Note: failed scp are always stored locally
# monitor file system usage

parsed_args = my_arg.parse_arg()

# passed as arg to bash script. bool
# note: pass str(bool), to easy bash
store_local = parsed_args["local"] # bool
print("store pic locally ?: %s" %store_local)


###############
# file system usage
###############
# monitor is storing pic locally

free_fs = my_utils.get_fs_free()
print("file system: %d%% free" %free_fs)



# cycle , delay  .  flash external led if present
def flash(c,d): # external led
	for i in range(0,c):
		GPIO.output(pin_led, GPIO.HIGH)
		time.sleep(d)
		GPIO.output(pin_led, GPIO.LOW)
		time.sleep(d)



#############
# clear Juice led
#############
# clear user led (seem to persists across reboot)
pj.status.SetLedState('D2',[0,0,0])


#################
# get and clear RTC alarm flag
#################
# flag seem to indicate whether wakeup was caused by RTC, or something else (wakeuponcharge, hardware poweron ..)
# read with RTC control status:
# RTC control status: {'error': 'NO_ERROR', 'data': {'alarm_wakeup_enabled': True, 'alarm_flag': False}}


# get value at boot (alarm_flag)
ret = pj.rtcAlarm.GetControlStatus()

if ret["error"] == "NO_ERROR":
	alarm_flag = ret["data"] ["alarm_flag"]
else:
	alarm_flag = None

s = "alarm flag at boot: %s. True means waked up by RTC. reset to false" %alarm_flag
print(s)
logging.info(s)

# clear it
pj.rtcAlarm.ClearAlarmFlag()



################
# analyze juice status
################
status = my_juice.get_status(pj)
# {'battery': 'CHARGING_FROM_IN', 
#'powerInput5vIo': 'NOT_PRESENT', 'powerInput': 'PRESENT', 
#'isButton': False, 'isFault': False}

on_battery = None

if status is not None:
	on_battery = (status['powerInput'] == "NOT_PRESENT" and status['powerInput5vIo'] == 'NOT_PRESENT')
	s = "status: %s. on battery: %s" %(str(status), on_battery)
	print(s)
	logging.info(s)

	print ("juice firmware version: ", pj.config.GetFirmwareVersion()['data']['version'])

	# internal led 2 'D2'. blue [r,g,b] range 0-255
	# blink x times, Blue 500 ms, off 500 ms
	# executed on juice microcontroler. if next set led too quick, will overwrite
	pj.status.SetLedBlink('D2', 5, [0,0,200], 100, [0, 0, 0], 100)

	if status["isFault"]:

		###############
		# fault, but keep going ...
		###############
		s = "status returned isFault True. keep going. I want to believe"
		print(s)
		logging.error(s)
		send_pushover(s, priority=1, title = "PIJuice")

else:
	# should not happen, as we checked status before
	s = "PiJuice Status (COM) ERROR, after we checked it. WTF"
	print(s)
	logging.error(s)
	send_pushover(s, priority=1, title = "PIJuice")

	try:
		# internal led. solid red RGB
		pj.status.SetLedState('D2', [200, 0 ,0])
		time.sleep(5)
	except:
		pass

	### WHAT TO DO ????
	#enable_wakeup(pj) # in case
	#sys.exit(1)
	fatal(s)


#############
# battery
#############

(soc, temp, vbat, iomv, ioma)  = my_juice.get_battery(pj)
# iocurrent  0 when connected to usb
# soc: 91, temp: 21, vbat: 4097, iomv: 5067, ioma: -428

# use str in case of None
s = "soc: %s, temp: %s, vbat: %s, iomv: %s, ioma: %s" %(str(soc),str(temp), str(vbat), str(iomv), str(ioma)) 

if soc is not None and soc < limit_soc:
	s = "soc %d too low vs limit %d" %(soc, limit_soc)
	logging.warning(s)
	print(s)
	# pushover done later (do not send at nite)
	#send_pushover(s, priority=0, title = "PIJuice")


print("GetIoCurrent: ",pj.status.GetIoCurrent())

#############
# fault status
#############

# not needed in test example
#print ("reset fault flag")
#my_juice.reset_fault_flag(pj)

fault_status = my_juice.get_fault_status(pj)

if fault_status is not None:
	s= 'fault status: %s' %str(fault_status)
	print(s)
	logging.info(s)

	if fault_status != {}:
		s= 'fault status is not empty: %s' %str(fault_status)
		print(s)
		logging.error(s)
		send_pushover(s, priority=0, title = "PIJuice")



#################
# power configuration
# read current values set by GUI  (can also set with API)
################


# WTF. GUI value not returned. works if set with API
# {'error': 'NO_ERROR', 'data': 127}

#################
# poweroff delay
#################
# set in halting(), just before sudo powerof
# value at boot incorrect, ir not CLI.  PowerOff value: {'error': 'NO_ERROR', 'data': [255]}
#  but can set value and then ok PowerOff value: {'error': 'NO_ERROR', 'data': [19]}
#     20 19, someaccount for some execution time

# Removes power from the PiJuice to the GPIO pins i.e Raspberry Pi. Delay is used here to give the Raspberry Pi enough time to do a safe shutdown before power has been removed.
# Q: can I do this anytime, or "just before calling sudo halt" ?
#  ==== do it when needed, 



#####################
# WakeUpOnCharge
#####################

# Used to wakeup the Raspberry Pi when the battery charge level reaches a certain percentage
# Wakeup on charge only works when the PiJuice 5V is off when charging is detected.
# At wakeup the Wakeup on charge flag is cleared so it has to be set again before shutdown.

# ADDITIONAL to RTC, so mess up with regular wakeup
# when power present on pijuice usb (4.5v to 10V)
# 0 means regardless of soc, incl no battery
# disable in GUI

# wakeup the Raspberry Pi when POWER in pijuice micro USB AND the battery charge level reaches a certain percentage
# can be disabled with CLI
# WakeUpOnCharge value: {'error': 'NO_ERROR', 'non_volatile': False, 'data': 'DISABLED'}

# seem need to be set at each boot
# DOES need to be enabled, to recover from depleted battery ?
# OR just disable. a depleted battery will eventually recharge, and  RTC wakeup sequence will restart
# if enabled, should not triger wakeup when battery is 60% and solar are charging via pijuice microusb (ie mess with RTC wakeup)
# enable function of current soc ?

# DECISION: disable with CLI, and not not enable in python. could also enable with 99%

"""
        if soc is None or soc < 10:
                pj.power.SetWakeUpOnCharge(20)

        else:
                pj.power.SetWakeUpOnCharge(98)

        time.sleep(0.4)
"""

# use str if DISABLED
print("wakeup the Pi when the battery over %s %%" %str(my_juice.get_wakeuponcharge(pj)))

#################
# watchdog
#################
# set in CLI. value there is as set in CLI

#  The watchdog timer has a configurable time-out. It defines the time after which it will power cycle if it does not receive a heartbeat signal
print("juice watchdog %d mn" %my_juice.get_watchdog(pj))


"""
# liporider. used GPIO.  not used
time.sleep(0.4)
print ("reading analog in")
lipovbat=pj.status.GetIoAnalogInput(1)
print (lipovbat)
lipovbat= "%0.1f" %(2.0 * lipovbat['data']/1000.0) # pont diviseur. 3.3v  logic max 3.6
print ("lipo vbat Volt", lipovbat)
logging.info('lipo bat Volt: ' + str(lipovbat)  )
"""


##############
# thinkspeak
##############
print ( "publish to thinkspeak" )

api_key = my_secret.thingspeak_apikey
write_key = my_secret.thingspeak_writekey

try:
	thing = thingspeak.Channel(285664, api_key=api_key, \
	  write_key=write_key, fmt='json', timeout=None)
	response = thing.update({1:vbat,2:soc,3:temp})
	print ("thingspeak", response)
except:
	print("Thingspeak failed")


# blynk thread
# update terminal and gauge in connected call back
# run()
#############################

def blynk_thread(now, soc, ret_code):

	# build now, str to be written to blynk terminal in connected callback 
	# ret_code = None is nite (script did not ran)

	# ret_code is 0, 1 or None.  %d is exception if None
	print ("	BLYNK THREAD starting. now: %s, soc %d, ret_code %s" %( now, soc, str(ret_code)))

	# now str is supposed to be already formated for terminal
	# add soc, vbat, fs , battery, and ret code to what is printed on blynk terminal
	now = "%s soc:%d%% vbat:%0.1fv" %(now, int(soc), vbat/1000)

	now = "%s fs:%d%%" %(now, free_fs)


	if on_battery:
		now = "%s B" %now
	else:
		now = "%s P" %now


	if alarm_flag:
		now = "%s R" %now
	else:
		now = "%s X" %now

	if ret_code is None:
		now = "%s N" %now

	elif ret_code == 0:
		now = "%s OK" %now
	else:
		now = "%s NOK" %now

	print("write to terminal:",now)

	###########
	# call backs
	###########
	# print now str to terminal

	def blynk_connected():
		print("     BLYNK_CONNECTED callback")
		logging.info('Blynk connected. %s' %now)
		try:
			print("     BLYNK_SYNC")
			#blynk.sync_all()
			blynk.sync_virtual(bbutton)
			blynk.sync_virtual(bcount)
			blynk.sync_virtual(bsleep)

			print("     BLYNK_WRITE write terminal and gauge: ", now)
			blynk.virtual_write(bterminal, now + '\n')

			# gauge
			blynk.virtual_write(btemp, temp)
			blynk.virtual_write(bsoc, soc)
			blynk.virtual_write(bvbat, vbat/1000)
			#blynk.virtual_write(blipovbat, lipovbat)
			#blynk.virtual_write(bibat, ibat)
		except Exception as e:
			s = "Exception connected call back: %s" %str(e)
			print(s)
			logging.error(s)


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

		# beware modulo. slider limited to 59
		if sleep_time >=5 and sleep_time <=120:
			sleep_time=int(value)
		else:
			sleep_time=60

		s= 'sleep time from Blynk: %dmn' %sleep_time
		print(s)
		logging.info(s)

	# .py will not run long enough ?
	@blynk.VIRTUAL_WRITE(bterminal)
	def v8_write_handler(value):
        	print ("     blynk handler: read terminal")
        	print (value)
	        blynk.virtual_write(bterminal, 'Command: ' + value + '\n')


	# register connected call back
	blynk.on_connect(blynk_connected)


	##################
	# endless loop
	#################

	try:
		blynk.run()
		#never returns
		# thread.exit()
	except Exception as e:
		print ("exception in Blynk.run. Blynk thread exit ") , e

	print("blynk thread exit")



################
# assume system date already synched from hwclock
################
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

	time_string = now.strftime("%b %d/%H:%M")
	print("time string from hwclock/system time:", time_string)
	# time string from hwclock/system time: Sep 30/07:37

	return(time_string,file_name,hour,month, mn)

####################
# use ntp , if fails used hwclock 
# try this first. if exception, use hwclock
# interact with hwclock ??
###################

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
		s = "time from google ntp: %s" %time_string
		#time from google ntp:  Mon Sep 30 10:50:38 2024
		# time from google ntp: Sun Oct  6 08:25:10 2024
		# extra space if day <10. leave it alone
		print(s)
		logging.info(s)

		# remove 1st and last word, ie sun and 2014
		s = time_string.split(' ')
		time_string = " ".join(s[1:-1])
		print(time_string)


		hour = datetime.datetime.fromtimestamp(response.tx_time).hour
		month =  datetime.datetime.fromtimestamp(response.tx_time).month
		year = datetime.datetime.fromtimestamp(response.tx_time).year
		mn = datetime.datetime.fromtimestamp(response.tx_time).minute
		day = datetime.datetime.fromtimestamp(response.tx_time).day
		file_name = str(month) + "_" + str(day) + "_" + str(hour) + "_" \
		+ str(mn) +  ".jpg"

		# led
		pj.status.SetLedBlink('D2', 3, [0,200,0], 100, [0, 0, 0], 100)


	except Exception as e:
		print ("NTPlib error, use hw clock ", str(e))
		# python 3 ?
		#AttributeError: 'NTPException' object has no attribute 'message'
		#print (e.message, e.args)
		logging.error('NTP lib exception, will use hwclock '  + str(e)  )

		(time_string,file_name,hour,month,mn) = get_time_and_file_hwclock() 

		# user led
		pj.status.SetLedBlink('D2', 3, [200,0,0], 100, [0, 0, 0], 100)

	finally:
		return(time_string,file_name,hour,month, mn)


#######################
# get time
# hwclock or ntp
######################

# current_mn set at start, used to set RTC 

if parsed_args["ntp"]:
	print ("get time from NTP and backup to hwclock if fails")
	(time_string,file_name,hour,month, _) = get_time_and_file_ntp()
else:
	print ("get time string system; ie synched from hwclock")
	(time_string,file_name,hour,month,_) = get_time_and_file_hwclock()

########################
# picture processing
########################
# time string is augmented with various info (soc, ..) and written to blynk terminal
s = "picture filename: %s. time string for blynk: %s" %(file_name,time_string)
print(s)
logging.info(s) 

# sunrise and sunset per month
#sun = [8,17,8,18,7,19,7,20,6,21,6,21,6,21,7,20,7,19,7,17,7,18,7,17]
sun = [7,18,6,18,6,19,7,20,6,21,6,21,6,21,5,21,5,21,6,20,6,18,7,18]

# to take and send pic to cloud
script = "/home/pi/beecamjuice/send_pic_juice.sh"

# send log to cloud. not used
#script_log = "/home/pi/beecamjuice/send_log.sh"

# send pic during day
print ("hour is" , hour, "month is ", month)
sunrise= sun[(month-1)*2]
sunset= sun[(month-1)*2+1]
print ("sun rise ", sunrise, "sunset ", sunset)

if soc < limit_soc: # quiet at nite
	logging.info('soc below limit: ' +str(soc) )




################
# nite or no
################
if (hour >= sunrise) and (hour <= sunset):

	is_nite = False

	s = "apres lever et avant coucher , push pic"
	print(s)
	logging.info(s)

	if soc < limit_soc: # quiet at nite
		# P3  Can't convert 'int' object to str implicitly < str(limit)
		send_pushover("soc %d < limit %d. Config: shutdown at 10%, wakeup at 70%" %(soc,limit_soc), title="PIJuice" )

	# in foreground ?
	ret_code=666 # will set set to 0 if shell script OK


	# pass bool as str
	s = "%s %s %s %s" %(script, file_name, str(store_local), local_pic)
	print("calling:", s)

	try:

	#	process = subprocess.Popen([script,file_name], stdout=subprocess.PIPE)
	#	print (" ")
	#	print (process.communicate())
	#	print (" ")
	#	ret_code = process.wait()


		############
		# execute shell script
		############

		ret_code = os.system(s)

	except Exception as e:
		s = "exception in script: %s" %str(e)
		print(s)
		logging.error(s)


	if ret_code == 0:
		s= "pic script return 0, ie OK. filename: %s" %file_name
		print(s)
		logging.info(s)

		if led:
			flash(3,0.1)

		# blink green
		# if 500ms, will be overwriten by further set led
		pj.status.SetLedBlink('D2', 4, [0,200,0], 100, [0, 0,0], 100)

	else :
		s = "ERROR in pic script. NOT SENT. ret code: %d" %ret_code
		print(s)
		logging.error(s)

		send_pushover("picture not sent. ret code: %d" %(ret_code), priority=1, title="PIJuice" )
		if led:
			flash(3,1)

		#blink red
		pj.status.SetLedBlink('D2', 4, [200,0,0], 100, [0, 0,0], 100)

else:
	is_nite = True

	s = "nigth. no pic"
	print(s)
	logging.info(s)

	ret_code = None

	if led:
		flash(1,0.1)

	# nite indicated later (ok; nok; N)
	# string send to blynk terminal. indicates nite 

	# blynk blue
	pj.status.SetLedBlink('D2', 4, [0,0,200], 100, [0, 0,0], 100)

# will not run until script has ran
# after blynk connected and synch
print ("BASH script has run or nigth")

# create blynk there so that it is available in main thread as well

# move to private server in docker

#class Blynk:
#    def __init__(self, token, server='blynk-cloud.com', port=None, connect=True, ssl=False):

# port 8089 mapped to server/property http port 8080 in docker
#  9444 mapped to htpps 9443


##############################
# create blynk
#############################

print("create blynk. server %s, port %d, ssl %s" %(blynk_server, blynk_port, blynk_ssl))
blynk = BlynkLib.Blynk(blynk_token, server=blynk_server, port=blynk_port, ssl=blynk_ssl)


####################
# start blynk thread
####################
# _  for python3
# time string: from ntp or hw. N added for nite.
# soc and ret code used for blynk terminal

print ("param for blynk thread:", time_string, soc,  ret_code)
_thread.start_new_thread(blynk_thread, (time_string, soc, ret_code))


print ("wait for blynk to run and synch button")
c=1
# HALT button
while (button == "2"):
	time.sleep(1)
	c=c+1
	if c==30:

		#########################
		# somehow blynk thread failed (could not connect, ..
		# pic may be there, but update GUI (inck terminal) not done
		########################
		# can keep moving. 
		s= "stay on button could not synch. BLYNK thread failed ?. terminal, gauge not updated. assume button OFF, ie go to sleep"
		print(s)
		logging.error(s)

		button="0"
		break

print ("button has synched or timeout on synch (blynk failed, GUI not updated")

# update count gauge
blynk.virtual_write(bcount, count)

# halt or stay on ?
# STAY ON if either pin to ground (jumper), or stay on button == "1"
# SHUTDOWN if pin high (no jumper) and stay on button == "0"
# pin: default PULLUP , no jumper = HIGH
# halt is int, button UNICODE !!!!!!!


# HALTING (RTC) if Pin H and button "0"
# pin default is pullup, ie halt. jumper to gnd to not halt
# NOTE: updated from None here, ie AFTER camera script and blynk connect. my_watchdog thread may see it as None 

go_to_sleep = (halt == 1 and button == "0")

print("HALTING (RTC) if Pin H (default as pullup) AND stay on button '0' (ie OFF)")
#print ("keep running if halt = LOW (jumper to ground) or stay on button = ON ie string 1")
#print ("shutdown if halt = HIGH (No jumper to ground, PULLUP) and stay on button = OFF ie string 0")

s = "halt pin: %d, stay on button: %s, go to sleep: %s. is_nite: %s" %(halt, button, go_to_sleep, is_nite)
print(s)
logging.info(s)

if go_to_sleep:
	print ("halt pin jumper to HIGH and button OFF. HALTING")

	end_time=datetime.datetime.now()
	print ("start time: ", start_time)
	print ("end time:   ", end_time)
	print ("elapse:     ", end_time - start_time)

        # flash led to signal end
	if led:
	        flash(10,0.1)

	#blink ligth blue RGB
	pj.status.SetLedBlink('D2', 5, [0,0,200], 100, [0, 0,0], 100)

	#############################
	# set alarm , done in GUI or here
	#############################
	# longer delay at nite
	if is_nite:
		sleep_time = sleep_time_nite

	s = "set RTC alarm %d mn from current mn %d" %((sleep_time, current_mn))
	print(s)
	logging.info(s)

	try:
		set_alarm(sleep_time,current_mn,pj)

	except Exception as e:
		s = "Exception while setting alarm: %s" %str(e)
		print(s)
		logging.error(s)

		fatal(s)

	#############################
	# halting
	# power, led, sudo halt
	#############################
	s = "halt with %d sec poweroff delay" %(poweroff_delay)
	print(s)
	logging.info(s)

	try:
		halting(pj,poweroff_delay)
	except Exception as e:
		s = "Exception while halting: %s" %str(e)
		print(s)
		logging.error(s)

		fatal(s)


# keep running
# go_to_sleep = (halt == 1 and button == "0")

else:
	print ("halt pin jumper to LOW or button ON. KEEPS RUNNING\n\n")

	# send pushover in all cases, whether halt pin or button
	# blynk button stay on
	s = ""
	if halt == 0:
		s = s + "halt pin connected to ground. "
	if button != "0":
		s = s + "Blynk Halt/run button set to run."

	# time to run  on battery based on soc
	ttr = get_ttr_h(soc)

	send_pushover("PI stays on\nbecause: %s\nsoc: %d%%\ncan run: %d hour on battery" %(s,soc, int(ttr)), priority = 1, title ="PIJuice is running")


	#SetLedBlink(led, count, rgb1, period1, rgb2, period2)
	# count = 255 infinite  period 10 2550 ms RGB 0 255
	# if 255 will keep bliking even if python has exited (stm32 does it)
	# blink red
	pj.status.SetLedBlink('D2', 5, [200,0,0], 100, [0,0,0], 100)

        # flash led to signal end
	if led:
		flash(5,1)

	blynk.virtual_write(bterminal, 'PI RUNNING. %d hour battery left\n' %int(ttr))

	# orange led to signal we are still on
	pj.status.SetLedState('D2', [0, 0 ,0])
	pj.status.SetLedState('D2', [100, 95 ,80])
	#pj.status.SetLedBlink('D2', 3, [0,200,0], 100, [0, 0, 0], 100)

	# datetime.timedelta
	e = datetime.datetime.now() -start_time

	s = "Exit. PI KEEP RUNNING. elapse: %s" %e
	print(s)
	logging.info(s)

	# send log to cloud
	#ret_code = os.system(script_log)
	#print ("send log script :" , script_log ,  "ret code: " , ret_code)


	#GPIO.cleanup()


	# exit to REPL, or keep running (to use Blynk)
	exit(0)
